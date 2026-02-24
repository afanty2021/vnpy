# REQ-004 监控告警系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-004
> 优先级：P0
> 状态：待实施

---

## 1. 模块概述

### 1.1 模块定位

`vnpy_china_monitor` 是A股交易系统的监控告警模块，负责：
- 系统状态监控（进程、QMT连接、内存、CPU）
- 交易状态监控（成交、委托、持仓、资金）
- 风控告警集成（仓位、亏损、止损等）
- 多通道通知（界面、邮件、微信）

### 1.2 模块位置

```
vnpy_china_monitor/
├── __init__.py               # 模块入口
├── CLAUDE.md                 # 模块文档
├── monitor/                  # 监控子模块
│   ├── __init__.py
│   ├── engine.py             # 监控引擎
│   ├── system_monitor.py     # 系统监控
│   ├── trade_monitor.py      # 交易监控
│   └── metrics.py            # 指标定义
├── alert/                    # 告警子模块
│   ├── __init__.py
│   ├── engine.py             # 告警引擎
│   ├── priority_queue.py     # 优先级队列
│   ├── deduplicator.py      # 去重机制
│   ├── channels/             # 通知通道
│   │   ├── __init__.py
│   │   ├── base.py          # 通道基类
│   │   ├── ui.py            # 界面通道
│   │   ├── email.py         # 邮件通道
│   │   └── wechat.py        # 微信通道
│   └── rules/                # 告警规则
│       ├── __init__.py
│       ├── base.py           # 规则基类
│       └── risk_bridge.py    # 风控桥接
├── integration/              # 集成模块
│   ├── __init__.py
│   └── risk_connector.py    # 风控连接器
└── tests/                   # 测试
    ├── __init__.py
    ├── test_monitor.py
    ├── test_alert.py
    └── test_integration.py
```

---

## 2. 核心类设计

### 2.1 监控引擎 (MonitorEngine)

**文件**: `vnpy_china_monitor/monitor/engine.py`

```python
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum

class MonitorType(Enum):
    """监控类型"""
    SYSTEM = "system"       # 系统监控
    TRADE = "trade"        # 交易监控
    RISK = "risk"          # 风控监控

@dataclass
class MonitorData:
    """监控数据"""
    monitor_type: MonitorType
    name: str
    value: any
    timestamp: datetime
    status: str = "normal"  # normal, warning, critical

class MonitorEngine:
    """监控引擎"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 监控项
        self._monitors: Dict[str, MonitorData] = {}

        # 监控器
        self._system_monitor = None
        self._trade_monitor = None

        # 回调
        self._callbacks: List[Callable] = []

    def register_system_monitor(self, monitor):
        """注册系统监控器"""

    def register_trade_monitor(self, monitor):
        """注册交易监控器"""

    def get_monitor_data(self, name: str) -> Optional[MonitorData]:
        """获取监控数据"""

    def get_all_monitors(self) -> List[MonitorData]:
        """获取所有监控数据"""

    def start(self):
        """启动监控"""

    def stop(self):
        """停止监控"""

    def register_callback(self, callback: Callable):
        """注册数据变化回调"""
```

**职责**:
- 管理所有监控项
- 协调系统监控和交易监控
- 提供监控数据查询接口

**工时估算**: 1.5 人天

---

### 2.2 系统监控器 (SystemMonitor)

**文件**: `vnpy_china_monitor/monitor/system_monitor.py`

```python
import psutil
from datetime import datetime
from typing import Dict

class SystemMonitor:
    """系统监控器"""

    def __init__(self, monitor_interval: int = 60):
        self.monitor_interval = monitor_interval  # 秒
        self._running = False
        self._last_check = {}

    def check_qmt_connection(self) -> Dict:
        """检查QMT连接状态"""

    def check_memory_usage(self) -> Dict:
        """检查内存使用"""

    def check_cpu_usage(self) -> Dict:
        """检查CPU使用"""

    def check_disk_usage(self) -> Dict:
        """检查磁盘使用"""

    def check_process_status(self) -> Dict:
        """检查进程状态"""

    def get_all_metrics(self) -> Dict:
        """获取所有指标"""

    def start(self):
        """启动监控"""

    def stop(self):
        """停止监控"""
```

