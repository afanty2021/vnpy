"""
报表生成器基类测试
"""

import pytest
from datetime import date, datetime
from vnpy_china_reporting.report.base import BaseReportGenerator
from vnpy_china_reporting.core.models import TradeRecord, PositionRecord, AccountData
from vnpy_china_reporting.core.enums import ReportType, PositionSide


class MockReportGenerator(BaseReportGenerator):
    """模拟报表生成器，用于测试基类"""

    def generate(self, report_date: date):
        """实现抽象方法"""
        from vnpy_china_reporting.core.models import ReportData
        return ReportData(
            report_type=ReportType.DAILY,
            start_date=report_date,
            end_date=report_date,
            account=self.get_account(),
            positions=self.get_positions(),
            trades=self.get_trades(report_date, report_date),
            daily_pnl=0.0,
            daily_pnl_ratio=0.0
        )


def test_base_report_generator_init():
    """测试基类初始化"""
    generator = MockReportGenerator()
    assert generator.main_engine is None
    assert generator.data_cache == {}


def test_base_report_generator_with_main_engine():
    """测试带主引擎的初始化"""
    mock_engine = object()
    generator = MockReportGenerator(main_engine=mock_engine)
    assert generator.main_engine is mock_engine


def test_get_trades_empty():
    """测试获取交易记录（空数据）"""
    generator = MockReportGenerator()
    trades = generator.get_trades(date(2025, 1, 1), date(2025, 1, 31))
    assert isinstance(trades, list)


def test_get_positions_empty():
    """测试获取持仓（空数据）"""
    generator = MockReportGenerator()
    positions = generator.get_positions()
    assert isinstance(positions, list)


def test_get_account():
    """测试获取账户数据"""
    generator = MockReportGenerator()
    account = generator.get_account()
    assert isinstance(account, AccountData)
    assert account.total_equity == 1000000.0
    assert account.available_cash == 500000.0


def test_calculate_daily_pnl():
    """测试计算当日盈亏"""
    generator = MockReportGenerator()

    trades = [
        TradeRecord(
            trade_id="1",
            symbol="000001",
            direction="buy",
            volume=100,
            price=10.0,
            amount=1000.0,
            commission=5.0,
            timestamp=datetime.now()
        ),
        TradeRecord(
            trade_id="2",
            symbol="000001",
            direction="sell",
            volume=100,
            price=11.0,
            amount=1100.0,
            commission=5.0,
            timestamp=datetime.now()
        )
    ]

    pnl = generator.calculate_daily_pnl(trades)
    # sell(1100) - buy(1000) - commission(10) = 90
    assert pnl == 90.0


def test_calculate_daily_pnl_no_trades():
    """测试无交易时的盈亏计算"""
    generator = MockReportGenerator()
    pnl = generator.calculate_daily_pnl([])
    assert pnl == 0.0


def test_calculate_position_weights():
    """测试计算持仓权重"""
    generator = MockReportGenerator()

    positions = [
        PositionRecord(
            symbol="000001",
            name="股票1",
            side=PositionSide.LONG,
            volume=1000,
            avg_cost=10.0,
            current_price=11.0,
            market_value=11000.0,
            unrealized_pnl=1000.0,
            unrealized_pnl_ratio=0.0
        ),
        PositionRecord(
            symbol="000002",
            name="股票2",
            side=PositionSide.LONG,
            volume=1000,
            avg_cost=20.0,
            current_price=19.0,
            market_value=19000.0,
            unrealized_pnl=-1000.0,
            unrealized_pnl_ratio=0.0
        )
    ]

    total_value = 30000.0
    generator.calculate_position_weights(positions, total_value)

    assert positions[0].unrealized_pnl_ratio == pytest.approx(11000 / 30000)
    assert positions[1].unrealized_pnl_ratio == pytest.approx(19000 / 30000)


def test_clear_cache():
    """测试清空缓存"""
    generator = MockReportGenerator()
    generator.data_cache = {"key": "value"}
    generator.clear_cache()
    assert generator.data_cache == {}


def test_get_mock_account_values():
    """测试模拟账户数据值"""
    generator = MockReportGenerator()
    account = generator.get_account()

    assert account.total_equity > 0
    assert account.available_cash >= 0
    assert account.market_value >= 0
    assert isinstance(account.timestamp, datetime)
