"""A股回测GUI引擎"""
from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine


class ChinaBacktestGuiEngine(BaseEngine):
    """A股回测GUI引擎"""

    engine_name: str = "ChinaBacktestApp"

    def __init__(self, main_engine, event_engine):
        super().__init__(main_engine, event_engine, self.engine_name)

    def init(self):
        self.write_log("A股回测引擎初始化完成")


__all__ = ["ChinaBacktestGuiEngine"]
