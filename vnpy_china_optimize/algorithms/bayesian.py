"""
贝叶斯优化器

使用高斯过程作为代理模型，通过期望改进（EI）采集函数
选择下一个采样点，适合昂贵的黑盒优化问题。
"""

from typing import List, Dict, Any, Callable
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern

from ..base.optimizer import BaseOptimizer
from ..base.result import OptimizationSummary, OptimizationMetrics, OptimizationResult
from datetime import datetime


class BayesianOptimizer(BaseOptimizer):
    """
    贝叶斯优化器

    使用高斯过程代理模型和期望改进采集函数。
    适合计算代价高的优化问题。

    算法参数：
    - n_initial: 初始随机采样次数
    - alpha: 高斯过程噪声参数
    - kernel: 核函数类型（"rbf"或"matern"）
    """

    def __init__(
        self,
        objective_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, tuple],
        n_initial: int = 5,
        alpha: float = 1e-6,
        kernel: str = "rbf",
        random_state: int = None,
        maximize: bool = True
    ) -> None:
        """
        初始化贝叶斯优化器

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            n_initial: 初始随机采样次数
            alpha: 高斯过程噪声
            kernel: 核函数类型
            random_state: 随机种子
            maximize: 是否最大化目标函数
        """
        super().__init__(objective_func, param_space, maximize=maximize)

        self.n_initial = n_initial
        self.alpha = alpha
        self.random_state = random_state

        if random_state is not None:
            np.random.seed(random_state)

        # 观测数据
        self.X_observed: List[np.ndarray] = []
        self.y_observed: List[float] = []

        # 高斯过程代理模型
        if kernel == "matern":
            gp_kernel = ConstantKernel(1.0) * Matern(
                length_scale=1.0,
                nu=2.5
            )
        else:
            gp_kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)

        self.gp = GaussianProcessRegressor(
            kernel=gp_kernel,
            alpha=alpha,
            normalize_y=True,
            n_restarts_optimizer=5
        )

    def optimize(
        self,
        n_iterations: int = 100,
        verbose: bool = False,
        **kwargs
    ) -> OptimizationSummary:
        """
        执行贝叶斯优化

        Args:
            n_iterations: 总迭代次数
            verbose: 是否打印进度

        Returns:
            OptimizationSummary对象
        """
        self.start_time = datetime.now()
        self.results = []
        self.evaluation_count = 0

        # 阶段1: 随机采样初始化
        if verbose:
            print(f"初始化：随机采样 {self.n_initial} 次")

        for i in range(self.n_initial):
            x = self._random_sample()
            x_dict = self._array_to_params(x)
            y = self.evaluate(x_dict)

            self.X_observed.append(x)
            self.y_observed.append(y)

            if verbose and (i + 1) % 5 == 0:
                print(f"  已完成 {i + 1}/{self.n_initial} 次初始化采样")

        # 阶段2: 贝叶斯优化迭代
        n_bayesian_iterations = n_iterations - self.n_initial

        if verbose:
            print(f"贝叶斯优化：迭代 {n_bayesian_iterations} 次")

        for i in range(n_bayesian_iterations):
            # 找到最优采样点
            x_next = self._propose_location()

            # 评估目标函数
            x_dict = self._array_to_params(x_next)
            y = self.evaluate(x_dict)

            # 更新观测数据
            self.X_observed.append(x_next)
            self.y_observed.append(y)

            # 记录结果
            self._record_result(x_dict, y)

            if verbose and (i + 1) % 10 == 0:
                best_y = max(self.y_observed)
                print(f"  迭代 {i + 1}/{n_bayesian_iterations}, "
                      f"当前最优: {best_y:.4f}")

        self.end_time = datetime.now()

        return self.get_summary()

    def _random_sample(self) -> np.ndarray:
        """随机采样"""
        return np.array([
            np.random.uniform(low, high)
            for low, high in self.bounds
        ])

    def _propose_location(self) -> np.ndarray:
        """
        提出下一个采样位置

        通过优化采集函数找到最有希望的采样点。
        """
        # 需要至少有一个观测点
        if len(self.X_observed) == 0:
            return self._random_sample()

        # 优化采集函数
        result = minimize(
            self._acquisition_function,
            x0=self.X_observed[-1],  # 从最后一个点开始
            bounds=self.bounds,
            method='L-BFGS-B'
        )

        return result.x

    def _acquisition_function(self, X: np.ndarray) -> float:
        """
        采集函数（Expected Improvement）

        Args:
            X: 候选采样点

        Returns:
            采集函数值（负值，用于最小化）
        """
        # 确保X是2D数组
        if X.ndim == 1:
            X = X.reshape(1, -1)

        # 拟合高斯过程
        X_array = np.array(self.X_observed)
        y_array = np.array(self.y_observed)
        self.gp.fit(X_array, y_array)

        # 预测均值和标准差
        mu, sigma = self.gp.predict(X, return_std=True)

        # 当前最优值
        best_y = max(self.y_observed) if self.y_observed else 0

        # 避免除零
        sigma = max(sigma[0], 1e-6)

        # 期望改进
        z = (mu[0] - best_y) / sigma
        ei = (mu[0] - best_y) * norm.cdf(z) + sigma * norm.pdf(z)

        return -ei  # 返回负值用于最小化

    def _record_result(self, params: Dict[str, Any], score: float) -> None:
        """记录优化结果"""
        # 创建基础指标
        metrics = OptimizationMetrics(
            return_value=score,  # 使用score作为收益率
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

    def get_surrogate_model(self) -> GaussianProcessRegressor:
        """获取代理模型"""
        return self.gp

    def predict(self, X: np.ndarray) -> tuple:
        """
        使用代理模型预测

        Args:
            X: 输入点

        Returns:
            (均值, 标准差)
        """
        if len(self.X_observed) == 0:
            return 0.0, 1.0

        X_array = np.array(self.X_observed)
        y_array = np.array(self.y_observed)
        self.gp.fit(X_array, y_array)

        return self.gp.predict(X.reshape(1, -1), return_std=True)
