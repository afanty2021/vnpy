"""
测试规则引擎
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, time, date
from typing import Optional, List
from dataclasses import dataclass

from vnpy.trader.object import TickData, BarData, OrderData, TradeData, ContractData
from vnpy.trader.constant import Exchange, Direction, Offset, OrderType, Status, Product
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from vnpy_china_rules.datasource import (
    StockInfo,
    DataSourceManager,
)
from vnpy_china_rules.engine import (
    RuleResult,
    PositionRecord,
    ChinaStockRulesEngine,
    T1RulesEngine,
    PriceLimitRulesEngine,
    TimeRulesEngine,
    UnitRulesEngine,
    IpoRulesEngine,
)


class MockDataSource:
    """模拟数据源"""

    def __init__(self):
        self.stock_info_map = {}
        self.market_data_map = {}

    def set_stock_info(self, symbol: str, info: StockInfo):
        """设置股票信息"""
        self.stock_info_map[symbol] = info

    def set_market_data(self, symbol: str, data):
        """设置行情数据"""
        self.market_data_map[symbol] = data

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票信息"""
        return self.stock_info_map.get(symbol)

    def get_market_data(self, symbol: str):
        """获取行情数据"""
        return self.market_data_map.get(symbol)


class TestRuleResult(unittest.TestCase):
    """测试RuleResult数据类"""

    def test_rule_result_creation(self):
        """测试RuleResult对象创建"""
        result = RuleResult(
            passed=True,
            rule_name="T+1规则",
            message="检查通过"
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.rule_name, "T+1规则")
        self.assertEqual(result.message, "检查通过")


class TestPositionRecord(unittest.TestCase):
    """测试PositionRecord数据类"""

    def test_position_record_creation(self):
        """测试PositionRecord对象创建"""
        record = PositionRecord(
            symbol="000001",
            volume=1000,
            buy_datetime=datetime(2024, 2, 24, 9, 30),
            available=1000
        )

        self.assertEqual(record.symbol, "000001")
        self.assertEqual(record.volume, 1000)
        self.assertEqual(record.buy_datetime, datetime(2024, 2, 24, 9, 30))
        self.assertEqual(record.available, 1000)


class TestT1RulesEngine(unittest.TestCase):
    """测试T+1规则引擎"""

    def setUp(self):
        """测试前准备"""
        # 创建规则引擎
        self.mock_dm = Mock(spec=DataSourceManager)
        self.rules_engine = ChinaStockRulesEngine(self.mock_dm)
        self.t1_engine = self.rules_engine.t1_rules

    def test_record_buy(self):
        """测试记录买入成交"""
        # 记录买入
        buy_time = datetime(2024, 2, 24, 9, 30)
        self.t1_engine.record_buy("000001", 1000, buy_time)

        # 验证持仓记录
        self.assertIn("000001", self.t1_engine.positions)
        self.assertEqual(len(self.t1_engine.positions["000001"]), 1)

        record = self.t1_engine.positions["000001"][0]
        self.assertEqual(record.symbol, "000001")
        self.assertEqual(record.volume, 1000)
        self.assertEqual(record.buy_datetime, buy_time)
        self.assertEqual(record.available, 1000)

    def test_record_sell(self):
        """测试记录卖出成交"""
        # 先记录买入
        buy_time = datetime(2024, 2, 23, 9, 30)  # 前一天买入
        self.t1_engine.record_buy("000001", 1000, buy_time)

        # 记录卖出
        sell_time = datetime(2024, 2, 24, 10, 0)
        self.t1_engine.record_sell("000001", 500, sell_time)

        # 验证持仓扣减
        record = self.t1_engine.positions["000001"][0]
        self.assertEqual(record.available, 500)  # 1000 - 500

    def test_get_sellable_volume_today_buy(self):
        """测试当日买入不可卖"""
        # 当日买入
        buy_time = datetime(2024, 2, 24, 9, 30)
        self.t1_engine.record_buy("000001", 1000, buy_time)

        # 查询可卖数量
        sellable = self.t1_engine.get_sellable_volume("000001", datetime(2024, 2, 24, 14, 0))
        self.assertEqual(sellable, 0)  # 当日买入不可卖

    def test_get_sellable_volume_previous_buy(self):
        """测试前日买入可卖"""
        # 前日买入
        buy_time = datetime(2024, 2, 23, 9, 30)
        self.t1_engine.record_buy("000001", 1000, buy_time)

        # 查询可卖数量
        sellable = self.t1_engine.get_sellable_volume("000001", datetime(2024, 2, 24, 14, 0))
        self.assertEqual(sellable, 1000)  # 前日买入可卖

    def test_get_sellable_volume_mixed(self):
        """测试混合持仓"""
        # 前日买入
        self.t1_engine.record_buy("000001", 500, datetime(2024, 2, 23, 9, 30))
        # 当日买入
        self.t1_engine.record_buy("000001", 800, datetime(2024, 2, 24, 9, 30))

        # 查询可卖数量
        sellable = self.t1_engine.get_sellable_volume("000001", datetime(2024, 2, 24, 14, 0))
        self.assertEqual(sellable, 500)  # 只有前日买入的500可卖

    def test_check_sell_order_passed(self):
        """测试卖出订单检查通过"""
        # 前日买入
        self.t1_engine.record_buy("000001", 1000, datetime(2024, 2, 23, 9, 30))

        # 创建卖出订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=10.0,
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.t1_engine.check(order)

        # 验证结果
        self.assertTrue(result.passed)
        self.assertEqual(result.rule_name, "T+1规则")

    def test_check_sell_order_failed(self):
        """测试卖出订单检查失败"""
        # 当日买入
        self.t1_engine.record_buy("000001", 1000, datetime(2024, 2, 24, 9, 30))

        # 创建卖出订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=10.0,
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.t1_engine.check(order)

        # 验证结果
        self.assertFalse(result.passed)
        self.assertEqual(result.rule_name, "T+1规则")
        self.assertIn("可卖数量不足", result.message)

    def test_check_buy_order(self):
        """测试买入订单（买入不受T+1限制）"""
        # 创建买入订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.0,
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.t1_engine.check(order)

        # 验证结果（买入不检查T+1）
        self.assertTrue(result.passed)


