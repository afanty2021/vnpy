# A股监控告警模块

> 更新时间：2026-02-24
> 版本：0.1.0
> 开发状态：开发中

## 模块概述

`vnpy_china_monitor` 是A股交易系统的监控告警模块，负责：
- 系统状态监控（进程、QMT连接、内存、CPU）
- 交易状态监控（成交、委托、持仓、资金）
- 风控告警集成（仓位、亏损、止损等）
- 多通道通知（界面、邮件、微信）

## 模块架构

```
vnpy_china_monitor/
├── __init__.py               # 模块入口
├── event.py                   # 事件定义
├── settings.py                # 配置项
├── monitor/                  # 监控子模块
│   ├── __init__.py
│   ├── engine.py             # 监控引擎
│   ├── system_monitor.py     # 系统监控
│   └── trade_monitor.py      # 交易监控
├── alert/                    # 告警子模块
│   ├── __init__.py
│   ├── engine.py             # 告警引擎
│   ├── priority_queue.py     # 优先级队列
│   ├── deduplicator.py       # 去重机制
│   ├── channels/             # 通知通道
│   │   ├── __init__.py
│   │   ├── base.py          # 通道基类
│   │   ├── ui.py            # 界面通道
│   │   ├── email.py         # 邮件通道
│   │   └── wechat.py        # 微信通道
│   └── rules/                # 告警规则
│       ├── __init__.py
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

## 核心组件

### 1. 监控引擎 (MonitorEngine)

负责管理所有监控项，协调系统监控和交易监控。

```python
from vnpy_china_monitor.monitor import MonitorEngine, MonitorType

# 创建监控引擎
monitor_engine = MonitorEngine(main_engine, event_engine)

# 注册系统监控器
system_monitor = SystemMonitor(monitor_engine)
monitor_engine.register_system_monitor(system_monitor)

# 注册交易监控器
trade_monitor = TradeMonitor(main_engine, event_engine, monitor_engine)
monitor_engine.register_trade_monitor(trade_monitor)

# 获取监控数据
all_monitors = monitor_engine.get_all_monitors()
system_monitors = monitor_engine.get_monitors_by_type(MonitorType.SYSTEM)
```

### 2. 系统监控器 (SystemMonitor)

监控QMT连接状态、内存、CPU、磁盘使用情况。

```python
from vnpy_china_monitor.monitor import SystemMonitor

# 创建系统监控器
system_monitor = SystemMonitor(
    monitor_engine,
    check_interval=60,
    memory_warning=0.80,
    memory_critical=0.90,
)

# 设置QMT网关
system_monitor.set_qmt_gateway(qmt_gateway)

# 获取所有指标
metrics = system_monitor.get_all_metrics()

# 启动监控
system_monitor.start()
```

### 3. 交易监控器 (TradeMonitor)

监控成交记录、委托状态、持仓变化、资金变化。

```python
from vnpy_china_monitor.monitor import TradeMonitor

# 创建交易监控器
trade_monitor = TradeMonitor(main_engine, event_engine, monitor_engine)

# 获取持仓
positions = trade_monitor.get_positions()

# 获取账户
account = trade_monitor.get_account()

# 获取日统计
daily_stats = trade_monitor.get_daily_stats()

# 获取持仓汇总
position_summary = trade_monitor.get_position_summary()
```

### 4. 告警引擎 (AlertEngine)

管理告警事件、优先级队列、去重和多通道通知。

```python
from vnpy_china_monitor.alert import AlertEngine, AlertPriority, AlertSeverity

# 创建告警引擎
alert_engine = AlertEngine(main_engine, event_engine)

# 发送告警
alert_id = alert_engine.send_alert(
    title="测试告警",
    message="这是一条测试告警",
    severity=AlertSeverity.INFO,
    priority=AlertPriority.NORMAL,
    source="system",
)

# 确认告警
alert_engine.acknowledge_alert(alert_id, "user")

# 获取活跃告警
active_alerts = alert_engine.get_active_alerts()

# 获取告警历史
history = alert_engine.get_alert_history(limit=100)

# 获取统计
stats = alert_engine.get_stats()
```

### 5. 通知通道

#### UI通道
```python
from vnpy_china_monitor.alert.channels import UIChannel

channel = UIChannel(enabled=True, popup_duration=10)
channel.set_message_callback(callback)
alert_engine.register_channel(channel)
```

#### 邮件通道
```python
from vnpy_china_monitor.alert.channels import EmailChannel

channel = EmailChannel(
    enabled=True,
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_user="user@example.com",
    smtp_password="password",
    email_to=["receiver@example.com"],
)
channel.test_connection()
alert_engine.register_channel(channel)
```

#### 微信通道
```python
from vnpy_china_monitor.alert.channels import WechatChannel

