"""
金字塔委托执行器单元测试
"""

import pytest
from vnpy_china_capital.order.pyramid import PyramidOrderExecutor
from vnpy_china_capital.objects.types import OrderBatchType


class TestPyramidOrderExecutor:
    """金字塔委托执行器测试类"""

    def test_create_pyramid_batches_buy_default(self):
        """测试默认金字塔买入批次"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)
        batches = executor.create_pyramid_batches(direction="buy")

        # 验证批次数量
        assert len(batches) == 3

        # 验证总数量
        assert sum(b.volume for b in batches) == 1000

        # 验证批次类型
        for batch in batches:
            assert batch.batch_type == OrderBatchType.PYRAMID_BUY

        # 验证金字塔模式（越买越多）
        assert batches[0].volume == 200  # 20%
        assert batches[1].volume == 300  # 30%
        assert batches[2].volume == 500  # 50%

    def test_create_pyramid_batches_sell_default(self):
        """测试默认金字塔卖出批次"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)
        batches = executor.create_pyramid_batches(direction="sell")

        # 验证批次数量
        assert len(batches) == 3

        # 验证总数量
        assert sum(b.volume for b in batches) == 1000

        # 验证批次类型
        for batch in batches:
            assert batch.batch_type == OrderBatchType.PYRAMID_SELL

        # 验证倒金字塔模式（越卖越多）
        assert batches[0].volume == 500  # 50%
        assert batches[1].volume == 300  # 30%
        assert batches[2].volume == 200  # 20%

    def test_create_pyramid_batches_custom_ratios(self):
        """测试自定义比例"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=4)
        batches = executor.create_pyramid_batches(
            direction="buy",
            ratios=[0.1, 0.2, 0.3, 0.4]
        )

        # 验证批次数量
        assert len(batches) == 4

        # 验证总数量
        assert sum(b.volume for b in batches) == 1000

    def test_create_pyramid_batches_custom_ratios_with_remainder(self):
        """测试自定义比例带余数"""
        executor = PyramidOrderExecutor(total_volume=1003, n_levels=3)
        batches = executor.create_pyramid_batches(
            direction="buy",
            ratios=[0.2, 0.3, 0.5]
        )

        # 验证总数量
        assert sum(b.volume for b in batches) == 1003

    def test_time_delays(self):
        """测试时间延迟"""
        executor = PyramidOrderExecutor(
            total_volume=1000,
            n_levels=3,
            interval_seconds=120
        )
        batches = executor.create_pyramid_batches(direction="buy")

        # 验证时间间隔
        assert batches[0].delay == 0
        assert batches[1].delay == 120
        assert batches[2].delay == 240

    def test_execution_flow(self):
        """测试执行流程"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)
        executor.create_batches(direction="buy")

        # 模拟执行
        executed = 0
        while not executor.is_complete():
            batch = executor.get_next_batch()
            if batch:
                executed += batch.volume

        # 验证执行完成
        assert executed == 1000
        assert executor.is_complete() is True

    def test_invalid_direction(self):
        """测试无效方向"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)

        with pytest.raises(ValueError):
            executor.create_batches(direction="invalid")

    def test_invalid_ratios_sum(self):
        """测试无效比例总和"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)

        with pytest.raises(ValueError):
            executor.create_batches(direction="buy", ratios=[0.2, 0.3, 0.3])

    def test_different_levels(self):
        """测试不同层数"""
        # 2层
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=2)
        batches = executor.create_pyramid_batches(direction="buy")
        assert len(batches) == 2

        # 4层
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=4)
        batches = executor.create_pyramid_batches(direction="buy")
        assert len(batches) == 4

    def test_execution_status(self):
        """测试执行状态"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)
        executor.create_batches(direction="buy")

        # 初始状态
        status = executor.get_execution_status()
        assert status["total_volume"] == 1000
        assert status["executed_volume"] == 0
        assert status["remaining_volume"] == 1000
        assert status["total_batches"] == 3
        assert status["is_complete"] is False

        # 执行一批
        executor.get_next_batch()
        status = executor.get_execution_status()
        assert status["executed_volume"] == 200

    def test_get_default_ratios(self):
        """测试获取默认比例"""
        executor = PyramidOrderExecutor(total_volume=1000, n_levels=3)

        buy_ratios = executor.get_default_ratios("buy")
        assert buy_ratios == [0.2, 0.3, 0.5]

        sell_ratios = executor.get_default_ratios("sell")
        assert sell_ratios == [0.5, 0.3, 0.2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
