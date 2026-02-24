"""
龙虎榜游资策略

追踪游资（营业部）买入信号，执行短期交易。
"""

from typing import Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.dragon_tiger.models import DragonTigerRecord
from vnpy_china_strategy.config import DragonTigerConfig


class BrokerMoneyStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """游资策略

    策略逻辑：
    1. 筛选游资净买入 > 阈值的股票
    2. 游资买入占比 > 60%
    3. 短期持有 (2-3天)

    参数：
    - broker_threshold: 游资买入阈值(万)
    - broker_ratio: 游资买入占比
    - holding_days: 持有天数
    - position_ratio: 仓位比例
    """

    parameters = [
        "broker_threshold",
        "broker_ratio",
        "holding_days",
        "position_ratio",
    ]

    variables = [
        "signal_count",
        "positions",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.broker_threshold = setting.get("broker_threshold", 500.0)  # 500万
        self.broker_ratio = setting.get("broker_ratio", 0.6)  # 60%
        self.holding_days = setting.get("holding_days", 3)
        self.position_ratio = setting.get("position_ratio", 0.08)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, int] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = DragonTigerConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("游资策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("游资策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取当日龙虎榜
        dt_data = self._get_dragon_tiger_data(current_date)
        if not dt_data:
            return

        # 筛选游资买入信号
        buy_signals = self._check_buy_signals(dt_data)
        for record in buy_signals:
            self._execute_buy(record)

        # 检查卖出信号
        self._check_sell_signals(bar.datetime)

    def _get_dragon_tiger_data(self, trade_date: date) -> List[DragonTigerRecord]:
        """获取龙虎榜数据"""
        if not self.data_service:
            return []

        try:
            data_list = self.data_service.get_dragon_tiger_data(trade_date)
            return [DragonTigerRecord.from_dict(d) for d in data_list]
        except Exception:
            return []

    def _check_buy_signals(self, records: List[DragonTigerRecord]) -> List[DragonTigerRecord]:
        """检查买入信号

        筛选条件：
        1. 游资净买入 > 阈值
        2. 游资买入占比 > 阈值
        """
        signals = []
        for record in records:
            # 游资净买入 > 阈值
            if record.broker_net < self.broker_threshold * 10000:
                continue

            # 游资买入占比 > 阈值
            if record.total_buy > 0:
                ratio = float(record.broker_buy) / float(record.total_buy)
                if ratio < self.broker_ratio:
                    continue
            else:
                continue

            # 排除ST股票
            if not self.is_tradeable(record.symbol):
                continue

            signals.append(record)

        return signals

    def _execute_buy(self, record: DragonTigerRecord):
        """执行买入"""
        if record.symbol in self.positions:
            return

        if not self.is_tradeable(record.symbol):
            return

        price = self.get_current_price(record.symbol)
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
        exchange = self._get_exchange_from_symbol(record.symbol)
        vt_symbol = f"{record.symbol}.{exchange.value}"

        if hasattr(self, "buy"):
            self.buy(price, size, vt_symbol)

        # 记录持仓
        self.positions[record.symbol] = 0
        self.position_manager.add_position(
            record.symbol, size, price, datetime.now()
        )

        self.signal_count += 1
        self.write_log(
            f"游资买入: {record.name}({record.symbol}), "
            f"游资净买入: {record.broker_net/10000:.2f}万"
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
