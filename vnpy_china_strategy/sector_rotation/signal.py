"""
板块轮动信号策略

基于动量交叉等信号进行板块轮动。
"""

from typing import Dict, List, Optional
from datetime import datetime, date

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.sector_rotation.models import RotationSignal, SectorStrength
from vnpy_china_strategy.config import SectorRotationConfig


class RotationSignalStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """轮动信号策略

    策略逻辑：
    1. 监控板块动量变化
    2. 动量反转或加速时产生轮动信号
    3. 执行轮动操作

    参数：
    - rebalance_threshold: 轮动阈值
    - momentum_lookback: 动量回看天数
    """

    parameters = [
        "rebalance_threshold",
        "momentum_lookback",
        "position_ratio",
        "holding_days",
    ]

    variables = [
        "rotation_signals",
        "positions",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.rebalance_threshold = setting.get("rebalance_threshold", 0.2)
        self.momentum_lookback = setting.get("momentum_lookback", 20)
        self.position_ratio = setting.get("position_ratio", 0.15)
        self.holding_days = setting.get("holding_days", 20)

        # 策略变量
        self.rotation_signals: List[RotationSignal] = []
        self.positions: Dict[str, int] = {}
        self.last_momentum: Dict[str, float] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = SectorRotationConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("轮动信号策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("轮动信号策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 计算当前动量
        current_momentum = self._calculate_current_momentum()

        # 检查轮动信号
        signals = self._check_rotation_signals(current_momentum)

        if signals:
            self.rotation_signals.extend(signals)
            self._execute_rotation(signals)

        # 更新动量
        self.last_momentum = current_momentum

    def _calculate_current_momentum(self) -> Dict[str, float]:
        """计算当前动量"""
        # 获取板块列表
        sector_list = self._get_sector_list()

        momentum = {}
        for sector in sector_list:
            bars = self._get_sector_bars(sector, self.momentum_lookback)
            if len(bars) >= 5:
                momentum[sector] = self._calculate_momentum_value(bars)

        return momentum

    def _calculate_momentum_value(self, bars: List[BarData]) -> float:
        """计算动量值

        Args:
            bars: K线数据

        Returns:
            动量值
        """
        if len(bars) < 2:
            return 0.0

        # 使用价格变化率
        start_price = bars[0].open_price
        end_price = bars[-1].close_price

        if start_price <= 0:
            return 0.0

        return (end_price - start_price) / start_price

    def _check_rotation_signals(
        self,
        current_momentum: Dict[str, float]
    ) -> List[RotationSignal]:
        """检查轮动信号

        Args:
            current_momentum: 当前动量

        Returns:
            轮动信号列表
        """
        signals = []

        if not self.last_momentum:
            return signals

        # 比较动量变化
        for sector, momentum in current_momentum.items():
            last_momentum = self.last_momentum.get(sector, 0)

            # 动量反转（从负到正）
            if last_momentum < 0 and momentum > 0:
                signal = RotationSignal(
                    from_sector="",
                    to_sector=sector,
                    signal_date=date.today(),
                    confidence=abs(momentum),
                    reason="动量反转"
                )
                signals.append(signal)

            # 动量加速（增长超过阈值）
            momentum_change = momentum - last_momentum
            if momentum_change > self.rebalance_threshold:
                signal = RotationSignal(
                    from_sector="",
                    to_sector=sector,
                    signal_date=date.today(),
                    confidence=abs(momentum_change),
                    reason="动量加速"
                )
                signals.append(signal)

            # 动量减弱（从正到负）
            elif last_momentum > 0 and momentum < 0:
                signal = RotationSignal(
                    from_sector=sector,
                    to_sector="",
                    signal_date=date.today(),
                    confidence=abs(last_momentum),
                    reason="动量减弱"
                )
                signals.append(signal)

        return signals

    def _execute_rotation(self, signals: List[RotationSignal]):
        """执行轮动

        Args:
            signals: 轮动信号列表
        """
        for signal in signals:
            # 轮出
            if signal.from_sector:
                self._close_sector_positions(signal.from_sector)

            # 轮入
            if signal.to_sector:
                self._open_sector_positions(signal.to_sector)

    def _get_sector_list(self) -> List[str]:
        """获取板块列表"""
        return [
            "银行", "房地产", "医药生物", "电子", "计算机",
            "有色金属", "化工", "机械设备", "汽车", "电力设备"
        ]

    def _get_sector_bars(self, sector: str, days: int) -> List[BarData]:
        """获取板块K线数据"""
        return []

    def _open_sector_positions(self, sector: str):
        """开仓板块"""
        stocks = self._get_sector_stocks(sector)
        if not stocks:
            return

        position_per_stock = self.position_ratio / min(len(stocks), 3)

        for symbol in stocks[:3]:
            if symbol in self.positions:
                continue

            if not self.is_tradeable(symbol):
                continue

            price = self.get_current_price(symbol)
            if not price:
                continue

            account = self.cta_engine.get_account() if self.cta_engine else None
            if account:
                risk_amount = account.available * position_per_stock
                size = self.calculate_position_size(price, risk_amount)
            else:
                size = 100

            if size <= 0:
                continue

            exchange = self._get_exchange_from_symbol(symbol)
            vt_symbol = f"{symbol}.{exchange.value}"

            if hasattr(self, "buy"):
                self.buy(price, size, vt_symbol)

            self.positions[symbol] = 0
            self.position_manager.add_position(
                symbol, size, price, datetime.now()
            )

    def _close_sector_positions(self, sector: str):
        """平仓板块"""
        stocks = self._get_sector_stocks(sector)

        for symbol in stocks:
            if symbol in self.positions:
                self._execute_sell(symbol)

    def _get_sector_stocks(self, sector: str) -> List[str]:
        """获取板块内股票"""
        return []

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
