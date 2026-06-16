"""
核心数据模型单元测试
"""

import unittest
from datetime import datetime, date
from vnpy_china_reporting.core.enums import ReportType, PositionSide, RiskLevel, TradeDirection
from vnpy_china_reporting.core.models import (
    TradeRecord,
    PositionRecord,
    AccountData,
    ReportData,
    PositionAnalysis,
    RiskMetrics,
    DailySummary,
    MonthlySummary,
)


class TestEnums(unittest.TestCase):
    """测试枚举类型"""

    def test_report_type(self):
        """测试报表类型枚举"""
        self.assertEqual(ReportType.DAILY.value, "daily")
        self.assertEqual(ReportType.MONTHLY.value, "monthly")
        self.assertEqual(ReportType.YEARLY.value, "yearly")

    def test_position_side(self):
        """测试持仓方向枚举"""
        self.assertEqual(PositionSide.LONG.value, "long")
        self.assertEqual(PositionSide.SHORT.value, "short")

    def test_risk_level(self):
        """测试风险等级枚举"""
        self.assertEqual(RiskLevel.LOW.value, "low")
        self.assertEqual(RiskLevel.MEDIUM.value, "medium")
        self.assertEqual(RiskLevel.HIGH.value, "high")

    def test_trade_direction(self):
        """测试交易方向枚举"""
        self.assertEqual(TradeDirection.BUY.value, "buy")
        self.assertEqual(TradeDirection.SELL.value, "sell")


class TestTradeRecord(unittest.TestCase):
    """测试交易记录数据类"""

    def setUp(self):
        """创建测试数据"""
        self.trade = TradeRecord(
            trade_id="T001",
            symbol="000001",
            direction="buy",
            volume=1000,
            price=10.50,
            amount=10500.0,
            commission=15.75,
            timestamp=datetime(2026, 2, 25, 10, 30, 0)
        )

    def test_trade_record_creation(self):
        """测试交易记录创建"""
        self.assertEqual(self.trade.trade_id, "T001")
        self.assertEqual(self.trade.symbol, "000001")
        self.assertEqual(self.trade.direction, "buy")
        self.assertEqual(self.trade.volume, 1000)
        self.assertEqual(self.trade.price, 10.50)
        self.assertEqual(self.trade.amount, 10500.0)
        self.assertEqual(self.trade.commission, 15.75)

    def test_trade_record_modification(self):
        """测试交易记录修改"""
        self.trade.volume = 2000
        self.trade.price = 11.00
        self.assertEqual(self.trade.volume, 2000)
        self.assertEqual(self.trade.price, 11.00)


class TestPositionRecord(unittest.TestCase):
    """测试持仓记录数据类"""

    def setUp(self):
        """创建测试数据"""
        self.position = PositionRecord(
            symbol="600519",
            name="贵州茅台",
            side=PositionSide.LONG,
            volume=100,
            avg_cost=1800.0,
            current_price=2200.0,
            market_value=220000.0,
            unrealized_pnl=40000.0,
            unrealized_pnl_ratio=0.2222
        )

    def test_position_record_creation(self):
        """测试持仓记录创建"""
        self.assertEqual(self.position.symbol, "600519")
        self.assertEqual(self.position.name, "贵州茅台")
        self.assertEqual(self.position.side, PositionSide.LONG)
        self.assertEqual(self.position.volume, 100)
        self.assertEqual(self.position.avg_cost, 1800.0)
        self.assertEqual(self.position.current_price, 2200.0)
        self.assertEqual(self.position.market_value, 220000.0)

    def test_unrealized_pnl_calculation(self):
        """测试未实现盈亏计算"""
        expected_pnl = (self.position.current_price - self.position.avg_cost) * self.position.volume
        self.assertAlmostEqual(self.position.unrealized_pnl, expected_pnl, places=2)


class TestAccountData(unittest.TestCase):
    """测试账户数据类"""

    def setUp(self):
        """创建测试数据"""
        self.account = AccountData(
            total_equity=1000000.0,
            available_cash=300000.0,
            market_value=700000.0,
            total_pnl=50000.0,
            total_pnl_ratio=0.05,
            commission=2000.0,
            timestamp=datetime(2026, 2, 25, 15, 0, 0)
        )

    def test_account_data_creation(self):
        """测试账户数据创建"""
        self.assertEqual(self.account.total_equity, 1000000.0)
        self.assertEqual(self.account.available_cash, 300000.0)
        self.assertEqual(self.account.market_value, 700000.0)
        self.assertEqual(self.account.total_pnl, 50000.0)

    def test_total_equity_calculation(self):
        """测试总权益计算"""
        expected_equity = self.account.available_cash + self.account.market_value
        self.assertAlmostEqual(expected_equity, 1000000.0, places=2)


