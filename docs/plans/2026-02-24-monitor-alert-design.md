# 监控告警系统设计文档

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-004
> 优先级：P0
>
> **变更记录**:
> - v1.1: 添加与AStockRiskManager集成接口、告警去重机制、告警优先级系统
> - v1.0: 初始版本

---

## 1. 设计目标

构建完善的A股交易监控告警系统，实现：

1. **系统监控**：进程、QMT连接、内存、CPU、磁盘
2. **交易监控**：成交、委托、持仓、资金、盈亏实时监控
3. **风控告警**：仓位、亏损、止损、异常交易告警
4. **多通道通知**：邮件、微信、短信、界面弹窗
5. **风控集成**：与vnpy_china_rules的AStockRiskManager深度集成
6. **智能告警**：告警去重、优先级管理、冷却时间控制

### 1.1 与AStockRiskManager集成

**监控告警系统与风控模块的集成是核心设计**：

```
┌─────────────────────────────────────────────────────────────────┐
│                 监控告警与风控集成架构                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   vnpy_china_rules (REQ-002)           vnpy_china_monitor (REQ-004)│
│   ┌─────────────────────────┐         ┌─────────────────────────┐│
│   │  AStockRiskManager      │────────▶│  AlertEngine            ││
│   │  • PositionControlRule  │  触发   │  • 去重机制            ││
│   │  • StopProfitLossRule   │  告警   │  • 优先级队列          ││
│   │  • CapitalRiskRule      │         │  • 冷却时间            ││
│   │  • TradingLimitRule     │         │  • 多通道通知          ││
│   └─────────────────────────┘         └─────────────────────────┘│
│                  │                              │                 │
│                  │ 通过接口集成                  │                 │
│                  ▼                              ▼                 │
│           IRiskAlertProvider               AlertChannel          │
│           (风控告警提供者)                (通知通道)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     监控告警系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│  【监控层】                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │SystemMon │ │TradeMon  │ │RiskMon   │ │CustomMon │          │
│  │(系统监控)│ │(交易监控)│ │(风控监控)│ │(自定义)  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  【告警层】                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ AlertEn  │ │AlertRule │ │AlertChan │ │AlertHist │          │
│  │(告警引擎)│ │(告警规则)│ │(通知通道)│ │(历史记录)│          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  【通知层】                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Email    │ │ WeChat   │ │  SMS     │ │   GUI    │          │
│  │(邮件)    │ │(企业微信)│ │(短信)    │ │(界面弹窗)│          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_monitor/
├── __init__.py
├── monitor/
│   ├── __init__.py
│   ├── base.py                 # 监控器基类
│   ├── system_monitor.py      # 系统监控
│   ├── trade_monitor.py       # 交易监控
│   └── risk_monitor.py        # 风控监控
├── alert/
│   ├── __init__.py
│   ├── engine.py              # 告警引擎
│   ├── rule.py                # 告警规则
│   ├── channel.py             # 通知通道基类
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── email_channel.py   # 邮件通道
│   │   ├── wechat_channel.py  # 微信通道
│   │   ├── sms_channel.py     # 短信通道
│   │   └── gui_channel.py     # GUI弹窗通道
│   └── history.py             # 告警历史
├── notifier.py               # 统一通知器
└── config.py                  # 配置
```

---

## 3. 核心类设计

### 3.1 告警优先级系统

```python
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional


class AlertPriority(IntEnum):
    """告警优先级（数值越大优先级越高）"""
    INFO = 10        # 信息级别
    LOW = 20         # 低优先级
    NORMAL = 30      # 普通级别
    HIGH = 50        # 高优先级
    CRITICAL = 70    # 严重级别
    EMERGENCY = 90   # 紧急级别


@dataclass
class AlertFingerprint:
    """告警指纹 - 用于去重"""
    source: str              # 告警来源（system/trade/risk）
    type: str                # 告警类型
    key: str                 # 告警标识符（如股票代码、监控项名）

    def __hash__(self) -> int:
        return hash(f"{self.source}:{self.type}:{self.key}")

    def __eq__(self, other) -> bool:
        if not isinstance(other, AlertFingerprint):
            return False
        return (
            self.source == other.source and
            self.type == other.type and
            self.key == other.key
        )


@dataclass(order=True)
class AlertMessage:
    """告警消息（支持优先级排序）"""
    priority: int                    # 优先级（AlertPriority）
    timestamp: datetime               # 时间戳（用于排序）
    title: str = field(compare=False)  # 标题
    message: str = field(compare=False)  # 内容
    level: str = field(compare=False)   # 级别名称
    fingerprint: AlertFingerprint = field(compare=False, default=None)
    metadata: dict = field(compare=False, default_factory=dict)

    @classmethod
    def create(
        cls,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL,
        source: str = "system",
        alert_type: str = "general",
        key: str = "",
        **kwargs
    ) -> "AlertMessage":
        """创建告警消息"""
        return cls(
            priority=priority,
            timestamp=datetime.now(),
            title=title,
            message=message,
            level=priority.name,
            fingerprint=AlertFingerprint(source, alert_type, key) if key else None,
            metadata=kwargs
        )
```

