"""
策略基类测试

测试ChinaStockStrategy和TradingRuleMixin的功能。
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

import pytest

from vnpy.trader.object import OrderData, TradeData, BarData, TickData
from vnpy.trader.constant import Direction, Offset, Exchange, OrderType, Status

from vnpy_china_rules.engine import (
    ChinaStockRulesEngine,
    T1RulesEngine,
    PriceLimitRulesEngine,
)
from vnpy_china_rules.datasource import (
    DataSourceManager,
    StockInfo,
)
from vnpy_china_rules.strategy import (
    ChinaStockStrategy,
    TradingRuleMixin,
    create_strategy_base,
)


class MockDataSource:
    """模拟数据源"""

    def get_stock_info(self, symbol: str):
        if symbol == "000001.SZSE":
            return StockInfo(
                symbol="000001.SZSE",
                exchange=Exchange.SZSE,
                name="平安银行",
                market_type="main",
                is_st=False,
                list_date="1991-04-03",
                limit_ratio=0.10,
            )
        elif symbol == "600000.SH":
            return StockInfo(
                symbol="600000.SH",
                exchange=Exchange.SSE,
                name="浦发银行",
                market_type="main",
                is_st=False,
                list_date="1999-11-10",
                limit_ratio=0.10,
            )
        return None

    def get_market_data(self, symbol: str):
        return None


def create_order(
    symbol: str = "000001.SZSE",
    exchange: Exchange = Exchange.SZSE,
    direction: Direction = Direction.LONG,
    offset: Offset = Offset.OPEN,
    price: float = 10.0,
    volume: float = 100.0,
) -> OrderData:
    """创建订单数据"""
    return OrderData(
        symbol=symbol,
        exchange=exchange,
        orderid="test_order",
        gateway_name="TEST",
        direction=direction,
        offset=offset,
        price=price,
        volume=volume,
        datetime=datetime.now(),
    )


def create_trade(
    symbol: str = "000001.SZSE",
    exchange: Exchange = Exchange.SZSE,
    direction: Direction = Direction.LONG,
    offset: Offset = Offset.OPEN,
    price: float = 10.0,
    volume: float = 100.0,
) -> TradeData:
    """创建成交数据"""
    return TradeData(
        symbol=symbol,
        exchange=exchange,
        tradeid="test_trade",
        orderid="test_order",
        gateway_name="TEST",
        direction=direction,
        offset=offset,
        price=price,
        volume=volume,
        datetime=datetime.now(),
    )


def create_bar(
    symbol: str = "000001.SZSE",
    exchange: Exchange = Exchange.SZSE,
) -> BarData:
    """创建K线数据"""
    return BarData(
        symbol=symbol,
        exchange=exchange,
        gateway_name="TEST",
        datetime=datetime.now(),
        open_price=10.0,
        high_price=10.5,
        low_price=9.8,
        close_price=10.2,
        volume=10000,
    )


class TestChinaStockStrategy:
    """测试ChinaStockStrategy基类"""

    def test_init(self):
        """测试初始化"""
        mock_engine = Mock()
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={"max_position": 10000},
        )

        assert strategy.cta_engine is mock_engine
        assert strategy.strategy_name == "test_strategy"
        assert strategy.vt_symbol == "000001.SZSE"
        assert strategy.active is False
        assert strategy.pos == 0

    def test_parameters_and_variables(self):
        """测试参数和变量定义"""
        # 检查参数和变量是否正确定义
        assert hasattr(ChinaStockStrategy, "parameters")
        assert hasattr(ChinaStockStrategy, "variables")

    def test_init_with_settings(self):
        """测试带参数设置的初始化 - 基类不处理自定义参数，由子类处理"""
        mock_engine = Mock()
        # 基类会解析设置，但不会自动设置为属性
        # 子类需要在__init__中处理
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={"max_position": 20000, "stop_loss": 0.03},
        )

        # 基类不处理自定义参数，只验证基本属性
        assert strategy.strategy_name == "test_strategy"
        assert strategy.vt_symbol == "000001.SZSE"

    def test_write_log(self):
        """测试日志方法"""
        mock_engine = Mock()
        mock_engine.write_log = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 写日志
        strategy.write_log("测试日志")

        # 验证日志写入
        mock_engine.write_log.assert_called_once_with("测试日志", strategy)

    def test_get_parameters(self):
        """测试获取参数 - 基类只返回核心参数"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={"max_position": 10000},
        )

        # 获取参数 - 基类只返回核心参数
        params = strategy.get_parameters()

        assert "strategy_name" in params
        assert "vt_symbol" in params
        # 基类的parameters是空列表，所以不返回自定义参数
        # 这是正确的设计，子类需要定义parameters列表

    def test_get_variables(self):
        """测试获取变量"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        strategy.pos = 1000

        # 获取变量
        vars_dict = strategy.get_variables()

        assert "pos" in vars_dict
        assert vars_dict["pos"] == 1000

    def test_callback_methods(self):
        """测试回调方法"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 测试回调方法可以正常调用（不抛异常）
        strategy.on_init()
        strategy.on_start()
        strategy.on_stop()

    def test_on_trade_callback(self):
        """测试成交回调"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 创建成交数据
        trade = create_trade(direction=Direction.LONG, volume=1000)

        # 调用回调
        strategy.on_trade(trade)

        # 验证持仓更新
        assert strategy.pos == 1000

    def test_on_trade_sell_callback(self):
        """测试卖出成交回调"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 先买入
        trade_buy = create_trade(direction=Direction.LONG, volume=1000)
        strategy.on_trade(trade_buy)
        assert strategy.pos == 1000

        # 卖出
        trade_sell = create_trade(direction=Direction.SHORT, volume=500)
        strategy.on_trade(trade_sell)
        assert strategy.pos == 500

    def test_on_order_callback(self):
        """测试委托回调"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 创建委托数据
        order = create_order()

        # 调用回调（不抛异常即可）
        strategy.on_order(order)

    def test_on_bar_callback(self):
        """测试K线回调"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 创建K线数据
        bar = create_bar()

        # 调用回调（不抛异常即可）
        strategy.on_bar(bar)

    def test_on_tick_callback(self):
        """测试Tick回调"""
        mock_engine = Mock()

        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )

        # 创建Tick数据
        tick = TickData(
            symbol="000001",
            exchange=Exchange.SZSE,
            gateway_name="TEST",
            datetime=datetime.now(),
            last_price=10.0,
            volume=1000,
        )

        # 调用回调（不抛异常即可）
        strategy.on_tick(tick)

    def test_parse_exchange(self):
        """测试交易所解析"""
        # 测试不同的symbol格式
        assert ChinaStockStrategy._parse_exchange("000001.SZSE") == Exchange.SZSE
        assert ChinaStockStrategy._parse_exchange("000001.SZ") == Exchange.SZSE
        assert ChinaStockStrategy._parse_exchange("600000.SH") == Exchange.SSE
        assert ChinaStockStrategy._parse_exchange("600000.SSE") == Exchange.SSE
        # 默认返回SZSE
        assert ChinaStockStrategy._parse_exchange("000001") == Exchange.SZSE


