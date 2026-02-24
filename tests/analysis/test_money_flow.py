"""
资金流向分析器单元测试
"""
import pytest
from datetime import datetime
from vnpy_china_analysis.money_flow.analyzer import MoneyFlowAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData, MoneyFlowData


class TestMoneyFlowAnalyzer:
    """资金流向分析器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.analyzer = MoneyFlowAnalyzer()

    def test_analyze_basic(self):
        """测试基本分析功能"""
        # 价格10元，1000手 = 100万元，超大单
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=1000,  # 手数
                amount=1000000,
                direction="buy",
                function_code=1
            )
        ]

        result = self.analyzer.analyze("000001", ticks)

        assert isinstance(result, MoneyFlowData)
        assert result.symbol == "000001"

    def test_main_inflow_calculation(self):
        """测试主力净流入计算"""
        # 超大单和大单买入
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=10000,  # 1000万元，超大单
                amount=10000000,
                direction="buy",
                function_code=1
            ),
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=5000,  # 500万元，大单
                amount=5000000,
                direction="buy",
                function_code=1
            )
        ]

        result = self.analyzer.analyze("000001", ticks)

        # 主力净流入 = 超大单 + 大单 = 1500万元
        assert result.main_inflow == 15000000

    def test_retail_inflow_calculation(self):
        """测试散户净流入计算"""
        # 中单和小单
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=100,  # 10万元，中单
                amount=100000,
                direction="buy",
                function_code=1
            ),
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=30,  # 3万元，小单
                amount=30000,
                direction="buy",
                function_code=1
            )
        ]

        result = self.analyzer.analyze("000001", ticks)

        # 散户净流入 = 中单 + 小单 = 13万元
        assert result.retail_inflow == 130000

    def test_net_inflow_calculation(self):
        """测试总净流入计算"""
        # 混合买卖
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=10000,  # 超大单买入
                amount=10000000,
                direction="buy",
                function_code=1
            ),
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=5000,  # 大单卖出
                amount=5000000,
                direction="sell",
                function_code=1
            )
        ]

        result = self.analyzer.analyze("000001", ticks)

        # 总净流入 = 买入 - 卖出 = 1000万 - 500万 = 500万
        assert result.net_inflow == 5000000

    def test_sell_direction(self):
        """测试卖出方向"""
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=10000,
                amount=10000000,
                direction="sell",
                function_code=1
            )
        ]

        result = self.analyzer.analyze("000001", ticks)

        # 卖出应该是负值
        assert result.super_large_inflow == -10000000

    def test_empty_ticks(self):
        """测试空列表"""
        result = self.analyzer.analyze("000001", [])

        assert result.symbol == "000001"
        assert result.net_inflow == 0

    def test_get_main_inflow(self):
        """测试获取主力净流入"""
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=10000,
                amount=10000000,
                direction="buy",
                function_code=1
            )
        ]

        self.analyzer.analyze("000001", ticks)

        main_inflow = self.analyzer.get_main_inflow("000001")
        assert main_inflow == 10000000

    def test_get_net_inflow(self):
        """测试获取总净流入"""
        ticks = [
            TickFlowData(
                symbol="000001",
                datetime=datetime.now(),
                price=10.0,
                volume=10000,
                amount=10000000,
                direction="buy",
                function_code=1
            )
        ]

        self.analyzer.analyze("000001", ticks)

        net_inflow = self.analyzer.get_net_inflow("000001")
        assert net_inflow == 10000000

    def test_flow_history_tracking(self):
        """测试历史跟踪"""
        tick = TickFlowData(
            symbol="000001",
            datetime=datetime.now(),
            price=10.0,
            volume=1000,
            amount=1000000,
            direction="buy",
            function_code=1
        )

        self.analyzer.analyze("000001", [tick])

        assert "000001" in self.analyzer.flow_history
        assert len(self.analyzer.flow_history["000001"]) > 0
