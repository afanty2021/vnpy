"""
VeighNa Alpha Monitor - Unit Tests

测试性能监控和预警系统的所有组件。
"""

import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import numpy as np

from vnpy.alpha.monitor.metrics import (
    MetricCategory,
    PerformanceMetric,
    ModelPerformanceSnapshot,
    TradingStatistics,
    calculate_performance_metrics,
    calculate_max_drawdown,
)
from vnpy.alpha.monitor.alert import (
    AlertLevel,
    AlertRule,
    Alert,
    DEFAULT_ALERT_RULES,
    create_threshold_rule,
    check_alerts,
)
from vnpy.alpha.monitor.tracker import (
    PerformanceTracker,
    TrackerConfig,
)
from vnpy.alpha.monitor.notifier import (
    LogNotifier,
    LogNotifierConfig,
    EmailNotifier,
    EmailNotifierConfig,
    WebhookNotifier,
    WebhookNotifierConfig,
    AlertNotifier,
)


class TestPerformanceMetric:
    """测试PerformanceMetric"""

    def test_create_metric(self) -> None:
        """测试创建指标"""
        metric = PerformanceMetric(
            name="test_metric",
            value=1.5,
            category=MetricCategory.RETURN,
        )
        assert metric.name == "test_metric"
        assert metric.value == 1.5
        assert metric.category == MetricCategory.RETURN
        assert metric.baseline is None
        assert metric.deviation is None

    def test_metric_with_baseline(self) -> None:
        """测试带基准的指标"""
        metric = PerformanceMetric(
            name="sharpe_ratio",
            value=1.2,
            category=MetricCategory.EFFICIENCY,
            baseline=1.0,
        )
        assert metric.baseline == 1.0
        assert metric.deviation == 0.2

    def test_is_better_than_baseline(self) -> None:
        """测试与基准比较"""
        # 高值更好
        metric_high = PerformanceMetric(
            name="return",
            value=0.15,
            category=MetricCategory.RETURN,
            baseline=0.10,
        )
        assert metric_high.is_better_than_baseline(higher_is_better=True) is True

        # 低值更好
        metric_low = PerformanceMetric(
            name="drawdown",
            value=-0.05,
            category=MetricCategory.RISK,
            baseline=-0.10,
        )
        assert metric_low.is_better_than_baseline(higher_is_better=False) is True

        # 无基准
        metric_no_baseline = PerformanceMetric(
            name="test",
            value=1.0,
            category=MetricCategory.RETURN,
        )
        assert metric_no_baseline.is_better_than_baseline() is None

    def test_deviation_pct(self) -> None:
        """测试偏差百分比"""
        metric = PerformanceMetric(
            name="test",
            value=12.0,
            category=MetricCategory.RETURN,
            baseline=10.0,
        )
        assert metric.deviation_pct() == 20.0

    def test_deviation_pct_zero_baseline(self) -> None:
        """测试基准为0时的偏差百分比"""
        metric = PerformanceMetric(
            name="test",
            value=1.0,
            category=MetricCategory.RETURN,
            baseline=0.0,
        )
        assert metric.deviation_pct() is None


class TestTradingStatistics:
    """测试TradingStatistics"""

    def test_win_rate(self) -> None:
        """测试胜率计算"""
        stats = TradingStatistics(
            total_trades=100,
            winning_trades=55,
            losing_trades=45,
        )
        assert stats.win_rate() == 0.55

    def test_win_rate_no_trades(self) -> None:
        """测试无交易时的胜率"""
        stats = TradingStatistics()
        assert stats.win_rate() == 0.0

    def test_profit_loss_ratio(self) -> None:
        """测试盈亏比"""
        stats = TradingStatistics(
            winning_trades=60,
            losing_trades=40,
        )
        assert stats.profit_loss_ratio() == 1.5

    def test_profit_loss_ratio_no_losses(self) -> None:
        """测试无亏损时的盈亏比"""
        stats = TradingStatistics(
            winning_trades=100,
            losing_trades=0,
        )
        assert stats.profit_loss_ratio() == float("inf")


