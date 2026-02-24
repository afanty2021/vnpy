"""
VeighNa A股交易规则适配模块

提供A股T+1、涨跌停等特有交易规则的适配功能。
"""

from vnpy_china_rules.datasource import (
    StockInfo,
    DataSource,
    QMTDataSource,
    TushareDataSource,
    DataSourceManager,
)


__all__ = [
    # 数据源
    "StockInfo",
    "DataSource",
    "QMTDataSource",
    "TushareDataSource",
    "DataSourceManager",
]


__version__ = "0.1.0"
__author__ = "VeighNa Team"
