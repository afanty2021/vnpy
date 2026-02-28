#!/usr/bin/env python3
"""
VeighNa Alpha Monitor - 独立演示脚本

直接使用 PerformanceTracker 演示功能，不依赖 AlphaLab。
"""

import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np
import importlib.util


def import_monitor_modules():
    """直接导入监控模块"""
    monitor_path = Path(__file__).parent.parent / "vnpy" / "alpha" / "monitor"

    def import_module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    # 按依赖顺序导入，并先设置 sys.modules 以支持相对导入
    # 1. 先导入 alert（notifier 依赖它）
    alert_mod = import_module("vnpy.alpha.monitor.alert", monitor_path / "alert.py")
    sys.modules["vnpy.alpha.monitor.alert"] = alert_mod

    # 2. 导入 metrics
    metrics_mod = import_module("vnpy.alpha.monitor.metrics", monitor_path / "metrics.py")
    sys.modules["vnpy.alpha.monitor.metrics"] = metrics_mod

    # 3. 导入 notifier（依赖 alert）
    notifier_mod = import_module("vnpy.alpha.monitor.notifier", monitor_path / "notifier.py")
    sys.modules["vnpy.alpha.monitor.notifier"] = notifier_mod

    # 4. 导入 tracker（依赖 alert, metrics, notifier）
    tracker_mod = import_module("vnpy.alpha.monitor.tracker", monitor_path / "tracker.py")
    sys.modules["vnpy.alpha.monitor.tracker"] = tracker_mod

    # 设置完整的包结构
    sys.modules["vnpy.alpha.monitor"] = type(sys)("vnpy.alpha.monitor")
    for mod_name, mod_obj in [
        ("alert", alert_mod),
        ("metrics", metrics_mod),
        ("notifier", notifier_mod),
        ("tracker", tracker_mod),
    ]:
        setattr(sys.modules["vnpy.alpha.monitor"], mod_name, mod_obj)
        sys.modules[f"vnpy.alpha.monitor.{mod_name}"] = mod_obj

    return metrics_mod, alert_mod, notifier_mod, tracker_mod


def main():
    """主演示函数"""
    print("=" * 70)
    print("VeighNa Alpha Monitor - 性能监控演示（独立版本）")
    print("=" * 70)

    # 导入模块
    metrics, alert, notifier, tracker_mod = import_monitor_modules()

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    lab_path = Path(temp_dir)
    print(f"\n使用临时目录: {lab_path}")

    try:
        # 创建追踪器
        tracker = tracker_mod.PerformanceTracker(
            model_name="demo_model",
            lab_path=str(lab_path),
        )
        print("性能追踪器创建成功")

        # 模拟回测结果 - 良好表现
        print("\n" + "-" * 70)
        print("模拟回测 1：良好表现")
        print("-" * 70)

        good_returns = np.array([
            0.015, 0.022, -0.008, 0.018, 0.025,
            0.012, -0.005, 0.028, 0.019, 0.014,
        ])

        good_snapshot = metrics.ModelPerformanceSnapshot(
            model_name="demo_model",
            timestamp=datetime.now(),
            return_metrics={
                "total_return": metrics.PerformanceMetric(
                    name="total_return",
                    value=float(np.sum(good_returns)),
                    category=metrics.MetricCategory.RETURN,
                )
            },
            efficiency_metrics={
                "sharpe_ratio": metrics.PerformanceMetric(
                    name="sharpe_ratio",
                    value=1.8,
                    category=metrics.MetricCategory.EFFICIENCY,
                )
            },
            risk_metrics={
                "max_drawdown": metrics.PerformanceMetric(
                    name="max_drawdown",
                    value=-0.03,
                    category=metrics.MetricCategory.RISK,
                )
            },
        )

        alerts1 = tracker.record_performance(good_snapshot)
        print(f"回测完成，触发 {len(alerts1)} 个预警")

        # 模拟回测结果 - 表现较差
        print("\n" + "-" * 70)
        print("模拟回测 2：表现较差（触发预警）")
        print("-" * 70)

        poor_returns = np.array([
            -0.02, -0.015, 0.005, -0.025, -0.018,
            0.008, -0.022, 0.012, -0.028, -0.035,
        ])

        poor_snapshot = metrics.ModelPerformanceSnapshot(
            model_name="demo_model",
            timestamp=datetime.now(),
            return_metrics={
                "total_return": metrics.PerformanceMetric(
                    name="total_return",
                    value=float(np.sum(poor_returns)),
                    category=metrics.MetricCategory.RETURN,
                )
            },
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
                    value=-0.18,
                    category=metrics.MetricCategory.RISK,
                )
            },
            prediction_metrics={
                "ic": metrics.PerformanceMetric(
                    name="ic",
                    value=0.02,
                    category=metrics.MetricCategory.PREDICTION,
                )
            },
        )

        alerts2 = tracker.record_performance(poor_snapshot)
        print(f"回测完成，触发 {len(alerts2)} 个预警")
        for a in alerts2:
            print(f"  [{a.level.value.upper()}] {a.message}")

        # 查看性能报告
        print("\n" + "-" * 70)
        print("性能报告")
        print("-" * 70)

        report = tracker.generate_performance_report(days=30)
        print(f"快照数: {report['snapshots_count']}")
        print(f"总预警: {report['alerts']['total_count']}")
        print(f"活跃预警: {report['alerts']['active_count']}")
        print(f"  - INFO: {report['alerts']['by_level']['info']}")
        print(f"  - WARNING: {report['alerts']['by_level']['warning']}")
        print(f"  - CRITICAL: {report['alerts']['by_level']['critical']}")
        print(f"  - EMERGENCY: {report['alerts']['by_level']['emergency']}")

        # 查看活跃预警
        print("\n" + "-" * 70)
        print("活跃预警")
        print("-" * 70)

        active_alerts = tracker.get_active_alerts()
        for a in active_alerts:
            print(f"  [{a.level.value.upper()}] {a.metric_name}: {a.current_value:.4f} (阈值: {a.threshold})")

        # 确认预警
        if active_alerts:
            tracker.acknowledge_alert(0, "demo_user")
            tracker.acknowledge_alert(1, "demo_user")
            print(f"\n已确认 2 个预警")

        # 最终状态
        print("\n" + "-" * 70)
        print("最终状态")
        print("-" * 70)

        final_active = tracker.get_active_alerts()
        print(f"剩余活跃预警: {len(final_active)}")

        # 历史数据
        history = tracker.get_performance_history()
        print(f"历史快照数: {len(history)}")

        print("\n" + "=" * 70)
        print("演示完成！")
        print("=" * 70)
        print("\n功能验证:")
        print("  性能指标记录")
        print("  预警规则触发")
        print("  性能报告生成")
        print("  预警确认功能")
        print("  历史数据持久化")

    finally:
        # 清理
        shutil.rmtree(lab_path, ignore_errors=True)
        print(f"\n已清理临时目录")


if __name__ == "__main__":
    main()
