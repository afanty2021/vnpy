# P1-2: RPC心跳检测简化方案

## 问题描述

**文件**: `vnpy_china_data/adapter/rpc_qmt_adapter.py:589-624`

当前RPC心跳检测代码逻辑过于复杂，存在类型混乱：

```python
HEARTBEAT_TOLERANCE: int = 30  # 秒
pull_tolerance: int = HEARTBEAT_TOLERANCE * 1000  # 毫秒

time_since_last_ping = (now - self._last_received_ping) * 1000
if time_since_last_ping > pull_tolerance:
    if not hasattr(self, '_last_warning_time'):
        self.on_disconnected()
        self._last_warning_time = now
    else:
        last_warning = self._last_warning_time
        if isinstance(last_warning, (int, float)):
            if (now - last_warning) > HEARTBEAT_TOLERANCE:
                self.on_disconnected()
                self._last_warning_time = now
        else:
            print(f"警告: _last_warning_time类型错误 ({type(last_warning)})...")
```

**问题**：
1. 时间单位混用（秒和毫秒）
2. 类型检查复杂，容易出现错误
3. 警告频率控制逻辑不清晰
4. 调试信息过多

## 修复方案

### 方案设计

统一使用**毫秒**作为时间单位，简化逻辑，使用状态机模式管理连接状态。

### 实现步骤

#### 步骤1: 重构RPC客户端

修改 `vnpy_china_data/adapter/rpc_qmt_adapter.py` 中的 `CustomRpcClient` 类：

