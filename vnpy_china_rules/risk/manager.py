"""
A股风险管理器

整合 vnpy_riskmanager 和 A股规则引擎
"""

from typing import Optional, List, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

if TYPE_CHECKING:
    from vnpy_riskmanager.engine import RiskEngine

from vnpy_china_rules.engine import ChinaStockRulesEngine
from vnpy_china_rules.datasource import DataSourceManager

try:
    from vnpy_china_rules.risk.rules import (
        CapitalRiskRule,
        PositionControlRule,
        StopProfitLossRule,
        TradingLimitRule,
    )
except ImportError:
    # vnpy_riskmanager 缺失时降级为 None；_register_custom_rules 仅在
    # _init_risk_manager 成功后调用（vnpy_riskmanager 已安装），运行时非 None。
    CapitalRiskRule = None
    PositionControlRule = None
    StopProfitLossRule = None
    TradingLimitRule = None


@dataclass
class RiskAlertEvent:
    """风控告警事件"""
    rule_name: str           # 规则名称
    rule_type: str           # 规则类型
    message: str             # 触发消息
    severity: str            # 严重程度 (info/warning/critical)
    data: dict = field(default_factory=dict)  # 相关数据
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳


class IRiskAlertProvider:
    """风控告警提供者接口 - 被vnpy_china_monitor调用"""

    def get_active_risk_alerts(self) -> List[RiskAlertEvent]:
        """获取当前活跃的风控告警"""
        raise NotImplementedError

    def subscribe_risk_events(self, callback: Callable[[RiskAlertEvent], None]):
        """订阅风控事件"""
        raise NotImplementedError

    def get_risk_status(self) -> dict:
        """获取风控状态摘要"""
        raise NotImplementedError


