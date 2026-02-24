"""
图表生成器单元测试
"""

import pytest
import os
import tempfile
from datetime import date

from vnpy_china_reporting.core.models import PositionRecord
from vnpy_china_reporting.core.enums import PositionSide
from vnpy_china_reporting.export import ChartGenerator


class TestChartGenerator:
    """图表生成器测试类"""

    @pytest.fixture
    def generator(self):
        """创建图表生成器实例"""
        return ChartGenerator()

    @pytest.fixture
    def sample_positions(self):
        """创建示例持仓数据"""
        return [
            PositionRecord(
                symbol="000001",
                name="平安银行",
                side=PositionSide.LONG,
                volume=10000,
                avg_cost=10.5,
                current_price=11.0,
                market_value=110000.0,
                unrealized_pnl=5000.0,
                unrealized_pnl_ratio=0.0476
            ),
            PositionRecord(
                symbol="600000",
                name="浦发银行",
                side=PositionSide.LONG,
                volume=20000,
                avg_cost=8.0,
                current_price=7.5,
                market_value=150000.0,
                unrealized_pnl=-10000.0,
                unrealized_pnl_ratio=-0.0625
            ),
            PositionRecord(
                symbol="000002",
                name="万科A",
                side=PositionSide.LONG,
                volume=15000,
                avg_cost=20.0,
                current_price=22.0,
                market_value=330000.0,
                unrealized_pnl=30000.0,
                unrealized_pnl_ratio=0.1
            ),
        ]

    def test_generator_init(self, generator):
        """测试生成器初始化"""
        assert generator is not None
        assert generator.default_dpi == 300
        assert generator.default_figsize == (10, 6)

    def test_generate_equity_curve(self, generator):
        """测试生成资金曲线图"""
        equity_data = [100000, 105000, 102000, 108000, 110000, 115000]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "equity_curve.png")

            result = generator.generate_equity_curve(equity_data, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_generate_equity_curve_with_dates(self, generator):
        """测试带日期的资金曲线图"""
        equity_data = [100000, 105000, 102000, 108000]
        dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "equity_curve_dates.png")

            result = generator.generate_equity_curve(equity_data, dates=dates, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True

    def test_generate_pnl_distribution(self, generator):
        """测试生成盈亏分布图"""
        pnl_data = [
            1000, -500, 2000, -300, 1500, 800, -1200,
            3000, -800, 500, 2500, -200, 1800, 600
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "pnl_distribution.png")

            result = generator.generate_pnl_distribution(pnl_data, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_generate_industry_pie(self, generator):
        """测试生成行业饼图"""
        industry_data = {
            "银行": {"value": 500000, "ratio": 0.5, "count": 2},
            "地产": {"value": 300000, "ratio": 0.3, "count": 3},
            "消费": {"value": 200000, "ratio": 0.2, "count": 2}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "industry_pie.png")

            result = generator.generate_industry_pie(industry_data, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_generate_industry_pie_empty(self, generator):
        """测试空行业数据"""
        industry_data = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "empty_pie.png")

            result = generator.generate_industry_pie(industry_data, filepath=filepath)

            if generator._matplotlib_available:
                assert result is False

    def test_generate_position_bar(self, generator, sample_positions):
        """测试生成持仓柱状图"""
        position_data = [
            {
                "symbol": p.symbol,
                "name": p.name,
                "market_value": p.market_value,
                "pnl": p.unrealized_pnl
            }
            for p in sample_positions
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "position_bar.png")

            result = generator.generate_position_bar(position_data, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_generate_position_pie(self, generator, sample_positions):
        """测试生成持仓饼图"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "position_pie.png")

            result = generator.generate_position_pie(sample_positions, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True

    def test_generate_daily_return_bar(self, generator):
        """测试生成日收益率柱状图"""
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, 0.008, -0.003]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "daily_return.png")

            result = generator.generate_daily_return_bar(returns, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_generate_sharpe_chart(self, generator):
        """测试生成夏普比率图"""
        # 生成足够的收益率数据
        import numpy as np
        np.random.seed(42)
        returns = list(np.random.normal(0.001, 0.02, 50))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "sharpe_chart.png")

            result = generator.generate_sharpe_chart(returns, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True

    def test_generate_sharpe_chart_insufficient_data(self, generator):
        """测试数据不足时的夏普比率图"""
        returns = [0.01, 0.02]  # 数据太少

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "sharpe_short.png")

            result = generator.generate_sharpe_chart(returns, filepath=filepath)

            if generator._matplotlib_available:
                assert result is False

    def test_generate_drawdown_chart(self, generator):
        """测试生成回撤图"""
        equity_curve = [100000, 105000, 103000, 108000, 102000, 106000, 110000]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "drawdown_chart.png")

            result = generator.generate_drawdown_chart(equity_curve, filepath=filepath)

            if generator._matplotlib_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_generate_drawdown_empty(self, generator):
        """测试空资金曲线"""
        equity_curve = []

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "drawdown_empty.png")

            result = generator.generate_drawdown_chart(equity_curve, filepath=filepath)

            if generator._matplotlib_available:
                assert result is False

    def test_custom_dpi_and_figsize(self):
        """测试自定义DPI和图形尺寸"""
        generator = ChartGenerator(dpi=150, figsize=(8, 6))

        assert generator.default_dpi == 150
        assert generator.default_figsize == (8, 6)
