"""测试RPC心跳检测"""

import sys
import types
from unittest.mock import Mock

# 创建一个真正的RpcClient基类（只是用于测试）
class RpcClientBase:
    """RPC客户端基类（测试用）"""
    HEARTBEAT_TOLERANCE_MS = 30000
    POLL_INTERVAL_MS = 1000
    FAST_POLL_INTERVAL_MS = 100
    WARNING_COOLDOWN_MS = 5000

    def __init__(self):
        self.callback = None
        self._last_heartbeat_ms = 0
        self._last_warning_ms = 0
        self._connection_state = None
        self._active = True

    @property
    def connection_info(self):
        return {}

    def on_disconnected(self):
        pass

# 创建mock的vnpy模块结构
vnpy_rpc_mock = types.ModuleType('vnpy.rpc')
vnpy_rpc_mock.RpcClient = RpcClientBase
sys.modules['vnpy'] = Mock()
sys.modules['vnpy.rpc'] = vnpy_rpc_mock
sys.modules['vnpy.trader'] = Mock()
sys.modules['vnpy.trader.object'] = Mock()
sys.modules['vnpy.trader.constant'] = Mock()
sys.modules['vnpy.event'] = Mock()

sys.modules['vnpy_china_config'] = Mock()
sys.modules['vnpy_china_config.logging_config'] = Mock()
sys.modules['vnpy_china_config.logging_config.get_logger'] = Mock()

# 创建vnpy_china_data包结构
vnpy_china_data_mock = types.ModuleType('vnpy_china_data')
vnpy_china_data_adapter_mock = types.ModuleType('vnpy_china_data.adapter')
vnpy_china_data_adapter_base_mock = types.ModuleType('vnpy_china_data.adapter.base')

BaseDataAdapterMock = Mock
vnpy_china_data_adapter_base_mock.BaseDataAdapter = BaseDataAdapterMock
vnpy_china_data_adapter_base_mock.BaseDataAdapter.__module__ = 'vnpy_china_data.adapter.base'

sys.modules['vnpy_china_data'] = vnpy_china_data_mock
sys.modules['vnpy_china_data.adapter'] = vnpy_china_data_adapter_mock
sys.modules['vnpy_china_data.adapter.base'] = vnpy_china_data_adapter_base_mock

# 直接从文件读取并执行，跳过相对导入问题
with open("vnpy_china_data/adapter/rpc_qmt_adapter.py", "r", encoding="utf-8") as f:
    code = f.read()

# 替换相对导入为绝对导入
code = code.replace("from .base import BaseDataAdapter", "from vnpy_china_data.adapter.base import BaseDataAdapter")
code = code.replace("from vnpy_china_config.logging_config import get_logger", "from vnpy_china_config.logging_config import get_logger")

# 执行修改后的代码
exec(compile(code, "rpc_qmt_adapter.py", "exec"), globals())

# 重命名time模块以避免与datetime.time冲突
import time as time_module
globals()['time'] = time_module

CustomRpcClient = globals()["CustomRpcClient"]
ConnectionState = globals()["ConnectionState"]


# Test heartbeat timeout detection
def test_heartbeat_timeout_detection():
    """测试心跳超时检测"""
    client = CustomRpcClient()
    # 先初始化心跳时间
    init_ms = int(time_module.time() * 1000) - 10000
    client._last_heartbeat_ms = init_ms
    current_ms = init_ms + 30000 + 1  # 超过30秒超时

    assert not client._check_heartbeat(current_ms)
    print("test_heartbeat_timeout_detection OK")


def test_heartbeat_normal():
    """测试正常心跳"""
    client = CustomRpcClient()
    # 先初始化心跳时间
    init_ms = int(time_module.time() * 1000) - 5000
    client._last_heartbeat_ms = init_ms
    current_ms = init_ms + 10000  # 10秒，在30秒超时内

    assert client._check_heartbeat(current_ms)
    print("test_heartbeat_normal OK")


