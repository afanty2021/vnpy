"""
测试A股规则模块GUI集成
验证规则引擎与GUI引擎的集成功能
"""

import pytest
from datetime import datetime, time
from unittest.mock import Mock, MagicMock, patch

from vnpy_china_rules.gui_engine import ChinaRulesGuiEngine
from vnpy_china_rules.engine import ChinaStockRulesEngine, RuleResult
from vnpy.trader.object import OrderData, TradeData, TickData
from vnpy.trader.constant import Direction, OrderType, Status


class TestChinaRulesGuiEngine:
    """测试GUI引擎"""

    def test_init_without_main_engine(self):
        """测试初始化（不使用真实主引擎）"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            # 模拟BaseEngine的初始化
            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"

            # 手动初始化属性
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}

            # 模拟事件注册
            event_engine.register = Mock()

            # 初始化规则引擎
            gui_engine.init_rules_engine()

            # 验证规则引擎已创建
            assert gui_engine.rules_engine is not None
            assert isinstance(gui_engine.rules_engine, ChinaStockRulesEngine)

            print("✓ GUI引擎初始化成功")

    def test_get_sellable_volume(self):
        """测试获取可卖数量"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 记录一些买入
            gui_engine.rules_engine.t1_rules.record_buy("000001", 1000, datetime(2026, 2, 20))
            gui_engine.rules_engine.t1_rules.record_buy("000001", 2000, datetime(2026, 2, 21))

            # 测试可卖数量（今天买入的不可卖）
            sellable = gui_engine.get_sellable_volume("000001")
            assert sellable == 3000  # 之前买入的都可以卖

            print(f"✓ 可卖数量查询成功: {sellable}股")

    def test_calculate_limit_price(self):
        """测试计算涨跌停价格"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 测试主板股票（10%）
            limit_up, limit_down = gui_engine.calculate_limit_price("000001", 10.0)
            assert abs(limit_up - 11.0) < 0.01  # 10% 涨停
            assert abs(limit_down - 9.0) < 0.01  # 10% 跌停

            print(f"✓ 涨跌停价格计算成功: 涨停{limit_up}, 跌停{limit_down}")

    def test_get_trading_status(self):
        """测试获取交易状态"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 获取交易状态
            status = gui_engine.get_trading_status()

            # 验证状态字典包含必要字段
            assert "current_time" in status
            assert "trading_phase" in status
            assert "is_trading" in status

            print(f"✓ 交易状态获取成功: {status['trading_phase']}")

    def test_process_trade_event(self):
        """测试成交事件处理"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 创建成交事件
            trade = TradeData(
                symbol="000001",
                exchange="SZSE",
                orderid="TEST001",
                tradeid="TRADE001",
                direction=Direction.LONG,
                price=10.0,
                volume=1000,
                datetime=datetime(2026, 2, 20, 9, 30),
                gateway_name="TEST",
            )

            event = Mock()
            event.data = trade

            # 处理成交事件
            gui_engine.process_trade_event(event)

            # 验证持仓已记录
            sellable = gui_engine.get_sellable_volume("000001")
            assert sellable == 1000

            print("✓ 成交事件处理成功")

    def test_process_tick_event(self):
        """测试行情事件处理"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 创建行情事件
            tick = TickData(
                symbol="000001",
                exchange="SZSE",
                datetime=datetime(2026, 2, 25, 9, 30),
                gateway_name="TEST",
                name="测试股票",
                last_price=10.5,
                pre_close=10.0,
            )

            event = Mock()
            event.data = tick

            # 处理行情事件
            gui_engine.process_tick_event(event)

            # 验证昨收价已缓存
            pre_close = gui_engine.get_pre_close("000001")
            assert pre_close == 10.0

            print("✓ 行情事件处理成功")

    def test_get_check_history(self):
        """测试获取检查历史"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 创建订单事件
            order = OrderData(
                symbol="000001",
                exchange="SZSE",
                orderid="ORDER001",
                direction=Direction.LONG,
                price=10.0,
                volume=1000,
                datetime=datetime(2026, 2, 25, 9, 30),
                gateway_name="TEST",
            )

            event = Mock()
            event.data = order

            # 处理订单事件
            gui_engine.process_order_event(event)

            # 获取检查历史
            history = gui_engine.get_check_history()

            # 验证历史记录
            assert len(history) == 1
            assert history[0]["symbol"] == "000001"

            print("✓ 检查历史获取成功")

    def test_clear_check_history(self):
        """测试清空检查历史"""
        with patch("vnpy_china_rules.gui_engine.BaseEngine.__init__"):
            main_engine = Mock()
            event_engine = Mock()

            gui_engine = ChinaRulesGuiEngine.__new__(ChinaRulesGuiEngine)
            gui_engine.main_engine = main_engine
            gui_engine.event_engine = event_engine
            gui_engine.engine_name = "ChinaRulesApp"
            gui_engine.rules_engine = None
            gui_engine.check_results = []
            gui_engine.pre_close_cache = {}
            event_engine.register = Mock()

            gui_engine.init_rules_engine()

            # 添加一些历史记录
            order = OrderData(
                symbol="000001",
                exchange="SZSE",
                orderid="ORDER001",
                direction=Direction.LONG,
                price=10.0,
                volume=1000,
                datetime=datetime(2026, 2, 25, 9, 30),
                gateway_name="TEST",
            )

            event = Mock()
            event.data = order
            gui_engine.process_order_event(event)

            # 清空历史
            gui_engine.clear_check_history()

            # 验证历史已清空
            history = gui_engine.get_check_history()
            assert len(history) == 0

            print("✓ 检查历史清空成功")


def test_gui_integration():
    """运行所有GUI集成测试"""
    test = TestChinaRulesGuiEngine()

    print("\n" + "=" * 50)
    print("测试A股规则模块GUI集成")
    print("=" * 50 + "\n")

    test.test_init_without_main_engine()
    test.test_get_sellable_volume()
    test.test_calculate_limit_price()
    test.test_get_trading_status()
    test.test_process_trade_event()
    test.test_process_tick_event()
    test.test_get_check_history()
    test.test_clear_check_history()

    print("\n" + "=" * 50)
    print("所有GUI集成测试通过!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    test_gui_integration()
