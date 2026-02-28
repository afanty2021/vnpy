# vnpy_china_data/adapter - 数据适配器模块

> 更新时间：2026-02-28
> 版本：1.1.0

## 模块概述

vnpy_china_data/adapter 模块提供各种数据源的适配器实现，统一不同数据源（QMT、Tushare等）的访问接口。

## 核心功能

### 适配器基类 (BaseDataAdapter)

所有适配器继承自 `BaseDataAdapter`，提供统一的数据访问接口：

```python
class BaseDataAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def get_bar_data(self, symbol: str, exchange: Exchange, interval: Interval, start: datetime, end: datetime) -> List[BarData]: ...
```

### RPC QMT 适配器 (RpcQmtAdapter)

通过 RPC 协议连接 QMT 交易终端，提供实时和历史数据访问。

#### 核心特性

- **双 Socket 架构**：
  - REQ (请求) Socket：用于主动查询历史数据
  - SUB (订阅) Socket：接收实时心跳和行情推送

- **心跳检测机制**：
  - 心跳超时容差：30 秒
  - 心跳轮询间隔：1 秒（正常）/ 100ms（快速）
  - 警告冷却时间：60 秒

#### 心跳处理机制详解

```python
class CustomRpcClient(RpcClient):
    HEARTBEAT_TOLERANCE_MS = 30000      # 30秒心跳容差
    POLL_INTERVAL_MS = 1000             # 正常轮询间隔
    FAST_POLL_INTERVAL_MS = 100         # 快速轮询间隔
    WARNING_COOLDOWN_MS = 60000         # 60秒警告冷却
```

**心跳更新逻辑**：
1. **SUB Socket**：接收服务器推送的心跳包，自动更新 `_last_heartbeat_ms`
2. **REQ Socket**：在调用 `query_history` 后手动更新心跳时间戳

```python
# 成功查询后更新心跳时间戳
if result:
    from time import time as current_time
    self._last_heartbeat_ms = int(current_time() * 1000)
```

**警告级别**：
- `DEBUG`：心跳超时但不触发断开（下载数据时的正常情况）
- `WARNING`：心跳超时且触发断开连接

### 连接状态管理

```python
class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
```

### 历史数据下载

支持多种数据类型下载：

```python
# 日线数据
bars = adapter.query_history(
    symbol="000001",
    exchange=Exchange.SZSE,
    interval=Interval.DAILY,
    start=datetime(2021, 1, 1),
    end=datetime.now(),
    dividend_type="front"  # 前复权
)

# 分钟线数据
bars = adapter.query_history(
    symbol="000001",
    exchange=Exchange.SZSE,
    interval=Interval.MINUTE,
    start=datetime(2026, 2, 1),
    end=datetime.now()
)
```

## 目录结构

```
adapter/
├── __init__.py                 # 模块初始化，导出适配器
├── base.py                     # BaseDataAdapter 基类
├── rpc_qmt_adapter.py          # RPC QMT 适配器
└── (其他适配器...)
```

## 快速开始

### 基本使用

```python
from vnpy_china_data.adapter import RpcQmtAdapter
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime, timedelta

# 创建适配器实例
adapter = RpcQmtAdapter(
    rep_address="tcp://192.168.2.168:10010",
    pub_address="tcp://192.168.2.168:10020",
    account_id="your_account_id"
)

# 连接
if adapter.connect():
    print("连接成功")

    # 查询历史数据
    end = datetime.now()
    start = end - timedelta(days=30)

    bars = adapter.query_history(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=start,
        end=end
    )

    print(f"获取到 {len(bars)} 条K线数据")

    # 断开连接
    adapter.disconnect()
```

### 批量下载

```python
from vnpy_china_data.service import ChinaDataService

service = ChinaDataService()
service.connect()

# 下载股票列表
stocks = service.get_stock_list()

for stock in stocks:
    bars = service.get_bar_data(
        symbol=stock.symbol,
        exchange=stock.exchange,
        interval=Interval.DAILY,
        start=datetime(2021, 1, 1),
        end=datetime.now()
    )
    print(f"{stock.symbol} {stock.exchange.value}: {len(bars)} bars")
```

## 配置说明

### QMT RPC 配置

在 `.vntrader_china/config/global_development.yaml` 中配置：

```yaml
qmt:
  enabled: true
  use_rpc: true               # 使用 RPC 模式
  account_id: "your_account_id"
  # mini_path 不需要在 RPC 模式下配置

rpc:
  rep_address: "tcp://192.168.2.168:10010"
  pub_address: "tcp://192.168.2.168:10020"
  request_timeout: 5000
```

### 本地 QMT 配置

```yaml
qmt:
  enabled: true
  use_rpc: false              # 本地模式
  account_id: "your_account_id"
  mini_path: "D:/国金证券QMT交易端/userdata_mini/"
  session_id: 0
  password: ""
```

## 相关模块

- [vnpy_china_data](../) - A股数据服务
- [vnpy_china_config](../../vnpy_china_config/) - 配置管理
- [vnpy.rpc](../../../vnpy/rpc/) - RPC 通信框架

## 变更记录

### 2026-02-28 - v1.1.0
- 🔧 **心跳检测优化**：
  - 修复 REQ Socket 请求时心跳超时的误报问题
  - 在 `query_history` 成功后更新心跳时间戳
  - 将警告冷却时间从 5 秒增加到 60 秒
  - 将心跳超时日志级别从 WARNING 降为 DEBUG

### 2026-02-27
- 🐛 **Bug修复**：
  - 添加 `gateway_name` 字段到 BarData 对象
  - 修复 Interval 枚举处理问题
  - 实现 miniQMT 历史数据下载功能

### 2026-02-26
- 🔴 **Bug修复**：
  - 修复 RPC 客户端心跳检测中的 TypeError
  - 添加类型注解和运行时断言
  - 优化 `_last_warning_time` 的类型检查


