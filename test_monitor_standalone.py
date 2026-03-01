"""
VeighNa Alpha Monitor - Standalone Unit Tests

独立测试脚本，不依赖完整的 vnpy.alpha 模块。
"""

import sys
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np


# 直接导入监控模块
sys.path.insert(0, str(Path(__file__).parent))

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


def test_performance_metric() -> bool:
    """测试PerformanceMetric"""
    print("Testing PerformanceMetric...")
    try:
        metric = PerformanceMetric(
            name="test_metric",
            value=1.5,
            category=MetricCategory.RETURN,
        )
        assert metric.name == "test_metric"
        assert metric.value == 1.5
        assert metric.category == MetricCategory.RETURN

        # 测试带基准
        metric2 = PerformanceMetric(
            name="sharpe_ratio",
            value=1.2,
            category=MetricCategory.EFFICIENCY,
            baseline=1.0,
        )
        assert metric2.deviation == 0.2
        assert metric2.deviation_pct() == 20.0

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_trading_statistics() -> bool:
    """测试TradingStatistics"""
    print("Testing TradingStatistics...")
    try:
        stats = TradingStatistics(
            total_trades=100,
            winning_trades=55,
            losing_trades=45,
        )
        assert stats.win_rate() == 0.55
        assert stats.profit_loss_ratio() == 1.2222222222222223
        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_model_performance_snapshot() -> bool:
    """测试ModelPerformanceSnapshot"""
    print("Testing ModelPerformanceSnapshot...")
    try:
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
        assert snapshot.get_metric("total_return") is not None

        all_metrics = snapshot.get_all_metrics()
        assert len(all_metrics) == 2

        data = snapshot.to_dict()
        assert data["model_name"] == "test_model"

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_calculate_performance_metrics() -> bool:
    """测试性能指标计算"""
    print("Testing calculate_performance_metrics...")
    try:
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01])
        metrics = calculate_performance_metrics(returns)

        assert "total_return" in metrics
        assert "avg_return" in metrics
        assert "std_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

        # 测试预测指标
        predictions = np.array([0.1, 0.2, 0.15, 0.3, 0.25])
        targets = np.array([0.12, 0.18, 0.2, 0.28, 0.22])

        metrics2 = calculate_performance_metrics(
            returns=returns,
            predictions=predictions,
            targets=targets,
        )
        assert "ic" in metrics2
        assert "rank_ic" in metrics2

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_alert_level() -> bool:
    """测试AlertLevel"""
    print("Testing AlertLevel...")
    try:
        assert AlertLevel.INFO.priority() == 1
        assert AlertLevel.WARNING.priority() == 2
        assert AlertLevel.CRITICAL.priority() == 3
        assert AlertLevel.EMERGENCY.priority() == 4
        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_alert_rule() -> bool:
    """测试AlertRule"""
    print("Testing AlertRule...")
    try:
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            category="test",
            level=AlertLevel.WARNING,
            condition=lambda x: x < 1.0,
            threshold=1.0,
            comparison_operator=lambda x, y: x < y,
        )
        assert rule.evaluate(0.5) is True
        assert rule.evaluate(1.5) is False

        # 测试禁用规则
        rule2 = AlertRule(
            name="test",
            metric_name="test",
            category="test",
            level=AlertLevel.WARNING,
            condition=lambda x: True,
            threshold=0.0,
            comparison_operator=lambda x, y: True,
            enabled=False,
        )
        assert rule2.evaluate(0.0) is False

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_create_threshold_rule() -> bool:
    """测试create_threshold_rule"""
    print("Testing create_threshold_rule...")
    try:
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

        # 测试无效操作符
        try:
            create_threshold_rule(
                name="test",
                metric_name="test",
                category="test",
                level=AlertLevel.WARNING,
                operator="invalid",
                threshold=0.0,
            )
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_alert() -> bool:
    """测试Alert"""
    print("Testing Alert...")
    try:
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert message",
            timestamp=datetime.now(),
        )
        assert alert.is_active() is True

        alert.acknowledge("test_user")
        assert alert.acknowledged is True
        assert alert.is_active() is False

        # 测试年龄
        timestamp = datetime.now() - timedelta(seconds=30)
        alert2 = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="Test alert message",
            timestamp=timestamp,
        )
        age = alert2.age_seconds()
        assert 25 <= age <= 35  # 允许一些偏差

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_check_alerts() -> bool:
    """测试check_alerts"""
    print("Testing check_alerts...")
    try:
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

        # 测试不触发
        alerts2 = check_alerts({"sharpe_ratio": 1.5}, rules)
        assert len(alerts2) == 0

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_performance_tracker() -> bool:
    """测试PerformanceTracker"""
    print("Testing PerformanceTracker...")
    try:
        temp_path = Path(tempfile.mkdtemp())
        try:
            tracker = PerformanceTracker(
                model_name="test_model",
                lab_path=str(temp_path),
            )
            assert tracker.model_name == "test_model"
            assert tracker.storage_dir.exists()

            # 测试记录性能
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

            # 测试限制数量
            for i in range(5):
                s = ModelPerformanceSnapshot(
                    model_name="test_model",
                    timestamp=datetime.now(),
                    metadata={"index": i},
                )
                tracker.record_performance(s)

            history = tracker.get_performance_history(limit=3)
            assert len(history) == 3

            # 测试报告
            report = tracker.generate_performance_report(days=30)
            assert report["model_name"] == "test_model"
            assert report["snapshots_count"] >= 1

            print("  PASSED")
            return True
        finally:
            shutil.rmtree(temp_path)
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_notifier() -> bool:
    """测试通知系统"""
    print("Testing Notifier...")
    try:
        # 测试 LogNotifier
        log_notifier = LogNotifier()
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

        # 测试 AlertNotifier
        notifier = AlertNotifier()
        notifier.add_channel(LogNotifier())
        results = notifier.notify(alert)
        assert "log" in results
        assert results["log"] is True

        # 测试批量通知
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
        batch_results = notifier.notify_batch(alerts)
        assert len(batch_results) == 3

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_default_alert_rules() -> bool:
    """测试默认预警规则"""
    print("Testing DEFAULT_ALERT_RULES...")
    try:
        assert len(DEFAULT_ALERT_RULES) > 0

        sharpe_rules = [r for r in DEFAULT_ALERT_RULES if r.metric_name == "sharpe_ratio"]
        assert len(sharpe_rules) >= 2

        dd_rules = [r for r in DEFAULT_ALERT_RULES if r.metric_name == "max_drawdown"]
        assert len(dd_rules) >= 2

        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_save_and_load() -> bool:
    """测试保存和加载"""
    print("Testing save and load...")
    try:
        temp_path = Path(tempfile.mkdtemp())
        try:
            # 创建第一个追踪器并记录数据
            tracker1 = PerformanceTracker(
                model_name="test_model",
                lab_path=str(temp_path),
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
                lab_path=str(temp_path),
            )
            history = tracker2.get_performance_history()
            assert len(history) == 1
            assert history[0].metadata["test"] == "data"

            print("  PASSED")
            return True
        finally:
            shutil.rmtree(temp_path)
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("VeighNa Alpha Monitor - Standalone Tests")
    print("=" * 60)

    tests = [
        test_performance_metric,
        test_trading_statistics,
        test_model_performance_snapshot,
        test_calculate_performance_metrics,
        test_alert_level,
        test_alert_rule,
        test_create_threshold_rule,
        test_alert,
        test_check_alerts,
        test_performance_tracker,
        test_notifier,
        test_default_alert_rules,
        test_save_and_load,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
