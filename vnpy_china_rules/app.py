"""
A股交易规则应用模块
提供VeighNa GUI集成
"""

from pathlib import Path
from typing import Type
from vnpy.trader.app import BaseApp
from .gui_engine import ChinaRulesGuiEngine


class ChinaRulesApp(BaseApp):
    """A股交易规则应用"""

    app_name: str = "ChinaRulesApp"
    app_module: str = "vnpy_china_rules"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股规则"
    engine_class: Type[ChinaRulesGuiEngine] = ChinaRulesGuiEngine
    widget_name: str = "ChinaRulesWidget"
    icon_name: str = "rules.ico"


__all__ = ["ChinaRulesApp"]