### 3.2 风控告警接口

```python
from abc import ABC, abstractmethod
from typing import List


class IRiskAlertProvider(ABC):
    """风控告警提供者接口 - AStockRiskManager需实现此接口"""

    @abstractmethod
    def get_active_risk_alerts(self) -> List[AlertMessage]:
        """获取当前活跃的风控告警"""
        pass

    @abstractmethod
    def subscribe_risk_events(self, callback):
        """订阅风控事件"""
        pass

    @abstractmethod
    def get_risk_status(self) -> dict:
        """获取风控状态"""
        pass


class RiskAlertBridge:
    """风控告警桥接器 - 连接AStockRiskManager和AlertEngine"""

    def __init__(self, risk_manager: "AStockRiskManager", alert_engine: "AlertEngine"):
        """
        初始化桥接器

        Args:
            risk_manager: AStockRiskManager实例
            alert_engine: AlertEngine实例
        """
        self.risk_manager = risk_manager
        self.alert_engine = alert_engine

        # 风控规则映射到告警优先级
        self.rule_priority_map = {
            "PositionControlRule": AlertPriority.HIGH,
            "StopProfitLossRule": AlertPriority.CRITICAL,
            "CapitalRiskRule": AlertPriority.CRITICAL,
            "TradingLimitRule": AlertPriority.HIGH,
        }

        # 订阅风控事件
        if hasattr(risk_manager, 'subscribe_risk_events'):
            risk_manager.subscribe_risk_events(self._on_risk_event)

    def _on_risk_event(self, event: dict):
        """
        处理风控事件

        Args:
            event: 风控事件字典
                - rule_name: 规则名称
                - rule_type: 规则类型
                - message: 触发消息
                - data: 相关数据
        """
        rule_name = event.get("rule_name", "")
        rule_type = event.get("rule_type", "")
        message = event.get("message", "")
        data = event.get("data", {})

        # 获取优先级
        priority = self.rule_priority_map.get(rule_name, AlertPriority.NORMAL)

        # 创建告警消息
        alert = AlertMessage.create(
            title=f"风控触发: {rule_name}",
            message=message,
            priority=priority,
            source="risk",
            alert_type=rule_type,
            key=data.get("symbol", rule_name),
            **data
        )

        # 发送到告警引擎
        self.alert_engine.send_alert(alert)

    def check_risk_status(self):
        """检查风控状态并发送告警"""
        if not hasattr(self.risk_manager, 'get_risk_status'):
            return

        status = self.risk_manager.get_risk_status()

        # 检查各类风控指标
        if status.get("daily_loss_ratio", 0) < -0.05:
            self.alert_engine.send_alert(AlertMessage.create(
                title="日亏损告警",
                message=f"当日亏损{abs(status['daily_loss_ratio']):.2%}",
                priority=AlertPriority.EMERGENCY,
                source="risk",
                alert_type="daily_loss",
                key="daily"
            ))

        if status.get("total_position_ratio", 0) > 0.8:
            self.alert_engine.send_alert(AlertMessage.create(
                title="总仓位告警",
                message=f"总仓位{status['total_position_ratio']:.2%}超过80%",
                priority=AlertPriority.HIGH,
                source="risk",
                alert_type="position",
                key="total"
            ))
```

### 3.3 告警去重机制

