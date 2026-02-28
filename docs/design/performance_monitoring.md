# 模型性能监控与预警系统设计方案

> 更新时间：2026-02-28

## Context

**问题背景**：
1. **无持续监控**：现有系统仅在回测时计算性能指标，无实盘运行时的持续监控
2. **无预警机制**：当模型性能退化时无法及时预警
3. **无历史追踪**：性能指标没有历史记录，无法分析趋势

**现有能力**：
- `BacktestingEngine.calculate_statistics()` 已实现完整指标计算
- 支持 Sharpe Ratio、最大回撤、收益回撤比等关键指标
- `AlphaLens` 集成提供 IC、Rank IC 等因子分析指标

**目标**：设计模型性能监控与预警系统，包括：
1. 性能指标采集与存储
2. 多级预警规则引擎
3. 预警通知机制
4. 性能历史分析与可视化

---

## 设计方案

### 1. 新增文件

| 文件 | 职责 |
|------|------|
| `vnpy/alpha/monitor/metrics.py` | 性能指标定义与计算 |
| `vnpy/alpha/monitor/alert.py` | 预警规则与触发器 |
| `vnpy/alpha/monitor/tracker.py` | PerformanceTracker 性能追踪器 |
| `vnpy/alpha/monitor/notifier.py` | 预警通知管理器 |

### 2. 性能指标定义

**文件**: `vnpy/alpha/monitor/metrics.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class MetricCategory(Enum):
    """指标类别"""
    RETURN = "return"           # 收益类
    RISK = "risk"               # 风险类
    EFFICIENCY = "efficiency"   # 效率类
    PREDICTION = "prediction"   # 预测类


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    category: MetricCategory
    timestamp: datetime

    # 基准对比
    baseline: float | None = None
    deviation: float | None = None  # 与基准的偏离度

    # 统计信息
    rolling_mean: float | None = None
    rolling_std: float | None = None
    percentile: float | None = None  # 历史分位数


@dataclass
class ModelPerformanceSnapshot:
    """模型性能快照"""
    model_name: str
    version_id: str
    snapshot_time: datetime

    # 收益类指标
    total_return: float = 0.0
    annual_return: float = 0.0
    daily_return: float = 0.0

    # 风险类指标
    max_drawdown: float = 0.0
    max_ddpercent: float = 0.0
    return_std: float = 0.0

    # 效率类指标
    sharpe_ratio: float = 0.0
    return_drawdown_ratio: float = 0.0
    win_rate: float = 0.0

    # 预测类指标（因子分析）
    ic_mean: float | None = None
    ic_ir: float | None = None      # IC信息比率
    rank_ic_mean: float | None = None

    # 交易统计
    total_trades: int = 0
    total_turnover: float = 0.0
    total_commission: float = 0.0

    # 元数据
    observation_days: int = 0
    metadata: dict = field(default_factory=dict)
```

### 3. 预警规则引擎

