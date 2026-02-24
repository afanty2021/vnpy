"""
可转债转股套利策略

基于转股溢价率进行套利。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.convertible.models import ConvertibleBond, ConvertibleArbitragePosition
from vnpy_china_strategy.config import ConvertibleConfig


class ConvertibleArbitrageStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """可转债转股套利策略

    策略逻辑：
    1. 筛选转股溢价率为负的转债
    2. 正股处于上升趋势
    3. 买入转债+融券正股
    4. 执行转股后平仓

    参数：
    - premium_threshold: 溢价率阈值 (负数)
    - min_conversion_value: 最小转股价值
    - trend_days: 趋势判断天数
    """

    parameters = [
        "premium_threshold",
        "min_conversion_value",
        "trend_days",
        "position_ratio",
        "holding_days",
    ]

    variables = [
        "signal_count",
        "positions",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.premium_threshold = setting.get("premium_threshold", -5.0)  # -5%
        self.min_conversion_value = setting.get("min_conversion_value", 100.0)  # 100元
        self.trend_days = setting.get("trend_days", 20)
        self.position_ratio = setting.get("position_ratio", 0.2)
        self.holding_days = setting.get("holding_days", 20)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, ConvertibleArbitragePosition] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = ConvertibleConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("可转债套利策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("可转债套利策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取全部可转债
        cb_list = self._get_all_convertible_bonds()

        for cb in cb_list:
            if self._check_arbitrage_opportunity(cb):
                self._execute_arbitrage(cb)

        # 检查平仓信号
        self._check_close_signals(current_date)

    def _get_all_convertible_bonds(self) -> List[ConvertibleBond]:
        """获取全部可转债"""
        if not self.data_service:
            return []

        try:
            data_list = self.data_service.get_convertible_bonds()
            return [ConvertibleBond.from_dict(d) for d in data_list]
        except Exception:
            pass

        return []

    def _check_arbitrage_opportunity(self, cb: ConvertibleBond) -> bool:
        """检查套利机会

        筛选条件：
        1. 转股溢价率为负
        2. 转股价值 >= 阈值
        3. 正股上升趋势
        """
        # 转股溢价率为负
        if cb.premium_rate >= self.premium_threshold:
            return False

        # 转股价值足够
        if cb.conversion_value < self.min_conversion_value:
            return False

        # 正股上升趋势
        if not self._is_stock_uptrend(cb.stock_symbol):
            return False

        # 检查成交量
        if cb.volume < 10000000:  # 1000万
            return False

        # 排除已持仓
        if cb.symbol in self.positions:
            return False

        return True

    def _is_stock_uptrend(self, symbol: str) -> bool:
        """判断正股是否处于上升趋势

        Args:
            symbol: 股票代码

        Returns:
            是否上升趋势
        """
        # 获取K线数据
        bars = self.get_bar_data(symbol, self.trend_days)
        if len(bars) < self.trend_days:
            return False

        # 计算动量
        start_price = bars[0].open_price
        end_price = bars[-1].close_price

        if start_price <= 0:
            return False

        momentum = (end_price - start_price) / start_price

        # 上升趋势：动量 > 5%
        return momentum > 0.05

    def _execute_arbitrage(self, cb: ConvertibleBond):
        """执行套利

        Args:
            cb: 可转债
        """
        # 获取转债价格
        cb_price = self._get_cb_price(cb.symbol)
        if not cb_price:
            cb_price = cb.cb_price

        # 获取正股价格
        stock_price = self.get_current_price(cb.stock_symbol)
        if not stock_price:
            return

        # 计算仓位
        account = self.cta_engine.get_account() if self.cta_engine else None
        if not account:
            return

        position_value = account.available * self.position_ratio

        # 转债仓位
        cb_value = position_value / 2
        cb_volume = int(cb_value / cb_price / 10) * 10  # 10张=1手

        # 正股仓位（融券）
        stock_volume = int(cb_volume * cb.conversion_ratio)

        if cb_volume <= 0 or stock_volume <= 0:
            return

        # 1. 买入可转债
        if hasattr(self, "buy"):
            self.buy(cb_price, cb_volume, cb.symbol)

        # 2. 融券卖出正股（模拟）
        # 实际需要券商支持融券
        # if hasattr(self, "short"):
        #     self.short(stock_price, stock_volume, cb.stock_symbol)

        # 3. 记录套利持仓
        self.positions[cb.symbol] = ConvertibleArbitragePosition(
            cb_symbol=cb.symbol,
            stock_symbol=cb.stock_symbol,
            cb_volume=cb_volume,
            stock_volume=stock_volume,
            entry_cb_price=cb_price,
            entry_stock_price=stock_price,
            entry_datetime=date.today()
        )

        self.signal_count += 1
        self.write_log(
            f"可转债套利: {cb.name}({cb.symbol}), "
            f"溢价率: {cb.premium_rate:.2f}%, "
            f"转股价值: {cb.conversion_value:.2f}"
        )

    def _get_cb_price(self, symbol: str) -> Optional[float]:
        """获取转债价格

        Args:
            symbol: 转债代码

        Returns:
            转债价格
        """
        # 简化实现
        return None

    def _check_close_signals(self, current_date: date):
        """检查平仓信号

        平仓条件：
        1. 持有天数达到
        2. 转股溢价率转正
        3. 触发强赎
        """
        to_close = []

        for cb_symbol, position in list(self.positions.items()):
            # 持有天数达到
            holding_days = (current_date - position.entry_datetime).days
            if holding_days >= self.holding_days:
                to_close.append(cb_symbol)
                continue

            # 检查溢价率
            cb = self._get_convertible_bond(cb_symbol)
            if cb and cb.premium_rate > 0:
                to_close.append(cb_symbol)

        for cb_symbol in to_close:
            self._close_arbitrage(cb_symbol)

    def _get_convertible_bond(self, symbol: str) -> Optional[ConvertibleBond]:
        """获取可转债信息"""
        cb_list = self._get_all_convertible_bonds()
        for cb in cb_list:
            if cb.symbol == symbol:
                return cb
        return None

    def _close_arbitrage(self, cb_symbol: str):
        """平仓套利

        Args:
            cb_symbol: 转债代码
        """
        position = self.positions.get(cb_symbol)
        if not position:
            return

        # 1. 卖出可转债
        cb_price = self._get_cb_price(cb_symbol)
        if cb_price and position.cb_volume > 0:
            if hasattr(self, "sell"):
                self.sell(cb_price, position.cb_volume, cb_symbol)

        # 2. 买回正股平仓（融券）
        # 实际需要券商支持
        # if hasattr(self, "cover"):
        #     stock_price = self.get_current_price(position.stock_symbol)
        #     if stock_price:
        #         self.cover(stock_price, position.stock_volume, position.stock_symbol)

        # 3. 计算收益
        cb_pnl = (cb_price - position.entry_cb_price) * position.cb_volume if cb_price else 0

        del self.positions[cb_symbol]

        self.write_log(
            f"可转债套利平仓: {cb_symbol}, "
            f"转债盈亏: {cb_pnl:.2f}"
        )
