"""基础层：优化器基类和结果数据类"""

from .result import (
    OptimizationStatus,
    OptimizationMetrics,
    OptimizationResult,
    OptimizationSummary,
)
from .optimizer import BaseOptimizer

__all__ = [
    "OptimizationStatus",
    "OptimizationMetrics",
    "OptimizationResult",
    "OptimizationSummary",
    "BaseOptimizer",
]
