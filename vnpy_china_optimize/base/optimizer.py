"""
优化器基类

所有优化算法应继承此类，实现optimize方法。
"""

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import numpy as np

from .result import OptimizationResult, OptimizationMetrics, OptimizationSummary, OptimizationStatus


class BaseOptimizer(ABC):
    """
    优化器基类

    所有优化算法应继承此类。
    """

    def __init__(
        self,
        objective_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, tuple],
        maximize: bool = True
    ) -> None:
        """
        初始化优化器

        Args:
            objective_func: 目标函数，输入参数字典，返回分数
            param_space: 参数空间 {param_name: (min, max)}
            maximize: 是否最大化目标函数
        """
        self.objective_func = objective_func
        self.param_space = param_space
        self.maximize = maximize

        # 参数名称和边界
        self.param_names = list(param_space.keys())
        self.bounds = [param_space[name] for name in self.param_names]

        # 结果存储
        self.results: List[OptimizationResult] = []
        self.evaluation_count: int = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @abstractmethod
    def optimize(
        self,
        n_iterations: int = 100,
        **kwargs
    ) -> OptimizationSummary:
        """
        执行优化

        Args:
            n_iterations: 迭代次数
            **kwargs: 其他算法特定参数

        Returns:
            OptimizationSummary对象
        """
        pass

    def evaluate(self, params: Dict[str, Any]) -> float:
        """
        评估参数组合

        Args:
            params: 参数字典

        Returns:
            目标函数值
        """
        self.evaluation_count += 1
        score = self.objective_func(params)

        if not self.maximize:
            score = -score

        return score

    def _create_result(
        self,
        params: Dict[str, Any],
        metrics: OptimizationMetrics
    ) -> OptimizationResult:
        """创建优化结果"""
        return OptimizationResult(
            params=params,
            metrics=metrics,
            timestamp=datetime.now()
        )

    def get_summary(self) -> OptimizationSummary:
        """获取优化汇总"""
        if not self.results:
            return OptimizationSummary(
                total_evaluations=0,
                best_score=0.0,
                worst_score=0.0,
                avg_score=0.0,
                best_params={},
                best_metrics=OptimizationMetrics(
                    return_value=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0
                )
            )

        # 排序结果（按内部比较分数：evaluate 对 minimize 取负以统一用 max，reverse=True 选最优）
        sorted_results = sorted(
            self.results,
            key=lambda x: x.score,
            reverse=True
        )

        best = sorted_results[0]

        # 最小化模式下 evaluate 返回 -objective，记录的 metrics.return_value/sharpe_ratio 均为负。
        # 汇总展示需统一还原为真实目标值：best/worst/avg 直接乘 sign，all_results 与 best_metrics
        # 用 dataclasses.replace 重建，避免标量已还原但列表/指标仍带负号的不一致
        sign = -1.0 if not self.maximize else 1.0

        def _to_display(r: OptimizationResult) -> OptimizationResult:
            if sign == 1.0:
                return r
            restored = replace(
                r.metrics,
                return_value=r.metrics.return_value * sign,
                sharpe_ratio=r.metrics.sharpe_ratio * sign,
            )
            return replace(r, metrics=restored)

        display_results = [_to_display(r) for r in self.results]
        best_d = _to_display(best)
        worst_d = _to_display(sorted_results[-1])

        return OptimizationSummary(
            total_evaluations=self.evaluation_count,
            best_score=best_d.score,
            worst_score=worst_d.score,
            avg_score=sum(r.score for r in display_results) / len(display_results),
            best_params=best.params,
            best_metrics=best_d.metrics,
            all_results=display_results,
        )

    def _params_to_array(self, params: Dict[str, Any]) -> np.ndarray:
        """参数字典转数组"""
        return np.array([params[name] for name in self.param_names])

    def _array_to_params(self, array: np.ndarray) -> Dict[str, Any]:
        """数组转参数字典"""
        return {
            name: array[i]
            for i, name in enumerate(self.param_names)
        }

    def _validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数是否在有效范围内"""
        for name, value in params.items():
            if name not in self.param_space:
                continue
            low, high = self.param_space[name]
            if not (low <= value <= high):
                return False
        return True

    def _random_params(self) -> Dict[str, Any]:
        """生成随机参数"""
        return {
            name: np.random.uniform(low, high)
            for name, (low, high) in self.param_space.items()
        }
