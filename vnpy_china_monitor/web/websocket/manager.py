"""
WebSocket连接管理器

管理WebSocket连接的生命周期、订阅和消息广播
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional, Set

from vnpy_china_monitor.web.websocket.events import (
    EventType,
    WebSocketEvent,
)

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """连接信息"""

    def __init__(self, client_id: str, connected_at: datetime):
        self.client_id = client_id
        self.connected_at = connected_at
        self.subscriptions: Set[str] = set()
        self.last_ping: Optional[datetime] = None
        self.last_pong: Optional[datetime] = None


class ConnectionManager:
    """WebSocket连接管理器

    负责：
    - 连接生命周期管理
    - 主题订阅管理
    - 消息广播
    - 心跳检测
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        max_connections: int = 100,
    ):
        """初始化连接管理器

        Args:
            heartbeat_interval: 心跳间隔（秒）
            max_connections: 最大连接数
        """
        self.heartbeat_interval = heartbeat_interval
        self.max_connections = max_connections

        # 活跃连接
        self._active_connections: Set[Any] = set()

        # 连接信息
        self._connection_info: Dict[Any, ConnectionInfo] = {}

        # 主题订阅
        self._topic_subscriptions: Dict[str, Set[Any]] = defaultdict(set)

        # 锁
        self._lock = asyncio.Lock()

        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None

        logger.info(
            f"ConnectionManager initialized: heartbeat_interval={heartbeat_interval}, "
            f"max_connections={max_connections}"
        )

    async def connect(self, websocket: Any, client_id: str) -> bool:
        """接受新连接

        Args:
            websocket: WebSocket连接对象
            client_id: 客户端ID

        Returns:
            是否成功连接
        """
        async with self._lock:
            # 检查连接数限制
            if len(self._active_connections) >= self.max_connections:
                logger.warning(f"Max connections reached: {self.max_connections}")
                await websocket.close(code=1001, reason="Max connections reached")
                return False

            try:
                await websocket.accept()

                self._active_connections.add(websocket)

                self._connection_info[websocket] = ConnectionInfo(
                    client_id=client_id,
                    connected_at=datetime.now(),
                )

                logger.info(f"WebSocket connected: client_id={client_id}, total={len(self._active_connections)}")

                # 发送连接成功消息
                await self._send_event(websocket, WebSocketEvent(
                    type=EventType.SUBSCRIBE,
                    data={"message": "Connected successfully", "client_id": client_id},
                ))

                return True

            except Exception as e:
                logger.error(f"Error accepting WebSocket connection: {e}")
                return False

    def disconnect(self, websocket: Any) -> None:
        """断开连接

        Args:
            websocket: WebSocket连接对象
        """
        # 从活跃连接中移除
        if websocket in self._active_connections:
            self._active_connections.discard(websocket)

        # 获取连接信息
        info = self._connection_info.pop(websocket, None)
        if info:
            logger.info(
                f"WebSocket disconnected: client_id={info.client_id}, "
                f"duration={datetime.now() - info.connected_at}"
            )

        # 清理订阅
        if info:
            for topic in info.subscriptions:
                if topic in self._topic_subscriptions:
                    self._topic_subscriptions[topic].discard(websocket)

    async def subscribe(self, websocket: Any, topic: str) -> bool:
        """订阅主题

        Args:
            websocket: WebSocket连接对象
            topic: 主题名称

        Returns:
            是否订阅成功
        """
        info = self._connection_info.get(websocket)
        if not info:
            logger.warning(f"Cannot subscribe: WebSocket not found for topic={topic}")
            return False

        # 添加订阅
        info.subscriptions.add(topic)
        self._topic_subscriptions[topic].add(websocket)

        logger.info(f"Client {info.client_id} subscribed to topic: {topic}")

        # 发送确认
        await self._send_event(websocket, WebSocketEvent(
            type=EventType.SUBSCRIBE,
            data={"topic": topic, "action": "subscribed"},
        ))

        return True

    async def unsubscribe(self, websocket: Any, topic: str) -> bool:
        """取消订阅

        Args:
            websocket: WebSocket连接对象
            topic: 主题名称

        Returns:
            是否取消成功
        """
        info = self._connection_info.get(websocket)
        if not info:
            return False

        # 移除订阅
        info.subscriptions.discard(topic)
        if topic in self._topic_subscriptions:
            self._topic_subscriptions[topic].discard(websocket)

        logger.info(f"Client {info.client_id} unsubscribed from topic: {topic}")

        # 发送确认
        await self._send_event(websocket, WebSocketEvent(
            type=EventType.UNSUBSCRIBE,
            data={"topic": topic, "action": "unsubscribed"},
        ))

        return True

    async def broadcast(
        self,
        topic: str,
        event: WebSocketEvent,
    ) -> int:
        """广播消息到主题订阅者

        Args:
            topic: 主题名称
            event: WebSocket事件

        Returns:
            发送成功的连接数
        """
        if topic not in self._topic_subscriptions:
            return 0

        event.topic = topic

        # 获取订阅者
        subscribers = self._topic_subscriptions[topic].copy()

        success_count = 0

        # 并发发送
        tasks = []
        for websocket in subscribers:
            tasks.append(self._send_event_safe(websocket, event))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)

        return success_count

    async def send_personal(self, websocket: Any, event: WebSocketEvent) -> bool:
        """发送个人消息

        Args:
            websocket: WebSocket连接对象
            event: WebSocket事件

        Returns:
            是否发送成功
        """
        return await self._send_event_safe(websocket, event)

    async def _send_event(self, websocket: Any, event: WebSocketEvent) -> bool:
        """发送事件

        Args:
            websocket: WebSocket连接对象
            event: WebSocket事件

        Returns:
            是否发送成功
        """
        try:
            await websocket.send_json(event.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.disconnect(websocket)
            return False

    async def _send_event_safe(
        self,
        websocket: Any,
        event: WebSocketEvent,
    ) -> bool:
        """安全发送事件（捕获异常）

        Args:
            websocket: WebSocket连接对象
            event: WebSocket事件

        Returns:
            是否发送成功
        """
        if websocket not in self._active_connections:
            return False

        return await self._send_event(websocket, event)

    async def handle_message(
        self,
        websocket: Any,
        message: Dict[str, Any],
    ) -> None:
        """处理客户端消息

        Args:
            websocket: WebSocket连接对象
            message: 消息内容
        """
        try:
            msg_type = message.get("type")
            data = message.get("data", {})

            if msg_type == EventType.SUBSCRIBE.value:
                # 订阅主题
                topic = data.get("topic")
                if topic:
                    await self.subscribe(websocket, topic)

            elif msg_type == EventType.UNSUBSCRIBE.value:
                # 取消订阅
                topic = data.get("topic")
                if topic:
                    await self.unsubscribe(websocket, topic)

            elif msg_type == EventType.PING.value:
                # 心跳响应
                info = self._connection_info.get(websocket)
                if info:
                    info.last_ping = datetime.now()

                await self._send_event(websocket, WebSocketEvent(
                    type=EventType.PONG,
                    data={"timestamp": datetime.now().isoformat()},
                ))

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    async def start_heartbeat(self) -> None:
        """启动心跳检测"""
        if self._heartbeat_task is not None:
            logger.warning("Heartbeat task already running")
            return

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Heartbeat task started")

    async def stop_heartbeat(self) -> None:
        """停止心跳检测"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat task stopped")

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                async with self._lock:
                    now = datetime.now()
                    to_remove = []

                    # 检查所有连接
                    for websocket, info in list(self._connection_info.items()):
                        # 检查最后心跳时间
                        if info.last_pong:
                            idle_time = (now - info.last_pong).total_seconds()
                            # 如果超过3倍心跳间隔没有响应，断开连接
                            if idle_time > self.heartbeat_interval * 3:
                                logger.warning(
                                    f"Connection timeout: client_id={info.client_id}, "
                                    f"idle_time={idle_time}s"
                                )
                                to_remove.append(websocket)
                                continue

                    # 清理超时连接
                    for websocket in to_remove:
                        try:
                            await websocket.close(code=1000, reason="Heartbeat timeout")
                        except Exception:
                            pass
                        self.disconnect(websocket)

                    # 发送心跳
                    if self._active_connections:
                        ping_event = WebSocketEvent(
                            type=EventType.PING,
                            data={"timestamp": now.isoformat()},
                        )

                        for websocket in list(self._active_connections):
                            await self._send_event_safe(websocket, ping_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "active_connections": len(self._active_connections),
            "max_connections": self.max_connections,
            "topics": {
                topic: len(subs)
                for topic, subs in self._topic_subscriptions.items()
            },
        }
