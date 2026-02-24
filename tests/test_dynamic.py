"""
动态仓位管理器测试
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnpy_china_capital.position.dynamic import DynamicPosition


class TestDynamicPosition:
    """动态仓位管理器测试类"""

    def test_dynamic_basic(self):
        """测试基本动态仓位"""
        sizer = DynamicPosition(base_position=0.8)

        symbols = ["000001", "000002", "000003"]
        prices = {s: 10.0 for s in symbols}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 基础仓位 80%，分配到 3 只股票
        # 80000 / 3 = 26666.67 / 10 = 2666 -> 取整到 2600
        assert len(positions) == 3

    def test_dynamic_with_volatility(self):
        """测试带市场波动率的动态仓位"""
        sizer = DynamicPosition(base_position=0.8, min_position=0.3, max_position=1.0)

        symbols = ["000001", "000002"]
        prices = {"000001": 10.0, "000002": 10.0}
        capital = 100000.0

        # 低波动率市场
        positions_low = sizer.calculate_positions(
            symbols, capital, prices, market_volatility=0.1
        )
        ratio_low = sizer.get_current_ratio()

        # 高波动率市场
        sizer.reset_ratio()
        positions_high = sizer.calculate_positions(
            symbols, capital, prices, market_volatility=0.5
        )
        ratio_high = sizer.get_current_ratio()

        # 低波动率应该获得更高仓位
        assert ratio_low > ratio_high

    def test_dynamic_min_max_bounds(self):
        """测试最小最大仓位限制"""
        sizer = DynamicPosition(
            base_position=0.8,
            min_position=0.3,
            max_position=1.0
        )

        # 极高波动率应该触发最小仓位
        ratio_extreme = sizer.calculate_dynamic_ratio(10.0)
        assert ratio_extreme >= 0.3

        # 零波动率应该接近最大仓位
        sizer.reset_ratio()
        ratio_zero = sizer.calculate_dynamic_ratio(0.0)
        assert ratio_zero <= 1.0

    def test_dynamic_with_trend(self):
        """测试带趋势强度的动态仓位"""
        # 使用较低的 min_position 避免被边界限制
        sizer = DynamicPosition(base_position=0.5, min_position=0.1)

        # 强趋势
        ratio_strong = sizer.calculate_dynamic_ratio(
            market_volatility=0.2, trend_strength=0.9
        )

        # 弱趋势
        sizer.reset_ratio()
        ratio_weak = sizer.calculate_dynamic_ratio(
            market_volatility=0.2, trend_strength=0.1
        )

        # 强趋势应该有更高仓位
        assert ratio_strong > ratio_weak

    def test_dynamic_empty_symbols(self):
        """测试空列表"""
        sizer = DynamicPosition()

        positions = sizer.calculate_positions([], 100000.0, {})

        assert positions == {}

    def test_dynamic_allocations(self):
        """测试分配记录"""
        sizer = DynamicPosition(base_position=0.6)

        symbols = ["000001", "000002"]
        prices = {"000001": 10.0, "000002": 10.0}
        capital = 100000.0
        market_volatility = 0.2

        positions = sizer.calculate_positions(
            symbols, capital, prices, market_volatility=market_volatility
        )

        # 检查 allocations
        assert len(sizer.allocations) == 2
        for symbol, allocation in sizer.allocations.items():
            assert allocation.symbol == symbol
            assert "动态仓位分配" in allocation.reason

    def test_dynamic_ratio_reset(self):
        """测试仓位比例重置"""
        sizer = DynamicPosition(base_position=0.8)

        # 先设置一个不同的比例
        sizer.calculate_dynamic_ratio(0.5)
        assert sizer.get_current_ratio() != 0.8

        # 重置
        sizer.reset_ratio()
        assert sizer.get_current_ratio() == 0.8

    def test_dynamic_max_position_count(self):
        """测试最大持仓数量"""
        sizer = DynamicPosition(max_position_count=3)

        symbols = ["000001", "000002", "000003", "000004", "000005"]
        prices = {s: 10.0 for s in symbols}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 最多持仓3只
        assert len(positions) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
