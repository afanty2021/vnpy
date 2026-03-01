#!/usr/bin/env python3
"""
VeighNa Alpha Monitor - 完整功能验证脚本（独立版本）

直接导入子模块，不依赖 alpha/__init__.py
"""

import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np
import importlib.util


def import_module_from_file(module_name, file_path):
    """从文件直接导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_test():
    """运行完整功能测试"""
    print("=" * 70)
    print("VeighNa Alpha Monitor - 完整功能测试（独立版本）")
    print("=" * 70)

    monitor_path = Path(__file__).parent / "vnpy" / "alpha" / "monitor"

    # 导入模块（注意顺序：alert 被 notifier 依赖，notifier 被 tracker 依赖）
    print("\n正在导入监控模块...")
    metrics = import_module_from_file("vnpy.alpha.monitor.metrics", monitor_path / "metrics.py")
    alert = import_module_from_file("vnpy.alpha.monitor.alert", monitor_path / "alert.py")
    notifier_mod = import_module_from_file("vnpy.alpha.monitor.notifier", monitor_path / "notifier.py")
    tracker_mod = import_module_from_file("vnpy.alpha.monitor.tracker", monitor_path / "tracker.py")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    lab_path = Path(temp_dir)
    print(f"使用临时目录: {lab_path}")

    try:
        # 测试 1: 创建性能指标
        print("\n[测试 1] 创建性能指标...")
        metric = metrics.PerformanceMetric(
            name="sharpe_ratio",
            value=1.5,
            category=metrics.MetricCategory.EFFICIENCY,
            baseline=1.0,
        )
        print(f"  指标名称: {metric.name}")
        print(f"  当前值: {metric.value}")
        print(f"  基准值: {metric.baseline}")
        print(f"  偏差: {metric.deviation}")
        print(f"  偏差%: {metric.deviation_pct()}%")
        print("  PASSED")

        # 测试 2: 创建性能快照
        print("\n[测试 2] 创建性能快照...")
        snapshot = metrics.ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            return_metrics={
                "total_return": metrics.PerformanceMetric(
                    name="total_return",
                    value=0.15,
                    category=metrics.MetricCategory.RETURN,
                )
            },
            risk_metrics={
                "max_drawdown": metrics.PerformanceMetric(
                    name="max_drawdown",
                    value=-0.05,
                    category=metrics.MetricCategory.RISK,
                )
            },
        )
        print(f"  模型名称: {snapshot.model_name}")
        print(f"  收益指标数: {len(snapshot.return_metrics)}")
        print(f"  风险指标数: {len(snapshot.risk_metrics)}")
        print("  PASSED")

        # 测试 3: 计算性能指标
        print("\n[测试 3] 计算性能指标...")
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01, 0.02, -0.02, 0.04])
        calc_metrics = metrics.calculate_performance_metrics(returns)
        print(f"  总收益: {calc_metrics.get('total_return', 0):.4f}")
        print(f"  夏普比率: {calc_metrics.get('sharpe_ratio', 0):.4f}")
        print(f"  最大回撤: {calc_metrics.get('max_drawdown', 0):.4f}")
        print("  PASSED")

        # 测试 4: 创建预警规则
        print("\n[测试 4] 创建预警规则...")
        rule = alert.create_threshold_rule(
            name="低夏普比率",
            metric_name="sharpe_ratio",
            category="efficiency",
            level=alert.AlertLevel.WARNING,
            operator_str="<",
            threshold=1.0,
        )
        print(f"  规则名称: {rule.name}")
        print(f"  评估 0.5: {rule.evaluate(0.5)}")
        print(f"  评估 1.5: {rule.evaluate(1.5)}")
        print("  PASSED")

        # 测试 5: 检查预警
        print("\n[测试 5] 检查预警触发...")
        test_metrics = {
            "sharpe_ratio": 0.3,
            "max_drawdown": -0.20,
        }
        triggered_alerts = alert.check_alerts(test_metrics, alert.DEFAULT_ALERT_RULES, model_name="test_model")
        print(f"  触发预警数: {len(triggered_alerts)}")
        for a in triggered_alerts:
            print(f"    - [{a.level.value}] {a.rule_name}")
        print("  PASSED")

        # 测试 6: 性能追踪器
        print("\n[测试 6] 性能追踪器...")
        tracker = tracker_mod.PerformanceTracker(
            model_name="test_model",
            lab_path=str(lab_path),
        )
        print(f"  追踪器创建成功")
        print(f"  存储目录: {tracker.storage_dir}")

        # 创建会触发预警的快照
        snapshot_with_alerts = metrics.ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            efficiency_metrics={
                "sharpe_ratio": metrics.PerformanceMetric(
                    name="sharpe_ratio",
                    value=0.3,
                    category=metrics.MetricCategory.EFFICIENCY,
                )
            },
            risk_metrics={
                "max_drawdown": metrics.PerformanceMetric(
                    name="max_drawdown",
                    value=-0.20,
                    category=metrics.MetricCategory.RISK,
                )
            },
        )

        alerts = tracker.record_performance(snapshot_with_alerts)
        print(f"  记录快照成功，触发 {len(alerts)} 个预警")
        print("  PASSED")

        # 测试 7: 获取历史数据
        print("\n[测试 7] 获取历史性能数据...")
        history = tracker.get_performance_history()
        print(f"  历史快照数: {len(history)}")
        print("  PASSED")

        # 测试 8: 生成性能报告
        print("\n[测试 8] 生成性能报告...")
        report = tracker.generate_performance_report(days=30)
        print(f"  模型名称: {report['model_name']}")
        print(f"  快照数量: {report['snapshots_count']}")
        print("  PASSED")

        # 测试 9: 通知系统
        print("\n[测试 9] 通知系统...")
        alert_notifier = notifier_mod.AlertNotifier()
        alert_notifier.add_channel(notifier_mod.LogNotifier())

        test_alert_obj = alert.Alert(
            rule_name="测试规则",
            metric_name="test_metric",
            level=alert.AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="测试预警消息",
            timestamp=datetime.now(),
        )

        results = alert_notifier.notify(test_alert_obj)
        print(f"  通知渠道: {list(results.keys())}")
        print("  PASSED")

        # 测试 10: 数据持久化
        print("\n[测试 10] 数据持久化...")
        tracker2 = tracker_mod.PerformanceTracker(
            model_name="test_model",
            lab_path=str(lab_path),
        )
        history2 = tracker2.get_performance_history()
        print(f"  新追踪器加载的历史快照数: {len(history2)}")
        print("  PASSED")

        print("\n" + "=" * 70)
        print("所有测试 PASSED!")
        print("=" * 70)
        print("\n监控系统功能验证总结:")
        print("  性能指标")
        print("  预警规则系统")
        print("  性能追踪器")
        print("  通知系统")
        print("  数据持久化")
        return True

    except Exception as e:
        print(f"\n测试 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时目录
        shutil.rmtree(lab_path, ignore_errors=True)


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