```python
import hashlib
import json
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Set


class AlertDeduplicator:
    """告警去重器 - 防止短时间内重复告警"""

    def __init__(self, dedup_window: int = 300):
        """
        初始化去重器

        Args:
            dedup_window: 去重时间窗口（秒），默认5分钟
        """
        self.dedup_window = dedup_window
        self.alert_history: Dict[AlertFingerprint, deque] = {}
        self.cooldown_periods: Dict[AlertFingerprint, datetime] = {}

    def should_send(self, alert: AlertMessage) -> bool:
        """
        判断是否应该发送告警

        Args:
            alert: 告警消息

        Returns:
            True表示应该发送，False表示被去重
        """
        if not alert.fingerprint:
            return True

        # 检查冷却期
        if alert.fingerprint in self.cooldown_periods:
            cooldown_end = self.cooldown_periods[alert.fingerprint]
            if datetime.now() < cooldown_end:
                return False

        return True

    def record_sent(self, alert: AlertMessage, cooldown: int = 0):
        """
        记录已发送的告警

        Args:
            alert: 告警消息
            cooldown: 冷却时间（秒）
        """
        if not alert.fingerprint:
            return

        # 记录发送时间
        if alert.fingerprint not in self.alert_history:
            self.alert_history[alert.fingerprint] = deque(maxlen=10)

        self.alert_history[alert.fingerprint].append(datetime.now())

        # 设置冷却期
        if cooldown > 0:
            self.cooldown_periods[alert.fingerprint] = datetime.now() + timedelta(seconds=cooldown)

    def get_alert_count(self, fingerprint: AlertFingerprint, window: int = None) -> int:
        """
        获取指定时间窗口内的告警次数

        Args:
            fingerprint: 告警指纹
            window: 时间窗口（秒），默认使用dedup_window

        Returns:
            告警次数
        """
        if fingerprint not in self.alert_history:
            return 0

        window = window or self.dedup_window
        cutoff = datetime.now() - timedelta(seconds=window)

        count = sum(1 for t in self.alert_history[fingerprint] if t > cutoff)
        return count

    def clear_history(self, fingerprint: AlertFingerprint = None):
        """
        清除历史记录

        Args:
            fingerprint: 告警指纹，None表示清除全部
        """
        if fingerprint:
            self.alert_history.pop(fingerprint, None)
            self.cooldown_periods.pop(fingerprint, None)
        else:
            self.alert_history.clear()
            self.cooldown_periods.clear()
```

### 3.4 监控器基类

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MonitorItem:
    """监控项"""
    name: str
    value: Any
    timestamp: datetime
    status: str  # normal/warning/critical


class BaseMonitor(ABC):
    """监控器基类"""

    name: str = ""

    def __init__(self, event_engine, alert_engine):
        self.event_engine = event_engine
        self.alert_engine = alert_engine
        self.enabled = True
        self.items: dict[str, MonitorItem] = {}

    @abstractmethod
    def check(self) -> list[MonitorItem]:
        """执行检查，返回监控项列表"""
        pass

    def start(self):
        """启动监控"""
        pass

    def stop(self):
        """停止监控"""
        pass
```

### 3.2 系统监控

```python
import psutil
from datetime import datetime


class SystemMonitor(BaseMonitor):
    """系统监控"""

    name = "system"

    parameters = {
        "cpu_threshold": 80,        # CPU阈值
        "memory_threshold": 80,    # 内存阈值
        "disk_threshold": 90,      # 磁盘阈值
    }

    def check(self) -> list[MonitorItem]:
        """检查系统状态"""
        items = []

        # CPU使用率
        cpu_percent = psutil.cpu_percent()
        items.append(MonitorItem(
            name="cpu_usage",
            value=cpu_percent,
            timestamp=datetime.now(),
            status="critical" if cpu_percent > self.cpu_threshold else "normal"
        ))

        # 内存使用率
        memory = psutil.virtual_memory()
        items.append(MonitorItem(
            name="memory_usage",
            value=memory.percent,
            timestamp=datetime.now(),
            status="critical" if memory.percent > self.memory_threshold else "normal"
        ))

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        items.append(MonitorItem(
            name="disk_usage",
            value=disk.percent,
            timestamp=datetime.now(),
            status="critical" if disk.percent > self.disk_threshold else "normal"
        ))

        return items


class QMTConnectionMonitor(BaseMonitor):
    """QMT连接监控"""

    name = "qmt_connection"

    def __init__(self, event_engine, alert_engine, gateway):
        super().__init__(event_engine, alert_engine)
        self.gateway = gateway

    def check(self) -> list[MonitorItem]:
        """检查QMT连接状态"""
        # 检查网关是否连接
        connected = self.gateway and self.gateway.connected

        return [MonitorItem(
            name="qmt_connected",
            value=connected,
            timestamp=datetime.now(),
            status="critical" if not connected else "normal"
        )]
```

### 3.3 交易监控

```python
from vnpy.trader.object import TradeData, OrderData, PositionData
from vnpy.event import Event, EVENT_TRADE, EVENT_ORDER