class TestPriceLimitRulesEngine(unittest.TestCase):
    """测试涨跌停规则引擎"""

    def setUp(self):
        """测试前准备"""
        self.mock_dm = Mock(spec=DataSourceManager)
        self.rules_engine = ChinaStockRulesEngine(self.mock_dm)
        self.price_limit_engine = self.rules_engine.price_limit_rules

        # 创建模拟股票信息
        self.stock_info_main = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )

        self.stock_info_st = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="ST平安",
            market_type="主板",
            is_st=True,
            list_date="19910403",
            limit_ratio=0.05
        )

    def test_calculate_limit_price_main_board(self):
        """测试主板涨跌停价格计算"""
        # 模拟数据源返回股票信息（使用实际的limit_ratio值）
        self.mock_dm.get_stock_info.return_value = None  # 返回None，使用默认10%

        limit_up, limit_down = self.price_limit_engine.calculate_limit_price(
            "000001", 10.00
        )

        # 主板10%
        self.assertEqual(limit_up, 11.00)
        self.assertEqual(limit_down, 9.00)

    def test_calculate_limit_price_with_custom_ratio(self):
        """测试自定义涨跌停比例"""
        limit_up, limit_down = self.price_limit_engine.calculate_limit_price(
            "000001", 10.00, limit_ratio=0.20
        )

        self.assertEqual(limit_up, 12.00)
        self.assertEqual(limit_down, 8.00)

    def test_check_buy_order_passed(self):
        """测试买入订单价格检查通过"""
        # 模拟数据源返回股票信息
        self.mock_dm.get_stock_info.return_value = self.stock_info_main

        # 创建买入订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,  # 低于涨停价11.00
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.price_limit_engine.check(order, prev_close=10.00)

        # 验证结果
        self.assertTrue(result.passed)
        self.assertEqual(result.rule_name, "涨跌停规则")

    def test_check_buy_order_failed(self):
        """测试买入订单价格检查失败"""
        # 模拟数据源返回股票信息
        self.mock_dm.get_stock_info.return_value = self.stock_info_main

        # 创建买入订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=11.50,  # 高于涨停价11.00
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.price_limit_engine.check(order, prev_close=10.00)

        # 验证结果
        self.assertFalse(result.passed)
        self.assertIn("超过涨停价", result.message)

    def test_check_sell_order_failed(self):
        """测试卖出订单价格检查失败"""
        # 模拟数据源返回股票信息
        self.mock_dm.get_stock_info.return_value = self.stock_info_main

        # 创建卖出订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=8.50,  # 低于跌停价9.00
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.price_limit_engine.check(order, prev_close=10.00)

        # 验证结果
        self.assertFalse(result.passed)
        self.assertIn("低于跌停价", result.message)

    def test_check_with_stock_info_not_available(self):
        """测试股票信息不可用"""
        # 模拟数据源返回None
        self.mock_dm.get_stock_info.return_value = None

        # 创建订单
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 检查订单
        result = self.price_limit_engine.check(order, prev_close=10.00)

        # 验证结果（数据不可用时应该使用默认10%）
        self.assertTrue(result.passed)


