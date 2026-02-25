"""
A股分析应用模块
提供VeighNa GUI集成
"""

from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .engine import ChinaAnalysisEngine


class ChinaAnalysisApp(BaseApp):
    """A股分析应用"""

    app_name: str = "ChinaAnalysisApp"
    app_module: str = "vnpy_china_analysis"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股分析"
    engine_class: Type[ChinaAnalysisEngine] = ChinaAnalysisEngine
    widget_name: str = "ChinaAnalysisWidget"
    icon_name: str = "analysis.ico"


__all__ = ["ChinaAnalysisApp"]
