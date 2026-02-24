"""
IC/IR分析器模块

本模块提供信息系数（IC）和信息比率（IR）的计算功能，
这是量化投资中最重要的因子评价指标。

IC (Information Coefficient): 衡量因子预测能力，相关系数越高表示预测能力越强
IR (Information Ratio): 衡量IC的稳定性，IR = IC均值 / IC标准差
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from scipy.stats import spearmanr, pearsonr


class ICAnalyzer:
    """IC/IR分析器

    提供信息系数（IC）和信息比率（IR）的计算功能：
    - IC (Information Coefficient): 皮尔逊相关系数和斯皮尔曼相关系数
    - Rank IC: 排名信息系数，对异常值更稳健
    - IR (Information Ratio): IC稳定性指标

    Attributes:
        ic_history: IC历史记录
        rank_ic_history: Rank IC历史记录
    """

    def __init__(self) -> None:
        """初始化分析器"""
        self.ic_history: List[float] = []
        self.rank_ic_history: List[float] = []

    def calculate_ic(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        method: str = "pearson"
    ) -> float:
        """计算IC (Information Coefficient)

        IC是预测值与实际收益率之间的相关系数，衡量因子的预测能力。

        Args:
            predictions: 预测值数组（如预测收益率）
            actuals: 实际值数组
            method: 相关系数计算方法，"pearson"（皮尔逊）或 "spearman"（斯皮尔曼）

        Returns:
            IC值，范围[-1, 1]

        Raises:
            ValueError: 当预测值和实际值长度不匹配时
            ValueError: 当method不是有效的计算方法时
        """
        # 验证输入
        if len(predictions) != len(actuals):
            raise ValueError("预测值和实际值长度不匹配")
        if len(predictions) < 2:
            raise ValueError("需要至少2个样本计算相关系数")

        # 检查是否有足够的变异
        if np.std(predictions) == 0 or np.std(actuals) == 0:
            return 0.0

        if method == "pearson":
            # 皮尔逊相关系数
            ic, _ = pearsonr(predictions, actuals)
        elif method == "spearman":
            # 斯皮尔曼相关系数
            ic, _ = spearmanr(predictions, actuals)
        else:
            raise ValueError(f"未知的IC计算方法: {method}，请使用 'pearson' 或 'spearman'")

        # 处理NaN情况
        if np.isnan(ic):
            return 0.0

        return float(ic)

    def calculate_rank_ic(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray
    ) -> float:
        """计算Rank IC

        Rank IC是将预测值和实际值分别排名后计算IC，
        对极端值更稳健，不受异常值影响。

        Args:
            predictions: 预测值数组
            actuals: 实际值数组

        Returns:
            Rank IC值，范围[-1, 1]
        """
        # 验证输入
        if len(predictions) != len(actuals):
            raise ValueError("预测值和实际值长度不匹配")
        if len(predictions) < 2:
            raise ValueError("需要至少2个样本计算相关系数")

        # 将预测值和实际值转换为排名
        pred_ranks = np.argsort(np.argsort(predictions))
        actual_ranks = np.argsort(np.argsort(actuals))

        # 计算排名相关系数
        if np.std(pred_ranks) == 0 or np.std(actual_ranks) == 0:
            return 0.0

        rank_ic, _ = pearsonr(pred_ranks, actual_ranks)

        # 处理NaN情况
        if np.isnan(rank_ic):
            return 0.0

        return float(rank_ic)

    def calculate_ic_series(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        n_periods: Optional[int] = None
    ) -> np.ndarray:
        """计算IC时间序列

        将预测值和实际值按时间分段，计算每个时间段的IC值。

        Args:
            predictions: 预测值数组
            actuals: 实际值数组
            n_periods: 时间段数量，默认自动计算

        Returns:
            IC值数组
        """
        if len(predictions) != len(actuals):
            raise ValueError("预测值和实际值长度不匹配")

        n = len(predictions)

        # 自动计算时间段数量
        if n_periods is None:
            # 假设每月一个周期
            n_periods = max(1, n // 20)

        if n_periods <= 0 or n_periods > n:
            n_periods = 1

        period_size = n // n_periods

        ic_series = []
        for i in range(n_periods):
            start_idx = i * period_size
            end_idx = start_idx + period_size if i < n_periods - 1 else n

            pred_slice = predictions[start_idx:end_idx]
            actual_slice = actuals[start_idx:end_idx]

            if len(pred_slice) >= 2:
                ic = self.calculate_ic(pred_slice, actual_slice)
                ic_series.append(ic)

        return np.array(ic_series)

    def calculate_ir(
        self,
        ic_series: np.ndarray,
        annualized: bool = False,
        periods_per_year: int = 12
    ) -> float:
        """计算IR (Information Ratio)

        IR = IC均值 / IC标准差，反映IC的稳定性。
        IR越高表示因子预测能力越稳定。

        Args:
            ic_series: IC值序列
            annualized: 是否年化IR
            periods_per_year: 每年有多少个周期（月度为12）

        Returns:
            IR值
        """
        if len(ic_series) == 0:
            return 0.0

        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series, ddof=1)  # 使用样本标准差

        if ic_std == 0:
            return 0.0

        ir = ic_mean / ic_std

        if annualized:
            # 年化IR
            ir = ir * np.sqrt(periods_per_year)

        return float(ir)

    def add_to_history(
        self,
        ic: float,
        rank_ic: Optional[float] = None
    ) -> None:
        """添加IC到历史记录

        Args:
            ic: IC值
            rank_ic: Rank IC值（可选）
        """
        self.ic_history.append(ic)
        if rank_ic is not None:
            self.rank_ic_history.append(rank_ic)

    def get_ic_statistics(self) -> Dict[str, float]:
        """获取IC统计信息

        Returns:
            包含IC统计指标的字典
        """
        if not self.ic_history:
            return {
                "ic_mean": 0.0,
                "ic_std": 0.0,
                "ic_ir": 0.0,
                "ic_count": 0
            }

        ic_array = np.array(self.ic_history)

        return {
            "ic_mean": float(np.mean(ic_array)),
            "ic_std": float(np.std(ic_array, ddof=1)),
            "ic_ir": float(np.mean(ic_array) / np.std(ic_array, ddof=1)) if np.std(ic_array, ddof=1) > 0 else 0.0,
            "ic_count": len(ic_array),
            "ic_min": float(np.min(ic_array)),
            "ic_max": float(np.max(ic_array)),
            "ic_positive_ratio": float(np.mean(ic_array > 0))
        }

    def get_rank_ic_statistics(self) -> Dict[str, float]:
        """获取Rank IC统计信息

        Returns:
            包含Rank IC统计指标的字典
        """
        if not self.rank_ic_history:
            return {
                "rank_ic_mean": 0.0,
                "rank_ic_std": 0.0,
                "rank_ic_ir": 0.0,
                "rank_ic_count": 0
            }

        rank_ic_array = np.array(self.rank_ic_history)

        return {
            "rank_ic_mean": float(np.mean(rank_ic_array)),
            "rank_ic_std": float(np.std(rank_ic_array, ddof=1)),
            "rank_ic_ir": float(np.mean(rank_ic_array) / np.std(rank_ic_array, ddof=1)) if np.std(rank_ic_array, ddof=1) > 0 else 0.0,
            "rank_ic_count": len(rank_ic_array),
            "rank_ic_min": float(np.min(rank_ic_array)),
            "rank_ic_max": float(np.max(rank_ic_array)),
            "rank_ic_positive_ratio": float(np.mean(rank_ic_array > 0))
        }

    def clear_history(self) -> None:
        """清除历史记录"""
        self.ic_history.clear()
        self.rank_ic_history.clear()
