"""
A股交易规则GUI引擎
管理A股交易规则的GUI功能
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine
from vnpy.trader.object import OrderData, TradeData, TickData
from vnpy.trader.constant import Direction
from loguru import logger


class ChinaRulesGuiEngine(BaseEngine):
    """A股交易规则GUI引擎

    提供A股交易规则的GUI管理功能：
    - T+1规则管理
    - 涨跌停规则管理
    - 交易时间管理
    - 规则检查结果展示
    """

    engine_name: str = "ChinaRulesApp"

    def __init__(self, main_engine: Any, event_engine: EventEngine) -> None:
        """初始化引擎"""
        super().__init__(main_engine, event_engine, self.engine_name)

        # 规则引擎引用
        self.rules_engine: Optional[Any] = None

        # 规则检查结果历史
        self.check_results: List[Dict[str, Any]] = []

        # 昨收价缓存 {symbol: pre_close}
        self.pre_close_cache: Dict[str, float] = {}

        # 注册事件监听
        self.register_event()

        # 初始化规则引擎
        self.init_rules_engine()

    def init_rules_engine(self) -> None:
        """初始化规则引擎"""
        try:
            from .datasource import DataSourceManager
            from .engine import ChinaStockRulesEngine

            # 创建数据源管理器
            dm = DataSourceManager()

            # 尝试注册QMT数据源（如果可用）
            try:
                from .datasource import QMTDataSource
                qmt_source = QMTDataSource(self.main_engine)
                dm.register_source("qmt", qmt_source, primary=True)
                self.write_log("QMT数据源已注册")
            except Exception as e:
                logger.warning(f"QMT数据源注册失败: {e}")

            # 创建规则引擎
            self.rules_engine = ChinaStockRulesEngine(dm)
            self.write_log("A股交易规则引擎初始化完成")
        except ImportError as e:
            self.write_log(f"警告：无法导入规则引擎: {e}")

    def register_event(self) -> None:
        """注册事件监听"""
        # 订阅订单事件进行规则检查
        self.event_engine.register("order", self.process_order_event)
        # 订阅成交事件更新T+1持仓
        self.event_engine.register("trade", self.process_trade_event)
        # 订阅行情事件更新昨收价
        self.event_engine.register("tick", self.process_tick_event)

    def process_order_event(self, event: Event) -> None:
        """处理订单事件"""
        order = event.data
        # 记录规则检查结果
        if self.rules_engine:
            results = self.rules_engine.check_order(order)
            self.check_results.append({
                "time": datetime.now(),
                "symbol": order.symbol,
                "rule_results": results,
            })

    def process_trade_event(self, event: Event) -> None:
        """处理成交事件"""
        trade: TradeData = event.data
        if self.rules_engine:
            self.rules_engine.on_trade(trade)

    def process_tick_event(self, event: Event) -> None:
        """处理行情事件"""
        tick: TickData = event.data
        # 缓存昨收价
        if hasattr(tick, "pre_close") and tick.pre_close:
            self.pre_close_cache[tick.symbol] = tick.pre_close

    def set_rules_engine(self, rules_engine: Any) -> None:
        """设置规则引擎"""
        self.rules_engine = rules_engine
        self.write_log("规则引擎已设置")

    def get_rules_engine(self) -> Optional[Any]:
        """获取规则引擎"""
        return self.rules_engine

    # GUI功能方法

    def get_sellable_volume(self, symbol: str) -> int:
        """
        获取可卖出数量

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        int
            可卖出数量
        """
        if self.rules_engine:
            return self.rules_engine.t1_rules.get_sellable_volume(
                symbol, datetime.now()
            )
        return 0

    def calculate_limit_price(
        self, symbol: str, prev_close: float
    ) -> Optional[tuple[float, float]]:
        """
        计算涨跌停价格

        Parameters
        ----------
        symbol : str
            股票代码
        prev_close : float
            昨收价

        Returns
        -------
        Optional[tuple[float, float]]
            (涨停价, 跌停价) 或 None
        """
        if self.rules_engine:
            try:
                return self.rules_engine.price_limit_rules.calculate_limit_price(
                    symbol, prev_close
                )
            except Exception as e:
                logger.error(f"计算涨跌停价格失败: {e}")
        return None

    def get_pre_close(self, symbol: str) -> Optional[float]:
        """
        获取昨收价

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[float]
            昨收价或None
        """
        # 从缓存获取
        if symbol in self.pre_close_cache:
            return self.pre_close_cache[symbol]

        # 尝试从数据源获取
        if self.rules_engine:
            market_data = self.rules_engine.dm.get_market_data(symbol)
            if market_data and hasattr(market_data, "pre_close"):
                self.pre_close_cache[symbol] = market_data.pre_close
                return market_data.pre_close

        return None

    def is_trading_time(self) -> bool:
        """
        判断当前是否在交易时间

        Returns
        -------
        bool
            是否在交易时间
        """
        if self.rules_engine:
            return self.rules_engine.time_rules.is_trading_time(datetime.now())
        return False

    def get_trading_status(self) -> Dict[str, Any]:
        """
        获取交易状态信息

        Returns
        -------
        Dict[str, Any]
            交易状态信息
        """
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()

        # 判断交易时段
        trading_phase = "非交易时间"
        from datetime import time

        if time(9, 15) <= current_time <= time(9, 25):
            trading_phase = "集合竞价"
        elif time(9, 30) <= current_time <= time(11, 30):
            trading_phase = "上午交易"
        elif time(13, 0) <= current_time <= time(15, 0):
            trading_phase = "下午交易"
        elif time(15, 0) <= current_time <= time(15, 30):
            trading_phase = "大宗交易"

        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "trading_phase": trading_phase,
            "is_trading": self.is_trading_time(),
        }

    def check_order(self, order: Any) -> list:
        """检查订单"""
        if self.rules_engine:
            return self.rules_engine.check_order(order)
        return []

    def get_check_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取检查历史

        Parameters
        ----------
        limit : int
            最大返回数量

        Returns
        -------
        List[Dict[str, Any]]
            检查历史列表
        """
        return self.check_results[-limit:] if self.check_results else []

    def clear_check_history(self) -> None:
        """清空检查历史"""
        self.check_results.clear()
        self.write_log("检查历史已清空")


__all__ = ["ChinaRulesGuiEngine"]
