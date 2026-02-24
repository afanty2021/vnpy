"""
可转债策略测试
"""

import unittest
from datetime import date
from unittest.mock import Mock

from vnpy_china_strategy.convertible.models import ConvertibleBond, ConvertibleArbitragePosition
from vnpy_china_strategy.convertible.arbitrage import ConvertibleArbitrageStrategy


class TestConvertibleModels(unittest.TestCase):
    """测试可转债数据模型"""

    def test_convertible_bond_creation(self):
        """测试可转债创建"""
        cb = ConvertibleBond(
            symbol="113009",
            name="广汽转债",
            stock_symbol="601238",
            stock_name="广汽集团",
            cb_price=120.5,
            stock_price=12.8,
            conversion_price=14.0,
            conversion_value=91.43,
            conversion_ratio=7.1428,
            premium_rate=-3.5,
            pure_bond_value=105.0,
            yield_to_maturity=1.2,
            maturity_date=date(2027, 6, 30),
            rating="AAA",
            call_price=18.2,
            volume=50000000,
            amount=600000000,
        )

        self.assertEqual(cb.symbol, "113009")
        self.assertEqual(cb.stock_symbol, "601238")
        self.assertLess(cb.premium_rate, 0)

    def test_convertible_arbitrage_position_creation(self):
        """测试套利持仓创建"""
        position = ConvertibleArbitragePosition(
            cb_symbol="113009",
            stock_symbol="601238",
            cb_volume=100,
            stock_volume=714,
            entry_cb_price=120.0,
            entry_stock_price=12.5,
            entry_datetime=date(2026, 2, 20),
        )

        self.assertEqual(position.cb_symbol, "113009")
        self.assertGreater(position.stock_volume, 0)


class TestConvertibleArbitrageStrategy(unittest.TestCase):
    """测试可转债套利策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = ConvertibleArbitrageStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_convertible",
            vt_symbol="113009.SZSE",
            setting={
                "premium_threshold": -5.0,
                "min_conversion_value": 100.0,
                "trend_days": 20,
            }
        )

        self.assertEqual(strategy.premium_threshold, -5.0)
        self.assertEqual(strategy.min_conversion_value, 100.0)


if __name__ == "__main__":
    unittest.main()
