"""
北向资金因子模块

提供北向资金（沪股通/深股通）相关的因子计算功能。

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


class NorthboundFactor(BaseFactor):
    """北向资金因子

    北向资金因子是基于沪股通和深股通（统称北向资金）流向数据计算的因子。
    北向资金是境外投资者通过沪股通和深股通投资A股市场的资金，
    通常被视为"聪明钱"，对市场走势有一定领先作用。

    主要因子包括：
    - 北向资金净流入：沪股通和深股通的净买入金额
    - 持股变化：北向资金持股数量或市值的变化
    - 资金流向强度：净流入与成交额的比值
    - 持仓集中度：北向资金持仓的行业/个股集中度

    Attributes:
        name: 因子名称，默认"northbound"
        factor_type: 因子类型，固定为FactorType.NORTHBOUND

    Example:
        >>> factor = NorthboundFactor()
        >>> # 假设 data 包含北向资金数据
        >>> result = factor.calculate(data)
    """

    def __init__(self, lookback_days: int = 20) -> None:
        """初始化北向资金因子

        Args:
            lookback_days: 回看天数，默认20天
        """
        super().__init__(
            name="northbound",
            factor_type=FactorType.NORTHBOUND,
            lookback_days=lookback_days
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算北向资金综合因子

        综合考虑净流入、持股变化等因素计算综合因子值。

        Args:
            data: 包含北向资金数据的DataFrame，应包含以下列：
                - symbol: 股票代码
                - datetime: 交易日期
                - net_inflow: 北向资金净流入金额
                - holding_change: 持股变化比例
                - turnover: 成交额

        Returns:
            pd.Series: 北向资金综合因子值

        Raises:
            ValueError: 当数据为空或格式不正确时
        """
        if not self.validate_data(data):
            raise ValueError("数据为空或格式不正确")

        # 验证必要列
        required_cols = ["symbol", "datetime"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"缺少必要列: {col}")

        # 计算综合因子（简化实现）
        result = pd.Series(
            np.zeros(len(data)),
            index=data.index,
            name="northbound_factor"
        )

        # 如果有净流入数据，则纳入计算
        if "net_inflow" in data.columns:
            inflow_normalized = self._normalize_factor(data["net_inflow"])
            result += inflow_normalized * 0.5

        # 如果有持股变化数据，则纳入计算
        if "holding_change" in data.columns:
            change_normalized = self._normalize_factor(data["holding_change"])
            result += change_normalized * 0.3

        # 如果有成交额数据，则计算资金流向强度
        if "net_inflow" in data.columns and "turnover" in data.columns:
            # 避免除零
            flow_strength = data["net_inflow"] / (data["turnover"] + 1e-8)
            strength_normalized = self._normalize_factor(flow_strength)
            result += strength_normalized * 0.2

        return result

    def get_net_inflow(self, data: pd.DataFrame) -> pd.Series:
        """计算北向资金净流入因子

        净流入 = 买入成交额 - 卖出成交额
        正值表示净流入，负值表示净流出。

        Args:
            data: 包含北向资金交易数据的DataFrame，应包含：
                - buy_amount: 买入成交额
                - sell_amount: 卖出成交额

        Returns:
            pd.Series: 北向资金净流入因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="net_inflow")

        if "buy_amount" not in data.columns or "sell_amount" not in data.columns:
            # 尝试使用综合的 net_inflow 列
            if "net_inflow" in data.columns:
                return pd.Series(
                    data["net_inflow"].values,
                    index=data.index,
                    name="net_inflow"
                )
            return pd.Series(np.zeros(len(data)), index=data.index, name="net_inflow")

        net_inflow = data["buy_amount"] - data["sell_amount"]
        return pd.Series(net_inflow.values, index=data.index, name="net_inflow")

    def get_holding_change(self, data: pd.DataFrame) -> pd.Series:
        """计算持股变化因子

        持股变化 = (当前持股数量 - 上期持股数量) / 上期持股数量
        反映北向资金对股票的增持或减持力度。

        Args:
            data: 包含持股数据的DataFrame，应包含：
                - current_holding: 当前持股数量
                - previous_holding: 上期持股数量

        Returns:
            pd.Series: 持股变化因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="holding_change")

        if "current_holding" not in data.columns or "previous_holding" not in data.columns:
            # 尝试使用综合的 holding_change 列
            if "holding_change" in data.columns:
                return pd.Series(
                    data["holding_change"].values,
                    index=data.index,
                    name="holding_change"
                )
            return pd.Series(np.zeros(len(data)), index=data.index, name="holding_change")

        # 避免除零
        change = (data["current_holding"] - data["previous_holding"]) / (
            data["previous_holding"] + 1e-8
        )
        return pd.Series(change.values, index=data.index, name="holding_change")

    def get_flow_strength(self, data: pd.DataFrame) -> pd.Series:
        """计算资金流向强度因子

        资金流向强度 = 净流入 / 成交额
        反映资金流入相对于交易活跃度的强度。

        Args:
            data: 包含资金流和成交额数据的DataFrame，应包含：
                - net_inflow: 净流入金额
                - turnover: 成交额

        Returns:
            pd.Series: 资金流向强度因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="flow_strength")

        if "net_inflow" not in data.columns or "turnover" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="flow_strength")

        # 避免除零
        flow_strength = data["net_inflow"] / (data["turnover"] + 1e-8)
        return pd.Series(flow_strength.values, index=data.index, name="flow_strength")

    def get_cumulative_inflow(self, data: pd.DataFrame, days: int = 5) -> pd.Series:
        """计算累计净流入因子

        统计过去N个交易日的累计净流入金额，
        反映北向资金的中期趋势。

        Args:
            data: 包含日期和净流入数据的DataFrame，应包含：
                - datetime: 交易日期
                - net_inflow: 净流入金额
            days: 累计天数窗口

        Returns:
            pd.Series: 累计净流入因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="cumulative_inflow")

        if "datetime" not in data.columns or "net_inflow" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="cumulative_inflow")

        # 按股票分组计算累计净流入
        result = data.groupby("symbol")["net_inflow"].transform(
            lambda x: x.rolling(window=days, min_periods=1).sum()
        )

        return pd.Series(result.values, index=data.index, name="cumulative_inflow")

    def get_inflow_momentum(self, data: pd.DataFrame) -> pd.Series:
        """计算净流入动量因子

        净流入动量 = 当日净流入 / 过去N日平均净流入
        反映北向资金流入的加速或减速情况。

        Args:
            data: 包含日期和净流入数据的DataFrame，应包含：
                - datetime: 交易日期
                - net_inflow: 净流入金额

        Returns:
            pd.Series: 净流入动量因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="inflow_momentum")

        if "datetime" not in data.columns or "net_inflow" not in data.columns:
            return pd.Series(np.ones(len(data)), index=data.index, name="inflow_momentum")

        # 计算过去N天的平均净流入
        mean_inflow = data.groupby("symbol")["net_inflow"].transform(
            lambda x: x.shift(1).rolling(window=self.lookback_days, min_periods=1).mean()
        )

        # 避免除零
        momentum = data["net_inflow"] / (mean_inflow + 1e-8)

        return pd.Series(momentum.values, index=data.index, name="inflow_momentum")

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
        """获取北向资金因子所需的数据列

        Returns:
            List[str]: 所需列名列表
        """
        return [
            "symbol",
            "datetime",
            "net_inflow",
            "buy_amount",
            "sell_amount",
            "current_holding",
            "previous_holding",
            "turnover"
        ]
