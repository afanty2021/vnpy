"""
分批委托执行器

将大单拆分成多个小单分批执行，降低市场冲击成本。
"""

from typing import List, Optional
from .base import OrderExecutor
from ..objects.types import OrderBatch, OrderBatchType


class SplitOrderExecutor(OrderExecutor):
    """
    分批委托执行器

    将大单拆分成多个等量的小单分批执行，适用于需要拆分大单的场
    景，可以降低对市场价格的影响。

    示例:
        >>> executor = SplitOrderExecutor(total_volume=10000, n_batches=10)
        >>> batches = executor.create_equal_batches()
        >>> for batch in batches:
        ...     print(f"委托数量: {batch.volume}, 延迟: {batch.delay}秒")
    """

    def __init__(
        self,
        total_volume: int,
        n_batches: int = 5,
        interval_seconds: int = 60
    ) -> None:
        """
        构造函数

        Args:
            total_volume: 总委托数量
            n_batches: 分批数量，默认为5批
            interval_seconds: 每批间隔秒数，默认为60秒
        """
        super().__init__(total_volume)
        self.n_batches = n_batches
        self.interval_seconds = interval_seconds

    def create_batches(self) -> List[OrderBatch]:
        """
        创建等量分批

        将总委托数量平均分成若干批，最后一批会包含所有余数。

        Returns:
            批次列表

        Raises:
            ValueError: 当 n_batches 小于1时
        """
        if self.n_batches < 1:
            raise ValueError("n_batches 必须大于等于1")

        if self.total_volume <= 0:
            raise ValueError("total_volume 必须大于0")

        # 计算每批的基础数量
        volume_per_batch = self.total_volume // self.n_batches

        batches: List[OrderBatch] = []

        for i in range(self.n_batches):
            # 最后一批调整数量，包含所有余数
            if i == self.n_batches - 1:
                volume = self.total_volume - volume_per_batch * (self.n_batches - 1)
            else:
                volume = volume_per_batch

            # 创建批次
            batch = OrderBatch(
                price=0,  # 0表示市价单
                volume=volume,
                delay=i * self.interval_seconds,
                batch_type=OrderBatchType.EQUAL
            )
            batches.append(batch)

        self.batches = batches
        return batches

    def create_equal_batches(self) -> List[OrderBatch]:
        """
        创建等量分批（别名方法）

        Returns:
            批次列表
        """
        return self.create_batches()

    def get_batch_by_index(self, index: int) -> Optional[OrderBatch]:
        """
        根据索引获取指定批次

        Args:
            index: 批次索引

        Returns:
            指定索引的批次，如果索引无效则返回 None
        """
        if 0 <= index < len(self.batches):
            return self.batches[index]
        return None
