"""因子组合模块

提供因子组合、权重分配、因子正交化等功能。
"""

import polars as pl
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WeightMethod(Enum):
    """权重计算方法"""
    EQUAL = "equal"  # 等权重
    IC_WEIGHTED = "ic_weighted"  # IC加权
    IR_WEIGHTED = "ir_weighted"  # IR加权
    CUSTOM = "custom"  # 自定义权重
    OPTIMIZED = "optimized"  # 优化权重（最大夏普比率）


class OrthogonalMethod(Enum):
    """正交化方法"""
    NONE = "none"  # 不正交
    GRAM_SCHMIDT = "gram_schmidt"  # Gram-Schmidt正交化
    PCA = "pca"  # 主成分分析


@dataclass
class FactorWeight:
    """因子权重"""
    factor_name: str
    weight: float
    ic: float = 0.0
    ir: float = 0.0


@dataclass
class FactorCombinationConfig:
    """因子组合配置"""
    factors: List[str]
    weights: Optional[Dict[str, float]] = None  # 自定义权重
    weight_method: WeightMethod = WeightMethod.IC_WEIGHTED
    orthogonal_method: OrthogonalMethod = OrthogonalMethod.NONE
    normalize: bool = True  # 是否标准化因子
    winsorize: bool = True  # 是否去极值
    winsorize_method: str = "mad"  # 去极值方法: mad, std, percentile
    rebalance_freq: str = "M"  # 调仓频率: D, W, M


@dataclass
class FactorTimingConfig:
    """因子择时配置"""
    enable_timing: bool = False
    lookback_window: int = 20  # 择时回看窗口
    ic_threshold: float = 0.02  # IC阈值
    volatility_adjust: bool = True  # 波动率调整
    regime_switch: bool = False  # 市场状态切换


