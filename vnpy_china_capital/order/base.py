"""
订单执行器基类

定义所有订单执行器的抽象基类和通用接口。
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..objects.types import OrderBatch


class OrderExecutor(ABC):
    """
    订单执行器抽象基类

    负责将大单拆分成多个小单分批执行，以降低市场冲击成本。
    所有具体的执行算法都应继承此类。
    """

    def __init__(self, total_volume: int) -> None:
        """
        构造函数

        Args:
            total_volume: 总委托数量
        """
        self.total_volume = total_volume
        self.batches: List[OrderBatch] = []
        self.current_batch_index: int = 0

    @abstractmethod
    def create_batches(self) -> List[OrderBatch]:
        """
        创建委托批次

        Returns:
            批次列表
        """
        pass

    def get_next_batch(self) -> Optional[OrderBatch]:
        """
        获取下一批委托

        Returns:
            下一批委托，如果没有更多批次则返回 None
        """
        if self.current_batch_index >= len(self.batches):
            return None

        batch = self.batches[self.current_batch_index]
        self.current_batch_index += 1
        return batch

    def is_complete(self) -> bool:
        """
        检查是否所有批次都已执行完成

        Returns:
            是否完成
        """
        return self.current_batch_index >= len(self.batches)

    def reset(self) -> None:
        """重置执行器状态"""
        self.current_batch_index = 0

    def get_executed_volume(self) -> int:
        """
        获取已执行的数量

        Returns:
            已执行的总数
        """
        return sum(b.volume for b in self.batches[:self.current_batch_index])

    def get_remaining_volume(self) -> int:
        """
        获取剩余数量

        Returns:
            剩余总数
        """
        return sum(b.volume for b in self.batches[self.current_batch_index:])

    def get_execution_status(self) -> dict:
        """
        获取执行状态

        Returns:
            执行状态字典
        """
        return {
            "total_volume": self.total_volume,
            "executed_volume": self.get_executed_volume(),
            "remaining_volume": self.get_remaining_volume(),
            "total_batches": len(self.batches),
            "current_batch": self.current_batch_index,
            "is_complete": self.is_complete()
        }
