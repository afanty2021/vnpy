"""
等权重仓位管理器测试
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnpy_china_capital.position.equal_weight import EqualWeightPosition


class TestEqualWeightPosition:
    """等权重仓位管理器测试类"""

    def test_equal_weight_basic(self):
        """测试基本等权重分配"""
        sizer = EqualWeightPosition(max_position=5)

        symbols = ["000001", "000002", "000003", "000004", "000005"]
        prices = {s: 10.0 for s in symbols}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 验证结果
        assert len(positions) == 5
        # 每只股票分配 20000 元，10 元价格 = 2000 股
        for symbol, volume in positions.items():
            assert volume == 2000

    def test_equal_weight_max_position(self):
        """测试最大持仓数量限制"""
        sizer = EqualWeightPosition(max_position=3)

        symbols = ["000001", "000002", "000003", "000004", "000005"]
        prices = {s: 10.0 for s in symbols}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 最多持仓3只
        assert len(positions) == 3

    def test_equal_weight_rounding(self):
        """测试取整规则"""
        sizer = EqualWeightPosition(max_position=1)

        symbols = ["000001"]
        prices = {"000001": 10.5}
        capital = 10000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 10000 / 10.5 = 952.38 -> 900股（取整到100）
        assert positions["000001"] % 100 == 0
        assert positions["000001"] > 0

    def test_empty_symbols(self):
        """测试空列表"""
        sizer = EqualWeightPosition(max_position=5)

        positions = sizer.calculate_positions([], 100000.0, {})

        assert positions == {}

    def test_zero_price(self):
        """测试价格为0的情况"""
        sizer = EqualWeightPosition(max_position=3)

        symbols = ["000001", "000002", "000003"]
        prices = {"000001": 10.0, "000002": 0, "000003": 15.0}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 价格为0的股票应该被跳过
        assert "000002" not in positions
        assert len(positions) == 2

    def test_allocations_recorded(self):
        """测试分配记录"""
        sizer = EqualWeightPosition(max_position=3)

        symbols = ["000001", "000002", "000003"]
        prices = {s: 10.0 for s in symbols}
        capital = 90000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 检查 allocations 记录
        assert len(sizer.allocations) == 3
        for symbol, allocation in sizer.allocations.items():
            assert allocation.symbol == symbol
            assert allocation.weight == pytest.approx(1.0 / 3)
            assert allocation.reason == "等权重分配"

    def test_single_stock(self):
        """测试单只股票"""
        sizer = EqualWeightPosition(max_position=1)

        symbols = ["000001"]
        prices = {"000001": 10.0}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 100000 / 1 = 100000 元，10 元 = 10000 股 -> 取整到 100 = 10000 股
        assert positions["000001"] == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
