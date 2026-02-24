"""
时间加权平均价格（TWAP）执行器

在指定时间窗口内均匀执行委托，以获得时间加权平均价格。
适用于大单拆分场景。
"""

from typing import List
from .base import OrderExecutor
from ..objects.types import OrderBatch, OrderBatchType


class TWAPOrderExecutor(OrderExecutor):
    """
    时间加权平均价格（TWAP）执行器

    在指定时间窗口内将委托均匀分成若干份执行，以获得接近时间
    加权平均价格的价格。适用于大单拆分场景，可以降低市场冲击。

    示例:
        >>> # 在5分钟内执行10000股，分成10批
        >>> executor = TWAPOrderExecutor(
        ...     total_volume=10000,
        ...     time_window_seconds=300,
        ...     n_slices=10
        ... )
        >>> batches = executor.create_twap_batches()
        >>> for batch in batches:
        ...     print(f"委托数量: {batch.volume}, 延迟: {batch.delay}秒")
    """

    def __init__(
        self,
        total_volume: int,
        time_window_seconds: int = 300,
        n_slices: int = 10
    ) -> None:
        """
        构造函数

        Args:
            total_volume: 总委托数量
            time_window_seconds: 时间窗口（秒），默认为300秒（5分钟）
            n_slices: 切片数量，默认为10份
        """
        super().__init__(total_volume)
        self.time_window_seconds = time_window_seconds
        self.n_slices = n_slices

    def create_batches(self) -> List[OrderBatch]:
        """
        创建TWAP批次

        在时间窗口内均匀创建若干批次，每批之间的时间间隔相等。

        Returns:
            批次列表

        Raises:
            ValueError: 当 time_window_seconds 小于1时
            ValueError: 当 n_slices 小于1时
        """
        if self.time_window_seconds < 1:
            raise ValueError("time_window_seconds 必须大于等于1")

        if self.n_slices < 1:
            raise ValueError("n_slices 必须大于等于1")

        if self.total_volume <= 0:
            raise ValueError("total_volume 必须大于0")

        # 计算每批之间的时间间隔
        interval = self.time_window_seconds // self.n_slices

        # 计算每批的基础数量
        volume_per_slice = self.total_volume // self.n_slices

        batches: List[OrderBatch] = []

        for i in range(self.n_slices):
            # 最后一批调整数量，包含所有余数
            if i == self.n_slices - 1:
                volume = self.total_volume - volume_per_slice * (self.n_slices - 1)
            else:
                volume = volume_per_slice

            # 创建批次
            batch = OrderBatch(
                price=0,  # 0表示市价单
                volume=volume,
                delay=i * interval,
                batch_type=OrderBatchType.TWAP
            )
            batches.append(batch)

        self.batches = batches
        return batches

    def create_twap_batches(self) -> List[OrderBatch]:
        """
        创建TWAP批次（别名方法）

        Returns:
            批次列表
        """
        return self.create_batches()

    def get_interval_seconds(self) -> int:
        """
        获取每批之间的时间间隔

        Returns:
            时间间隔（秒）
        """
        return self.time_window_seconds // self.n_slices

    def get_batch_interval(self) -> int:
        """
        获取每批之间的时间间隔（别名方法）

        Returns:
            时间间隔（秒）
        """
        return self.get_interval_seconds()
