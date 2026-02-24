"""
TWAP执行器单元测试
"""

import pytest
from vnpy_china_capital.order.twap import TWAPOrderExecutor
from vnpy_china_capital.objects.types import OrderBatchType


class TestTWAPOrderExecutor:
    """TWAP执行器测试类"""

    def test_create_twap_batches_basic(self):
        """测试基本TWAP批次"""
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=300,
            n_slices=10
        )
        batches = executor.create_twap_batches()

        # 验证切片数量
        assert len(batches) == 10

        # 验证总数量
        assert sum(b.volume for b in batches) == 1000

        # 验证批次类型
        for batch in batches:
            assert batch.batch_type == OrderBatchType.TWAP

    def test_time_interval(self):
        """测试时间间隔"""
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=300,
            n_slices=10
        )
        batches = executor.create_twap_batches()

        # 验证时间间隔
        assert batches[0].delay == 0
        assert batches[1].delay == 30
        assert batches[2].delay == 60

    def test_volume_distribution(self):
        """测试数量分布"""
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=300,
            n_slices=10
        )
        batches = executor.create_twap_batches()

        # 每批100股
        for i, batch in enumerate(batches):
            assert batch.volume == 100

    def test_create_twap_batches_with_remainder(self):
        """测试带余数的情况"""
        executor = TWAPOrderExecutor(
            total_volume=1003,
            time_window_seconds=300,
            n_slices=10
        )
        batches = executor.create_twap_batches()

        # 验证总数量
        assert sum(b.volume for b in batches) == 1003

        # 前9批各100股，第10批103股
        for i in range(9):
            assert batches[i].volume == 100
        assert batches[9].volume == 103

    def test_execution_flow(self):
        """测试执行流程"""
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=300,
            n_slices=10
        )
        executor.create_batches()

        # 模拟执行
        executed = 0
        while not executor.is_complete():
            batch = executor.get_next_batch()
            if batch:
                executed += batch.volume

        # 验证执行完成
        assert executed == 1000
        assert executor.is_complete() is True

    def test_get_interval_seconds(self):
        """测试获取时间间隔"""
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=300,
            n_slices=10
        )
        executor.create_batches()

        interval = executor.get_interval_seconds()
        assert interval == 30

    def test_invalid_params(self):
        """测试无效参数"""
        # time_window_seconds 为0
        with pytest.raises(ValueError):
            executor = TWAPOrderExecutor(
                total_volume=1000,
                time_window_seconds=0,
                n_slices=10
            )
            executor.create_batches()

        # n_slices 为0
        with pytest.raises(ValueError):
            executor = TWAPOrderExecutor(
                total_volume=1000,
                time_window_seconds=300,
                n_slices=0
            )
            executor.create_batches()

        # total_volume 为0
        with pytest.raises(ValueError):
            executor = TWAPOrderExecutor(
                total_volume=0,
                time_window_seconds=300,
                n_slices=10
            )
            executor.create_batches()

    def test_execution_status(self):
        """测试执行状态"""
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=300,
            n_slices=10
        )
        executor.create_batches()

        # 初始状态
        status = executor.get_execution_status()
        assert status["total_volume"] == 1000
        assert status["executed_volume"] == 0
        assert status["remaining_volume"] == 1000
        assert status["total_batches"] == 10
        assert status["is_complete"] is False

        # 执行一批
        executor.get_next_batch()
        status = executor.get_execution_status()
        assert status["executed_volume"] == 100

    def test_different_time_windows(self):
        """测试不同时间窗口"""
        # 1分钟窗口
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=60,
            n_slices=6
        )
        batches = executor.create_twap_batches()
        assert executor.get_interval_seconds() == 10

        # 10分钟窗口
        executor = TWAPOrderExecutor(
            total_volume=1000,
            time_window_seconds=600,
            n_slices=10
        )
        batches = executor.create_twap_batches()
        assert executor.get_interval_seconds() == 60

    def test_large_volume(self):
        """测试大数量"""
        executor = TWAPOrderExecutor(
            total_volume=1000000,
            time_window_seconds=3600,
            n_slices=100
        )
        batches = executor.create_twap_batches()

        assert len(batches) == 100
        assert sum(b.volume for b in batches) == 1000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