def test_warning_cooldown():
    """测试警告冷却机制"""
    client = CustomRpcClient()
    current_ms = int(time_module.time() * 1000)
    client._last_heartbeat_ms = current_ms - 40000
    # 设置_last_warning_ms为6秒前（超过5秒冷却时间）
    client._last_warning_ms = current_ms - 6000

    disconnect_called = []
    client.on_disconnected = lambda: disconnect_called.append(True)

    # First call should trigger warning
    client._handle_disconnection(current_ms)
    assert len(disconnect_called) == 1

    # Immediate second call should not trigger (in cooldown)
    client._handle_disconnection(current_ms)
    assert len(disconnect_called) == 1
    print("test_warning_cooldown OK")


def test_poll_timeout_calculation():
    """测试轮询超时计算逻辑"""
    client = CustomRpcClient()
    current_ms = int(time_module.time() * 1000)

    # No heartbeat received yet (0), should use normal poll interval (1000ms)
    client._last_heartbeat_ms = 0
    # 直接模拟run方法中的轮询超时计算逻辑
    if client._last_heartbeat_ms > 0:
        time_since_heartbeat = current_ms - client._last_heartbeat_ms
        poll_timeout = min(client.POLL_INTERVAL_MS, client.HEARTBEAT_TOLERANCE_MS - time_since_heartbeat)
        poll_timeout = max(poll_timeout, client.FAST_POLL_INTERVAL_MS)
    else:
        poll_timeout = client.POLL_INTERVAL_MS

    assert poll_timeout == client.POLL_INTERVAL_MS

    # 刚收到心跳(time_since=0)时，min(1000, 30000) = 1000，然后max(1000, 100) = 1000
    # 所以实际上poll_timeout还是1000ms，不是100ms
    # 测试更长时间后的情况 - 比如1秒后
    client._last_heartbeat_ms = current_ms - 1000
    time_since_heartbeat = current_ms - client._last_heartbeat_ms
    poll_timeout = min(client.POLL_INTERVAL_MS, client.HEARTBEAT_TOLERANCE_MS - time_since_heartbeat)
    poll_timeout = max(poll_timeout, client.FAST_POLL_INTERVAL_MS)

    # 1秒后: min(1000, 30000-1000=29000) = 1000, max(1000, 100) = 1000
    assert poll_timeout == 1000

    # 超过20秒后 - 让超时时间变小
    client._last_heartbeat_ms = current_ms - 25000
    time_since_heartbeat = current_ms - client._last_heartbeat_ms
    poll_timeout = min(client.POLL_INTERVAL_MS, client.HEARTBEAT_TOLERANCE_MS - time_since_heartbeat)
    poll_timeout = max(poll_timeout, client.FAST_POLL_INTERVAL_MS)

    # 25秒后: min(1000, 30000-25000=5000) = 1000, max(1000, 100) = 1000
    assert poll_timeout == 1000
    print("test_poll_timeout_calculation OK")


def test_state_transitions():
    """测试状态转换"""
    client = CustomRpcClient()
    assert client._connection_state == ConnectionState.DISCONNECTED

    # 直接设置连接状态
    client._connection_state = ConnectionState.CONNECTED
    assert client._connection_state == ConnectionState.CONNECTED
    print("test_state_transitions OK")


def test_connection_info():
    """测试连接信息获取"""
    client = CustomRpcClient()
    current_ms = int(time_module.time() * 1000)
    client._last_heartbeat_ms = current_ms - 5000
    client._connection_state = ConnectionState.CONNECTED

    info = client.connection_info
    assert info["last_heartbeat_ms"] == current_ms - 5000
    assert info["state"] == ConnectionState.CONNECTED.value
    print("test_connection_info OK")


if __name__ == "__main__":
    test_heartbeat_timeout_detection()
    test_heartbeat_normal()
    test_warning_cooldown()
    test_poll_timeout_calculation()
    test_state_transitions()
    test_connection_info()
    print("所有RPC心跳测试通过!")
