"""
Web API测试模块

测试VeighNa Web监控系统的REST API接口
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json


@pytest.fixture
def mock_rpc_client():
    """模拟RPC客户端"""
    with patch('vnpy_china_monitor.web.rpc.client.RpcClient') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def test_app(mock_rpc_client):
    """测试应用实例（启动 lifespan 初始化 app.state，并注入测试用户）"""
    from vnpy_china_monitor.web.server import app

    # 用 with 触发 lifespan，使 server.lifespan 初始化 app.state.auth_manager 等服务
    with TestClient(app) as client:
        # SimpleUserStore 已移除硬编码 admin/admin123，测试需显式注入测试用户
        auth_manager = getattr(app.state, "auth_manager", None)
        if auth_manager is not None and hasattr(auth_manager, "user_store"):
            auth_manager.user_store.add_user("admin", "admin123")
        yield client


@pytest.fixture
def auth_token(test_app):
    """获取认证令牌（成功返回 access_token，失败返回 None）"""
    response = test_app.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        # login 返回 ApiResponse，access_token 在 data 字段内
        data = response.json().get("data") or {}
        return data.get("access_token")
    return None


class TestAuthAPI:
    """认证API测试"""

    def test_login_success(self, test_app):
        """测试成功登录"""
        response = test_app.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        # login 返回 ApiResponse，access_token 在 data；不再签发 refresh_token
        assert "access_token" in body["data"]

    def test_login_invalid_credentials(self, test_app):
        """测试无效凭据登录"""
        response = test_app.post(
            "/api/auth/login",
            json={"username": "wrong", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_get_current_user(self, test_app, auth_token):
        """测试获取当前用户信息"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        # /api/auth/me 返回 ApiResponse，username 在 data 内
        data = response.json().get("data") or {}
        assert data.get("username") == "admin"

    def test_logout(self, test_app, auth_token):
        """测试登出"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200


class TestMarketAPI:
    """行情API测试"""

    def test_get_tick(self, test_app, auth_token, mock_rpc_client):
        """测试获取单个行情"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        # 模拟RPC响应
        mock_rpc_client.get_tick.return_value = {
            "vt_symbol": "000001.SZSE",
            "last_price": 10.50,
            "volume": 1000000
        }

        response = test_app.get(
            "/api/market/tick/000001.SZSE",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_all_ticks(self, test_app, auth_token):
        """测试获取所有行情"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/market/ticks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ticks" in data

    def test_subscribe_symbol(self, test_app, auth_token):
        """测试订阅合约"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.post(
            "/api/market/subscribe",
            json={"vt_symbol": "000001.SZSE"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

    def test_unsubscribe_symbol(self, test_app, auth_token):
        """测试取消订阅"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.delete(
            "/api/market/subscribe/000001.SZSE",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200


class TestTradeAPI:
    """交易API测试"""

    def test_get_account(self, test_app, auth_token):
        """测试获取账户信息"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/trade/account",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "account" in data

    def test_get_positions(self, test_app, auth_token):
        """测试获取持仓列表"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/trade/positions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data

    def test_send_order(self, test_app, auth_token):
        """测试发送委托"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        order_request = {
            "vt_symbol": "000001.SZSE",
            "direction": "多",
            "type": "限价",
            "volume": 100,
            "price": 10.50
        }

        response = test_app.post(
            "/api/trade/order/send",
            json=order_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

    def test_cancel_order(self, test_app, auth_token):
        """测试撤销委托"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.post(
            "/api/trade/order/cancel",
            json={"vt_orderid": "test_order_id"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200


class TestStrategyAPI:
    """策略API测试"""

    def test_get_strategies(self, test_app, auth_token):
        """测试获取策略列表"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/strategy",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data

    def test_start_strategy(self, test_app, auth_token):
        """测试启动策略"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.post(
            "/api/strategy/test_strategy/start",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

    def test_stop_strategy(self, test_app, auth_token):
        """测试停止策略"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.post(
            "/api/strategy/test_strategy/stop",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200


class TestAlertAPI:
    """告警API测试

    web 进程未注入 AlertEngine（仅有 RpcClient，无 main_engine/event_engine），
    AlertService 不再被空实例化注入 app.state，故所有 /api/alerts 端点显式返回 503。
    待 AlertEngine 真正 wiring 后，再改回 200 断言。
    """

    def test_get_alerts_returns_503_when_not_initialized(self, test_app, auth_token):
        """未注入告警服务时 /api/alerts 返回 503（而非伪装的空 200）"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/alerts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 503

    def test_get_alert_stats_returns_503_when_not_initialized(self, test_app, auth_token):
        """未注入告警服务时 /api/alerts/stats 返回 503"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.get(
            "/api/alerts/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 503

    def test_acknowledge_alert_returns_503_when_not_initialized(self, test_app, auth_token):
        """未注入告警服务时 acknowledge 返回 503"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        response = test_app.post(
            "/api/alerts/test_alert_id/acknowledge",
            json={"comment": "已处理"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 503


@pytest.mark.asyncio
class TestWebSocket:
    """WebSocket测试"""

    async def test_websocket_connection(self, test_app):
        """测试WebSocket连接"""
        # 这里需要使用异步WebSocket客户端进行测试
        # 示例代码，实际实现可能需要调整
        pass

    async def test_websocket_subscription(self, test_app):
        """测试WebSocket订阅"""
        pass


@pytest.mark.performance
class TestPerformance:
    """性能测试"""

    def test_concurrent_requests(self, test_app, auth_token):
        """测试并发请求"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        import asyncio

        async def make_request(client, endpoint, token):
            return client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )

        # 简化的并发测试示例
        # 实际实现需要更复杂的异步处理
        pass

    def test_response_time(self, test_app, auth_token):
        """测试响应时间"""
        if not auth_token:
            pytest.skip("需要有效的认证令牌")

        import time

        start = time.time()
        response = test_app.get(
            "/api/trade/account",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        end = time.time()

        assert response.status_code == 200
        assert (end - start) < 1.0  # 响应时间应小于1秒


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
