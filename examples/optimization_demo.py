"""
VeighNa策略参数优化示例

演示如何使用vnpy_china_optimize模块进行策略参数优化。
"""
import numpy as np
from vnpy_china_optimize import (
    BayesianOptimizer,
    PSOOptimizer,
    OptimizationReportGenerator,
    OverfitDetector,
    ChinaOptimizerSetting,
    ChinaTradingCost,
    OptimizationMetrics,
)


def simple_strategy_objective(params: dict) -> float:
    """
    简单策略目标函数

    模拟一个双均线策略的优化目标。
    """
    # 提取参数
    fast_window = int(params["fast_window"])
    slow_window = int(params["slow_window"])
    threshold = params["threshold"]

    # 简单的模拟：最优参数在 fast=20, slow=60, threshold=0.02
    # 使用高斯函数模拟收益曲面
    fast_score = np.exp(-((fast_window - 20) ** 2) / 200)
    slow_score = np.exp(-((slow_window - 60) ** 2) / 500)
    threshold_score = np.exp(-((threshold - 0.02) ** 2) / 0.0005)

    # 综合评分（加上一些随机噪声模拟真实回测）
    noise = np.random.normal(0, 0.05)
    score = (fast_score + slow_score + threshold_score) / 3 + noise

    return score


def example_bayesian_optimization():
    """贝叶斯优化示例"""
    print("\n" + "=" * 60)
    print("贝叶斯优化示例")
    print("=" * 60)

    # 定义参数空间
    param_space = {
        "fast_window": (5, 30),
        "slow_window": (30, 120),
        "threshold": (0.005, 0.05)
    }

    # 创建优化器
    optimizer = BayesianOptimizer(
        objective_func=simple_strategy_objective,
        param_space=param_space,
        n_initial=10,
        random_state=42
    )

    # 执行优化
    summary = optimizer.optimize(n_iterations=50, verbose=True)

    # 输出结果
    print(f"\n最优参数:")
    for param, value in summary.best_params.items():
        print(f"  {param}: {value:.4f}")
    print(f"\n最优分数: {summary.best_score:.4f}")

    return summary


def example_pso_optimization():
    """粒子群优化示例"""
    print("\n" + "=" * 60)
    print("粒子群优化示例")
    print("=" * 60)

    # 定义参数空间
    param_space = {
        "fast_window": (5, 30),
        "slow_window": (30, 120),
        "threshold": (0.005, 0.05)
    }

    # 创建优化器
    optimizer = PSOOptimizer(
        objective_func=simple_strategy_objective,
        param_space=param_space,
        population_size=30,
        random_state=42
    )

    # 执行优化
    summary = optimizer.optimize(n_iterations=100, verbose=True)

    # 输出结果
    print(f"\n最优参数:")
    for param, value in summary.best_params.items():
        print(f"  {param}: {value:.4f}")
    print(f"\n最优分数: {summary.best_score:.4f}")

    return summary


def example_overfit_detection(summary):
    """过拟合检测示例"""
    print("\n" + "=" * 60)
    print("过拟合检测示例")
    print("=" * 60)

    # 模拟回测函数
    def mock_backtest(params, start_date, end_date):
        # 简单模拟：根据时间段返回不同结果
        if "2023" in start_date:
            # 训练集
            return OptimizationMetrics(
                return_value=0.25,
                sharpe_ratio=1.8,
                max_drawdown=-0.12,
                win_rate=0.55,
                total_trades=100
            ), None
        else:
            # 测试集（表现稍差）
            return OptimizationMetrics(
                return_value=0.12,
                sharpe_ratio=0.9,
                max_drawdown=-0.18,
                win_rate=0.48,
                total_trades=60
            ), None

    # 创建检测器
    detector = OverfitDetector(
        backtest_func=mock_backtest,
        decay_threshold=0.6
    )

    # 执行样本外测试
    result = detector.out_sample_test(
        params=summary.best_params,
        train_start="2023-01-01",
        train_end="2023-06-30",
        test_start="2023-07-01",
        test_end="2023-12-31"
    )

    print(f"\n样本外测试结果:")
    print(f"  训练集收益率: {result.train_return:.2%}")
    print(f"  测试集收益率: {result.test_return:.2%}")
    print(f"  收益率衰减: {result.return_decay:.2%}")
    print(f"  是否过拟合: {'是' if result.is_overfit else '否'}")
    print(f"  风险等级: {result.risk_level}")

    return result


def example_report_generation(summary, overfit_result):
    """报告生成示例"""
    print("\n" + "=" * 60)
    print("优化报告生成示例")
    print("=" * 60)

    # 创建报告生成器
    generator = OptimizationReportGenerator()

    # 生成报告
    report = generator.generate(summary, overfit_result)

    print(report)

    # 导出报告
    generator.export_to_txt("optimization_report.txt")
    print("\n报告已导出到: optimization_report.txt")


def example_china_trading_cost():
    """A股交易成本示例"""
    print("\n" + "=" * 60)
    print("A股交易成本计算示例")
    print("=" * 60)

    # 创建交易成本配置
    cost_config = ChinaTradingCost()

    # 计算买入成本
    price = 10.0
    volume = 100  # 100手

    buy_cost = cost_config.calculate_buy_cost(price, volume)
    sell_income = cost_config.calculate_sell_cost(price, volume)
    round_trip_cost = cost_config.calculate_round_trip_cost(price, volume)

    print(f"\n交易参数:")
    print(f"  价格: {price}元")
    print(f"  数量: {volume}手")
    print(f"\n成本分析:")
    print(f"  买入成本: {buy_cost:.2f}元")
    print(f"  卖出收入: {sell_income:.2f}元")
    print(f"  往返成本率: {round_trip_cost:.4%}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print(" " * 15 + "VeighNa策略参数优化示例")
    print("=" * 60)

    # 设置随机种子保证可复现
    np.random.seed(42)

    # 1. 贝叶斯优化
    bayesian_summary = example_bayesian_optimization()

    # 2. 粒子群优化
    # pso_summary = example_pso_optimization()

    # 3. 过拟合检测
    overfit_result = example_overfit_detection(bayesian_summary)

    # 4. 报告生成
    example_report_generation(bayesian_summary, overfit_result)

    # 5. A股交易成本
    example_china_trading_cost()


if __name__ == "__main__":
    main()
