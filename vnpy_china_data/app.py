"""
A股数据服务应用模块
提供VeighNa GUI集成
"""

from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .gui_engine import ChinaDataGuiEngine


class ChinaDataApp(BaseApp):
    """A股数据服务应用"""

    app_name: str = "ChinaDataApp"
    app_module: str = "vnpy_china_data"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股数据"
    engine_class: Type[ChinaDataGuiEngine] = ChinaDataGuiEngine
    widget_name: str = "ChinaDataWidget"
    icon_name: str = "database.ico"


__all__ = ["ChinaDataApp"]
