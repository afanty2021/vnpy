"""
测试粒子群优化器
"""
import pytest
import numpy as np
from vnpy_china_optimize.algorithms.pso import PSOOptimizer


def test_pso_optimizer():
    """测试粒子群优化器"""

    def sphere(params: dict) -> float:
        """球面函数，最小值在原点"""
        x = params["x"]
        y = params["y"]
        return -(x ** 2 + y ** 2)  # 转换为最大化问题

    param_space = {
        "x": (-10, 10),
        "y": (-10, 10)
    }

    optimizer = PSOOptimizer(
        objective_func=sphere,
        param_space=param_space,
        population_size=20,
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=50)

    # 验证结果
    assert summary.total_evaluations > 0
    assert len(summary.all_results) > 0

    # 最优解应该在 (0, 0) 附近
    assert abs(summary.best_params["x"]) < 1.5
    assert abs(summary.best_params["y"]) < 1.5


def test_pso_convergence():
    """测试PSO收敛性"""
    def sphere(params: dict) -> float:
        x = params["x"]
        y = params["y"]
        return -(x ** 2 + y ** 2)

    param_space = {"x": (-10, 10), "y": (-10, 10)}

    optimizer = PSOOptimizer(
        objective_func=sphere,
        param_space=param_space,
        population_size=20,
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=100)

    # 应该收敛到 (0, 0) 附近
    assert abs(summary.best_params["x"]) < 1.0
    assert abs(summary.best_params["y"]) < 1.0


def test_pso_with_decay():
    """测试惯性权重衰减"""
    def sphere(params: dict) -> float:
        x = params["x"]
        return -x ** 2

    param_space = {"x": (-10, 10)}

    optimizer = PSOOptimizer(
        objective_func=sphere,
        param_space=param_space,
        population_size=15,
        w_decay=True,  # 启用衰减
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=50)

    # 应该收敛到 0 附近
    assert abs(summary.best_params["x"]) < 1.5


def test_pso_multimodal():
    """测试多峰函数优化"""
    def rastrigin(params: dict) -> float:
        """Rastrigin函数，多峰函数"""
        A = 10
        x = params["x"]
        y = params["y"]
        return -A * 2 - (x**2 - A * np.cos(2 * np.pi * x)) - (y**2 - A * np.cos(2 * np.pi * y))

    param_space = {
        "x": (-5.12, 5.12),
        "y": (-5.12, 5.12)
    }

    optimizer = PSOOptimizer(
        objective_func=rastrigin,
        param_space=param_space,
        population_size=30,
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=50)

    # 验证结果
    assert summary.total_evaluations > 0
    # 最优解应该在 (0, 0) 附近
    assert abs(summary.best_params["x"]) < 2
    assert abs(summary.best_params["y"]) < 2


def test_pso_with_minimize():
    """测试最小化模式"""
    def sphere(params: dict) -> float:
        x = params["x"]
        return x ** 2  # 最小值在 0

    param_space = {"x": (-10, 10)}

    optimizer = PSOOptimizer(
        objective_func=sphere,
        param_space=param_space,
        population_size=15,
        maximize=False,  # 最小化
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=30)

    # 应该找到最小值在 0 附近
    assert abs(summary.best_params["x"]) < 2
