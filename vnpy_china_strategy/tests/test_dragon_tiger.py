"""
龙虎榜策略测试

测试机构席位追踪、游资策略和跟随策略。
"""

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from vnpy_china_strategy.dragon_tiger.models import DragonTigerRecord
from vnpy_china_strategy.dragon_tiger.institution import InstitutionTrackerStrategy
from vnpy_china_strategy.dragon_tiger.broker import BrokerMoneyStrategy
from vnpy_china_strategy.dragon_tiger.follow import FollowStrategy


class TestDragonTigerModels(unittest.TestCase):
    """测试龙虎榜数据模型"""

    def test_dragon_tiger_record_creation(self):
        """测试龙虎榜记录创建"""
        record = DragonTigerRecord(
            trade_date=date(2026, 2, 20),
            symbol="000001",
            name="平安银行",
            close_price=15.50,
            change_pct=5.23,
            institution_buy=Decimal("20000000"),
            institution_sell=Decimal("5000000"),
            institution_net=Decimal("15000000"),
            institution_count=3,
            broker_buy=Decimal("10000000"),
            broker_sell=Decimal("2000000"),
            broker_net=Decimal("8000000"),
            total_buy=Decimal("30000000"),
            total_sell=Decimal("7000000"),
            net_buy=Decimal("23000000"),
            turnover=Decimal("500000000"),
            turnover_rate=8.5,
        )

        self.assertEqual(record.symbol, "000001")
        self.assertEqual(record.name, "平安银行")
        self.assertEqual(record.institution_count, 3)
        self.assertGreater(record.institution_net, 0)

    def test_dragon_tiger_record_to_dict(self):
        """测试龙虎榜记录转字典"""
        record = DragonTigerRecord(
            trade_date=date(2026, 2, 20),
            symbol="000001",
            name="测试",
            close_price=10.0,
            change_pct=1.0,
        )

        data = record.to_dict()
        self.assertEqual(data["symbol"], "000001")
        self.assertEqual(data["name"], "测试")


class TestInstitutionTrackerStrategy(unittest.TestCase):
    """测试机构席位追踪策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()
        self.cta_engine.get_account = Mock(return_value=Mock(
            available=1000000,
            balance=1000000,
            pre_balance=1000000
        ))

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = InstitutionTrackerStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_institution",
            vt_symbol="000001.SZSE",
            setting={
                "institution_threshold": 1000,
                "min_institution_count": 3,
                "holding_days": 5,
                "position_ratio": 0.1,
            }
        )

        self.assertEqual(strategy.institution_threshold, 1000)
        self.assertEqual(strategy.min_institution_count, 3)
        self.assertEqual(strategy.holding_days, 5)

    def test_check_buy_signals(self):
        """测试买入信号检查"""
        strategy = InstitutionTrackerStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_institution",
            vt_symbol="000001.SZSE",
            setting={}
        )

        # 创建符合买入条件的记录
        record = DragonTigerRecord(
            trade_date=date(2026, 2, 20),
            symbol="000001",
            name="测试",
            close_price=15.0,
            change_pct=5.0,
            institution_buy=Decimal("20000000"),
            institution_sell=Decimal("5000000"),
            institution_net=Decimal("15000000"),  # 1500万 > 1000万
            institution_count=3,  # >= 3
        )

        signals = [record]
        buy_signals = strategy._check_buy_signals(signals)

        # 应该筛选出信号
        self.assertEqual(len(buy_signals), 1)
        self.assertEqual(buy_signals[0].symbol, "000001")

    def test_check_buy_signals_insufficient(self):
        """测试买入信号检查 - 不符合条件"""
        strategy = InstitutionTrackerStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_institution",
            vt_symbol="000001.SZSE",
            setting={}
        )

        # 创建不符合买入条件的记录
        record = DragonTigerRecord(
            trade_date=date(2026, 2, 20),
            symbol="000001",
            name="测试",
            close_price=15.0,
            change_pct=5.0,
            institution_buy=Decimal("5000000"),
            institution_sell=Decimal("4000000"),
            institution_net=Decimal("1000000"),  # 1000万 <= 1000万
            institution_count=2,  # < 3
        )

        signals = [record]
        buy_signals = strategy._check_buy_signals(signals)

        # 不应该筛选出信号
        self.assertEqual(len(buy_signals), 0)


class TestBrokerMoneyStrategy(unittest.TestCase):
    """测试游资策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = BrokerMoneyStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_broker",
            vt_symbol="000001.SZSE",
            setting={
                "broker_threshold": 500,
                "broker_ratio": 0.6,
                "holding_days": 3,
            }
        )

        self.assertEqual(strategy.broker_threshold, 500)
        self.assertEqual(strategy.broker_ratio, 0.6)


class TestFollowStrategy(unittest.TestCase):
    """测试跟随策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = FollowStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_follow",
            vt_symbol="000001.SZSE",
            setting={
                "appear_count": 2,
                "follow_days": 10,
                "pullback_ratio": 0.05,
            }
        )

        self.assertEqual(strategy.appear_count, 2)
        self.assertEqual(strategy.follow_days, 10)


if __name__ == "__main__":
    unittest.main()
