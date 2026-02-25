"""vnpy_china_capital - A股资金管理模块"""

# GUI应用
from .app import ChinaCapitalApp
from .gui_engine import ChinaCapitalGuiEngine

# 数据对象
from .objects import CapitalFlowData

# 数据库操作
from .database import CapitalFlowDatabase

# 历史数据导入
from .importer import QMTHistoryImporter

__version__ = "1.0.0"

__all__ = [
    "ChinaCapitalApp",
    "ChinaCapitalGuiEngine",
    "CapitalFlowData",
    "CapitalFlowDatabase",
    "QMTHistoryImporter",
]