class TestReportData(unittest.TestCase):
    """测试报表数据类"""

    def setUp(self):
        """创建测试数据"""
        self.account = AccountData(
            total_equity=1000000.0,
            available_cash=300000.0,
            market_value=700000.0,
            total_pnl=50000.0,
            total_pnl_ratio=0.05,
            commission=2000.0,
            timestamp=datetime(2026, 2, 25, 15, 0, 0)
        )

        self.positions = [
            PositionRecord(
                symbol="600519",
                name="贵州茅台",
                side=PositionSide.LONG,
                volume=100,
                avg_cost=1800.0,
                current_price=2200.0,
                market_value=220000.0,
                unrealized_pnl=40000.0,
                unrealized_pnl_ratio=0.2222
            ),
            PositionRecord(
                symbol="000001",
                name="平安银行",
                side=PositionSide.LONG,
                volume=10000,
                avg_cost=12.0,
                current_price=15.0,
                market_value=150000.0,
                unrealized_pnl=30000.0,
                unrealized_pnl_ratio=0.25
            ),
        ]

        self.trades = [
            TradeRecord(
                trade_id="T001",
                symbol="600519",
                direction="buy",
                volume=100,
                price=1800.0,
                amount=180000.0,
                commission=270.0,
                timestamp=datetime(2026, 2, 20, 10, 30, 0)
            ),
        ]

        self.report = ReportData(
            report_type=ReportType.DAILY,
            start_date=date(2026, 2, 25),
            end_date=date(2026, 2, 25),
            account=self.account,
            positions=self.positions,
            trades=self.trades,
            daily_pnl=10000.0,
            daily_pnl_ratio=0.01
        )

    def test_report_data_creation(self):
        """测试报表数据创建"""
        self.assertEqual(self.report.report_type, ReportType.DAILY)
        self.assertEqual(self.report.start_date, date(2026, 2, 25))
        self.assertEqual(len(self.report.positions), 2)
        self.assertEqual(len(self.report.trades), 1)

    def test_default_values(self):
        """测试默认值"""
        empty_report = ReportData(
            report_type=ReportType.MONTHLY,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            account=self.account
        )
        self.assertEqual(empty_report.positions, [])
        self.assertEqual(empty_report.trades, [])
        self.assertIsNone(empty_report.daily_pnl)  # 权益变化法：期初权益缺失时为 None


class TestPositionAnalysis(unittest.TestCase):
    """测试持仓分析数据类"""

    def test_position_analysis_creation(self):
        """测试持仓分析创建"""
        analysis = PositionAnalysis(
            total_positions=5,
            total_market_value=1000000.0,
            top_holdings=[
                {"symbol": "600519", "name": "贵州茅台", "market_value": 500000.0},
                {"symbol": "000001", "name": "平安银行", "market_value": 300000.0},
            ],
            concentration=0.8,
            industry_distribution={"白酒": 0.5, "银行": 0.3, "科技": 0.2}
        )

        self.assertEqual(analysis.total_positions, 5)
        self.assertEqual(len(analysis.top_holdings), 2)
        self.assertAlmostEqual(analysis.concentration, 0.8)


class TestRiskMetrics(unittest.TestCase):
    """测试风险指标数据类"""

    def test_risk_metrics_creation(self):
        """测试风险指标创建"""
        metrics = RiskMetrics(
            var_95=50000.0,
            volatility=0.15,
            sharpe_ratio=1.5,
            max_drawdown=0.2,
            risk_level=RiskLevel.MEDIUM
        )

        self.assertEqual(metrics.risk_level, RiskLevel.MEDIUM)
        self.assertAlmostEqual(metrics.sharpe_ratio, 1.5)


class TestDailySummary(unittest.TestCase):
    """测试每日摘要数据类"""

    def test_daily_summary_creation(self):
        """测试每日摘要创建"""
        summary = DailySummary(
            date=date(2026, 2, 25),
            total_trades=10,
            buy_trades=6,
            sell_trades=4,
            total_volume=50000,
            total_amount=500000.0,
            total_commission=750.0,
            net_pnl=10000.0
        )

        self.assertEqual(summary.date, date(2026, 2, 25))
        self.assertEqual(summary.total_trades, 10)
        self.assertEqual(summary.buy_trades + summary.sell_trades, summary.total_trades)

    def test_default_values(self):
        """测试默认值"""
        summary = DailySummary(date=date(2026, 2, 25))
        self.assertEqual(summary.total_trades, 0)
        self.assertEqual(summary.buy_trades, 0)


class TestMonthlySummary(unittest.TestCase):
    """测试月度摘要数据类"""

    def test_monthly_summary_creation(self):
        """测试月度摘要创建"""
        summary = MonthlySummary(
            year=2026,
            month=2,
            trading_days=20,
            total_pnl=100000.0,
            total_commission=5000.0,
            total_trades=200,
            avg_daily_pnl=5000.0,
            win_rate=0.6
        )

        self.assertEqual(summary.year, 2026)
        self.assertEqual(summary.month, 2)
        self.assertAlmostEqual(summary.win_rate, 0.6)

    def test_default_values(self):
        """测试默认值"""
        summary = MonthlySummary(year=2026, month=2)
        self.assertEqual(summary.trading_days, 0)
        self.assertEqual(summary.total_pnl, 0.0)


if __name__ == "__main__":
    unittest.main()
