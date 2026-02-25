"""
因子模块

提供各类因子的实现，包括技术因子、龙虎榜因子、北向资金因子、板块轮动因子等。
以及因子组合、权重分配、正交化等高级功能。
"""

from .base import BaseFactor
from .dragon_tiger import DragonTigerFactor
from .northbound import NorthboundFactor
from .sector_rotation import SectorRotationFactor
from .loader import FactorDataLoader, FactorCalculator, create_factor_calculator
from .combination import (
    FactorCombiner,
    FactorTimer,
    FactorCombinationConfig,
    FactorTimingConfig,
    FactorWeight,
    WeightMethod,
    OrthogonalMethod,
    create_factor_combiner,
)

__all__ = [
    "BaseFactor",
    "DragonTigerFactor",
    "NorthboundFactor",
    "SectorRotationFactor",
    "FactorDataLoader",
    "FactorCalculator",
    "create_factor_calculator",
    # 因子组合
    "FactorCombiner",
    "FactorTimer",
    "FactorCombinationConfig",
    "FactorTimingConfig",
    "FactorWeight",
    "WeightMethod",
    "OrthogonalMethod",
    "create_factor_combiner",
]
