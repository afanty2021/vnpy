"""Tests for vnpy_china_backtest module - REQ-006 增强回测系统"""

import sys
sys.path.insert(0, '/Users/berton/Github/vnpy')

import pytest
from datetime import datetime


class TestAStockCost:
    """Test A股交易成本"""

    def test_creation(self):
        """Test cost creation"""
        from vnpy_china_backtest.cost import AStockCost
        cost = AStockCost()
        assert cost is not None


class TestTradingCost:
    """Test trading cost"""

    def test_creation(self):
        """Test trading cost creation"""
        from vnpy_china_backtest.cost import TradingCost
        tc = TradingCost(
            commission=100.0,
            stamp_duty=50.0,
            transfer_fee=10.0,
            handling_fee=5.0,
            total=165.0,
            cost_rate=0.001
        )
        assert tc is not None


class TestCostConfig:
    """Test cost configuration"""

    def test_creation(self):
        """Test config creation"""
        from vnpy_china_backtest.cost import CostConfig
        config = CostConfig()
        assert config is not None


class TestCostCalculator:
    """Test cost calculator"""

    def test_creation(self):
        """Test calculator creation"""
        from vnpy_china_backtest.cost import CostCalculator
        calc = CostCalculator()
        assert calc is not None


class TestSlippageConfig:
    """Test slippage configuration"""

    def test_creation(self):
        """Test slippage config creation"""
        from vnpy_china_backtest.slippage import SlippageConfig
        config = SlippageConfig()
        assert config is not None


class TestSlippageModels:
    """Test slippage models"""

    def test_fixed_slippage_creation(self):
        """Test fixed slippage creation"""
        from vnpy_china_backtest.slippage import FixedSlippage
        model = FixedSlippage()
        assert model is not None

    def test_percent_slippage_creation(self):
        """Test percent slippage creation"""
        from vnpy_china_backtest.slippage import PercentSlippage
        model = PercentSlippage()
        assert model is not None

    def test_impact_cost_slippage_creation(self):
        """Test impact cost slippage creation"""
        from vnpy_china_backtest.slippage import ImpactCostSlippage
        model = ImpactCostSlippage()
        assert model is not None


class TestPriceLimitEngine:
    """Test price limit engine"""

    def test_creation(self):
        """Test engine creation"""
        from vnpy_china_backtest.rules.price_limit import PriceLimitEngine
        engine = PriceLimitEngine()
        assert engine is not None


class TestT1Simulator:
    """Test T+1 simulator"""

    def test_creation(self):
        """Test simulator creation"""
        from vnpy_china_backtest.rules.t1_simulator import T1Simulator
        sim = T1Simulator()
        assert sim is not None

    def test_position_record_creation(self):
        """Test position record creation"""
        from vnpy_china_backtest.rules.t1_simulator import PositionRecord

        record = PositionRecord(
            symbol="000001",
            volume=1000,
            available=0,
            frozen=1000,
            avg_price=10.0
        )
        assert record.symbol == "000001"
        assert record.volume == 1000


class TestEnhancedMetrics:
    """Test enhanced metrics"""

    def test_creation(self):
        """Test metrics creation"""
        from vnpy_china_backtest.report.metrics import EnhancedMetrics
        metrics = EnhancedMetrics()
        assert metrics is not None


class TestBacktestConfig:
    """Test backtest configuration"""

    def test_creation(self):
        """Test config creation"""
        from vnpy_china_backtest.config import BacktestConfig
        config = BacktestConfig()
        assert config is not None

    def test_default_values(self):
        """Test default config values"""
        from vnpy_china_backtest.config import BacktestConfig
        config = BacktestConfig()
        # 检查默认值
        assert config.commission_rate > 0
        assert config.initial_capital > 0
