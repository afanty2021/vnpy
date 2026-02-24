"""
北向资金数据模型

定义北向资金（沪股通/深股通）相关的数据结构。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


@dataclass
class NorthboundFlowData:
    """北向资金流向数据"""

    trade_date: date

    # 沪股通数据
    sh_net_inflow: float = 0.0  # 沪股通净流入
    sh_buy_volume: float = 0.0  # 沪股通买入金额
    sh_sell_volume: float = 0.0  # 沪股通卖出金额

    # 深股通数据
    sz_net_inflow: float = 0.0  # 深股通净流入
    sz_buy_volume: float = 0.0  # 深股通买入金额
    sz_sell_volume: float = 0.0  # 深股通卖出金额

    # 合计数据
    total_net_inflow: float = 0.0  # 北向资金净流入合计

    # 个股持股变化
    holding_changes: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """计算合计数据"""
        self.total_net_inflow = self.sh_net_inflow + self.sz_net_inflow

    @property
    def is_inflow(self) -> bool:
        """是否净流入"""
        return self.total_net_inflow > 0

    @property
    def inflow_strength(self) -> str:
        """流入强度"""
        if self.total_net_inflow > 50:
            return "大幅流入"
        elif self.total_net_inflow > 20:
            return "中幅流入"
        elif self.total_net_inflow > 5:
            return "小幅流入"
        elif self.total_net_inflow > -5:
            return "基本持平"
        elif self.total_net_inflow > -20:
            return "小幅流出"
        elif self.total_net_inflow > -50:
            return "中幅流出"
        else:
            return "大幅流出"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "sh_net_inflow": self.sh_net_inflow,
            "sh_buy_volume": self.sh_buy_volume,
            "sh_sell_volume": self.sh_sell_volume,
            "sz_net_inflow": self.sz_net_inflow,
            "sz_buy_volume": self.sz_buy_volume,
            "sz_sell_volume": self.sz_sell_volume,
            "total_net_inflow": self.total_net_inflow,
            "holding_changes": self.holding_changes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NorthboundFlowData":
        """从字典创建"""
        trade_date = data.get("trade_date")
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)

        return cls(
            trade_date=trade_date,
            sh_net_inflow=float(data.get("sh_net_inflow", 0)),
            sh_buy_volume=float(data.get("sh_buy_volume", 0)),
            sh_sell_volume=float(data.get("sh_sell_volume", 0)),
            sz_net_inflow=float(data.get("sz_net_inflow", 0)),
            sz_buy_volume=float(data.get("sz_buy_volume", 0)),
            sz_sell_volume=float(data.get("sz_sell_volume", 0)),
            holding_changes=data.get("holding_changes", {}),
        )


@dataclass
class StockHoldingData:
    """个股持股数据"""

    symbol: str
    trade_date: date
    shares: float = 0.0  # 持股数量（股）
    shares_ratio: float = 0.0  # 持股比例（%）
    holdings: float = 0.0  # 持股市值（万元）
    change_shares: float = 0.0  # 持股数量变化
    change_ratio: float = 0.0  # 持股比例变化
    change_holdings: float = 0.0  # 持股市值变化

    @property
    def is_increase(self) -> bool:
        """是否增持"""
        return self.change_shares > 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "shares": self.shares,
            "shares_ratio": self.shares_ratio,
            "holdings": self.holdings,
            "change_shares": self.change_shares,
            "change_ratio": self.change_ratio,
            "change_holdings": self.change_holdings,
        }


@dataclass
class TopHolderData:
    """北向资金持股前十大数据"""

    symbol: str
    trade_date: date
    holders: List[StockHoldingData] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "holders": [h.to_dict() for h in self.holders],
        }
