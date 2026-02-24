"""
业绩预告事件策略

基于业绩预告进行交易。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.event_driven.models import EarningsForecast
from vnpy_china_strategy.config import EventDrivenConfig


class EarningsForecastStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """业绩预告事件策略

    策略逻辑：
    1. 获取即将发布的业绩预告
    2. 预增/扭亏类型的股票可能上涨
    3. 预告发布后卖出

    参数：
    - event_types: 关注的业绩类型
    - min_yoy_change: 最少同比变化
    - holding_days: 持有天数
    """

    parameters = [
        "event_types",
        "min_yoy_change",
        "holding_days",
        "position_ratio",
    ]

    variables = [
        "signal_count",
        "positions",
    ]

    # 正面业绩类型
    POSITIVE_TYPES = ["预增", "扭亏", "续盈"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.event_types = setting.get(
            "event_types",
            ["预增", "扭亏", "续盈"]
        )
        self.min_yoy_change = setting.get("min_yoy_change", 0.2)  # 20%
        self.holding_days = setting.get("holding_days", 5)
        self.position_ratio = setting.get("position_ratio", 0.1)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, int] = {}
        self.event_cache: Dict[str, EarningsForecast] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = EventDrivenConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("业绩预告策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("业绩预告策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取近期业绩预告
        forecasts = self._get_upcoming_earnings(days_ahead=7)

        for forecast in forecasts:
            if self._check_signal(forecast):
                self._execute_buy(forecast.symbol, forecast)

        # 检查卖出信号
        self._check_sell_signals(bar.datetime)

    def _get_upcoming_earnings(self, days_ahead: int) -> List[EarningsForecast]:
        """获取即将发布的业绩预告

        Args:
            days_ahead: 提前天数

        Returns:
            业绩预告列表
        """
        if not self.data_service:
            return []

        try:
            data_list = self.data_service.get_earnings_forecast("", days_ahead)
            return [EarningsForecast.from_dict(d) for d in data_list]
        except Exception:
            pass

        return []

    def _check_signal(self, forecast: EarningsForecast) -> bool:
        """检查买入信号

        筛选条件：
        1. 业绩类型为正面
        2. 同比变化 >= 阈值
        """
        # 检查业绩类型
        if forecast.earnings_type not in self.event_types:
            return False

        # 检查同比变化
        if forecast.yoy_change is not None:
            if forecast.yoy_change < self.min_yoy_change:
                return False

        # 排除已持仓
        if forecast.symbol in self.positions:
            return False

        # 检查是否可交易
        if not self.is_tradeable(forecast.symbol):
            return False

        return True

    def _execute_buy(self, symbol: str, forecast: EarningsForecast):
        """执行买入

        Args:
            symbol: 股票代码
            forecast: 业绩预告
        """
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

        # 缓存事件
        self.event_cache[symbol] = forecast

        self.signal_count += 1
        self.write_log(
            f"业绩预告买入: {forecast.name}({symbol}), "
            f"类型: {forecast.earnings_type}, "
            f"同比: {forecast.yoy_change*100:.1f}%"
        )

    def _check_sell_signals(self, current_time: datetime):
        """检查卖出信号"""
        to_close = []

        for symbol, days in list(self.positions.items()):
            # 持有天数达到
            if days >= self.holding_days:
                to_close.append(symbol)
            # 业绩预减/预亏
            elif self._check_negative_earnings(symbol):
                to_close.append(symbol)

        for symbol in to_close:
            self._execute_sell(symbol)

        # 更新持仓天数
        for symbol in self.positions:
            self.positions[symbol] += 1

    def _check_negative_earnings(self, symbol: str) -> bool:
        """检查是否业绩预减/预亏

        Args:
            symbol: 股票代码

        Returns:
            是否预减/预亏
        """
        # 简化实现
        return False

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

        # 清除缓存
        if symbol in self.event_cache:
            del self.event_cache[symbol]
