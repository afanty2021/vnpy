"""A股回测应用模块"""
from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .gui_engine import ChinaBacktestGuiEngine


class ChinaBacktestApp(BaseApp):
    """A股回测应用"""
    app_name: str = "ChinaBacktestApp"
    app_module: str = "vnpy_china_backtest"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股回测"
    engine_class: Type[ChinaBacktestGuiEngine] = ChinaBacktestGuiEngine
    widget_name: str = "ChinaBacktestWidget"
    icon_name: str = "backtest.ico"


__all__ = ["ChinaBacktestApp"]
