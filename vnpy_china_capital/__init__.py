"""vnpy_china_capital - A股资金管理模块"""

# GUI应用
from .app import ChinaCapitalApp
from .gui_engine import ChinaCapitalGuiEngine

__version__ = "1.0.0"

__all__ = [
    "ChinaCapitalApp",
    "ChinaCapitalGuiEngine",
]
