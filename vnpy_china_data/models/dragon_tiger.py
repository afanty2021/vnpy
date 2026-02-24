"""
龙虎榜数据模型

定义龙虎榜相关的数据结构。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class DragonTigerData:
    """龙虎榜数据"""

    symbol: str
    name: str
    trade_date: date
    close_price: float = 0.0
    change_pct: float = 0.0  # 涨跌幅
    turnover_rate: float = 0.0  # 换手率

    # 机构席位数据
    institution_net_buy: float = 0.0  # 机构净买入
    institution_buy: float = 0.0  # 机构买入
    institution_sell: float = 0.0  # 机构卖出

    # 营业部数据
    broker_net_buy: float = 0.0  # 营业部净买入
    broker_buy: float = 0.0  # 营业部买入
    broker_sell: float = 0.0  # 营业部卖出

    # 买入卖出的营业部列表
    buy_brokers: List[str] = field(default_factory=list)
    sell_brokers: List[str] = field(default_factory=list)

    # 综合数据
    total_net_buy: float = 0.0  # 总净买入
    reason: str = ""  # 上榜原因

    def __post_init__(self):
        """计算汇总数据"""
        self.total_net_buy = self.institution_net_buy + self.broker_net_buy

    @property
    def is_net_buy(self) -> bool:
        """是否净买入"""
        return self.total_net_buy > 0

    @property
    def buy_strength(self) -> str:
        """买入强度"""
        if self.change_pct > 9:
            return "涨停"
        elif self.change_pct > 5:
            return "强势"
        elif self.change_pct > 0:
            return "上涨"
        elif self.change_pct > -5:
            return "下跌"
        else:
            return "大跌"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "close_price": self.close_price,
            "change_pct": self.change_pct,
            "turnover_rate": self.turnover_rate,
            "institution_net_buy": self.institution_net_buy,
            "institution_buy": self.institution_buy,
            "institution_sell": self.institution_sell,
            "broker_net_buy": self.broker_net_buy,
            "broker_buy": self.broker_buy,
            "broker_sell": self.broker_sell,
            "buy_brokers": self.buy_brokers,
            "sell_brokers": self.sell_brokers,
            "total_net_buy": self.total_net_buy,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DragonTigerData":
        """从字典创建"""
        trade_date = data.get("trade_date")
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)

        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            trade_date=trade_date,
            close_price=float(data.get("close_price", 0)),
            change_pct=float(data.get("change_pct", 0)),
            turnover_rate=float(data.get("turnover_rate", 0)),
            institution_net_buy=float(data.get("institution_net_buy", 0)),
            institution_buy=float(data.get("institution_buy", 0)),
            institution_sell=float(data.get("institution_sell", 0)),
            broker_net_buy=float(data.get("broker_net_buy", 0)),
            broker_buy=float(data.get("broker_buy", 0)),
            broker_sell=float(data.get("broker_sell", 0)),
            buy_brokers=data.get("buy_brokers", []),
            sell_brokers=data.get("sell_brokers", []),
            reason=data.get("reason", ""),
        )


@dataclass
class BrokerTradeData:
    """营业部交易数据"""

    broker_name: str
    trade_date: date
    buy_amount: float = 0.0  # 买入金额
    sell_amount: float = 0.0  # 卖出金额
    net_amount: float = 0.0  # 净买入金额
    buy_count: int = 0  # 买入次数
    sell_count: int = 0  # 卖出次数
    symbols: List[str] = field(default_factory=list)  # 交易的股票

    def to_dict(self) -> dict:
        return {
            "broker_name": self.broker_name,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "buy_amount": self.buy_amount,
            "sell_amount": self.sell_amount,
            "net_amount": self.net_amount,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "symbols": self.symbols,
        }
