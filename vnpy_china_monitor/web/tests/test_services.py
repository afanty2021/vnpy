"""
服务层测试模块

测试VeighNa Web监控系统的业务服务层
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_rpc_client():
    """模拟RPC客户端"""
    client = Mock()
    return client


@pytest.fixture
def mock_event_engine():
    """模拟事件引擎"""
    engine = Mock()
    return engine


class TestMarketService:
    """行情服务测试"""

    @pytest.fixture
    def market_service(self, mock_rpc_client):
        from vnpy_china_monitor.web.services.market_service import MarketService
        return MarketService(mock_rpc_client)

    def test_get_tick(self, market_service):
        """测试获取单个行情（MarketService.get_tick 从本地缓存取，需先 update_tick）"""
        market_service.update_tick({
            "vt_symbol": "000001.SZSE",
            "last_price": 10.50,
            "volume": 1000000
        })

        tick = market_service.get_tick("000001.SZSE")
        assert tick is not None
        assert tick["vt_symbol"] == "000001.SZSE"

    def test_get_history_bars(self, market_service, mock_rpc_client):
        """测试获取K线数据"""
        mock_rpc_client.get_history_bars.return_value = [
            {
                "datetime": "2024-01-01 09:30:00",
                "open": 10.0,
                "high": 10.5,
                "low": 9.8,
                "close": 10.3,
                "volume": 10000
            }
        ]

        bars = market_service.get_history_bars("000001.SZSE", "1m")
        assert len(bars) > 0
        mock_rpc_client.get_history_bars.assert_called_once()

    def test_subscribe(self, market_service, mock_rpc_client):
        """测试订阅行情（MarketService.subscribe 通过 rpc_client.call 发起）"""
        market_service.subscribe("000001.SZSE")
        mock_rpc_client.call.assert_called_once()

    def test_format_tick(self, market_service):
        """测试行情数据格式化（format_tick(vt_symbol) 从缓存取并挑选字段）"""
        market_service.update_tick({
            "vt_symbol": "000001.SZSE",
            "last_price": 10.50,
            "volume": 1000000,
            "datetime": "2024-01-01 09:30:00"
        })

        formatted = market_service.format_tick("000001.SZSE")
        assert formatted is not None
        assert formatted["vt_symbol"] == "000001.SZSE"
        assert formatted["last_price"] == 10.50


class TestTradeService:
    """交易服务测试"""

    @pytest.fixture
    def trade_service(self, mock_rpc_client):
        from vnpy_china_monitor.web.services.trade_service import TradeService
        return TradeService(mock_rpc_client)

    def test_get_account(self, trade_service, mock_rpc_client):
        """测试获取账户信息"""
        mock_rpc_client.get_account.return_value = {
            "accountid": "test_account",
            "balance": 100000.0,
            "available": 80000.0
        }

        account = trade_service.get_account()
        assert account is not None
        assert account["accountid"] == "test_account"

    def test_get_positions(self, trade_service, mock_rpc_client):
        """测试获取持仓列表（TradeService.get_positions 调 rpc.get_position，单数）"""
        mock_rpc_client.get_position.return_value = [
            {
                "vt_symbol": "000001.SZSE",
                "direction": "多",
                "volume": 1000,
                "price": 10.50
            }
        ]

        positions = trade_service.get_positions()
        assert len(positions) > 0
        assert positions[0]["vt_symbol"] == "000001.SZSE"

    def test_send_order(self, trade_service, mock_rpc_client):
        """测试发送委托"""
        mock_rpc_client.send_order.return_value = "test_order_id"

        order_id = trade_service.send_order(
            "000001.SZSE", "多", "限价", 100, 10.50
        )
        assert order_id == "test_order_id"
        mock_rpc_client.send_order.assert_called_once()

    def test_cancel_order(self, trade_service, mock_rpc_client):
        """测试撤销委托"""
        trade_service.cancel_order("test_order_id")
        mock_rpc_client.cancel_order.assert_called_once_with("test_order_id")


class TestStrategyService:
    """策略服务测试"""

    @pytest.fixture
    def strategy_service(self, mock_rpc_client):
        from vnpy_china_monitor.web.services.strategy_service import StrategyService
        return StrategyService(mock_rpc_client)

    def test_get_all_strategies(self, strategy_service, mock_rpc_client):
        """测试获取所有策略（实现返回 rpc 原值 dict，策略列表在 'strategies' 键下）"""
        mock_rpc_client.get_all_strategies.return_value = {
            "strategies": [
                {
                    "name": "test_strategy",
                    "status": "running",
                    "vt_symbol": "000001.SZSE"
                }
            ]
        }

        result = strategy_service.get_all_strategies()
        strategies = result["strategies"]
        assert len(strategies) > 0
        assert strategies[0]["name"] == "test_strategy"

    def test_start_strategy(self, strategy_service, mock_rpc_client):
        """测试启动策略"""
        strategy_service.start_strategy("test_strategy")
        mock_rpc_client.start_strategy.assert_called_once_with("test_strategy")

    def test_stop_strategy(self, strategy_service, mock_rpc_client):
        """测试停止策略"""
        strategy_service.stop_strategy("test_strategy")
        mock_rpc_client.stop_strategy.assert_called_once_with("test_strategy")

    def test_set_strategy_param(self, strategy_service, mock_rpc_client):
        """测试设置策略参数"""
        strategy_service.set_strategy_param(
            "test_strategy", "param_name", "param_value"
        )
        mock_rpc_client.set_strategy_param.assert_called_once()


class TestAlertService:
    """告警服务测试"""

    @pytest.fixture
    def alert_service(self):
        from vnpy_china_monitor.alert import AlertEngine
        from vnpy_china_monitor.web.services.alert_service import AlertService
        # 用真实 AlertEngine（Mock main/event）而非 Mock alert_engine，
        # 使 send_alert 真实存储告警、get_active_alerts/get_stats 返回真实聚合结果
        alert_engine = AlertEngine(main_engine=Mock(), event_engine=Mock())
        return AlertService(alert_engine)

    def test_send_alert(self, alert_service, mock_event_engine):
        """测试发送告警"""
        alert_id = alert_service.send_alert(
            "测试告警",
            "这是一条测试告警",
            "info"
        )
        assert alert_id is not None

    def test_get_active_alerts(self, alert_service):
        """测试获取活跃告警"""
        # 先发送一些告警
        alert_service.send_alert("告警1", "消息1", "info")
        alert_service.send_alert("告警2", "消息2", "warning")

        alerts = alert_service.get_active_alerts()
        assert len(alerts) >= 2

    def test_acknowledge_alert(self, alert_service):
        """测试确认告警"""
        alert_id = alert_service.send_alert("测试告警", "消息", "info")
        result = alert_service.acknowledge_alert(alert_id, "已处理")
        assert result is True

    def test_get_stats(self, alert_service):
        """测试获取告警统计"""
        alert_service.send_alert("告警1", "消息1", "critical")
        alert_service.send_alert("告警2", "消息2", "warning")
        alert_service.send_alert("告警3", "消息3", "info")

        stats = alert_service.get_stats()
        assert "total_sent" in stats
        assert "by_severity" in stats
        assert stats["by_severity"]["critical"] >= 1


@pytest.mark.integration
class TestServiceIntegration:
    """服务集成测试"""

    def test_market_trade_integration(self):
        """测试行情与交易服务集成"""
        mock_rpc = Mock()
        from vnpy_china_monitor.web.services import (
            MarketService,
            TradeService
        )

        market_service = MarketService(mock_rpc)
        trade_service = TradeService(mock_rpc)

        # 模拟获取行情后交易（MarketService.get_tick 从缓存取，需先 update_tick）
        market_service.update_tick({
            "vt_symbol": "000001.SZSE",
            "last_price": 10.50
        })

        tick = market_service.get_tick("000001.SZSE")
        assert tick is not None

        # 基于行情发送委托（send_order 签名: vt_symbol, direction, volume, price）
        mock_rpc.send_order.return_value = "test_order_id"
        order_id = trade_service.send_order(
            "000001.SZSE", "多", 100, tick["last_price"]
        )
        assert order_id == "test_order_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
