"""
单元测试：因子基类和A股因子

测试 vnpy_china_ml.factors 模块中定义的所有因子类
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from vnpy_china_ml.factors import (
    BaseFactor,
    DragonTigerFactor,
    NorthboundFactor,
    SectorRotationFactor,
)
from vnpy_china_ml.utils.types import FactorType


# ==================== 测试 BaseFactor ====================

class TestBaseFactor:
    """测试因子基类"""

    def test_base_factor_creation(self):
        """测试因子基类创建"""
        # 创建一个继承BaseFactor的具体因子用于测试
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series([1.0], index=data.index)

        factor = TestFactor("test", FactorType.TECHNICAL, lookback_days=30)
        assert factor.name == "test"
        assert factor.factor_type == FactorType.TECHNICAL
        assert factor.lookback_days == 30

    def test_validate_data_with_empty_data(self):
        """测试空数据验证"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series()

        factor = TestFactor("test", FactorType.TECHNICAL)
        assert factor.validate_data(pd.DataFrame()) is False
        assert factor.validate_data(None) is False

    def test_validate_data_with_valid_data(self):
        """测试有效数据验证"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series([1.0], index=data.index)

        factor = TestFactor("test", FactorType.TECHNICAL)
        data = pd.DataFrame({"symbol": ["000001.SZ"], "close": [10.0]})
        assert factor.validate_data(data) is True

    def test_get_lookback_days(self):
        """测试获取回看天数"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series()

        factor = TestFactor("test", FactorType.TECHNICAL, lookback_days=50)
        assert factor.get_lookback_days() == 50

    def test_set_lookback_days(self):
        """测试设置回看天数"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series()

        factor = TestFactor("test", FactorType.TECHNICAL)
        factor.set_lookback_days(100)
        assert factor.get_lookback_days() == 100

    def test_set_lookback_days_invalid(self):
        """测试设置无效回看天数"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series()

        factor = TestFactor("test", FactorType.TECHNICAL)
        with pytest.raises(ValueError, match="lookback_days必须大于0"):
            factor.set_lookback_days(0)

    def test_get_required_columns(self):
        """测试获取所需列"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series()

        factor = TestFactor("test", FactorType.TECHNICAL)
        required = factor.get_required_columns()
        assert "symbol" in required
        assert "datetime" in required
        assert "close" in required

    def test_repr(self):
        """测试字符串表示"""
        class TestFactor(BaseFactor):
            def calculate(self, data: pd.DataFrame) -> pd.Series:
                return pd.Series()

        factor = TestFactor("test_factor", FactorType.TECHNICAL, lookback_days=20)
        repr_str = repr(factor)
        assert "test_factor" in repr_str
        assert "technical" in repr_str


# ==================== 测试 DragonTigerFactor ====================

class TestDragonTigerFactor:
    """测试龙虎榜因子"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        dates = pd.date_range(start="2025-01-01", periods=10, freq="D")
        return pd.DataFrame({
            "symbol": ["000001.SZ"] * 10,
            "datetime": dates,
            "institution_buy": np.random.randn(10) * 1000000 + 500000,
            "institution_sell": np.random.randn(10) * 1000000 + 400000,
            "buy_amount": np.random.randn(10) * 10000000 + 5000000,
            "sell_amount": np.random.randn(10) * 10000000 + 4000000,
            "volume": np.random.randint(1000000, 10000000, 10),
            "float_share": np.random.randint(10000000, 100000000, 10),
        })

    def test_creation(self):
        """测试龙虎榜因子创建"""
        factor = DragonTigerFactor()
        assert factor.name == "dragon_tiger"
        assert factor.factor_type == FactorType.DRAGON_TIGER
        assert factor.lookback_days == 20

    def test_creation_with_custom_lookback(self):
        """测试自定义回看天数"""
        factor = DragonTigerFactor(lookback_days=30)
        assert factor.lookback_days == 30

    def test_calculate(self, sample_data):
        """测试计算龙虎榜因子"""
        factor = DragonTigerFactor()
        result = factor.calculate(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "dragon_tiger_factor"

    def test_calculate_with_minimal_data(self):
        """测试最小数据计算"""
        factor = DragonTigerFactor()
        data = pd.DataFrame({
            "symbol": ["000001.SZ"],
            "datetime": [datetime.now()],
        })
        result = factor.calculate(data)
        assert len(result) == 1

    def test_calculate_raises_on_empty_data(self):
        """测试空数据抛出异常"""
        factor = DragonTigerFactor()
        with pytest.raises(ValueError):
            factor.calculate(pd.DataFrame())

    def test_get_institution_net_buy(self, sample_data):
        """测试机构净买入"""
        factor = DragonTigerFactor()
        result = factor.get_institution_net_buy(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "institution_net_buy"

    def test_get_turnover_rate(self, sample_data):
        """测试换手率"""
        factor = DragonTigerFactor()
        result = factor.get_turnover_rate(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "turnover_rate"

    def test_get_buy_sell_ratio(self, sample_data):
        """测试买卖总额比"""
        factor = DragonTigerFactor()
        result = factor.get_buy_sell_ratio(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "buy_sell_ratio"

    def test_get_listing_count(self):
        """测试上榜次数"""
        factor = DragonTigerFactor()
        data = pd.DataFrame({
            "symbol": ["000001.SZ"] * 5,
            "datetime": pd.date_range(start="2025-01-01", periods=5, freq="D"),
            "listed": [1, 0, 1, 1, 0],
        })
        result = factor.get_listing_count(data, days=3)
        assert len(result) == len(data)
        assert result.name == "listing_count"

    def test_get_required_columns(self):
        """测试所需列"""
        factor = DragonTigerFactor()
        required = factor.get_required_columns()
        assert "symbol" in required
        assert "institution_buy" in required
        assert "buy_amount" in required


# ==================== 测试 NorthboundFactor ====================

class TestNorthboundFactor:
    """测试北向资金因子"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        dates = pd.date_range(start="2025-01-01", periods=10, freq="D")
        return pd.DataFrame({
            "symbol": ["000001.SZ"] * 10,
            "datetime": dates,
            "net_inflow": np.random.randn(10) * 10000000 + 5000000,
            "buy_amount": np.random.randn(10) * 10000000 + 5000000,
            "sell_amount": np.random.randn(10) * 10000000 + 4000000,
            "current_holding": np.random.randint(1000000, 10000000, 10),
            "previous_holding": np.random.randint(900000, 9000000, 10),
            "turnover": np.random.randint(10000000, 100000000, 10),
        })

    def test_creation(self):
        """测试北向资金因子创建"""
        factor = NorthboundFactor()
        assert factor.name == "northbound"
        assert factor.factor_type == FactorType.NORTHBOUND
        assert factor.lookback_days == 20

    def test_creation_with_custom_lookback(self):
        """测试自定义回看天数"""
        factor = NorthboundFactor(lookback_days=30)
        assert factor.lookback_days == 30

    def test_calculate(self, sample_data):
        """测试计算北向资金因子"""
        factor = NorthboundFactor()
        result = factor.calculate(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "northbound_factor"

    def test_calculate_with_minimal_data(self):
        """测试最小数据计算"""
        factor = NorthboundFactor()
        data = pd.DataFrame({
            "symbol": ["000001.SZ"],
            "datetime": [datetime.now()],
        })
        result = factor.calculate(data)
        assert len(result) == 1

    def test_calculate_raises_on_empty_data(self):
        """测试空数据抛出异常"""
        factor = NorthboundFactor()
        with pytest.raises(ValueError):
            factor.calculate(pd.DataFrame())

    def test_get_net_inflow(self, sample_data):
        """测试净流入"""
        factor = NorthboundFactor()
        result = factor.get_net_inflow(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "net_inflow"

    def test_get_holding_change(self, sample_data):
        """测试持股变化"""
        factor = NorthboundFactor()
        result = factor.get_holding_change(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "holding_change"

    def test_get_flow_strength(self, sample_data):
        """测试资金流向强度"""
        factor = NorthboundFactor()
        result = factor.get_flow_strength(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "flow_strength"

    def test_get_cumulative_inflow(self, sample_data):
        """测试累计净流入"""
        factor = NorthboundFactor()
        result = factor.get_cumulative_inflow(sample_data, days=5)
        assert len(result) == len(sample_data)
        assert result.name == "cumulative_inflow"

    def test_get_inflow_momentum(self, sample_data):
        """测试净流入动量"""
        factor = NorthboundFactor()
        result = factor.get_inflow_momentum(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "inflow_momentum"

    def test_get_required_columns(self):
        """测试所需列"""
        factor = NorthboundFactor()
        required = factor.get_required_columns()
        assert "symbol" in required
        assert "net_inflow" in required
        assert "buy_amount" in required


# ==================== 测试 SectorRotationFactor ====================

class TestSectorRotationFactor:
    """测试板块轮动因子"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        dates = pd.date_range(start="2025-01-01", periods=9, freq="D")
        return pd.DataFrame({
            "sector": ["TECH", "MED", "FIN"] * 3,
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"] * 3,
            "datetime": dates,
            "return": np.random.randn(9) * 0.02,
            "market_return": np.random.randn(9) * 0.01,
            "volume": np.random.randint(1000000, 10000000, 9),
            "float_share": np.random.randint(10000000, 100000000, 9),
            "net_inflow": np.random.randn(9) * 10000000,
        })

    def test_creation(self):
        """测试板块轮动因子创建"""
        factor = SectorRotationFactor()
        assert factor.name == "sector_rotation"
        assert factor.factor_type == FactorType.SECTOR_ROTATION
        assert factor.lookback_days == 20

    def test_creation_with_custom_lookback(self):
        """测试自定义回看天数"""
        factor = SectorRotationFactor(lookback_days=30)
        assert factor.lookback_days == 30

    def test_calculate(self, sample_data):
        """测试计算板块轮动因子"""
        factor = SectorRotationFactor()
        result = factor.calculate(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "sector_rotation_factor"

    def test_calculate_with_minimal_data(self):
        """测试最小数据计算"""
        factor = SectorRotationFactor()
        data = pd.DataFrame({
            "sector": ["科技"],
            "datetime": [datetime.now()],
        })
        result = factor.calculate(data)
        assert len(result) == 1

    def test_calculate_raises_on_empty_data(self):
        """测试空数据抛出异常"""
        factor = SectorRotationFactor()
        with pytest.raises(ValueError):
            factor.calculate(pd.DataFrame())

    def test_get_momentum(self, sample_data):
        """测试板块动量"""
        factor = SectorRotationFactor()
        result = factor.get_momentum(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "momentum"

    def test_get_relative_strength(self, sample_data):
        """测试相对强弱"""
        factor = SectorRotationFactor()
        result = factor.get_relative_strength(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "relative_strength"

    def test_get_sector_turnover(self, sample_data):
        """测试板块换手率"""
        factor = SectorRotationFactor()
        result = factor.get_sector_turnover(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "sector_turnover"

    def test_get_sector_flow(self, sample_data):
        """测试板块资金流向"""
        factor = SectorRotationFactor()
        result = factor.get_sector_flow(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "sector_flow"

    def test_get_momentum_reversal(self, sample_data):
        """测试动量反转"""
        factor = SectorRotationFactor()
        result = factor.get_momentum_reversal(sample_data, short_period=3, long_period=10)
        assert len(result) == len(sample_data)
        assert result.name == "momentum_reversal"

    def test_get_leading_lagging(self, sample_data):
        """测试领先滞后"""
        factor = SectorRotationFactor()
        result = factor.get_leading_lagging(sample_data)
        assert len(result) == len(sample_data)
        assert result.name == "leading_lagging"

    def test_get_required_columns(self):
        """测试所需列"""
        factor = SectorRotationFactor()
        required = factor.get_required_columns()
        assert "sector" in required
        assert "return" in required
        assert "market_return" in required


# ==================== 测试集成场景 ====================

class TestFactorIntegration:
    """测试因子集成场景"""

    def test_all_factor_types_different(self):
        """测试不同因子类型"""
        dragon_tiger = DragonTigerFactor()
        northbound = NorthboundFactor()
        sector_rotation = SectorRotationFactor()

        assert dragon_tiger.factor_type == FactorType.DRAGON_TIGER
        assert northbound.factor_type == FactorType.NORTHBOUND
        assert sector_rotation.factor_type == FactorType.SECTOR_ROTATION

    def test_factor_with_time_series_data(self):
        """测试时间序列数据处理"""
        dates = pd.date_range(start="2025-01-01", periods=30, freq="D")
        data = pd.DataFrame({
            "symbol": ["000001.SZ"] * 30,
            "datetime": dates,
            "institution_buy": np.random.randn(30) * 1000000 + 500000,
            "institution_sell": np.random.randn(30) * 1000000 + 400000,
            "buy_amount": np.random.randn(30) * 10000000 + 5000000,
            "sell_amount": np.random.randn(30) * 10000000 + 4000000,
            "volume": np.random.randint(1000000, 10000000, 30),
            "float_share": np.random.randint(10000000, 100000000, 30),
        })

        factor = DragonTigerFactor(lookback_days=10)
        result = factor.calculate(data)
        assert len(result) == 30
        assert not result.isna().all()

    def test_normalization_preserves_shape(self):
        """测试归一化保持数据形状"""
        dates = pd.date_range(start="2025-01-01", periods=20, freq="D")
        data = pd.DataFrame({
            "symbol": ["000001.SZ"] * 20,
            "datetime": dates,
            "net_inflow": np.random.randn(20) * 10000000 + 5000000,
            "holding_change": np.random.randn(20) * 0.1,
            "turnover": np.random.randint(10000000, 100000000, 20),
        })

        factor = NorthboundFactor()
        result = factor.calculate(data)
        assert len(result) == len(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
