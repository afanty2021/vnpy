"""
日报生成器测试
"""

import pytest
from datetime import date, datetime
from vnpy_china_reporting.report.daily import DailyReportGenerator
from vnpy_china_reporting.core.models import TradeRecord, PositionRecord, AccountData
from vnpy_china_reporting.core.enums import ReportType, PositionSide


def test_daily_report_generator_init():
    """测试日报生成器初始化"""
    generator = DailyReportGenerator()
    assert generator.main_engine is None
    assert generator.report_type == ReportType.DAILY


def test_daily_report_generator_with_main_engine():
    """测试带主引擎的日报生成器"""
    mock_engine = object()
    generator = DailyReportGenerator(main_engine=mock_engine)
    assert generator.main_engine is mock_engine


def test_generate_daily_report():
    """测试生成日报"""
    generator = DailyReportGenerator()
    report_date = date(2025, 1, 15)

    report = generator.generate(report_date)

    assert report.report_type == ReportType.DAILY
    assert report.start_date == report_date
    assert report.end_date == report_date
    assert isinstance(report.account, AccountData)
    assert isinstance(report.trades, list)
    assert isinstance(report.positions, list)


def test_generate_daily_report_today():
    """测试生成今日日报"""
    generator = DailyReportGenerator()
    today = date.today()

    report = generator.generate(today)

    assert report.start_date == today
    assert report.end_date == today


def test_get_trades_detail():
    """测试获取交易明细"""
    generator = DailyReportGenerator()
    report_date = date(2025, 1, 15)

    # 测试空交易明细
    details = generator.get_trades_detail(report_date)
    assert isinstance(details, list)
    assert len(details) == 0


def test_get_summary():
    """测试获取日报摘要"""
    generator = DailyReportGenerator()
    report_date = date(2025, 1, 15)

    report = generator.generate(report_date)
    summary = generator.get_summary(report)

    assert "报表日期" in summary
    assert "期初余额" in summary
    assert "期末余额" in summary
    assert "当日盈亏" in summary
    assert "收益率" in summary
    assert "交易次数" in summary
    assert "持仓数量" in summary


def test_daily_pnl_calculation():
    """测试日报盈亏计算"""
    # 创建一个带模拟数据的生成器
    generator = DailyReportGenerator()

    # 模拟买入交易
    class MockMainEngine:
        def get_trades(self):
            return [
                MockTrade(
                    symbol="000001",
                    direction=MockDirection("buy"),
                    volume=1000,
                    price=10.0,
                    timestamp=datetime(2025, 1, 15, 10, 0, 0)
                )
            ]

        def get_positions(self):
            return []

        def get_account(self):
            return MockAccount()

    class MockTrade:
        def __init__(self, symbol, direction, volume, price, timestamp):
            self.symbol = symbol
            self.direction = direction
            self.volume = volume
            self.price = price
            self.timestamp = timestamp

    class MockDirection:
        def __init__(self, value):
            self.value = value

    class MockAccount:
        balance = 1000000.0
        available = 500000.0
        position_value = 500000.0
        pnl = 0.0
        pnl_ratio = 0.0
        commission = 0.0

    generator_with_data = DailyReportGenerator(main_engine=MockMainEngine())
    report = generator_with_data.generate(date(2025, 1, 15))

    # 验证数据
    assert report.report_type == ReportType.DAILY
    assert isinstance(report.daily_pnl, float)


def test_empty_daily_report():
    """测试空日报"""
    generator = DailyReportGenerator()
    report = generator.generate(date(2025, 1, 1))

    assert report.daily_pnl == 0.0
    assert report.daily_pnl_ratio == 0.0
    assert len(report.trades) == 0


def test_position_ratio_calculation():
    """测试持仓比例计算"""
    generator = DailyReportGenerator()
    report = generator.generate(date(2025, 1, 15))

    # 验证市值和比例
    assert report.account.market_value >= 0