**监控指标**:
| 指标 | 阈值(警告/严重) | 检查频率 |
|-----|---------------|---------|
| QMT连接 | -/断开 | 30秒 |
| 内存使用率 | 80%/90% | 60秒 |
| CPU使用率 | 80%/90% | 60秒 |
| 磁盘使用率 | 85%/95% | 300秒 |
| 进程状态 | -/崩溃 | 30秒 |

**工时估算**: 1 人天

---

### 2.3 交易监控器 (TradeMonitor)

**文件**: `vnpy_china_monitor/monitor/trade_monitor.py`

```python
from vnpy.trader.object import TradeData, OrderData, AccountData, PositionData
from datetime import datetime
from typing import Dict, List

class TradeMonitor:
    """交易监控器"""

    def __init__(self, main_engine):
        self.main_engine = main_engine
        self._trade_history: List[TradeData] = []
        self._order_history: List[OrderData] = []

    def on_trade(self, trade: TradeData):
        """成交推送"""

    def on_order(self, order: OrderData):
        """委托推送"""

    def get_positions(self) -> List[PositionData]:
        """获取持仓"""

    def get_account(self) -> AccountData:
        """获取账户"""

    def get_daily_stats(self) -> Dict:
        """获取日统计数据"""

    def get_position_summary(self) -> Dict:
        """获取持仓汇总"""

    def get_order_stats(self) -> Dict:
        """获取委托统计"""
```

**监控内容**:
- 成交记录（时间、价格、数量、费用）
- 委托状态（ submitted, partial, filled, cancelled, rejected）
- 持仓变化（持仓量、成本、市值、盈亏）
- 资金变化（余额、可用、冻结）
- 日盈亏统计

**工时估算**: 1 人天

---

### 2.4 告警引擎 (AlertEngine)

**文件**: `vnpy_china_monitor/alert/engine.py`

```python
from vnpy.event import EventEngine, Event
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Callable, Dict, Optional
from enum import Enum
import heapq

class AlertPriority(IntEnum):
    """告警优先级"""
    INFO = 10
    LOW = 20
    NORMAL = 30
    HIGH = 50
    CRITICAL = 70
    EMERGENCY = 90

class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class AlertEvent:
    """告警事件"""
    id: str
    priority: AlertPriority
    title: str
    message: str
    severity: AlertSeverity
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict = field(default_factory=dict)
    acknowledged: bool = False

class AlertEngine:
    """告警引擎"""

    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 告警队列（优先级堆）
        self._alert_queue: List[AlertEvent] = []

        # 活跃告警
        self._active_alerts: Dict[str, AlertEvent] = {}

        # 去重器
        self._deduplicator = None

        # 通知通道
        self._channels: List[AlertChannel] = []

        # 告警回调
        self._callbacks: List[Callable] = []

    def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        priority: AlertPriority = AlertPriority.NORMAL,
        source: str = "system",
        data: Dict = None
    ):
        """发送告警"""

    def acknowledge_alert(self, alert_id: str):
        """确认告警"""

    def get_active_alerts(self) -> List[AlertEvent]:
        """获取活跃告警"""

    def get_alert_history(self, limit: int = 100) -> List[AlertEvent]:
        """获取告警历史"""

    def register_channel(self, channel: 'AlertChannel'):
        """注册通知通道"""

    def connect_risk_manager(self, risk_manager):
        """连接风控管理器"""

    def start(self):
        """启动告警引擎"""

    def stop(self):
        """停止告警引擎"""
```

**核心功能**:
- 优先级队列管理
- 告警去重
- 多通道通知
- 告警确认和历史记录

**工时估算**: 2 人天

---

### 2.5 告警去重器 (AlertDeduplicator)

