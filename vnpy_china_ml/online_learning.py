"""在线学习模块

支持模型的增量更新和在线学习，使模型能够适应市场变化。
"""

import numpy as np
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from collections import deque

from .model.manager import ModelManager
from .model.china_model import ChinaAlphaModel
from .utils.types import ModelType


@dataclass
class OnlineLearningConfig:
    """在线学习配置

    Attributes:
        min_samples: 最小样本数要求
        max_samples: 最大样本数（滑动窗口）
        update_interval: 更新间隔（样本数）
        learning_rate: 学习率（用于增量更新）
        decay_factor: 旧数据衰减因子
        enable_auto_retrain: 是否自动重新训练
        performance_threshold: 性能阈值，低于此值触发重训练
    """
    min_samples: int = 100
    max_samples: int = 10000
    update_interval: int = 100
    learning_rate: float = 0.01
    decay_factor: float = 0.95
    enable_auto_retrain: bool = True
    performance_threshold: float = 0.50


@dataclass
class TrainingSample:
    """训练样本

    Attributes:
        features: 特征向量
        label: 标签值
        weight: 样本权重
        timestamp: 样本时间戳
        symbol: 股票代码
    """
    features: np.ndarray
    label: float
    weight: float = 1.0
    timestamp: Optional[datetime] = None
    symbol: Optional[str] = None


