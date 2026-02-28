"""
VeighNa Alpha Monitor - Performance Tracker

性能追踪器，负责记录模型性能、检查预警并保存历史数据。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
import json
import logging

from .metrics import (
    MetricCategory,
    PerformanceMetric,
    ModelPerformanceSnapshot,
    TradingStatistics,
    calculate_performance_metrics,
    calculate_max_drawdown,
)
from .alert import Alert, AlertLevel, AlertRule, DEFAULT_ALERT_RULES
from .notifier import AlertNotifier, LogNotifier


logger = logging.getLogger(__name__)


@dataclass
class TrackerConfig:
    """
    追踪器配置

    Attributes:
        storage_path: 存储路径
        max_history_size: 最大历史记录数
        rolling_window: 滚动统计窗口大小
        enable_auto_save: 是否自动保存
        auto_save_interval: 自动保存间隔（秒）
    """

    storage_path: str = "performance"
    max_history_size: int = 1000
    rolling_window: int = 20
    enable_auto_save: bool = True
    auto_save_interval: int = 300  # 5分钟


class PerformanceTracker:
    """
    性能追踪器

    记录模型性能指标，检查预警规则，保存历史数据。

    Usage:
        tracker = PerformanceTracker("my_model", "/path/to/lab")
        tracker.record_performance(snapshot, alert_rules)
    """

    def __init__(
        self,
        model_name: str,
        lab_path: str,
        config: Optional[TrackerConfig] = None,
    ) -> None:
        """
        初始化追踪器

        Args:
            model_name: 模型名称
            lab_path: AlphaLab路径
            config: 追踪器配置
        """
        self.model_name = model_name
        self.lab_path = Path(lab_path)
        self.config = config or TrackerConfig()

        # 存储路径
        self.storage_dir = self.lab_path / self.config.storage_path
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 历史数据
        self._history: list[ModelPerformanceSnapshot] = []
        self._alerts: list[Alert] = []
        self._alert_history: dict[str, datetime] = {}  # 规则名称 -> 最后触发时间

        # 通知系统
        self._notifier = AlertNotifier()
        self._notifier.add_channel(LogNotifier())

        # 加载历史数据
        self._load_history()

    def _get_history_file(self) -> Path:
        """获取历史数据文件路径"""
        return self.storage_dir / f"{self.model_name}_history.json"

    def _get_alerts_file(self) -> Path:
        """获取预警历史文件路径"""
        return self.storage_dir / f"{self.model_name}_alerts.json"

    def _load_history(self) -> None:
        """加载历史数据"""
        history_file = self._get_history_file()

        if not history_file.exists():
            return

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for snapshot_data in data[-self.config.max_history_size :]:
                try:
                    snapshot = self._deserialize_snapshot(snapshot_data)
                    self._history.append(snapshot)
                except Exception as e:
                    logger.warning(f"Failed to load snapshot: {e}")

            logger.info(f"Loaded {len(self._history)} performance snapshots")

        except Exception as e:
            logger.error(f"Failed to load history: {e}")

    def _deserialize_snapshot(self, data: dict[str, Any]) -> ModelPerformanceSnapshot:
        """从字典反序列化快照"""
        timestamp = datetime.fromisoformat(data["timestamp"])

        # 重建指标
        return_metrics = {}
        for name, metric_data in data.get("return_metrics", {}).items():
            return_metrics[name] = PerformanceMetric(
                name=name,
                value=metric_data["value"],
                category=MetricCategory.RETURN,
                timestamp=timestamp,
                baseline=metric_data.get("baseline"),
                deviation=metric_data.get("deviation"),
            )

        risk_metrics = {}
        for name, metric_data in data.get("risk_metrics", {}).items():
            risk_metrics[name] = PerformanceMetric(
                name=name,
                value=metric_data["value"],
                category=MetricCategory.RISK,
                timestamp=timestamp,
                baseline=metric_data.get("baseline"),
                deviation=metric_data.get("deviation"),
            )

        efficiency_metrics = {}
        for name, metric_data in data.get("efficiency_metrics", {}).items():
            efficiency_metrics[name] = PerformanceMetric(
                name=name,
                value=metric_data["value"],
                category=MetricCategory.EFFICIENCY,
                timestamp=timestamp,
                baseline=metric_data.get("baseline"),
                deviation=metric_data.get("deviation"),
            )

        prediction_metrics = {}
        for name, metric_data in data.get("prediction_metrics", {}).items():
            prediction_metrics[name] = PerformanceMetric(
                name=name,
                value=metric_data["value"],
                category=MetricCategory.PREDICTION,
                timestamp=timestamp,
                baseline=metric_data.get("baseline"),
                deviation=metric_data.get("deviation"),
            )

        # 重建交易统计
        trading_stats = None
        if data.get("trading_stats"):
            stats_data = data["trading_stats"]
            trading_stats = TradingStatistics(
                total_trades=stats_data.get("total_trades", 0),
                winning_trades=stats_data.get("winning_trades", 0),
                losing_trades=stats_data.get("losing_trades", 0),
            )

        return ModelPerformanceSnapshot(
            model_name=data["model_name"],
            timestamp=timestamp,
            return_metrics=return_metrics,
            risk_metrics=risk_metrics,
            efficiency_metrics=efficiency_metrics,
            prediction_metrics=prediction_metrics,
            trading_stats=trading_stats,
            metadata=data.get("metadata", {}),
        )

    def _save_snapshot(self, snapshot: ModelPerformanceSnapshot) -> None:
        """
        保存快照到文件

        Args:
            snapshot: 性能快照
        """
        if not self.config.enable_auto_save:
            return

        # 添加到历史
        self._history.append(snapshot)

        # 限制历史大小
        if len(self._history) > self.config.max_history_size:
            self._history = self._history[-self.config.max_history_size :]

        # 序列化并保存
        try:
            data = [s.to_dict() for s in self._history]

            with open(self._get_history_file(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")

    def _check_alerts(
        self,
        snapshot: ModelPerformanceSnapshot,
        rules: list[AlertRule],
    ) -> list[Alert]:
        """
        检查预警规则

        Args:
            snapshot: 性能快照
            rules: 预警规则列表

        Returns:
            触发的预警列表
        """
        alerts: list[Alert] = []
        now = datetime.now()

        # 获取所有指标
        all_metrics = snapshot.get_all_metrics()

        for rule in rules:
            # 检查冷却时间
            if rule.name in self._alert_history:
                last_trigger = self._alert_history[rule.name]
                if (now - last_trigger).total_seconds() < rule.cooldown_seconds:
                    continue

            # 检查指标
            if rule.metric_name not in all_metrics:
                continue

            metric = all_metrics[rule.metric_name]

            if rule.evaluate(metric.value):
                # 创建预警
                alert = Alert(
                    rule_name=rule.name,
                    metric_name=rule.metric_name,
                    level=rule.level,
                    current_value=metric.value,
                    threshold=rule.threshold,
                    message=f"{rule.name}: {rule.metric_name} = {metric.value:.4f}, 阈值: {rule.threshold}",
                    timestamp=now,
                    model_name=self.model_name,
                )

                alerts.append(alert)
                self._alert_history[rule.name] = now

        return alerts

    def record_performance(
        self,
        snapshot: ModelPerformanceSnapshot,
        alert_rules: Optional[list[AlertRule]] = None,
    ) -> list[Alert]:
        """
        记录性能快照并检查预警

        Args:
            snapshot: 性能快照
            alert_rules: 预警规则列表（默认使用DEFAULT_ALERT_RULES）

        Returns:
            触发的预警列表
        """
        rules = alert_rules or DEFAULT_ALERT_RULES

        # 检查预警
        triggered_alerts = self._check_alerts(snapshot, rules)

        # 保存快照
        self._save_snapshot(snapshot)

        # 保存预警
        self._alerts.extend(triggered_alerts)

        # 发送通知
        for alert in triggered_alerts:
            self._notifier.notify(alert)

        logger.info(
            f"Recorded performance snapshot for {self.model_name}, "
            f"triggered {len(triggered_alerts)} alerts"
        )

        return triggered_alerts

    def get_performance_history(
        self,
        limit: Optional[int] = None,
    ) -> list[ModelPerformanceSnapshot]:
        """
        获取历史性能数据

        Args:
            limit: 返回记录数限制

        Returns:
            历史快照列表
        """
        if limit is None:
            return self._history.copy()
        return self._history[-limit:]

    def get_rolling_statistics(
        self,
        metric_name: str,
        window: Optional[int] = None,
) -> dict[str, float]:
        """
        计算滚动统计

        Args:
            metric_name: 指标名称
            window: 窗口大小（默认使用配置值）

        Returns:
            包含mean、std、min、max的字典
        """
        window = window or self.config.rolling_window

        # 获取历史值
        values: list[float] = []
        for snapshot in self._history:
            metric = snapshot.get_metric(metric_name)
            if metric is not None:
                values.append(metric.value)

        if len(values) < 2:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        import numpy as np

        values_array = np.array(values[-window:])
        return {
            "mean": float(np.mean(values_array)),
            "std": float(np.std(values_array)),
            "min": float(np.min(values_array)),
            "max": float(np.max(values_array)),
        }

    def acknowledge_alert(
        self,
        alert_id: int,
        user: str = "system",
    ) -> bool:
        """
        确认预警

        Args:
            alert_id: 预警索引
            user: 确认人

        Returns:
            是否成功确认
        """
        if 0 <= alert_id < len(self._alerts):
            self._alerts[alert_id].acknowledge(user)
            return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        """
        获取活跃（未确认）预警

        Returns:
            未确认的预警列表
        """
        return [alert for alert in self._alerts if alert.is_active()]

    def generate_performance_report(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        生成性能报告

        Args:
            days: 报告天数

        Returns:
            包含性能摘要的字典
        """
        cutoff_time = datetime.now() - timedelta(days=days)

        # 筛选时间范围内的快照
        recent_snapshots = [
            s for s in self._history if s.timestamp >= cutoff_time
        ]

        if not recent_snapshots:
            return {
                "model_name": self.model_name,
                "period_days": days,
                "snapshots_count": 0,
                "message": "No data available for the specified period",
            }

        # 统计信息
        latest = recent_snapshots[-1]

        # 汇总指标
        summary: dict[str, Any] = {
            "model_name": self.model_name,
            "period_days": days,
            "snapshots_count": len(recent_snapshots),
            "latest_timestamp": latest.timestamp.isoformat(),
            "metrics": {},
        }

        # 计算各指标的统计
        for metric_name in latest.get_all_metrics().keys():
            stats = self.get_rolling_statistics(metric_name, window=len(recent_snapshots))
            summary["metrics"][metric_name] = stats

        # 预警统计
        active_alerts = self.get_active_alerts()
        summary["alerts"] = {
            "total_count": len(self._alerts),
            "active_count": len(active_alerts),
            "by_level": {
                "info": len([a for a in self._alerts if a.level == AlertLevel.INFO]),
                "warning": len([a for a in self._alerts if a.level == AlertLevel.WARNING]),
                "critical": len([a for a in self._alerts if a.level == AlertLevel.CRITICAL]),
                "emergency": len([a for a in self._alerts if a.level == AlertLevel.EMERGENCY]),
            },
        }

        return summary

    def add_notifier_channel(self, channel: Any) -> None:
        """
        添加通知渠道

        Args:
            channel: 通知渠道对象
        """
        self._notifier.add_channel(channel)

    def get_metric_baseline(
        self,
        metric_name: str,
        percentile: float = 50.0,
) -> Optional[float]:
        """
        获取指标基准值（历史百分位数）

        Args:
            metric_name: 指标名称
            percentile: 百分位数 (0-100)

        Returns:
            基准值，无数据时返回None
        """
        values: list[float] = []
        for snapshot in self._history:
            metric = snapshot.get_metric(metric_name)
            if metric is not None:
                values.append(metric.value)

        if not values:
            return None

        import numpy as np

        return float(np.percentile(values, percentile))
