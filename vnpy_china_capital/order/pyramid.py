"""
金字塔委托执行器

金字塔委托模式：买入时越买越多（左侧金字塔），卖出时越卖越多。
适用于趋势跟踪策略，随着趋势确认逐步加仓。
"""

from typing import List, Optional

from .base import OrderExecutor
from ..objects.types import OrderBatch, OrderBatchType


class PyramidOrderExecutor(OrderExecutor):
    """
    金字塔委托执行器

    买入时采用左侧金字塔模式（越买越多），卖出时采用倒金字塔模式
    （越卖越多）。适用于趋势跟踪策略，随着趋势确认逐步加仓。

    示例:
        >>> # 金字塔买入：3层分别为20%、30%、50%
        >>> executor = PyramidOrderExecutor(total_volume=10000, n_levels=3)
        >>> batches = executor.create_pyramid_batches(direction="buy")
        >>> for batch in batches:
        ...     print(f"委托数量: {batch.volume}, 延迟: {batch.delay}秒")

        >>> # 自定义比例
        >>> executor = PyramidOrderExecutor(total_volume=10000, n_levels=4)
        >>> batches = executor.create_pyramid_batches(
        ...     direction="buy",
        ...     ratios=[0.1, 0.2, 0.3, 0.4]
        ... )
    """

    # 默认金字塔比例
    DEFAULT_BUY_RATIOS: List[float] = [0.2, 0.3, 0.5]
    DEFAULT_SELL_RATIOS: List[float] = [0.5, 0.3, 0.2]

    def __init__(
        self,
        total_volume: int,
        n_levels: int = 3,
        interval_seconds: int = 120
    ) -> None:
        """
        构造函数

        Args:
            total_volume: 总委托数量
            n_levels: 金字塔层数，默认为3层
            interval_seconds: 每层间隔秒数，默认为120秒
        """
        super().__init__(total_volume)
        self.n_levels = n_levels
        self.interval_seconds = interval_seconds

    def create_batches(
        self,
        direction: str = "buy",
        ratios: Optional[List[float]] = None
    ) -> List[OrderBatch]:
        """
        创建金字塔批次

        Args:
            direction: 方向，"buy" 或 "sell"
            ratios: 自定义比例列表，如果为 None 则使用默认比例

        Returns:
            批次列表

        Raises:
            ValueError: 当 direction 不是 "buy" 或 "sell" 时
            ValueError: 当 ratios 总和不为1时
        """
        if direction not in ("buy", "sell"):
            raise ValueError("direction 必须是 'buy' 或 'sell'")

        # 使用默认比例或自定义比例
        if ratios is None:
            if direction == "buy":
                default_ratios = self.DEFAULT_BUY_RATIOS
            else:
                default_ratios = self.DEFAULT_SELL_RATIOS

            # 如果层数大于默认比例数量，则均匀分配
            if self.n_levels > len(default_ratios):
                ratios = [1.0 / self.n_levels] * self.n_levels
            elif self.n_levels < len(default_ratios):
                # 如果层数小于默认比例数量，截取前n_levels个并归一化
                ratios = default_ratios[:self.n_levels]
                # 归一化确保总和为1
                ratio_sum = sum(ratios)
                if ratio_sum > 0:
                    ratios = [r / ratio_sum for r in ratios]
            else:
                ratios = default_ratios[:self.n_levels]
        else:
            # 调整比例列表长度
            if len(ratios) > self.n_levels:
                ratios = ratios[:self.n_levels]
            elif len(ratios) < self.n_levels:
                # 填充默认值
                default = self.DEFAULT_BUY_RATIOS if direction == "buy" else self.DEFAULT_SELL_RATIOS
                ratios = ratios + default[len(ratios):self.n_levels]

        # 验证比例总和
        ratio_sum = sum(ratios)
        if abs(ratio_sum - 1.0) > 0.001:
            raise ValueError(f"比例总和必须为1，当前为 {ratio_sum}")

        # 计算每批数量
        volumes = [int(self.total_volume * r) for r in ratios]

        # 调整最后一批确保总数正确
        if volumes:
            volumes[-1] = self.total_volume - sum(volumes[:-1])

        # 确定批次类型
        batch_type = (OrderBatchType.PYRAMID_BUY if direction == "buy"
                     else OrderBatchType.PYRAMID_SELL)

        # 创建批次
        batches: List[OrderBatch] = [
            OrderBatch(
                price=0,  # 0表示市价单
                volume=v,
                delay=i * self.interval_seconds,
                batch_type=batch_type
            )
            for i, v in enumerate(volumes)
        ]

        self.batches = batches
        return batches

    def create_pyramid_batches(
        self,
        direction: str = "buy",
        ratios: Optional[List[float]] = None
    ) -> List[OrderBatch]:
        """
        创建金字塔批次（别名方法）

        Args:
            direction: 方向，"buy" 或 "sell"
            ratios: 自定义比例列表

        Returns:
            批次列表
        """
        return self.create_batches(direction, ratios)

    def get_default_ratios(self, direction: str) -> List[float]:
        """
        获取指定方向的默认金字塔比例

        Args:
            direction: 方向，"buy" 或 "sell"

        Returns:
            默认比例列表
        """
        if direction == "buy":
            return self.DEFAULT_BUY_RATIOS[:self.n_levels]
        else:
            return self.DEFAULT_SELL_RATIOS[:self.n_levels]
