"""
过拟合检测器

通过样本外测试、前向验证等方法，
检测参数优化是否存在过拟合问题。
"""

import logging
from typing import Dict, Any, List, Callable, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

from ..base.result import OptimizationMetrics

logger = logging.getLogger(__name__)


@dataclass
class OverfitTestResult:
    """过拟合测试结果"""
    # 测试类型
    test_type: str  # "out_sample", "walk_forward", "stability"

    # 训练集指标
    train_return: float
    train_sharpe: float

    # 测试集指标
    test_return: float
    test_sharpe: float

    # 衰减比率
    return_decay: float      # 收益率衰减
    sharpe_decay: float      # 夏普比率衰减

    # 稳定性指标
    stability_score: float   # 稳定性评分

    # 判断结果
    is_overfit: bool         # 是否过拟合
    risk_level: str          # 风险等级: "low", "medium", "high"

    def to_dict(self) -> Dict:
        return {
            "test_type": self.test_type,
            "train_return": self.train_return,
            "train_sharpe": self.train_sharpe,
            "test_return": self.test_return,
            "test_sharpe": self.test_sharpe,
            "return_decay": self.return_decay,
            "sharpe_decay": self.sharpe_decay,
            "stability_score": self.stability_score,
            "is_overfit": self.is_overfit,
            "risk_level": self.risk_level
        }


