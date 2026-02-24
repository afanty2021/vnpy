"""
龙虎榜数据模型
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional


@dataclass
class DragonTigerRecord:
    """龙虎榜记录

    包含单只股票上榜当日的完整交易信息。
    """

    # 基础信息
    trade_date: date  # 交易日期
    symbol: str  # 股票代码
    name: str  # 股票名称
    close_price: float  # 收盘价
    change_pct: float  # 涨跌幅

    # 机构席位数据
    institution_buy: Decimal = field(default_factory=lambda: Decimal("0"))  # 机构买入金额
    institution_sell: Decimal = field(default_factory=lambda: Decimal("0"))  # 机构卖出金额
    institution_net: Decimal = field(default_factory=lambda: Decimal("0"))  # 机构净买入
    institution_count: int = 0  # 机构买入家数

    # 营业部游资数据
    broker_buy: Decimal = field(default_factory=lambda: Decimal("0"))  # 游资买入金额
    broker_sell: Decimal = field(default_factory=lambda: Decimal("0"))  # 游资卖出金额
    broker_net: Decimal = field(default_factory=lambda: Decimal("0"))  # 游资净买入

    # 合计
    total_buy: Decimal = field(default_factory=lambda: Decimal("0"))  # 总买入
    total_sell: Decimal = field(default_factory=lambda: Decimal("0"))  # 总卖出
    net_buy: Decimal = field(default_factory=lambda: Decimal("0"))  # 净买入

    # 成交额
    turnover: Decimal = field(default_factory=lambda: Decimal("0"))  # 成交额
    turnover_rate: float = 0.0  # 换手率

    # 席位详情
    institution_details: List["InstitutionDetail"] = field(default_factory=list)
    broker_details: List["BrokerDetail"] = field(default_factory=list)

    def to_dict(self):
        """转换为字典"""
        return {
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "symbol": self.symbol,
            "name": self.name,
            "close_price": self.close_price,
            "change_pct": self.change_pct,
            "institution_buy": float(self.institution_buy),
            "institution_sell": float(self.institution_sell),
            "institution_net": float(self.institution_net),
            "institution_count": self.institution_count,
            "broker_buy": float(self.broker_buy),
            "broker_sell": float(self.broker_sell),
            "broker_net": float(self.broker_net),
            "total_buy": float(self.total_buy),
            "total_sell": float(self.total_sell),
            "net_buy": float(self.net_buy),
            "turnover": float(self.turnover),
            "turnover_rate": self.turnover_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DragonTigerRecord":
        """从字典创建"""
        return cls(
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else date.today(),
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            close_price=data.get("close_price", 0.0),
            change_pct=data.get("change_pct", 0.0),
            institution_buy=Decimal(str(data.get("institution_buy", 0))),
            institution_sell=Decimal(str(data.get("institution_sell", 0))),
            institution_net=Decimal(str(data.get("institution_net", 0))),
            institution_count=data.get("institution_count", 0),
            broker_buy=Decimal(str(data.get("broker_buy", 0))),
            broker_sell=Decimal(str(data.get("broker_sell", 0))),
            broker_net=Decimal(str(data.get("broker_net", 0))),
            total_buy=Decimal(str(data.get("total_buy", 0))),
            total_sell=Decimal(str(data.get("total_sell", 0))),
            net_buy=Decimal(str(data.get("net_buy", 0))),
            turnover=Decimal(str(data.get("turnover", 0))),
            turnover_rate=data.get("turnover_rate", 0.0),
        )


@dataclass
class InstitutionDetail:
    """机构席位详情"""

    name: str  # 席位名称
    buy_amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 买入金额
    sell_amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 卖出金额
    net_amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 净买入
    rank: int = 0  # 排名

    def to_dict(self):
        return {
            "name": self.name,
            "buy_amount": float(self.buy_amount),
            "sell_amount": float(self.sell_amount),
            "net_amount": float(self.net_amount),
            "rank": self.rank,
        }


@dataclass
class BrokerDetail:
    """营业部游资详情"""

    broker_name: str  # 营业部名称
    buy_amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 买入金额
    sell_amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 卖出金额
    net_amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 净买入

    def to_dict(self):
        return {
            "broker_name": self.broker_name,
            "buy_amount": float(self.buy_amount),
            "sell_amount": float(self.sell_amount),
            "net_amount": float(self.net_amount),
        }
