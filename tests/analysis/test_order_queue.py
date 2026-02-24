"""
委托队列分析器单元测试
"""
import pytest
from datetime import datetime
from vnpy_china_analysis.level2.order_queue import OrderQueueAnalyzer
from vnpy_china_analysis.objects.types import OrderQueueData


class TestOrderQueueAnalyzer:
    """委托队列分析器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.analyzer = OrderQueueAnalyzer()

    def test_analyze_basic(self):
        """测试基本分析功能"""
        # 构造测试数据
        data = {
            "ask_prices": [10.1, 10.2, 10.3, 10.4, 10.5],
            "ask_volumes": [1000, 2000, 3000, 4000, 5000],
            "ask_queue": [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]],
            "bid_prices": [10.0, 9.9, 9.8, 9.7, 9.6],
            "bid_volumes": [5000, 4000, 3000, 2000, 1000],
            "bid_queue": [[10, 9], [8, 7], [6, 5], [4, 3], [2, 1]]
        }

        result = self.analyzer.analyze("000001", data)

        # 验证结果
        assert result.symbol == "000001"
        assert isinstance(result, OrderQueueData)
        assert len(result.ask_prices) == 5
        assert len(result.bid_prices) == 5

    def test_get_support_level(self):
        """测试支撑位识别"""
        # 先添加一些数据
        data = {
            "ask_prices": [10.1, 10.2, 10.3, 10.4, 10.5],
            "ask_volumes": [100, 200, 300, 400, 500],
            "ask_queue": [],
            "bid_prices": [10.0, 9.9, 9.8, 9.7, 9.6],
            "bid_volumes": [10000, 1000, 500, 200, 100],  # 第一档支撑最强
            "bid_queue": []
        }

        self.analyzer.analyze("000001", data)

        support = self.analyzer.get_support_level("000001")

        assert support is not None
        assert "price" in support
        assert "strength" in support
        assert support["price"] == 10.0  # 最强支撑价位

    def test_get_resistance_level(self):
        """测试阻力位识别"""
        data = {
            "ask_prices": [10.1, 10.2, 10.3, 10.4, 10.5],
            "ask_volumes": [10000, 1000, 500, 200, 100],  # 第一档阻力最强
            "ask_queue": [],
            "bid_prices": [10.0, 9.9, 9.8, 9.7, 9.6],
            "bid_volumes": [100, 200, 300, 400, 500],
            "bid_queue": []
        }

        self.analyzer.analyze("000001", data)

        resistance = self.analyzer.get_resistance_level("000001")

        assert resistance is not None
        assert "price" in resistance
        assert "strength" in resistance
        assert resistance["price"] == 10.1  # 最强阻力价位

    def test_empty_data(self):
        """测试空数据处理"""
        data = {
            "ask_prices": [],
            "ask_volumes": [],
            "ask_queue": [],
            "bid_prices": [],
            "bid_volumes": [],
            "bid_queue": []
        }

        result = self.analyzer.analyze("000002", data)

        assert result.symbol == "000002"
        assert len(result.ask_prices) == 0

    def test_get_level_no_data(self):
        """测试无数据时获取支撑阻力位"""
        result = self.analyzer.get_support_level("NO_DATA")
        assert result == {}

        result = self.analyzer.get_resistance_level("NO_DATA")
        assert result == {}

    def test_history_tracking(self):
        """测试历史数据跟踪"""
        data = {
            "ask_prices": [10.1],
            "ask_volumes": [100],
            "ask_queue": [],
            "bid_prices": [10.0],
            "bid_volumes": [100],
            "bid_queue": []
        }

        # 添加3条记录
        for _ in range(3):
            self.analyzer.analyze("000001", data)

        assert "000001" in self.analyzer.queue_history
        assert len(self.analyzer.queue_history["000001"]) == 3
