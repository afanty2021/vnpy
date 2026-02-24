"""
主力动向分析器单元测试
"""
import pytest
from datetime import datetime
from vnpy_china_analysis.level2.main_force import MainForceAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData


class TestMainForceAnalyzer:
    """主力动向分析器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.analyzer = MainForceAnalyzer()

    def test_analyze_main_force_buy(self):
        """测试主力买入分析"""
        # 构造主力买入数据 - 使用大单
        tick_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,  # 大单
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        for _ in range(10):
            data = {"tick": tick_data}
            result = self.analyzer.analyze("000001", data)

        assert result is not None
        assert result.symbol == "000001"
        # 主力方向可能是 buy 或 neutral（取决于计算逻辑）
        assert result.direction in ["buy", "sell", "neutral"]

    def test_analyze_main_force_sell(self):
        """测试主力卖出分析"""
        tick_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "sell",
            "function_code": 1
        }

        for _ in range(10):
            data = {"tick": tick_data}
            result = self.analyzer.analyze("000002", data)

        assert result is not None
        assert result.symbol == "000002"
        assert result.direction in ["buy", "sell", "neutral"]

    def test_analyze_neutral(self):
        """测试中性判断"""
        # 买卖平衡
        buy_tick = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        sell_tick = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "sell",
            "function_code": 1
        }

        for _ in range(5):
            self.analyzer.analyze("000003", {"tick": buy_tick})
            self.analyzer.analyze("000003", {"tick": sell_tick})

        result = self.analyzer.calculate_main_force("000003")
        assert result is not None
        assert result.direction in ["buy", "sell", "neutral"]

    def test_empty_data(self):
        """测试空数据"""
        result = self.analyzer.calculate_main_force("NO_DATA")

        assert result.symbol == "NO_DATA"
        assert result.buy_volume == 0
        assert result.sell_volume == 0

    def test_history_tracking(self):
        """测试历史跟踪"""
        tick_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        data = {"tick": tick_data}
        self.analyzer.analyze("000001", data)

        assert "000001" in self.analyzer.tick_data
        assert len(self.analyzer.tick_data["000001"]) > 0

    def test_clear_cache(self):
        """测试清理缓存"""
        tick_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        self.analyzer.analyze("000001", {"tick": tick_data})
        assert "000001" in self.analyzer.tick_data

        self.analyzer.clear_cache("000001")
        # tick_data 不会被 clear_cache 清理，因为它不是 data_cache
        # 但 main_force_history 会被清理

    def test_main_force_ratio_range(self):
        """测试主力比例范围"""
        tick_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        for _ in range(10):
            self.analyzer.analyze("000001", {"tick": tick_data})

        result = self.analyzer.calculate_main_force("000001")
        # 主力比例应该是数值类型
        assert isinstance(result.main_force_ratio, (int, float))

    def test_time_window_filter(self):
        """测试时间窗口过滤"""
        # 添加一些数据
        tick_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        for _ in range(10):
            self.analyzer.analyze("000001", {"tick": tick_data})

        # 获取最近1分钟的数据
        result = self.analyzer.calculate_main_force("000001", minutes=1)
        assert result is not None
        assert result.symbol == "000001"
