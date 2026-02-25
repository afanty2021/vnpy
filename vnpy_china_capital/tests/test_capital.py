"""Tests for vnpy_china_capital module - REQ-008 资金管理"""

import sys
sys.path.insert(0, '/Users/berton/Github/vnpy')

import pytest
from datetime import datetime


class TestCompoundEquity:
    """Test compound equity calculator"""

    def test_creation(self):
        """Test compound equity calculator creation"""
        from vnpy_china_capital.equity.compound import CompoundGrowthCalculator
        calc = CompoundGrowthCalculator()
        assert calc is not None


class TestEquityCurve:
    """Test equity curve calculator"""

    def test_creation(self):
        """Test equity curve creation"""
        from vnpy_china_capital.equity.curve import EquityCurveManager
        curve = EquityCurveManager()
        assert curve is not None


class TestDrawdownCalculator:
    """Test drawdown calculator"""

    def test_creation(self):
        """Test drawdown calculator creation"""
        from vnpy_china_capital.equity.drawdown import DrawdownController
        calc = DrawdownController()
        assert calc is not None


class TestDynamicPosition:
    """Test dynamic position sizing"""

    def test_creation(self):
        """Test dynamic position creation"""
        from vnpy_china_capital.position.dynamic import DynamicPosition
        pos = DynamicPosition()
        assert pos is not None


class TestEqualWeightPosition:
    """Test equal weight position sizing"""

    def test_creation(self):
        """Test equal weight position creation"""
        from vnpy_china_capital.position.equal_weight import EqualWeightPosition
        pos = EqualWeightPosition()
        assert pos is not None


class TestRiskParityPosition:
    """Test risk parity position sizing"""

    def test_creation(self):
        """Test risk parity position creation"""
        from vnpy_china_capital.position.risk_parity import RiskParityPosition
        pos = RiskParityPosition()
        assert pos is not None
