"""
北向资金数据模型
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, Optional, List


@dataclass
class NorthboundFlow:
    """北向资金流向

    记录每日的北向资金（沪股通+深股通）净流入情况。
    """

    trade_date: date  # 交易日期
    net_inflow: Decimal = field(default_factory=lambda: Decimal("0"))  # 净流入
    inflow: Decimal = field(default_factory=lambda: Decimal("0"))  # 买入额
    outflow: Decimal = field(default_factory=lambda: Decimal("0"))  # 卖出额
    balance: Decimal = field(default_factory=lambda: Decimal("0"))  # 余额

    def to_dict(self) -> Dict:
        return {
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "net_inflow": float(self.net_inflow),
            "inflow": float(self.inflow),
            "outflow": float(self.outflow),
            "balance": float(self.balance),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NorthboundFlow":
        return cls(
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else date.today(),
            net_inflow=Decimal(str(data.get("net_inflow", 0))),
            inflow=Decimal(str(data.get("inflow", 0))),
            outflow=Decimal(str(data.get("outflow", 0))),
            balance=Decimal(str(data.get("balance", 0))),
        )


@dataclass
class StockHoldingChange:
    """个股持股变化

    记录北向资金对单只股票的持股变化情况。
    """

    symbol: str  # 股票代码
    trade_date: date  # 交易日期
    holding_shares: int = 0  # 持股数
    holding_ratio: float = 0.0  # 持股比例
    change_shares: int = 0  # 变化股数
    change_ratio: float = 0.0  # 变化比例
    net_inflow: Decimal = field(default_factory=lambda: Decimal("0"))  # 净流入

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "holding_shares": self.holding_shares,
            "holding_ratio": self.holding_ratio,
            "change_shares": self.change_shares,
            "change_ratio": self.change_ratio,
            "net_inflow": float(self.net_inflow),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StockHoldingChange":
        return cls(
            symbol=data.get("symbol", ""),
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else date.today(),
            holding_shares=data.get("holding_shares", 0),
            holding_ratio=data.get("holding_ratio", 0.0),
            change_shares=data.get("change_shares", 0),
            change_ratio=data.get("change_ratio", 0.0),
            net_inflow=Decimal(str(data.get("net_inflow", 0))),
        )


@dataclass
class SectorNorthboundFlow:
    """板块北向资金流向

    记录北向资金在不同板块的分布情况。
    """

    sector: str  # 板块名称
    trade_date: date  # 交易日期
    net_inflow: Decimal = field(default_factory=lambda: Decimal("0"))  # 净流入
    stock_count: int = 0  # 流入股票数
    avg_change: float = 0.0  # 平均涨幅

    def to_dict(self) -> Dict:
        return {
            "sector": self.sector,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "net_inflow": float(self.net_inflow),
            "stock_count": self.stock_count,
            "avg_change": self.avg_change,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SectorNorthboundFlow":
        return cls(
            sector=data.get("sector", ""),
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else date.today(),
            net_inflow=Decimal(str(data.get("net_inflow", 0))),
            stock_count=data.get("stock_count", 0),
            avg_change=data.get("avg_change", 0.0),
        )


@dataclass
class NorthboundStock:
    """北向资金持股明细

    记录北向资金对单只股票的持股详情。
    """

    symbol: str  # 股票代码
    name: str  # 股票名称
    trade_date: date  # 交易日期
    holding_shares: int  # 持股数
    holding_ratio: float  # 持股比例
    share_change: int  # 持股变化
    share_change_ratio: float  # 持股变化比例

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "holding_shares": self.holding_shares,
            "holding_ratio": self.holding_ratio,
            "share_change": self.share_change,
            "share_change_ratio": self.share_change_ratio,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NorthboundStock":
        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else date.today(),
            holding_shares=data.get("holding_shares", 0),
            holding_ratio=data.get("holding_ratio", 0.0),
            share_change=data.get("share_change", 0),
            share_change_ratio=data.get("share_change_ratio", 0.0),
        )