**文件**: `vnpy_china_monitor/alert/deduplicator.py`

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Set
import hashlib

@dataclass
class DedupeConfig:
    """去重配置"""
    window_seconds: int = 300      # 去重时间窗口（5分钟）
    cooldown_seconds: int = 600    # 冷却时间（10分钟）
    max_same_alerts: int = 3      # 相同告警最大次数

class AlertDeduplicator:
    """告警去重器"""

    def __init__(self, config: DedupeConfig = None):
        self.config = config or DedupeConfig()
        self._alert_fingerprints: Dict[str, List[datetime]] = {}
        self._cooldown_fingerprints: Set[str] = set()
        self._stats = {
            "total_alerts": 0,
            "deduped_count": 0,
            "cooldown_count": 0,
        }

    def should_send(self, alert) -> bool:
        """判断是否应该发送告警"""

    def record_alert(self, fingerprint: str):
        """记录已发送的告警"""

    def get_fingerprint(self, alert) -> str:
        """计算告警指纹"""

    def get_stats(self) -> Dict:
        """获取去重统计"""
```

**去重策略**:
1. **指纹生成**: 基于 `source + title + severity` 生成唯一指纹
2. **时间窗口**: 5分钟内相同告警只发送一次
3. **冷却时间**: 同一告警冷却10分钟后重置
4. **最大次数**: 同一告警最多发送3次

**工时估算**: 0.5 人天

---

### 2.6 通知通道基类

**文件**: `vnpy_china_monitor/alert/channels/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AlertMessage:
    """告警消息"""
    title: str
    message: str
    severity: str
    priority: int
    timestamp: datetime
    source: str
    data: dict = None

