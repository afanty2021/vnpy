"""
报表数据源模块

提供权益快照与行业映射的持久化存储和采集，作为报表生成（权益变化法盈亏、
行业分析）的数据源。

复用 vnpy_china_config.GlobalConfig 的 MySQL 配置与 pymysql + DBUtils 连接池
（与 vnpy_china_data 一致）。
"""

from .db import DataSourceDB
from .schema import init_schema, EQUITY_SNAPSHOT_DDL, STOCK_INDUSTRY_DDL
from .equity_store import EquitySnapshotStore
from .equity_collector import EquitySnapshotCollector
from .industry_store import IndustryStore
from .industry_collector import IndustryCollector
from .scheduler import DailyScheduler
from .service import ReportingDataService

__all__ = [
    "DataSourceDB",
    "init_schema",
    "EQUITY_SNAPSHOT_DDL",
    "STOCK_INDUSTRY_DDL",
    "EquitySnapshotStore",
    "EquitySnapshotCollector",
    "IndustryStore",
    "IndustryCollector",
    "DailyScheduler",
    "ReportingDataService",
]