channel = WechatChannel(
    enabled=True,
    webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
)
alert_engine.register_channel(channel)
```

### 6. 风控桥接

```python
from vnpy_china_monitor.alert.rules import RiskAlertBridge
from vnpy_china_rules.risk import AStockRiskManager

# 创建风控桥接器
risk_bridge = RiskAlertBridge(
    alert_engine=alert_engine,
    risk_manager=risk_manager,
    check_interval=60,
)

# 启动
risk_bridge.start()

# 停止
risk_bridge.stop()
```

## 配置项

### 监控设置 (MonitorSettings)

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| qmt_check_interval | 30 | QMT连接检查间隔(秒) |
| system_check_interval | 60 | 系统检查间隔(秒) |
| memory_warning_threshold | 0.80 | 内存警告阈值 |
| memory_critical_threshold | 0.90 | 内存严重阈值 |
| cpu_warning_threshold | 0.80 | CPU警告阈值 |
| cpu_critical_threshold | 0.90 | CPU严重阈值 |
| disk_warning_threshold | 0.85 | 磁盘警告阈值 |
| disk_critical_threshold | 0.95 | 磁盘严重阈值 |

### 去重设置 (DedupeSettings)

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| window_seconds | 300 | 去重时间窗口（5分钟） |
| cooldown_seconds | 600 | 冷却时间（10分钟） |
| max_same_alerts | 3 | 相同告警最大次数 |

## 使用示例

### 基础使用

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

### 与风控集成

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

## 事件定义

| 事件类型 | 说明 | 数据格式 |
|---------|------|----------|
| EVENT_MONITOR_DATA | 监控数据更新 | `{monitor_type, name, value, status, timestamp}` |
| EVENT_ALERT_SENT | 告警发送 | `{alert_id, title, severity, timestamp}` |
| EVENT_ALERT_ACKNOWLEDGED | 告警确认 | `{alert_id, acknowledged_by, timestamp}` |
| EVENT_RISK_ALERT | 风控告警 | `{rule_name, rule_type, message, severity}` |

## 依赖

### 内部依赖
- `vnpy.event` - 事件引擎
- `vnpy.trader.engine` - 交易引擎
- `vnpy_china_rules.risk` - A股风控模块

### 外部依赖
- `psutil` - 系统监控 >=5.9.0
- `requests` - HTTP请求 >=2.28.0

## 测试

运行测试：
```bash
# 运行所有测试
pytest vnpy_china_monitor/tests/ -v

# 只运行监控测试
pytest vnpy_china_monitor/tests/test_monitor.py -v

# 只运行告警测试
pytest vnpy_china_monitor/tests/test_alert.py -v

# 只运行集成测试
pytest vnpy_china_monitor/tests/test_integration.py -v
```

## 开发计划

### Phase 1: 基础框架搭建 (已完成)
- [x] 模块目录结构创建
- [x] __init__.py 和基础类
- [x] 事件定义
- [x] 配置项定义

### Phase 2: 监控引擎 (已完成)
- [x] MonitorEngine 实现
- [x] SystemMonitor 实现
- [x] TradeMonitor 实现

### Phase 3: 告警引擎 (已完成)
- [x] AlertEngine 核心
- [x] AlertDeduplicator
- [x] AlertPriorityQueue
- [x] 通知通道基类
- [x] UI通道实现

### Phase 4: 风控集成 (已完成)
- [x] RiskAlertBridge
- [x] RiskConnector

### Phase 5: 高级功能 (开发中)
- [x] 邮件通道
- [x] 微信通道

### Phase 6: 测试与文档 (进行中)
- [x] 单元测试
- [ ] 集成测试
- [ ] 文档完善

## 变更记录

### 2026-02-24
- ✨ 创建 vnpy_china_monitor 模块
- 📊 实现监控引擎 (MonitorEngine)
- 📊 实现系统监控器 (SystemMonitor)
- 📊 实现交易监控器 (TradeMonitor)
- 📊 实现告警引擎 (AlertEngine)
- 📊 实现告警去重器 (AlertDeduplicator)
- 📊 实现优先级队列 (AlertPriorityQueue)
- 📊 实现通知通道 (UI/Email/Wechat)
- 📊 实现风控桥接 (RiskAlertBridge)
- 📊 实现风控连接器 (RiskConnector)
- ✅ 完成单元测试

---


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Feb 25, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #6750 | 6:07 AM | 🔵 | REQ-012 web monitor module (vnpy_china_monitor) implementation discovered in req012-web-monitor worktree | ~422 |
| #6749 | " | 🔵 | vnpy_china_monitor module implemented in req012-web-monitor worktree with monitoring and alerting capabilities | ~389 |
</claude-mem-context>