class TradeMonitor(BaseMonitor):
    """交易监控"""

    name = "trade"

    def __init__(self, event_engine, alert_engine, main_engine):
        super().__init__(event_engine, alert_engine)
        self.main_engine = main_engine

        # 注册事件
        self.event_engine.register(EVENT_TRADE, self.on_trade)
        self.event_engine.register(EVENT_ORDER, self.on_order)

        # 交易统计
        self.today_trades: list[TradeData] = []
        self.today_orders: list[OrderData] = []

    def on_trade(self, event: Event):
        """成交推送"""
        trade: TradeData = event.data
        self.today_trades.append(trade)

        # 发送成交通知
        self.alert_engine.send(
            title="成交通知",
            message=f"{trade.symbol} {trade.direction.value} {trade.volume}股 @{trade.price}",
            level="info"
        )

    def on_order(self, event: Event):
        """委托推送"""
        order: OrderData = event.data
        self.today_orders.append(order)

        # 委托被拒绝
        if order.status == Status.REJECTED:
            self.alert_engine.send(
                title="委托被拒绝",
                message=f"{order.symbol}: {order.msg}",
                level="warning"
            )

    def check(self) -> list[MonitorItem]:
        """检查交易统计"""
        items = []

        # 当日成交笔数
        items.append(MonitorItem(
            name="today_trade_count",
            value=len(self.today_trades),
            timestamp=datetime.now(),
            status="normal"
        ))

        # 当日委托笔数
        items.append(MonitorItem(
            name="today_order_count",
            value=len(self.today_orders),
            timestamp=datetime.now(),
            status="normal"
        ))

        # 获取持仓和资金
        positions = self.main_engine.get_all_positions()
        account = self.main_engine.get_account()

        if account:
            # 当日盈亏
            items.append(MonitorItem(
                name="daily_pnl",
                value=account.balance - account.pre_balance,
                timestamp=datetime.now(),
                status="normal"
            ))

            # 资金使用率
            usage = (account.balance - account.available) / account.balance
            items.append(MonitorItem(
                name="capital_usage",
                value=usage,
                timestamp=datetime.now(),
                status="warning" if usage > 0.8 else "normal"
            ))

        return items

    def reset_daily(self):
        """重置当日统计"""
        self.today_trades.clear()
        self.today_orders.clear()
```

### 3.5 告警引擎（更新版）

```python
from vnpy.event import EventEngine, Event
from typing import Callable, Optional, List
import heapq
from threading import Lock


class AlertEngine:
    """告警引擎 - 支持去重、优先级、冷却时间"""

    def __init__(self, event_engine: EventEngine):
        self.event_engine = event_engine
        self.channels: dict[str, AlertChannel] = {}
        self.rules: list[AlertRule] = []

        # 新增：去重器和优先级队列
        self.deduplicator = AlertDeduplicator(dedup_window=300)
        self.priority_queue: List[AlertMessage] = []
        self.queue_lock = Lock()

        # 告警历史
        self.history: AlertHistory = AlertHistory()

        # 风控集成
        self.risk_bridge: Optional[RiskAlertBridge] = None

        # 加载配置
        self._load_config()

    def register_channel(self, name: str, channel: "AlertChannel"):
        """注册告警通道"""
        self.channels[name] = channel

    def add_rule(self, rule: "AlertRule"):
        """添加告警规则"""
        self.rules.append(rule)

    def connect_risk_manager(self, risk_manager: "AStockRiskManager"):
        """连接风控管理器"""
        self.risk_bridge = RiskAlertBridge(risk_manager, self)

    def send(
        self,
        title: str,
        message: str,
        level: str = "info",
        channels: Optional[list[str]] = None,
        source: str = "system",
        alert_type: str = "general",
        key: str = "",
        priority: Optional[int] = None,
        cooldown: int = 0
    ):
        """
        发送告警（兼容旧接口）

        Args:
            title: 告警标题
            message: 告警内容
            level: 级别 (info/warning/critical)
            channels: 通知通道列表
            source: 告警来源
            alert_type: 告警类型
            key: 告警标识符
            priority: 优先级（数值）
            cooldown: 冷却时间（秒）
        """
        # 映射level到priority
        priority_map = {
            "info": AlertPriority.INFO,
            "warning": AlertPriority.HIGH,
            "critical": AlertPriority.CRITICAL
        }
        alert_priority = priority or priority_map.get(level, AlertPriority.NORMAL)

        alert = AlertMessage.create(
            title=title,
            message=message,
            priority=AlertPriority(alert_priority),
            source=source,
            alert_type=alert_type,
            key=key
        )

        self.send_alert(alert, channels=channels, cooldown=cooldown)

    def send_alert(
        self,
        alert: AlertMessage,
        channels: Optional[list[str]] = None,
        cooldown: int = 0
    ):
        """
        发送告警消息（新接口）

        Args:
            alert: 告警消息
            channels: 通知通道列表
            cooldown: 冷却时间（秒）
        """
        # 检查去重
        if not self.deduplicator.should_send(alert):
            return

        # 记录已发送
        self.deduplicator.record_sent(alert, cooldown)

        # 记录历史
        self.history.add(
            alert.title,
            alert.message,
            alert.level,
            channels or list(self.channels.keys())
        )

        # 添加到优先级队列
        with self.queue_lock:
            heapq.heappush(self.priority_queue, alert)

        # 发送到各通道
        channels = channels or list(self.channels.keys())
        for channel_name in channels:
            channel = self.channels.get(channel_name)
            if channel:
                try:
                    channel.send(
                        alert.title,
                        alert.message,
                        alert.level,
                        priority=alert.priority
                    )
                except Exception as e:
                    print(f"发送告警失败: {e}")

    def get_pending_alerts(self, count: int = 10) -> List[AlertMessage]:
        """
        获取待处理的高优先级告警

        Args:
            count: 获取数量

        Returns:
            按优先级排序的告警列表
        """
        with self.queue_lock:
            if not self.priority_queue:
                return []

            # 弹出前count个告警
            alerts = []
            temp = []

            for _ in range(min(count, len(self.priority_queue))):
                alert = heapq.heappop(self.priority_queue)
                alerts.append(alert)
                temp.append(alert)

            # 重新放回队列
            for alert in temp:
                heapq.heappush(self.priority_queue, alert)

            return sorted(alerts, key=lambda x: (-x.priority, x.timestamp))

    def evaluate_rules(self, monitor_items: list[MonitorItem]):
        """评估告警规则"""
        for item in monitor_items:
            for rule in self.rules:
                if rule.match(item):
                    # 获取规则优先级
                    priority = getattr(rule, 'priority', AlertPriority.NORMAL)
                    cooldown = getattr(rule, 'cooldown', 300)

                    self.send(
                        title=f"{rule.name}告警",
                        message=f"{item.name}: {item.value}",
                        level=rule.level,
                        priority=priority,
                        cooldown=cooldown
                    )
