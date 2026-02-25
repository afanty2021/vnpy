"""
A股策略应用模块
提供VeighNa GUI集成
"""

from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .engine import ChinaStrategyEngine


class ChinaStrategyApp(BaseApp):
    """A股策略应用"""

    app_name: str = "ChinaStrategyApp"
    app_module: str = "vnpy_china_strategy"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股策略"
    engine_class: Type[ChinaStrategyEngine] = ChinaStrategyEngine
    widget_name: str = "ChinaStrategyWidget"
    icon_name: str = "strategy.ico"


__all__ = ["ChinaStrategyApp"]