class FactorCombiner:
    """因子组合器

    提供多种因子组合方式：
    1. 等权重组合
    2. IC/IR加权组合
    3. 自定义权重组合
    4. 优化权重组合
    """

    def __init__(self, config: FactorCombinationConfig):
        """初始化因子组合器

        Args:
            config: 因子组合配置
        """
        self.config = config
        self.factor_weights: List[FactorWeight] = []
        self.orthogonalized = False

    def combine_factors(
        self,
        factor_data: pl.DataFrame,
        ic_data: Optional[Dict[str, float]] = None,
        ir_data: Optional[Dict[str, float]] = None
    ) -> pl.DataFrame:
        """组合因子

        Args:
            factor_data: 因子数据，包含 (datetime, symbol, factor1, factor2, ...)
            ic_data: 各因子的IC值（用于加权）
            ir_data: 各因子的IR值（用于加权）

        Returns:
            组合后的因子DataFrame
        """
        logger.info(f"开始组合因子: {self.config.factors}")

        # 1. 预处理：去极值和标准化
        df = self._preprocess_factors(factor_data)

        # 2. 正交化
        if self.config.orthogonal_method != OrthogonalMethod.NONE:
            df = self._orthogonalize_factors(df)
            self.orthogonalized = True

        # 3. 计算权重
        self.factor_weights = self._calculate_weights(df, ic_data, ir_data)

        # 4. 组合因子
        df = self._apply_weights(df)

        logger.info(f"因子组合完成，使用{len(self.factor_weights)}个因子")

        return df

    def _preprocess_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """预处理因子

        包括去极值和标准化。

        Args:
            df: 因子数据

        Returns:
            预处理后的数据
        """
        result = df.clone()

        for factor_name in self.config.factors:
            if factor_name not in df.columns:
                logger.warning(f"因子 {factor_name} 不在数据中")
                continue

            # 去极值
            if self.config.winsorize:
                result = result.with_columns([
                    pl.col(factor_name)
                    .map_batches(lambda s: pl.Series(self._winsorize(s.to_numpy(), self.config.winsorize_method)), return_dtype=pl.Float64)
                    .over(["symbol"])
                    .alias(f"{factor_name}_clean")
                ])
                factor_name = f"{factor_name}_clean"

            # 标准化
            if self.config.normalize:
                result = result.with_columns([
                    pl.col(factor_name)
                    .map_batches(lambda s: pl.Series(self._zscore(s.to_numpy())), return_dtype=pl.Float64)
                    .over(["symbol"])
                    .alias(f"{factor_name}_norm")
                ])
                factor_name = f"{factor_name}_norm"

        return result

    def _winsorize(self, data: np.ndarray, method: str = "mad") -> np.ndarray:
        """去极值

        Args:
            data: 数据
            method: 去极值方法

        Returns:
            去极值后的数据
        """
        if method == "mad":
            # MAD方法：中位数绝对偏差
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            upper = median + 3 * mad
            lower = median - 3 * mad
        elif method == "std":
            # 标准差方法
            mean = np.mean(data)
            std = np.std(data)
            upper = mean + 3 * std
            lower = mean - 3 * std
        elif method == "percentile":
            # 百分位方法
            upper = np.percentile(data, 97.5)
            lower = np.percentile(data, 2.5)
        else:
            return data

        return np.clip(data, lower, upper)

    def _zscore(self, data: np.ndarray) -> np.ndarray:
        """Z-score标准化

        Args:
            data: 数据

        Returns:
            标准化后的数据
        """
        mean = np.mean(data)
        std = np.std(data)
        return (data - mean) / std if std > 0 else data - mean

    def _orthogonalize_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """因子正交化

        Args:
            df: 因子数据

        Returns:
            正交化后的数据
        """
        factors = [f for f in self.config.factors if f in df.columns]

        if len(factors) < 2:
            return df

        if self.config.orthogonal_method == OrthogonalMethod.GRAM_SCHMIDT:
            return self._gram_schmidt_orthogonalize(df, factors)
        elif self.config.orthogonal_method == OrthogonalMethod.PCA:
            return self._pca_orthogonalize(df, factors)
        else:
            return df

    def _gram_schmidt_orthogonalize(
        self,
        df: pl.DataFrame,
        factors: List[str]
    ) -> pl.DataFrame:
        """Gram-Schmidt正交化

        Args:
            df: 因子数据
            factors: 因子列表

        Returns:
            正交化后的数据
        """
        result = df.clone()

        # 获取第一个因子作为基准
        base_factor = factors[0]
        orthogonalized = [base_factor]

        for i, factor in enumerate(factors[1:], 1):
            # 获取数据
            base_data = result[base_factor].to_numpy()
            current_data = result[factor].to_numpy()

            # 计算投影
            projection = np.dot(base_data, current_data) / np.dot(base_data, base_data)
            orthogonal = current_data - projection * base_data

            # 添加新列
            ortho_name = f"{factor}_ortho"
            result = result.with_columns([
                pl.Series(ortho_name, orthogonal)
            ])
            orthogonalized.append(ortho_name)

        return result

    def _pca_orthogonalize(
        self,
        df: pl.DataFrame,
        factors: List[str]
    ) -> pl.DataFrame:
        """PCA正交化

        Args:
            df: 因子数据
            factors: 因子列表

        Returns:
            正交化后的数据
        """
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        # 提取因子数据
        factor_matrix = df.select(factors).to_numpy()

        # 标准化
        scaler = StandardScaler()
        factor_matrix_scaled = scaler.fit_transform(factor_matrix)

        # PCA
        pca = PCA(n_components=len(factors))
        pca_components = pca.fit_transform(factor_matrix_scaled)

        # 添加到DataFrame
        result = df.clone()
        for i in range(len(factors)):
            ortho_name = f"{factors[i]}_pca"
            result = result.with_columns([
                pl.Series(ortho_name, pca_components[:, i])
            ])

        return result

    def _calculate_weights(
        self,
        df: pl.DataFrame,
        ic_data: Optional[Dict[str, float]],
        ir_data: Optional[Dict[str, float]]
    ) -> List[FactorWeight]:
        """计算因子权重

        Args:
            df: 因子数据
            ic_data: IC数据
            ir_data: IR数据

        Returns:
            因子权重列表
        """
        factors = [f for f in self.config.factors if f in df.columns]

        if self.config.weight_method == WeightMethod.EQUAL:
            return self._equal_weights(factors)

        elif self.config.weight_method == WeightMethod.IC_WEIGHTED:
            return self._ic_weights(factors, ic_data)

        elif self.config.weight_method == WeightMethod.IR_WEIGHTED:
            return self._ir_weights(factors, ir_data)

        elif self.config.weight_method == WeightMethod.CUSTOM:
            return self._custom_weights(factors)

        elif self.config.weight_method == WeightMethod.OPTIMIZED:
            return self._optimized_weights(df, factors)

        else:
            return self._equal_weights(factors)

    def _equal_weights(self, factors: List[str]) -> List[FactorWeight]:
        """等权重

        Args:
            factors: 因子列表

        Returns:
            因子权重列表
        """
        weight = 1.0 / len(factors) if factors else 0.0
        return [
            FactorWeight(
                factor_name=f,
                weight=weight
            )
            for f in factors
        ]

    def _ic_weights(
        self,
        factors: List[str],
        ic_data: Optional[Dict[str, float]]
    ) -> List[FactorWeight]:
        """IC加权

        Args:
            factors: 因子列表
            ic_data: IC数据

        Returns:
            因子权重列表
        """
        if not ic_data:
            logger.warning("IC数据未提供，使用等权重")
            return self._equal_weights(factors)

        # 计算绝对IC
        abs_ic = {f: abs(ic_data.get(f, 0.0)) for f in factors}

        # 归一化
        total = sum(abs_ic.values())
        if total == 0:
            return self._equal_weights(factors)

        return [
            FactorWeight(
                factor_name=f,
                weight=abs_ic[f] / total,
                ic=ic_data.get(f, 0.0)
            )
            for f in factors
        ]

    def _ir_weights(
        self,
        factors: List[str],
        ir_data: Optional[Dict[str, float]]
    ) -> List[FactorWeight]:
        """IR加权

        Args:
            factors: 因子列表
            ir_data: IR数据

        Returns:
            因子权重列表
        """
        if not ir_data:
            logger.warning("IR数据未提供，使用等权重")
            return self._equal_weights(factors)

        # 计算绝对IR
        abs_ir = {f: abs(ir_data.get(f, 0.0)) for f in factors}

        # 归一化
        total = sum(abs_ir.values())
        if total == 0:
            return self._equal_weights(factors)

        return [
            FactorWeight(
                factor_name=f,
                weight=abs_ir[f] / total,
                ir=ir_data.get(f, 0.0)
            )
            for f in factors
        ]

    def _custom_weights(self, factors: List[str]) -> List[FactorWeight]:
        """自定义权重

        Args:
            factors: 因子列表

        Returns:
            因子权重列表
        """
        if not self.config.weights:
            logger.warning("自定义权重未提供，使用等权重")
            return self._equal_weights(factors)

        # 验证权重
        total = sum(self.config.weights.get(f, 0.0) for f in factors)

        if total == 0:
            return self._equal_weights(factors)

        # 归一化
        return [
            FactorWeight(
                factor_name=f,
                weight=self.config.weights.get(f, 0.0) / total
            )
            for f in factors
        ]

    def _optimized_weights(
        self,
        df: pl.DataFrame,
        factors: List[str]
    ) -> List[FactorWeight]:
        """优化权重（最大化夏普比率）

        Args:
            df: 因子数据
            factors: 因子列表

        Returns:
            因子权重列表
        """
        try:
            from scipy.optimize import minimize

            # 计算因子协方差矩阵
            factor_matrix = df.select(factors).fill_null(0).to_numpy()

            # 计算均值和协方差
            mean_returns = np.mean(factor_matrix, axis=0)
            cov_matrix = np.cov(factor_matrix.T)

            # 优化目标：最小化波动率（或最大化夏普比率）
            n = len(factors)

            def portfolio_volatility(weights):
                return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

            # 约束条件
            constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
            bounds = tuple((0, 1) for _ in range(n))

            # 初始值
            x0 = np.array([1.0 / n] * n)

            # 优化
            result = minimize(
                portfolio_volatility,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                return [
                    FactorWeight(
                        factor_name=factors[i],
                        weight=float(result.x[i])
                    )
                    for i in range(n)
                ]
            else:
                logger.warning("优化失败，使用等权重")
                return self._equal_weights(factors)

        except Exception as e:
            logger.warning(f"优化权重计算失败: {e}，使用等权重")
            return self._equal_weights(factors)

    def _apply_weights(self, df: pl.DataFrame) -> pl.DataFrame:
        """应用权重组合因子

        Args:
            df: 因子数据

        Returns:
            组合后的数据
        """
        # 计算组合因子
        weighted_sums = []
        for fw in self.factor_weights:
            factor_col = fw.factor_name
            if self.orthogonalized:
                # 如果已正交化，查找正交化后的列名
                if f"{factor_col}_ortho" in df.columns:
                    factor_col = f"{factor_col}_ortho"
                elif f"{factor_col}_pca" in df.columns:
                    factor_col = f"{factor_col}_pca"

            if factor_col in df.columns:
                weighted_sums.append(pl.col(factor_col) * fw.weight)

        if weighted_sums:
            df = df.with_columns([
                sum(weighted_sums).alias("combined_factor")
            ])

        return df

    def get_weights(self) -> List[FactorWeight]:
        """获取当前因子权重

        Returns:
            因子权重列表
        """
        return self.factor_weights


class FactorTimer:
    """因子择时器

    根据因子表现动态调整因子权重。
    """

    def __init__(self, config: FactorTimingConfig):
        """初始化因子择时器

        Args:
            config: 择时配置
        """
        self.config = config
        self.ic_history: Dict[str, List[float]] = {}

    def update_ic(self, factor_name: str, ic: float) -> None:
        """更新IC历史

        Args:
            factor_name: 因子名称
            ic: IC值
        """
        if factor_name not in self.ic_history:
            self.ic_history[factor_name] = []

        self.ic_history[factor_name].append(ic)

        # 保持窗口长度
        if len(self.ic_history[factor_name]) > self.config.lookback_window:
            self.ic_history[factor_name].pop(0)

    def get_timing_weights(self, factors: List[str]) -> Dict[str, float]:
        """获取择时权重

        Args:
            factors: 因子列表

        Returns:
            因子权重字典
        """
        if not self.config.enable_timing:
            return {f: 1.0 / len(factors) for f in factors}

        timing_weights = {}

        for factor in factors:
            if factor not in self.ic_history or not self.ic_history[factor]:
                timing_weights[factor] = 0.0
                continue

            # 计算平均IC
            avg_ic = np.mean(self.ic_history[factor][-self.config.lookback_window:])

            # IC阈值过滤
            if abs(avg_ic) < self.config.ic_threshold:
                timing_weights[factor] = 0.0
            else:
                timing_weights[factor] = avg_ic

        # 归一化
        total = sum(abs(w) for w in timing_weights.values())
        if total > 0:
            timing_weights = {
                f: abs(w) / total for f, w in timing_weights.items()
            }
        else:
            timing_weights = {f: 1.0 / len(factors) for f in factors}

        return timing_weights


def create_factor_combiner(
    factors: List[str],
    weight_method: Union[str, WeightMethod] = WeightMethod.IC_WEIGHTED,
    orthogonal_method: Union[str, OrthogonalMethod] = OrthogonalMethod.NONE,
    custom_weights: Optional[Dict[str, float]] = None
) -> FactorCombiner:
    """创建因子组合器

    Args:
        factors: 因子列表
        weight_method: 权重方法
        orthogonal_method: 正交化方法
        custom_weights: 自定义权重

    Returns:
        因子组合器实例
    """
    if isinstance(weight_method, str):
        weight_method = WeightMethod(weight_method)

    if isinstance(orthogonal_method, str):
        orthogonal_method = OrthogonalMethod(orthogonal_method)

    config = FactorCombinationConfig(
        factors=factors,
        weights=custom_weights,
        weight_method=weight_method,
        orthogonal_method=orthogonal_method
    )

    return FactorCombiner(config)


__all__ = [
    "FactorCombiner",
    "FactorTimer",
    "FactorCombinationConfig",
    "FactorTimingConfig",
    "FactorWeight",
    "WeightMethod",
    "OrthogonalMethod",
    "create_factor_combiner",
]
