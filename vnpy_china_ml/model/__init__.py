"""
模型模块

提供A股机器学习模型和交易规则适配器。
"""

from .china_model import ChinaAlphaModel
from .adapters import T1RuleAdapter, PriceLimitAdapter, ChinaTradingAdapter
from .manager import ModelManager, ModelMetadata

__all__ = [
    "ChinaAlphaModel",
    "T1RuleAdapter",
    "PriceLimitAdapter",
    "ChinaTradingAdapter",
    "ModelManager",
    "ModelMetadata",
]