class OverfitDetector:
    """
    过拟合检测器

    通过样本外测试、前向验证等方法，
    检测参数优化是否存在过拟合问题。
    """

    def __init__(
        self,
        backtest_func: Callable[[Dict[str, Any], str, str], Tuple[OptimizationMetrics, Any]],
        decay_threshold: float = 0.5,
        stability_threshold: float = 0.5
    ) -> None:
        """
        初始化过拟合检测器

        Args:
            backtest_func: 回测函数，输入参数和日期范围，返回回测指标
            decay_threshold: 衰减阈值（低于此值认为过拟合）
            stability_threshold: 稳定性阈值
        """
        self.backtest_func = backtest_func
        self.decay_threshold = decay_threshold
        self.stability_threshold = stability_threshold

    def out_sample_test(
        self,
        params: Dict[str, Any],
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str
    ) -> OverfitTestResult:
        """
        样本外测试

        将数据分为训练集和测试集，在训练集上优化参数，
        在测试集上验证性能。

        Args:
            params: 待测试参数
            train_start: 训练集开始日期
            train_end: 训练集结束日期
            test_start: 测试集开始日期
            test_end: 测试集结束日期

        Returns:
            OverfitTestResult对象
        """
        # 训练集回测
        train_metrics = self._run_backtest(
            params, train_start, train_end
        )

        # 测试集回测
        test_metrics = self._run_backtest(
            params, test_start, test_end
        )

        # 计算衰减比率
        return_decay = self._calculate_decay(
            train_metrics.return_value,
            test_metrics.return_value
        )
        sharpe_decay = self._calculate_decay(
            train_metrics.sharpe_ratio,
            test_metrics.sharpe_ratio
        )

        # 判断过拟合
        is_overfit = return_decay < self.decay_threshold

        # 评估风险等级
        risk_level = self._assess_risk_level(return_decay, sharpe_decay)

        return OverfitTestResult(
            test_type="out_sample",
            train_return=train_metrics.return_value,
            train_sharpe=train_metrics.sharpe_ratio,
            test_return=test_metrics.return_value,
            test_sharpe=test_metrics.sharpe_ratio,
            return_decay=return_decay,
            sharpe_decay=sharpe_decay,
            stability_score=0.0,  # 样本外测试不计算稳定性
            is_overfit=is_overfit,
            risk_level=risk_level
        )

    def walk_forward_validation(
        self,
        params: Dict[str, Any],
        start_date: str,
        end_date: str,
        train_days: int = 252,    # 训练窗口：1年
        test_days: int = 63,      # 测试窗口：3个月
        step_days: int = 21       # 步长：1个月
    ) -> OverfitTestResult:
        """
        前向验证

        滚动窗口验证，更接近实盘情况。

        Args:
            params: 待测试参数
            start_date: 开始日期
            end_date: 结束日期
            train_days: 训练窗口天数
            test_days: 测试窗口天数
            step_days: 滚动步长

        Returns:
            OverfitTestResult对象
        """
        # 转换日期为数值
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # 执行前向验证
        test_returns = []
        test_sharpes = []
        current_date = start

        while True:
            train_start = current_date
            train_end = train_start + timedelta(days=train_days)

            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=test_days)

            # 检查是否超出范围
            if test_end > end:
                break

            # 执行测试集回测
            test_metrics = self._run_backtest(
                params,
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d")
            )

            test_returns.append(test_metrics.return_value)
            test_sharpes.append(test_metrics.sharpe_ratio)

            # 滚动窗口
            current_date = test_start + timedelta(days=step_days)

        # 计算统计量
        if not test_returns:
            return self._empty_result("walk_forward")

        avg_return = np.mean(test_returns)
        std_return = np.std(test_returns)
        avg_sharpe = np.mean(test_sharpes)
        std_sharpe = np.std(test_sharpes)

        # 稳定性评分（变异系数的倒数）
        stability_score = 1.0 / (1.0 + std_return / (abs(avg_return) + 1e-6))

        # 使用第一次窗口作为"训练"
        train_return = test_returns[0] if test_returns else 0.0
        train_sharpe = test_sharpes[0] if test_sharpes else 0.0

        return_decay = self._calculate_decay(train_return, avg_return)
        sharpe_decay = self._calculate_decay(train_sharpe, avg_sharpe)

        # 判断过拟合（基于稳定性）
        is_overfit = stability_score < (1 - self.stability_threshold)

        return OverfitTestResult(
            test_type="walk_forward",
            train_return=train_return,
            train_sharpe=train_sharpe,
            test_return=avg_return,
            test_sharpe=avg_sharpe,
            return_decay=return_decay,
            sharpe_decay=sharpe_decay,
            stability_score=stability_score,
            is_overfit=is_overfit,
            risk_level=self._assess_risk_level(return_decay, sharpe_decay, stability_score)
        )

    def check_stability(
        self,
        params_list: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        tolerance: float = 0.1
    ) -> Dict[str, Any]:
        """
        参数稳定性分析

        测试相似参数是否产生相似结果。

        Args:
            params_list: 参数列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            tolerance: 容差

        Returns:
            稳定性分析结果
        """
        results = []

        for params in params_list:
            metrics = self._run_backtest(params, start_date, end_date)
            results.append({
                "params": params,
                "return": metrics.return_value,
                "sharpe": metrics.sharpe_ratio
            })

        if not results:
            return {"is_stable": False, "variance": 0.0}

        # 计算方差
        returns = [r["return"] for r in results]
        variance = np.var(returns)
        mean_return = np.mean(returns)

        # 变异系数
        cv = np.sqrt(variance) / (abs(mean_return) + 1e-6)

        # 判断稳定性
        is_stable = cv < tolerance

        return {
            "is_stable": is_stable,
            "variance": variance,
            "coefficient_of_variation": cv,
            "mean_return": mean_return,
            "return_range": (min(returns), max(returns))
        }

    def _run_backtest(
        self,
        params: Dict[str, Any],
        start_date: str,
        end_date: str
    ) -> OptimizationMetrics:
        """运行回测"""
        # 调用回测函数
        result = self.backtest_func(params, start_date, end_date)

        # backtest_func 可能返回 None（回测失败/异常），避免 None.get 崩溃
        if result is None:
            logger.warning(f"backtest_func 返回 None: params={params}, {start_date}~{end_date}")
            return OptimizationMetrics(
                return_value=0.0, sharpe_ratio=0.0, max_drawdown=0.0
            )

        # 转换为OptimizationMetrics
        if isinstance(result, tuple):
            return result[0]  # 假设第一个是指标
        elif isinstance(result, OptimizationMetrics):
            return result
        else:
            # 如果返回的是字典，转换为OptimizationMetrics
            return OptimizationMetrics(
                return_value=result.get("return_value", 0.0),
                sharpe_ratio=result.get("sharpe_ratio", 0.0),
                max_drawdown=result.get("max_drawdown", 0.0),
            )

    def _calculate_decay(self, train_value: float, test_value: float) -> float:
        """计算衰减比率"""
        if train_value == 0:
            return 0.0
        return test_value / train_value if train_value > 0 else 0.0

    def _assess_risk_level(
        self,
        return_decay: float,
        sharpe_decay: float,
        stability_score: float = 1.0
    ) -> str:
        """评估风险等级"""
        if return_decay >= 0.8 and sharpe_decay >= 0.8:
            return "low"
        elif return_decay >= 0.5 and sharpe_decay >= 0.5:
            return "medium"
        else:
            return "high"

    def _empty_result(self, test_type: str) -> OverfitTestResult:
        """返回空结果"""
        return OverfitTestResult(
            test_type=test_type,
            train_return=0.0,
            train_sharpe=0.0,
            test_return=0.0,
            test_sharpe=0.0,
            return_decay=0.0,
            sharpe_decay=0.0,
            stability_score=0.0,
            is_overfit=True,
            risk_level="high"
        )
