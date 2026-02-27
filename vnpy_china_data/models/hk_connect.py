"""
港股通股票名单数据模型
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class HkConnectStock:
    """港股通股票信息

    表示被纳入港股通范围的香港本地股票。
    注意：虽然通过沪港通/深港通交易，但股票本身在香港联合交易所上市，
    历史数据下载时应使用 Exchange.SEHK（香港本地）后缀。
    """

    # 股票基本信息
    symbol: str                    # 股票代码（不含交易所后缀，如 "00700"）
    name: str                      # 股票名称（如 "腾讯控股"）

    # 交易通道信息
    channel: str                   # 交易通道：SHHK（沪港通）或 SZHK（深港通）
    channel_type: str              # 通道类型：SH（沪市）或 SZ（深市）

    # 分类信息
    category: Optional[str] = None # 分类：港股通/深港股通
    industry: Optional[str] = None # 行业分类

    # 状态信息
    status: str = "active"         # 状态：active（纳入）或 suspended（暂停）
    list_date: Optional[date] = None  # 纳入港股通日期

    # 数据来源
    source: str = "sse"            # 数据来源：sse（上交所）或 szse（深交所）

    @property
    def vnpy_symbol(self) -> str:
        """VeighNa 格式代码（用于显示和查询）

        例如：00700.SHHK, 01810.SZHK

        注意：历史数据下载时需要转换为 00700.SEHK
        """
        return f"{self.symbol}.{self.channel}"

    @property
    def qmt_symbol(self) -> str:
        """QMT 格式代码（用于历史数据下载）

        统一使用香港本地交易所后缀，因为港股通股票
        本身就是在香港联合交易所上市的。

        例如：00700.HK
        """
        return f"{self.symbol}.HK"

    @classmethod
    def from_dict(cls, data: dict) -> "HkConnectStock":
        """从字典创建实例"""
        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            channel=data.get("channel", ""),
            channel_type=data.get("channel_type", ""),
            category=data.get("category"),
            industry=data.get("industry"),
            status=data.get("status", "active"),
            list_date=data.get("list_date"),
            source=data.get("source", "sse"),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "channel": self.channel,
            "channel_type": self.channel_type,
            "category": self.category,
            "industry": self.industry,
            "status": self.status,
            "list_date": self.list_date.isoformat() if self.list_date else None,
            "source": self.source,
        }