class TestModelPerformanceSnapshot:
    """测试ModelPerformanceSnapshot"""

    def test_create_snapshot(self) -> None:
        """测试创建快照"""
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
        )
        assert snapshot.model_name == "test_model"
        assert len(snapshot.return_metrics) == 0
        assert len(snapshot.risk_metrics) == 0

    def test_snapshot_with_metrics(self) -> None:
        """测试带指标的快照"""
        now = datetime.now()
        return_metric = PerformanceMetric(
            name="total_return",
            value=0.15,
            category=MetricCategory.RETURN,
        )
        risk_metric = PerformanceMetric(
            name="max_drawdown",
            value=-0.05,
            category=MetricCategory.RISK,
        )

        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=now,
            return_metrics={"total_return": return_metric},
            risk_metrics={"max_drawdown": risk_metric},
        )

        assert len(snapshot.return_metrics) == 1
        assert len(snapshot.risk_metrics) == 1

    def test_get_metric(self) -> None:
        """测试获取指标"""
        metric = PerformanceMetric(
            name="sharpe_ratio",
            value=1.5,
            category=MetricCategory.EFFICIENCY,
        )
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            efficiency_metrics={"sharpe_ratio": metric},
        )

        retrieved = snapshot.get_metric("sharpe_ratio")
        assert retrieved is not None
        assert retrieved.value == 1.5

    def test_get_metric_not_found(self) -> None:
        """测试获取不存在的指标"""
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
        )
        assert snapshot.get_metric("non_existent") is None

    def test_get_all_metrics(self) -> None:
        """测试获取所有指标"""
        return_metric = PerformanceMetric(
            name="return",
            value=0.1,
            category=MetricCategory.RETURN,
        )
        risk_metric = PerformanceMetric(
            name="drawdown",
            value=-0.05,
            category=MetricCategory.RISK,
        )

        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            return_metrics={"return": return_metric},
            risk_metrics={"drawdown": risk_metric},
        )

        all_metrics = snapshot.get_all_metrics()
        assert len(all_metrics) == 2
        assert "return" in all_metrics
        assert "drawdown" in all_metrics

    def test_to_dict(self) -> None:
        """测试转换为字典"""
        now = datetime.now()
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=now,
            metadata={"version": "1.0"},
        )

        data = snapshot.to_dict()
        assert data["model_name"] == "test_model"
        assert "timestamp" in data
        assert data["metadata"]["version"] == "1.0"


