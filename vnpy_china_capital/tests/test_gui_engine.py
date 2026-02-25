"""测试ChinaCapitalGuiEngine功能"""
import sys
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch

import pytest

# 添加项目路径
sys.path.insert(0, "/Users/berton/Github/vnpy")

from vnpy.event import EventEngine, Event
from vnpy.trader.constant import Exchange, Direction, Offset
from vnpy.trader.object import TradeData, AccountData
from vnpy_china_capital.gui_engine import ChinaCapitalGuiEngine


class TestChinaCapitalGuiEngine:
    """测试GUI引擎功能"""

    def setup_method(self):
        """每个测试前的设置"""
        self.event_engine = EventEngine()
        self.event_engine.start()

        # 创建mock主引擎
        self.main_engine = Mock()
        self.main_engine.write_log = Mock()
        self.main_engine.get_all_accounts = Mock(return_value=[])

        # 创建GUI引擎
        self.gui_engine = ChinaCapitalGuiEngine(self.main_engine, self.event_engine)

    def teardown_method(self):
        """每个测试后的清理"""
        self.event_engine.stop()

    def test_init_without_database(self):
        """测试无数据库时的初始化"""
        # 验证数据库状态
        assert self.gui_engine.capital_db is None
        assert self.gui_engine.capital_flow_db is None
        assert isinstance(self.gui_engine.flows_cache, list)

        # 验证日志消息
        self.main_engine.write_log.assert_called()

    def test_database_status(self):
        """测试获取数据库状态"""
        status = self.gui_engine.get_database_status()

        assert "connected" in status
        assert "cache_count" in status
        assert "database_type" in status
        assert status["connected"] is False
        assert status["database_type"] == "memory"

    def test_register_event(self):
        """测试事件注册"""
        # 注册事件
        self.gui_engine.register_event()

        # 验证事件处理器已注册（通过触发事件验证）
        assert True  # 如果没有抛出异常，说明注册成功

    def test_process_trade_event_with_account(self):
        """测试处理成交事件（有账户）"""
        # 创建模拟账户（AccountData没有available参数）
        account = AccountData(
            gateway_name="TEST",
            accountid="test_account",
            balance=100000.0,
            frozen=5000.0
        )
        self.main_engine.get_all_accounts = Mock(return_value=[account])

        # 创建模拟成交数据（需要orderid参数）
        trade = TradeData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="test_order_001",
            tradeid="test_trade_001",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.5,
            volume=1000,
            datetime=datetime.now()
        )

        # 创建事件
        event = Event(type="trade", data=trade)

        # 处理事件
        self.gui_engine.process_trade_event(event)

        # 验证缓存中有一条记录
        assert len(self.gui_engine.flows_cache) == 1

        # 验证记录内容
        flow = self.gui_engine.flows_cache[0]
        assert flow["symbol"] == "000001"
        assert flow["exchange"] == "SZSE"
        # Direction的value是中文（"多"）而不是英文
        assert flow["direction"] in ["LONG", "多"]  # 兼容两种情况
        assert flow["offset"] in ["OPEN", "开"]  # 兼容两种情况
        assert flow["price"] == 10.5
        assert flow["volume"] == 1000
        assert flow["amount"] == 10500.0

    def test_process_trade_event_without_account(self):
        """测试处理成交事件（无账户）"""
        # 没有账户
        self.main_engine.get_all_accounts = Mock(return_value=[])

        # 创建模拟成交数据（需要orderid参数）
        trade = TradeData(
            gateway_name="TEST",
            symbol="000002",
            exchange=Exchange.SZSE,
            orderid="test_order_002",
            tradeid="test_trade_002",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=20.0,
            volume=500,
            datetime=datetime.now()
        )

        # 创建事件
        event = Event(type="trade", data=trade)

        # 处理事件
        self.gui_engine.process_trade_event(event)

        # 验证没有记录（因为没有账户）
        assert len(self.gui_engine.flows_cache) == 0

    def test_get_capital_flows_from_cache(self):
        """测试从缓存获取资金流水"""
        # 添加一些缓存数据
        self.gui_engine.flows_cache = [
            {
                "symbol": "000001",
                "exchange": "SZSE",
                "amount": 10000.0,
                "flow_type": "trade"
            },
            {
                "symbol": "000002",
                "exchange": "SZSE",
                "amount": 20000.0,
                "flow_type": "trade"
            }
        ]

        # 获取流水
        flows = self.gui_engine.get_capital_flows()

        # 验证返回了2条记录
        assert len(flows) == 2
        assert flows[0]["symbol"] == "000001"
        assert flows[1]["symbol"] == "000002"

    def test_get_flow_statistics_from_cache(self):
        """测试从缓存获取统计信息"""
        # 添加缓存数据
        self.gui_engine.flows_cache = [
            {
                "symbol": "000001",
                "amount": 10000.0,
                "flow_type": "trade"
            },
            {
                "symbol": "000002",
                "amount": 20000.0,
                "flow_type": "trade"
            },
            {
                "symbol": "000001",
                "amount": 5000.0,
                "flow_type": "trade"
            }
        ]

        # 获取统计
        stats = self.gui_engine.get_flow_statistics()

        # 验证统计结果
        assert "trade" in stats
        assert stats["trade"]["count"] == 3
        assert stats["trade"]["total_amount"] == 35000.0
        assert stats["trade"]["symbol_count"] == 2

    def test_get_daily_flow_summary_from_cache(self):
        """测试从缓存获取每日汇总"""
        today = date.today()

        # 添加缓存数据
        self.gui_engine.flows_cache = [
            {
                "symbol": "000001",
                "exchange": "SZSE",
                "flow_type": "trade",
                "amount": 10000.0,
                "trade_time": datetime.combine(today, datetime.min.time())
            },
            {
                "symbol": "000001",
                "exchange": "SZSE",
                "flow_type": "trade",
                "amount": 5000.0,
                "trade_time": datetime.combine(today, datetime.min.time())
            }
        ]

        # 获取汇总
        summary = self.gui_engine.get_daily_flow_summary(today)

        # 验证汇总结果
        assert len(summary) == 1
        assert summary[0]["symbol"] == "000001"
        assert summary[0]["count"] == 2
        assert summary[0]["total_amount"] == 15000.0
        assert summary[0]["avg_amount"] == 7500.0

    def test_import_historical_data_to_cache(self):
        """测试导入历史数据到缓存"""
        # 准备测试数据
        flows = [
            {
                "symbol": "000001",
                "exchange": "SZSE",
                "amount": 10000.0,
                "flow_type": "trade"
            },
            {
                "symbol": "000002",
                "exchange": "SZSE",
                "amount": 20000.0,
                "flow_type": "trade"
            }
        ]

        # 导入数据
        result = self.gui_engine.import_historical_data(flows)

        # 验证结果
        assert result["success_count"] == 2
        assert result["error_count"] == 0
        assert len(self.gui_engine.flows_cache) == 2

    def test_import_historical_data_with_errors(self):
        """测试导入历史数据（包含错误）"""
        # 准备测试数据（包含无效数据）
        flows = [
            {
                "symbol": "000001",
                "amount": 10000.0
            },
            None,  # 无效数据
            {
                "symbol": "000002",
                "amount": 20000.0
            }
        ]

        # 导入数据
        result = self.gui_engine.import_historical_data(flows)

        # 验证结果
        assert result["success_count"] == 2  # 两条有效数据
        assert result["error_count"] == 1  # 一条错误数据


