"""
年报生成器测试
"""

import pytest
from datetime import date
from vnpy_china_reporting.report.yearly import YearlyReportGenerator
from vnpy_china_reporting.core.enums import ReportType


def test_yearly_report_generator_init():
    """测试年报生成器初始化"""
    generator = YearlyReportGenerator()
    assert generator.main_engine is None
    assert generator.report_type == ReportType.YEARLY
    assert generator.monthly_generator is not None


def test_yearly_report_generator_with_main_engine():
    """测试带主引擎的年报生成器"""
    mock_engine = object()
    generator = YearlyReportGenerator(main_engine=mock_engine)
    assert generator.main_engine is mock_engine


def test_generate_yearly_report():
    """测试生成年报"""
    generator = YearlyReportGenerator()
    year = 2025

    report = generator.generate(year)

    assert report.report_type == ReportType.YEARLY
    assert report.start_date == date(2025, 1, 1)
    assert report.end_date == date(2025, 12, 31)
    assert isinstance(report.account.total_equity, float)


def test_generate_yearly_report_2024():
    """测试生成2024年年报（闰年）"""
    generator = YearlyReportGenerator()
    year = 2024

    report = generator.generate(year)

    assert report.report_type == ReportType.YEARLY
    assert report.start_date == date(2024, 1, 1)
    assert report.end_date == date(2024, 12, 31)


def test_generate_by_date():
    """测试根据日期生成年报"""
    generator = YearlyReportGenerator()
    report_date = date(2025, 6, 15)

    report = generator.generate_by_date(report_date)

    assert report.report_type == ReportType.YEARLY
    assert report.start_date == date(2025, 1, 1)
    assert report.end_date == date(2025, 12, 31)


def test_get_yearly_summary():
    """测试获取年报摘要"""
    generator = YearlyReportGenerator()
    report = generator.generate(2025)

    summary = generator.get_yearly_summary(report)

    assert "报表年份" in summary
    assert "期初余额" in summary
    assert "期末余额" in summary
    assert "年度盈亏" in summary
    assert "年度收益率" in summary
    assert "交易次数" in summary
    assert "持仓数量" in summary


def test_get_yearly_stats():
    """测试获取年度统计"""
    generator = YearlyReportGenerator()
    stats = generator.get_yearly_stats(2025)

    assert "year" in stats
    assert stats["year"] == 2025
    assert "total_trading_days" in stats
    assert "total_pnl" in stats
    assert "avg_monthly_pnl" in stats
    assert "positive_months" in stats
    assert "negative_months" in stats
    assert stats["positive_months"] + stats["negative_months"] == 12


def test_get_monthly_breakdown():
    """测试获取月度分解"""
    generator = YearlyReportGenerator()
    breakdown = generator.get_monthly_breakdown(2025)

    assert len(breakdown) == 12

    # 验证1月数据
    assert "2025年01月" in breakdown
    jan_data = breakdown["2025年01月"]
    assert "start_date" in jan_data
    assert "end_date" in jan_data
    assert "daily_pnl" in jan_data
    assert "total_trades" in jan_data


def test_empty_yearly_report():
    """测试空年报"""
    generator = YearlyReportGenerator()
    report = generator.generate(2025)

    assert report.daily_pnl == 0.0
    assert report.daily_pnl_ratio == 0.0
    assert len(report.trades) == 0


def test_yearly_report_monthly_generator_integration():
    """测试年报生成器与月报生成器集成"""
    generator = YearlyReportGenerator()

    # 验证内部月报生成器
    assert generator.monthly_generator is not None
    monthly_report = generator.monthly_generator.generate(2025, 1)
    assert monthly_report.report_type == ReportType.MONTHLY


def test_yearly_stats_total_trading_days():
    """测试年度统计交易日总数"""
    generator = YearlyReportGenerator()
    stats = generator.get_yearly_stats(2025)

    # 2025年有约260个交易日（排除周末）
    assert stats["total_trading_days"] > 0
    assert 250 <= stats["total_trading_days"] <= 265


def test_monthly_breakdown_keys():
    """测试月度分解键名"""
    generator = YearlyReportGenerator()
    breakdown = generator.get_monthly_breakdown(2025)

    expected_keys = [
        "2025年01月", "2025年02月", "2025年03月", "2025年04月",
        "2025年05月", "2025年06月", "2025年07月", "2025年08月",
        "2025年09月", "2025年10月", "2025年11月", "2025年12月"
    ]

    for key in expected_keys:
        assert key in breakdown