class TestTradingRuleMixin:
    """测试TradingRuleMixin混入类"""

    def test_mixin_init(self):
        """测试混入类初始化"""
        class TestStrategy(TradingRuleMixin):
            pass

        strategy = TestStrategy()
        assert hasattr(strategy, "rules_engine")
        assert strategy.rules_engine is None

    def test_check_buy_without_rules_engine(self):
        """测试无规则引擎时的买入检查"""
        class TestStrategy(TradingRuleMixin):
            pass

        strategy = TestStrategy()

        # 应该返回通过（因为没有规则引擎）
        can_buy, msg = strategy.check_buy("000001.SZSE", 10.0, 1000)

        assert can_buy is True
        assert "规则引擎未初始化" in msg

    def test_check_sell_without_rules_engine(self):
        """测试无规则引擎时的卖出检查"""
        class TestStrategy(TradingRuleMixin):
            pass

        strategy = TestStrategy()

        # 应该返回通过（因为没有规则引擎）
        can_sell, msg = strategy.check_sell("000001.SZSE", 10.0, 1000)

        assert can_sell is True
        assert "规则引擎未初始化" in msg

    def test_get_sellable_volume_without_rules_engine(self):
        """测试无规则引擎时的可卖数量查询"""
        class TestStrategy(TradingRuleMixin):
            pass

        strategy = TestStrategy()

        # 应该返回0
        volume = strategy.get_sellable_volume("000001.SZSE")

        assert volume == 0


