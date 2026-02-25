"""
FastAPI Web服务器

VeighNa Web监控系统的主服务器
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from vnpy_china_monitor.web.config import (
    WebMonitorConfig,
    get_config,
    set_config,
)
from vnpy_china_monitor.web.rpc.client import RpcClientWrapper
from vnpy_china_monitor.web.websocket.manager import ConnectionManager
from vnpy_china_monitor.web.websocket.events import EventType, WebSocketEvent
from vnpy_china_monitor.web.services.market_service import MarketService
from vnpy_china_monitor.web.services.trade_service import TradeService
from vnpy_china_monitor.web.services.strategy_service import StrategyService
from vnpy_china_monitor.web.services.alert_service import AlertService
from vnpy_china_monitor.web.api import (
    auth_router,
    market_router,
    trade_router,
    strategy_router,
    alert_router,
)

# 尝试导入 ML API（如果可用）
try:
    from vnpy_china_ml.web.api import ml_router
    ML_API_AVAILABLE = True
except ImportError:
    ML_API_AVAILABLE = False
    ml_router = None

logger = logging.getLogger(__name__)


# 全局实例
_rpc_client: Optional[RpcClientWrapper] = None
_connection_manager: Optional[ConnectionManager] = None
_market_service: Optional[MarketService] = None
_trade_service: Optional[TradeService] = None
_strategy_service: Optional[StrategyService] = None
_alert_service: Optional[AlertService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    Args:
        app: FastAPI应用实例

    Yields:
        None
    """
    global _rpc_client, _connection_manager
    global _market_service, _trade_service, _strategy_service, _alert_service

    config = get_config()

    # 启动时初始化
    logger.info("Starting VeighNa Web Monitor...")

    # 初始化RPC客户端
    _rpc_client = RpcClientWrapper(
        rep_address=config.rpc.rep_address,
        pub_address=config.rpc.pub_address,
        auto_reconnect=config.rpc.auto_reconnect,
        reconnect_interval=config.rpc.reconnect_interval,
        request_timeout=config.rpc.request_timeout,
    )

    # 连接RPC（使用同步连接，避免 signal 模块的线程问题）
    if _rpc_client.connect():
        logger.info("RPC client connected successfully")
    else:
        logger.warning("RPC client connection failed, will retry in background...")

    # 初始化WebSocket管理器
    _connection_manager = ConnectionManager(
        heartbeat_interval=config.websocket.heartbeat_interval,
        max_connections=config.websocket.max_connections,
    )

    # 启动心跳
    await _connection_manager.start_heartbeat()

    # 初始化服务
    _market_service = MarketService(_rpc_client)
    _trade_service = TradeService(_rpc_client)
    _strategy_service = StrategyService(_rpc_client)
    _alert_service = AlertService()

    # 注册RPC事件订阅
    _register_rpc_events()

    # 将服务添加到应用状态
    app.state.rpc_client = _rpc_client
    app.state.connection_manager = _connection_manager
    app.state.market_service = _market_service
    app.state.trade_service = _trade_service
    app.state.strategy_service = _strategy_service
    app.state.alert_service = _alert_service

    logger.info("VeighNa Web Monitor started successfully")

    yield

    # 关闭时清理
    logger.info("Shutting down VeighNa Web Monitor...")

    # 停止心跳
    if _connection_manager:
        await _connection_manager.stop_heartbeat()

    # 断开RPC
    if _rpc_client:
        _rpc_client.disconnect()

    logger.info("VeighNa Web Monitor shut down")


def _register_rpc_events():
    """注册RPC事件订阅"""
    if not _rpc_client:
        return

    # 订阅行情事件
    _rpc_client.subscribe("tick", _on_tick_event)
    _rpc_client.subscribe("bar", _on_bar_event)

    # 订阅交易事件
    _rpc_client.subscribe("order", _on_order_event)
    _rpc_client.subscribe("trade", _on_trade_event)
    _rpc_client.subscribe("position", _on_position_event)
    _rpc_client.subscribe("account", _on_account_event)

    # 订阅策略事件
    _rpc_client.subscribe("strategy", _on_strategy_event)

    logger.info("RPC event subscriptions registered")


def _on_tick_event(data: dict):
    """处理行情事件"""
    if _market_service:
        _market_service.update_tick(data)

    # 通过WebSocket广播
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "tick",
                WebSocketEvent(type=EventType.MARKET_TICK, data=data),
            )
        )


def _on_bar_event(data: dict):
    """处理K线事件"""
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "bar",
                WebSocketEvent(type=EventType.MARKET_BAR, data=data),
            )
        )


def _on_order_event(data: dict):
    """处理委托事件"""
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "order",
                WebSocketEvent(type=EventType.TRADE_ORDER, data=data),
            )
        )


def _on_trade_event(data: dict):
    """处理成交事件"""
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "trade",
                WebSocketEvent(type=EventType.TRADE_TRADE, data=data),
            )
        )


def _on_position_event(data: dict):
    """处理持仓事件"""
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "position",
                WebSocketEvent(type=EventType.TRADE_POSITION, data=data),
            )
        )


def _on_account_event(data: dict):
    """处理账户事件"""
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "account",
                WebSocketEvent(type=EventType.TRADE_ACCOUNT, data=data),
            )
        )


def _on_strategy_event(data: dict):
    """处理策略事件"""
    if _connection_manager:
        import asyncio
        asyncio.create_task(
            _connection_manager.broadcast(
                "strategy",
                WebSocketEvent(type=EventType.STRATEGY_STATUS, data=data),
            )
        )


def create_web_app(config: Optional[WebMonitorConfig] = None) -> FastAPI:
    """创建Web应用

    Args:
        config: 配置对象

    Returns:
        FastAPI应用实例
    """
    # 设置配置
    if config:
        set_config(config)

    config = get_config()
    config.validate()

    # 创建应用
    app = FastAPI(
        title="VeighNa Web Monitor",
        description="VeighNa量化交易系统Web监控与远程控制",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS中间件
    if config.cors.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors.allow_origins,
            allow_credentials=config.cors.allow_credentials,
            allow_methods=config.cors.allow_methods,
            allow_headers=config.cors.allow_headers,
        )

    # 注册路由
    app.include_router(auth_router)
    app.include_router(market_router)
    app.include_router(trade_router)
    app.include_router(strategy_router)
    app.include_router(alert_router)

    # 注册 ML API（如果可用）
    if ML_API_AVAILABLE and ml_router:
        app.include_router(ml_router)
        logger.info("ML API 路由已注册")

    # WebSocket端点
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket连接端点

        Args:
            websocket: WebSocket连接
            client_id: 客户端ID
        """
        manager = app.state.connection_manager
        if not manager:
            await websocket.close(code=1011, reason="服务未初始化")
            return

        # 接受连接
        if not await manager.connect(websocket, client_id):
            return

        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()

                # 解析JSON
                import json
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await manager.send_personal(websocket, WebSocketEvent(
                        type=EventType.ERROR,
                        data={"message": "Invalid JSON format"},
                    ))
                    continue

                # 处理消息
                await manager.handle_message(websocket, message)

        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)

    # 根路径
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """根路径，返回欢迎页面"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>VeighNa Web Monitor</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                }
                h1 { color: #333; }
                p { color: #666; line-height: 1.6; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>VeighNa Web Monitor</h1>
            <p>VeighNa量化交易系统 Web监控与远程控制系统</p>
            <p><a href="/docs">查看API文档</a></p>
        </body>
        </html>
        """

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        rpc_connected = _rpc_client.connected if _rpc_client else False

        return {
            "status": "healthy",
            "rpc_connected": rpc_connected,
        }

    return app
