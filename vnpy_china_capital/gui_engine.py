"""A股资金管理GUI引擎"""
from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine


class ChinaCapitalGuiEngine(BaseEngine):
    """A股资金管理GUI引擎"""

    engine_name: str = "ChinaCapitalApp"

    def __init__(self, main_engine, event_engine):
        super().__init__(main_engine, event_engine, self.engine_name)

    def init(self):
        self.main_engine.write_log("A股资金管理引擎初始化完成")


__all__ = ["ChinaCapitalGuiEngine"]
