"""
模型模块

提供A股机器学习模型和交易规则适配器。
"""

from .china_model import ChinaAlphaModel
from .adapters import T1RuleAdapter, PriceLimitAdapter, ChinaTradingAdapter
from .manager import ModelManager, ModelMetadata
from .version_manager import ModelVersionManager
from .ab_tester import ModelABTester
from .ab_test import ABTestConfig, ABTestResult, ModelVersionInfo

__all__ = [
    "ChinaAlphaModel",
    "T1RuleAdapter",
    "PriceLimitAdapter",
    "ChinaTradingAdapter",
    "ModelManager",
    "ModelMetadata",
    "ModelVersionManager",
    "ModelABTester",
    "ABTestConfig",
    "ABTestResult",
    "ModelVersionInfo",
]
