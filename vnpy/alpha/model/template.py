from abc import ABCMeta, abstractmethod
from typing import Any

import numpy as np

from vnpy.alpha.dataset import AlphaDataset, Segment


class AlphaModel(metaclass=ABCMeta):
    """Template class for machine learning algorithms"""

    # 新增：增量训练能力标识
    supports_incremental: bool = False

    @abstractmethod
    def fit(self, dataset: AlphaDataset) -> None:
        """
        Fit the model with dataset
        """
        pass

    @abstractmethod
    def predict(self, dataset: AlphaDataset, segment: Segment) -> np.ndarray:
        """
        Make predictions using the model
        """
        pass

    def detail(self) -> Any:
        """
        Output detailed information about the model
        """
        return

    # 新增：增量训练接口
    def partial_fit(self, dataset: AlphaDataset, **kwargs) -> dict:
        """
        增量训练（可选实现）

        Args:
            dataset: AlphaDataset 实例
            **kwargs: 额外的训练参数

        Returns:
            dict: 训练结果，包含 loss、metrics 等信息

        Raises:
            NotImplementedError: 如果模型不支持增量训练
        """
        if not self.supports_incremental:
            raise NotImplementedError(f"{self.__class__.__name__} 不支持增量训练")
        raise NotImplementedError("子类必须实现 partial_fit()")

    # 新增：训练状态序列化
    def get_training_state(self) -> dict:
        """
        获取训练状态用于序列化

        Returns:
            dict: 训练状态字典，包含模型权重、优化器状态等
        """
        return {}

    def set_training_state(self, state: dict) -> None:
        """
        从序列化的状态恢复模型

        Args:
            state: 训练状态字典
        """
        pass
