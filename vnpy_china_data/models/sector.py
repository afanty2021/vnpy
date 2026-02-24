"""
板块数据模型

定义板块相关的数据结构。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class SectorData:
    """板块数据"""

    sector_code: str
    sector_name: str
    trade_date: Optional[date] = None

    # 行情数据
    change_pct: float = 0.0  # 涨跌幅
    volume: float = 0.0  # 成交量
    turnover: float = 0.0  # 成交额
    pe_ratio: float = 0.0  # 市盈率

    # 成分股数据
    stock_count: int = 0  # 成分股数量
    up_count: int = 0  # 上涨数量
    down_count: int = 0  # 下跌数量

    def to_dict(self) -> dict:
        return {
            "sector_code": self.sector_code,
            "sector_name": self.sector_name,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "turnover": self.turnover,
            "pe_ratio": self.pe_ratio,
            "stock_count": self.stock_count,
            "up_count": self.up_count,
            "down_count": self.down_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SectorData":
        trade_date = data.get("trade_date")
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)

        return cls(
            sector_code=data.get("sector_code", ""),
            sector_name=data.get("sector_name", ""),
            trade_date=trade_date,
            change_pct=float(data.get("change_pct", 0)),
            volume=float(data.get("volume", 0)),
            turnover=float(data.get("turnover", 0)),
            pe_ratio=float(data.get("pe_ratio", 0)),
            stock_count=int(data.get("stock_count", 0)),
            up_count=int(data.get("up_count", 0)),
            down_count=int(data.get("down_count", 0)),
        )


@dataclass
class SectorStock:
    """板块成分股"""

    sector_code: str
    sector_name: str
    symbol: str
    stock_name: str
    weight: float = 0.0  # 权重
    change_pct: float = 0.0  # 涨跌幅

    def to_dict(self) -> dict:
        return {
            "sector_code": self.sector_code,
            "sector_name": self.sector_name,
            "symbol": self.symbol,
            "stock_name": self.stock_name,
            "weight": self.weight,
            "change_pct": self.change_pct,
        }


@dataclass
class SectorListData:
    """板块列表数据"""

    sectors: List[SectorData] = field(default_factory=list)
    update_time: Optional[date] = None

    def to_dict(self) -> dict:
        return {
            "sectors": [s.to_dict() for s in self.sectors],
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }


@dataclass
class IndustryClassification:
    """行业分类"""

    industry_code: str
    industry_name: str
    parent_code: Optional[str] = None
    level: int = 1  # 层级
    stock_count: int = 0

    def to_dict(self) -> dict:
        return {
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "parent_code": self.parent_code,
            "level": self.level,
            "stock_count": self.stock_count,
        }


@dataclass
class ConceptData:
    """概念板块数据"""

    concept_code: str
    concept_name: str
    trade_date: Optional[date] = None
    change_pct: float = 0.0
    volume: float = 0.0
    turnover: float = 0.0
    stock_count: int = 0
    related_stocks: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "concept_code": self.concept_code,
            "concept_name": self.concept_name,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "turnover": self.turnover,
            "stock_count": self.stock_count,
            "related_stocks": self.related_stocks,
        }