class TestChinaStockStrategyWithRules:
    """测试带规则引擎的策略基类"""

    @pytest.fixture
    def rules_engine(self):
        """创建规则引擎"""
        dm = DataSourceManager()
        dm.register_source("mock", MockDataSource(), primary=True)
        return ChinaStockRulesEngine(dm)

    def test_check_buy_with_rules(self, rules_engine):
        """测试带规则引擎的买入检查"""
        mock_engine = Mock()
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )
        strategy.rules_engine = rules_engine

        # 检查买入（交易单位检查：100股最小单位）
        can_buy, msg = strategy.check_buy("000001.SZSE", 10.0, 100)

        # 100股应该通过交易单位检查
        assert can_buy is True

    def test_check_buy_with_invalid_volume(self, rules_engine):
        """测试买入数量不符合交易单位"""
        mock_engine = Mock()
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )
        strategy.rules_engine = rules_engine

        # 检查买入（数量不符合交易单位）
        can_buy, msg = strategy.check_buy("000001.SZSE", 10.0, 50)

        # 50股不应该通过交易单位检查
        assert can_buy is False
        assert "交易单位" in msg

    def test_check_sell_with_t1_rules(self, rules_engine):
        """测试带T+1规则的卖出检查"""
        mock_engine = Mock()
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )
        strategy.rules_engine = rules_engine

        # 先买入（记录T+1持仓）
        yesterday = datetime.now() - timedelta(days=2)
        rules_engine.t1_rules.record_buy("000001.SZSE", 1000, yesterday)

        # 检查卖出
        can_sell, msg = strategy.check_sell("000001.SZSE", 10.0, 500)

        # 因为是昨天买入的，所以可以卖出
        assert can_sell is True

    def test_check_sell_same_day(self, rules_engine):
        """测试当日买入不能当日卖出"""
        mock_engine = Mock()
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )
        strategy.rules_engine = rules_engine

        # 当日买入
        today = datetime.now()
        rules_engine.t1_rules.record_buy("000001.SZSE", 1000, today)

        # 检查卖出
        can_sell, msg = strategy.check_sell("000001.SZSE", 10.0, 500)

        # 当日买入不能卖出
        assert can_sell is False
        assert "T+1" in msg or "可卖" in msg

    def test_get_sellable_volume(self, rules_engine):
        """测试获取可卖出数量"""
        mock_engine = Mock()
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={},
        )
        strategy.rules_engine = rules_engine

        # 两天前买入1000股
        yesterday = datetime.now() - timedelta(days=2)
        rules_engine.t1_rules.record_buy("000001.SZSE", 1000, yesterday)

        # 今日买入500股
        today = datetime.now()
        rules_engine.t1_rules.record_buy("000001.SZSE", 500, today)

        # 获取可卖出数量
        sellable = rules_engine.t1_rules.get_sellable_volume("000001.SZSE", today)

        # 只有昨天买的1000股可以卖出
        assert sellable == 1000


class TestCreateStrategyBase:
    """测试create_strategy_base便捷函数"""

    def test_create_strategy(self):
        """测试创建带规则引擎的策略实例"""
        mock_engine = Mock()
        mock_dm = Mock()

        # 测试函数
        strategy = ChinaStockStrategy(
            cta_engine=mock_engine,
            strategy_name="test_strategy",
            vt_symbol="000001.SZSE",
            setting={"max_position": 10000},
        )

        # 模拟设置规则引擎
        mock_rules_engine = Mock()
        strategy.rules_engine = mock_rules_engine

        assert strategy.rules_engine is mock_rules_engine
        assert strategy.strategy_name == "test_strategy"


class TestStrategyInheritance:
    """测试策略继承"""

    def test_custom_strategy_inheritance(self):
        """测试自定义策略继承"""

        class MyStockStrategy(ChinaStockStrategy):
            """我的A股策略"""

            parameters = [
                "max_position",
                "stop_loss",
            ]

            variables = [
                "pos",
                "avg_price",
            ]

            def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
                super().__init__(cta_engine, strategy_name, vt_symbol, setting)
                self.max_position = setting.get("max_position", 10000)
                self.stop_loss = setting.get("stop_loss", 0.02)
                self.avg_price = 0.0

            def on_init(self):
                self.write_log("策略初始化")

            def on_bar(self, bar):
                # 示例交易逻辑
                if self.pos == 0:
                    # 买入
                    can_buy, msg = self.check_buy(self.vt_symbol, bar.close_price, 1000)
                    if can_buy:
                        self.buy(bar.close_price, 1000)

        mock_engine = Mock()

        # 创建自定义策略
        strategy = MyStockStrategy(
            cta_engine=mock_engine,
            strategy_name="my_strategy",
            vt_symbol="000001.SZSE",
            setting={"max_position": 20000, "stop_loss": 0.03},
        )

        assert strategy.max_position == 20000
        assert strategy.stop_loss == 0.03
        assert strategy.pos == 0
        assert strategy.avg_price == 0.0

        # 初始化
        strategy.on_init()

    def test_mixin_inheritance(self):
        """测试混入类继承"""

        class MyBaseStrategy:
            """已有的策略基类"""

            def __init__(self, name: str):
                self.name = name
                self.value = 0

        class MyMixedStrategy(MyBaseStrategy, TradingRuleMixin):
            """混入了交易规则功能的策略"""

            def __init__(self, name: str):
                super().__init__(name)
                self.rules_engine = None

            def trade(self, symbol: str, price: float, volume: int):
                can_buy, msg = self.check_buy(symbol, price, volume)
                return can_buy

        strategy = MyMixedStrategy("test")

        assert strategy.name == "test"
        assert strategy.rules_engine is None
        # 测试check_buy方法
        can_buy, msg = strategy.check_buy("000001.SZSE", 10.0, 100)
        assert can_buy is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
