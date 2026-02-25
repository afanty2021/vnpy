"""
机器学习模块配置

定义特征配置、模型配置、训练配置和评估配置。
"""

from typing import List

from pydantic import Field, field_validator

from vnpy_china_config.base import BaseConfig


class MLModuleConfig(BaseConfig):
    """机器学习模块配置

    统一管理机器学习相关配置。

    Attributes:
        # 特征配置
        feature_types: 特征类型列表

        # 模型配置
        default_model_type: 默认模型类型（lightgbm/xgboost/random_forest/lstm）
        train_test_split: 训练集/测试集划分比例

        # 训练配置
        retrain_interval: 重训练间隔（天）
        min_train_samples: 最小训练样本数

        # IC/IR分析
        ic_threshold: IC 阈值
        ir_threshold: IR 阈值
    """

    # 特征配置
    feature_types: List[str] = Field(default_factory=lambda: ["technical", "fundamental", "market"])

    # 模型配置
    default_model_type: str = "lightgbm"
    train_test_split: float = 0.8

    # 训练配置
    retrain_interval: int = 7
    min_train_samples: int = 1000

    # IC/IR分析
    ic_threshold: float = 0.05
    ir_threshold: float = 0.5

    @field_validator("default_model_type")
    @classmethod
    def validate_model_type(cls, v: str) -> str:
        """验证模型类型"""
        valid_types = ["lightgbm", "xgboost", "random_forest", "lasso", "ridge", "lstm"]
        if v not in valid_types:
            raise ValueError(f"无效的 default_model_type: {v}，必须是 {valid_types} 之一")
        return v

    @field_validator("train_test_split")
    @classmethod
    def validate_split_ratio(cls, v: float) -> float:
        """验证划分比例"""
        if v <= 0 or v >= 1:
            raise ValueError(f"train_test_split 必须在 0-1 之间，当前值: {v}")
        return v

    @field_validator("retrain_interval")
    @classmethod
    def validate_retrain_interval(cls, v: int) -> int:
        """验证重训练间隔"""
        if v <= 0:
            raise ValueError(f"retrain_interval 必须大于 0，当前值: {v}")
        return v

    @field_validator("min_train_samples")
    @classmethod
    def validate_min_samples(cls, v: int) -> int:
        """验证最小样本数"""
        if v <= 0:
            raise ValueError(f"min_train_samples 必须大于 0，当前值: {v}")
        return v

    @field_validator("ic_threshold", "ir_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """验证阈值"""
        if v < 0:
            raise ValueError(f"阈值不能为负数，当前值: {v}")
        return v
