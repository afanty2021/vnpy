"""
事件驱动策略测试
"""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from vnpy_china_strategy.event_driven.models import EarningsForecast, PolicyEvent
from vnpy_china_strategy.event_driven.earnings import EarningsForecastStrategy
from vnpy_china_strategy.event_driven.policy import PolicyEventStrategy


class TestEventDrivenModels(unittest.TestCase):
    """测试事件驱动数据模型"""

    def test_earnings_forecast_creation(self):
        """测试业绩预告创建"""
        forecast = EarningsForecast(
            symbol="000001",
            name="平安银行",
            forecast_date=date(2026, 2, 20),
            report_date=date(2026, 3, 31),
            earnings_type="预增",
            earnings_range_low=Decimal("1000000000"),
            earnings_range_high=Decimal("1500000000"),
            yoy_change=0.5,
        )

        self.assertEqual(forecast.symbol, "000001")
        self.assertEqual(forecast.earnings_type, "预增")

    def test_policy_event_creation(self):
        """测试政策事件创建"""
        event = PolicyEvent(
            event_date=date(2026, 2, 20),
            policy_title="新能源政策发布",
            related_sectors=["电气设备", "汽车", "有色金属"],
            impact_level="正面",
            keywords=["新能源", "碳中和"],
        )

        self.assertEqual(len(event.related_sectors), 3)
        self.assertEqual(event.impact_level, "正面")


class TestEarningsForecastStrategy(unittest.TestCase):
    """测试业绩预告策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = EarningsForecastStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_earnings",
            vt_symbol="000001.SZSE",
            setting={
                "event_types": ["预增", "扭亏", "续盈"],
                "min_yoy_change": 0.2,
                "holding_days": 5,
            }
        )

        self.assertEqual(len(strategy.event_types), 3)


class TestPolicyEventStrategy(unittest.TestCase):
    """测试政策事件策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = PolicyEventStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_policy",
            vt_symbol="000001.SZSE",
            setting={
                "keywords": ["新能源", "半导体", "医药"],
                "impact_threshold": 0.5,
                "sector_exposure": 0.15,
            }
        )

        self.assertEqual(len(strategy.keywords), 3)


if __name__ == "__main__":
    unittest.main()
