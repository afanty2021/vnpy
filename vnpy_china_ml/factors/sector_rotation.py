"""
板块轮动因子模块

提供行业/板块轮动相关的因子计算功能。

数据格式说明：
    本模块使用 pandas 进行数据处理。vnpy_china_ml 的 dataset/、backtesting/、
    gui_engine.py 等模块使用 polars。跨模块传递 DataFrame 时需要进行转换：
        - pandas → polars:  pl.from_pandas(df)
        - polars → pandas:  df.to_pandas()
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .base import BaseFactor
from ..utils.types import FactorType


class SectorRotationFactor(BaseFactor):
    """板块轮动因子

    板块轮动因子是基于不同行业/板块相对表现计算的因子。
    A股市场存在明显的行业轮动特征，通过捕捉板块间的
    相对强弱变化，可以预测未来的热点转换方向。

    主要因子包括：
    - 板块动量：过去N天板块的累计收益率
    - 相对强弱：板块相对于市场基准的超额收益
    - 板块换手率：板块内股票的换手率情况
    - 资金流向：板块的资金净流入情况

    Attributes:
        name: 因子名称，默认"sector_rotation"
        factor_type: 因子类型，固定为FactorType.SECTOR_ROTATION

    Example:
        >>> factor = SectorRotationFactor()
        >>> # 假设 data 包含板块数据
        >>> result = factor.calculate(data)
    """

    def __init__(self, lookback_days: int = 20) -> None:
        """初始化板块轮动因子

        Args:
            lookback_days: 回看天数，默认20天
        """
        super().__init__(
            name="sector_rotation",
            factor_type=FactorType.SECTOR_ROTATION,
            lookback_days=lookback_days
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算板块轮动综合因子

        综合考虑动量、相对强弱等因素计算综合因子值。

        Args:
            data: 包含板块数据的DataFrame，应包含以下列：
                - sector: 板块名称
                - datetime: 交易日期
                - return: 板块收益率
                - market_return: 市场基准收益率
                - volume: 成交量

        Returns:
            pd.Series: 板块轮动综合因子值

        Raises:
            ValueError: 当数据为空或格式不正确时
        """
        if not self.validate_data(data):
            raise ValueError("数据为空或格式不正确")

        # 验证必要列
        required_cols = ["sector", "datetime"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"缺少必要列: {col}")

        # 计算综合因子（简化实现）
        result = pd.Series(
            np.zeros(len(data)),
            index=data.index,
            name="sector_rotation_factor"
        )

        # 如果有收益率数据，计算动量因子
        if "return" in data.columns:
            momentum = self.get_momentum(data)
            momentum_normalized = self._normalize_by_sector(momentum)
            result += momentum_normalized * 0.4

        # 如果有市场收益率数据，计算相对强弱
        if "return" in data.columns and "market_return" in data.columns:
            relative_strength = self.get_relative_strength(data)
            relative_normalized = self._normalize_by_sector(relative_strength)
            result += relative_normalized * 0.4

        # 如果有成交量数据，计算换手率因子
        if "volume" in data.columns and "float_share" in data.columns:
            turnover = data["volume"] / (data["float_share"] + 1e-8)
            turnover_normalized = self._normalize_by_sector(turnover)
            result += turnover_normalized * 0.2

        return result

    def get_momentum(self, data: pd.DataFrame) -> pd.Series:
        """计算板块动量因子

        动量 = 过去N天板块的累计收益率
        动量效应表明过去表现好的板块未来可能继续表现好。

        Args:
            data: 包含板块收益率数据的DataFrame，应包含：
                - sector: 板块名称
                - datetime: 交易日期
                - return: 日收益率

        Returns:
            pd.Series: 板块动量因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="momentum")

        if "return" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="momentum")

        # 按板块分组计算滚动累计收益
        momentum = data.groupby("sector")["return"].transform(
            lambda x: x.rolling(window=self.lookback_days, min_periods=1).sum()
        )

        return pd.Series(momentum.values, index=data.index, name="momentum")

    def get_relative_strength(self, data: pd.DataFrame) -> pd.Series:
        """计算相对强弱因子

        相对强弱 = 板块收益率 - 市场基准收益率
        正值表示板块跑赢市场，负值表示跑输市场。

        Args:
            data: 包含板块和市场收益率数据的DataFrame，应包含：
                - sector: 板块名称
                - return: 板块收益率
                - market_return: 市场基准收益率

        Returns:
            pd.Series: 相对强弱因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="relative_strength")

        if "return" not in data.columns or "market_return" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="relative_strength")

        relative_strength = data["return"] - data["market_return"]
        return pd.Series(relative_strength.values, index=data.index, name="relative_strength")

    def get_sector_turnover(self, data: pd.DataFrame) -> pd.Series:
        """计算板块换手率因子

        板块换手率 = 板块内股票换手率的加权平均
        高换手率通常表示板块交易活跃。

        Args:
            data: 包含板块和换手率数据的DataFrame，应包含：
                - sector: 板块名称
                - volume: 成交量
                - float_share: 流通股本

        Returns:
            pd.Series: 板块换手率因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="sector_turnover")

        if "volume" not in data.columns or "float_share" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="sector_turnover")

        # 计算单只股票换手率
        turnover = data["volume"] / (data["float_share"] + 1e-8)

        # 按板块分组计算平均换手率
        sector_turnover = data.groupby("sector")["volume"].transform(
            lambda x: x / (data.loc[x.index, "float_share"] + 1e-8)
        )

        return pd.Series(sector_turnover.values, index=data.index, name="sector_turnover")

    def get_sector_flow(self, data: pd.DataFrame) -> pd.Series:
        """计算板块资金流向因子

        板块资金流向 = 板块内股票的资金净流入之和
        反映板块的资金关注度。

        Args:
            data: 包含板块和资金流数据的DataFrame，应包含：
                - sector: 板块名称
                - net_inflow: 资金净流入

        Returns:
            pd.Series: 板块资金流向因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="sector_flow")

        if "net_inflow" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="sector_flow")

        # 按板块分组计算累计资金流
        sector_flow = data.groupby("sector")["net_inflow"].transform(
            lambda x: x.rolling(window=self.lookback_days, min_periods=1).sum()
        )

        return pd.Series(sector_flow.values, index=data.index, name="sector_flow")

    def get_momentum_reversal(self, data: pd.DataFrame, short_period: int = 5, long_period: int = 20) -> pd.Series:
        """计算动量反转因子

        动量反转 = 短期动量 - 长期动量
        正值表示短期动量强于长期，可能存在反转风险。

        Args:
            data: 包含板块收益率数据的DataFrame，应包含：
                - sector: 板块名称
                - datetime: 交易日期
                - return: 日收益率
            short_period: 短期动量周期，默认5天
            long_period: 长期动量周期，默认20天

        Returns:
            pd.Series: 动量反转因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="momentum_reversal")

        if "return" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="momentum_reversal")

        # 计算短期动量
        short_momentum = data.groupby("sector")["return"].transform(
            lambda x: x.rolling(window=short_period, min_periods=1).sum()
        )

        # 计算长期动量
        long_momentum = data.groupby("sector")["return"].transform(
            lambda x: x.rolling(window=long_period, min_periods=1).sum()
        )

        # 动量反转 = 短期 - 长期
        momentum_reversal = short_momentum - long_momentum

        return pd.Series(momentum_reversal.values, index=data.index, name="momentum_reversal")

    def get_leading_lagging(self, data: pd.DataFrame) -> pd.Series:
        """计算领先滞后因子

        领先滞后 = 板块当日收益相对于未来N天收益的相关性
        正值表示板块可能领先市场，负值表示可能滞后。

        Args:
            data: 包含板块收益率数据的DataFrame，应包含：
                - sector: 板块名称
                - return: 日收益率

        Returns:
            pd.Series: 领先滞后因子值（简化实现，返回当期收益率）
        """
        if not self.validate_data(data):
            return pd.Series([], name="leading_lagging")

        if "return" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="leading_lagging")

        # 简化实现：返回当期收益率作为领先滞后的近似
        # 实际实现中需要计算与未来收益的相关性
        return pd.Series(data["return"].values, index=data.index, name="leading_lagging")

    def _normalize_by_sector(self, factor: pd.Series) -> pd.Series:
        """按板块归一化因子值

        对每个板块内的因子值进行z-score标准化。

        Args:
            factor: 原始因子值

        Returns:
            pd.Series: 归一化后的因子值
        """
        # 按板块分组进行标准化
        result = pd.Series(
            np.zeros(len(factor)),
            index=factor.index,
            name=f"{factor.name}_normalized"
        )

        # 简单的组内标准化
        for sector in factor.get("sector", pd.Series([""] * len(factor))).unique():
            mask = factor.index.isin(
                factor[factor.get("sector", pd.Series([""] * len(factor))) == sector].index
            )
            if mask.any():
                sector_values = factor[mask]
                mean = sector_values.mean()
                std = sector_values.std()
                if std > 0 and not pd.isna(std):
                    result[mask] = (sector_values - mean) / std

        return result

    def _normalize_factor(self, factor: pd.Series) -> pd.Series:
        """归一化因子值到[-1, 1]区间

        使用z-score标准化后映射到[-1, 1]区间。

        Args:
            factor: 原始因子值

        Returns:
            pd.Series: 归一化后的因子值
        """
        mean = factor.mean()
        std = factor.std()

        if std == 0 or pd.isna(std):
            return pd.Series(np.zeros(len(factor)), index=factor.index)

        z_score = (factor - mean) / std
        # 映射到[-1, 1]
        normalized = 2 / (1 + np.exp(-z_score)) - 1
        return normalized

    def get_required_columns(self) -> List[str]:
        """获取板块轮动因子所需的数据列

        Returns:
            List[str]: 所需列名列表
        """
        return [
            "sector",
            "symbol",
            "datetime",
            "return",
            "market_return",
            "volume",
            "float_share",
            "net_inflow"
        ]