class TestTimeRulesEngine(unittest.TestCase):
    """测试交易时间规则引擎"""

    def setUp(self):
        """测试前准备"""
        self.mock_dm = Mock(spec=DataSourceManager)
        self.rules_engine = ChinaStockRulesEngine(self.mock_dm)
        self.time_engine = self.rules_engine.time_rules

    def test_is_trading_time_morning(self):
        """测试上午交易时间"""
        # 集合竞价时间
        self.assertTrue(self.time_engine.is_trading_time(datetime(2024, 2, 24, 9, 20)))
        # 上午交易时间
        self.assertTrue(self.time_engine.is_trading_time(datetime(2024, 2, 24, 10, 0)))
        self.assertTrue(self.time_engine.is_trading_time(datetime(2024, 2, 24, 11, 30)))

    def test_is_trading_time_afternoon(self):
        """测试下午交易时间"""
        self.assertTrue(self.time_engine.is_trading_time(datetime(2024, 2, 24, 13, 0)))
        self.assertTrue(self.time_engine.is_trading_time(datetime(2024, 2, 24, 14, 0)))
        self.assertTrue(self.time_engine.is_trading_time(datetime(2024, 2, 24, 15, 0)))

    def test_is_trading_time_false(self):
        """测试非交易时间"""
        # 早盘前
        self.assertFalse(self.time_engine.is_trading_time(datetime(2024, 2, 24, 9, 10)))
        # 午休时间
        self.assertFalse(self.time_engine.is_trading_time(datetime(2024, 2, 24, 12, 0)))
        # 收盘后
        self.assertFalse(self.time_engine.is_trading_time(datetime(2024, 2, 24, 15, 1)))

    def test_can_submit_order_auction(self):
        """测试集合竞价时间可委托"""
        self.assertTrue(self.time_engine.can_submit_order(datetime(2024, 2, 24, 9, 20)))
        self.assertTrue(self.time_engine.can_submit_order(datetime(2024, 2, 24, 9, 25)))

    def test_can_submit_order_normal(self):
        """测试正常交易时间可委托"""
        self.assertTrue(self.time_engine.can_submit_order(datetime(2024, 2, 24, 10, 0)))
        self.assertTrue(self.time_engine.can_submit_order(datetime(2024, 2, 24, 14, 0)))

    def test_can_submit_order_false(self):
        """测试不可委托时间"""
        self.assertFalse(self.time_engine.can_submit_order(datetime(2024, 2, 24, 12, 0)))
        self.assertFalse(self.time_engine.can_submit_order(datetime(2024, 2, 24, 15, 1)))

    def test_check_order_passed(self):
        """测试订单时间检查通过"""
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=500,
            datetime=datetime(2024, 2, 24, 14, 0)  # 交易时间
        )

        result = self.time_engine.check(order)
        self.assertTrue(result.passed)

    def test_check_order_failed(self):
        """测试订单时间检查失败"""
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=500,
            datetime=datetime(2024, 2, 24, 12, 0)  # 非交易时间
        )

        result = self.time_engine.check(order)
        self.assertFalse(result.passed)
        self.assertIn("非交易时间", result.message)


class TestUnitRulesEngine(unittest.TestCase):
    """测试交易单位规则引擎"""

    def setUp(self):
        """测试前准备"""
        self.mock_dm = Mock(spec=DataSourceManager)
        self.rules_engine = ChinaStockRulesEngine(self.mock_dm)
        self.unit_engine = self.rules_engine.unit_rules

    def test_check_order_passed(self):
        """测试订单数量检查通过"""
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=100,  # 100股的整数倍
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        result = self.unit_engine.check(order)
        self.assertTrue(result.passed)

    def test_check_order_failed_not_multiple(self):
        """测试订单数量不是100的整数倍"""
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=150,  # 不是100的整数倍
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        result = self.unit_engine.check(order)
        self.assertFalse(result.passed)
        self.assertIn("必须是100股", result.message)

    def test_check_order_failed_too_small(self):
        """测试订单数量小于100股"""
        order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=50,  # 小于100股
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        result = self.unit_engine.check(order)
        self.assertFalse(result.passed)


