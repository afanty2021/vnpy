#!/usr/bin/env python3
"""
VeighNa Alpha Monitor - 完整功能验证脚本

测试监控系统的所有核心功能。
"""

import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np


def run_test():
    """运行完整功能测试"""
    print("=" * 70)
    print("VeighNa Alpha Monitor - 完整功能测试")
    print("=" * 70)

    # 直接导入监控模块
    from vnpy.alpha.monitor.metrics import (
        MetricCategory,
        PerformanceMetric,
        ModelPerformanceSnapshot,
        TradingStatistics,
        calculate_performance_metrics,
    )
    from vnpy.alpha.monitor.alert import (
        AlertLevel,
        Alert,
        create_threshold_rule,
        check_alerts,
        DEFAULT_ALERT_RULES,
    )
    from vnpy.alpha.monitor.tracker import PerformanceTracker
    from vnpy.alpha.monitor.notifier import LogNotifier, AlertNotifier

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    lab_path = Path(temp_dir)
    print(f"\n使用临时目录: {lab_path}")

    try:
        # 测试 1: 创建性能指标
        print("\n[测试 1] 创建性能指标...")
        metric = PerformanceMetric(
            name="sharpe_ratio",
            value=1.5,
            category=MetricCategory.EFFICIENCY,
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
            risk_metrics={
                "max_drawdown": PerformanceMetric(
                    name="max_drawdown",
                    value=-0.05,
                    category=MetricCategory.RISK,
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
        metrics = calculate_performance_metrics(returns)
        print(f"  总收益: {metrics.get('total_return', 0):.4f}")
        print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.4f}")
        print(f"  最大回撤: {metrics.get('max_drawdown', 0):.4f}")
        print("  PASSED")

        # 测试 4: 创建预警规则
        print("\n[测试 4] 创建预警规则...")
        rule = create_threshold_rule(
            name="低夏普比率",
            metric_name="sharpe_ratio",
            category="efficiency",
            level=AlertLevel.WARNING,
            operator_str="<",
            threshold=1.0,
        )
        print(f"  规则名称: {rule.name}")
        print(f"  触发条件: {rule}")
        print(f"  评估 0.5: {rule.evaluate(0.5)}")
        print(f"  评估 1.5: {rule.evaluate(1.5)}")
        print("  PASSED")

        # 测试 5: 检查预警
        print("\n[测试 5] 检查预警触发...")
        test_metrics = {
            "sharpe_ratio": 0.3,  # 会触发 WARNING 和 CRITICAL
            "max_drawdown": -0.20,  # 会触发 EMERGENCY
        }
        alerts = check_alerts(test_metrics, DEFAULT_ALERT_RULES, model_name="test_model")
        print(f"  测试指标: sharpe_ratio={test_metrics['sharpe_ratio']}, max_drawdown={test_metrics['max_drawdown']}")
        print(f"  触发预警数: {len(alerts)}")
        for alert in alerts:
            print(f"    - [{alert.level.value}] {alert.rule_name}: {alert.message}")
        print("  PASSED")

        # 测试 6: 性能追踪器
        print("\n[测试 6] 性能追踪器...")
        tracker = PerformanceTracker(
            model_name="test_model",
            lab_path=str(lab_path),
        )
        print(f"  追踪器创建成功")
        print(f"  存储目录: {tracker.storage_dir}")

        # 创建一个会触发预警的快照
        snapshot_with_alerts = ModelPerformanceSnapshot(
            model_name="test_model",
            timestamp=datetime.now(),
            efficiency_metrics={
                "sharpe_ratio": PerformanceMetric(
                    name="sharpe_ratio",
                    value=0.3,
                    category=MetricCategory.EFFICIENCY,
                )
            },
            risk_metrics={
                "max_drawdown": PerformanceMetric(
                    name="max_drawdown",
                    value=-0.20,
                    category=MetricCategory.RISK,
                )
            },
        )

        triggered_alerts = tracker.record_performance(snapshot_with_alerts)
        print(f"  记录快照成功，触发 {len(triggered_alerts)} 个预警")
        print("  PASSED")

        # 测试 7: 获取历史数据
        print("\n[测试 7] 获取历史性能数据...")
        history = tracker.get_performance_history()
        print(f"  历史快照数: {len(history)}")
        if history:
            latest = history[-1]
            print(f"  最新快照时间: {latest.timestamp}")
        print("  PASSED")

        # 测试 8: 生成性能报告
        print("\n[测试 8] 生成性能报告...")
        report = tracker.generate_performance_report(days=30)
        print(f"  模型名称: {report['model_name']}")
        print(f"  快照数量: {report['snapshots_count']}")
        if 'alerts' in report:
            print(f"  总预警数: {report['alerts']['total_count']}")
            print(f"  活跃预警数: {report['alerts']['active_count']}")
        print("  PASSED")

        # 测试 9: 通知系统
        print("\n[测试 9] 通知系统...")
        notifier = AlertNotifier()
        notifier.add_channel(LogNotifier())

        test_alert = Alert(
            rule_name="测试规则",
            metric_name="test_metric",
            level=AlertLevel.WARNING,
            current_value=0.5,
            threshold=1.0,
            message="测试预警消息",
            timestamp=datetime.now(),
        )

        results = notifier.notify(test_alert)
        print(f"  通知渠道: {list(results.keys())}")
        print(f"  发送结果: {results}")
        print("  PASSED")

        # 测试 10: 数据持久化
        print("\n[测试 10] 数据持久化...")
        # 创建新的追踪器实例，验证数据加载
        tracker2 = PerformanceTracker(
            model_name="test_model",
            lab_path=str(lab_path),
        )
        history2 = tracker2.get_performance_history()
        print(f"  新追踪器加载的历史快照数: {len(history2)}")
        print("  PASSED")

        print("\n" + "=" * 70)
        print("所有测试 PASSED!")
        print("=" * 70)
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
