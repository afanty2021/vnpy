"""Tests for CapitalFlowData - REQ-008 资金流水数据模型"""

import sys
sys.path.insert(0, '/Users/berton/Github/vnpy')

import pytest
from datetime import datetime

from vnpy_china_capital.objects.capital_flow import CapitalFlowData
from vnpy.trader.constant import Direction, Offset


class TestCapitalFlowData:
    """资金流水数据测试"""

    def test_capital_flow_data_creation(self):
        """测试资金流水数据创建"""
        flow = CapitalFlowData(
            flow_id="test_flow_1",
            gateway_name="TEST",
            trade_id="trade_001",
            symbol="000001",
            exchange="SZSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000,
            amount=10500.0,
            balance=50000.0,
            available=39500.0,
            trade_time=datetime.now(),
            created_at=datetime.now(),
            flow_type="trade",
            description="买入平安银行"
        )

        assert flow.symbol == "000001"
        assert flow.amount == 10500.0
        assert flow.flow_type == "trade"
        assert flow.description == "买入平安银行"

    def test_flow_id_auto_generation(self):
        """测试flow_id自动生成"""
        flow = CapitalFlowData(
            flow_id="",  # 空字符串，应该自动生成
            gateway_name="TEST",
            trade_id="trade_123",
            symbol="600000",
            exchange="SSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.0,
            volume=100,
            amount=1000.0,
            balance=10000.0,
            available=9000.0,
            trade_time=datetime.now(),
            created_at=datetime.now(),
            flow_type="trade"
        )

        assert flow.flow_id == "TEST_trade_123"

    def test_vt_symbol_property(self):
        """测试vt_symbol属性"""
        flow = CapitalFlowData(
            flow_id="test",
            gateway_name="TEST",
            trade_id="trade_001",
            symbol="000001",
            exchange="SZSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000,
            amount=10500.0,
            balance=50000.0,
            available=39500.0,
            trade_time=datetime.now(),
            created_at=datetime.now(),
            flow_type="trade"
        )

        assert flow.vt_symbol == "000001.SZSE"

    def test_to_db_dict(self):
        """测试转换为数据库字典"""
        trade_time = datetime.now()
        created_at = datetime.now()

        flow = CapitalFlowData(
            flow_id="test_flow_1",
            gateway_name="TEST",
            trade_id="trade_001",
            symbol="000001",
            exchange="SZSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000,
            amount=10500.0,
            balance=50000.0,
            available=39500.0,
            trade_time=trade_time,
            created_at=created_at,
            flow_type="trade",
            description="测试"
        )

        db_dict = flow.to_db_dict()

        assert db_dict["flow_id"] == "test_flow_1"
        assert db_dict["symbol"] == "000001"
        assert db_dict["exchange"] == "SZSE"
        assert db_dict["direction"] == "多"  # Direction.LONG.value
        assert db_dict["offset"] == "开"     # Offset.OPEN.value
        assert db_dict["price"] == 10.50
        assert db_dict["amount"] == 10500.0
        assert db_dict["flow_type"] == "trade"
        assert db_dict["description"] == "测试"

    def test_from_db_dict(self):
        """测试从数据库字典创建对象"""
        trade_time = datetime.now()
        created_at = datetime.now()

        db_dict = {
            "flow_id": "test_flow_1",
            "gateway_name": "TEST",
            "trade_id": "trade_001",
            "symbol": "000001",
            "exchange": "SZSE",
            "direction": "多",
            "offset": "开",
            "price": 10.50,
            "volume": 1000,
            "amount": 10500.0,
            "balance": 50000.0,
            "available": 39500.0,
            "trade_time": trade_time,
            "created_at": created_at,
            "flow_type": "trade",
            "description": "测试"
        }

        flow = CapitalFlowData.from_db_dict(db_dict)

        assert flow.flow_id == "test_flow_1"
        assert flow.symbol == "000001"
        assert flow.exchange == "SZSE"
        assert flow.direction == Direction.LONG
        assert flow.offset == Offset.OPEN
        assert flow.price == 10.50
        assert flow.amount == 10500.0
        assert flow.flow_type == "trade"
        assert flow.description == "测试"

    def test_from_trade_data(self):
        """测试从TradeData创建资金流水"""
        from vnpy.trader.object import TradeData, AccountData
        from vnpy.trader.constant import Exchange

        trade_time = datetime.now()

        # 创建模拟的TradeData
        trade_data = TradeData(
            gateway_name="TEST",
            symbol="600000",
            exchange=Exchange.SSE,
            orderid="order_001",
            tradeid="trade_001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000,
            datetime=trade_time,
        )

        # 创建模拟的AccountData
        account_data = AccountData(
            gateway_name="TEST",
            accountid="account_001",
            balance=50000.0,
            frozen=500.0,
        )

        # 从TradeData创建资金流水
        flow = CapitalFlowData.from_trade_data(
            trade_data=trade_data,
            account_data=account_data,
            flow_type="trade",
            description="买入浦发银行"
        )

        assert flow.gateway_name == "TEST"
        assert flow.trade_id == "trade_001"
        assert flow.symbol == "600000"
        assert flow.exchange == "SSE"
        assert flow.direction == Direction.LONG
        assert flow.offset == Offset.OPEN
        assert flow.price == 10.50
        assert flow.volume == 1000
        assert flow.amount == 10500.0  # price * volume
        assert flow.balance == 50000.0
        assert flow.available == 49500.0  # balance - frozen
        assert flow.flow_type == "trade"
        assert flow.description == "买入浦发银行"
        assert flow.flow_id == "TEST_trade_001"  # 自动生成

    def test_description_default_value(self):
        """测试description字段的默认值"""
        flow = CapitalFlowData(
            flow_id="test",
            gateway_name="TEST",
            trade_id="trade_001",
            symbol="000001",
            exchange="SZSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000,
            amount=10500.0,
            balance=50000.0,
            available=39500.0,
            trade_time=datetime.now(),
            created_at=datetime.now(),
            flow_type="trade"
            # 不提供description，应该使用默认值
        )

        assert flow.description == ""

    def test_flow_type_values(self):
        """测试不同的流水类型"""
        flow_types = ["trade", "transfer", "fee", "withdraw", "deposit"]

        for flow_type in flow_types:
            flow = CapitalFlowData(
                flow_id=f"test_{flow_type}",
                gateway_name="TEST",
                trade_id=f"trade_{flow_type}",
                symbol="000001",
                exchange="SZSE",
                direction=Direction.LONG,
                offset=Offset.OPEN,
                price=10.50,
                volume=1000,
                amount=10500.0,
                balance=50000.0,
                available=39500.0,
                trade_time=datetime.now(),
                created_at=datetime.now(),
                flow_type=flow_type
            )

            assert flow.flow_type == flow_type

    def test_from_db_dict_with_null_direction_offset(self):
        """测试从数据库字典创建对象时处理NULL的direction和offset字段

        对于非交易类型的流水（如转账、出入金），direction和offset字段在数据库中可能为NULL。
        此测试验证from_db_dict方法能正确处理这种情况。
        """
        trade_time = datetime.now()
        created_at = datetime.now()

        # 模拟数据库中非交易类型的流水记录（direction和offset为NULL）
        db_dict = {
            "flow_id": "flow_withdraw_1",
            "gateway_name": "TEST",
            "trade_id": "withdraw_001",
            "symbol": "",
            "exchange": "",
            "direction": None,  # NULL值
            "offset": None,     # NULL值
            "price": 0.0,
            "volume": 0.0,
            "amount": 5000.0,   # 出金金额
            "balance": 45000.0,
            "available": 45000.0,
            "trade_time": trade_time,
            "created_at": created_at,
            "flow_type": "withdraw",
            "description": "银证转账转出"
        }

        # 应该能够正常创建对象，不会抛出ValueError
        flow = CapitalFlowData.from_db_dict(db_dict)

        assert flow.flow_id == "flow_withdraw_1"
        assert flow.direction is None  # NULL值应转换为None
        assert flow.offset is None     # NULL值应转换为None
        assert flow.flow_type == "withdraw"
        assert flow.amount == 5000.0
