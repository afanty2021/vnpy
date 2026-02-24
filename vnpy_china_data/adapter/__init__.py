"""
数据适配器模块

提供不同数据源的适配器实现。
"""

from .base import BaseDataAdapter
from .tushare_adapter import TushareDataAdapter
from .qmt_adapter import QMTDataAdapter

__all__ = [
    "BaseDataAdapter",
    "TushareDataAdapter",
    "QMTDataAdapter",
]
