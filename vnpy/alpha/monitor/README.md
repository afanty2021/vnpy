# VeighNa Alpha Monitor - 性能监控系统

## 概述

性能监控系统提供了完整的模型性能追踪、预警规则和通知功能，帮助量化交易者实时监控模型表现。

## 核心功能

### 1. 性能指标追踪

追踪模型的关键性能指标，包括：
- **收益指标**：总收益率、平均收益率、超额收益等
- **风险指标**：最大回撤、下行风险等
- **效率指标**：夏普比率、信息比率等
- **预测指标**：IC (相关系数)、Rank IC 等

### 2. 预警规则系统

内置7种预设预警规则：
- 低夏普比率警告 (< 1.0)
- 极低夏普比率警告 (< 0.5)
- 高回撤警告 (< -5%)
- 严重回撤警告 (< -10%)
- 紧急回撤警告 (< -15%)
- IC值下降警告 (< 0.05)
- 负超额收益警告

### 3. 多渠道通知

支持多种通知渠道：
- **日志通知**：记录到系统日志
- **邮件通知**：通过 SMTP 发送邮件
- **Webhook通知**：HTTP POST 到指定 URL

## 快速开始

### 基础用法

```python
from vnpy.alpha import AlphaLab
from vnpy.alpha.monitor import DEFAULT_ALERT_RULES
import numpy as np

# 创建 AlphaLab 实例
lab = AlphaLab("./my_lab")

# 准备回测结果
backtest_result = {
    "returns": np.random.randn(100) * 0.01,  # 收益率序列
    "predictions": np.random.randn(100),      # 预测值
    "targets": np.random.randn(100),          # 目标值
    "trading_stats": {
        "total_trades": 50,
        "winning_trades": 30,
        "losing_trades": 20,
    }
}

# 运行回测并追踪性能
alerts = lab.run_backtest_with_tracking(
    model_name="my_model",
    backtest_result=backtest_result,
)

print(f"触发了 {len(alerts)} 个预警")
for alert in alerts:
    print(f"[{alert.level}] {alert.message}")
```

### 获取性能报告

```python
# 生成最近30天的性能报告
report = lab.generate_performance_report(
    model_name="my_model",
    days=30,
)

print(f"模型名称: {report['model_name']}")
print(f"快照数量: {report['snapshots_count']}")
print(f"总预警数: {report['alerts']['total_count']}")
print(f"活跃预警: {report['alerts']['active_count']}")
```

### 查看活跃预警

```python
# 获取未确认的预警
active_alerts = lab.get_active_alerts("my_model")

for alert in active_alerts:
    print(f"[{alert.level}] {alert.metric_name}: {alert.current_value}")

# 确认预警
lab.acknowledge_alert("my_model", alert_id=0, user="trader")
```

## 高级用法

### 自定义预警规则

```python
from vnpy.alpha.monitor import create_threshold_rule, AlertLevel

# 创建自定义规则
custom_rules = [
    create_threshold_rule(
        name="极高收益率",
        metric_name="total_return",
        category="return",
        level=AlertLevel.INFO,
        operator_str=">",
        threshold=0.2,
        higher_is_better=True,
    ),
    create_threshold_rule(
        name="超低回撤",
        metric_name="max_drawdown",
        category="risk",
        level=AlertLevel.CRITICAL,
        operator_str="<",
        threshold=-0.08,
        higher_is_better=False,
    ),
]

# 使用自定义规则
alerts = lab.run_backtest_with_tracking(
    model_name="my_model",
    backtest_result=backtest_result,
    alert_rules=custom_rules,
)
```

### 配置邮件通知

```python
from vnpy.alpha.monitor import (
    PerformanceTracker,
    EmailNotifier,
    EmailNotifierConfig,
)

# 配置邮件通知
email_config = EmailNotifierConfig(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your_email@gmail.com",
    password="your_password",
    from_addr="your_email@gmail.com",
    to_addrs=["trader@example.com"],
)

email_notifier = EmailNotifier(email_config)

# 添加到追踪器
tracker = lab.get_performance_tracker("my_model")
tracker.add_notifier_channel(email_notifier)
```

### 配置 Webhook 通知

```python
from vnpy.alpha.monitor import (
    WebhookNotifier,
    WebhookNotifierConfig,
)

webhook_config = WebhookNotifierConfig(
    url="https://your-webhook-url.com/alerts",
    headers={"Authorization": "Bearer your_token"},
)

webhook_notifier = WebhookNotifier(webhook_config)

tracker = lab.get_performance_tracker("my_model")
tracker.add_notifier_channel(webhook_notifier)
```

## 文件结构

```
lab_path/
└── performance/          # 性能数据存储目录
    ├── model1_history.json    # 模型1的历史快照
    ├── model2_history.json    # 模型2的历史快照
    └── ...
```

## API 参考

### AlphaLab 方法

- `get_performance_tracker(model_name)` - 获取模型性能追踪器
- `run_backtest_with_tracking(model_name, backtest_result, alert_rules)` - 运行回测并追踪
- `get_model_performance(model_name, limit)` - 获取历史性能数据
- `get_active_alerts(model_name)` - 获取活跃预警
- `acknowledge_alert(model_name, alert_id, user)` - 确认预警
- `generate_performance_report(model_name, days)` - 生成性能报告

### 回测结果格式

```python
backtest_result = {
    # 可选：收益率序列
    "returns": np.array([...]),

    # 可选：预测和目标值（用于计算IC）
    "predictions": np.array([...]),
    "targets": np.array([...]),

    # 可选：交易统计数据
    "trading_stats": {
        "total_trades": 100,
        "long_trades": 60,
        "short_trades": 40,
        "winning_trades": 55,
        "losing_trades": 45,
        "avg_return": 0.01,
        "avg_hold_time": 5.0,
        "turnover_rate": 0.1,
    },

    # 可选：其他预计算的指标
    "metrics": {
        "sharpe_ratio": 1.5,
        "max_drawdown": -0.05,
    },

    # 可选：元数据
    "metadata": {
        "strategy_version": "1.0",
        "backtest_date": "2026-02-28",
    },
}
```

## 测试

运行功能验证测试：

```bash
python test_monitor_final.py
```

## 注意事项

1. **数据持久化**：性能数据自动保存到 `{lab_path}/performance/` 目录
2. **冷却时间**：同一规则在冷却时间内不会重复触发
3. **预警确认**：确认后的预警不再显示为活跃状态
4. **通知失败**：通知失败不会影响性能数据的记录
