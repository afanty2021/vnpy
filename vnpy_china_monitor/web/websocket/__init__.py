"""
WebSocket连接管理

提供实时数据推送功能
"""

from vnpy_china_monitor.web.websocket.manager import ConnectionManager
from vnpy_china_monitor.web.websocket.events import WebSocketEvent, EventType

__all__ = [
    "ConnectionManager",
    "WebSocketEvent",
    "EventType",
]