class AlertChannel(ABC):
    """告警通道基类"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @abstractmethod
    def send(self, message: AlertMessage) -> bool:
        """发送告警消息"""

    @abstractmethod
    def test_connection(self) -> bool:
        """测试通道连接"""

    def format_message(self, message: AlertMessage) -> str:
        """格式化消息"""
```

---

### 2.7 风控桥接 (RiskAlertBridge)

**文件**: `vnpy_china_monitor/alert/rules/risk_bridge.py`

```python
from vnpy_china_rules.risk import AStockRiskManager, RiskAlertEvent, IRiskAlertProvider
from datetime import datetime, timedelta
from typing import Dict, List

class RiskAlertBridge:
    """风控告警桥接器"""

    def __init__(self, alert_engine, risk_manager: AStockRiskManager):
        self.alert_engine = alert_engine
        self.risk_manager = risk_manager
        self._last_check = datetime.now()
        self._check_interval = 60  # 秒

    def start(self):
        """启动桥接器"""

    def stop(self):
        """停止桥接器"""

    def check_risk_status(self):
        """检查风控状态"""

    def _on_risk_alert(self, alert: RiskAlertEvent):
        """处理风控告警"""

    def _convert_severity(self, severity: str) -> AlertSeverity:
        """转换严重程度"""

    def _convert_priority(self, severity: str) -> AlertPriority:
        """转换优先级"""
```

**集成逻辑**:
1. 订阅 AStockRiskManager 的风控事件
2. 定期查询风控状态
3. 将风控告警转换为监控告警
4. 根据严重程度设置优先级

**工时估算**: 1 人天

---

## 3. 接口设计

### 3.1 与 REQ-002 集成接口

```python
# vnpy_china_monitor/integration/risk_connector.py
from vnpy_china_rules.risk import AStockRiskManager, IRiskAlertProvider

class RiskConnector:
    """风控连接器"""

    def __init__(self, monitor_system):
        self.monitor_system = monitor_system

    def connect(self, risk_manager: AStockRiskManager):
        """连接到风控管理器"""

    def disconnect(self):
        """断开连接"""

    def is_connected(self) -> bool:
        """检查连接状态"""
```

### 3.2 事件定义

```python
# vnpy_china_monitor/event.py
from vnpy.event import Event

EVENT_MONITOR_DATA = "eMonitorData"
EVENT_ALERT_SENT = "eAlertSent"
EVENT_ALERT_ACKNOWLEDGED = "eAlertAck"
EVENT_RISK_ALERT = "eRiskAlert"

# 事件数据格式
{
    "monitor_type": "system|trade|risk",
    "name": "memory|cpu|position|...",
    "value": ...,
    "status": "normal|warning|critical",
    "timestamp": "..."
}
```

---

## 4. 开发计划

### 4.1 开发阶段

| 阶段 | 内容 | 工时 | 依赖 |
|-----|------|-----|------|
| **Phase 1** | 基础框架搭建 | 2天 | - |
| | - 模块目录结构创建 | 0.5天 | - |
| | - __init__.py 和基础类 | 0.5天 | - |
| | - 事件定义 | 0.5天 | - |
| | - 日志配置 | 0.5天 | - |
| **Phase 2** | 监控引擎 | 3.5天 | Phase 1 |
| | - MonitorEngine 实现 | 1.5天 | - |
| | - SystemMonitor 实现 | 1天 | - |
| | - TradeMonitor 实现 | 1天 | - |
| **Phase 3** | 告警引擎 | 4天 | Phase 1 |
| | - AlertEngine 核心 | 1.5天 | - |
| | - AlertDeduplicator | 0.5天 | - |
| | - AlertPriorityQueue | 0.5天 | - |
| | - 通知通道基类 | 0.5天 | - |
| | - UI通道实现 | 1天 | - |
| **Phase 4** | 风控集成 | 2天 | Phase 2, Phase 3 |
| | - RiskAlertBridge | 1天 | - |
| | - RiskConnector | 0.5天 | - |
| | - 与AStockRiskManager对接 | 0.5天 | - |
| **Phase 5** | 高级功能 | 2天 | Phase 3 |
| | - 邮件通道 | 0.5天 | - |
| | - 微信通道 | 0.5天 | - |
| | - 告警规则扩展 | 1天 | - |
| **Phase 6** | 测试与文档 | 2天 | All |
| | - 单元测试 | 1天 | - |
| | - 集成测试 | 0.5天 | - |
| | - 文档编写 | 0.5天 | - |

### 4.2 总工时估算

| 阶段 | 工时 |
|-----|------|
| Phase 1 | 2天 |
| Phase 2 | 3.5天 |
| Phase 3 | 4天 |
| Phase 4 | 2天 |
| Phase 5 | 2天 |
| Phase 6 | 2天 |
| **总计** | **15.5天** |

---

## 5. 实现顺序

### 5.1 第一周

| 日期 | 任务 | 交付物 |
|-----|------|-------|
| Day 1 | 模块结构搭建 | 目录结构、基础类 |
| Day 2 | MonitorEngine | 监控引擎框架 |
| Day 3 | SystemMonitor | 系统监控器 |
| Day 4 | TradeMonitor | 交易监控器 |
| Day 5 | AlertEngine核心 | 告警引擎骨架 |

### 5.2 第二周

| 日期 | 任务 | 交付物 |
|-----|------|-------|
| Day 6 | 告警去重器 | AlertDeduplicator |
| Day 7 | 通知通道 | UI通道实现 |
| Day 8 | RiskAlertBridge | 风控桥接器 |
| Day 9 | 邮件/微信通道 | 通知通道完善 |
| Day 10 | 测试与集成 | 测试用例 |

---

## 6. 配置项

### 6.1 监控配置

```python
# vnpy_china_monitor/settings.py
from dataclasses import dataclass

@dataclass
class MonitorSettings:
    """监控设置"""
    # 系统监控
    qmt_check_interval: int = 30          # QMT连接检查间隔(秒)
    system_check_interval: int = 60         # 系统检查间隔(秒)
    memory_warning_threshold: float = 0.80  # 内存警告阈值
    memory_critical_threshold: float = 0.90 # 内存严重阈值

    # 交易监控
    trade_check_interval: int = 5           # 交易检查间隔(秒)
    max_trade_history: int = 10000          # 最大成交历史记录

    # 告警设置
    alert_check_interval: int = 1           # 告警检查间隔(秒)
    max_active_alerts: int = 100           # 最大活跃告警数
    alert_history_limit: int = 1000        # 告警历史限制

    # 去重设置
    dedupe_window_seconds: int = 300       # 去重时间窗口
    dedupe_cooldown_seconds: int = 600     # 冷却时间
    dedupe_max_count: int = 3              # 最大重复次数
```

### 6.2 通知通道配置

```python
@dataclass
class ChannelSettings:
    """通知通道设置"""
    # UI通道
    ui_enabled: bool = True
    ui_popup_duration: int = 10             # 弹窗持续时间(秒)

    # 邮件通道
    email_enabled: bool = False
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: list = None

    # 微信通道
    wechat_enabled: bool = False
    wechat_webhook_url: str = ""
```

---

## 7. 测试策略

### 7.1 单元测试

| 测试类 | 测试方法 | 覆盖内容 |
|-------|---------|---------|
| TestMonitorEngine | test_register_monitor | 监控器注册 |
| | test_get_monitor_data | 数据获取 |
| | test_callback | 回调通知 |
| TestSystemMonitor | test_memory_check | 内存监控 |
| | test_cpu_check | CPU监控 |
| | test_qmt_connection | QMT连接 |
| TestAlertEngine | test_send_alert | 告警发送 |
| | test_priority_queue | 优先级队列 |
| | test_deduplication | 去重机制 |
| TestRiskAlertBridge | test_connect | 连接风控 |
| | test_convert_severity | 程度转换 |

### 7.2 集成测试

- MonitorEngine + SystemMonitor 集成
- MonitorEngine + TradeMonitor 集成
- AlertEngine + AlertDeduplicator 集成
- AlertEngine + RiskAlertBridge + AStockRiskManager 集成

---

## 8. 使用示例

### 8.1 基本使用

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_china_monitor import MonitorSystem

# 创建监控系统
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

monitor_system = MonitorSystem(main_engine, event_engine)

# 配置
monitor_system.configure(
    memory_warning_threshold=0.75,
    email_enabled=True,
    email_to=["trader@example.com"]
)

# 启动
monitor_system.start()

# 发送告警
monitor_system.alert_engine.send_alert(
    title="测试告警",
    message="这是一条测试告警",
    severity=AlertSeverity.INFO
)

# 获取监控数据
data = monitor_system.monitor_engine.get_all_monitors()

# 停止
monitor_system.stop()
```

### 8.2 与风控集成

```python
from vnpy_china_rules.risk import create_risk_manager
from vnpy_china_monitor import MonitorSystem

# 创建风控管理器
risk_manager = create_risk_manager(main_engine, event_engine)

# 创建监控系统
monitor_system = MonitorSystem(main_engine, event_engine)

# 连接风控
monitor_system.connect_risk_manager(risk_manager)

# 启动
monitor_system.start()

# 当风控规则触发时，告警会自动发送到监控系统
```

---

## 9. 已知依赖

### 9.1 内部依赖

| 模块 | 依赖内容 |
|-----|---------|
| vnpy.event | EventEngine, Event |
| vnpy.trader.engine | MainEngine |
| vnpy_china_rules.risk | AStockRiskManager, IRiskAlertProvider, RiskAlertEvent |

### 9.2 外部依赖

| 包 | 用途 | 版本 |
|---|------|-----|
| psutil | 系统监控 | >=5.9.0 |
| aiosmtpd | 邮件发送 | >=1.4.0 |
| requests | HTTP请求 | >=2.28.0 |

---

## 10. 风险与应对

| 风险 | 影响 | 应对措施 |
|-----|------|---------|
| QMT连接不稳定 | 监控告警频繁 | 增加连接重试机制和去重 |
| 告警风暴 | 系统性能下降 | 严格去重和限流 |
| 邮件发送失败 | 告警未送达 | 记录失败日志，降级到UI通知 |

---

*文档结束*
