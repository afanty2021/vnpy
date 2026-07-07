"""
A股优化设置

提供A股市场的交易成本计算和优化配置。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from vnpy.trader.optimize import OptimizationSetting

# A 股默认费率单一真值源：dataclass 字段与下游函数默认参数统一引用以下常量，
# 避免费率调整时多处字面量漏改（如 2023-08-28 印花税 0.001→0.0005）
_DEFAULT_COMMISSION_RATE: float = 0.0003   # 万3佣金
_DEFAULT_MIN_COMMISSION: float = 5.0        # 最低5元
_DEFAULT_STAMP_DUTY: float = 0.0005         # 印花税0.05%（仅卖出，自 2023-08-28 起）


@dataclass
class ChinaTradingCost:
    """A股交易成本配置"""
    commission_rate: float = _DEFAULT_COMMISSION_RATE
    min_commission: float = _DEFAULT_MIN_COMMISSION
    stamp_duty: float = _DEFAULT_STAMP_DUTY
    transfer_fee: float = 0.00001         # 过户费0.001%
    handling_fee: float = 0.00000685      # 经手费0.000685%
    slippage: float = 0.0                 # 滑点（可配置）

    def calculate_buy_cost(self, price: float, volume: int) -> float:
        """
        计算买入成本

        Args:
            price: 买入价格
            volume: 买入数量（手，1手=100股）

        Returns:
            总成本
        """
        # 买入金额
        amount = price * volume * 100  # 转换为股数

        # 佣金（按万3计算，最低5元）
        commission = max(amount * self.commission_rate, self.min_commission)

        # 过户费（双向收取）
        transfer = amount * self.transfer_fee

        # 经手费（双向收取）
        handling = amount * self.handling_fee

        # 滑点
        slippage_cost = amount * self.slippage

        return amount + commission + transfer + handling + slippage_cost

    def calculate_sell_cost(self, price: float, volume: int) -> float:
        """
        计算卖出成本

        Args:
            price: 卖出价格
            volume: 卖出数量（手）

        Returns:
            净收入（扣除成本后）
        """
        # 卖出金额
        amount = price * volume * 100

        # 佣金
        commission = max(amount * self.commission_rate, self.min_commission)

        # 印花税（仅卖出，0.1%）
        stamp = amount * self.stamp_duty

        # 过户费
        transfer = amount * self.transfer_fee

        # 经手费
        handling = amount * self.handling_fee

        # 滑点
        slippage_cost = amount * self.slippage

        # 总成本
        total_cost = commission + stamp + transfer + handling + slippage_cost

        return amount - total_cost

    def calculate_round_trip_cost(self, price: float, volume: int) -> float:
        """
        计算往返交易成本

        Args:
            price: 交易价格
            volume: 交易数量

        Returns:
            往返总成本率
        """
        buy_cost = self.calculate_buy_cost(price, volume)
        sell_income = self.calculate_sell_cost(price, volume)

        total_cost = buy_cost - sell_income
        cost_rate = total_cost / buy_cost if buy_cost > 0 else 0

        return cost_rate


class ChinaOptimizerSetting(OptimizationSetting):
    """
    A股优化设置

    扩展自vnpy.trader.optimize.OptimizationSetting，
    添加A股特定的交易成本配置。
    """

    def __init__(self) -> None:
        super().__init__()
        self.trading_cost: ChinaTradingCost = ChinaTradingCost()
        self.t1_rule: bool = True  # T+1规则
        self.price_limit: bool = True  # 涨跌停规则
        self.min_trading_unit: int = 100  # 最小交易单位（股）

    def set_trading_cost(
        self,
        commission_rate: float = _DEFAULT_COMMISSION_RATE,
        min_commission: float = _DEFAULT_MIN_COMMISSION,
        stamp_duty: float = _DEFAULT_STAMP_DUTY,
        slippage: float = 0.0
    ) -> None:
        """设置交易成本"""
        self.trading_cost = ChinaTradingCost(
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_duty=stamp_duty,
            slippage=slippage
        )

    def calculate_total_cost(
        self,
        entry_price: float,
        exit_price: float,
        volume: int
    ) -> float:
        """
        计算完整交易成本

        Args:
            entry_price: 开仓价格
            exit_price: 平仓价格
            volume: 交易数量

        Returns:
            总成本金额
        """
        buy_cost = self.trading_cost.calculate_buy_cost(entry_price, volume)
        sell_income = self.trading_cost.calculate_sell_cost(exit_price, volume)

        return buy_cost - sell_income


def calculate_china_trading_cost(
    price: float,
    volume: int,
    is_buy: bool = True,
    commission_rate: float = _DEFAULT_COMMISSION_RATE,
    stamp_duty: float = _DEFAULT_STAMP_DUTY
) -> float:
    """
    便捷函数：计算A股交易成本

    Args:
        price: 交易价格
        volume: 交易数量（手）
        is_buy: 是否买入
        commission_rate: 佣金率
        stamp_duty: 印花税率

    Returns:
        交易成本
    """
    cost_config = ChinaTradingCost(
        commission_rate=commission_rate,
        stamp_duty=stamp_duty
    )

    if is_buy:
        return cost_config.calculate_buy_cost(price, volume)
    else:
        return cost_config.calculate_sell_cost(price, volume)
