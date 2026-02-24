"""
持仓分析器测试
"""

import pytest
from datetime import date
from vnpy_china_reporting.analysis.position import PositionAnalyzer
from vnpy_china_reporting.core.models import PositionRecord
from vnpy_china_reporting.core.enums import PositionSide


def create_mock_positions():
    """创建模拟持仓数据"""
    return [
        PositionRecord(
            symbol="000001",
            name="平安银行",
            side=PositionSide.LONG,
            volume=10000,
            avg_cost=12.5,
            current_price=13.0,
            market_value=130000,
            unrealized_pnl=5000,
            unrealized_pnl_ratio=0.04
        ),
        PositionRecord(
            symbol="000002",
            name="万科A",
            side=PositionSide.LONG,
            volume=5000,
            avg_cost=8.0,
            current_price=7.5,
            market_value=37500,
            unrealized_pnl=-2500,
            unrealized_pnl_ratio=-0.0625
        ),
        PositionRecord(
            symbol="600000",
            name="浦发银行",
            side=PositionSide.LONG,
            volume=8000,
            avg_cost=10.0,
            current_price=11.0,
            market_value=88000,
            unrealized_pnl=8000,
            unrealized_pnl_ratio=0.1
        ),
        PositionRecord(
            symbol="600519",
            name="贵州茅台",
            side=PositionSide.LONG,
            volume=200,
            avg_cost=1800.0,
            current_price=2000.0,
            market_value=400000,
            unrealized_pnl=40000,
            unrealized_pnl_ratio=0.111
        ),
    ]


def test_position_analyzer_init():
    """测试持仓分析器初始化"""
    analyzer = PositionAnalyzer()
    assert analyzer is not None


def test_analyze_distribution():
    """测试持仓分布分析"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    result = analyzer.analyze_distribution(positions)

    assert result["total_positions"] == 4
    assert result["total_market_value"] > 0
    assert result["large_position_ratio"] >= 0
    assert result["medium_position_ratio"] >= 0
    assert result["small_position_ratio"] >= 0


def test_analyze_distribution_empty():
    """测试空持仓分布分析"""
    analyzer = PositionAnalyzer()

    result = analyzer.analyze_distribution([])

    assert result["total_positions"] == 0
    assert result["total_market_value"] == 0.0


def test_analyze_pnl():
    """测试盈亏分析"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    result = analyzer.analyze_pnl(positions)

    assert result["profitable_count"] == 3
    assert result["loss_count"] == 1
    assert result["total_pnl"] > 0
    assert result["best_pnl"] > 0
    assert result["worst_pnl"] < 0


def test_analyze_pnl_empty():
    """测试空盈亏分析"""
    analyzer = PositionAnalyzer()

    result = analyzer.analyze_pnl([])

    assert result["profitable_count"] == 0
    assert result["loss_count"] == 0
    assert result["total_pnl"] == 0.0


def test_analyze_concentration():
    """测试持仓集中度分析"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    result = analyzer.analyze_concentration(positions)

    assert result["ratio"] > 0
    assert result["hhi"] > 0
    assert result["ratio"] <= 1.0


def test_analyze_concentration_empty():
    """测试空持仓集中度分析"""
    analyzer = PositionAnalyzer()

    result = analyzer.analyze_concentration([])

    assert result["ratio"] == 0.0
    assert result["hhi"] == 0.0


def test_analyze_industry():
    """测试行业分析"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    result = analyzer.analyze_industry(positions)

    # 由于没有设置industry属性，应该返回"未知"
    assert "未知" in result


def test_analyze():
    """测试综合持仓分析"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    result = analyzer.analyze(positions)

    assert result.total_positions == 4
    assert result.total_market_value > 0
    assert isinstance(result.top_holdings, list)
    assert isinstance(result.concentration, float)
    assert isinstance(result.industry_distribution, dict)


def test_get_top_positions():
    """测试获取前N大持仓"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    top3 = analyzer.get_top_positions(positions, top_n=3)

    assert len(top3) == 3
    # 验证按市值排序（转为float比较）
    first = float(top3[0]["市值"].replace(",", ""))
    second = float(top3[1]["市值"].replace(",", ""))
    third = float(top3[2]["市值"].replace(",", ""))
    assert first >= second >= third


def test_get_top_positions_more_than_available():
    """测试获取超过实际数量的持仓"""
    analyzer = PositionAnalyzer()
    positions = create_mock_positions()

    top10 = analyzer.get_top_positions(positions, top_n=10)

    # 应该返回所有持仓
    assert len(top10) == 4
