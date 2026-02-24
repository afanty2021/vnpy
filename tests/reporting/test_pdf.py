"""
PDF导出器单元测试
"""

import pytest
import os
import tempfile
from datetime import date, datetime

from vnpy_china_reporting.core.models import (
    ReportData, PositionAnalysis, PositionRecord, AccountData
)
from vnpy_china_reporting.core.enums import ReportType, PositionSide
from vnpy_china_reporting.export import PDFExporter


class TestPDFExporter:
    """PDF导出器测试类"""

    @pytest.fixture
    def exporter(self):
        """创建导出器实例"""
        return PDFExporter()

    @pytest.fixture
    def sample_report(self):
        """创建示例报表数据"""
        account = AccountData(
            total_equity=1000000.0,
            available_cash=500000.0,
            market_value=500000.0,
            total_pnl=50000.0,
            total_pnl_ratio=0.05,
            commission=1000.0,
            timestamp=datetime.now()
        )

        positions = [
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
        ]

        from vnpy_china_reporting.core.models import TradeRecord
        trades = [
            TradeRecord(
                trade_id="T001",
                symbol="000001",
                direction="buy",
                volume=10000,
                price=10.5,
                amount=105000.0,
                commission=50.0,
                timestamp=datetime.now()
            ),
        ]

        report = ReportData(
            report_type=ReportType.DAILY,
            start_date=date(2026, 2, 25),
            end_date=date(2026, 2, 25),
            account=account,
            positions=positions,
            trades=trades,
            daily_pnl=50000.0,
            daily_pnl_ratio=0.05
        )

        return report

    @pytest.fixture
    def sample_analysis(self):
        """创建示例持仓分析数据"""
        analysis = PositionAnalysis(
            total_positions=5,
            total_market_value=1000000.0,
            top_holdings=[],
            concentration=0.5,
            industry_distribution={
                "银行": {
                    "value": 500000.0,
                    "ratio": 0.5,
                    "count": 2,
                    "avg_pnl": 2500.0
                }
            }
        )
        return analysis

    def test_exporter_init(self, exporter):
        """测试导出器初始化"""
        assert exporter is not None
        assert exporter.page_size == "A4"
        assert exporter.orientation == "portrait"

    def test_export_daily_report(self, exporter, sample_report):
        """测试导出日报"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_daily.pdf")

            result = exporter.export_daily_report(sample_report, filepath)

            # 如果reportlab可用，检查文件是否生成
            if exporter._reportlab_available:
                assert result is True
                assert os.path.exists(filepath)
            else:
                # 如果reportlab不可用，应该生成txt文件
                txt_filepath = filepath.replace('.pdf', '.txt')
                assert result is True

    def test_export_monthly_report(self, exporter, sample_report):
        """测试导出月报"""
        # 修改为月报类型
        sample_report.report_type = ReportType.MONTHLY
        sample_report.start_date = date(2026, 2, 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_monthly.pdf")

            result = exporter.export_monthly_report(sample_report, filepath)

            if exporter._reportlab_available:
                assert result is True
                assert os.path.exists(filepath)
            else:
                assert result is True

    def test_export_position_analysis(self, exporter, sample_analysis):
        """测试导出持仓分析"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_analysis.pdf")

            result = exporter.export_position_analysis(sample_analysis, filepath)

            if exporter._reportlab_available:
                assert result is True
                assert os.path.exists(filepath)
            else:
                assert result is True

    def test_export_with_empty_positions(self, exporter, sample_report):
        """测试空持仓情况"""
        sample_report.positions = []

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_empty.pdf")

            result = exporter.export_daily_report(sample_report, filepath)

            if exporter._reportlab_available:
                assert result is True
                assert os.path.exists(filepath)

    def test_export_with_empty_trades(self, exporter, sample_report):
        """测试无交易情况"""
        sample_report.trades = []

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_no_trades.pdf")

            result = exporter.export_daily_report(sample_report, filepath)

            if exporter._reportlab_available:
                assert result is True

    def test_fallback_export(self, exporter, sample_report):
        """测试回退导出方法"""
        # 模拟reportlab不可用的情况
        original_available = exporter._reportlab_available
        exporter._reportlab_available = False

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_fallback.pdf")

            result = exporter.export_daily_report(sample_report, filepath)

            # 应该成功生成txt文件
            assert result is True
            txt_filepath = filepath.replace('.pdf', '.txt')
            assert os.path.exists(txt_filepath)

        exporter._reportlab_available = original_available