class OnlineLearner:
    """在线学习器

    支持机器学习模型的增量更新和在线学习。

    Features:
    - 增量更新模型参数
    - 滑动窗口管理
    - 样本权重衰减
    - 自动触发重新训练
    - 性能监控触发更新
    """

    def __init__(
        self,
        model: ChinaAlphaModel,
        config: Optional[OnlineLearningConfig] = None
    ):
        """初始化在线学习器

        Args:
            model: 机器学习模型
            config: 在线学习配置
        """
        self.model = model
        self.config = config or OnlineLearningConfig()

        # 训练样本缓冲区
        self._sample_buffer: deque = deque(maxlen=self.config.max_samples)

        # 更新计数器
        self._update_count = 0

        # 性能跟踪
        self._recent_predictions: deque = deque(maxlen=100)
        self._recent_actuals: deque = deque(maxlen=100)

        # 最后更新时间
        self._last_update_time: Optional[datetime] = None

    def add_sample(
        self,
        features: np.ndarray,
        label: float,
        weight: float = 1.0,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None
    ) -> None:
        """添加训练样本

        Args:
            features: 特征向量
            label: 标签值
            weight: 样本权重
            timestamp: 时间戳
            symbol: 股票代码
        """
        sample = TrainingSample(
            features=features,
            label=label,
            weight=weight,
            timestamp=timestamp or datetime.now(),
            symbol=symbol
        )

        self._sample_buffer.append(sample)

    def add_samples(self, samples: List[TrainingSample]) -> None:
        """批量添加训练样本

        Args:
            samples: 训练样本列表
        """
        for sample in samples:
            self._sample_buffer.append(sample)

    def should_update(self) -> bool:
        """判断是否应该更新模型

        Returns:
            是否应该更新
        """
        if len(self._sample_buffer) < self.config.min_samples:
            return False

        self._update_count += 1

        # 检查更新间隔
        if self._update_count >= self.config.update_interval:
            self._update_count = 0
            return True

        # 检查性能衰减
        if self.config.enable_auto_retrain:
            current_performance = self._calculate_recent_performance()
            if current_performance < self.config.performance_threshold:
                return True

        return False

    def update_model(self) -> Dict[str, float]:
        """更新模型

        执行增量更新或重新训练。

        Returns:
            更新结果字典
        """
        if len(self._sample_buffer) < self.config.min_samples:
            return {
                "status": "skipped",
                "reason": "insufficient_samples",
                "sample_count": len(self._sample_buffer)
            }

        # 准备训练数据
        samples = list(self._sample_buffer)
        X = np.array([s.features for s in samples])
        y = np.array([s.label for s in samples])
        weights = np.array([s.weight for s in samples])

        # 应用时间衰减
        if self.config.decay_factor < 1.0:
            weights = self._apply_time_decay(weights, samples)

        try:
            # 尝试增量更新（部分模型支持）
            if self._supports_incremental_update():
                result = self._incremental_update(X, y, weights)
            else:
                # 完全重新训练
                result = self._full_retrain(X, y, weights)

            self._last_update_time = datetime.now()
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _supports_incremental_update(self) -> bool:
        """检查模型是否支持增量更新

        Returns:
            是否支持
        """
        # 随机森林等树模型可以通过warm_start支持增量更新
        # sklearn的某些模型支持partial_fit
        model_type = self.model.model_type

        # 简化处理：大多数情况做完全重新训练
        return False

    def _incremental_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """增量更新模型

        Args:
            X: 特征矩阵
            y: 目标变量
            sample_weight: 样本权重

        Returns:
            更新结果
        """
        # 对于支持warm_start的模型
        if hasattr(self.model.model, 'warm_start'):
            self.model.model.warm_start = True

        # 使用较小的学习率进行增量更新
        if sample_weight is not None:
            # 衰减旧样本的影响
            sample_weight = sample_weight * self.config.learning_rate

        self.model.model.fit(X, y, sample_weight=sample_weight)

        return {
            "status": "success",
            "method": "incremental",
            "samples_used": len(X),
            "learning_rate": self.config.learning_rate
        }

    def _full_retrain(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """完全重新训练模型

        Args:
            X: 特征矩阵
            y: 目标变量
            sample_weight: 样本权重

        Returns:
            更新结果
        """
        # 重新训练
        result = self.model.train(
            X, y,
            sample_weight=sample_weight,
            feature_names=self.model.feature_names
        )

        return {
            "status": "success",
            "method": "full_retrain",
            "samples_used": len(X),
            **result
        }

    def _apply_time_decay(
        self,
        weights: np.ndarray,
        samples: List[TrainingSample]
    ) -> np.ndarray:
        """应用时间衰减权重

        越新的样本权重越高。

        Args:
            weights: 原始权重
            samples: 样本列表

        Returns:
            衰减后的权重
        """
        if not samples:
            return weights

        n = len(samples)
        # 每个样本在时间序中的排名（0=最早），保持与 weights/samples 原序对齐，
        # 避免排序后 decay_factors 与 weights（原序）错位相乘
        times = [s.timestamp or datetime.min for s in samples]
        order = sorted(range(n), key=lambda i: times[i])  # 时间从早到晚的样本下标
        rank = [0] * n
        for position, idx in enumerate(order):
            rank[idx] = position

        # 越新（rank 越大）衰减因子越接近 1（decay_factor^(n-1-rank)）
        decay_factors = np.array([
            self.config.decay_factor ** (n - 1 - rank[i]) for i in range(n)
        ])

        return np.asarray(weights) * decay_factors

    def _calculate_recent_performance(self) -> float:
        """计算最近的预测性能

        Returns:
            性能指标（方向准确率）
        """
        if len(self._recent_predictions) == 0 or len(self._recent_actuals) == 0:
            return 0.0

        # 计算方向准确率
        pred_directions = np.sign(self._recent_predictions)
        actual_directions = np.sign(self._recent_actuals)

        accuracy = (pred_directions == actual_directions).mean()
        return float(accuracy)

    def record_prediction(
        self,
        predicted_return: float,
        actual_return: float
    ) -> None:
        """记录预测结果

        Args:
            predicted_return: 预测收益率
            actual_return: 实际收益率
        """
        self._recent_predictions.append(predicted_return)
        self._recent_actuals.append(actual_return)

    def get_buffer_info(self) -> Dict[str, int]:
        """获取缓冲区信息

        Returns:
            缓冲区信息字典
        """
        return {
            "current_size": len(self._sample_buffer),
            "max_size": self.config.max_samples,
            "min_size": self.config.min_samples,
            "update_count": self._update_count
        }

    def clear_buffer(self) -> None:
        """清空样本缓冲区"""
        self._sample_buffer.clear()
        self._update_count = 0


class OnlineLearningManager:
    """在线学习管理器

    管理多个模型的在线学习过程。

    Features:
    - 管理多个在线学习器
    - 自动调度更新
    - 持久化学习配置
    - 批量更新接口
    """

    def __init__(
        self,
        model_manager: ModelManager,
        config: Optional[OnlineLearningConfig] = None
    ):
        """初始化在线学习管理器

        Args:
            model_manager: 模型管理器
            config: 默认在线学习配置
        """
        self.model_manager = model_manager
        self.default_config = config or OnlineLearningConfig()

        # 在线学习器字典 {model_id: OnlineLearner}
        self._learners: Dict[str, OnlineLearner] = {}

        # 模型特定配置
        self._configs: Dict[str, OnlineLearningConfig] = {}

    def register_model(
        self,
        model_id: str,
        config: Optional[OnlineLearningConfig] = None
    ) -> bool:
        """注册模型用于在线学习

        Args:
            model_id: 模型ID
            config: 在线学习配置

        Returns:
            是否注册成功
        """
        model = self.model_manager.load_model(model_id)
        if model is None:
            return False

        config = config or self.default_config

        self._learners[model_id] = OnlineLearner(model, config)
        self._configs[model_id] = config

        return True

    def unregister_model(self, model_id: str) -> None:
        """注销模型

        Args:
            model_id: 模型ID
        """
        self._learners.pop(model_id, None)
        self._configs.pop(model_id, None)

    def add_sample(
        self,
        model_id: str,
        features: np.ndarray,
        label: float,
        **kwargs
    ) -> None:
        """为指定模型添加训练样本

        Args:
            model_id: 模型ID
            features: 特征向量
            label: 标签值
            **kwargs: 其他样本参数
        """
        if model_id not in self._learners:
            return

        self._learners[model_id].add_sample(features, label, **kwargs)

    def add_samples_batch(
        self,
        model_id: str,
        X: np.ndarray,
        y: np.ndarray,
        **kwargs
    ) -> None:
        """批量添加训练样本

        Args:
            model_id: 模型ID
            X: 特征矩阵
            y: 目标变量
            **kwargs: 其他样本参数
        """
        if model_id not in self._learners:
            return

        samples = []
        for i in range(len(X)):
            sample = TrainingSample(
                features=X[i],
                label=y[i],
                **kwargs
            )
            samples.append(sample)

        self._learners[model_id].add_samples(samples)

    def check_and_update(
        self,
        model_id: Optional[str] = None
    ) -> Dict[str, Dict]:
        """检查并更新模型

        Args:
            model_id: 模型ID，None表示检查所有模型

        Returns:
            更新结果字典 {model_id: result}
        """
        results = {}

        model_ids = [model_id] if model_id else list(self._learners.keys())

        for mid in model_ids:
            if mid not in self._learners:
                continue

            learner = self._learners[mid]

            if learner.should_update():
                # 更新模型
                update_result = learner.update_model()

                # 保存更新后的模型
                if update_result.get("status") == "success":
                    self.model_manager.register_model(
                        model_name=f"{mid}_updated",
                        model=learner.model,
                        description="在线学习更新"
                    )

                results[mid] = update_result

        return results

    def record_prediction_result(
        self,
        model_id: str,
        predicted_return: float,
        actual_return: float
    ) -> None:
        """记录预测结果

        Args:
            model_id: 模型ID
            predicted_return: 预测收益率
            actual_return: 实际收益率
        """
        if model_id in self._learners:
            self._learners[model_id].record_prediction(
                predicted_return, actual_return
            )

    def get_learner_info(self, model_id: str) -> Optional[Dict]:
        """获取在线学习器信息

        Args:
            model_id: 模型ID

        Returns:
            学习器信息字典
        """
        if model_id not in self._learners:
            return None

        learner = self._learners[model_id]

        return {
            "model_id": model_id,
            "config": {
                "min_samples": learner.config.min_samples,
                "max_samples": learner.config.max_samples,
                "update_interval": learner.config.update_interval,
                "enable_auto_retrain": learner.config.enable_auto_retrain,
            },
            "buffer": learner.get_buffer_info(),
            "last_update": learner._last_update_time.isoformat() if learner._last_update_time else None,
        }

    def get_all_learner_info(self) -> Dict[str, Dict]:
        """获取所有在线学习器信息

        Returns:
            学习器信息字典
        """
        return {
            model_id: self.get_learner_info(model_id)
            for model_id in self._learners.keys()
        }


__all__ = [
    "OnlineLearner",
    "OnlineLearningManager",
    "OnlineLearningConfig",
    "TrainingSample",
]