**文件**: `vnpy/alpha/monitor/alert.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class AlertLevel(Enum):
    """预警级别"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告
    CRITICAL = "critical"   # 严重
    EMERGENCY = "emergency" # 紧急


@dataclass
class AlertRule:
    """预警规则"""
    name: str
    metric_name: str
    level: AlertLevel

    # 触发条件
    condition: Callable[[float, dict], bool]  # (当前值, 上下文) -> 是否触发
    threshold: float | None = None

    # 规则配置
    lookback_days: int = 20      # 回看天数
    consecutive_count: int = 1   # 连续触发次数

    # 预警信息
    message_template: str = ""
    description: str = ""


# 预设预警规则
DEFAULT_ALERT_RULES: list[AlertRule] = [
    # Sharpe Ratio 预警
    AlertRule(
        name="sharpe_ratio_low",
        metric_name="sharpe_ratio",
        level=AlertLevel.WARNING,
        threshold=1.0,
        condition=lambda v, ctx: v < 1.0,
        message_template="Sharpe Ratio ({value:.2f}) 低于阈值 {threshold}"
    ),
    AlertRule(
        name="sharpe_ratio_critical",
        metric_name="sharpe_ratio",
        level=AlertLevel.CRITICAL,
        threshold=0.5,
        condition=lambda v, ctx: v < 0.5,
        message_template="Sharpe Ratio ({value:.2f}) 严重低于阈值 {threshold}"
    ),

    # 最大回撤预警
    AlertRule(
        name="max_drawdown_warning",
        metric_name="max_ddpercent",
        level=AlertLevel.WARNING,
        threshold=-10.0,
        condition=lambda v, ctx: v < -10.0,
        message_template="最大回撤 ({value:.2f}%) 超过预警阈值"
    ),
    AlertRule(
        name="max_drawdown_critical",
        metric_name="max_ddpercent",
        level=AlertLevel.CRITICAL,
        threshold=-20.0,
        condition=lambda v, ctx: v < -20.0,
        message_template="最大回撤 ({value:.2f}%) 超过严重阈值，请立即检查"
    ),

    # IC 预警（因子预测能力）
    AlertRule(
        name="ic_degradation",
        metric_name="ic_mean",
        level=AlertLevel.WARNING,
        threshold=0.02,
        condition=lambda v, ctx: v < 0.02,
        message_template="IC均值 ({value:.4f}) 过低，因子预测能力退化"
    ),

    # 性能退化预警（与历史对比）
    AlertRule(
        name="performance_degradation",
        metric_name="sharpe_ratio",
        level=AlertLevel.WARNING,
        condition=lambda v, ctx: v < ctx.get("rolling_mean", v) - 2 * ctx.get("rolling_std", 0),
        message_template="Sharpe Ratio 显著低于历史均值（2σ）"
    ),

    # 连续亏损预警
    AlertRule(
        name="consecutive_losses",
        metric_name="daily_return",
        level=AlertLevel.WARNING,
        consecutive_count=5,
        condition=lambda v, ctx: ctx.get("consecutive_negative_count", 0) >= 5,
        message_template="连续 {count} 个交易日亏损"
    ),
]


@dataclass
class Alert:
    """预警事件"""
    alert_id: str
    rule_name: str
    level: AlertLevel
    metric_name: str
    metric_value: float

    message: str
    triggered_at: datetime

    # 上下文信息
    model_name: str
    version_id: str
    context: dict

    # 处理状态
    acknowledged: bool = False
    resolved_at: datetime | None = None
    resolution_note: str = ""
```

### 4. 性能追踪器

**文件**: `vnpy/alpha/monitor/tracker.py`

```python
class PerformanceTracker:
    """性能追踪器"""

    def __init__(
        self,
        lab: AlphaLab,
        alert_rules: list[AlertRule] | None = None
    ):
        self.lab = lab
        self.alert_rules = alert_rules or DEFAULT_ALERT_RULES
        self.performance_path = lab.lab_path / "performance"
        self.performance_path.mkdir(exist_ok=True)

        # 内存缓存
        self._metrics_history: dict[str, list[PerformanceMetric]] = {}
        self._alerts: list[Alert] = []

    def record_performance(
        self,
        model_name: str,
        version_id: str,
        statistics: dict,
        prediction_metrics: dict | None = None
    ) -> ModelPerformanceSnapshot:
        """
        记录模型性能快照

        Parameters
        ----------
        model_name : str
            模型名称
        version_id : str
            模型版本ID
        statistics : dict
            回测统计指标（来自 BacktestingEngine.calculate_statistics()）
        prediction_metrics : dict, optional
            预测指标（IC、Rank IC等）
        """
        snapshot = ModelPerformanceSnapshot(
            model_name=model_name,
            version_id=version_id,
            snapshot_time=datetime.now(),
            # 从 statistics 映射
            total_return=statistics.get("total_return", 0),
            annual_return=statistics.get("annual_return", 0),
            sharpe_ratio=statistics.get("sharpe_ratio", 0),
            max_drawdown=statistics.get("max_drawdown", 0),
            max_ddpercent=statistics.get("max_ddpercent", 0),
            return_drawdown_ratio=statistics.get("return_drawdown_ratio", 0),
            total_trades=statistics.get("total_trade_count", 0),
            observation_days=statistics.get("total_days", 0),
        )

        # 添加预测指标
        if prediction_metrics:
            snapshot.ic_mean = prediction_metrics.get("ic_mean")
            snapshot.ic_ir = prediction_metrics.get("ic_ir")
            snapshot.rank_ic_mean = prediction_metrics.get("rank_ic_mean")

        # 保存快照
        self._save_snapshot(snapshot)

        # 检查预警规则
        self._check_alerts(snapshot)

        return snapshot

    def get_performance_history(
        self,
        model_name: str,
        metric_name: str,
        days: int = 30
    ) -> list[PerformanceMetric]:
        """获取性能指标历史"""
        ...

    def get_rolling_statistics(
        self,
        model_name: str,
        metric_name: str,
        window: int = 20
    ) -> dict:
        """计算滚动统计量"""
        ...

    def check_alerts(self, snapshot: ModelPerformanceSnapshot) -> list[Alert]:
        """检查预警规则并生成预警"""
        ...

    def acknowledge_alert(self, alert_id: str, note: str = "") -> bool:
        """确认预警"""
        ...

    def get_active_alerts(self, model_name: str | None = None) -> list[Alert]:
        """获取未处理的预警"""
        ...

    def generate_performance_report(
        self,
        model_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> dict:
        """生成性能报告"""
        ...
```

