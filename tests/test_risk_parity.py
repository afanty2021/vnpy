"""
风险平价仓位管理器测试
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnpy_china_capital.position.risk_parity import RiskParityPosition


class TestRiskParityPosition:
    """风险平价仓位管理器测试类"""

    def test_risk_parity_basic(self):
        """测试基本风险平价分配"""
        sizer = RiskParityPosition()

        symbols = ["000001", "000002", "000003"]
        prices = {s: 10.0 for s in symbols}
        capital = 100000.0

        positions = sizer.calculate_positions(symbols, capital, prices)

        # 默认波动率相同，权重应该相等
        assert len(positions) == 3

    def test_risk_parity_with_volatility(self):
        """测试带波动率的风险平价分配"""
        sizer = RiskParityPosition()

        symbols = ["000001", "000002"]
        prices = {"000001": 10.0, "000002": 10.0}
        volatilities = {"000001": 0.1, "000002": 0.3}  # 000001 波动率更低
        capital = 100000.0

        positions = sizer.calculate_positions(
            symbols, capital, prices, volatilities=volatilities
        )

        # 波动率低的股票应该获得更高权重
        assert len(positions) == 2
        # 000001 波动率是 000002 的 1/3，权重应该是 3 倍
        # 100000 * 0.75 / 10 = 7500 -> 7400
        # 100000 * 0.25 / 10 = 2500 -> 2400
        assert positions["000001"] > positions["000002"]

    def test_risk_parity_empty_symbols(self):
        """测试空列表"""
        sizer = RiskParityPosition()

        positions = sizer.calculate_positions([], 100000.0, {})

        assert positions == {}

    def test_risk_parity_zero_volatility(self):
        """测试波动率为0的处理"""
        sizer = RiskParityPosition()

        symbols = ["000001", "000002"]
        prices = {"000001": 10.0, "000002": 10.0}
        volatilities = {"000001": 0, "000002": 0.2}  # 000001 波动率为0
        capital = 100000.0

        positions = sizer.calculate_positions(
            symbols, capital, prices, volatilities=volatilities
        )

        # 波动率为0的股票应该被处理（使用最小值）
        assert len(positions) >= 1

    def test_risk_parity_allocations(self):
        """测试分配记录"""
        sizer = RiskParityPosition()

        symbols = ["000001", "000002"]
        prices = {"000001": 10.0, "000002": 10.0}
        volatilities = {"000001": 0.1, "000002": 0.2}
        capital = 100000.0

        positions = sizer.calculate_positions(
            symbols, capital, prices, volatilities=volatilities
        )

        # 检查 allocations
        assert len(sizer.allocations) == 2
        for symbol, allocation in sizer.allocations.items():
            assert allocation.symbol == symbol
            assert "风险平价分配" in allocation.reason

    def test_risk_parity_weights_sum(self):
        """测试权重总和为1"""
        sizer = RiskParityPosition()

        symbols = ["000001", "000002", "000003", "000004"]
        prices = {s: 10.0 for s in symbols}
        volatilities = {s: 0.2 for s in symbols}
        capital = 100000.0

        positions = sizer.calculate_positions(
            symbols, capital, prices, volatilities=volatilities
        )

        # 权重总和应该为1
        total_weight = sum(a.weight for a in sizer.allocations.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_default_volatility_setting(self):
        """测试默认波动率设置"""
        sizer = RiskParityPosition()
        sizer.set_default_volatility(0.3)

        assert sizer.default_volatility == 0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
