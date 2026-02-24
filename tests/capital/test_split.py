"""
分批委托执行器单元测试
"""

import pytest
from vnpy_china_capital.order.split import SplitOrderExecutor
from vnpy_china_capital.objects.types import OrderBatchType


class TestSplitOrderExecutor:
    """分批委托执行器测试类"""

    def test_create_equal_batches_basic(self):
        """测试基本等量分批"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
        batches = executor.create_equal_batches()

        # 验证批次数量
        assert len(batches) == 5

        # 验证总数量
        assert sum(b.volume for b in batches) == 1000

        # 验证时间间隔
        for i, batch in enumerate(batches):
            assert batch.delay == i * 60

    def test_create_equal_batches_with_remainder(self):
        """测试带余数的等量分批"""
        executor = SplitOrderExecutor(total_volume=1003, n_batches=5)
        batches = executor.create_equal_batches()

        # 验证总数量正确
        assert sum(b.volume for b in batches) == 1003

        # 验证各批次数量
        assert batches[0].volume == 200  # 1003 // 5 = 200
        assert batches[1].volume == 200
        assert batches[2].volume == 200
        assert batches[3].volume == 200
        assert batches[4].volume == 203  # 最后一批包含余数

    def test_create_equal_batches_batch_type(self):
        """测试批次类型"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
        batches = executor.create_equal_batches()

        # 验证批次类型
        for batch in batches:
            assert batch.batch_type == OrderBatchType.EQUAL

    def test_execution_flow(self):
        """测试分批执行流程"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
        executor.create_equal_batches()

        # 模拟执行
        executed = 0
        while not executor.is_complete():
            batch = executor.get_next_batch()
            if batch:
                executed += batch.volume

        # 验证执行完成
        assert executed == 1000
        assert executor.is_complete() is True

    def test_get_batch_by_index(self):
        """测试根据索引获取批次"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
        executor.create_equal_batches()

        # 获取指定索引的批次
        batch = executor.get_batch_by_index(2)
        assert batch is not None
        assert batch.volume == 200

        # 获取无效索引
        batch = executor.get_batch_by_index(10)
        assert batch is None

    def test_execution_status(self):
        """测试执行状态"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
        executor.create_equal_batches()

        # 初始状态
        status = executor.get_execution_status()
        assert status["total_volume"] == 1000
        assert status["executed_volume"] == 0
        assert status["remaining_volume"] == 1000
        assert status["total_batches"] == 5
        assert status["current_batch"] == 0
        assert status["is_complete"] is False

        # 执行一批
        executor.get_next_batch()
        status = executor.get_execution_status()
        assert status["executed_volume"] == 200
        assert status["remaining_volume"] == 800
        assert status["current_batch"] == 1

    def test_reset(self):
        """测试重置功能"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
        executor.create_equal_batches()

        # 执行部分批次
        executor.get_next_batch()
        executor.get_next_batch()

        # 重置
        executor.reset()

        # 验证状态
        status = executor.get_execution_status()
        assert status["current_batch"] == 0
        assert status["is_complete"] is False

    def test_invalid_params(self):
        """测试无效参数"""
        # n_batches 为0
        with pytest.raises(ValueError):
            executor = SplitOrderExecutor(total_volume=1000, n_batches=0)
            executor.create_batches()

        # total_volume 为0
        with pytest.raises(ValueError):
            executor = SplitOrderExecutor(total_volume=0, n_batches=5)
            executor.create_batches()

    def test_single_batch(self):
        """测试单批情况"""
        executor = SplitOrderExecutor(total_volume=1000, n_batches=1)
        batches = executor.create_equal_batches()

        assert len(batches) == 1
        assert batches[0].volume == 1000
        assert batches[0].delay == 0

    def test_large_volume(self):
        """测试大数量"""
        executor = SplitOrderExecutor(total_volume=1000000, n_batches=100)
        batches = executor.create_equal_batches()

        assert len(batches) == 100
        assert sum(b.volume for b in batches) == 1000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