### 5. 预警通知管理器

**文件**: `vnpy/alpha/monitor/notifier.py`

```python
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    """通知渠道基类"""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送预警通知"""
        pass


class LogNotifier(NotificationChannel):
    """日志通知"""

    def send(self, alert: Alert) -> bool:
        level_map = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.CRITICAL: logger.error,
            AlertLevel.EMERGENCY: logger.critical,
        }
        log_func = level_map.get(alert.level, logger.info)
        log_func(f"[{alert.level.value.upper()}] {alert.message}")
        return True


class EmailNotifier(NotificationChannel):
    """邮件通知"""

    def __init__(self, smtp_config: dict):
        self.smtp_config = smtp_config

    def send(self, alert: Alert) -> bool:
        # 实现邮件发送
        ...


class WebhookNotifier(NotificationChannel):
    """Webhook通知（企业微信、钉钉等）"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, alert: Alert) -> bool:
        # 实现 webhook 调用
        ...


class AlertNotifier:
    """预警通知管理器"""

    def __init__(self):
        self.channels: list[NotificationChannel] = []
        self.level_filters: dict[AlertLevel, list[NotificationChannel]] = {}

    def add_channel(
        self,
        channel: NotificationChannel,
        levels: list[AlertLevel] | None = None
    ):
        """添加通知渠道"""
        self.channels.append(channel)
        if levels:
            for level in levels:
                if level not in self.level_filters:
                    self.level_filters[level] = []
                self.level_filters[level].append(channel)

    def notify(self, alert: Alert) -> dict[str, bool]:
        """发送预警通知到所有相关渠道"""
        results = {}

        # 获取该级别应通知的渠道
        channels = self.level_filters.get(alert.level, self.channels)

        for channel in channels:
            try:
                success = channel.send(alert)
                results[channel.__class__.__name__] = success
            except Exception as e:
                logger.error(f"通知发送失败: {channel.__class__.__name__}, {e}")
                results[channel.__class__.__name__] = False

        return results
```

### 6. AlphaLab 集成

**文件**: `vnpy/alpha/lab.py`（修改）

```python
from .monitor.tracker import PerformanceTracker
from .monitor.alert import AlertLevel

class AlphaLab:
    def __init__(self, lab_path: str):
        ...
        # 新增性能追踪器
        self.performance_tracker = PerformanceTracker(self)

    def run_backtest_with_tracking(
        self,
        model_name: str,
        dataset: AlphaDataset,
        strategy_class: type,
        capital: float = 1_000_000,
        track_performance: bool = True
    ) -> tuple[dict, ModelPerformanceSnapshot | None]:
        """
        运行回测并跟踪性能

        Returns
        -------
        tuple[dict, ModelPerformanceSnapshot | None]
            (回测统计结果, 性能快照)
        """
        # 运行回测
        engine = BacktestingEngine(self)
        ...
        statistics = engine.calculate_statistics()

        # 记录性能
        snapshot = None
        if track_performance:
            version = self.version_manager.get_latest_version(model_name)
            snapshot = self.performance_tracker.record_performance(
                model_name=model_name,
                version_id=version.version_id if version else "unknown",
                statistics=statistics
            )

        return statistics, snapshot

    def get_model_performance(
        self,
        model_name: str,
        days: int = 30
    ) -> dict:
        """获取模型性能历史"""
        return self.performance_tracker.get_performance_history(model_name, days)

    def get_active_alerts(
        self,
        model_name: str | None = None,
        level: AlertLevel | None = None
    ) -> list[Alert]:
        """获取未处理的预警"""
        alerts = self.performance_tracker.get_active_alerts(model_name)
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts
```

### 7. 性能数据存储格式

**文件**: `lab_path/performance/{model_name}_history.json`

