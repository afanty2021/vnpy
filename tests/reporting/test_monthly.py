"""
月报生成器测试
"""

import pytest
from datetime import date
from vnpy_china_reporting.report.monthly import MonthlyReportGenerator
from vnpy_china_reporting.core.enums import ReportType


def test_monthly_report_generator_init():
    """测试月报生成器初始化"""
    generator = MonthlyReportGenerator()
    assert generator.main_engine is None
    assert generator.report_type == ReportType.MONTHLY
    assert generator.daily_generator is not None


def test_monthly_report_generator_with_main_engine():
    """测试带主引擎的月报生成器"""
    mock_engine = object()
    generator = MonthlyReportGenerator(main_engine=mock_engine)
    assert generator.main_engine is mock_engine


def test_generate_monthly_report():
    """测试生成月报"""
    generator = MonthlyReportGenerator()
    year = 2025
    month = 1

    report = generator.generate(year, month)

    assert report.report_type == ReportType.MONTHLY
    assert report.start_date == date(2025, 1, 1)
    assert report.end_date == date(2025, 1, 31)
    assert isinstance(report.account.total_equity, float)


def test_generate_monthly_report_february():
    """测试生成二月月报（考虑闰年）"""
    generator = MonthlyReportGenerator()
    year = 2024  # 闰年
    month = 2

    report = generator.generate(year, month)

    assert report.report_type == ReportType.MONTHLY
    assert report.end_date == date(2024, 2, 29)


def test_generate_monthly_report_non_leap_year():
    """测试生成非闰年二月月报"""
    generator = MonthlyReportGenerator()
    year = 2025  # 非闰年
    month = 2

    report = generator.generate(year, month)

    assert report.report_type == ReportType.MONTHLY
    assert report.end_date == date(2025, 2, 28)


def test_generate_by_date():
    """测试根据日期生成月报"""
    generator = MonthlyReportGenerator()
    report_date = date(2025, 6, 15)

    report = generator.generate_by_date(report_date)

    assert report.report_type == ReportType.MONTHLY
    assert report.start_date == date(2025, 6, 1)
    assert report.end_date == date(2025, 6, 30)


def test_get_trading_days():
    """测试获取交易日"""
    generator = MonthlyReportGenerator()

    # 2025年1月应该有大约21-22个交易日（排除周末）
    trading_days = generator.get_trading_days(2025, 1)
    assert len(trading_days) > 0
    assert all(d.weekday() < 5 for d in trading_days)


def test_get_trading_days_january():
    """测试获取1月交易日"""
    generator = MonthlyReportGenerator()
    trading_days = generator.get_trading_days(2025, 1)

    # 2025年1月有31天，排除周末后有23天
    assert len(trading_days) == 23


def test_get_trading_days_february():
    """测试获取2月交易日"""
    generator = MonthlyReportGenerator()

    # 2025年2月有28天，排除周末后大约20天
    trading_days = generator.get_trading_days(2025, 2)
    assert 19 <= len(trading_days) <= 21


def test_get_monthly_summary():
    """测试获取月报摘要"""
    generator = MonthlyReportGenerator()
    report = generator.generate(2025, 1)

    summary = generator.get_monthly_summary(report)

    assert "报表月份" in summary
    assert "期初余额" in summary
    assert "期末余额" in summary
    assert "月度盈亏" in summary
    assert "月度收益率" in summary
    assert "交易次数" in summary
    assert "持仓数量" in summary


def test_get_monthly_stats():
    """测试获取月度统计"""
    generator = MonthlyReportGenerator()
    stats = generator.get_monthly_stats(2025, 1)

    assert "trading_days" in stats
    assert "total_pnl" in stats
    assert "avg_daily_pnl" in stats
    assert "positive_days" in stats
    assert "negative_days" in stats
    assert stats["trading_days"] > 0


def test_empty_monthly_report():
    """测试空月报"""
    generator = MonthlyReportGenerator()
    report = generator.generate(2025, 1)

    assert report.daily_pnl == 0.0
    assert report.daily_pnl_ratio == 0.0
    assert len(report.trades) == 0


def test_monthly_report_daily_generator_integration():
    """测试月报生成器与日报生成器集成"""
    generator = MonthlyReportGenerator()

    # 验证内部日报生成器
    assert generator.daily_generator is not None
    daily_report = generator.daily_generator.generate(date(2025, 1, 15))
    assert daily_report.report_type == ReportType.DAILY
