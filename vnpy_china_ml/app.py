"""A股机器学习应用模块"""
from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .gui_engine import ChinaMlGuiEngine


class ChinaMlApp(BaseApp):
    """A股机器学习应用"""
    app_name: str = "ChinaMlApp"
    app_module: str = "vnpy_china_ml"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股机器学习"
    engine_class: Type[ChinaMlGuiEngine] = ChinaMlGuiEngine
    widget_name: str = "ChinaMlWidget"
    icon_name: str = "ml.ico"


__all__ = ["ChinaMlApp"]
