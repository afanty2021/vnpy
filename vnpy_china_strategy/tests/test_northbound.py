"""
北向资金策略测试

测试北向资金流向、持股变化和板块偏好策略。
"""

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

from vnpy_china_strategy.northbound.models import NorthboundFlow, StockHoldingChange
from vnpy_china_strategy.northbound.flow import NorthboundFlowStrategy
from vnpy_china_strategy.northbound.holding import HoldingChangeStrategy
from vnpy_china_strategy.northbound.sector import SectorPreferenceStrategy


class TestNorthboundModels(unittest.TestCase):
    """测试北向资金数据模型"""

    def test_northbound_flow_creation(self):
        """测试北向资金流向创建"""
        flow = NorthboundFlow(
            trade_date=date(2026, 2, 20),
            net_inflow=Decimal("1500000000"),
            inflow=Decimal("5000000000"),
            outflow=Decimal("3500000000"),
            balance=Decimal("20000000000"),
        )

        self.assertEqual(flow.trade_date, date(2026, 2, 20))
        self.assertEqual(flow.net_inflow, Decimal("1500000000"))

    def test_stock_holding_change_creation(self):
        """测试持股变化创建"""
        change = StockHoldingChange(
            symbol="000001",
            trade_date=date(2026, 2, 20),
            holding_shares=10000000,
            holding_ratio=0.5,
            change_shares=500000,
            change_ratio=0.05,
            net_inflow=Decimal("10000000"),
        )

        self.assertEqual(change.symbol, "000001")
        self.assertEqual(change.holding_shares, 10000000)


class TestNorthboundFlowStrategy(unittest.TestCase):
    """测试北向资金流向策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()
        account = Mock()
        account.available = 1000000
        self.cta_engine.get_account = Mock(return_value=account)

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = NorthboundFlowStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_flow",
            vt_symbol="510300.SH",
            setting={
                "net_inflow_threshold": 10,
                "market_filter": "沪深300",
                "position_ratio": 0.15,
            }
        )

        self.assertEqual(strategy.net_inflow_threshold, 10)
        self.assertEqual(strategy.market_filter, "沪深300")
        self.assertEqual(strategy.position_ratio, 0.15)


class TestHoldingChangeStrategy(unittest.TestCase):
    """测试持股变化策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = HoldingChangeStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_holding",
            vt_symbol="000001.SZSE",
            setting={
                "change_threshold": 0.05,
                "consecutive_days": 3,
                "min_shares": 1000000,
            }
        )

        self.assertEqual(strategy.change_threshold, 0.05)
        self.assertEqual(strategy.consecutive_days, 3)


class TestSectorPreferenceStrategy(unittest.TestCase):
    """测试板块偏好策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = SectorPreferenceStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_sector",
            vt_symbol="000001.SZSE",
            setting={
                "sector_top_n": 5,
                "sector_change_threshold": 0.03,
            }
        )

        self.assertEqual(strategy.sector_top_n, 5)


if __name__ == "__main__":
    unittest.main()
