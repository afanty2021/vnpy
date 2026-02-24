"""
北向资金板块偏好策略

根据北向资金在不同板块的偏好选择股票。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.northbound.models import SectorNorthboundFlow
from vnpy_china_strategy.config import NorthboundConfig


class SectorPreferenceStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """北向资金板块偏好策略

    策略逻辑：
    1. 分析北向资金在不同板块的净流入
    2. 选择净流入最多的前N个板块
    3. 从中选择优质股票买入

    参数：
    - sector_top_n: 板块前N只
    - sector_change_threshold: 板块涨幅阈值
    """

    parameters = [
        "sector_top_n",
        "sector_change_threshold",
        "position_ratio",
        "holding_days",
    ]

    variables = [
        "preferred_sectors",
        "signal_count",
        "positions",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.sector_top_n = setting.get("sector_top_n", 5)
        self.sector_change_threshold = setting.get("sector_change_threshold", 0.03)
        self.position_ratio = setting.get("position_ratio", 0.1)
        self.holding_days = setting.get("holding_days", 10)

        # 策略变量
        self.preferred_sectors: List[str] = []
        self.signal_count = 0
        self.positions: Dict[str, int] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = NorthboundConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("北向板块偏好策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("北向板块偏好策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取板块资金流向
        sector_flows = self._get_sector_flows(current_date)

        if not sector_flows:
            return

        # 选择偏好板块
        self._select_preferred_sectors(sector_flows)

        # 筛选买入信号
        buy_signals = self._check_buy_signals()
        for symbol in buy_signals:
            self._execute_buy(symbol)

        # 检查卖出信号
        self._check_sell_signals(bar.datetime)

    def _get_sector_flows(
        self,
        trade_date: date
    ) -> List[SectorNorthboundFlow]:
        """获取板块资金流向"""
        # 简化实现
        return []

    def _select_preferred_sectors(
        self,
        sector_flows: List[SectorNorthboundFlow]
    ):
        """选择偏好板块

        筛选条件：
        1. 净流入 > 0
        2. 涨幅 > 阈值
        3. 排序取前N
        """
        # 过滤
        valid_flows = [
            f for f in sector_flows
            if f.net_inflow > 0 and f.avg_change > self.sector_change_threshold
        ]

        # 排序
        sorted_flows = sorted(
            valid_flows,
            key=lambda x: x.net_inflow,
            reverse=True
        )

        # 取前N
        self.preferred_sectors = [
            f.sector for f in sorted_flows[:self.sector_top_n]
        ]

    def _check_buy_signals(self) -> List[str]:
        """检查买入信号

        从偏好板块中选择股票买入
        """
        signals = []

        for sector in self.preferred_sectors:
            # 获取板块内股票
            stocks = self._get_sector_stocks(sector)

            for symbol in stocks:
                if symbol in self.positions:
                    continue

                # 检查是否可交易
                if not self.is_tradeable(symbol):
                    continue

                signals.append(symbol)

        return signals[:10]  # 限制买入数量

    def _get_sector_stocks(self, sector: str) -> List[str]:
        """获取板块内股票"""
        # 简化实现
        return []

    def _execute_buy(self, symbol: str):
        """执行买入"""
        if symbol in self.positions:
            return

        price = self.get_current_price(symbol)
        if not price:
            return

        # 计算仓位
        account = self.cta_engine.get_account() if self.cta_engine else None
        if account:
            risk_amount = account.available * self.position_ratio
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
