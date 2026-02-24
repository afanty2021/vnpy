"""
逐笔成交分析器单元测试
"""
import pytest
from datetime import datetime
from vnpy_china_analysis.level2.tick_flow import TickFlowAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData


class TestTickFlowAnalyzer:
    """逐笔成交分析器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.analyzer = TickFlowAnalyzer()

    def test_analyze_single_tick(self):
        """测试单个tick分析"""
        data = {
            "datetime": datetime.now(),
            "price": 10.5,
            "volume": 1000,
            "amount": 10500,
            "direction": "buy",
            "function_code": 1
        }

        result = self.analyzer.analyze("000001", data)

        assert result is not None
        assert result.symbol == "000001"
        assert result.price == 10.5

    def test_get_transaction_summary(self):
        """测试获取成交汇总"""
        # 添加几笔成交
        for i in range(5):
            data = {
                "datetime": datetime.now(),
                "price": 10.0 + i * 0.01,
                "volume": 1000,
                "amount": 10000,
                "direction": "buy" if i % 2 == 0 else "sell",
                "function_code": 1
            }
            self.analyzer.analyze("000001", data)

        summary = self.analyzer.get_transaction_summary("000001")

        assert summary is not None
        assert summary["symbol"] == "000001"
        assert summary["total_count"] == 5
        assert summary["buy_count"] == 3  # 0, 2, 4
        assert summary["sell_count"] == 2  # 1, 3

    def test_detect_large_trade(self):
        """测试大单检测"""
        # 小单
        small_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 100,
            "amount": 1000,
            "direction": "buy",
            "function_code": 1
        }

        self.analyzer.analyze("000001", small_data)
        summary = self.analyzer.get_transaction_summary("000001")
        assert summary["total_amount"] < 50000

        # 大单
        large_data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 10000,
            "amount": 100000,
            "direction": "buy",
            "function_code": 1
        }

        self.analyzer.analyze("000001", large_data)
        summary = self.analyzer.get_transaction_summary("000001")
        assert summary["total_amount"] > 50000

    def test_get_buy_volume(self):
        """测试获取买入量"""
        for i in range(3):
            data = {
                "datetime": datetime.now(),
                "price": 10.0,
                "volume": 1000,
                "amount": 10000,
                "direction": "buy",
                "function_code": 1
            }
            self.analyzer.analyze("000001", data)

        # 添加一笔卖出
        data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 500,
            "amount": 5000,
            "direction": "sell",
            "function_code": 1
        }
        self.analyzer.analyze("000001", data)

        summary = self.analyzer.get_transaction_summary("000001")
        assert summary["buy_volume"] == 3000  # 3 * 1000

    def test_get_sell_volume(self):
        """测试获取卖出量"""
        # 买入
        data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 1000,
            "amount": 10000,
            "direction": "buy",
            "function_code": 1
        }
        self.analyzer.analyze("000001", data)

        # 卖出
        data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 500,
            "amount": 5000,
            "direction": "sell",
            "function_code": 1
        }
        self.analyzer.analyze("000001", data)

        summary = self.analyzer.get_transaction_summary("000001")
        assert summary["sell_volume"] == 500

    def test_clear_history(self):
        """测试清理历史"""
        data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 1000,
            "amount": 10000,
            "direction": "buy",
            "function_code": 1
        }

        self.analyzer.analyze("000001", data)
        assert "000001" in self.analyzer.tick_history

        self.analyzer.tick_history.clear()
        assert "000001" not in self.analyzer.tick_history

    def test_empty_symbol(self):
        """测试不存在的股票代码"""
        summary = self.analyzer.get_transaction_summary("NO_DATA")
        assert summary == {}

    def test_net_volume_calculation(self):
        """测试净成交量计算"""
        # 买入
        for i in range(3):
            data = {
                "datetime": datetime.now(),
                "price": 10.0,
                "volume": 1000,
                "amount": 10000,
                "direction": "buy",
                "function_code": 1
            }
            self.analyzer.analyze("000001", data)

        # 卖出
        data = {
            "datetime": datetime.now(),
            "price": 10.0,
            "volume": 500,
            "amount": 5000,
            "direction": "sell",
            "function_code": 1
        }
        self.analyzer.analyze("000001", data)

        summary = self.analyzer.get_transaction_summary("000001")
        assert summary["net_volume"] == 2500  # 3000 - 500