class TestCalculatePerformanceMetrics:
    """测试性能指标计算"""

    def test_empty_returns(self) -> None:
        """测试空收益率序列"""
        metrics = calculate_performance_metrics(np.array([]))
        assert len(metrics) == 0

    def test_basic_metrics(self) -> None:
        """测试基本指标计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01])
        metrics = calculate_performance_metrics(returns)

        assert "total_return" in metrics
        assert "avg_return" in metrics
        assert "std_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

    def test_max_drawdown(self) -> None:
        """测试最大回撤计算"""
        returns = np.array([0.01, 0.02, -0.05, -0.02, 0.01])
        dd = calculate_max_drawdown(returns)
        assert dd < 0  # 回撤应该是负数

    def test_prediction_metrics(self) -> None:
        """测试预测指标计算"""
        predictions = np.array([0.1, 0.2, 0.15, 0.3, 0.25])
        targets = np.array([0.12, 0.18, 0.2, 0.28, 0.22])

        metrics = calculate_performance_metrics(
            returns=np.array([0.01, 0.02, 0.01, 0.03, 0.01]),
            predictions=predictions,
            targets=targets,
        )

        assert "ic" in metrics
        assert "rank_ic" in metrics

    def test_excess_return(self) -> None:
        """测试超额收益计算"""
        returns = np.array([0.01, 0.02, 0.01])
        baseline_returns = np.array([0.005, 0.01, 0.005])

        metrics = calculate_performance_metrics(
            returns=returns,
            baseline_returns=baseline_returns,
        )

        assert "excess_return" in metrics
        assert metrics["excess_return"] > 0


class TestAlertLevel:
    """测试AlertLevel"""

    def test_priority(self) -> None:
        """测试优先级"""
        assert AlertLevel.INFO.priority() == 1
        assert AlertLevel.WARNING.priority() == 2
        assert AlertLevel.CRITICAL.priority() == 3
        assert AlertLevel.EMERGENCY.priority() == 4


class TestAlertRule:
    """测试AlertRule"""

    def test_create_rule(self) -> None:
        """测试创建规则"""
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            category="test",
            level=AlertLevel.WARNING,
            condition=lambda x: x < 1.0,
            threshold=1.0,
            comparison_operator=lambda x, y: x < y,
        )
        assert rule.name == "test_rule"
        assert rule.enabled is True

    def test_evaluate_trigger(self) -> None:
        """测试触发评估"""
        rule = AlertRule(
            name="low_sharpe",
            metric_name="sharpe_ratio",
            category="efficiency",
            level=AlertLevel.WARNING,
            condition=lambda x: x < 1.0,
            threshold=1.0,
            comparison_operator=lambda x, y: x < y,
        )
        assert rule.evaluate(0.5) is True
        assert rule.evaluate(1.5) is False

    def test_evaluate_disabled(self) -> None:
        """测试禁用规则的评估"""
        rule = AlertRule(
            name="test",
            metric_name="test",
            category="test",
            level=AlertLevel.WARNING,
            condition=lambda x: True,
            threshold=0.0,
            comparison_operator=lambda x, y: True,
            enabled=False,
        )
        assert rule.evaluate(0.0) is False

    def test_str_representation(self) -> None:
        """测试字符串表示"""
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            category="test",
            level=AlertLevel.WARNING,
            condition=lambda x: x < 1.0,
            threshold=1.0,
            comparison_operator=lambda x, y: x < y,
        )
        str_repr = str(rule)
        assert "test_rule" in str_repr
        assert "test_metric" in str_repr


class TestCreateThresholdRule:
    """测试create_threshold_rule"""

    def test_create_less_than_rule(self) -> None:
        """测试小于规则"""
        rule = create_threshold_rule(
            name="low_sharpe",
            metric_name="sharpe_ratio",
            category="efficiency",
            level=AlertLevel.WARNING,
            operator="<",
            threshold=1.0,
        )
        assert rule.evaluate(0.5) is True
        assert rule.evaluate(1.5) is False

    def test_create_greater_than_rule(self) -> None:
        """测试大于规则"""
        rule = create_threshold_rule(
            name="high_drawdown",
            metric_name="max_drawdown",
            category="risk",
            level=AlertLevel.CRITICAL,
            operator=">",
            threshold=-0.1,
        )
        assert rule.evaluate(-0.05) is True
        assert rule.evaluate(-0.15) is False

    def test_invalid_operator(self) -> None:
        """测试无效操作符"""
        with pytest.raises(ValueError):
            create_threshold_rule(
                name="test",
                metric_name="test",
                category="test",
                level=AlertLevel.WARNING,
                operator="invalid",
                threshold=0.0,
            )


class TestAlert:
    """测试Alert"""

    def test_create_alert(self) -> None:
        """测试创建预警"""
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert message",
            timestamp=datetime.now(),
        )
        assert alert.rule_name == "test_rule"
        assert alert.is_active() is True

    def test_acknowledge_alert(self) -> None:
        """测试确认预警"""
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert message",
            timestamp=datetime.now(),
        )
        alert.acknowledge("test_user")
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "test_user"
        assert alert.is_active() is False

    def test_age_seconds(self) -> None:
        """测试预警年龄"""
        timestamp = datetime.now() - timedelta(seconds=30)
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert message",
            timestamp=timestamp,
        )
        age = alert.age_seconds()
        assert 29 <= age <= 31  # 允许一些时间偏差

    def test_to_dict(self) -> None:
        """测试转换为字典"""
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert message",
            timestamp=datetime.now(),
            model_name="test_model",
        )
        data = alert.to_dict()
        assert data["rule_name"] == "test_rule"
        assert data["level"] == "warning"
        assert data["model_name"] == "test_model"


class TestCheckAlerts:
    """测试check_alerts"""

    def test_check_alerts_triggered(self) -> None:
        """测试触发预警"""
        rules = [
            create_threshold_rule(
                name="low_sharpe",
                metric_name="sharpe_ratio",
                category="efficiency",
                level=AlertLevel.WARNING,
                operator="<",
                threshold=1.0,
            )
        ]
        metrics = {"sharpe_ratio": 0.5}

        alerts = check_alerts(metrics, rules, model_name="test_model")
        assert len(alerts) == 1
        assert alerts[0].metric_name == "sharpe_ratio"

    def test_check_alerts_no_trigger(self) -> None:
        """测试不触发预警"""
        rules = [
            create_threshold_rule(
                name="low_sharpe",
                metric_name="sharpe_ratio",
                category="efficiency",
                level=AlertLevel.WARNING,
                operator="<",
                threshold=1.0,
            )
        ]
        metrics = {"sharpe_ratio": 1.5}

        alerts = check_alerts(metrics, rules)
        assert len(alerts) == 0

    def test_check_alerts_missing_metric(self) -> None:
        """测试指标不存在"""
        rules = [
            create_threshold_rule(
                name="low_sharpe",
                metric_name="sharpe_ratio",
                category="efficiency",
                level=AlertLevel.WARNING,
                operator="<",
                threshold=1.0,
            )
        ]
        metrics = {"other_metric": 0.5}

        alerts = check_alerts(metrics, rules)
        assert len(alerts) == 0


class TestPerformanceTracker:
    """测试PerformanceTracker"""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def tracker(self, temp_dir: Path) -> PerformanceTracker:
        """创建追踪器实例"""
        return PerformanceTracker(
            model_name="test_model",
            lab_path=str(temp_dir),
        )

    def test_init(self, tracker: PerformanceTracker) -> None:
        """测试初始化"""
        assert tracker.model_name == "test_model"
        assert tracker.storage_dir.exists()

    def test_record_performance(self, tracker: PerformanceTracker) -> None:
        """测试记录性能"""
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            return_metrics={
                "total_return": PerformanceMetric(
                    name="total_return",
                    value=0.15,
                    category=MetricCategory.RETURN,
                )
            },
        )

        alerts = tracker.record_performance(snapshot)
        assert len(tracker.get_performance_history()) == 1

    def test_record_with_alerts(self, tracker: PerformanceTracker) -> None:
        """测试记录并触发预警"""
        # 创建会触发预警的快照
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            efficiency_metrics={
                "sharpe_ratio": PerformanceMetric(
                    name="sharpe_ratio",
                    value=0.3,  # 低于默认阈值1.0
                    category=MetricCategory.EFFICIENCY,
                )
            },
        )

        alerts = tracker.record_performance(snapshot)
        assert len(alerts) > 0

    def test_get_performance_history_limit(self, tracker: PerformanceTracker) -> None:
        """测试获取限制数量的历史"""
        # 创建多个快照
        for i in range(5):
            snapshot = ModelPerformanceSnapshot(
                model_name="test_model",
                timestamp=datetime.now(),
                metadata={"index": i},
            )
            tracker.record_performance(snapshot)

        history = tracker.get_performance_history(limit=3)
        assert len(history) == 3

    def test_acknowledge_alert(self, tracker: PerformanceTracker) -> None:
        """测试确认预警"""
        # 创建触发预警的快照
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            risk_metrics={
                "max_drawdown": PerformanceMetric(
                    name="max_drawdown",
                    value=-0.20,  # 触发紧急预警
                    category=MetricCategory.RISK,
                )
            },
        )

        alerts = tracker.record_performance(snapshot)
        if alerts:
            alert_id = len(tracker._alerts) - 1
            result = tracker.acknowledge_alert(alert_id, "test_user")
            assert result is True
            assert tracker._alerts[alert_id].acknowledged is True

    def test_get_active_alerts(self, tracker: PerformanceTracker) -> None:
        """测试获取活跃预警"""
        # 创建触发预警的快照
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            risk_metrics={
                "max_drawdown": PerformanceMetric(
                    name="max_drawdown",
                    value=-0.20,
                    category=MetricCategory.RISK,
                )
            },
        )

        tracker.record_performance(snapshot)
        active_alerts = tracker.get_active_alerts()
        assert len(active_alerts) > 0

    def test_generate_performance_report(self, tracker: PerformanceTracker) -> None:
        """测试生成性能报告"""
        # 创建一些历史数据
        for i in range(3):
            snapshot = ModelPerformanceSnapshot(
                model_name="test_model",
                timestamp=datetime.now() - timedelta(days=i),
            )
            tracker.record_performance(snapshot)

        report = tracker.generate_performance_report(days=30)
        assert report["model_name"] == "test_model"
        assert report["snapshots_count"] == 3

    def test_get_rolling_statistics(self, tracker: PerformanceTracker) -> None:
        """测试滚动统计"""
        # 添加多个快照
        for value in [0.1, 0.15, 0.12, 0.18, 0.14]:
            snapshot = ModelPerformanceSnapshot(
                model_name="test_model",
                timestamp=datetime.now(),
                return_metrics={
                    "total_return": PerformanceMetric(
                        name="total_return",
                        value=value,
                        category=MetricCategory.RETURN,
                    )
                },
            )
            tracker.record_performance(snapshot)

        stats = tracker.get_rolling_statistics("total_return", window=3)
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    def test_save_and_load(self, temp_dir: Path) -> None:
        """测试保存和加载"""
        # 创建第一个追踪器并记录数据
        tracker1 = PerformanceTracker(
            model_name="test_model",
            lab_path=str(temp_dir),
        )
        snapshot = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            metadata={"test": "data"},
        )
        tracker1.record_performance(snapshot)

        # 创建第二个追踪器并验证数据加载
        tracker2 = PerformanceTracker(
            model_name="test_model",
            lab_path=str(temp_dir),
        )
        history = tracker2.get_performance_history()
        assert len(history) == 1
        assert history[0].metadata["test"] == "data"


class TestLogNotifier:
    """测试LogNotifier"""

    @pytest.fixture
    def log_notifier(self) -> LogNotifier:
        """创建日志通知器"""
        return LogNotifier()

    def test_notify(self, log_notifier: LogNotifier) -> None:
        """测试通知"""
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert",
            timestamp=datetime.now(),
        )
        result = log_notifier.notify(alert)
        assert result is True

    @patch("vnpy.alpha.monitor.notifier.logger")
    def test_notify_with_logger_error(self, mock_logger: Mock) -> None:
        """测试日志记录失败"""
        mock_logger.log.side_effect = Exception("Log error")
        notifier = LogNotifier()

        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert",
            timestamp=datetime.now(),
        )
        result = notifier.notify(alert)
        assert result is False


class TestEmailNotifier:
    """测试EmailNotifier"""

    def test_notify_unconfigured(self) -> None:
        """测试未配置的邮件通知"""
        config = EmailNotifierConfig()  # 空配置
        notifier = EmailNotifier(config)

        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert",
            timestamp=datetime.now(),
        )
        result = notifier.notify(alert)
        assert result is False


class TestWebhookNotifier:
    """测试WebhookNotifier"""

    def test_notify_unconfigured(self) -> None:
        """测试未配置的Webhook通知"""
        config = WebhookNotifierConfig()  # 空URL
        notifier = WebhookNotifier(config)

        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert",
            timestamp=datetime.now(),
        )
        result = notifier.notify(alert)
        assert result is False


class TestAlertNotifier:
    """测试AlertNotifier"""

    def test_add_channel(self) -> None:
        """测试添加渠道"""
        notifier = AlertNotifier()
        channel = LogNotifier()
        notifier.add_channel(channel)
        assert "log" in notifier.get_channels()

    def test_remove_channel(self) -> None:
        """测试移除渠道"""
        notifier = AlertNotifier()
        channel = LogNotifier()
        notifier.add_channel(channel)
        result = notifier.remove_channel("log")
        assert result is True
        assert "log" not in notifier.get_channels()

    def test_notify(self) -> None:
        """测试发送通知"""
        notifier = AlertNotifier()
        notifier.add_channel(LogNotifier())

        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert",
            timestamp=datetime.now(),
        )
        results = notifier.notify(alert)
        assert "log" in results
        assert results["log"] is True

    def test_notify_no_channels(self) -> None:
        """测试无渠道时的通知"""
        notifier = AlertNotifier()

        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert",
            timestamp=datetime.now(),
        )
        results = notifier.notify(alert)
        assert len(results) == 0

    def test_notify_batch(self) -> None:
        """测试批量通知"""
        notifier = AlertNotifier()
        notifier.add_channel(LogNotifier())

        alerts = [
            Alert(
                rule_name=f"test_rule_{i}",
                metric_name="test_metric",
                level=AlertLevel.WARNING,
                current_value=0.5,
                threshold=1.0,
                message=f"Test alert {i}",
                timestamp=datetime.now(),
            )
            for i in range(3)
        ]
        results = notifier.notify_batch(alerts)
        assert len(results) == 3


class TestDefaultAlertRules:
    """测试默认预警规则"""

    def test_default_rules_exist(self) -> None:
        """测试默认规则存在"""
        assert len(DEFAULT_ALERT_RULES) > 0

    def test_sharpe_ratio_rules(self) -> None:
        """测试夏普比率规则"""
        sharpe_rules = [r for r in DEFAULT_ALERT_RULES if r.metric_name == "sharpe_ratio"]
        assert len(sharpe_rules) >= 2

    def test_max_drawdown_rules(self) -> None:
        """测试最大回撤规则"""
        dd_rules = [r for r in DEFAULT_ALERT_RULES if r.metric_name == "max_drawdown"]
        assert len(dd_rules) >= 2
