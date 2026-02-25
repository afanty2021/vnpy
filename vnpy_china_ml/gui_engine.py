"""A股机器学习GUI引擎"""
from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine


class ChinaMlGuiEngine(BaseEngine):
    """A股机器学习GUI引擎"""

    engine_name: str = "ChinaMlApp"

    def __init__(self, main_engine, event_engine):
        super().__init__(main_engine, event_engine, self.engine_name)

    def init(self):
        self.write_log("A股机器学习引擎初始化完成")


__all__ = ["ChinaMlGuiEngine"]
