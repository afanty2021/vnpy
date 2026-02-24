"""
龙虎榜机构席位策略

追踪机构席位买入信号，执行相应的买入卖出操作。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Direction, Offset

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.dragon_tiger.models import DragonTigerRecord
from vnpy_china_strategy.config import DragonTigerConfig


class InstitutionTrackerStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """机构席位追踪策略

    策略逻辑：
    1. 每日收盘后获取当日龙虎榜数据
    2. 筛选机构净买入 > 阈值的股票
    3. 机构买入家数 >= 3家
    4. 买入后持有 N 天卖出

    参数：
    - institution_threshold: 机构买入阈值(万)
    - min_institution_count: 最少机构数
    - holding_days: 持有天数
    - position_ratio: 仓位比例
    """

    # 策略参数
    parameters = [
        "institution_threshold",
        "min_institution_count",
        "holding_days",
        "position_ratio",
        "stop_loss_pct",
        "stop_profit_pct",
    ]

    # 策略变量
    variables = [
        "signal_count",
        "positions",
        "last_trade_date",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.institution_threshold = setting.get("institution_threshold", 1000.0)  # 1000万
        self.min_institution_count = setting.get("min_institution_count", 3)
        self.holding_days = setting.get("holding_days", 5)
        self.position_ratio = setting.get("position_ratio", 0.1)
        self.stop_loss_pct = setting.get("stop_loss_pct", -5.0)
        self.stop_profit_pct = setting.get("stop_profit_pct", 10.0)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, int] = {}  # symbol -> entry_day
        self.last_trade_date: Optional[date] = None

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = DragonTigerConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("机构席位追踪策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("机构席位追踪策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("机构席位追踪策略停止")
        # 平仓
        self.close_all_positions()

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 每日只处理一次
        current_date = bar.datetime.date()
        if self.last_trade_date == current_date:
            return

        self.last_trade_date = current_date

        # 风控检查
        if not self.check_risk_limits():
            self.write_log("风控检查未通过，暂停交易")
            return

        # 获取当日龙虎榜
        dt_data = self._get_dragon_tiger_data(current_date)

        if not dt_data:
            return

        # 筛选机构买入信号
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
        except Exception as e:
            self.write_log(f"获取龙虎榜数据失败: {e}")
            return []

    def _check_buy_signals(self, records: List[DragonTigerRecord]) -> List[DragonTigerRecord]:
        """检查买入信号

        Args:
            records: 龙虎榜记录列表

        Returns:
            符合条件的买入信号列表
        """
        signals = []
        for record in records:
            # 机构净买入 > 阈值
            if record.institution_net < self.institution_threshold * 10000:
                continue

            # 机构买入家数 >= 阈值
            if record.institution_count < self.min_institution_count:
                continue

            # 排除ST股票
            if not self.is_tradeable(record.symbol):
                continue

            signals.append(record)

        return signals

    def _execute_buy(self, record: DragonTigerRecord):
        """执行买入

        Args:
            record: 龙虎榜记录
        """
        if record.symbol in self.positions:
            return

        # 检查是否可交易
        if not self.is_tradeable(record.symbol):
            return

        # 获取当前价格
        price = self.get_current_price(record.symbol)
        if not price:
            self.write_log(f"无法获取价格: {record.symbol}")
            return

        # 计算仓位
        account = self.cta_engine.get_account() if self.cta_engine else None
        if account:
            risk_amount = account.available * self.position_ratio
            size = self.calculate_position_size(price, risk_amount)
        else:
            size = 100  # 默认100股

        if size <= 0:
            return

        # 执行买入
        exchange = self._get_exchange_from_symbol(record.symbol)
        vt_symbol = f"{record.symbol}.{exchange.value}"

        # 调用CTA引擎买入
        if hasattr(self, "buy"):
            self.buy(price, size, vt_symbol)

        # 记录持仓
        self.positions[record.symbol] = 0
        self.position_manager.add_position(
            record.symbol, size, price, datetime.now()
        )

        self.signal_count += 1
        self.write_log(
            f"买入信号: {record.name}({record.symbol}), "
            f"机构净买入: {record.institution_net/10000:.2f}万, "
            f"机构数: {record.institution_count}"
        )

    def _check_sell_signals(self, current_time: datetime):
        """检查卖出信号

        Args:
            current_time: 当前时间
        """
        to_close = []

        for symbol, days in list(self.positions.items()):
            # 持有天数达到
            if days >= self.holding_days:
                to_close.append(symbol)
                self.write_log(f"持有天数达到卖出: {symbol}")
            # 止损
            elif self._check_stop_loss(symbol):
                to_close.append(symbol)
                self.write_log(f"止损卖出: {symbol}")
            # 止盈
            elif self._check_stop_profit(symbol):
                to_close.append(symbol)
                self.write_log(f"止盈卖出: {symbol}")

        for symbol in to_close:
            self._execute_sell(symbol)

        # 更新持仓天数
        for symbol in self.positions:
            self.positions[symbol] += 1

    def _check_stop_loss(self, symbol: str) -> bool:
        """检查止损

        Args:
            symbol: 股票代码

        Returns:
            是否触发止损
        """
        position = self.position_manager.get_position(symbol)
        if not position:
            return False

        entry_price = position.get("entry_price", 0)
        if entry_price <= 0:
            return False

        current_price = self.get_current_price(symbol)
        if not current_price:
            return False

        pnl_pct = (current_price - entry_price) / entry_price * 100
        return pnl_pct <= self.stop_loss_pct

    def _check_stop_profit(self, symbol: str) -> bool:
        """检查止盈

        Args:
            symbol: 股票代码

        Returns:
            是否触发止盈
        """
        position = self.position_manager.get_position(symbol)
        if not position:
            return False

        entry_price = position.get("entry_price", 0)
        if entry_price <= 0:
            return False

        current_price = self.get_current_price(symbol)
        if not current_price:
            return False

        pnl_pct = (current_price - entry_price) / entry_price * 100
        return pnl_pct >= self.stop_profit_pct

    def _execute_sell(self, symbol: str):
        """执行卖出

        Args:
            symbol: 股票代码
        """
        if symbol not in self.positions:
            return

        # 获取当前价格
        price = self.get_current_price(symbol)
        if not price:
            return

        # 获取持仓数量
        position = self.position_manager.get_position(symbol)
        volume = position.get("volume", 0) if position else 0

        if volume <= 0:
            return

        # 执行卖出
        exchange = self._get_exchange_from_symbol(symbol)
        vt_symbol = f"{symbol}.{exchange.value}"

        if hasattr(self, "sell"):
            self.sell(price, volume, vt_symbol)

        # 移除持仓
        del self.positions[symbol]
        self.position_manager.remove_position(symbol)

    def close_all_positions(self):
        """平所有持仓"""
        for symbol in list(self.positions.keys()):
            self._execute_sell(symbol)