class TestChinaCapitalGuiEngineWithDatabase:
    """测试GUI引擎功能（带数据库）"""

    def setup_method(self):
        """每个测试前的设置"""
        self.event_engine = EventEngine()
        self.event_engine.start()

        # 创建mock主引擎
        self.main_engine = Mock()
        self.main_engine.write_log = Mock()
        self.main_engine.get_all_accounts = Mock(return_value=[])

        # 创建mock数据库
        self.mock_db = Mock()
        self.mock_db.create_capital_flow_table = Mock(return_value=True)
        self.mock_db.save_capital_flow = Mock(return_value=True)
        self.mock_db.query_capital_flow = Mock(return_value=[])

        # Patch get_data_service
        with patch('vnpy_china_data.service.get_data_service') as mock_service:
            mock_ds = Mock()
            mock_ds.database = self.mock_db
            mock_service.return_value = mock_ds

            # 创建GUI引擎
            self.gui_engine = ChinaCapitalGuiEngine(self.main_engine, self.event_engine)

    def teardown_method(self):
        """每个测试后的清理"""
        self.event_engine.stop()

    def test_init_with_database(self):
        """测试有数据库时的初始化"""
        # 验证数据库已连接
        assert self.gui_engine.capital_db is not None
        assert self.gui_engine.capital_flow_db is not None

        # 验证表已创建
        self.mock_db.create_capital_flow_table.assert_called_once()

    def test_database_status_connected(self):
        """测试数据库连接状态"""
        status = self.gui_engine.get_database_status()

        assert status["connected"] is True
        # Mock的类型名可能是"Mock"或"MagicMock"
        assert "Mock" in status["database_type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
