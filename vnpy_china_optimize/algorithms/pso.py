"""
粒子群优化器

模拟鸟群觅食行为的优化算法，通过个体最优和全局最优
的引导来搜索解空间。
"""

from typing import List, Dict, Any, Callable
import numpy as np
from datetime import datetime

from ..base.optimizer import BaseOptimizer
from ..base.result import OptimizationSummary, OptimizationMetrics, OptimizationResult


class PSOOptimizer(BaseOptimizer):
    """
    粒子群优化器（Particle Swarm Optimization）

    模拟鸟群觅食行为的优化算法，
    适合连续参数空间的优化问题。

    算法参数：
    - w: 惯性权重（控制历史速度的影响）
    - c1: 认知系数（个体最优的影响）
    - c2: 社会系数（全局最优的影响）
    """

    def __init__(
        self,
        objective_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, tuple],
        population_size: int = 30,
        max_iterations: int = 100,
        w: float = 0.7,            # 惯性权重
        c1: float = 1.5,           # 认知系数
        c2: float = 1.5,           # 社会系数
        w_decay: bool = True,      # 惯性权重衰减
        random_state: int = None,
        maximize: bool = True
    ) -> None:
        """
        初始化粒子群优化器

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            population_size: 粒子数量
            max_iterations: 最大迭代次数
            w: 惯性权重
            c1: 认知系数
            c2: 社会系数
            w_decay: 是否衰减惯性权重
            random_state: 随机种子
            maximize: 是否最大化目标函数
        """
        super().__init__(objective_func, param_space, maximize=maximize)

        self.population_size = population_size
        self.max_iterations = max_iterations
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.w_decay = w_decay

        if random_state is not None:
            np.random.seed(random_state)

        # 粒子群
        self.particles: np.ndarray = None
        self.velocities: np.ndarray = None

        # 个体最优和全局最优
        self.pbest_positions: np.ndarray = None
        self.pbest_scores: np.ndarray = None
        self.gbest_position: np.ndarray = None
        self.gbest_score: float = -np.inf

    def optimize(
        self,
        n_iterations: int = None,
        verbose: bool = False,
        **kwargs
    ) -> OptimizationSummary:
        """
        执行粒子群优化

        Args:
            n_iterations: 迭代次数
            verbose: 是否打印进度

        Returns:
            OptimizationSummary对象
        """
        n_iterations = n_iterations or self.max_iterations

        self.start_time = datetime.now()
        self.results = []
        self.evaluation_count = 0

        # 初始化粒子群
        self._initialize_particles()

        if verbose:
            print(f"粒子群优化开始：粒子数={self.population_size}, "
                  f"迭代次数={n_iterations}")

        for iteration in range(n_iterations):
            # 更新惯性权重（线性衰减）
            if self.w_decay:
                w = self.w * (1 - iteration / n_iterations)
                w = max(0.4, w)  # 最小值0.4
            else:
                w = self.w

            # 更新每个粒子
            for i in range(self.population_size):
                # 更新速度
                r1, r2 = np.random.rand(2)
                cognitive = self.c1 * r1 * (self.pbest_positions[i] - self.particles[i])
                social = self.c2 * r2 * (self.gbest_position - self.particles[i])
                self.velocities[i] = w * self.velocities[i] + cognitive + social

                # 更新位置
                self.particles[i] += self.velocities[i]

                # 边界处理
                self._clip_particle(i)

                # 评估适应度（evaluate 内部已自增 evaluation_count，无需重复计数）
                params_dict = self._array_to_params(self.particles[i])
                score = self.evaluate(params_dict)

                # 更新个体最优
                if score > self.pbest_scores[i]:
                    self.pbest_scores[i] = score
                    self.pbest_positions[i] = self.particles[i].copy()

                    # 更新全局最优
                    if score > self.gbest_score:
                        self.gbest_score = score
                        self.gbest_position = self.particles[i].copy()

                        # 记录结果
                        self._record_result(params_dict, score)

            if verbose and (iteration + 1) % 10 == 0:
                print(f"  迭代 {iteration + 1}/{n_iterations}, "
                      f"当前最优: {self.gbest_score:.4f}")

        self.end_time = datetime.now()

        return self.get_summary()

    def _initialize_particles(self) -> None:
        """初始化粒子群"""
        n_params = len(self.param_names)

        # 初始化粒子位置
        self.particles = np.array([
            [np.random.uniform(low, high) for low, high in self.bounds]
            for _ in range(self.population_size)
        ])

        # 初始化速度（设为0或小的随机值）
        self.velocities = np.random.uniform(
            -0.1, 0.1,
            (self.population_size, n_params)
        )

        # 初始化个体最优
        self.pbest_positions = self.particles.copy()
        self.pbest_scores = np.full(self.population_size, -np.inf)

        # 初始化全局最优
        self.gbest_position = np.zeros(n_params)
        self.gbest_score = -np.inf

        # 初始评估（evaluate 内部已自增 evaluation_count）
        for i in range(self.population_size):
            params_dict = self._array_to_params(self.particles[i])
            score = self.evaluate(params_dict)
            self.pbest_scores[i] = score

            if score > self.gbest_score:
                self.gbest_score = score
                self.gbest_position = self.particles[i].copy()

        # 记录初始全局最优（避免主循环无改进时 get_summary 返回空汇总，但 gbest 实有值）
        if self.gbest_score > -np.inf:
            best_params = self._array_to_params(self.gbest_position)
            self._record_result(best_params, self.gbest_score)

    def _clip_particle(self, idx: int) -> None:
        """将粒子限制在边界内"""
        for i, (low, high) in enumerate(self.bounds):
            if self.particles[idx][i] < low:
                self.particles[idx][i] = low
                self.velocities[idx][i] *= -0.5  # 反弹并减速
            elif self.particles[idx][i] > high:
                self.particles[idx][i] = high
                self.velocities[idx][i] *= -0.5

    def _record_result(self, params: Dict[str, Any], score: float) -> None:
        """记录优化结果"""
        metrics = OptimizationMetrics(
            return_value=score,
            sharpe_ratio=score,
            max_drawdown=0.0,
            win_rate=0.5
        )

        result = OptimizationResult(
            params=params,
            metrics=metrics,
            timestamp=datetime.now()
        )

        self.results.append(result)
