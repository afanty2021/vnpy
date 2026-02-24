"""
可转债数据模型
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class ConvertibleBond:
    """可转债

    记录可转债的完整信息。
    """

    # 基本信息
    symbol: str  # 转债代码
    name: str  # 转债名称
    stock_symbol: str = ""  # 正股代码
    stock_name: str = ""  # 正股名称

    # 价格数据
    cb_price: float = 0.0  # 转债价格
    stock_price: float = 0.0  # 正股价格

    # 转股数据
    conversion_price: float = 0.0  # 转股价
    conversion_value: float = 0.0  # 转股价值
    conversion_ratio: float = 0.0  # 转股比例

    # 溢价率
    premium_rate: float = 0.0  # 转股溢价率
    pure_bond_value: float = 0.0  # 纯债价值
    yield_to_maturity: float = 0.0  # 到期收益率

    # 其他
    maturity_date: Optional[date] = None  # 到期日
    rating: str = ""  # 评级
    call_price: float = 0.0  # 强赎价
    volume: float = 0.0  # 成交量
    amount: float = 0.0  # 成交额

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "stock_symbol": self.stock_symbol,
            "stock_name": self.stock_name,
            "cb_price": self.cb_price,
            "stock_price": self.stock_price,
            "conversion_price": self.conversion_price,
            "conversion_value": self.conversion_value,
            "conversion_ratio": self.conversion_ratio,
            "premium_rate": self.premium_rate,
            "pure_bond_value": self.pure_bond_value,
            "yield_to_maturity": self.yield_to_maturity,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "rating": self.rating,
            "call_price": self.call_price,
            "volume": self.volume,
            "amount": self.amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConvertibleBond":
        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            stock_symbol=data.get("stock_symbol", ""),
            stock_name=data.get("stock_name", ""),
            cb_price=data.get("cb_price", 0.0),
            stock_price=data.get("stock_price", 0.0),
            conversion_price=data.get("conversion_price", 0.0),
            conversion_value=data.get("conversion_value", 0.0),
            conversion_ratio=data.get("conversion_ratio", 0.0),
            premium_rate=data.get("premium_rate", 0.0),
            pure_bond_value=data.get("pure_bond_value", 0.0),
            yield_to_maturity=data.get("yield_to_maturity", 0.0),
            maturity_date=date.fromisoformat(data["maturity_date"]) if data.get("maturity_date") else None,
            rating=data.get("rating", ""),
            call_price=data.get("call_price", 0.0),
            volume=data.get("volume", 0.0),
            amount=data.get("amount", 0.0),
        )


@dataclass
class ConvertibleArbitragePosition:
    """可转债套利持仓

    记录可转债套利的持仓信息。
    """

    cb_symbol: str  # 转债代码
    stock_symbol: str  # 正股代码
    cb_volume: int  # 转债持仓数量
    stock_volume: int  # 正股持仓数量（融券）
    entry_cb_price: float  # 转债买入价格
    entry_stock_price: float  # 正股卖出价格
    entry_datetime: date  # 建仓时间

    def to_dict(self) -> Dict:
        return {
            "cb_symbol": self.cb_symbol,
            "stock_symbol": self.stock_symbol,
            "cb_volume": self.cb_volume,
            "stock_volume": self.stock_volume,
            "entry_cb_price": self.entry_cb_price,
            "entry_stock_price": self.entry_stock_price,
            "entry_datetime": self.entry_datetime.isoformat() if self.entry_datetime else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConvertibleArbitragePosition":
        return cls(
            cb_symbol=data.get("cb_symbol", ""),
            stock_symbol=data.get("stock_symbol", ""),
            cb_volume=data.get("cb_volume", 0),
            stock_volume=data.get("stock_volume", 0),
            entry_cb_price=data.get("entry_cb_price", 0.0),
            entry_stock_price=data.get("entry_stock_price", 0.0),
            entry_datetime=date.fromisoformat(data["entry_datetime"]) if data.get("entry_datetime") else date.today(),
        )