```

### 3.6 通知通道（更新版）

```python
from abc import ABC, abstractmethod
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AlertChannel(ABC):
    """告警通道基类"""

    name: str = ""

    @abstractmethod
    def send(self, title: str, message: str, level: str, priority: int = 30):
        """发送告警"""
        pass


class EmailChannel(AlertChannel):
    """邮件告警通道"""

    name = "email"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        min_priority: int = 30
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.min_priority = min_priority  # 最低发送优先级

    def send(self, title: str, message: str, level: str, priority: int = 30):
        """发送邮件"""
        # 检查优先级
        if priority < self.min_priority:
            return

        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ",".join(self.to_addrs)
        msg["Subject"] = f"[{level.upper()}] {title}"

        body = f"""
        <h2>{title}</h2>
        <p><strong>级别:</strong> {level}</p>
        <p><strong>优先级:</strong> {priority}</p>
        <p><strong>时间:</strong> {datetime.now()}</p>
        <p><strong>内容:</strong> {message}</p>
        """
        msg.attach(MIMEText(body, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
```

### 3.7 告警规则（更新版）

```python
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: Callable[[Any], bool]
    level: str  # info/warning/critical
    priority: int = 30  # 新增：优先级数值
    message_template: str = ""
    enabled: bool = True
    cooldown: int = 300  # 冷却时间（秒）

    def match(self, item: MonitorItem) -> bool:
        """匹配规则"""
        if not self.enabled:
            return False
        return self.condition(item)
```

### 3.8 原告警规则构建器（更新版）

```python
class AlertRuleBuilder:
    """告警规则构建器"""

    @staticmethod
    def create_threshold_rule(
        name: str,
        monitor_name: str,
        threshold: float,
        operator: str = ">",
        level: str = "warning",
        priority: int = 30
    ) -> AlertRule:
        """创建阈值告警规则"""

        if operator == ">":
            condition = lambda x: x > threshold
        elif operator == "<":
            condition = lambda x: x < threshold
        elif operator == ">=":
            condition = lambda x: x >= threshold
        elif operator == "<=":
            condition = lambda x: x <= threshold
        elif operator == "==":
            condition = lambda x: x == threshold

        return AlertRule(
            name=name,
            condition=lambda item: (
                item.name == monitor_name and condition(item.value)
            ),
            level=level,
            priority=priority,
            message_template=f"{monitor_name}触发告警: {threshold}",
            cooldown=300
        )

    @staticmethod
    def create_position_rule(max_position_ratio: float) -> AlertRule:
        """创建仓位告警规则"""
        return AlertRule(
            name="仓位告警",
            condition=lambda item: (
                item.name == "total_position_ratio"
                and item.value > max_position_ratio
            ),
            level="warning",
            priority=AlertPriority.HIGH,  # 高优先级
            message_template=f"仓位比例{item.value:.2%}超过限制{max_position_ratio:.2%}",
            cooldown=600  # 10分钟冷却
        )

    @staticmethod
    def create_loss_rule(max_loss_ratio: float) -> AlertRule:
        """创建亏损告警规则"""
        return AlertRule(
            name="亏损告警",
            condition=lambda item: (
                item.name == "daily_pnl"
                and item.value < -max_loss_ratio
            ),
            level="critical",
            priority=AlertPriority.CRITICAL,  # 严重优先级
            message_template=f"当日亏损{abs(item.value):.2%}达到限制{max_loss_ratio:.2%}",
            cooldown=1800  # 30分钟冷却
        )
```


class AlertRuleBuilder:
    """告警规则构建器"""

    @staticmethod
    def create_threshold_rule(
        name: str,
        monitor_name: str,
        threshold: float,
        operator: str = ">",
        level: str = "warning"
    ) -> AlertRule:
        """创建阈值告警规则"""

        if operator == ">":
            condition = lambda x: x > threshold
        elif operator == "<":
            condition = lambda x: x < threshold
        elif operator == ">=":
            condition = lambda x: x >= threshold
        elif operator == "<=":
            condition = lambda x: x <= threshold
        elif operator == "==":
            condition = lambda x: x == threshold

        return AlertRule(
            name=name,
            condition=lambda item: (
                item.name == monitor_name and condition(item.value)
            ),
            level=level,
            message_template=f"{monitor_name}触发告警: {threshold}"
        )

    @staticmethod
    def create_position_rule(max_position_ratio: float) -> AlertRule:
        """创建仓位告警规则"""
        return AlertRule(
            name="仓位告警",
            condition=lambda item: (
                item.name == "total_position_ratio"
                and item.value > max_position_ratio
            ),
            level="warning",
            message_template=f"仓位比例{item.value:.2%}超过限制{max_position_ratio:.2%}"
        )

    @staticmethod
    def create_loss_rule(max_loss_ratio: float) -> AlertRule:
        """创建亏损告警规则"""
        return AlertRule(
            name="亏损告警",
            condition=lambda item: (
                item.name == "daily_pnl"
                and item.value < -max_loss_ratio
            ),
            level="critical",
            message_template=f"当日亏损{abs(item.value):.2%}达到限制{max_loss_ratio:.2%}"
        )
```

### 3.6 通知通道

```python
from abc import ABC, abstractmethod
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AlertChannel(ABC):
    """告警通道基类"""

    name: str = ""

    @abstractmethod
    def send(self, title: str, message: str, level: str):
        """发送告警"""
        pass


class EmailChannel(AlertChannel):
    """邮件告警通道"""

    name = "email"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str]
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, title: str, message: str, level: str):
        """发送邮件"""
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ",".join(self.to_addrs)
        msg["Subject"] = f"[{level.upper()}] {title}"

        body = f"""
        <h2>{title}</h2>
        <p><strong>级别:</strong> {level}</p>
        <p><strong>时间:</strong> {datetime.now()}</p>
        <p><strong>内容:</strong> {message}</p>
        """
        msg.attach(MIMEText(body, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)


class WeChatChannel(AlertChannel):
    """企业微信告警通道"""

    name = "wechat"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str, level: str):
        """发送企业微信消息"""
        import requests

        color = {
            "info": "#172B4D",
            "warning": "#FFAB00",
            "critical": "#FF5630"
        }.get(level, "#172B4D")

        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"""### {title}
> 级别: {level}
> 时间: {datetime.now()}
> 内容: {message}
"""
            }
        }

        requests.post(self.webhook_url, json=data)


class GUIChannel(AlertChannel):
    """GUI弹窗告警通道"""

    name = "gui"

    def __init__(self, main_window):
        self.main_window = main_window

    def send(self, title: str, message: str, level: str):
        """发送GUI弹窗"""
        # 通过Qt信号发送
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QTimer

        icon = {
            "info": QMessageBox.Information,
            "warning": QMessageBox.Warning,
            "critical": QMessageBox.Critical
        }.get(level, QMessageBox.Information)

        # 在主线程中显示
        QTimer.singleShot(0, lambda: QMessageBox(
            icon,
            title,
            message
        ).exec())
```

---

## 4. 告警历史（更新版）

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import json
from collections import defaultdict


@dataclass
class AlertRecord:
    """告警记录"""
    id: str
    title: str
    message: str
    level: str
    priority: int
    timestamp: datetime
    channels: List[str]
    fingerprint: Optional[str] = None
    sent: bool = True
    deduplicated: bool = False  # 是否被去重


class AlertHistory:
    """告警历史 - 支持去重统计"""

    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.records: List[AlertRecord] = []

        # 新增：去重统计
        self.dedup_stats: Dict[str, int] = defaultdict(int)
        self.total_sent: int = 0
        self.total_dedup: int = 0

    def add(
        self,
        title: str,
        message: str,
        level: str,
        channels: List[str] = None,
        priority: int = 30,
        fingerprint: Optional[str] = None,
        deduplicated: bool = False
    ):
        """添加告警记录"""
        import uuid
        record = AlertRecord(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            level=level,
            priority=priority,
            timestamp=datetime.now(),
            channels=channels or [],
            fingerprint=fingerprint,
            sent=not deduplicated,
            deduplicated=deduplicated
        )
        self.records.append(record)

        # 更新统计
        if deduplicated:
            self.total_dedup += 1
            if fingerprint:
                self.dedup_stats[fingerprint] += 1
        else:
            self.total_sent += 1

        # 限制记录数量
        if len(self.records) > self.max_records:
            removed = self.records.pop(0)
            if removed.deduplicated and removed.fingerprint:
                self.dedup_stats[removed.fingerprint] -= 1
                if self.dedup_stats[removed.fingerprint] <= 0:
                    del self.dedup_stats[removed.fingerprint]

    def get_recent(self, limit: int = 100) -> List[AlertRecord]:
        """获取最近的告警记录"""
        return self.records[-limit:]

    def get_by_level(self, level: str) -> List[AlertRecord]:
        """按级别筛选"""
        return [r for r in self.records if r.level == level]

    def get_by_priority(self, min_priority: int = 50) -> List[AlertRecord]:
        """按优先级筛选"""
        return [r for r in self.records if r.priority >= min_priority]

    def get_dedup_stats(self) -> Dict[str, int]:
        """获取去重统计"""
        return dict(self.dedup_stats)

    def get_summary(self) -> dict:
        """获取告警摘要"""
        level_counts = defaultdict(int)
        for r in self.records:
            level_counts[r.level] += 1

        return {
            "total": len(self.records),
            "sent": self.total_sent,
            "deduplicated": self.total_dedup,
            "by_level": dict(level_counts),
            "dedup_rate": f"{self.total_dedup / max(self.total_sent + self.total_dedup, 1) * 100:.1f}%"
        }

    def to_json(self) -> str:
        """导出为JSON"""
        return json.dumps([
            {
                "id": r.id,
                "title": r.title,
                "message": r.message,
                "level": r.level,
                "priority": r.priority,
                "timestamp": r.timestamp.isoformat(),
                "channels": r.channels,
                "sent": r.sent,
                "deduplicated": r.deduplicated
            }
            for r in self.records
        ], ensure_ascii=False, indent=2)
```

---

## 5. 集成方式（更新版）

### 5.1 与AStockRiskManager集成

```python
from vnpy_china_monitor import MonitorSystem
from vnpy_china_rules.risk.manager import AStockRiskManager


def main():
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 1. 初始化风控系统
    risk_manager = AStockRiskManager(main_engine, event_engine)
    risk_manager.initialize(
        qmt_gateway=main_engine.get_gateway("QMT"),
        tushare_token="your_token"
    )

    # 2. 初始化监控系统
    monitor_system = MonitorSystem(event_engine, main_engine)

    # 3. 连接风控管理器
    monitor_system.alert_engine.connect_risk_manager(risk_manager)

    # 4. 配置告警通道
    monitor_system.alert_engine.register_channel(
        "email",
        EmailChannel(
            smtp_host="smtp.qq.com",
            smtp_port=465,
            username="xxx@qq.com",
            password="xxx",
            from_addr="xxx@qq.com",
            to_addrs=["yyy@qq.com"],
            min_priority=50  # 只发送高优先级及以上告警
        )
    )

    monitor_system.alert_engine.register_channel(
        "wechat",
        WeChatChannel(webhook_url="https://qyapi.weixin.qq.com/xxx")
    )

    # 5. 添加告警规则
    monitor_system.alert_engine.add_rule(
        AlertRuleBuilder.create_loss_rule(0.05)  # 5%日亏损
    )
    monitor_system.alert_engine.add_rule(
        AlertRuleBuilder.create_position_rule(0.8)  # 80%总仓位
    )

    # 6. 启动监控
    monitor_system.start()

    # 运行
    main_engine.start()
```

---

## 5. 配置设计

```python
# vnpy_china_monitor/config.py


@dataclass
class MonitorConfig:
    """监控配置"""

    # 系统监控
    enable_system_monitor: bool = True
    system_check_interval: int = 60  # 秒

    # 交易监控
    enable_trade_monitor: bool = True
    trade_check_interval: int = 10  # 秒

    # 风控监控
    enable_risk_monitor: bool = True
    risk_check_interval: int = 5  # 秒

    # 告警配置
    enable_alert: bool = True

    # 邮件配置
    email_enabled: bool = False
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    email_username: str = ""
    email_password: str = ""
    from_addr: str = ""
    to_addrs: list[str] = field(default_factory=list)

    # 微信配置
    wechat_enabled: bool = False
    wechat_webhook: str = ""

    # 短信配置
    sms_enabled: bool = False
    sms_api_key: str = ""

    # GUI配置
    gui_enabled: bool = True


# 默认配置
DEFAULT_CONFIG = MonitorConfig()
```

---

## 6. 集成方式

```python
from vnpy_china_monitor import MonitorSystem


def main():
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 初始化监控系统
    monitor_system = MonitorSystem(event_engine, main_engine)

    # 配置告警通道
    monitor_system.alert_engine.register_channel(
        "email",
        EmailChannel(
            smtp_host="smtp.qq.com",
            smtp_port=465,
            username="xxx@qq.com",
            password="xxx",
            from_addr="xxx@qq.com",
            to_addrs=["yyy@qq.com"]
        )
    )

    monitor_system.alert_engine.register_channel(
        "wechat",
        WeChatChannel(webhook_url="https://qyapi.weixin.qq.com/xxx")
    )

    # 添加告警规则
    monitor_system.alert_engine.add_rule(
        AlertRuleBuilder.create_loss_rule(0.05)
    )
    monitor_system.alert_engine.add_rule(
        AlertRuleBuilder.create_position_rule(0.8)
    )

    # 启动监控
    monitor_system.start()

    # 运行
    main_engine.start()
```

---

## 7. 实施计划（更新版）

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基础类 | 0.5人天 |
| 2 | 实现告警优先级系统和去重机制 | 1人天 |
| 3 | 实现系统监控器 | 1人天 |
| 4 | 实现交易监控器 | 1.5人天 |
| 5 | 实现与AStockRiskManager的集成 | 1人天 |
| 6 | 实现告警引擎（支持优先级队列） | 1人天 |
| 7 | 实现通知通道（邮件/微信/短信/GUI） | 1.5人天 |
| 8 | 实现告警历史（去重统计） | 0.5人天 |
| 合计 | | **8人天** |

> 注：v1.1新增风控集成、去重机制、优先级系统，工时从6人天增加到8人天

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.1 | 2026-02-24 | 添加与AStockRiskManager集成接口、告警去重机制、告警优先级系统 |
| v1.0 | 2026-02-24 | 初始版本 |

---

## 9. 新增API参考

### 9.1 告警优先级常量

```python
from vnpy_china_monitor.alert import AlertPriority

# 使用示例
alert = AlertMessage.create(
    title="紧急告警",
    message="系统发生严重错误",
    priority=AlertPriority.EMERGENCY  # 90
)
```

### 9.2 去重器使用

```python
from vnpy_china_monitor.alert import AlertDeduplicator, AlertMessage

deduplicator = AlertDeduplicator(dedup_window=300)

alert = AlertMessage.create(
    title="测试告警",
    message="这是一条测试",
    source="test",
    alert_type="test",
    key="test_key"
)

# 检查是否应该发送
if deduplicator.should_send(alert):
    # 发送告警...
    # 记录发送，设置5分钟冷却
    deduplicator.record_sent(alert, cooldown=300)
```

### 9.3 风控告警桥接

```python
from vnpy_china_monitor.alert import RiskAlertBridge

# 连接风控管理器
bridge = RiskAlertBridge(risk_manager, alert_engine)

# 手动检查风控状态
bridge.check_risk_status()

# 触发风控事件时会自动发送告警
```

---

`★ Insight ─────────────────────────────────────`
**REQ-004 v1.1的关键改进：**
1. **告警优先级系统**：数值化优先级(10-90)，支持优先级队列排序
2. **告警去重机制**：基于告警指纹的去重，防止短时间重复告警
3. **风控深度集成**：通过RiskAlertBridge和IRiskAlertProvider接口实现与AStockRiskManager的无缝集成
4. **冷却时间控制**：每个告警规则可配置独立冷却时间
`─────────────────────────────────────────────────`
