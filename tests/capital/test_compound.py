"""
复利增长计算器单元测试
"""

import pytest
from vnpy_china_capital.equity.compound import CompoundGrowthCalculator


class TestCompoundGrowthCalculator:
    """复利增长计算器测试类"""

    def test_init(self):
        """测试初始化"""
        calculator = CompoundGrowthCalculator(target_return=0.20)

        assert calculator.target_return == 0.20

    def test_calculate_kelly_fraction_basic(self):
        """测试基本凯利公式计算"""
        calculator = CompoundGrowthCalculator()

        # 假设胜率50%，盈亏比2:1
        kelly = calculator.calculate_kelly_fraction(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=1000
        )

        # f* = (2 * 0.5 - 0.5) / 2 = 0.25
        # 半凯利 = 0.25 * 0.5 = 0.125
        assert kelly > 0.1
        assert kelly < 0.15

    def test_calculate_kelly_fraction_zero_win_rate(self):
        """测试零胜率"""
        calculator = CompoundGrowthCalculator()

        kelly = calculator.calculate_kelly_fraction(
            win_rate=0.0,
            avg_win=2000,
            avg_loss=1000
        )

        assert kelly == 0.0

    def test_calculate_kelly_fraction_full_win_rate(self):
        """测试100%胜率"""
        calculator = CompoundGrowthCalculator()

        kelly = calculator.calculate_kelly_fraction(
            win_rate=1.0,
            avg_win=2000,
            avg_loss=1000
        )

        assert kelly == 0.0

    def test_calculate_kelly_fraction_negative_expectancy(self):
        """测试负期望值"""
        calculator = CompoundGrowthCalculator()

        # 胜率30%，盈亏比1:1
        kelly = calculator.calculate_kelly_fraction(
            win_rate=0.3,
            avg_win=1000,
            avg_loss=1000
        )

        # (1 * 0.3 - 0.7) / 1 = -0.4 < 0，应该返回0
        assert kelly == 0.0

    def test_calculate_kelly_fraction_zero_loss(self):
        """测试零亏损"""
        calculator = CompoundGrowthCalculator()

        kelly = calculator.calculate_kelly_fraction(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=0
        )

        assert kelly == 0.0

    def test_calculate_position_size(self):
        """测试仓位大小计算"""
        calculator = CompoundGrowthCalculator()

        # 10万资金，25%凯利，25%最大限制
        position = calculator.calculate_position_size(
            current_capital=100000,
            kelly_fraction=0.25,
            max_position=0.25
        )

        assert position == 25000

    def test_calculate_position_size_exceeds_max(self):
        """测试超过最大仓位限制"""
        calculator = CompoundGrowthCalculator()

        # 10万资金，100%凯利（不可能这么大），25%最大限制
        position = calculator.calculate_position_size(
            current_capital=100000,
            kelly_fraction=1.0,
            max_position=0.25
        )

        assert position == 25000  # 受限于最大仓位

    def test_project_growth(self):
        """测试复利增长计算"""
        calculator = CompoundGrowthCalculator()

        # 10万本金，20%年化，10年
        final = calculator.project_growth(
            initial_capital=100000,
            annual_return=0.20,
            years=10
        )

        # 100000 * (1.2)^10 = 619173.6
        assert abs(final - 619173.6) < 1.0

    def test_project_growth_zero_return(self):
        """测试零收益复利"""
        calculator = CompoundGrowthCalculator()

        final = calculator.project_growth(
            initial_capital=100000,
            annual_return=0.0,
            years=10
        )

        assert final == 100000

    def test_project_growth_negative_return(self):
        """测试负收益复利"""
        calculator = CompoundGrowthCalculator()

        final = calculator.project_growth(
            initial_capital=100000,
            annual_return=-0.10,
            years=10
        )

        assert final < 100000
        assert final > 0

    def test_calculate_needed_return(self):
        """测试计算所需收益率"""
        calculator = CompoundGrowthCalculator()

        # 10万到100万，10年
        needed = calculator.calculate_needed_return(
            initial_capital=100000,
            target_capital=1000000,
            years=10
        )

        # (10/1)^(1/10) - 1 = 25.89%
        assert abs(needed - 0.2589) < 0.01

    def test_calculate_period_returns(self):
        """测试每年资金序列"""
        calculator = CompoundGrowthCalculator()

        returns = calculator.calculate_period_returns(
            initial_capital=100000,
            annual_return=0.20,
            years=5
        )

        assert len(returns) == 5
        assert abs(returns[0] - 120000) < 1.0
        assert abs(returns[-1] - 248832) < 1.0  # 100000 * 1.2^5

    def test_calculate_fractional_kelly(self):
        """测试分数凯利"""
        calculator = CompoundGrowthCalculator()

        # 胜率50%，盈亏比2:1
        full_kelly = calculator.calculate_kelly_fraction(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=1000
        )

        # 半凯利
        half_kelly = calculator.calculate_fractional_kelly(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=1000,
            fraction=0.5
        )

        assert half_kelly == full_kelly * 0.5

    def test_calculate_fractional_kelly_different_fractions(self):
        """测试不同分数的凯利"""
        calculator = CompoundGrowthCalculator()

        kelly_25 = calculator.calculate_fractional_kelly(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=1000,
            fraction=0.25
        )

        kelly_75 = calculator.calculate_fractional_kelly(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=1000,
            fraction=0.75
        )

        assert kelly_25 < kelly_75

    def test_calculate_optimal_f(self):
        """测试最优仓位计算"""
        calculator = CompoundGrowthCalculator()

        # 50%胜率，2:1盈亏比
        optimal = calculator.calculate_optimal_f(
            win_rate=0.5,
            avg_win=2000,
            avg_loss=1000,
            max_position=0.25
        )

        # 凯利约为0.125，受限于0.25
        assert optimal == 0.125

    def test_calculate_optimal_f_unconstrained(self):
        """测试无限制时的最优仓位"""
        calculator = CompoundGrowthCalculator()

        # 60%胜率，3:1盈亏比
        optimal = calculator.calculate_optimal_f(
            win_rate=0.6,
            avg_win=3000,
            avg_loss=1000,
            max_position=1.0
        )

        # b = 3, p = 0.6, q = 0.4
        # f* = (3 * 0.6 - 0.4) / 3 = 1.4 / 3 = 0.4666...
        # 半凯利 = 0.2333...
        assert optimal > 0.2
        assert optimal < 0.3

    def test_estimate_max_drawdown_from_kelly(self):
        """测试估算最大回撤"""
        calculator = CompoundGrowthCalculator()

        # 高凯利仓位
        dd = calculator.estimate_max_drawdown_from_kelly(
            kelly_fraction=0.25,
            win_rate=0.5
        )

        assert dd > 0
        assert dd < 1.0

    def test_estimate_max_drawdown_zero_kelly(self):
        """测试零凯利的回撤估算"""
        calculator = CompoundGrowthCalculator()

        dd = calculator.estimate_max_drawdown_from_kelly(
            kelly_fraction=0.0,
            win_rate=0.5
        )

        assert dd == 0.0

    def test_calculate_kelly_with_large_loss(self):
        """测试大亏损情况"""
        calculator = CompoundGrowthCalculator()

        kelly = calculator.calculate_kelly_fraction(
            win_rate=0.4,
            avg_win=1000,
            avg_loss=5000
        )

        # b = 0.2, p = 0.4, q = 0.6
        # f* = (0.2*0.4 - 0.6) / 0.2 = -2.6 < 0
        assert kelly == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
