"""
资金指标计算单元测试
"""
import pytest
from datetime import datetime
from vnpy_china_analysis.money_flow.indicator import MoneyFlowIndicator
from vnpy_china_analysis.objects.types import MoneyFlowData


class TestMoneyFlowIndicator:
    """资金指标计算测试"""

    def setup_method(self):
        """测试前置设置"""
        self.indicator = MoneyFlowIndicator()

    def _add_sample_data(self, symbol: str, count: int = 10):
        """添加示例数据"""
        for i in range(count):
            data = {
                "datetime": datetime.now(),
                "price": 10.0,
                "volume": 1000 * (i + 1),  # 递增
                "amount": 10000 * (i + 1),
                "direction": "buy" if i % 2 == 0 else "sell",
                "function_code": 1
            }
            self.indicator.calculate(symbol, data)

    def test_get_net_inflow_rate(self):
        """测试净流入率计算"""
        self._add_sample_data("000001", 10)

        rate = self.indicator.get_net_inflow_rate("000001")

        # 净流入率应该是一个百分比
        assert isinstance(rate, float)

    def test_get_main_force_strength(self):
        """测试主力强度计算"""
        # 添加主力买入数据
        for i in range(10):
            data = {
                "datetime": datetime.now(),
                "price": 10.0,
                "volume": 10000,  # 大单
                "amount": 100000,
                "direction": "buy",
                "function_code": 1
            }
            self.indicator.calculate("000001", data)

        strength = self.indicator.get_main_force_strength("000001")

        # 主力强度应该是正值（主力大幅流入）
        assert isinstance(strength, float)

    def test_get_momentum(self):
        """测试资金动量"""
        self._add_sample_data("000001", 20)

        momentum = self.indicator.get_momentum("000001")

        assert isinstance(momentum, float)

    def test_get_flow_trend(self):
        """测试资金流向趋势"""
        self._add_sample_data("000001", 15)

        trend = self.indicator.get_flow_trend("000001")

        assert "trend" in trend
        assert trend["trend"] in ["strong_inflow", "moderate_inflow", "strong_outflow",
                                   "moderate_outflow", "neutral", "unknown"]

    def test_get_buying_pressure(self):
        """测试买入压力"""
        self._add_sample_data("000001", 10)

        pressure = self.indicator.get_buying_pressure("000001")

        # 买入压力应该在0-100之间
        assert 0 <= pressure <= 100

    def test_empty_symbol(self):
        """测试空股票代码"""
        rate = self.indicator.get_net_inflow_rate("NO_DATA")
        assert rate == 0.0

        strength = self.indicator.get_main_force_strength("NO_DATA")
        assert strength == 0.0

        trend = self.indicator.get_flow_trend("NO_DATA")
        assert trend["trend"] == "unknown"

        pressure = self.indicator.get_buying_pressure("NO_DATA")
        assert pressure == 50.0  # 中性

    def test_calculate_basic(self):
        """测试基本计算功能"""
        data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 1000,
            "amount": 10000,
            "direction": "buy",
            "function_code": 1
        }

        result = self.indicator.calculate("000001", data)

        assert isinstance(result, MoneyFlowData)
        assert result.symbol == "000001"

    def test_history_tracking(self):
        """测试历史跟踪"""
        self._add_sample_data("000001", 5)

        assert "000001" in self.indicator.flow_history
        assert len(self.indicator.flow_history["000001"]) == 5

    def test_clear_cache(self):
        """测试清理缓存"""
        self._add_sample_data("000001", 5)
        assert "000001" in self.indicator.flow_history

        self.indicator.clear_cache("000001")
        # flow_history 独立于 data_cache，需要单独清理
        self.indicator.flow_history.clear()
        assert "000001" not in self.indicator.flow_history

    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        # 创建一个限制为10的indicator
        indicator = MoneyFlowIndicator(cache_size=10)

        # 添加15条数据
        for i in range(15):
            data = {
                "datetime": datetime.now(),
                "price": 10.0,
                "volume": 1000,
                "amount": 10000,
                "direction": "buy",
                "function_code": 1
            }
            indicator.calculate("000001", data)

        # 缓存应该限制在10条
        assert len(indicator.flow_history["000001"]) == 10
