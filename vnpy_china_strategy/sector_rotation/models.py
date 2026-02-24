"""
板块轮动数据模型
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class SectorData:
    """板块数据

    记录单个板块的日线行情数据。
    """

    sector: str  # 板块名称
    trade_date: date  # 交易日期
    close_index: float = 0.0  # 收盘点位
    change_pct: float = 0.0  # 涨跌幅
    turnover_rate: float = 0.0  # 换手率
    pe: float = 0.0  # 市盈率
    volume: Decimal = field(default_factory=lambda: Decimal("0"))  # 成交量
    amount: Decimal = field(default_factory=lambda: Decimal("0"))  # 成交额

    def to_dict(self) -> Dict:
        return {
            "sector": self.sector,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "close_index": self.close_index,
            "change_pct": self.change_pct,
            "turnover_rate": self.turnover_rate,
            "pe": self.pe,
            "volume": float(self.volume),
            "amount": float(self.amount),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SectorData":
        return cls(
            sector=data.get("sector", ""),
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else date.today(),
            close_index=data.get("close_index", 0.0),
            change_pct=data.get("change_pct", 0.0),
            turnover_rate=data.get("turnover_rate", 0.0),
            pe=data.get("pe", 0.0),
            volume=Decimal(str(data.get("volume", 0))),
            amount=Decimal(str(data.get("amount", 0))),
        )


@dataclass
class SectorStrength:
    """板块强度

    计算板块相对大盘的强度指标。
    """

    sector: str  # 板块名称
    strength: float = 0.0  # 强度值 (相对大盘)
    momentum_5d: float = 0.0  # 5日动量
    momentum_20d: float = 0.0  # 20日动量
    momentum_60d: float = 0.0  # 60日动量
    fund_flow: Decimal = field(default_factory=lambda: Decimal("0"))  # 资金净流入
    rank: int = 0  # 强度排名

    def to_dict(self) -> Dict:
        return {
            "sector": self.sector,
            "strength": self.strength,
            "momentum_5d": self.momentum_5d,
            "momentum_20d": self.momentum_20d,
            "momentum_60d": self.momentum_60d,
            "fund_flow": float(self.fund_flow),
            "rank": self.rank,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SectorStrength":
        return cls(
            sector=data.get("sector", ""),
            strength=data.get("strength", 0.0),
            momentum_5d=data.get("momentum_5d", 0.0),
            momentum_20d=data.get("momentum_20d", 0.0),
            momentum_60d=data.get("momentum_60d", 0.0),
            fund_flow=Decimal(str(data.get("fund_flow", 0))),
            rank=data.get("rank", 0),
        )


@dataclass
class RotationSignal:
    """轮动信号

    记录板块轮动的信号信息。
    """

    from_sector: str  # 轮出板块
    to_sector: str  # 轮入板块
    signal_date: date  # 信号日期
    confidence: float = 0.0  # 置信度
    reason: str = ""  # 轮动原因

    def to_dict(self) -> Dict:
        return {
            "from_sector": self.from_sector,
            "to_sector": self.to_sector,
            "signal_date": self.signal_date.isoformat() if self.signal_date else None,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RotationSignal":
        return cls(
            from_sector=data.get("from_sector", ""),
            to_sector=data.get("to_sector", ""),
            signal_date=date.fromisoformat(data["signal_date"]) if data.get("signal_date") else date.today(),
            confidence=data.get("confidence", 0.0),
            reason=data.get("reason", ""),
        )


@dataclass
class SectorIndex:
    """板块指数

    板块的指数数据。
    """

    sector_code: str  # 板块代码
    sector_name: str  # 板块名称
    trade_date: date  # 交易日期
    close: float = 0.0  # 收盘价
    change_pct: float = 0.0  # 涨跌幅
    volume: float = 0.0  # 成交量
    amount: float = 0.0  # 成交额

    def to_dict(self) -> Dict:
        return {
            "sector_code": self.sector_code,
            "sector_name": self.sector_name,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "close": self.close,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
        }
