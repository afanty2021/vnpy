"""
龙虎榜因子模块

提供龙虎榜相关的因子计算功能，包括机构净买入、换手率等。

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


class DragonTigerFactor(BaseFactor):
    """龙虎榜因子

    龙虎榜因子是基于交易所每日公布的龙虎榜数据计算的因子。
    龙虎榜展示了当日涨幅波动较大股票的买卖前五名营业部信息，
    对于跟踪机构动向和市场情绪具有重要参考价值。

    主要因子包括：
    - 机构净买入：机构买入金额与卖出金额的差额
    - 龙虎榜换手率：龙虎榜股票的换手率情况
    - 买卖总额比：买入总额与卖出总额的比值
    - 上榜次数：股票进入龙虎榜的次数

    Attributes:
        name: 因子名称，默认"dragon_tiger"
        factor_type: 因子类型，固定为FactorType.DRAGON_TIGER

    Example:
        >>> factor = DragonTigerFactor()
        >>> # 假设 data 包含龙虎榜数据
        >>> result = factor.calculate(data)
    """

    def __init__(self, lookback_days: int = 20) -> None:
        """初始化龙虎榜因子

        Args:
            lookback_days: 回看天数，默认20天
        """
        super().__init__(
            name="dragon_tiger",
            factor_type=FactorType.DRAGON_TIGER,
            lookback_days=lookback_days
        )

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算龙虎榜综合因子

        综合考虑机构净买入、换手率等因素计算综合因子值。

        Args:
            data: 包含龙虎榜数据的DataFrame，应包含以下列：
                - symbol: 股票代码
                - datetime: 交易日期
                - institution_net_buy: 机构净买入金额
                - turnover_rate: 换手率
                - buy_amount: 买入总额
                - sell_amount: 卖出总额

        Returns:
            pd.Series: 龙虎榜综合因子值

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
        # 实际实现中需要根据具体数据列计算
        result = pd.Series(
            np.zeros(len(data)),
            index=data.index,
            name="dragon_tiger_factor"
        )

        # 如果有机构净买入数据，则纳入计算
        if "institution_net_buy" in data.columns:
            net_buy_normalized = self._normalize_factor(data["institution_net_buy"])
            result += net_buy_normalized * 0.4

        # 如果有换手率数据，则纳入计算
        if "turnover_rate" in data.columns:
            turnover_normalized = self._normalize_factor(data["turnover_rate"])
            result += turnover_normalized * 0.3

        # 如果有买卖总额比数据，则纳入计算
        if "buy_amount" in data.columns and "sell_amount" in data.columns:
            # 避免除零
            ratio = data["buy_amount"] / (data["sell_amount"] + 1e-8)
            ratio_normalized = self._normalize_factor(ratio)
            result += ratio_normalized * 0.3

        return result

    def get_institution_net_buy(self, data: pd.DataFrame) -> pd.Series:
        """计算机构净买入因子

        机构净买入 = 机构买入金额 - 机构卖出金额
        正值表示机构净买入，负值表示机构净卖出。

        Args:
            data: 包含龙虎榜机构买卖数据的DataFrame，应包含：
                - institution_buy: 机构买入金额
                - institution_sell: 机构卖出金额

        Returns:
            pd.Series: 机构净买入因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="institution_net_buy")

        if "institution_buy" not in data.columns or "institution_sell" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="institution_net_buy")

        net_buy = data["institution_buy"] - data["institution_sell"]
        return pd.Series(net_buy.values, index=data.index, name="institution_net_buy")

    def get_turnover_rate(self, data: pd.DataFrame) -> pd.Series:
        """计算龙虎榜换手率因子

        换手率 = 成交量 / 流通股本
        高换手率通常表示股票交易活跃。

        Args:
            data: 包含交易数据的DataFrame，应包含：
                - volume: 成交量
                - float_share: 流通股本

        Returns:
            pd.Series: 换手率因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="turnover_rate")

        if "volume" not in data.columns or "float_share" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="turnover_rate")

        # 避免除零
        turnover = data["volume"] / (data["float_share"] + 1e-8)
        return pd.Series(turnover.values, index=data.index, name="turnover_rate")

    def get_buy_sell_ratio(self, data: pd.DataFrame) -> pd.Series:
        """计算买卖总额比因子

        买卖总额比 = 买入总额 / 卖出总额
        大于1表示买方力量更强。

        Args:
            data: 包含买卖金额数据的DataFrame，应包含：
                - buy_amount: 买入总额
                - sell_amount: 卖出总额

        Returns:
            pd.Series: 买卖总额比因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="buy_sell_ratio")

        if "buy_amount" not in data.columns or "sell_amount" not in data.columns:
            return pd.Series(np.ones(len(data)), index=data.index, name="buy_sell_ratio")

        # 避免除零
        ratio = data["buy_amount"] / (data["sell_amount"] + 1e-8)
        return pd.Series(ratio.values, index=data.index, name="buy_sell_ratio")

    def get_listing_count(self, data: pd.DataFrame, days: int = 20) -> pd.Series:
        """计算龙虎榜上榜次数因子

        统计在过去N天内股票进入龙虎榜的次数。
        上榜次数越多，说明该股票越活跃。

        Args:
            data: 包含日期和上榜标记的DataFrame，应包含：
                - datetime: 交易日期
                - listed: 是否上榜（布尔值或0/1）
            days: 统计天数窗口

        Returns:
            pd.Series: 上榜次数因子值
        """
        if not self.validate_data(data):
            return pd.Series([], name="listing_count")

        if "datetime" not in data.columns or "listed" not in data.columns:
            return pd.Series(np.zeros(len(data)), index=data.index, name="listing_count")

        # 按股票分组计算滚动上榜次数
        result = data.groupby("symbol")["listed"].transform(
            lambda x: x.rolling(window=days, min_periods=1).sum()
        )

        return pd.Series(result.values, index=data.index, name="listing_count")

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
        """获取龙虎榜因子所需的数据列

        Returns:
            List[str]: 所需列名列表
        """
        return [
            "symbol",
            "datetime",
            "institution_buy",
            "institution_sell",
            "buy_amount",
            "sell_amount",
            "volume",
            "float_share"
        ]