class TestIpoRulesEngine(unittest.TestCase):
    """测试新股申购规则引擎"""

    def setUp(self):
        """测试前准备"""
        self.mock_dm = Mock(spec=DataSourceManager)
        self.rules_engine = ChinaStockRulesEngine(self.mock_dm)
        self.ipo_engine = self.rules_engine.ipo_rules

    def test_calculate_subs_quota(self):
        """测试申购额度计算"""
        # 模拟账户数据
        account_data = {
            "market_value": 10000.0,  # 1万元市值
            "cash": 50000.0  # 5万元现金
        }

        quota = self.ipo_engine.calculate_subs_quota(account_data)

        # 申购额度 = 市值 / 10000 * 1000
        # 10000 / 10000 * 1000 = 1000股
        self.assertEqual(quota, 1000)

    def test_calculate_subs_quota_zero(self):
        """测试无市值时申购额度为0"""
        account_data = {
            "market_value": 0,
            "cash": 50000.0
        }

        quota = self.ipo_engine.calculate_subs_quota(account_data)
        self.assertEqual(quota, 0)


class TestChinaStockRulesEngine(unittest.TestCase):
    """测试A股交易规则引擎"""

    def setUp(self):
        """测试前准备"""
        # 创建模拟数据源管理器
        self.mock_dm = Mock(spec=DataSourceManager)

        # 创建规则引擎
        self.rules_engine = ChinaStockRulesEngine(self.mock_dm)

        # 创建测试订单
        self.buy_order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=100,
            datetime=datetime(2024, 2, 24, 14, 0)
        )

    def test_check_order_all_passed(self):
        """测试订单全面检查通过"""
        # 模拟股票信息和行情数据
        stock_info = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )
        self.mock_dm.get_stock_info.return_value = stock_info

        mock_tick = TickData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            datetime=datetime(2024, 2, 24, 14, 0),
            last_price=10.50,
            pre_close=10.00
        )
        self.mock_dm.get_market_data.return_value = mock_tick

        # 检查订单
        results = self.rules_engine.check_order(self.buy_order)

        # 验证结果
        self.assertIsInstance(results, list)
        # 所有规则都应该通过
        for result in results:
            self.assertTrue(result.passed, f"{result.rule_name}: {result.message}")

    def test_can_submit_order_passed(self):
        """测试订单可提交判断（通过）"""
        # 模拟数据
        stock_info = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )
        self.mock_dm.get_stock_info.return_value = stock_info

        mock_tick = TickData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            datetime=datetime(2024, 2, 24, 14, 0),
            last_price=10.50,
            pre_close=10.00
        )
        self.mock_dm.get_market_data.return_value = mock_tick

        # 判断是否可提交
        can_submit, message = self.rules_engine.can_submit_order(self.buy_order)

        # 验证结果
        self.assertTrue(can_submit)
        self.assertEqual(message, "订单检查通过")

    def test_can_submit_order_failed(self):
        """测试订单可提交判断（失败）"""
        # 模拟数据
        stock_info = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )
        self.mock_dm.get_stock_info.return_value = stock_info

        mock_tick = TickData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            datetime=datetime(2024, 2, 24, 14, 0),
            last_price=10.50,
            pre_close=10.00
        )
        self.mock_dm.get_market_data.return_value = mock_tick

        # 创建不符合规则的订单
        bad_order = OrderData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test002",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=150,  # 不是100的整数倍
            datetime=datetime(2024, 2, 24, 14, 0)
        )

        # 判断是否可提交
        can_submit, message = self.rules_engine.can_submit_order(bad_order)

        # 验证结果
        self.assertFalse(can_submit)
        self.assertIn("交易单位", message)

    def test_constants(self):
        """测试常量定义"""
        # 交易时间常量
        self.assertEqual(self.rules_engine.TRADING_MORNING_START, time(9, 15))
        self.assertEqual(self.rules_engine.TRADING_MORNING_END, time(11, 30))
        self.assertEqual(self.rules_engine.TRADING_AFTERNOON_START, time(13, 0))
        self.assertEqual(self.rules_engine.TRADING_AFTERNOON_END, time(15, 0))

        # 涨跌停比例常量
        self.assertEqual(self.rules_engine.LIMIT_RATIO_MAIN, 0.10)
        self.assertEqual(self.rules_engine.LIMIT_RATIO_SME, 0.20)
        self.assertEqual(self.rules_engine.LIMIT_RATIO_SCI, 0.20)
        self.assertEqual(self.rules_engine.LIMIT_RATIO_BSE, 0.30)
        self.assertEqual(self.rules_engine.LIMIT_RATIO_ST, 0.05)


