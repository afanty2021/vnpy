"""A股数据加载器

负责从数据库或API加载历史K线数据，支持多种数据源。
"""

import polars as pl
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

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


__all__ = ["ChinaDataLoader", "Alpha158Calculator"]
