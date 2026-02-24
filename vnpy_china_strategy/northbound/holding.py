"""
北向资金持股变化策略

追踪北向资金持股变化，选择连续增持的股票。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.northbound.models import StockHoldingChange
from vnpy_china_strategy.config import NorthboundConfig


class HoldingChangeStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """北向资金持股变化策略

    策略逻辑：
    1. 监控北向资金持股变化
    2. 持股比例增加 > 阈值
    3. 连续增持效果更好

    参数：
    - change_threshold: 变化阈值
    - consecutive_days: 连续天数
    - min_shares: 最少持股数
    """

    parameters = [
        "change_threshold",
        "consecutive_days",
        "min_shares",
        "position_ratio",
        "holding_days",
    ]

    variables = [
        "signalpositions",
    ]

    def __init__(
        self, cta_engine, strategy_name, vt_symbol, setting
    ):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.change_threshold = setting.get("change_threshold", 0.05)  # 5%
        self.consecutive_days = setting.get("consecutive_days", 3)
        self.min_shares = setting.get("min_shares", 1000000)  # 100万股
        self.position_ratio = setting.get("position_ratio", 0.1)
        self.holding_days = setting.get("holding_days", 10)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, int] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = NorthboundConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("北向持股变化策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("北向持股变化策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取所有股票的持股变化
        stock_changes = self._get_all_holding_changes(current_date)

        if not stock_changes:
            return

        # 筛选买入信号
        buy_signals = self._check_buy_signals(stock_changes)
        for symbol in buy_signals:
            self._execute_buy(symbol)

        # 检查卖出信号
        self._check_sell_signals(bar.datetime)

    def _get_all_holding_changes(
        self,
        trade_date: date
    ) -> Dict[str, List[StockHoldingChange]]:
        """获取所有股票的持股变化"""
        # 这里简化实现，实际需要从数据服务获取
        # 返回每个股票最近N天的持股变化列表
        return {}

    def _get_stock_holding_changes(
        self,
        symbol: str,
        days: int
    ) -> List[StockHoldingChange]:
        """获取单只股票的持股变化

        Args:
            symbol: 股票代码
            days: 天数

        Returns:
            持股变化列表
        """
        if not self.data_service:
            return []

        try:
            data = self.data_service.get_stock_holding(symbol, date.today())
            if data:
                return [StockHoldingChange.from_dict(data)]
        except Exception:
            pass
        return []

    def _check_buy_signals(
        self,
        stock_changes: Dict[str, List[StockHoldingChange]]
    ) -> List[str]:
        """检查买入信号

        筛选条件：
        1. 持股比例增加 > 阈值
        2. 连续增持天数 >= consecutive_days
        3. 持股数 > 最少持股数
        """
        signals = []

        # 遍历所有股票
        for symbol, changes in stock_changes.items():
            if len(changes) < self.consecutive_days:
                continue

            # 检查是否连续增持
            is_consecutive = True
            for change in changes[:self.consecutive_days]:
                if change.change_ratio < self.change_threshold:
                    is_consecutive = False
                    break

            if not is_consecutive:
                continue

            # 检查持股数
            if changes[0].holding_shares < self.min_shares:
                continue

            signals.append(symbol)

        return signals

    def _execute_buy(self, symbol: str):
        """执行买入"""
        if symbol in self.positions:
            return

        if not self.is_tradeable(symbol):
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
        self.write_log(f"北向增持买入: {symbol}")

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
