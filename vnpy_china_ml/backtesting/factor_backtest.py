"""因子有效性回测模块

提供因子有效性评估的回测功能，包括IC、RankIC、IR等指标计算，
以及分层回测分析。
"""

import polars as pl
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging

try:
    from vnpy_china_data import ChinaDataService
    CHINA_DATA_AVAILABLE = True
except ImportError:
    CHINA_DATA_AVAILABLE = False
    ChinaDataService = None

logger = logging.getLogger(__name__)


@dataclass
class FactorIcResult:
    """因子IC值结果"""
    date: date
    ic: float
    rank_ic: float
    sample_count: int


@dataclass
class FactorIcStats:
    """因子IC统计"""
    ic_mean: float
    ic_std: float
    ic_ir: float  # Information Ratio = ic_mean / ic_std
    rank_ic_mean: float
    rank_ic_std: float
    rank_ic_ir: float
    ic_positive_ratio: float  # IC > 0 的比例
    ic_absolute_mean: float  # |IC| 的均值
    win_rate: float  # 方向正确率


@dataclass
class LayerBacktestResult:
    """分层回测结果"""
    layer: int  # 层数（1-5）
    total_return: float  # 总收益率
    annual_return: float  # 年化收益率
    volatility: float  # 波动率
    sharpe_ratio: float  # 夏普比率
    max_drawdown: float  # 最大回撤
    win_rate: float  # 胜率
    avg_daily_return: float  # 平均日收益


@dataclass
class FactorBacktestReport:
    """因子回测报告"""
    factor_name: str
    start_date: date
    end_date: date
    ic_stats: FactorIcStats
    ic_series: List[FactorIcResult]
    layer_results: List[LayerBacktestResult]
    summary: Dict[str, float]


