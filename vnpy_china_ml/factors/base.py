"""
因子基类模块

定义所有因子的抽象基类，提供统一的接口和规范。

数据格式说明：
    本模块使用 pandas 进行数据处理。vnpy_china_ml 的 dataset/、backtesting/、
    gui_engine.py 等模块使用 polars。跨模块传递 DataFrame 时需要进行转换：
        - pandas → polars:  pl.from_pandas(df)
        - polars → pandas:  df.to_pandas()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime

from ..utils.types import FactorType


class BaseFactor(ABC):
    """因子基类

    所有因子类必须继承此基类并实现calculate方法。
    因子是用于预测股票收益的特征指标，每个因子都有特定的
    计算逻辑和数据需求。

    Attributes:
        name: 因子名称
        factor_type: 因子类型（来自FactorType枚举）
        lookback_days: 回看天数，用于计算因子的历史数据窗口

    Example:
        >>> class MyFactor(BaseFactor):
        ...     def __init__(self):
        ...         super().__init__("my_factor", FactorType.TECHNICAL)
        ...
        ...     def calculate(self, data: pd.DataFrame) -> pd.Series:
        ...         # 实现因子计算逻辑
        ...         return result
    """

    def __init__(
        self,
        name: str,
        factor_type: FactorType,
        lookback_days: int = 20
    ) -> None:
        """初始化因子

        Args:
            name: 因子名称
            factor_type: 因子类型
            lookback_days: 回看天数，默认20天
        """
        self.name = name
        self.factor_type = factor_type
        self.lookback_days = lookback_days

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算因子值

        子类必须实现此方法以计算具体的因子值。

        Args:
            data: 包含市场数据的DataFrame，至少需要包含以下列：
                - symbol: 股票代码
                - datetime: 数据时间
                - close: 收盘价
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - volume: 成交量
                （具体列可能因因子类型而异）

        Returns:
            pd.Series: 因子值序列，索引为datetime

        Raises:
            ValueError: 当数据格式不正确或缺少必要字段时
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """验证数据有效性

        检查输入数据是否为空且包含必要的列。

        Args:
            data: 待验证的数据DataFrame

        Returns:
            bool: 数据是否有效
        """
        if data is None or data.empty:
            return False
        return True

    def get_required_columns(self) -> List[str]:
        """获取因子计算所需的数据列

        子类可以重写此方法以指定额外的数据列需求。

        Returns:
            List[str]: 所需列名列表
        """
        return ["symbol", "datetime", "close"]

    def get_lookback_days(self) -> int:
        """获取回看天数

        Returns:
            int: 回看天数
        """
        return self.lookback_days

    def set_lookback_days(self, days: int) -> None:
        """设置回看天数

        Args:
            days: 新的回看天数，必须大于0
        """
        if days <= 0:
            raise ValueError("lookback_days必须大于0")
        self.lookback_days = days

    def __repr__(self) -> str:
        """返回因子的字符串表示"""
        return f"{self.__class__.__name__}(name='{self.name}', type={self.factor_type.value}, lookback={self.lookback_days})"