```json
{
  "model_name": "my_lgb_model",
  "snapshots": [
    {
      "version_id": "v20260228_143022",
      "snapshot_time": "2026-02-28T14:30:22",
      "total_return": 15.5,
      "annual_return": 18.2,
      "sharpe_ratio": 1.85,
      "max_drawdown": -50000,
      "max_ddpercent": -5.2,
      "return_drawdown_ratio": 3.1,
      "ic_mean": 0.045,
      "observation_days": 120
    }
  ],
  "alerts": [
    {
      "alert_id": "alert_20260228_001",
      "rule_name": "sharpe_ratio_low",
      "level": "warning",
      "message": "Sharpe Ratio (0.85) 低于阈值 1.0",
      "triggered_at": "2026-02-28T15:00:00",
      "acknowledged": false
    }
  ]
}
```

### 8. 预警流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    性能监控与预警流程                              │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
    │  回测/实盘    │────▶│ PerformanceTracker│────▶│ 记录快照     │
    │  运行结果     │     │ .record_performance│    │ 到文件       │
    └──────────────┘     └──────────────────┘     └─────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  检查预警规则     │
                         │  .check_alerts() │
                         └──────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ Sharpe < 1.0│ │ 回撤 > 10% │ │ IC < 0.02  │
            │  WARNING    │ │  WARNING   │ │  WARNING   │
            └─────────────┘ └─────────────┘ └─────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
                         ┌──────────────────┐
                         │  生成 Alert 对象  │
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  AlertNotifier   │
                         │  分发通知        │
                         └──────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ LogNotifier │ │EmailNotifier│ │WebhookNotif.│
            └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 实现任务

### Phase 1: 核心组件（P0）

- [ ] 创建 `PerformanceMetric` 和 `ModelPerformanceSnapshot` 数据类
- [ ] 创建 `AlertRule` 和 `Alert` 数据类
- [ ] 定义预设预警规则 `DEFAULT_ALERT_RULES`

### Phase 2: 追踪器实现（P0）

- [ ] 实现 `PerformanceTracker.record_performance()`
- [ ] 实现 `PerformanceTracker._check_alerts()`
- [ ] 实现性能快照存储（JSON格式）

### Phase 3: 通知系统（P1）

- [ ] 实现 `LogNotifier`
- [ ] 实现 `EmailNotifier`（可选）
- [ ] 实现 `WebhookNotifier`（企业微信/钉钉）
- [ ] 实现 `AlertNotifier` 管理器

### Phase 4: AlphaLab 集成（P0）

- [ ] 添加 `PerformanceTracker` 初始化
- [ ] 添加 `run_backtest_with_tracking()` 方法
- [ ] 添加 `get_model_performance()` 方法
- [ ] 添加 `get_active_alerts()` 方法

### Phase 5: 测试验证（P0）

- [ ] 单元测试：预警规则触发逻辑
- [ ] 单元测试：性能快照存储
- [ ] 集成测试：完整监控流程

---

## 验证方案

### 1. 功能测试

```python
# 测试预警触发
lab = AlphaLab("./test_lab")

# 模拟性能数据
statistics = {
    "sharpe_ratio": 0.8,  # 低于阈值 1.0
    "max_ddpercent": -15,  # 超过预警阈值
}

snapshot = lab.performance_tracker.record_performance(
    model_name="test_model",
    version_id="v1",
    statistics=statistics
)

# 检查预警
alerts = lab.get_active_alerts()
assert len(alerts) >= 2  # Sharpe 和回撤预警
```

### 2. 通知测试

```python
# 测试通知发送
notifier = AlertNotifier()
notifier.add_channel(LogNotifier())
notifier.add_channel(WebhookNotifier(webhook_url), levels=[AlertLevel.CRITICAL])

alert = Alert(
    alert_id="test_001",
    rule_name="sharpe_ratio_critical",
    level=AlertLevel.CRITICAL,
    ...
)

results = notifier.notify(alert)
assert results.get("LogNotifier") == True
```

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `vnpy/alpha/monitor/__init__.py` | 新增 | 模块导出 |
| `vnpy/alpha/monitor/metrics.py` | 新增 | 性能指标定义 |
| `vnpy/alpha/monitor/alert.py` | 新增 | 预警规则与事件 |
| `vnpy/alpha/monitor/tracker.py` | 新增 | 性能追踪器 |
| `vnpy/alpha/monitor/notifier.py` | 新增 | 通知管理器 |
| `vnpy/alpha/lab.py` | 修改 | 集成监控功能 |
| `tests/test_monitor.py` | 新增 | 单元测试 |