```python
"""
RPC QMT数据适配器

通过RPC连接到Windows服务器上的QMT服务，实现跨平台数据访问。
适用于Mac/Linux客户端访问Windows上的QMT数据。
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, date, time
from threading import Thread, Event, Lock
from collections import defaultdict
from enum import Enum

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.event import EventEngine
from vnpy.rpc import RpcClient

from vnpy_china_config.logging_config import get_logger

from .base import BaseDataAdapter

logger = get_logger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class CustomRpcClient(RpcClient):
    """自定义RPC客户端

    继承自vnpy.rpc.RpcClient，添加可配置的callback功能。
    使用统一的时间单位（毫秒）和清晰的状态管理。

    配置参数：
        HEARTBEAT_TOLERANCE_MS: 心跳容忍时间（毫秒）
        POLL_INTERVAL_MS: 轮询间隔（毫秒）
        WARNING_COOLDOWN_MS: 警告冷却时间（毫秒）
    """

    # 心跳配置常量（统一使用毫秒）
    HEARTBEAT_TOLERANCE_MS = 30000  # 30秒无心跳视为断开
    POLL_INTERVAL_MS = 1000  # 正常轮询间隔1秒
    FAST_POLL_INTERVAL_MS = 100  # 快速轮询间隔100ms
    WARNING_COOLDOWN_MS = 5000  # 警告冷却时间5秒

    def __init__(self):
        """初始化"""
        super().__init__()
        self.callback = None

        # 连接状态管理
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = Lock()

        # 时间戳管理（统一使用毫秒）
        self._last_heartbeat_ms: int = 0
        self._last_warning_ms: int = 0

    def run(self) -> None:
        """运行RPC客户端循环

        改进：
        - 统一使用毫秒时间戳
        - 简化状态判断逻辑
        - 清晰的警告频率控制
        """
        from time import time as current_time
        import zmq

        while self._active:
            current_ms = int(current_time() * 1000)

            # 检查连接状态
            if not self._check_heartbeat(current_ms):
                # 心跳超时，触发断开连接处理
                self._handle_disconnection(current_ms)

            # 计算轮询超时时间
            poll_timeout = self._calculate_poll_timeout(current_ms)

            # 等待消息或超时
            if not self._socket_sub.poll(poll_timeout):
                continue

            # 接收数据
            try:
                topic, data = self._socket_sub.recv_pyobj(flags=zmq.NOBLOCK)

                # 更新心跳时间戳
                self._last_heartbeat_ms = current_ms

                # 重置连接状态
                if self._state != ConnectionState.CONNECTED:
                    self._set_state(ConnectionState.CONNECTED)
                    logger.info("RPC连接已建立")

                # 处理消息
                if topic == "heartbeat":
                    # 心跳消息，不需要处理
                    pass
                else:
                    # 业务消息，调用callback
                    if self.callback:
                        self.callback(topic, data)

            except zmq.ZMQError:
                # 接收错误，忽略并继续
                pass

        # 关闭连接
        self._cleanup()

    def _check_heartbeat(self, current_ms: int) -> bool:
        """检查心跳是否超时

        Args:
            current_ms: 当前时间戳（毫秒）

        Returns:
            bool: True表示心跳正常，False表示超时
        """
        # 初始化心跳时间戳
        if self._last_heartbeat_ms == 0:
            self._last_heartbeat_ms = current_ms
            return True

        # 计算距离上次心跳的时间
        time_since_heartbeat = current_ms - self._last_heartbeat_ms

        # 检查是否超时
        if time_since_heartbeat > self.HEARTBEAT_TOLERANCE_MS:
            return False

        return True

    def _handle_disconnection(self, current_ms: int) -> None:
        """处理断开连接

        Args:
            current_ms: 当前时间戳（毫秒）
        """
        # 检查警告冷却
        time_since_warning = current_ms - self._last_warning_ms

        if time_since_warning >= self.WARNING_COOLDOWN_MS:
            # 更新警告时间
            self._last_warning_ms = current_ms

            # 更新状态
            self._set_state(ConnectionState.DISCONNECTED)

            # 触发断开连接回调
            logger.warning(
                f"RPC心跳超时: {current_ms - self._last_heartbeat_ms}ms "
                f"(容忍: {self.HEARTBEAT_TOLERANCE_MS}ms)"
            )
            self.on_disconnected()

    def _calculate_poll_timeout(self, current_ms: int) -> int:
        """计算轮询超时时间

        Args:
            current_ms: 当前时间戳（毫秒）

        Returns:
            int: 轮询超时时间（毫秒）
        """
        if self._last_heartbeat_ms == 0:
            # 未收到过心跳，使用快速轮询
            return self.FAST_POLL_INTERVAL_MS

        time_since_heartbeat = current_ms - self._last_heartbeat_ms
        time_to_timeout = self.HEARTBEAT_TOLERANCE_MS - time_since_heartbeat

        if time_to_timeout <= 0:
            # 已经超时，使用快速轮询
            return self.FAST_POLL_INTERVAL_MS
        elif time_to_timeout < self.POLL_INTERVAL_MS:
            # 接近超时，使用更短的间隔
            return min(time_to_timeout, self.FAST_POLL_INTERVAL_MS)
        else:
            # 正常情况，使用标准轮询间隔
            return self.POLL_INTERVAL_MS

    def _set_state(self, state: ConnectionState) -> None:
        """设置连接状态

        Args:
            state: 新的连接状态
        """
        with self._state_lock:
            old_state = self._state
            self._state = state

            if old_state != state:
                logger.debug(f"RPC连接状态: {old_state.value} -> {state.value}")

    def _cleanup(self) -> None:
        """清理资源"""
        try:
            self._socket_req.close()
            self._socket_sub.close()
            logger.debug("RPC连接已关闭")
        except Exception as e:
            logger.error(f"关闭RPC连接时出错: {e}", exc_info=True)

    @property
    def state(self) -> ConnectionState:
        """获取当前连接状态"""
        with self._state_lock:
            return self._state

    @property
    def connection_info(self) -> Dict[str, Any]:
        """获取连接信息（用于调试）"""
        current_ms = int(time.time() * 1000)

        if self._last_heartbeat_ms == 0:
            time_since_heartbeat = 0
        else:
            time_since_heartbeat = current_ms - self._last_heartbeat_ms

        return {
            "state": self._state.value,
            "last_heartbeat_ms": self._last_heartbeat_ms,
            "time_since_heartbeat_ms": time_since_heartbeat,
            "is_timeout": time_since_heartbeat > self.HEARTBEAT_TOLERANCE_MS,
        }
```

