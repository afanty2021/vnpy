# 监控告警系统设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-004
> 优先级：P0

---

## 1. 设计目标

构建完善的A股交易监控告警系统，实现：

1. **系统监控**：进程、QMT连接、内存、CPU、磁盘
2. **交易监控**：成交、委托、持仓、资金、盈亏实时监控
3. **风控告警**：仓位、亏损、止损、异常交易告警
4. **多通道通知**：邮件、微信、短信、界面弹窗

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

### 3.1 监控器基类

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

### 3.4 告警引擎

```python
from vnpy.event import EventEngine, Event
from typing import Callable, Optional


class AlertEngine:
    """告警引擎"""

    def __init__(self, event_engine: EventEngine):
        self.event_engine = event_engine
        self.channels: dict[str, AlertChannel] = {}
        self.rules: list[AlertRule] = []
        self.history: AlertHistory = AlertHistory()

        # 加载配置
        self._load_config()

    def register_channel(self, name: str, channel: "AlertChannel"):
        """注册告警通道"""
        self.channels[name] = channel

    def add_rule(self, rule: "AlertRule"):
        """添加告警规则"""
        self.rules.append(rule)

    def send(
        self,
        title: str,
        message: str,
        level: str = "info",
        channels: Optional[list[str]] = None
    ):
        """发送告警"""
        # 记录历史
        self.history.add(title, message, level)

        # 发送到各通道
        channels = channels or list(self.channels.keys())
        for channel_name in channels:
            channel = self.channels.get(channel_name)
            if channel:
                try:
                    channel.send(title, message, level)
                except Exception as e:
                    print(f"发送告警失败: {e}")

    def evaluate_rules(self, monitor_items: list[MonitorItem]):
        """评估告警规则"""
        for item in monitor_items:
            for rule in self.rules:
                if rule.match(item):
                    self.send(
                        title=f"{rule.name}告警",
                        message=f"{item.name}: {item.value}",
                        level=rule.level
                    )
```

### 3.5 告警规则

```python
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: Callable[[Any], bool]
    level: str  # info/warning/critical
    message_template: str
    enabled: bool = True
    cooldown: int = 300  # 冷却时间（秒）


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

## 4. 告警历史

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import json


@dataclass
class AlertRecord:
    """告警记录"""
    id: str
    title: str
    message: str
    level: str
    timestamp: datetime
    channels: List[str]
    sent: bool = True


class AlertHistory:
    """告警历史"""

    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.records: List[AlertRecord] = []

    def add(self, title: str, message: str, level: str, channels: List[str] = None):
        """添加告警记录"""
        import uuid
        record = AlertRecord(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            level=level,
            timestamp=datetime.now(),
            channels=channels or []
        )
        self.records.append(record)

        # 限制记录数量
        if len(self.records) > self.max_records:
            self.records.pop(0)

    def get_recent(self, limit: int = 100) -> List[AlertRecord]:
        """获取最近的告警记录"""
        return self.records[-limit:]

    def get_by_level(self, level: str) -> List[AlertRecord]:
        """按级别筛选"""
        return [r for r in self.records if r.level == level]

    def to_json(self) -> str:
        """导出为JSON"""
        return json.dumps([
            {
                "id": r.id,
                "title": r.title,
                "message": r.message,
                "level": r.level,
                "timestamp": r.timestamp.isoformat(),
                "channels": r.channels
            }
            for r in self.records
        ], ensure_ascii=False, indent=2)
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

## 7. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基础类 | 0.5人天 |
| 2 | 实现系统监控器 | 1人天 |
| 3 | 实现交易监控器 | 1.5人天 |
| 4 | 实现告警引擎和规则 | 1人天 |
| 5 | 实现通知通道（邮件/微信/短信/GUI） | 1.5人天 |
| 6 | 实现告警历史 | 0.5人天 |
| 合计 | | **6人天** |

> 注：需求文档中预估5人天，实际设计为6人天，建议增加1人天以确保质量

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
