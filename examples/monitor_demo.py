#!/usr/bin/env python3
"""
VeighNa Alpha Monitor - 演示脚本

展示性能监控系统的基本用法。
"""

import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from vnpy.alpha.lab import AlphaLab


def main():
    """主演示函数"""
    print("=" * 70)
    print("VeighNa Alpha Monitor - 性能监控演示")
    print("=" * 70)

    # 创建临时实验室目录
    temp_dir = tempfile.mkdtemp()
    lab_path = Path(temp_dir)
    print(f"\n创建临时实验室: {lab_path}")

    try:
        # 创建 AlphaLab 实例
        lab = AlphaLab(str(lab_path))
        print("AlphaLab 实例创建成功")

        # 模拟模型1 - 良好表现
        print("\n" + "-" * 70)
        print("模拟模型1（良好表现）")
        print("-" * 70)

        model1_result = {
            "returns": np.array([
                0.015, 0.022, -0.008, 0.018, 0.025,
                0.012, -0.005, 0.028, 0.019, 0.014,
                0.021, -0.003, 0.016, 0.023, 0.011,
                0.017, 0.009, -0.012, 0.026, 0.013,
            ]),
            "predictions": np.random.randn(100),
            "targets": np.random.randn(100) * 0.5,
            "trading_stats": {
                "total_trades": 40,
                "long_trades": 25,
                "short_trades": 15,
                "winning_trades": 24,
                "losing_trades": 16,
            },
            "metadata": {"strategy": "momentum", "version": "1.0"},
        }

        alerts1 = lab.run_backtest_with_tracking(
            model_name="model_good",
            backtest_result=model1_result,
        )

        print(f"回测完成，触发 {len(alerts1)} 个预警")
        for alert in alerts1:
            print(f"  [{alert.level.value.upper()}] {alert.message}")

        # 模拟模型2 - 表现较差（会触发预警）
        print("\n" + "-" * 70)
        print("模拟模型2（表现较差）")
        print("-" * 70)

        model2_result = {
            "returns": np.array([
                -0.02, -0.015, 0.005, -0.025, -0.018,
                0.008, -0.022, 0.012, -0.028, -0.035,
                -0.012, 0.018, -0.045, 0.003, -0.028,
                -0.015, 0.022, -0.038, 0.008, -0.042,
            ]),
            "predictions": np.random.randn(100),
            "targets": np.random.randn(100) * 2,
            "trading_stats": {
                "total_trades": 60,
                "long_trades": 30,
                "short_trades": 30,
                "winning_trades": 18,
                "losing_trades": 42,
            },
            "metadata": {"strategy": "mean_reversion", "version": "2.0"},
        }

        alerts2 = lab.run_backtest_with_tracking(
            model_name="model_poor",
            backtest_result=model2_result,
        )

        print(f"回测完成，触发 {len(alerts2)} 个预警")
        for alert in alerts2:
            print(f"  [{alert.level.value.upper()}] {alert.message}")

        # 查看性能报告
        print("\n" + "-" * 70)
        print("性能报告")
        print("-" * 70)

        for model_name in ["model_good", "model_poor"]:
            report = lab.generate_performance_report(model_name, days=30)
            print(f"\n模型: {model_name}")
            print(f"  快照数: {report['snapshots_count']}")
            print(f"  总预警: {report['alerts']['total_count']}")
            print(f"  活跃预警: {report['alerts']['active_count']}")

        # 查看活跃预警
        print("\n" + "-" * 70)
        print("活跃预警")
        print("-" * 70)

        active_alerts = lab.get_active_alerts("model_poor")
        for alert in active_alerts:
            print(f"  [{alert.level.value.upper()}] {alert.metric_name}: {alert.current_value:.4f}")

        # 确认部分预警
        if active_alerts:
            print(f"\n确认了 {len(active_alerts)} 个预警")
            for i, alert in enumerate(active_alerts):
                lab.acknowledge_alert("model_poor", i, user="demo_user")

        # 最终报告
        print("\n" + "-" * 70)
        print("最终报告")
        print("-" * 70)

        for model_name in ["model_good", "model_poor"]:
            active = lab.get_active_alerts(model_name)
            print(f"{model_name}: {len(active)} 个活跃预警")

        print("\n" + "=" * 70)
        print("演示完成！")
        print("=" * 70)

    finally:
        # 清理临时目录
        shutil.rmtree(lab_path, ignore_errors=True)
        print(f"\n已清理临时目录: {lab_path}")


if __name__ == "__main__":
    main()