class TestT1PersistenceEngineInit(unittest.TestCase):
    """T+1持久化：db 注入与向后兼容"""

    def test_no_db_keeps_store_none_and_existing_behavior(self):
        """db=None 时 store 为 None，维持纯内存（现有行为不破坏）"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)
        self.assertIsNone(engine.store)

    def test_db_injected_creates_store_and_init_schema(self):
        """db 注入时创建 store、调用 init_schema、空流水重放无副作用"""
        mock_dm = Mock(spec=DataSourceManager)
        db = MagicMock()
        db.query.return_value = []  # 空流水
        engine = ChinaStockRulesEngine(mock_dm, db=db)
        self.assertIsNotNone(engine.store)
        # init_schema 触发过 execute(DDL)
        self.assertTrue(db.execute.called)

    def test_db_protocol_mismatch_falls_back_to_inmemory(self):
        """db 不满足协议时降级 store=None，不抛异常"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm, db=object())  # object() 无 execute/query
        self.assertIsNone(engine.store)

    def test_init_schema_failure_falls_back_to_inmemory(self):
        """db 协议正确但建表抛异常时降级 store=None，不抛异常"""
        mock_dm = Mock(spec=DataSourceManager)
        db = MagicMock()
        db.execute.side_effect = RuntimeError("db connection refused")
        engine = ChinaStockRulesEngine(mock_dm, db=db)
        self.assertIsNone(engine.store)

    def test_replay_rebuilds_same_as_continuous_record(self):
        """重放结果与连续 record_buy/sell 等价（含 FIFO 扣减）"""
        flow = [
            {"symbol": "000001", "direction": Direction.LONG.value,
             "volume": 1000, "trade_time": datetime(2024, 2, 23, 9, 30)},
            {"symbol": "000001", "direction": Direction.LONG.value,
             "volume": 500, "trade_time": datetime(2024, 2, 24, 9, 30)},
            {"symbol": "000001", "direction": Direction.SHORT.value,
             "volume": 300, "trade_time": datetime(2024, 2, 24, 14, 0)},
        ]
        mock_dm = Mock(spec=DataSourceManager)
        db = MagicMock()
        db.query.return_value = flow

        replayed = ChinaStockRulesEngine(mock_dm, db=db)

        # 参考引擎：连续 record
        ref = ChinaStockRulesEngine(mock_dm)
        ref.t1_rules.record_buy("000001", 1000, datetime(2024, 2, 23, 9, 30))
        ref.t1_rules.record_buy("000001", 500, datetime(2024, 2, 24, 9, 30))
        ref.t1_rules.record_sell("000001", 300, datetime(2024, 2, 24, 14, 0))

        # positions 逐批次相等
        rp = replayed.t1_rules.positions["000001"]
        fp = ref.t1_rules.positions["000001"]
        self.assertEqual(len(rp), len(fp))
        for r, f in zip(rp, fp):
            self.assertEqual((r.volume, r.available, r.buy_datetime),
                             (f.volume, f.available, f.buy_datetime))

        # 可卖量一致（2/25 视角：前日批次均可卖）
        self.assertEqual(
            replayed.t1_rules.get_sellable_volume("000001", datetime(2024, 2, 25, 9, 0)),
            ref.t1_rules.get_sellable_volume("000001", datetime(2024, 2, 25, 9, 0)),
        )

    def test_replay_skips_corrupt_row_without_aborting(self):
        """单条脏数据只跳过不中断重放，其余行正常重建，store 不被降级"""
        flow = [
            {"symbol": "000001", "direction": Direction.LONG.value,
             "volume": 1000, "trade_time": datetime(2024, 2, 23, 9, 30)},
            {"symbol": "000001", "direction": Direction.LONG.value,
             "volume": "not-a-number",  # 脏数据：int() 抛 ValueError
             "trade_time": datetime(2024, 2, 24, 9, 30)},
            {"symbol": "000001", "direction": Direction.SHORT.value,
             "volume": 300, "trade_time": datetime(2024, 2, 24, 14, 0)},
        ]
        mock_dm = Mock(spec=DataSourceManager)
        db = MagicMock()
        db.query.return_value = flow

        engine = ChinaStockRulesEngine(mock_dm, db=db)

        # 重放未被降级
        self.assertIsNotNone(engine.store)
        # 正常行被重建：买入1000(2/23) → 脏行跳过 → 卖出300(2/24) FIFO 扣减
        positions = engine.t1_rules.positions["000001"]
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].volume, 1000)
        self.assertEqual(positions[0].available, 700)  # 1000 - 300

    def _make_trade(self, symbol, direction, volume, dt, tradeid):
        return TradeData(
            gateway_name="TEST",
            symbol=symbol,
            exchange=Exchange.SZSE,
            orderid="o1",
            tradeid=tradeid,
            direction=direction,
            offset=Offset.OPEN if direction == Direction.LONG else Offset.CLOSE,
            price=10.0,
            volume=volume,
            datetime=dt,
        )

    def test_on_trade_appends_to_store_then_memory(self):
        """on_trade 先落库后内存，DB 与内存共用同一 trade_time"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)   # store=None
        engine.store = MagicMock()                # 注入可验证 mock
        engine.store.append_trade.return_value = 1

        dt = datetime(2024, 2, 24, 9, 30)
        trade = self._make_trade("000001", Direction.LONG, 1000, dt, "t1")
        engine.on_trade(trade)

        # vt_tradeid = f"{gateway_name}.{tradeid}" = "TEST.t1"
        engine.store.append_trade.assert_called_once_with(
            "TEST.t1", "000001", Direction.LONG.value, 1000, dt
        )
        # 内存已更新且 buy_datetime == trade_time（共用，非 now()）
        rec = engine.t1_rules.positions["000001"][0]
        self.assertEqual(rec.volume, 1000)
        self.assertEqual(rec.buy_datetime, dt)

    def test_on_trade_store_failure_falls_back_to_memory(self):
        """store 写入抛异常时，内存仍更新，on_trade 不阻断"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)
        engine.store = MagicMock()
        engine.store.append_trade.side_effect = RuntimeError("db down")

        dt = datetime(2024, 2, 24, 9, 30)
        trade = self._make_trade("000001", Direction.LONG, 1000, dt, "t1")
        engine.on_trade(trade)   # 不抛异常

        self.assertEqual(engine.t1_rules.positions["000001"][0].volume, 1000)

    def test_on_trade_duplicate_trade_id_is_idempotent(self):
        """重复 vt_tradeid：append_trade 返回 0 时内存不重复记录（幂等）"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)
        engine.store = MagicMock()
        engine.store.append_trade.return_value = 0  # 重复 trade_id，DB 已忽略

        dt = datetime(2024, 2, 24, 9, 30)
        trade = self._make_trade("000001", Direction.LONG, 1000, dt, "t1")
        engine.on_trade(trade)

        # append_trade 仍被调用（去重判定发生在 DB 层）
        engine.store.append_trade.assert_called_once_with(
            "TEST.t1", "000001", Direction.LONG.value, 1000, dt
        )
        # 但内存不更新（与 DB 一致，不虚增）
        self.assertNotIn("000001", engine.t1_rules.positions)

    def test_on_trade_store_none_updates_memory_only(self):
        """store=None（纯内存模式）时 on_trade 正常更新内存，不触碰 store"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)  # store 自然为 None
        self.assertIsNone(engine.store)

        dt = datetime(2024, 2, 24, 9, 30)
        trade = self._make_trade("000001", Direction.LONG, 1000, dt, "t1")
        engine.on_trade(trade)

        self.assertEqual(engine.t1_rules.positions["000001"][0].volume, 1000)
        self.assertEqual(engine.t1_rules.positions["000001"][0].buy_datetime, dt)

    def test_on_trade_short_direction_double_writes(self):
        """SHORT 成交：先落库后内存 FIFO 扣减"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)
        engine.store = MagicMock()
        engine.store.append_trade.return_value = 1
        # 预置持仓 1000（前日买入）
        engine.t1_rules.record_buy("000001", 1000, datetime(2024, 2, 23, 9, 30))

        dt = datetime(2024, 2, 24, 14, 0)
        trade = self._make_trade("000001", Direction.SHORT, 300, dt, "t2")
        engine.on_trade(trade)

        engine.store.append_trade.assert_called_once_with(
            "TEST.t2", "000001", Direction.SHORT.value, 300, dt
        )
        # FIFO 扣减：1000 - 300 = 700
        self.assertEqual(engine.t1_rules.positions["000001"][0].available, 700)


if __name__ == '__main__':
    unittest.main()
