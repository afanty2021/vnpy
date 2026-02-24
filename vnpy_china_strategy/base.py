"""
策略基础类

提供策略的通用基础功能，包括风控、信号检查等。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal


class RiskControlMixin:
    """风控混入类

    提供策略的风险控制功能：
    - 日止损检查
    - 持仓限制检查
    - ST股票检查
    - 涨跌停检查
    """

    # 默认风控参数
    max_daily_loss: float = -5000  # 最大日亏损
    max_position: int = 10  # 最大持仓股票数
    max_single_position: float = 0.2  # 单票最大仓位比例

    def check_risk_limits(self) -> bool:
        """检查风控限制

        Returns:
            是否通过风控检查
        """
        # 检查单日最大亏损
        if self.check_daily_loss_limit():
            return False

        # 检查最大持仓
        if self.check_position_limit():
            return False

        # 检查ST股票
        if self.check_st_stock():
            return False

        # 检查涨跌停
        if self.check_limit_up_down():
            return False

        return True

    def check_daily_loss_limit(self) -> bool:
        """检查日止损

        Returns:
            是否触发日止损
        """
        if not hasattr(self, "cta_engine"):
            return False

        account = self.cta_engine.get_account()
        if account:
            daily_pnl = account.balance - account.pre_balance
            if daily_pnl < self.max_daily_loss:
                self.write_log(f"触发日止损: {daily_pnl}")
                return True
        return False

    def check_position_limit(self) -> bool:
        """检查持仓限制

        Returns:
            是否超过持仓限制
        """
        if not hasattr(self, "cta_engine"):
            return False

        # 获取当前持仓
        positions = self.cta_engine.get_all_positions()
        if len(positions) >= self.max_position:
            self.write_log(f"超过最大持仓限制: {len(positions)}/{self.max_position}")
            return True
        return False

    def check_st_stock(self, symbol: str = "") -> bool:
        """检查ST股票

        Args:
            symbol: 股票代码，为空时检查所有持仓

        Returns:
            是否为ST股票
        """
        if not self.data_service:
            return False

        if symbol:
            # 检查指定股票
            stock_info = self.data_service.get_stock_info(symbol)
            if stock_info and stock_info.get("is_st", False):
                self.write_log(f"ST股票不可交易: {symbol}")
                return True
        return False

    def check_limit_up_down(self, symbol: str = "") -> bool:
        """检查涨跌停

        Args:
            symbol: 股票代码

        Returns:
            是否涨跌停
        """
        if not symbol:
            return False

        price = self.get_current_price(symbol)
        if not price:
            return False

        tick = self.get_tick(symbol)
        if not tick:
            return False

        # 涨停板
        if tick.limit_up and price >= tick.limit_up:
            self.write_log(f"涨停板不可买入: {symbol}")
            return True

        # 跌停板
        if tick.limit_down and price <= tick.limit_down:
            self.write_log(f"跌停板不可卖出: {symbol}")
            return True

        return False


class SignalChecker:
    """信号检查器

    提供策略信号的检查和过滤功能。
    """

    @staticmethod
    def check_buy_signal_conditions(
        price: float,
        volume: float,
        change_pct: float,
        min_price: float = 0,
        max_change_pct: float = 9.9
    ) -> bool:
        """检查买入信号条件

        Args:
            price: 当前价格
            volume: 成交量
            change_pct: 涨跌幅
            min_price: 最低价格限制
            max_change_pct: 最大涨幅限制

        Returns:
            是否满足买入条件
        """
        # 价格检查
        if price <= min_price:
            return False

        # 涨幅检查（避免追涨停）
        if change_pct >= max_change_pct:
            return False

        # 成交量检查
        if volume <= 0:
            return False

        return True

    @staticmethod
    def check_sell_signal_conditions(
        price: float,
        entry_price: float,
        change_pct: float,
        stop_loss_pct: float = -5.0,
        stop_profit_pct: float = 10.0
    ) -> bool:
        """检查卖出信号条件

        Args:
            price: 当前价格
            entry_price: 买入价格
            change_pct: 当前涨跌幅
            stop_loss_pct: 止损比例
            stop_profit_pct: 止盈比例

        Returns:
            是否触发卖出
        """
        if entry_price <= 0:
            return True

        pnl_pct = (price - entry_price) / entry_price * 100

        # 止损
        if pnl_pct <= stop_loss_pct:
            return True

        # 止盈
        if pnl_pct >= stop_profit_pct:
            return True

        return False


class PositionManager:
    """持仓管理器

    提供持仓的跟踪和管理功能。
    """

    def __init__(self):
        """初始化"""
        self.positions: Dict[str, Dict[str, Any]] = {}

    def add_position(
        self,
        symbol: str,
        volume: int,
        price: float,
        datetime: datetime
    ) -> None:
        """添加持仓

        Args:
            symbol: 股票代码
            volume: 持仓数量
            price: 持仓价格
            datetime: 持仓时间
        """
        self.positions[symbol] = {
            "volume": volume,
            "entry_price": price,
            "entry_datetime": datetime,
            "holding_days": 0
        }

    def update_position(
        self,
        symbol: str,
        volume: int,
        price: float
    ) -> None:
        """更新持仓

        Args:
            symbol: 股票代码
            volume: 持仓数量
            price: 当前价格
        """
        if symbol in self.positions:
            self.positions[symbol]["volume"] = volume
            self.positions[symbol]["current_price"] = price

    def remove_position(self, symbol: str) -> None:
        """移除持仓

        Args:
            symbol: 股票代码
        """
        if symbol in self.positions:
            del self.positions[symbol]

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取持仓

        Args:
            symbol: 股票代码

        Returns:
            持仓信息
        """
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有持仓

        Returns:
            所有持仓信息
        """
        return self.positions

    def calculate_holding_days(self, current_date: datetime) -> None:
        """计算持仓天数

        Args:
            current_date: 当前日期
        """
        for symbol in self.positions:
            entry_dt = self.positions[symbol].get("entry_datetime")
            if entry_dt:
                days = (current_date - entry_dt).days
                self.positions[symbol]["holding_days"] = days

    def check_holding_expired(
        self,
        symbol: str,
        max_days: int
    ) -> bool:
        """检查持仓是否过期

        Args:
            symbol: 股票代码
            max_days: 最大持有天数

        Returns:
            是否过期
        """
        position = self.get_position(symbol)
        if position:
            holding_days = position.get("holding_days", 0)
            return holding_days >= max_days
        return False
