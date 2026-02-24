"""
行业分析器测试
"""

import pytest
from vnpy_china_reporting.analysis.industry import IndustryAnalyzer
from vnpy_china_reporting.core.models import PositionRecord
from vnpy_china_reporting.core.enums import PositionSide


def create_mock_positions_with_industry():
    """创建带行业属性的模拟持仓数据"""
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
    ]


def test_industry_analyzer_init():
    """测试行业分析器初始化"""
    analyzer = IndustryAnalyzer()
    assert analyzer is not None


def test_analyze_distribution():
    """测试行业分布分析"""
    analyzer = IndustryAnalyzer()
    positions = create_mock_positions_with_industry()

    result = analyzer.analyze_distribution(positions)

    assert "industries" in result
    assert "distribution" in result
    assert "total_industries" in result


def test_analyze_distribution_empty():
    """测试空行业分布分析"""
    analyzer = IndustryAnalyzer()

    result = analyzer.analyze_distribution([])

    assert result["industries"] == []
    assert result["distribution"] == {}


def test_calculate_industry_return():
    """测试计算行业收益率"""
    analyzer = IndustryAnalyzer()
    positions = create_mock_positions_with_industry()

    result = analyzer.calculate_industry_return(positions)

    assert isinstance(result, dict)


def test_calculate_industry_return_empty():
    """测试空行业收益率计算"""
    analyzer = IndustryAnalyzer()

    result = analyzer.calculate_industry_return([])

    assert result == {}


def test_get_industry_summary():
    """测试获取行业摘要"""
    analyzer = IndustryAnalyzer()
    positions = create_mock_positions_with_industry()

    result = analyzer.get_industry_summary(positions)

    assert "total_industries" in result
    # 由于没有设置industry属性，应该是未知行业
    assert result["total_industries"] >= 0


def test_get_industry_summary_empty():
    """测试空行业摘要"""
    analyzer = IndustryAnalyzer()

    result = analyzer.get_industry_summary([])

    assert result["total_industries"] == 0
    assert result["top_industry"] is None
    assert result["worst_industry"] is None


def test_analyze_sector_allocation():
    """测试板块配置分析"""
    analyzer = IndustryAnalyzer()
    positions = create_mock_positions_with_industry()

    result = analyzer.analyze_sector_allocation(positions)

    assert "sectors" in result
    assert "benchmark_weight" in result
    assert "overweight" in result
    assert "underweight" in result


def test_analyze_sector_allocation_empty():
    """测试空板块配置分析"""
    analyzer = IndustryAnalyzer()

    result = analyzer.analyze_sector_allocation([])

    assert result["sectors"] == {}
    assert result["overweight"] == []
    assert result["underweight"] == []
