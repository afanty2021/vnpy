"""
vnpy_china_data - A股数据服务模块

提供A股交易系统的统一数据服务，包括：
- K线数据获取
- Tick数据获取
- 股票信息查询
- 龙虎榜数据
- 北向资金数据
- 板块数据
"""

from .service import ChinaDataService, get_data_service
from .cache import DataQueryCache
from .database import MySQLDatabaseLayer
from .adapter import TushareDataAdapter, QMTDataAdapter
from .models import (
    StockInfo,
    DragonTigerData,
    NorthboundFlowData,
    SectorData,
)

__version__ = "1.0.0"

__all__ = [
    "ChinaDataService",
    "get_data_service",
    "DataQueryCache",
    "MySQLDatabaseLayer",
    "TushareDataAdapter",
    "QMTDataAdapter",
    "StockInfo",
    "DragonTigerData",
    "NorthboundFlowData",
    "SectorData",
]
