"""
评估工具模块

本模块提供机器学习策略的评估功能：
- ic_ir: IC/IR分析器，用于评估因子预测能力
- metrics: A股评估指标，计算Alpha、Beta等绩效指标
- validator: 模型验证器，提供交叉验证、回测等功能
"""

from .ic_ir import ICAnalyzer
from .metrics import ChinaMetrics
from .validator import ModelValidator

__all__ = [
    "ICAnalyzer",
    "ChinaMetrics",
    "ModelValidator",
]
