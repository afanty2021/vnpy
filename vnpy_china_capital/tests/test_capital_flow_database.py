"""
Tests for CapitalFlowDatabase - REQ-008 资金流水数据库操作

测试数据库表的创建、资金流水的保存和查询功能。
"""

import os
import sys
# 项目根目录（本文件上溯三级：tests -> vnpy_china_capital -> 项目根）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, date, timedelta
from typing import Optional
import pytest
from unittest.mock import Mock, MagicMock, patch

from vnpy_china_capital.database import CapitalFlowDatabase
from vnpy_china_capital.objects.capital_flow import CapitalFlowData
from vnpy.trader.constant import Direction, Offset, Exchange
from vnpy.trader.object import TradeData, AccountData


class TestCapitalFlowDatabase:
    """资金流水数据库操作测试"""

    @pytest.fixture
    def mock_db_layer(self):
        """创建模拟的数据库层"""
        mock_db = Mock()
        mock_db.create_capital_flow_table = Mock(return_value=True)
        mock_db.save_capital_flow = Mock(return_value=True)
        mock_db.query_capital_flow = Mock(return_value=[])
        mock_db._execute_sql = Mock(return_value=True)
        return mock_db

    @pytest.fixture
    def capital_flow_db(self, mock_db_layer):
        """创建CapitalFlowDatabase实例"""
        return CapitalFlowDatabase(mock_db_layer)

    @pytest.fixture
    def sample_flow(self):
        """创建示例资金流水"""
        return CapitalFlowData(
            flow_id="TEST_trade_001",
            gateway_name="TEST",
            trade_id="trade_001",
            symbol="000001",
            exchange="SZSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000.0,
            amount=10500.0,
            balance=50000.0,
            available=39500.0,
            trade_time=datetime.now(),
            created_at=datetime.now(),
            flow_type="trade",
            description="买入平安银行"
        )

    def test_init_tables(self, capital_flow_db, mock_db_layer):
        """测试初始化数据库表"""
        result = capital_flow_db.init_tables()
        assert result is True
        mock_db_layer.create_capital_flow_table.assert_called_once()

    def test_save_capital_flow(self, capital_flow_db, mock_db_layer, sample_flow):
        """测试保存资金流水"""
        result = capital_flow_db.save_capital_flow(sample_flow)
        assert result is True
        mock_db_layer.save_capital_flow.assert_called_once_with(sample_flow)

    def test_save_capital_flow_from_trade(self, capital_flow_db, mock_db_layer):
        """测试从成交数据创建资金流水"""
        trade_time = datetime.now()

        trade_data = TradeData(
            gateway_name="TEST",
            symbol="600000",
            exchange=Exchange.SSE,
            orderid="order_001",
            tradeid="trade_002",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000,
            datetime=trade_time,
        )

        # AccountData 没有 available 参数，它通过 balance - frozen 自动计算
        account_data = AccountData(
            gateway_name="TEST",
            accountid="account_001",
            balance=50000.0,
            frozen=500.0,  # available = balance - frozen = 49500.0
        )

        flow = capital_flow_db.save_capital_flow_from_trade(
            trade=trade_data,
            account=account_data,
            flow_type="trade",
            description="买入浦发银行"
        )

        assert flow is not None
        assert flow.symbol == "600000"
        assert flow.amount == 10500.0
        assert flow.balance == 50000.0
        assert flow.available == 49500.0
        assert flow.flow_type == "trade"
        mock_db_layer.save_capital_flow.assert_called_once()

    def test_query_capital_flow(self, capital_flow_db, mock_db_layer, sample_flow):
        """测试查询资金流水"""
        mock_db_layer.query_capital_flow.return_value = [
            {
                "flow_id": "TEST_trade_001",
                "gateway_name": "TEST",
                "trade_id": "trade_001",
                "symbol": "000001",
                "exchange": "SZSE",
                "direction": "多",
                "offset": "开",
                "price": 10.50,
                "volume": 1000.0,
                "amount": 10500.0,
                "balance": 50000.0,
                "available": 39500.0,
                "trade_time": datetime.now(),
                "created_at": datetime.now(),
                "flow_type": "trade",
                "description": "买入平安银行"
            }
        ]

        flows = capital_flow_db.query_capital_flow(
            symbol="000001",
            flow_type="trade"
        )

        assert len(flows) == 1
        assert flows[0].symbol == "000001"
        assert flows[0].flow_type == "trade"

    def test_query_capital_flow_by_symbol(self, capital_flow_db, mock_db_layer):
        """测试按股票代码查询资金流水"""
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - 30)

        mock_db_layer.query_capital_flow.return_value = []

        capital_flow_db.query_capital_flow_by_symbol(symbol="000001", days=30)

        mock_db_layer.query_capital_flow.assert_called_once_with(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            symbol="000001",
            flow_type=None
        )

    def test_get_latest_capital_flow(self, capital_flow_db, mock_db_layer):
        """测试获取最新资金流水"""
        mock_db_layer.query_capital_flow.return_value = [
            {
                "flow_id": "TEST_trade_002",
                "gateway_name": "TEST",
                "trade_id": "trade_002",
                "symbol": "000001",
                "exchange": "SZSE",
                "direction": "多",
                "offset": "开",
                "price": 11.00,
                "volume": 1000.0,
                "amount": 11000.0,
                "balance": 50000.0,
                "available": 39000.0,
                "trade_time": datetime.now(),
                "created_at": datetime.now(),
                "flow_type": "trade",
                "description": "最新交易"
            }
        ]

        flow = capital_flow_db.get_latest_capital_flow(symbol="000001")

        assert flow is not None
        assert flow.symbol == "000001"
        assert flow.description == "最新交易"

    def test_get_latest_capital_flow_empty(self, capital_flow_db, mock_db_layer):
        """测试获取最新资金流水（无数据）"""
        mock_db_layer.query_capital_flow.return_value = []

        flow = capital_flow_db.get_latest_capital_flow(symbol="999999")

        assert flow is None

    def test_import_historical_flows(self, capital_flow_db, mock_db_layer, sample_flow):
        """测试批量导入历史流水（有效 rowcount）"""
        flows = [sample_flow] * 10
        mock_db_layer._execute_sql.return_value = 10  # 批量返回有效影响行数

        count = capital_flow_db.import_historical_flows(flows)

        assert count == 10

    def test_import_historical_flows_degrade_on_invalid_result(self, capital_flow_db, mock_db_layer, sample_flow):
        """C2: _execute_sql 返回无效值时降级逐条确认（不谎报 len(flows)）"""
        flows = [sample_flow] * 3
        mock_db_layer._execute_sql.return_value = None  # 批量未返回有效 rowcount
        mock_db_layer.save_capital_flow.side_effect = [True, False, True]  # 第2条失败

        count = capital_flow_db.import_historical_flows(flows)

        # 旧代码会谎报 len(flows)=3；新代码降级逐条返回真实成功数 2
        assert count == 2

    def test_delete_duplicate_flows(self, capital_flow_db, mock_db_layer):
        """测试删除重复流水"""
        mock_db_layer._execute_sql.return_value = 5

        count = capital_flow_db.delete_duplicate_flows()

        assert count == 5

    def test_get_flow_statistics(self, capital_flow_db, mock_db_layer):
        """测试获取资金流水统计"""
        mock_db_layer._execute_sql.return_value = [
            {
                "flow_type": "trade",
                "count": 10,
                "total_amount": 105000.0,
                "symbol_count": 3
            },
            {
                "flow_type": "fee",
                "count": 10,
                "total_amount": 50.0,
                "symbol_count": 5
            }
        ]

        stats = capital_flow_db.get_flow_statistics()

        assert "trade" in stats
        assert stats["trade"]["count"] == 10
        assert stats["trade"]["total_amount"] == 105000.0
        assert stats["trade"]["symbol_count"] == 3

        assert "fee" in stats
        assert stats["fee"]["count"] == 10
        assert stats["fee"]["total_amount"] == 50.0

    def test_get_daily_flow_summary(self, capital_flow_db, mock_db_layer):
        """测试获取每日流水汇总"""
        today = date.today()

        mock_db_layer._execute_sql.return_value = [
            {
                "symbol": "000001",
                "exchange": "SZSE",
                "flow_type": "trade",
                "count": 2,
                "total_amount": 21000.0,
                "avg_amount": 10500.0,
                "first_time": datetime.now(),
                "last_time": datetime.now()
            }
        ]

        summary = capital_flow_db.get_daily_flow_summary(target_date=today)

        assert len(summary) == 1
        assert summary[0]["symbol"] == "000001"
        assert summary[0]["total_amount"] == 21000.0
        mock_db_layer._execute_sql.assert_called_once()

    def test_query_with_date_filter(self, capital_flow_db, mock_db_layer):
        """测试带日期过滤的查询"""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 31)

        mock_db_layer.query_capital_flow.return_value = []

        capital_flow_db.query_capital_flow(
            start_date=start_date,
            end_date=end_date
        )

        mock_db_layer.query_capital_flow.assert_called_once_with(
            start_date="2026-01-01",
            end_date="2026-01-31",
            symbol=None,
            flow_type=None
        )

    def test_query_with_all_filters(self, capital_flow_db, mock_db_layer):
        """测试带所有过滤条件的查询"""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 31)

        mock_db_layer.query_capital_flow.return_value = []

        capital_flow_db.query_capital_flow(
            start_date=start_date,
            end_date=end_date,
            symbol="000001",
            flow_type="trade"
        )

        mock_db_layer.query_capital_flow.assert_called_once_with(
            start_date="2026-01-01",
            end_date="2026-01-31",
            symbol="000001",
            flow_type="trade"
        )


class TestCapitalFlowDatabaseIntegration:
    """集成测试：测试完整的数据流"""

    def test_full_workflow(self):
        """测试完整的资金流水工作流"""
        # 创建模拟数据库层
        mock_db = Mock()
        mock_db.create_capital_flow_table = Mock(return_value=True)
        mock_db.save_capital_flow = Mock(return_value=True)
        mock_db.query_capital_flow = Mock(return_value=[])

        # 创建CapitalFlowDatabase实例
        db = CapitalFlowDatabase(mock_db)

        # 1. 初始化表
        assert db.init_tables() is True

        # 2. 创建资金流水
        trade_time = datetime.now()
        flow = CapitalFlowData(
            flow_id="TEST_trade_001",
            gateway_name="TEST",
            trade_id="trade_001",
            symbol="000001",
            exchange="SZSE",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.50,
            volume=1000.0,
            amount=10500.0,
            balance=50000.0,
            available=39500.0,
            trade_time=trade_time,
            created_at=datetime.now(),
            flow_type="trade",
            description="买入平安银行"
        )

        # 3. 保存资金流水
        assert db.save_capital_flow(flow) is True

        # 4. 验证调用
        mock_db.save_capital_flow.assert_called_once_with(flow)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
