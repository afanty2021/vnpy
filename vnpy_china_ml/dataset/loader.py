"""A股数据加载器

负责从数据库或API加载历史K线数据，支持多种数据源。
"""

import numpy as np
import polars as pl
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from vnpy.trader.object import BarData
from vnpy.trader.database import get_database, BaseDatabase


class ChinaDataLoader:
    """A股数据加载器

    支持从 vnpy 数据库加载历史K线数据。
    """

    def __init__(self, database: Optional[BaseDatabase] = None):
        """初始化数据加载器

        Args:
            database: 数据库实例，默认使用 vnpy 默认数据库
        """
        self.database: BaseDatabase = database or get_database()

        # 数据缓存
        self._cache: dict = {}

    def load_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> pl.DataFrame:
        """加载K线数据

        Args:
            symbols: 股票代码列表，格式如 ["000001.SZSE", "600000.SSE"]
            start_date: 开始日期
            end_date: 结束日期
            interval: K线周期，默认 "1d"（日线）

        Returns:
            Polars DataFrame，包含以下列：
            - datetime: 时间戳
            - vt_symbol: 虚拟合约代码
            - open_price: 开盘价
            - high_price: 最高价
            - low_price: 最低价
            - close_price: 收盘价
            - volume: 成交量
            - turnover: 成交额
        """
        # 检查缓存
        cache_key = f"{'_'.join(sorted(symbols))}_{start_date}_{end_date}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key].clone()

        all_bars: List[BarData] = []

        for symbol in symbols:
            # 从数据库加载K线数据
            bars = self.database.load_bar_data(
                symbol=symbol,
                exchange="",  # 从 symbol 中解析
                interval=interval,
                start=datetime(start_date.year, start_date.month, start_date.day),
                end=datetime(end_date.year, end_date.month, end_date.day)
            )
            all_bars.extend(bars)

        if not all_bars:
            # 如果没有数据，返回空的DataFrame
            return self._create_empty_df()

        # 转换为 Polars DataFrame
        df = self._bars_to_dataframe(all_bars)

        # 缓存数据
        self._cache[cache_key] = df.clone()

        return df

    def _bars_to_dataframe(self, bars: List[BarData]) -> pl.DataFrame:
        """将 BarData 列表转换为 Polars DataFrame

        Args:
            bars: K线数据列表

        Returns:
            Polars DataFrame
        """
        data = []

        for bar in bars:
            data.append({
                "datetime": bar.datetime,
                "vt_symbol": bar.vt_symbol,
                "open_price": float(bar.open_price),
                "high_price": float(bar.high_price),
                "low_price": float(bar.low_price),
                "close_price": float(bar.close_price),
                "volume": float(bar.volume),
                "turnover": float(bar.turnover) if bar.turnover else 0.0,
            })

        df = pl.DataFrame(data)
        return df.sort(["datetime", "vt_symbol"])

    def _create_empty_df(self) -> pl.DataFrame:
        """创建空的K线数据DataFrame

        Returns:
            空的 Polars DataFrame
        """
        schema = {
            "datetime": pl.Datetime,
            "vt_symbol": pl.String,
            "open_price": pl.Float64,
            "high_price": pl.Float64,
            "low_price": pl.Float64,
            "close_price": pl.Float64,
            "volume": pl.Float64,
            "turnover": pl.Float64,
        }

        return pl.DataFrame(schema=schema)

    def load_from_csv(
        self,
        csv_path: str,
        symbol_col: str = "symbol",
        date_col: str = "date",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume"
    ) -> pl.DataFrame:
        """从CSV文件加载K线数据

        Args:
            csv_path: CSV文件路径
            symbol_col: 股票代码列名
            date_col: 日期列名
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名

        Returns:
            Polars DataFrame
        """
        df = pl.read_csv(csv_path)

        # 重命名列
        rename_map = {
            date_col: "datetime",
            symbol_col: "vt_symbol",
            open_col: "open_price",
            high_col: "high_price",
            low_col: "low_price",
            close_col: "close_price",
            volume_col: "volume"
        }

        df = df.rename(rename_map)

        # 确保 datetime 是 datetime 类型
        if "datetime" in df.columns:
            df = df.with_columns(
                pl.col("datetime").str.to_datetime()
            )

        # 添加缺失的列
        if "turnover" not in df.columns:
            df = df.with_columns(
                pl.lit(0.0).alias("turnover")
            )

        # 选择需要的列
        required_cols = [
            "datetime", "vt_symbol", "open_price", "high_price",
            "low_price", "close_price", "volume", "turnover"
        ]

        return df.select(required_cols).sort(["datetime", "vt_symbol"])

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()


