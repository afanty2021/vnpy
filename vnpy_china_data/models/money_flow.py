"""
资金流向数据模型
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class MoneyFlowData:
    """个股资金流向数据

    Tushare moneyflow接口返回的资金流向数据。
    """

    # 基本信息
    symbol: str                 # 股票代码
    name: str                   # 股票名称
    trade_date: date            # 交易日期

    # 价格信息
    close_price: float          # 收盘价
    change_pct: float           # 涨跌幅 (%)

    # 资金流向数据（单位：手）
    super_large_buy: int        # 超大单买入量
    super_large_sell: int       # 超大单卖出量
    large_buy: int              # 大单买入量
    large_sell: int             # 大单卖出量
    medium_buy: int             # 中单买入量
    medium_sell: int            # 中单卖出量
    small_buy: int              # 小单买入量
    small_sell: int             # 小单卖出量

    # 资金流向数据（单位：元）
    super_large_buy_amount: float     # 超大单买入金额
    super_large_sell_amount: float    # 超大单卖出金额
    large_buy_amount: float           # 大单买入金额
    large_sell_amount: float          # 大单卖出金额
    medium_buy_amount: float          # 中单买入金额
    medium_sell_amount: float         # 中单卖出金额
    small_buy_amount: float           # 小单买入金额
    small_sell_amount: float          # 小单卖出金额

    # 计算字段
    @property
    def super_large_net(self) -> int:
        """超大单净流入（手）"""
        return self.super_large_buy - self.super_large_sell

    @property
    def large_net(self) -> int:
        """大单净流入（手）"""
        return self.large_buy - self.large_sell

    @property
    def medium_net(self) -> int:
        """中单净流入（手）"""
        return self.medium_buy - self.medium_sell

    @property
    def small_net(self) -> int:
        """小单净流入（手）"""
        return self.small_buy - self.small_sell

    @property
    def super_large_net_amount(self) -> float:
        """超大单净流入金额（元）"""
        return self.super_large_buy_amount - self.super_large_sell_amount

    @property
    def large_net_amount(self) -> float:
        """大单净流入金额（元）"""
        return self.large_buy_amount - self.large_sell_amount

    @property
    def medium_net_amount(self) -> float:
        """中单净流入金额（元）"""
        return self.medium_buy_amount - self.medium_sell_amount

    @property
    def small_net_amount(self) -> float:
        """小单净流入金额（元）"""
        return self.small_buy_amount - self.small_sell_amount

    @property
    def total_net_amount(self) -> float:
        """总净流入金额（元）"""
        return (
            self.super_large_net_amount +
            self.large_net_amount +
            self.medium_net_amount +
            self.small_net_amount
        )

    @property
    def main_net_amount(self) -> float:
        """主力净流入金额（元）= 超大单 + 大单"""
        return self.super_large_net_amount + self.large_net_amount
