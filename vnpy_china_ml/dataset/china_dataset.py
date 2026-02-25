"""中国A股Alpha数据集

提供完整的A股数据加载、特征工程和数据准备功能。
"""

import numpy as np
import polars as pl
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .loader import ChinaDataLoader, Alpha158Calculator


class ChinaAlphaDataset:
    """中国A股Alpha数据集

    提供完整的A股数据加载、特征工程和数据准备功能。

    使用示例：
        ```python
        dataset = ChinaAlphaDataset(
            symbols=["000001.SZ", "600000.SH"],
            start_date="2023-01-01",
            end_date="2024-12-31"
        )

        # 加载并计算特征
        X_train, y_train = dataset.get_training_data()

        # 获取特征名称
        feature_names = dataset.get_feature_names()
        ```
    """

    def __init__(
        self,
        symbols: List[str],
        start_date: Union[str, date],
        end_date: Union[str, date],
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
        lookback_days: int = 60,
        forward_days: int = 5
    ):
        """初始化数据集

        Args:
            symbols: 股票代码列表，如 ["000001.SZ", "600000.SH"]
            start_date: 开始日期
            end_date: 结束日期
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            lookback_days: 回看天数（用于计算特征）
            forward_days: 预测天数（预测未来N天的收益）
        """
        # 日期处理
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        self.symbols: List[str] = symbols
        self.start_date: date = start_date
        self.end_date: date = end_date
        self.lookback_days: int = lookback_days
        self.forward_days: int = forward_days

        # 数据加载器
        self.loader: ChinaDataLoader = ChinaDataLoader()
        self.factor_calc: Alpha158Calculator = Alpha158Calculator()

        # 原始数据
        self.raw_df: Optional[pl.DataFrame] = None
        self.feature_df: Optional[pl.DataFrame] = None

        # 计算时间划分
        total_days = (end_date - start_date).days
        train_end = start_date + timedelta(days=int(total_days * train_ratio))
        valid_end = train_end + timedelta(days=int(total_days * valid_ratio))

        # 数据周期划分
        self.train_period: Tuple[date, date] = (start_date, train_end)
        self.valid_period: Tuple[date, date] = (train_end, valid_end)
        self.test_period: Tuple[date, date] = (valid_end, end_date)

        # 特征名称
        self.feature_names: List[str] = []

    def load_data(self) -> None:
        """加载原始K线数据"""
        self.raw_df = self.loader.load_bars(
            symbols=self.symbols,
            start_date=self.start_date - timedelta(days=self.lookback_days + 50),  # 额外加载数据用于计算特征
            end_date=self.end_date + timedelta(days=self.forward_days)
        )

        if self.raw_df is None or len(self.raw_df) == 0:
            raise ValueError("未能加载任何数据，请检查股票代码和日期范围")

    def calculate_features(self) -> None:
        """计算Alpha特征"""
        if self.raw_df is None:
            self.load_data()

        # 使用 Alpha158Calculator 计算因子
        self.feature_df = self.factor_calc.calculate_all(self.raw_df)

        # 计算目标变量（未来收益率）
        self.feature_df = self._calculate_labels(self.feature_df)

        # 提取特征名称
        base_cols = ["datetime", "vt_symbol", "open_price", "high_price",
                     "low_price", "close_price", "volume", "turnover", "label"]
        self.feature_names = [
            col for col in self.feature_df.columns
            if col not in base_cols
        ]

    def _calculate_labels(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算目标变量（未来收益率）

        Args:
            df: 特征数据

        Returns:
            添加了label列的DataFrame
        """
        result = df.sort(["datetime", "vt_symbol"])

        # 计算未来N天的收益率
        result = result.with_columns(
            pl.col("close_price")
            .shift(-self.forward_days)
            .over("vt_symbol")
            .alias("_future_close")
        )

        result = result.with_columns(
            (pl.col("_future_close") - pl.col("close_price")) / pl.col("close_price")
            .alias("label")
        )

        # 删除临时列
        if "_future_close" in result.columns:
            result = result.drop("_future_close")

        # 删除最后N行（没有未来数据）
        result = result.filter(
            pl.col("label").is_not_null()
        )

        return result

    def prepare_data(
        self,
        normalize: bool = True,
        drop_na: bool = True,
        fill_method: str = "ffill"
    ) -> None:
        """准备数据（特征工程）

        Args:
            normalize: 是否进行标准化
            drop_na: 是否删除缺失值
            fill_method: 缺失值填充方法 ("ffill", "mean", "zero")
        """
        if self.feature_df is None:
            self.calculate_features()

        df = self.feature_df.clone()

        # 处理缺失值
        if fill_method == "ffill":
            df = df.with_columns(
                pl.all().forward_fill().over("vt_symbol")
            )
        elif fill_method == "mean":
            for col in self.feature_names:
                if col in df.columns:
                    mean_val = df[col].mean()
                    df = df.with_columns(
                        pl.col(col).fill_null(mean_val)
                    )
        elif fill_method == "zero":
            df = df.with_columns(
                pl.col(self.feature_names).fill_null(0)
            )

        # 删除缺失值
        if drop_na:
            df = df.drop_nulls(subset=self.feature_names + ["label"])

        # 标准化（使用截面标准化）
        if normalize:
            for col in self.feature_names:
                if col in df.columns:
                    # 按日期分组进行截面标准化
                    df = df.with_columns(
                        ((pl.col(col) - pl.col(col).mean().over("datetime")) /
                         pl.col(col).std().over("datetime"))
                        .over("datetime")
                        .alias(col)
                    )

        self.feature_df = df

    def get_segment_data(self, segment: str = "train") -> Tuple[np.ndarray, np.ndarray]:
        """获取指定时间段的数据

        Args:
            segment: 时间段 ("train", "valid", "test")

        Returns:
            (X, y) 特征和目标变量的元组
        """
        if self.feature_df is None:
            self.prepare_data()

        # 确定时间范围
        if segment == "train":
            start, end = self.train_period
        elif segment == "valid":
            start, end = self.valid_period
        elif segment == "test":
            start, end = self.test_period
        else:
            raise ValueError(f"未知的时间段: {segment}")

        # 过滤数据
        df = self.feature_df.filter(
            (pl.col("datetime") >= pl.lit(start))
            & (pl.col("datetime") <= pl.lit(end))
        )

        if len(df) == 0:
            raise ValueError(f"时间段 {segment} 没有数据")

        # 提取特征和标签
        X = df.select(self.feature_names).to_numpy()
        y = df.select("label").to_numpy().flatten()

        return X, y

    def get_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取训练数据"""
        return self.get_segment_data("train")

    def get_validation_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取验证数据"""
        return self.get_segment_data("valid")

    def get_test_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取测试数据"""
        return self.get_segment_data("test")

    def get_all_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取所有数据"""
        if self.feature_df is None:
            self.prepare_data()

        X = self.feature_df.select(self.feature_names).to_numpy()
        y = self.feature_df.select("label").to_numpy().flatten()

        return X, y

    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        return self.feature_names.copy()

    def get_data_info(self) -> Dict:
        """获取数据集信息"""
        return {
            "symbols": self.symbols,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "train_period": (self.train_period[0].isoformat(), self.train_period[1].isoformat()),
            "valid_period": (self.valid_period[0].isoformat(), self.valid_period[1].isoformat()),
            "test_period": (self.test_period[0].isoformat(), self.test_period[1].isoformat()),
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "lookback_days": self.lookback_days,
            "forward_days": self.forward_days,
        }

    def save(self, path: str) -> None:
        """保存数据集到文件

        Args:
            path: 保存路径
        """
        if self.feature_df is None:
            self.prepare_data()

        self.feature_df.write_parquet(path)

    @classmethod
    def load(cls, path: str) -> "ChinaAlphaDataset":
        """从文件加载数据集

        Args:
            path: 文件路径

        Returns:
            ChinaAlphaDataset 实例
        """
        df = pl.read_parquet(path)

        # 创建一个空的数据集实例
        dataset = cls(
            symbols=[],
            start_date=date.today(),
            end_date=date.today()
        )

        dataset.feature_df = df

        # 提取特征名称
        base_cols = ["datetime", "vt_symbol", "open_price", "high_price",
                     "low_price", "close_price", "volume", "turnover", "label"]
        dataset.feature_names = [
            col for col in df.columns
            if col not in base_cols
        ]

        return dataset


def create_alpha_dataset(
    symbols: List[str],
    start_date: Union[str, date],
    end_date: Union[str, date],
    **kwargs
) -> ChinaAlphaDataset:
    """创建A股Alpha数据集的便捷函数

    Args:
        symbols: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        **kwargs: 其他参数传递给 ChinaAlphaDataset

    Returns:
        配置好的 ChinaAlphaDataset 实例

    Example:
        ```python
        dataset = create_alpha_dataset(
            symbols=["000001.SZ", "600000.SH"],
            start_date="2023-01-01",
            end_date="2024-12-31"
        )
        X_train, y_train = dataset.get_training_data()
        ```
    """
    dataset = ChinaAlphaDataset(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        **kwargs
    )

    # 自动加载和计算
    dataset.load_data()
    dataset.calculate_features()
    dataset.prepare_data()

    return dataset


__all__ = [
    "ChinaAlphaDataset",
    "create_alpha_dataset",
]
