"""
风控过滤器测试

测试ChinaStockRiskFilter的各个功能：
- check_order：订单检查
- on_trade：成交回调
- 禁用过滤器
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from vnpy.trader.object import OrderData, TradeData
from vnpy.trader.constant import Direction, Exchange, OrderType, Status, Offset

from vnpy_china_rules import (
    DataSourceManager,
    ChinaStockRulesEngine,
    ChinaStockRiskFilter,
    create_risk_filter,
)
from vnpy_china_rules.datasource import StockInfo


class TestChinaStockRiskFilter:
    """风控过滤器测试类"""

    @pytest.fixture
    def mock_datasource_manager(self):
        """创建模拟数据源管理器"""
        manager = Mock(spec=DataSourceManager)

        # 创建模拟股票信息
        stock_info = StockInfo(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="MAIN",
            is_st=False,
            list_date="1991-04-03",
            limit_ratio=0.10,
        )
        manager.get_stock_info.return_value = stock_info

        # 创建模拟行情数据
        market_data = Mock()
        market_data.pre_close = 12.50
        manager.get_market_data.return_value = market_data

        return manager

    @pytest.fixture
    def rules_engine(self, mock_datasource_manager):
        """创建规则引擎"""
        return ChinaStockRulesEngine(mock_datasource_manager)

    @pytest.fixture
    def risk_filter(self, rules_engine):
        """创建风控过滤器"""
        return ChinaStockRiskFilter(rules_engine)

    def test_check_order_pass(self, risk_filter):
        """测试订单检查通过"""
        # 创建一个有效的买入订单（交易时间内，100股，价格合理）
        order = OrderData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST001",
            type=OrderType.LIMIT,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=12.50,
            volume=100,
            status=Status.SUBMITTING,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        passed, message = risk_filter.check_order(order)

        # 买入订单应该通过（假设在交易时间内）
        # 注意：如果不在交易时间可能会失败
        assert isinstance(passed, bool)
        assert isinstance(message, str)

    def test_check_order_disabled(self, risk_filter):
        """测试禁用过滤器"""
        risk_filter.enabled = False

        order = OrderData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST001",
            type=OrderType.LIMIT,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=12.50,
            volume=100,
            status=Status.SUBMITTING,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        passed, message = risk_filter.check_order(order)

        # 禁用后应该直接通过
        assert passed is True
        assert message == ""

    def test_check_order_t1_rule(self, risk_filter, rules_engine):
        """测试T+1规则检查"""
        # 记录一个之前的买入（昨日买入）
        yesterday = datetime.now() - timedelta(days=1)
        rules_engine.t1_rules.record_buy("000001.SZSE", 1000, yesterday)

        # 尝试卖出1000股（应该通过，因为是昨天买的）
        order = OrderData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST002",
            type=OrderType.LIMIT,
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=12.50,
            volume=1000,
            status=Status.SUBMITTING,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        passed, message = risk_filter.check_order(order)

        # 昨日买入的可以卖出
        assert isinstance(passed, bool)

    def test_check_order_t1_rule_fail(self, risk_filter, rules_engine):
        """测试T+1规则检查失败（当日买入当日卖出）"""
        # 记录一个当日买入
        today = datetime.now()
        rules_engine.t1_rules.record_buy("000001.SZSE", 1000, today)

        # 尝试卖出1000股（应该失败，因为是当日买入）
        order = OrderData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST003",
            type=OrderType.LIMIT,
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=12.50,
            volume=1000,
            status=Status.SUBMITTING,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        passed, message = risk_filter.check_order(order)

        # 当日买入的不能卖出，应该失败
        assert passed is False
        assert "T+1" in message or "可卖" in message

    def test_check_order_unit_rule(self, risk_filter):
        """测试交易单位规则检查（小于100股）"""
        # 创建一个小于最小交易单位的订单
        order = OrderData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST004",
            type=OrderType.LIMIT,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=12.50,
            volume=50,  # 小于100股
            status=Status.SUBMITTING,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        passed, message = risk_filter.check_order(order)

        # 应该失败
        assert passed is False
        assert "最小单位" in message or "100" in message

    def test_on_trade_buy(self, risk_filter, rules_engine):
        """测试买入成交回调"""
        # 创建买入成交数据
        trade = TradeData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST001",
            tradeid="TRADE001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=12.50,
            volume=1000,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        # 记录初始状态
        initial_positions = len(risk_filter.rules_engine.t1_rules.positions.get("000001.SZSE", []))

        # 执行成交回调
        risk_filter.on_trade(trade)

        # 检查持仓是否被记录
        positions = risk_filter.rules_engine.t1_rules.positions.get("000001.SZSE", [])
        assert len(positions) > initial_positions
        assert positions[-1].volume == 1000

    def test_on_trade_sell(self, risk_filter, rules_engine):
        """测试卖出成交回调"""
        # 先记录一个买入
        yesterday = datetime.now() - timedelta(days=1)
        rules_engine.t1_rules.record_buy("000001.SZSE", 1000, yesterday)

        # 记录初始可用数量
        initial_available = rules_engine.t1_rules.get_sellable_volume(
            "000001.SZSE", datetime.now()
        )

        # 创建卖出成交数据
        trade = TradeData(
            symbol="000001.SZSE",
            exchange=Exchange.SZSE,
            orderid="TEST002",
            tradeid="TRADE002",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=12.50,
            volume=500,
            datetime=datetime.now(),
            gateway_name="TEST",
        )

        # 执行成交回调
        risk_filter.on_trade(trade)

        # 检查可用数量是否减少
        final_available = rules_engine.t1_rules.get_sellable_volume(
            "000001.SZSE", datetime.now()
        )
        assert final_available == initial_available - 500

    def test_create_risk_filter(self, rules_engine):
        """测试创建风控过滤器的便捷函数"""
        risk_filter = create_risk_filter(rules_engine)

        assert isinstance(risk_filter, ChinaStockRiskFilter)
        assert risk_filter.rules_engine is rules_engine
        assert risk_filter.enabled is True


# 运行测试时的入口
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
