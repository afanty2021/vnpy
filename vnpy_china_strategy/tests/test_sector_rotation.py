"""
板块轮动策略测试
"""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from vnpy_china_strategy.sector_rotation.models import SectorStrength, RotationSignal
from vnpy_china_strategy.sector_rotation.strength import SectorStrengthStrategy
from vnpy_china_strategy.sector_rotation.signal import RotationSignalStrategy


class TestSectorRotationModels(unittest.TestCase):
    """测试板块轮动数据模型"""

    def test_sector_strength_creation(self):
        """测试板块强度创建"""
        strength = SectorStrength(
            sector="银行",
            strength=1.5,
            momentum_5d=2.0,
            momentum_20d=5.0,
            momentum_60d=10.0,
            fund_flow=Decimal("1000000000"),
            rank=1,
        )

        self.assertEqual(strength.sector, "银行")
        self.assertEqual(strength.rank, 1)
        self.assertGreater(strength.strength, 1.0)

    def test_rotation_signal_creation(self):
        """测试轮动信号创建"""
        signal = RotationSignal(
            from_sector="房地产",
            to_sector="银行",
            signal_date=date(2026, 2, 20),
            confidence=0.8,
            reason="动量反转",
        )

        self.assertEqual(signal.from_sector, "房地产")
        self.assertEqual(signal.to_sector, "银行")


class TestSectorStrengthStrategy(unittest.TestCase):
    """测试板块强度策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = SectorStrengthStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_sector_strength",
            vt_symbol="000001.SZSE",
            setting={
                "rotation_period": 20,
                "top_n": 3,
                "momentum_days": 60,
                "min_strength": 1.0,
            }
        )

        self.assertEqual(strategy.rotation_period, 20)
        self.assertEqual(strategy.top_n, 3)


class TestRotationSignalStrategy(unittest.TestCase):
    """测试轮动信号策略"""

    def setUp(self):
        """设置测试环境"""
        self.cta_engine = Mock()

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = RotationSignalStrategy(
            cta_engine=self.cta_engine,
            strategy_name="test_rotation",
            vt_symbol="000001.SZSE",
            setting={
                "rebalance_threshold": 0.2,
                "momentum_lookback": 20,
            }
        )

        self.assertEqual(strategy.rebalance_threshold, 0.2)


if __name__ == "__main__":
    unittest.main()