#### 步骤2: 添加连接状态监控

在 `RpcQmtDataAdapter` 中添加状态监控：

```python
class RpcQmtDataAdapter(BaseDataAdapter):
    """RPC QMT数据适配器"""

    def __init__(
        self,
        req_address: str = "tcp://127.0.0.1:2014",
        sub_address: str = "tcp://127.0.0.1:4102",
        event_engine: Optional[EventEngine] = None,
    ):
        """初始化RPC QMT适配器"""
        super().__init__()
        self.req_address = req_address
        self.sub_address = sub_address
        self.event_engine = event_engine

        self._rpc_client: Optional["CustomRpcClient"] = None
        self._subscribed_symbols: set = set()
        self._symbol_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._tick_cache: Dict[str, TickData] = {}
        self._stop_event = Event()
        self._reconnect_thread: Optional[Thread] = None
        self._reconnect_interval = 30
        self._tick_count = 0
        self._last_tick_time: Optional[datetime] = None
        self._lock = Lock()

    def get_connection_status(self) -> Dict[str, Any]:
        """获取RPC连接状态

        Returns:
            连接状态信息字典，包含：
            - state: 连接状态
            - connected: 是否已连接
            - time_since_heartbeat_ms: 距离上次心跳的时间（毫秒）
            - is_timeout: 是否超时
        """
        if not self._rpc_client:
            return {
                "state": "not_initialized",
                "connected": False,
            }

        return self._rpc_client.connection_info

    def is_healthy(self) -> bool:
        """检查连接是否健康

        Returns:
            bool: True表示连接健康，False表示异常
        """
        status = self.get_connection_status()
        return status.get("connected", False) and not status.get("is_timeout", True)
```

### 测试方法

创建 `tests/test_rpc_heartbeat.py`：

```python
"""测试RPC心跳检测"""

import time
from unittest.mock import Mock, patch, MagicMock

from vnpy_china_data.adapter.rpc_qmt_adapter import CustomRpcClient, ConnectionState


def test_heartbeat_timeout_detection():
    """测试心跳超时检测"""
    client = CustomRpcClient()

    # 模拟最后心跳时间为30秒前
    current_ms = int(time.time() * 1000)
    client._last_heartbeat_ms = current_ms - 30000 - 1  # 刚超过30秒

    # 检查心跳应该返回False
    assert not client._check_heartbeat(current_ms)


def test_heartbeat_normal():
    """测试正常心跳"""
    client = CustomRpcClient()

    current_ms = int(time.time() * 1000)
    client._last_heartbeat_ms = current_ms - 10000  # 10秒前

    # 检查心跳应该返回True
    assert client._check_heartbeat(current_ms)


def test_warning_cooldown():
    """测试警告冷却机制"""
    client = CustomRpcClient()

    current_ms = int(time.time() * 1000)
    client._last_heartbeat_ms = current_ms - 40000  # 40秒前
    client._last_warning_ms = current_ms - 3000  # 3秒前警告过

    # 模拟on_disconnected回调
    disconnect_called = []
    client.on_disconnected = lambda: disconnect_called.append(True)

    # 第一次调用应该触发警告
    client._handle_disconnection(current_ms)
    assert len(disconnect_called) == 1

    # 立即再次调用，不应该触发（冷却中）
    client._handle_disconnection(current_ms)
    assert len(disconnect_called) == 1  # 没有增加

    # 5秒后再次调用，应该触发
    client._handle_disconnection(current_ms + 5000)
    assert len(disconnect_called) == 2


def test_poll_timeout_calculation():
    """测试轮询超时计算"""
    client = CustomRpcClient()

    current_ms = int(time.time() * 1000)

    # 未收到心跳，应该快速轮询
    client._last_heartbeat_ms = 0
    assert client._calculate_poll_timeout(current_ms) == client.FAST_POLL_INTERVAL_MS

    # 刚收到心跳，应该正常轮询
    client._last_heartbeat_ms = current_ms
    assert client._calculate_poll_timeout(current_ms) == client.POLL_INTERVAL_MS

    # 接近超时，应该快速轮询
    client._last_heartbeat_ms = current_ms - 29000
    assert client._calculate_poll_timeout(current_ms) == client.FAST_POLL_INTERVAL_MS


def test_state_transitions():
    """测试状态转换"""
    client = CustomRpcClient()

    # 初始状态
    assert client.state == ConnectionState.DISCONNECTED

    # 设置为已连接
    client._set_state(ConnectionState.CONNECTED)
    assert client.state == ConnectionState.CONNECTED


def test_connection_info():
    """测试连接信息获取"""
    client = CustomRpcClient()

    current_ms = int(time.time() * 1000)
    client._last_heartbeat_ms = current_ms - 5000
    client._set_state(ConnectionState.CONNECTED)

    info = client.connection_info
    assert info["state"] == "connected"
    assert info["time_since_heartbeat_ms"] == 5000
    assert not info["is_timeout"]


if __name__ == "__main__":
    test_heartbeat_timeout_detection()
    test_heartbeat_normal()
    test_warning_cooldown()
    test_poll_timeout_calculation()
    test_state_transitions()
    test_connection_info()
    print("所有测试通过")
```