class Alpha158Calculator:
    """Alpha 158 因子计算器

    基于 vnpy.alpha 模块计算经典的 Alpha 158 因子集。
    """

    def __init__(self):
        """初始化因子计算器"""
        pass

    def calculate_all(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算所有 Alpha 158 因子

        Args:
            df: 原始K线数据，必须包含 OHLCV 列

        Returns:
            包含所有因子的 DataFrame
        """
        # 基础列名
        price_cols = ["open_price", "high_price", "low_price", "close_price"]

        # 计算各类因子
        result_df = df.clone()

        # 1. 收益率因子
        result_df = self._calculate_return_factors(result_df)

        # 2. 技术指标因子
        result_df = self._calculate_technical_factors(result_df)

        # 3. 成交量因子
        result_df = self._calculate_volume_factors(result_df)

        # 4. 波动率因子
        result_df = self._calculate_volatility_factors(result_df)

        # 5. 价格统计因子
        result_df = self._calculate_price_stat_factors(result_df)

        return result_df

    def _calculate_return_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算收益率因子"""
        # 按股票分组计算收益率
        result = df.sort(["datetime", "vt_symbol"])

        # 5日收益率
        result = result.with_columns(
            pl.col("close_price")
            .pct_change(n=5)
            .over("vt_symbol")
            .alias("Return_5d")
        )

        # 10日收益率
        result = result.with_columns(
            pl.col("close_price")
            .pct_change(n=10)
            .over("vt_symbol")
            .alias("Return_10d")
        )

        # 20日收益率
        result = result.with_columns(
            pl.col("close_price")
            .pct_change(n=20)
            .over("vt_symbol")
            .alias("Return_20d")
        )

        # 60日收益率
        result = result.with_columns(
            pl.col("close_price")
            .pct_change(n=60)
            .over("vt_symbol")
            .alias("Return_60d")
        )

        return result

    def _calculate_technical_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算技术指标因子"""
        result = df.sort(["datetime", "vt_symbol"])

        # RSI (Relative Strength Index)
        # 简化版本：使用涨跌幅计算
        result = result.with_columns(
            pl.col("close_price")
            .pct_change()
            .over("vt_symbol")
            .alias("_price_change")
        )

        # 上涨和下跌
        result = result.with_columns(
            pl.when(pl.col("_price_change") > 0)
            .then(pl.col("_price_change"))
            .otherwise(0)
            .over("vt_symbol")
            .alias("_gain")
        )

        result = result.with_columns(
            pl.when(pl.col("_price_change") < 0)
            .then(-pl.col("_price_change"))
            .otherwise(0)
            .over("vt_symbol")
            .alias("_loss")
        )

        # 14日平均涨跌
        result = result.with_columns(
            pl.col("_gain")
            .rolling_mean(window_size=14)
            .over("vt_symbol")
            .alias("_avg_gain")
        )

        result = result.with_columns(
            pl.col("_loss")
            .rolling_mean(window_size=14)
            .over("vt_symbol")
            .alias("_avg_loss")
        )

        # RSI = 100 - (100 / (1 + RS))
        # RS = avg_gain / avg_loss
        result = result.with_columns(
            pl.when(pl.col("_avg_loss") != 0)
            .then(100 - (100 / (1 + pl.col("_avg_gain") / pl.col("_avg_loss"))))
            .otherwise(100)
            .alias("RSI_14")
        )

        # MACD (Moving Average Convergence Divergence)
        # 12日EMA
        result = result.with_columns(
            pl.col("close_price")
            .ewm_mean(alpha=2/13, adjust=False)
            .over("vt_symbol")
            .alias("_ema12")
        )

        # 26日EMA
        result = result.with_columns(
            pl.col("close_price")
            .ewm_mean(alpha=2/27, adjust=False)
            .over("vt_symbol")
            .alias("_ema26")
        )

        # MACD = EMA12 - EMA26
        result = result.with_columns(
            (pl.col("_ema12") - pl.col("_ema26"))
            .alias("MACD")
        )

        # Signal = 9日EMA of MACD
        result = result.with_columns(
            pl.col("MACD")
            .ewm_mean(alpha=2/10, adjust=False)
            .over("vt_symbol")
            .alias("MACD_Signal")
        )

        # 清理临时列
        temp_cols = ["_price_change", "_gain", "_loss", "_avg_gain", "_avg_loss", "_ema12", "_ema26"]
        for col in temp_cols:
            if col in result.columns:
                result = result.drop(col)

        return result

    def _calculate_volume_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算成交量因子"""
        result = df.sort(["datetime", "vt_symbol"])

        # 成交量比率（当前成交量 / 5日平均成交量）
        result = result.with_columns(
            pl.col("volume")
            .rolling_mean(window_size=5)
            .over("vt_symbol")
            .alias("_volume_ma5")
        )

        result = result.with_columns(
            (pl.col("volume") / pl.col("_volume_ma5"))
            .alias("Volume_Ratio")
        )

        # 成交量变化率
        result = result.with_columns(
            pl.col("volume")
            .pct_change(n=5)
            .over("vt_symbol")
            .alias("Volume_Change_5d")
        )

        # 清理临时列
        if "_volume_ma5" in result.columns:
            result = result.drop("_volume_ma5")

        return result

    def _calculate_volatility_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算波动率因子"""
        result = df.sort(["datetime", "vt_symbol"])

        # ATR (Average True Range) - 简化版本
        # True Range = max(high - low, abs(high - close_prev), abs(low - close_prev))
        result = result.with_columns(
            pl.col("high_price")
            .pct_change()
            .over("vt_symbol")
            .alias("_high_change")
        )

        result = result.with_columns(
            pl.col("low_price")
            .pct_change()
            .over("vt_symbol")
            .alias("_low_change")
        )

        # 简化的波动率：高低价差
        result = result.with_columns(
            (pl.col("high_price") - pl.col("low_price")) / pl.col("close_price")
            .alias("ATR_14_Simple")
        )

        # 布林带宽度
        result = result.with_columns(
            pl.col("close_price")
            .rolling_mean(window_size=20)
            .over("vt_symbol")
            .alias("_bb_middle")
        )

        result = result.with_columns(
            pl.col("close_price")
            .rolling_std(window_size=20)
            .over("vt_symbol")
            .alias("_bb_std")
        )

        result = result.with_columns(
            (2 * pl.col("_bb_std") / pl.col("_bb_middle"))
            .alias("Bollinger_Width")
        )

        # 清理临时列
        temp_cols = ["_high_change", "_low_change", "_bb_middle", "_bb_std"]
        for col in temp_cols:
            if col in result.columns:
                result = result.drop(col)

        return result

    def _calculate_price_stat_factors(self, df: pl.DataFrame) -> pl.DataFrame:
        """计算价格统计因子"""
        result = df.sort(["datetime", "vt_symbol"])

        # 价格动量 (ROC - Rate of Change)
        result = result.with_columns(
            ((pl.col("close_price") - pl.col("close_price").shift(10)) / pl.col("close_price").shift(10))
            .over("vt_symbol")
            .alias("ROC_10")
        )

        # 收盘价相对位置 (在N天内的分位数)
        result = result.with_columns(
            pl.col("close_price")
            .rolling_min(window_size=20)
            .over("vt_symbol")
            .alias("_min_20")
        )

        result = result.with_columns(
            pl.col("close_price")
            .rolling_max(window_size=20)
            .over("vt_symbol")
            .alias("_max_20")
        )

        result = result.with_columns(
            ((pl.col("close_price") - pl.col("_min_20")) / (pl.col("_max_20") - pl.col("_min_20")))
            .alias("Price_Position_20")
        )

        # 清理临时列
        temp_cols = ["_min_20", "_max_20"]
        for col in temp_cols:
            if col in result.columns:
                result = result.drop(col)

        return result


# ==================== 模块级数据准备函数 ====================
# 以下三个函数从 gui_engine 提取的纯逻辑版本，不依赖 self._log；
# 进度日志由调用方（gui_engine 薄包装）负责记录，数据为空抛 RuntimeError（消息文本契约保持）。


# 训练数据准备默认使用的股票池（与原 gui_engine._prepare_training_data 保持一致）
_DEFAULT_TRAINING_SYMBOLS: List[str] = [
    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
    "601318.SH", "601398.SH", "601857.SH", "601988.SH"
]

# 预测数据的股票名称映射（与原 gui_engine._prepare_prediction_data 保持一致）
_SYMBOL_NAMES: dict = {
    "000001.SZ": "平安银行", "000002.SZ": "万科A",
    "600000.SH": "浦发银行", "600036.SH": "招商银行",
    "600519.SH": "贵州茅台"
}


def prepare_training_data(
    start_date: date,
    end_date: date,
    lookback_days: int,
    forward_days: int
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """准备训练数据

    内部使用 create_alpha_dataset 加载并构造特征/标签。
    数据为空时抛 RuntimeError，消息必须包含「本地数据库中没有训练数据」。

    Args:
        start_date: 训练开始日期
        end_date: 训练结束日期
        lookback_days: 回看天数
        forward_days: 预测天数

    Returns:
        (X, y, feature_names) 元组

    Raises:
        RuntimeError: 数据集模块不可用或数据为空时
    """
    # 延迟导入 create_alpha_dataset（与原方法一致的错误处理）
    try:
        from vnpy_china_ml.dataset import create_alpha_dataset
    except ImportError as e:
        raise RuntimeError(
            f"数据集模块不可用: {e}\n"
            f"请确保已正确安装 vnpy_china_ml 模块"
        )

    # 创建数据集
    dataset = create_alpha_dataset(
        symbols=_DEFAULT_TRAINING_SYMBOLS,
        start_date=start_date,
        end_date=end_date,
        lookback_days=lookback_days,
        forward_days=forward_days
    )

    # 获取训练数据
    X, y = dataset.get_all_data()
    feature_names = dataset.get_feature_names()

    if len(X) == 0:
        raise RuntimeError(
            f"本地数据库中没有训练数据\n"
            f"请先下载历史数据:\n"
            f"  1. 打开「A股数据」模块\n"
            f"  2. 点击「下载历史数据」\n"
            f"  3. 选择股票代码和日期范围\n"
            f"  4. 确保下载范围包含 {start_date} 到 {end_date}\n"
            f"训练需要至少 {lookback_days} 天的历史数据"
        )

    return X, y, feature_names


def prepare_prediction_data(
    symbols: List[str],
    predict_date: date
) -> Tuple[np.ndarray, List[str], List[str]]:
    """准备预测数据

    使用 ChinaDataLoader 加载 K 线，Alpha158Calculator 计算因子，
    提取预测日期的最新横截面特征。返回的 vt_symbol 列与 _SYMBOL_NAMES 保持映射。

    数据为空时抛 RuntimeError，消息必须包含「本地数据库中没有股票数据」。

    Args:
        symbols: 股票代码列表
        predict_date: 预测日期

    Returns:
        (X, valid_symbols, valid_names) 元组，valid_symbols 来自 vt_symbol 列

    Raises:
        RuntimeError: 数据集模块不可用、K线数据为空、无可用预测数据或无因子特征
    """
    # 延迟导入（与原方法一致的错误处理）
    try:
        from vnpy_china_ml.dataset import ChinaDataLoader, Alpha158Calculator
    except ImportError as e:
        raise RuntimeError(
            f"数据集模块不可用: {e}\n"
            f"请确保已安装 vnpy.alpha 模块\n"
            f"安装命令: pip install vnpy-alpha"
        )

    # 数据加载器
    loader = ChinaDataLoader()
    factor_calc = Alpha158Calculator()

    # 计算数据起始日期（需要足够的历史数据计算因子）
    start_date = predict_date - timedelta(days=90)

    # 加载K线数据
    df = loader.load_bars(
        symbols=symbols,
        start_date=start_date,
        end_date=predict_date,
        interval="1d"
    )

    if len(df) == 0:
        raise RuntimeError(
            f"本地数据库中没有股票数据\n"
            f"请先下载历史数据:\n"
            f"  1. 打开「A股数据」模块\n"
            f"  2. 点击「下载历史数据」\n"
            f"  3. 选择股票代码和日期范围\n"
            f"  4. 确保下载范围包含 {start_date} 到 {predict_date}\n"
            f"当前请求的股票: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}"
        )

    # 计算因子
    df = factor_calc.calculate_all(df)

    # 获取预测日期的最新数据
    predict_datetime = datetime.combine(predict_date, datetime.min.time())
    latest_df = df.filter(
        pl.col("datetime") <= pl.lit(predict_datetime)
    ).group_by("vt_symbol").last()

    if len(latest_df) == 0:
        raise RuntimeError(
            f"没有可用的预测数据 (截至 {predict_date})\n"
            f"请确保:\n"
            f"  1. 已下载至少90天的历史数据（用于计算Alpha158因子）\n"
            f"  2. 预测日期在已下载数据范围内"
        )

    # 提取特征
    base_cols = ["datetime", "vt_symbol", "open_price", "high_price",
                 "low_price", "close_price", "volume", "turnover"]
    feature_cols = [col for col in latest_df.columns if col not in base_cols]

    if not feature_cols:
        raise RuntimeError(
            f"未能计算出任何因子特征\n"
            f"请检查 Alpha158 计算器是否正常工作\n"
            f"可能需要更多的历史数据来计算因子"
        )

    X = latest_df.select(feature_cols).to_numpy()

    # 获取有效的股票列表（vt_symbol + 名称映射）
    valid_symbols = latest_df["vt_symbol"].to_list()
    valid_names = [_SYMBOL_NAMES.get(s, s) for s in valid_symbols]

    return X, valid_symbols, valid_names


def calculate_alpha158_features(
    symbols: List[str],
    start_date: date,
    end_date: date,
    infer_factor_type: Optional[Callable[[str], str]] = None
) -> pl.DataFrame:
    """计算 Alpha 158 因子并构造特征 DataFrame

    内部流程：加载 K 线数据 -> 计算 Alpha158 因子 -> 按 _infer_factor_type 推断
    每个因子的类型 -> 计算重要性/相关性 -> 按重要性降序排序 -> 构造特征 DataFrame。

    数据为空时抛 RuntimeError（消息文本保持与原 gui_engine.calculate_features 一致）。

    Args:
        symbols: 股票代码列表
        start_date: 用户请求的开始日期（不含 90 天 buffer）
        end_date: 用户请求的结束日期
        infer_factor_type: 因子类型推断函数。为 None 时使用模块内置的简单实现
            （将所有因子归类为 "其他"）。gui_engine 通常传入 self._infer_factor_type。

    Returns:
        特征 DataFrame，包含 factor_name / factor_type / importance / correlation 列

    Raises:
        RuntimeError: K线数据为空或未能计算出任何因子特征
    """
    from vnpy_china_ml.dataset import ChinaDataLoader, Alpha158Calculator

    # 因子类型推断回退：所有因子归到 "其他"
    if infer_factor_type is None:
        def infer_factor_type(name: str) -> str:
            return "其他"

    # 数据加载器
    loader = ChinaDataLoader()
    factor_calc = Alpha158Calculator()

    # 计算数据起始日期（需要足够的历史数据计算因子）
    calc_start_date = start_date - timedelta(days=90)

    # 加载K线数据
    df = loader.load_bars(
        symbols=symbols,
        start_date=calc_start_date,
        end_date=end_date,
        interval="1d"
    )

    if len(df) == 0:
        raise RuntimeError(
            f"本地数据库中没有K线数据\n"
            f"请先下载历史数据:\n"
            f"  1. 打开「A股数据」模块\n"
            f"  2. 点击「下载历史数据」\n"
            f"  3. 选择股票代码和日期范围\n"
            f"  4. 确保下载范围包含 {calc_start_date} 到 {end_date}\n"
            f"当前请求的股票: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}"
        )

    # 计算因子
    df = factor_calc.calculate_all(df)

    # 提取特征列（calculate_features 里的 base_cols 多了 "label"，保持一致）
    base_cols = ["datetime", "vt_symbol", "open_price", "high_price",
                 "low_price", "close_price", "volume", "turnover", "label"]
    feature_cols = [col for col in df.columns if col not in base_cols]

    if not feature_cols:
        raise RuntimeError(
            f"未能计算出任何因子特征\n"
            f"请确保:\n"
            f"  1. 已下载至少90天的历史数据（用于计算Alpha158因子）\n"
            f"  2. 日期范围包含 {start_date} 到 {end_date}"
        )

    # 计算每个因子的类型
    features_data = []
    for col in feature_cols:
        ftype = infer_factor_type(col)
        # 使用最后一行的数据作为示例
        last_row = df.select(pl.col(col).last()).row(0)
        importance = abs(float(last_row[0])) if last_row[0] is not None else 0.0
        correlation = min(importance, 0.99)

        features_data.append({
            "factor_name": col,
            "factor_type": ftype,
            "importance": importance,
            "correlation": correlation
        })

    # 按重要性排序
    features_data.sort(key=lambda x: x["importance"], reverse=True)

    result_df = pl.DataFrame(features_data)

    return result_df


__all__ = [
    "ChinaDataLoader",
    "Alpha158Calculator",
    "prepare_training_data",
    "prepare_prediction_data",
    "calculate_alpha158_features",
]
