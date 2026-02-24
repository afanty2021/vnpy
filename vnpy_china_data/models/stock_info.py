"""
股票信息数据模型

定义股票基本信息的数据结构。
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from vnpy.trader.constant import Exchange


@dataclass
class StockInfo:
    """股票基本信息"""

    symbol: str
    name: str
    exchange: Exchange
    industry: str = ""
    area: str = ""
    market: str = ""  # 主板/创业板/科创板
    list_date: Optional[date] = None
    is_st: bool = False
    is_hs: bool = False  # 是否沪深港通标的
    total_shares: float = 0.0  # 总股本
    float_shares: float = 0.0  # 流通股本

    def is_main_board(self) -> bool:
        """是否主板"""
        return self.market in ["主板", "Main Board"]

    def is_gem(self) -> bool:
        """是否创业板"""
        return self.market in ["创业板", "GEM"]

    def is_star(self) -> bool:
        """是否科创板"""
        return self.market in ["科创板", "STAR"]

    def is_beijing(self) -> bool:
        """是否北交所"""
        return self.exchange == Exchange.BSE

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange.value,
            "industry": self.industry,
            "area": self.area,
            "market": self.market,
            "list_date": self.list_date.isoformat() if self.list_date else None,
            "is_st": self.is_st,
            "is_hs": self.is_hs,
            "total_shares": self.total_shares,
            "float_shares": self.float_shares,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StockInfo":
        """从字典创建"""
        exchange_str = data.get("exchange", "SZSE")
        exchange = Exchange(exchange_str) if exchange_str else Exchange.SZSE

        list_date_str = data.get("list_date")
        list_date = None
        if list_date_str:
            if isinstance(list_date_str, str):
                list_date = date.fromisoformat(list_date_str)
            elif isinstance(list_date_str, date):
                list_date = list_date_str

        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            exchange=exchange,
            industry=data.get("industry", ""),
            area=data.get("area", ""),
            market=data.get("market", ""),
            list_date=list_date,
            is_st=data.get("is_st", False),
            is_hs=data.get("is_hs", False),
            total_shares=float(data.get("total_shares", 0)),
            float_shares=float(data.get("float_shares", 0)),
        )
