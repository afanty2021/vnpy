"""
资金曲线管理模块

提供资金曲线管理、回撤控制和复利增长计算功能。
"""

from .curve import EquityCurveManager
from .drawdown import DrawdownController
from .compound import CompoundGrowthCalculator

__all__ = [
    "EquityCurveManager",
    "DrawdownController",
    "CompoundGrowthCalculator",
]