### 对比分析

#### 修复前

```python
# 复杂的类型检查
HEARTBEAT_TOLERANCE: int = 30
pull_tolerance: int = HEARTBEAT_TOLERANCE * 1000
time_since_last_ping = (now - self._last_received_ping) * 1000

if time_since_last_ping > pull_tolerance:
    if not hasattr(self, '_last_warning_time'):
        self.on_disconnected()
        self._last_warning_time = now
    else:
        last_warning = self._last_warning_time
        if isinstance(last_warning, (int, float)):
            if (now - last_warning) > HEARTBEAT_TOLERANCE:
                self.on_disconnected()
                self._last_warning_time = now
        else:
            print(f"警告: _last_warning_time类型错误...")
```

#### 修复后

```python
# 统一使用毫秒，逻辑清晰
HEARTBEAT_TOLERANCE_MS = 30000

def _check_heartbeat(self, current_ms: int) -> bool:
    if self._last_heartbeat_ms == 0:
        self._last_heartbeat_ms = current_ms
        return True

    time_since_heartbeat = current_ms - self._last_heartbeat_ms
    return time_since_heartbeat <= self.HEARTBEAT_TOLERANCE_MS

def _handle_disconnection(self, current_ms: int) -> None:
    time_since_warning = current_ms - self._last_warning_ms
    if time_since_warning >= self.WARNING_COOLDOWN_MS:
        self._last_warning_ms = current_ms
        self._set_state(ConnectionState.DISCONNECTED)
        logger.warning(f"RPC心跳超时: ...")
        self.on_disconnected()
```

### 验收标准

- [ ] 心跳超时检测准确
- [ ] 警告频率控制正常（冷却机制）
- [ ] 状态转换清晰可追踪
- [ ] 轮询间隔动态调整合理
- [ ] 代码行数减少30%以上
- [ ] 无类型检查相关的调试输出

### 性能对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 代码行数 | ~80行 | ~60行 |
| 时间单位 | 混用（秒/毫秒） | 统一（毫秒） |
| 状态管理 | 隐式 | 显式（枚举） |
| 警告控制 | 复杂if嵌套 | 冷却时间常量 |
| 可测试性 | 低 | 高（方法独立） |

---

**工作量估算**: 0.5人日
**优先级**: P1（应该修复）
**负责人**: 待分配