class AStockRiskManager(IRiskAlertProvider):
    """A股风险管理器 - 实现IRiskAlertProvider接口"""

    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 初始化 vnpy_riskmanager
        self.risk_engine: Optional["RiskEngine"] = None

        # 初始化 A股规则引擎
        self.china_rules_engine: Optional[ChinaStockRulesEngine] = None

        # 告警事件回调列表
        self._risk_callbacks: List[Callable[[RiskAlertEvent], None]] = []

        # 活跃告警列表
        self._active_alerts: List[RiskAlertEvent] = []

        # 告警统计
        self._alert_stats: dict = {
            "total_alerts": 0,
            "critical_count": 0,
            "warning_count": 0,
            "info_count": 0,
        }

    def initialize(self, qmt_gateway=None, tushare_token=None):
        """初始化风控系统"""
        # 1. 初始化数据源
        datasource_manager = DataSourceManager()

        if qmt_gateway:
            from vnpy_china_rules.datasource import QMTDataSource
            qmt_source = QMTDataSource(qmt_gateway)
            datasource_manager.register_source("qmt", qmt_source, primary=True)

        if tushare_token:
            from vnpy_china_rules.datasource import TushareDataSource
            tushare_source = TushareDataSource(tushare_token)
            datasource_manager.register_source("tushare", tushare_source)

        # 2. 初始化A股规则引擎
        self.china_rules_engine = ChinaStockRulesEngine(datasource_manager)

        # 3. 初始化vnpy_riskmanager
        self._init_risk_manager()

    def _init_risk_manager(self):
        """初始化风控引擎"""
        from vnpy_riskmanager import RiskManagerApp
        from vnpy_riskmanager.engine import RiskEngine

        # 添加风控应用
        self.main_engine.add_app(RiskManagerApp)
        self.risk_engine = self.main_engine.get_engine(RiskEngine)

        # 注册自定义规则
        self._register_custom_rules()

    def _register_custom_rules(self):
        """注册 A股自定义风控规则到 vnpy_riskmanager 引擎

        前置：仅 _init_risk_manager 成功后调用（vnpy_riskmanager 已安装），
        故顶部导入的 4 个规则类必非 None。
        add_rule 用 rule_class.name（类属性）作 setting key 与 rules 字典 key，
        与实例 rule.name（继承类属性）一致——隐含契约：规则不在 on_init 中
        动态修改 self.name（当前 4 个规则均无此行为）。
        """
        rule_classes = [
            CapitalRiskRule, PositionControlRule,
            StopProfitLossRule, TradingLimitRule,
        ]

        registered_rules = []
        for rule_class in rule_classes:
            try:
                self.risk_engine.add_rule(rule_class)
                rule = self.risk_engine.rules.get(rule_class.name)
                if rule is not None:
                    registered_rules.append(rule)
                else:
                    self.write_log(f"注册风控规则未找到实例: {rule_class.name}")
            except Exception as e:
                self.write_log(f"注册风控规则失败 {rule_class.__name__}: {e}")

        if not registered_rules:
            self.write_log("全部风控规则注册失败，请检查 vnpy_riskmanager 与规则类")

        try:
            self._register_rule_events(registered_rules)
        except Exception as e:
            self.write_log(f"风控规则事件回调注册失败: {e}")

        # 告警联动：仅 CapitalRiskRule/PositionControlRule 有 set_risk_manager
        for rule in registered_rules:
            try:
                if hasattr(rule, "set_risk_manager"):
                    rule.set_risk_manager(self)
            except Exception as e:
                self.write_log(f"风控规则告警联动失败 {rule.name}: {e}")
            self.write_log(f"成功注册风控规则: {rule.name}")

    def _register_rule_events(self, rules):
        """为新注册的规则补注册事件回调

        register_events 已在 RiskEngine.__init__ 跑完，后 add_rule 的规则需手动补。
        needs_callback 在 add_rule（实例化）后调用，规则方法已绑定子类重写版本。
        每事件类型显式 register 一次（不依赖 EventEngine.register 内部幂等性）。
        """
        from vnpy.trader.event import (
            EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_TIMER,
        )

        engine = self.risk_engine
        buckets = [
            ("on_tick", engine.tick_rules, EVENT_TICK, engine.process_tick_event),
            ("on_order", engine.order_rules, EVENT_ORDER, engine.process_order_event),
            ("on_trade", engine.trade_rules, EVENT_TRADE, engine.process_trade_event),
            ("on_timer", engine.timer_rules, EVENT_TIMER, engine.process_timer_event),
        ]

        events_to_register = []
        for method_name, bucket, event_type, handler in buckets:
            added = False
            for rule in rules:
                if engine.needs_callback(rule, method_name) and rule not in bucket:
                    bucket.append(rule)
                    added = True
            if added:
                events_to_register.append((event_type, handler))

        for event_type, handler in events_to_register:
            engine.event_engine.register(event_type, handler)

    def write_log(self, msg: str):
        """写日志"""
        # 尝试使用主引擎的日志功能
        if hasattr(self.main_engine, "get_logger"):
            logger = self.main_engine.get_logger()
            if logger:
                logger.info(msg)
                return

        # 降级使用 print
        print(f"[AStockRiskManager] {msg}")

    def get_risk_engine(self) -> "RiskEngine":
        """获取风控引擎"""
        return self.risk_engine

    def get_china_rules_engine(self) -> ChinaStockRulesEngine:
        """获取A股规则引擎"""
        return self.china_rules_engine

    # ==================== IRiskAlertProvider 接口实现 ====================

    def get_active_risk_alerts(self) -> List[RiskAlertEvent]:
        """获取当前活跃的风控告警"""
        # 清理超过1小时的告警
        now = datetime.now()
        self._active_alerts = [
            alert for alert in self._active_alerts
            if (now - alert.timestamp).total_seconds() < 3600
        ]
        return self._active_alerts.copy()

    def subscribe_risk_events(self, callback: Callable[[RiskAlertEvent], None]):
        """订阅风控事件"""
        if callback not in self._risk_callbacks:
            self._risk_callbacks.append(callback)

    def unsubscribe_risk_events(self, callback: Callable[[RiskAlertEvent], None]):
        """取消订阅风控事件"""
        if callback in self._risk_callbacks:
            self._risk_callbacks.remove(callback)

    def get_risk_status(self) -> dict:
        """获取风控状态摘要"""
        # 获取账户信息
        account = self.main_engine.get_account() if hasattr(self.main_engine, "get_account") else None

        # 计算风控指标
        total_pnl = 0.0
        daily_pnl = 0.0
        capital_usage = 0.0

        if account:
            total_pnl = getattr(account, "balance", 0) - getattr(account, "pre_balance", total_pnl)
            available = getattr(account, "available", 0)
            balance = getattr(account, "balance", 1)
            capital_usage = (balance - available) / balance if balance > 0 else 0

        # 计算持仓比例
        total_position_ratio = 0.0
        positions = self.main_engine.get_all_positions() if hasattr(self.main_engine, "get_all_positions") else []
        if account and account.balance > 0:
            position_value = sum(
                getattr(p, "volume", 0) * getattr(p, "price", 0)
                for p in positions
                if getattr(p, "volume", 0) > 0
            )
            total_position_ratio = position_value / account.balance

        # 计算日亏损比例
        daily_loss_ratio = 0.0
        if account and hasattr(account, "pre_balance") and account.pre_balance > 0:
            daily_loss_ratio = min(0, daily_pnl) / account.pre_balance

        return {
            "daily_pnl": daily_pnl,
            "daily_loss_ratio": daily_loss_ratio,
            "total_position_ratio": total_position_ratio,
            "capital_usage": capital_usage,
            "active_alerts": len(self._active_alerts),
            "alert_stats": self._alert_stats.copy(),
            "timestamp": datetime.now().isoformat(),
        }

    def _trigger_alert(
        self,
        rule_name: str,
        rule_type: str,
        message: str,
        severity: str = "info",
        data: dict = None
    ):
        """触发风控告警"""
        # 创建告警事件
        alert = RiskAlertEvent(
            rule_name=rule_name,
            rule_type=rule_type,
            message=message,
            severity=severity,
            data=data or {},
        )

        # 添加到活跃列表
        self._active_alerts.append(alert)

        # 更新统计
        self._alert_stats["total_alerts"] += 1
        if severity == "critical":
            self._alert_stats["critical_count"] += 1
        elif severity == "warning":
            self._alert_stats["warning_count"] += 1
        else:
            self._alert_stats["info_count"] += 1

        # 通知所有订阅者
        for callback in self._risk_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.write_log(f"告警回调执行失败: {str(e)}")

        # 写日志
        self.write_log(f"[{severity.upper()}] {rule_name}: {message}")

        return alert


def create_risk_manager(main_engine, event_engine, qmt_gateway=None, tushare_token=None):
    """
    便捷函数：创建并初始化A股风控管理器

    Args:
        main_engine: 主引擎
        event_engine: 事件引擎
        qmt_gateway: QMT网关实例（可选）
        tushare_token: Tushare token（可选）

    Returns:
        AStockRiskManager: 风控管理器实例
    """
    risk_manager = AStockRiskManager(main_engine, event_engine)
    risk_manager.initialize(qmt_gateway=qmt_gateway, tushare_token=tushare_token)
    return risk_manager
