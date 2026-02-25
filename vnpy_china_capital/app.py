"""A股资金管理应用模块"""
from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .gui_engine import ChinaCapitalGuiEngine


class ChinaCapitalApp(BaseApp):
    """A股资金管理应用"""
    app_name: str = "ChinaCapitalApp"
    app_module: str = "vnpy_china_capital"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股资金"
    engine_class: Type[ChinaCapitalGuiEngine] = ChinaCapitalGuiEngine
    widget_name: str = "ChinaCapitalWidget"
    icon_name: str = "capital.ico"


__all__ = ["ChinaCapitalApp"]
