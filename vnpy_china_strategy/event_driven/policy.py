"""
政策事件驱动策略

基于政策发布进行交易。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.event_driven.models import PolicyEvent
from vnpy_china_strategy.config import EventDrivenConfig


class PolicyEventStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """政策事件驱动策略

    策略逻辑：
    1. 监控政策发布
    2. 识别相关板块
    3. 事件发生后买入相关板块

    参数：
    - keywords: 关注关键词
    - impact_threshold: 影响阈值
    - sector_exposure: 板块暴露度
    """

    parameters = [
        "keywords",
        "impact_threshold",
        "sector_exposure",
        "position_ratio",
        "holding_days",
    ]

    variables = [
        "signal_count",
        "positions",
        "recent_events",
    ]

    # 政策关键词映射到板块
    KEYWORD_SECTOR_MAP = {
        "新能源": ["电气设备", "汽车", "有色金属"],
        "半导体": ["电子", "计算机"],
        "医药": ["医药生物"],
        "房地产": ["房地产", "建筑装饰"],
        "5G": ["通信", "电子", "计算机"],
        "人工智能": ["计算机", "电子"],
        "碳中和": ["电气设备", "环保", "钢铁"],
        "新基建": ["建筑装饰", "计算机", "通信"],
    }

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.keywords = setting.get(
            "keywords",
            ["新能源", "半导体", "医药", "房地产", "5G", "人工智能"]
        )
        self.impact_threshold = setting.get("impact_threshold", 0.5)
        self.sector_exposure = setting.get("sector_exposure", 0.15)
        self.position_ratio = setting.get("position_ratio", 0.1)
        self.holding_days = setting.get("holding_days", 10)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, int] = {}
        self.recent_events: List[PolicyEvent] = []

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = EventDrivenConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("政策事件策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("政策事件策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取近期政策事件
        events = self._get_recent_policy_events(days=30)

        for event in events:
            if self._check_event_signal(event):
                self._process_policy_event(event)

        # 检查卖出信号
        self._check_sell_signals(bar.datetime)

    def _get_recent_policy_events(self, days: int) -> List[PolicyEvent]:
        """获取近期政策事件

        Args:
            days: 天数

        Returns:
            政策事件列表
        """
        # 简化实现 - 模拟一些政策事件
        # 实际应该从数据服务获取
        return []

    def _check_event_signal(self, event: PolicyEvent) -> bool:
        """检查事件信号

        筛选条件：
        1. 影响级别为正面
        2. 相关板块在关注列表中
        """
        # 检查影响级别
        if event.impact_level != "正面":
            return False

        # 检查关键词
        for keyword in event.keywords:
            if keyword in self.keywords:
                return True

        return False

    def _process_policy_event(self, event: PolicyEvent):
        """处理政策事件

        Args:
            event: 政策事件
        """
        # 获取相关板块
        related_sectors = self._get_related_sectors(event)

        # 买入相关板块
        for sector in related_sectors:
            stocks = self._get_sector_stocks(sector)

            for symbol in stocks[:3]:
                if symbol in self.positions:
                    continue

                if not self.is_tradeable(symbol):
                    continue

                self._execute_buy(symbol, event)

        # 记录事件
        self.recent_events.append(event)

    def _get_related_sectors(self, event: PolicyEvent) -> List[str]:
        """获取相关板块

        Args:
            event: 政策事件

        Returns:
            相关板块列表
        """
        sectors = set()

        # 从事件中获取
        sectors.update(event.related_sectors)

        # 从关键词映射获取
        for keyword in event.keywords:
            if keyword in self.KEYWORD_SECTOR_MAP:
                sectors.update(self.KEYWORD_SECTOR_MAP[keyword])

        return list(sectors)

    def _get_sector_stocks(self, sector: str) -> List[str]:
        """获取板块内股票

        Args:
            sector: 板块名称

        Returns:
            股票列表
        """
        # 简化实现
        return []

    def _execute_buy(self, symbol: str, event: PolicyEvent):
        """执行买入

        Args:
            symbol: 股票代码
            event: 政策事件
        """
        price = self.get_current_price(symbol)
        if not price:
            return

        # 计算仓位
        account = self.cta_engine.get_account() if self.cta_engine else None
        if account:
            risk_amount = account.available * self.sector_exposure
            size = self.calculate_position_size(price, risk_amount)
        else:
            size = 100

        if size <= 0:
            return

        # 执行买入
        exchange = self._get_exchange_from_symbol(symbol)
        vt_symbol = f"{symbol}.{exchange.value}"

        if hasattr(self, "buy"):
            self.buy(price, size, vt_symbol)

        # 记录持仓
        self.positions[symbol] = 0
        self.position_manager.add_position(
            symbol, size, price, datetime.now()
        )

        self.signal_count += 1
        self.write_log(
            f"政策事件买入: {symbol}, 政策: {event.policy_title}"
        )

    def _check_sell_signals(self, current_time: datetime):
        """检查卖出信号"""
        to_close = []

        for symbol, days in list(self.positions.items()):
            if days >= self.holding_days:
                to_close.append(symbol)

        for symbol in to_close:
            self._execute_sell(symbol)

        # 更新持仓天数
        for symbol in self.positions:
            self.positions[symbol] += 1

    def _execute_sell(self, symbol: str):
        """执行卖出"""
        if symbol not in self.positions:
            return

        price = self.get_current_price(symbol)
        if not price:
            return

        position = self.position_manager.get_position(symbol)
        volume = position.get("volume", 0) if position else 0

        if volume <= 0:
            return

        exchange = self._get_exchange_from_symbol(symbol)
        vt_symbol = f"{symbol}.{exchange.value}"

        if hasattr(self, "sell"):
            self.sell(price, volume, vt_symbol)

        del self.positions[symbol]
        self.position_manager.remove_position(symbol)