class FactorBacktester:
    """因子回测器

    用于评估因子的有效性，包括：
    1. IC/RankIC/IR分析
    2. 分层回测（五分位）
    3. 换手率分析
    4. 因子衰减分析
    """

    def __init__(
        self,
        data_service: Optional[ChinaDataService] = None
    ):
        """初始化回测器

        Args:
            data_service: 数据服务实例
        """
        self.data_service = data_service

        if not CHINA_DATA_AVAILABLE and data_service:
            logger.warning("ChinaDataService不可用，部分回测功能受限")

    def backtest_factor(
        self,
        factor_data: pl.DataFrame,
        price_data: pl.DataFrame,
        start_date: date,
        end_date: date,
        forward_days: int = 5,
        n_layers: int = 5
    ) -> FactorBacktestReport:
        """回测因子有效性

        Args:
            factor_data: 因子数据，包含 (datetime, symbol, factor_value)
            price_data: 价格数据，包含 (datetime, symbol, close_price)
            start_date: 回测开始日期
            end_date: 回测结束日期
            forward_days: 预测天数
            n_layers: 分层数量

        Returns:
            因子回测报告
        """
        logger.info(f"开始回测因子: {start_date} 至 {end_date}")

        # 1. 计算未来收益率
        df = self._calculate_forward_returns(
            price_data, forward_days
        )

        # 2. 合并因子数据
        df = df.join(
            factor_data,
            on=["datetime", "symbol"],
            how="inner"
        )

        if len(df) == 0:
            logger.warning("合并后数据为空")
            return self._create_empty_report(start_date, end_date)

        # 3. 计算IC序列
        ic_series = self._calculate_ic_series(
            df, start_date, end_date
        )

        # 4. 计算IC统计
        ic_stats = self._calculate_ic_stats(ic_series)

        # 5. 分层回测
        layer_results = self._layer_backtest(
            df, start_date, end_date, n_layers
        )

        # 6. 生成报告摘要
        summary = self._generate_summary(ic_stats, layer_results)

        report = FactorBacktestReport(
            factor_name="factor",
            start_date=start_date,
            end_date=end_date,
            ic_stats=ic_stats,
            ic_series=ic_series,
            layer_results=layer_results,
            summary=summary
        )

        logger.info(f"回测完成: IC={ic_stats.ic_mean:.4f}, IR={ic_stats.ic_ir:.4f}")

        return report

    def _calculate_forward_returns(
        self,
        price_data: pl.DataFrame,
        forward_days: int
    ) -> pl.DataFrame:
        """计算未来收益率

        Args:
            price_data: 价格数据
            forward_days: 前瞻天数

        Returns:
            包含未来收益率的数据
        """
        # 确保按symbol和datetime排序
        df = price_data.sort(["symbol", "datetime"])

        # 计算未来收益率
        df = df.with_columns([
            pl.col("close_price")
            .shift(-forward_days)
            .over(["symbol"])
            .alias("future_close")
        ])

        # 计算收益率
        df = df.with_columns([
            ((pl.col("future_close") - pl.col("close_price")) / pl.col("close_price"))
            .alias("forward_return")
        ])

        # 过滤无效数据
        df = df.filter(
            pl.col("future_close").is_not_null()
        )

        return df

    def _calculate_ic_series(
        self,
        df: pl.DataFrame,
        start_date: date,
        end_date: date
    ) -> List[FactorIcResult]:
        """计算IC序列

        Args:
            df: 数据DataFrame
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            IC值序列
        """
        ic_series = []

        # 获取所有日期
        dates = df["datetime"].unique().to_list()

        for dt in dates:
            dt_date = dt.date() if isinstance(dt, datetime) else dt

            if dt_date < start_date or dt_date > end_date:
                continue

            # 获取当日数据
            daily_df = df.filter(pl.col("datetime") == dt)

            if len(daily_df) < 10:  # 样本太少
                continue

            # 计算IC（Pearson相关系数）
            factor_values = daily_df["factor_value"].to_numpy()
            returns = daily_df["forward_return"].to_numpy()

            # 移除无效值
            valid_mask = np.isfinite(factor_values) & np.isfinite(returns)
            factor_values = factor_values[valid_mask]
            returns = returns[valid_mask]

            if len(factor_values) < 5:
                continue

            # Pearson IC
            ic = float(np.corrcoef(factor_values, returns)[0, 1])

            # Rank IC (Spearman相关系数)
            from scipy.stats import spearmanr
            rank_ic, _ = spearmanr(factor_values, returns)

            ic_series.append(FactorIcResult(
                date=dt_date,
                ic=ic,
                rank_ic=rank_ic,
                sample_count=len(factor_values)
            ))

        return ic_series

    def _calculate_ic_stats(self, ic_series: List[FactorIcResult]) -> FactorIcStats:
        """计算IC统计量

        Args:
            ic_series: IC序列

        Returns:
            IC统计量
        """
        if not ic_series:
            return FactorIcStats(
                ic_mean=0.0, ic_std=0.0, ic_ir=0.0,
                rank_ic_mean=0.0, rank_ic_std=0.0, rank_ic_ir=0.0,
                ic_positive_ratio=0.0, ic_absolute_mean=0.0, win_rate=0.0
            )

        ic_values = [r.ic for r in ic_series if np.isfinite(r.ic)]
        rank_ic_values = [r.rank_ic for r in ic_series if np.isfinite(r.rank_ic)]

        ic_mean = np.mean(ic_values) if ic_values else 0.0
        ic_std = np.std(ic_values) if ic_values else 0.0
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0

        rank_ic_mean = np.mean(rank_ic_values) if rank_ic_values else 0.0
        rank_ic_std = np.std(rank_ic_values) if rank_ic_values else 0.0
        rank_ic_ir = rank_ic_mean / rank_ic_std if rank_ic_std > 0 else 0.0

        ic_positive_ratio = np.mean([1.0 if ic > 0 else 0.0 for ic in ic_values]) if ic_values else 0.0
        ic_absolute_mean = np.mean([abs(ic) for ic in ic_values]) if ic_values else 0.0

        # 计算胜率（假设IC绝对值>0.02为正确预测）
        win_rate = np.mean([1.0 if abs(ic) > 0.02 else 0.0 for ic in ic_values]) if ic_values else 0.0

        return FactorIcStats(
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            rank_ic_mean=rank_ic_mean,
            rank_ic_std=rank_ic_std,
            rank_ic_ir=rank_ic_ir,
            ic_positive_ratio=ic_positive_ratio,
            ic_absolute_mean=ic_absolute_mean,
            win_rate=win_rate
        )

    def _layer_backtest(
        self,
        df: pl.DataFrame,
        start_date: date,
        end_date: date,
        n_layers: int
    ) -> List[LayerBacktestResult]:
        """分层回测

        Args:
            df: 数据DataFrame
            start_date: 开始日期
            end_date: 结束日期
            n_layers: 分层数量

        Returns:
            分层回测结果列表
        """
        layer_results = []

        for layer in range(1, n_layers + 1):
            # 按日期分组，计算每层的分位数
            quantile = layer / n_layers

            # 计算每层的数据
            layer_df = df.group_by("datetime").map_groups(
                lambda group: self._get_layer_data(group, layer, n_layers)
            )

            if len(layer_df) == 0:
                continue

            # 计算收益指标
            returns = layer_df["forward_return"].to_numpy()

            total_return = float(np.mean(returns))
            volatility = float(np.std(returns))
            sharpe_ratio = total_return / volatility if volatility > 0 else 0.0

            # 最大回撤：按 datetime 排序后基于累计权益曲线的 peak-to-trough
            # （原 cumsum(无序跨日跨股 returns) 的 max-min 非真实回撤，数值无意义）
            dates = layer_df["datetime"].to_numpy()
            sort_idx = np.argsort(dates)
            cum_returns = np.cumsum(returns[sort_idx])
            running_max = np.maximum.accumulate(cum_returns)
            drawdowns = cum_returns - running_max
            max_drawdown = float(abs(drawdowns.min())) if drawdowns.size > 0 else 0.0

            # 计算胜率
            win_rate = float(np.mean(returns > 0))

            # 年化收益（假设252个交易日）
            annual_return = total_return * 252

            layer_results.append(LayerBacktestResult(
                layer=layer,
                total_return=total_return,
                annual_return=annual_return,
                volatility=volatility * np.sqrt(252),
                sharpe_ratio=sharpe_ratio * np.sqrt(252),
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                avg_daily_return=total_return
            ))

        return layer_results

    def _get_layer_data(
        self,
        group: pl.DataFrame,
        layer: int,
        n_layers: int
    ) -> pl.DataFrame:
        """获取指定层数的数据

        Args:
            group: 分组数据
            layer: 层数
            n_layers: 总层数

        Returns:
            该层的数据
        """
        # 计算分位数边界
        lower_quantile = (layer - 1) / n_layers
        upper_quantile = layer / n_layers

        # 按因子值排序并取分位数
        factor_values = group["factor_value"].to_numpy()

        # 计算分位数
        try:
            lower_bound = np.quantile(factor_values, lower_quantile)
            upper_bound = np.quantile(factor_values, upper_quantile)

            # 过滤该层数据
            if layer == n_layers:
                # 最后一层包含上界
                mask = (factor_values >= lower_bound)
            else:
                mask = (factor_values >= lower_bound) & (factor_values < upper_bound)

            return group.filter(pl.Series(mask))

        except Exception:
            return group.head(0)

    def _generate_summary(
        self,
        ic_stats: FactorIcStats,
        layer_results: List[LayerBacktestResult]
    ) -> Dict[str, float]:
        """生成报告摘要

        Args:
            ic_stats: IC统计
            layer_results: 分层结果

        Returns:
            摘要字典
        """
        summary = {
            "ic_mean": ic_stats.ic_mean,
            "ic_ir": ic_stats.ic_ir,
            "rank_ic_mean": ic_stats.rank_ic_mean,
            "win_rate": ic_stats.win_rate,
        }

        # 添加分层收益差异
        if len(layer_results) >= 2:
            # 多空收益 = 做多（最高分位 layer_results[-1]）- 做空（最低分位 layer_results[0]）
            long_short = layer_results[-1].total_return - layer_results[0].total_return
            summary["long_short_return"] = long_short

        return summary

    def _create_empty_report(
        self,
        start_date: date,
        end_date: date
    ) -> FactorBacktestReport:
        """创建空报告

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            空报告
        """
        empty_stats = FactorIcStats(
            ic_mean=0.0, ic_std=0.0, ic_ir=0.0,
            rank_ic_mean=0.0, rank_ic_std=0.0, rank_ic_ir=0.0,
            ic_positive_ratio=0.0, ic_absolute_mean=0.0, win_rate=0.0
        )

        return FactorBacktestReport(
            factor_name="",
            start_date=start_date,
            end_date=end_date,
            ic_stats=empty_stats,
            ic_series=[],
            layer_results=[],
            summary={}
        )

    def calculate_turnover(
        self,
        factor_data: pl.DataFrame,
        n_layers: int = 5
    ) -> Dict[int, float]:
        """计算换手率

        Args:
            factor_data: 因子数据
            n_layers: 分层数量

        Returns:
            每层的换手率
        """
        # 按日期排序
        df = factor_data.sort("datetime")

        # 获取所有日期
        dates = df["datetime"].unique().to_list()

        turnover_rates = {i: [] for i in range(1, n_layers + 1)}

        for i in range(len(dates) - 1):
            current_date = dates[i]
            next_date = dates[i + 1]

            current_df = df.filter(pl.col("datetime") == current_date)
            next_df = df.filter(pl.col("datetime") == next_date)

            # 为每个日期计算分位数
            for layer in range(1, n_layers + 1):
                current_layer = self._get_layer_data(current_df, layer, n_layers)
                next_layer = self._get_layer_data(next_df, layer, n_layers)

                if len(current_layer) == 0:
                    continue

                # 计算换手率
                current_symbols = set(current_layer["symbol"].to_list())
                next_symbols = set(next_layer["symbol"].to_list())

                stayed = current_symbols & next_symbols
                turnover = 1 - len(stayed) / len(current_symbols) if current_symbols else 0

                turnover_rates[layer].append(turnover)

        # 计算平均换手率
        avg_turnover = {
            layer: np.mean(rates) if rates else 0.0
            for layer, rates in turnover_rates.items()
        }

        return avg_turnover

    def calculate_factor_decay(
        self,
        factor_data: pl.DataFrame,
        price_data: pl.DataFrame,
        max_days: int = 20
    ) -> Dict[int, float]:
        """计算因子衰减

        分析因子在不同前瞻天数下的IC值变化。

        Args:
            factor_data: 因子数据
            price_data: 价格数据
            max_days: 最大前瞻天数

        Returns:
            不同天数下的IC值
        """
        decay_results = {}

        for days in range(1, max_days + 1):
            # 计算该前瞻天数下的IC
            df = self._calculate_forward_returns(price_data, days)
            df = df.join(factor_data, on=["datetime", "symbol"], how="inner")

            if len(df) == 0:
                decay_results[days] = 0.0
                continue

            # 计算IC
            factor_values = df["factor_value"].to_numpy()
            returns = df["forward_return"].to_numpy()

            valid_mask = np.isfinite(factor_values) & np.isfinite(returns)
            factor_values = factor_values[valid_mask]
            returns = returns[valid_mask]

            if len(factor_values) < 5:
                decay_results[days] = 0.0
                continue

            ic = float(np.corrcoef(factor_values, returns)[0, 1])
            decay_results[days] = ic

        return decay_results


def create_factor_backtester(
    data_service: Optional[ChinaDataService] = None
) -> FactorBacktester:
    """创建因子回测器

    Args:
        data_service: 数据服务实例

    Returns:
        因子回测器实例
    """
    return FactorBacktester(data_service)


__all__ = [
    "FactorBacktester",
    "FactorIcResult",
    "FactorIcStats",
    "LayerBacktestResult",
    "FactorBacktestReport",
    "create_factor_backtester",
]
