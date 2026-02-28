import json
import shelve
import pickle
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from functools import lru_cache

import polars as pl

from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from vnpy.trader.utility import extract_vt_symbol

from .logger import logger
from .dataset import AlphaDataset, to_datetime, Segment
from .model import AlphaModel, ModelVersion
from .model.version_manager import ModelVersionManager
from .monitor import (
    PerformanceTracker,
    PerformanceMetric,
    ModelPerformanceSnapshot,
    MetricCategory,
    DEFAULT_ALERT_RULES,
)
from .monitor.metrics import TradingStatistics


class AlphaLab:
    """Alpha Research Laboratory"""

    def __init__(self, lab_path: str) -> None:
        """Constructor"""
        # Set data paths
        self.lab_path: Path = Path(lab_path)

        self.daily_path: Path = self.lab_path.joinpath("daily")
        self.minute_path: Path = self.lab_path.joinpath("minute")
        self.component_path: Path = self.lab_path.joinpath("component")

        self.dataset_path: Path = self.lab_path.joinpath("dataset")
        self.model_path: Path = self.lab_path.joinpath("model")
        self.signal_path: Path = self.lab_path.joinpath("signal")

        self.contract_path: Path = self.lab_path.joinpath("contract.json")

        # Create folders
        for path in [
            self.lab_path,
            self.daily_path,
            self.minute_path,
            self.component_path,
            self.dataset_path,
            self.model_path,
            self.signal_path
        ]:
            if not path.exists():
                path.mkdir(parents=True)

        # Initialize version manager
        self.version_manager = ModelVersionManager(self.model_path)

        # Initialize performance trackers
        self.performance_trackers: dict[str, PerformanceTracker] = {}

    def save_bar_data(self, bars: list[BarData]) -> None:
        """Save bar data"""
        if not bars:
            return

        # Get file path
        bar: BarData = bars[0]

        if bar.interval == Interval.DAILY:
            file_path: Path = self.daily_path.joinpath(f"{bar.vt_symbol}.parquet")
        elif bar.interval == Interval.MINUTE:
            file_path = self.minute_path.joinpath(f"{bar.vt_symbol}.parquet")
        elif bar.interval:
            logger.error(f"Unsupported interval {bar.interval.value}")
            return

        data: list = []
        for bar in bars:
            bar_data: dict = {
                "datetime": bar.datetime.replace(tzinfo=None),
                "open": bar.open_price,
                "high": bar.high_price,
                "low": bar.low_price,
                "close": bar.close_price,
                "volume": bar.volume,
                "turnover": bar.turnover,
                "open_interest": bar.open_interest
            }
            data.append(bar_data)

        new_df: pl.DataFrame = pl.DataFrame(data)

        # If file exists, read and merge
        if file_path.exists():
            old_df: pl.DataFrame = pl.read_parquet(file_path)

            new_df = pl.concat([old_df, new_df])

            new_df = new_df.unique(subset=["datetime"])

            new_df = new_df.sort("datetime")

        # Save to file
        new_df.write_parquet(file_path)

    def load_bar_data(
        self,
        vt_symbol: str,
        interval: Interval | str,
        start: datetime | str,
        end: datetime | str
    ) -> list[BarData]:
        """Load bar data"""
        # Convert types
        if isinstance(interval, str):
            interval = Interval(interval)

        start = to_datetime(start)
        end = to_datetime(end)

        # Get folder path
        if interval == Interval.DAILY:
            folder_path: Path = self.daily_path
        elif interval == Interval.MINUTE:
            folder_path = self.minute_path
        else:
            logger.error(f"Unsupported interval {interval.value}")
            return []

        # Check if file exists
        file_path: Path = folder_path.joinpath(f"{vt_symbol}.parquet")
        if not file_path.exists():
            logger.error(f"File {file_path} does not exist")
            return []

        # Open file
        df: pl.DataFrame = pl.read_parquet(file_path)

        # Filter by date range
        df = df.filter((pl.col("datetime") >= start) & (pl.col("datetime") <= end))

        # Convert to BarData objects
        bars: list[BarData] = []

        symbol, exchange = extract_vt_symbol(vt_symbol)

        for row in df.iter_rows(named=True):
            bar = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=row["datetime"],
                interval=interval,
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"],
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=row["open_interest"],
                gateway_name="DB"
            )
            bars.append(bar)

        return bars

    def load_bar_df(
        self,
        vt_symbols: list[str],
        interval: Interval | str,
        start: datetime | str,
        end: datetime | str,
        extended_days: int
    ) -> pl.DataFrame | None:
        """Load bar data as DataFrame"""
        if not vt_symbols:
            return None

        # Convert types
        if isinstance(interval, str):
            interval = Interval(interval)

        start = to_datetime(start) - timedelta(days=extended_days)
        end = to_datetime(end) + timedelta(days=extended_days // 10)

        # Get folder path
        if interval == Interval.DAILY:
            folder_path: Path = self.daily_path
        elif interval == Interval.MINUTE:
            folder_path = self.minute_path
        else:
            logger.error(f"Unsupported interval {interval.value}")
            return None

        # Read data for each symbol
        dfs: list = []

        for vt_symbol in vt_symbols:
            # Check if file exists
            file_path: Path = folder_path.joinpath(f"{vt_symbol}.parquet")
            if not file_path.exists():
                logger.error(f"File {file_path} does not exist")
                continue

            # Open file
            df: pl.DataFrame = pl.read_parquet(file_path)

            # Filter by date range
            df = df.filter((pl.col("datetime") >= start) & (pl.col("datetime") <= end))

            # Specify data types
            df = df.with_columns(
                pl.col("open"),
                pl.col("high"),
                pl.col("low"),
                pl.col("close"),
                pl.col("volume"),
                pl.col("turnover"),
                pl.col("open_interest"),
                (pl.col("turnover") / pl.col("volume")).alias("vwap")
            )

            # Check for empty data
            if df.is_empty():
                continue

            # Normalize prices
            close_0: float = df.select(pl.col("close")).item(0, 0)

            df = df.with_columns(
                (pl.col("open") / close_0).alias("open"),
                (pl.col("high") / close_0).alias("high"),
                (pl.col("low") / close_0).alias("low"),
                (pl.col("close") / close_0).alias("close"),
            )

            # Convert zeros to NaN for suspended trading days
            numeric_columns: list = df.columns[1:]                              # Extract numeric columns

            mask: pl.Series = df[numeric_columns].sum_horizontal() == 0         # Sum by row, if 0 then suspended

            df = df.with_columns(                                               # Convert suspended day values to NaN
                [pl.when(mask).then(float("nan")).otherwise(pl.col(col)).alias(col) for col in numeric_columns]
            )

            # Add symbol column
            df = df.with_columns(pl.lit(vt_symbol).alias("vt_symbol"))

            # Cache in list
            dfs.append(df)

        # Concatenate results
        result_df: pl.DataFrame = pl.concat(dfs)
        return result_df

    def save_component_data(
        self,
        index_symbol: str,
        index_components: dict[str, list[str]]
    ) -> None:
        """Save index component data"""
        file_path: Path = self.component_path.joinpath(f"{index_symbol}")

        with shelve.open(str(file_path)) as db:
            db.update(index_components)

    @lru_cache      # noqa
    def load_component_data(
        self,
        index_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> dict[datetime, list[str]]:
        """Load index component data as DataFrame"""
        file_path: Path = self.component_path.joinpath(f"{index_symbol}")

        start = to_datetime(start)
        end = to_datetime(end)

        with shelve.open(str(file_path)) as db:
            keys: list[str] = list(db.keys())
            keys.sort()

            index_components: dict[datetime, list[str]] = {}
            for key in keys:
                dt: datetime = datetime.strptime(key, "%Y-%m-%d")
                if start <= dt <= end:
                    index_components[dt] = db[key]

            return index_components

    def load_component_symbols(
        self,
        index_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> list[str]:
        """Collect index component symbols"""
        index_components: dict[datetime, list[str]] = self.load_component_data(
            index_symbol,
            start,
            end
        )

        component_symbols: set[str] = set()

        for vt_symbols in index_components.values():
            component_symbols.update(vt_symbols)

        return list(component_symbols)

    def load_component_filters(
        self,
        index_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> dict[str, list[tuple[datetime, datetime]]]:
        """Collect index component duration filters"""
        index_components: dict[datetime, list[str]] = self.load_component_data(
            index_symbol,
            start,
            end
        )

        # Get all trading dates and sort
        trading_dates: list[datetime] = sorted(index_components.keys())

        # Initialize component duration dictionary
        component_filters: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)

        # Get all component symbols
        all_symbols: set[str] = set()
        for vt_symbols in index_components.values():
            all_symbols.update(vt_symbols)

        # Iterate through each component to identify its duration in the index
        for vt_symbol in all_symbols:
            period_start: datetime | None = None
            period_end: datetime | None = None

            # Iterate through each trading day to identify continuous holding periods
            for trading_date in trading_dates:
                if vt_symbol in index_components[trading_date]:
                    if period_start is None:
                        period_start = trading_date

                    period_end = trading_date
                else:
                    if period_start and period_end:
                        component_filters[vt_symbol].append((period_start, period_end))
                        period_start = None
                        period_end = None

            # Handle the last holding period
            if period_start and period_end:
                component_filters[vt_symbol].append((period_start, period_end))

        return component_filters

    def add_contract_setting(
        self,
        vt_symbol: str,
        long_rate: float,
        short_rate: float,
        size: float,
        pricetick: float
    ) -> None:
        """Add contract information"""
        contracts: dict = {}

        if self.contract_path.exists():
            with open(self.contract_path, encoding="UTF-8") as f:
                contracts = json.load(f)

        contracts[vt_symbol] = {
            "long_rate": long_rate,
            "short_rate": short_rate,
            "size": size,
            "pricetick": pricetick
        }

        with open(self.contract_path, mode="w+", encoding="UTF-8") as f:
            json.dump(
                contracts,
                f,
                indent=4,
                ensure_ascii=False
            )

    def load_contract_setttings(self) -> dict:
        """Load contract settings"""
        contracts: dict = {}

        if self.contract_path.exists():
            with open(self.contract_path, encoding="UTF-8") as f:
                contracts = json.load(f)

        return contracts

    def save_dataset(self, name: str, dataset: AlphaDataset) -> None:
        """Save dataset"""
        file_path: Path = self.dataset_path.joinpath(f"{name}.pkl")

        with open(file_path, mode="wb") as f:
            pickle.dump(dataset, f)

    def load_dataset(self, name: str) -> AlphaDataset | None:
        """Load dataset"""
        file_path: Path = self.dataset_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Dataset file {name} does not exist")
            return None

        with open(file_path, mode="rb") as f:
            dataset: AlphaDataset = pickle.load(f)
            return dataset

    def remove_dataset(self, name: str) -> bool:
        """Remove dataset"""
        file_path: Path = self.dataset_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Dataset file {name} does not exist")
            return False

        file_path.unlink()
        return True

    def list_all_datasets(self) -> list[str]:
        """List all datasets"""
        return [file.stem for file in self.dataset_path.glob("*.pkl")]

    def save_model(self, name: str, model: AlphaModel) -> None:
        """Save model"""
        file_path: Path = self.model_path.joinpath(f"{name}.pkl")

        with open(file_path, mode="wb") as f:
            pickle.dump(model, f)

    def load_model(self, name: str) -> AlphaModel | None:
        """Load model"""
        file_path: Path = self.model_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Model file {name} does not exist")
            return None

        with open(file_path, mode="rb") as f:
            model: AlphaModel = pickle.load(f)
            return model

    def remove_model(self, name: str) -> bool:
        """Remove model"""
        file_path: Path = self.model_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Model file {name} does not exist")
            return False

        file_path.unlink()
        return True

    def list_all_models(self) -> list[str]:
        """List all models"""
        return [file.stem for file in self.model_path.glob("*.pkl")]

    def save_signal(self, name: str, signal: pl.DataFrame) -> None:
        """Save signal"""
        file_path: Path = self.signal_path.joinpath(f"{name}.parquet")

        signal.write_parquet(file_path)

    def load_signal(self, name: str) -> pl.DataFrame | None:
        """Load signal"""
        file_path: Path = self.signal_path.joinpath(f"{name}.parquet")
        if not file_path.exists():
            logger.error(f"Signal file {name} does not exist")
            return None

        return pl.read_parquet(file_path)

    def remove_signal(self, name: str) -> bool:
        """Remove signal"""
        file_path: Path = self.signal_path.joinpath(f"{name}.parquet")
        if not file_path.exists():
            logger.error(f"Signal file {name} does not exist")
            return False

        file_path.unlink()
        return True

    def list_all_signals(self) -> list[str]:
        """List all signals"""
        return [file.stem for file in self.model_path.glob("*.parquet")]

    def train_model_incremental(
        self,
        model_name: str,
        dataset: AlphaDataset,
        model_type: str = "lgb",
        num_boost_round: int = 100,
        incremental: bool | None = None
    ) -> tuple[AlphaModel, ModelVersion]:
        """
        智能增量训练：自动检测是否增量

        Args:
            model_name: 模型名称
            dataset: 训练数据集
            model_type: 模型类型 ("lgb", "lasso", "mlp")
            num_boost_round: 增量训练的轮数（仅增量模式有效）
            incremental: 是否使用增量模式
                - True: 强制增量训练
                - False: 强制完整重训练
                - None (默认): 自动检测

        Returns:
            tuple[AlphaModel, ModelVersion]: 训练好的模型和版本信息
        """
        from .model.models.lgb_model import LgbModel
        from .model.models.lasso_model import LassoModel
        from .model.models.mlp_model import MlpModel
        import time

        # 检查是否存在现有模型
        existing_version: ModelVersion | None = self.version_manager.get_current_version(model_name)
        existing_model: AlphaModel | None = None

        if existing_version:
            existing_model = self.version_manager.load_model(model_name)

        # 确定训练模式
        use_incremental: bool
        if incremental is not None:
            # 用户强制指定模式，但需要检查模型是否支持增量
            if incremental and existing_model is not None and not existing_model.supports_incremental:
                # 模型不支持增量，强制使用完整训练
                use_incremental = False
            else:
                use_incremental = incremental
        elif existing_model is not None and existing_model.supports_incremental:
            use_incremental = True
        else:
            use_incremental = False

        # 创建模型实例
        model: AlphaModel
        if model_type == "lgb":
            model = LgbModel()
        elif model_type == "lasso":
            model = LassoModel()
        elif model_type == "mlp":
            model = MlpModel()
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # 训练模型
        training_start: float = time.time()

        if use_incremental and existing_model and model.supports_incremental:
            # 增量训练
            logger.info(f"Starting incremental training for model {model_name}")

            # 恢复已有模型状态
            if existing_model.get_training_state():
                model.set_training_state(existing_model.get_training_state())

            # 执行增量训练
            result: dict = model.partial_fit(dataset, num_boost_round=num_boost_round)
            logger.info(f"Incremental training completed: {result}")
        else:
            # 完整重训练
            logger.info(f"Starting full training for model {model_name}")
            model.fit(dataset)

        training_duration: float = time.time() - training_start

        # 获取训练统计信息
        train_loss: float | None = None
        valid_loss: float | None = None

        if hasattr(model, 'model') and model.model is not None:
            try:
                train_loss = model.model.best_score.get("train_0", {}).get("l2")
                valid_loss = model.model.best_score.get("valid_0", {}).get("l2")
            except (AttributeError, KeyError):
                pass

        # 创建版本信息
        train_period = dataset.data_periods.get(Segment.TRAIN, ("", ""))
        valid_period = dataset.data_periods.get(Segment.VALID, ("", ""))

        version: ModelVersion = ModelVersion(
            version_id="",  # 将由 version_manager 生成
            created_at=datetime.now(),
            train_period=train_period,
            valid_period=valid_period,
            n_samples=len(dataset.df) if dataset.df is not None else 0,
            training_duration=training_duration,
            train_loss=train_loss,
            valid_loss=valid_loss,
            is_incremental=use_incremental,
            base_version=existing_version.version_id if use_incremental and existing_version else None,
            description=f"{'增量' if use_incremental else '完整'}训练 - {model_type}",
            tags=[model_type, "incremental" if use_incremental else "full"]
        )

        # 保存模型和版本
        self.version_manager.create_version(model_name, version, model)

        return model, version

    def save_model_with_version(
        self,
        name: str,
        model: AlphaModel,
        dataset: AlphaDataset,
        description: str = "",
        tags: list[str] | None = None,
        training_duration: float | None = None,
        is_incremental: bool | None = None
    ) -> ModelVersion:
        """
        保存模型并创建版本记录

        Args:
            name: 模型名称
            model: AlphaModel 实例
            dataset: 训练数据集
            description: 版本描述
            tags: 版本标签列表
            training_duration: 训练时长（秒），如果未提供则设置为 None
            is_incremental: 是否为增量训练，如果未提供则根据基础版本自动判断

        Returns:
            ModelVersion: 创建的版本信息
        """
        # 获取训练统计信息
        train_loss: float | None = None
        valid_loss: float | None = None
        n_samples: int = 0

        if hasattr(model, 'model') and model.model is not None:
            try:
                train_loss = model.model.best_score.get("train_0", {}).get("l2")
                valid_loss = model.model.best_score.get("valid_0", {}).get("l2")
            except (AttributeError, KeyError):
                pass

        if dataset.df is not None:
            n_samples = len(dataset.df)

        # 检查是否为增量训练（只有存在基础版本时才启用增量模式）
        base_version: ModelVersion | None = self.version_manager.get_current_version(name)

        # 如果未传入 is_incremental，则根据基础版本自动判断
        if is_incremental is None:
            is_incremental = model.supports_incremental and base_version is not None

        # 获取训练周期信息
        train_period = dataset.data_periods.get(Segment.TRAIN, ("", ""))
        valid_period = dataset.data_periods.get(Segment.VALID, ("", ""))

        # 创建版本信息
        version: ModelVersion = ModelVersion(
            version_id="",
            created_at=datetime.now(),
            train_period=train_period,
            valid_period=valid_period,
            n_samples=n_samples,
            training_duration=training_duration,
            train_loss=train_loss,
            valid_loss=valid_loss,
            is_incremental=is_incremental,
            base_version=base_version.version_id if base_version else None,
            description=description,
            tags=tags or []
        )

        # 保存模型
        self.version_manager.create_version(name, version, model)

        logger.info(f"Saved model {name} with version {version.version_id}")
        return version

    def load_model_version(
        self,
        name: str,
        version_id: str | None = None
    ) -> tuple[AlphaModel, ModelVersion]:
        """
        加载指定版本

        Args:
            name: 模型名称
            version_id: 版本 ID，None 表示加载当前版本

        Returns:
            tuple[AlphaModel, ModelVersion]: 模型实例和版本信息

        Raises:
            ValueError: 如果模型或版本不存在
        """
        # 获取版本信息
        version: ModelVersion | None
        if version_id:
            version = self.version_manager.get_version(name, version_id)
        else:
            version = self.version_manager.get_current_version(name)

        if not version:
            raise ValueError(f"Model version not found: {name}" + (f" ({version_id})" if version_id else ""))

        # 加载模型
        model: AlphaModel | None = self.version_manager.load_model(name, version_id)
        if not model:
            raise ValueError(f"Failed to load model: {name}")

        logger.info(f"Loaded model {name} version {version.version_id}")
        return model, version

    def rollback_model(self, name: str, version_id: str) -> bool:
        """
        回滚到指定版本

        Args:
            name: 模型名称
            version_id: 要回滚到的版本 ID

        Returns:
            bool: 回滚是否成功
        """
        result: bool = self.version_manager.rollback(name, version_id)

        if result:
            logger.info(f"Rolled back model {name} to version {version_id}")
        else:
            logger.error(f"Failed to rollback model {name} to version {version_id}")

        return result

    def list_model_versions(self, name: str) -> list[ModelVersion]:
        """
        列出模型的所有版本

        Args:
            name: 模型名称

        Returns:
            list[ModelVersion]: 版本列表（按创建时间倒序）
        """
        return self.version_manager.list_versions(name)

    def delete_model_version(self, name: str, version_id: str) -> bool:
        """
        删除指定版本

        Args:
            name: 模型名称
            version_id: 要删除的版本 ID

        Returns:
            bool: 删除是否成功
        """
        result: bool = self.version_manager.delete_version(name, version_id)

        if result:
            logger.info(f"Deleted model {name} version {version_id}")
        else:
            logger.error(f"Failed to delete model {name} version {version_id}")

        return result

    # Performance monitoring methods

    def get_performance_tracker(
        self,
        model_name: str,
    ) -> PerformanceTracker:
        """
        获取或创建模型性能追踪器

        Args:
            model_name: 模型名称

        Returns:
            性能追踪器实例
        """
        if model_name not in self.performance_trackers:
            self.performance_trackers[model_name] = PerformanceTracker(
                model_name=model_name,
                lab_path=str(self.lab_path),
            )
        return self.performance_trackers[model_name]

    def run_backtest_with_tracking(
        self,
        model_name: str,
        backtest_result: dict[str, any],
        alert_rules: list | None = None,
    ) -> list:
        """
        运行回测并追踪性能

        Args:
            model_name: 模型名称
            backtest_result: 回测结果字典
            alert_rules: 自定义预警规则 (可选)

        Returns:
            触发的预警列表
        """
        tracker = self.get_performance_tracker(model_name)
        rules = alert_rules or DEFAULT_ALERT_RULES

        # 创建性能快照
        now: datetime = datetime.now()

        # 构建指标字典
        metrics_dict: dict[str, float] = backtest_result.get("metrics", {}).copy()

        # 计算标准指标
        returns = backtest_result.get("returns", [])
        if returns and len(returns) > 0:
            import numpy as np

            returns_array = np.array(returns)

            # 基本收益指标
            metrics_dict["total_return"] = float(np.sum(returns_array))
            metrics_dict["avg_return"] = float(np.mean(returns_array))
            metrics_dict["std_return"] = float(np.std(returns_array))

            # 夏普比率
            if len(returns_array) > 1:
                std_dev = float(np.std(returns_array))
                metrics_dict["sharpe_ratio"] = (
                    float(np.mean(returns_array) / std_dev) if std_dev > 0 else 0.0
                )

            # 最大回撤
            cumulative = np.cumsum(returns_array)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = cumulative - running_max
            metrics_dict["max_drawdown"] = float(np.min(drawdown))

        # IC 指标 (如果有预测和目标)
        predictions = backtest_result.get("predictions")
        targets = backtest_result.get("targets")
        if predictions is not None and targets is not None:
            try:
                from scipy.stats import pearsonr, spearmanr

                ic, _ = pearsonr(predictions, targets)
                metrics_dict["ic"] = float(ic)

                rank_ic, _ = spearmanr(predictions, targets)
                metrics_dict["rank_ic"] = float(rank_ic)
            except Exception:
                metrics_dict["ic"] = 0.0
                metrics_dict["rank_ic"] = 0.0

        # 获取历史基准
        baseline_metrics: dict[str, float] = {}
        for metric_name in ["sharpe_ratio", "max_drawdown", "ic", "total_return"]:
            baseline = tracker.get_metric_baseline(metric_name, percentile=50.0)
            if baseline is not None:
                baseline_metrics[metric_name] = baseline

        # 创建性能指标对象
        return_metrics: dict[str, PerformanceMetric] = {}
        risk_metrics: dict[str, PerformanceMetric] = {}
        efficiency_metrics: dict[str, PerformanceMetric] = {}
        prediction_metrics: dict[str, PerformanceMetric] = {}

        # 分类指标
        metric_categories: dict[str, tuple[dict, MetricCategory]] = {
            "total_return": (return_metrics, MetricCategory.RETURN),
            "avg_return": (return_metrics, MetricCategory.RETURN),
            "std_return": (return_metrics, MetricCategory.RETURN),
            "max_drawdown": (risk_metrics, MetricCategory.RISK),
            "downside_risk": (risk_metrics, MetricCategory.RISK),
            "sharpe_ratio": (efficiency_metrics, MetricCategory.EFFICIENCY),
            "information_ratio": (efficiency_metrics, MetricCategory.EFFICIENCY),
            "ic": (prediction_metrics, MetricCategory.PREDICTION),
            "rank_ic": (prediction_metrics, MetricCategory.PREDICTION),
            "excess_return": (efficiency_metrics, MetricCategory.EFFICIENCY),
        }

        for metric_name, metric_value in metrics_dict.items():
            if metric_name in metric_categories:
                metrics_dict_cat, category = metric_categories[metric_name]
                metrics_dict_cat[metric_name] = PerformanceMetric(
                    name=metric_name,
                    value=metric_value,
                    category=category,
                    timestamp=now,
                    baseline=baseline_metrics.get(metric_name),
                )

        # 交易统计
        trading_stats = None
        if "trading_stats" in backtest_result:
            stats_data = backtest_result["trading_stats"]
            trading_stats = TradingStatistics(
                total_trades=stats_data.get("total_trades", 0),
                long_trades=stats_data.get("long_trades", 0),
                short_trades=stats_data.get("short_trades", 0),
                winning_trades=stats_data.get("winning_trades", 0),
                losing_trades=stats_data.get("losing_trades", 0),
                avg_return=stats_data.get("avg_return", 0.0),
                avg_hold_time=stats_data.get("avg_hold_time"),
                turnover_rate=stats_data.get("turnover_rate", 0.0),
            )

        # 创建性能快照
        snapshot = ModelPerformanceSnapshot(
            model_name=model_name,
            timestamp=now,
            return_metrics=return_metrics,
            risk_metrics=risk_metrics,
            efficiency_metrics=efficiency_metrics,
            prediction_metrics=prediction_metrics,
            trading_stats=trading_stats,
            metadata=backtest_result.get("metadata", {}),
        )

        # 记录性能并检查预警
        triggered_alerts = tracker.record_performance(snapshot, rules)

        logger.info(
            f"Recorded performance for model {model_name}, "
            f"triggered {len(triggered_alerts)} alerts"
        )

        return triggered_alerts

    def get_model_performance(
        self,
        model_name: str,
        limit: int | None = None,
    ) -> list[ModelPerformanceSnapshot]:
        """
        获取模型历史性能数据

        Args:
            model_name: 模型名称
            limit: 返回记录数限制

        Returns:
            历史快照列表
        """
        tracker = self.get_performance_tracker(model_name)
        return tracker.get_performance_history(limit=limit)

    def get_active_alerts(
        self,
        model_name: str,
    ) -> list:
        """
        获取模型的活跃预警

        Args:
            model_name: 模型名称

        Returns:
            活跃预警列表
        """
        tracker = self.get_performance_tracker(model_name)
        return tracker.get_active_alerts()

    def acknowledge_alert(
        self,
        model_name: str,
        alert_id: int,
        user: str = "system",
    ) -> bool:
        """
        确认模型预警

        Args:
            model_name: 模型名称
            alert_id: 预警ID
            user: 确认人

        Returns:
            是否成功
        """
        tracker = self.get_performance_tracker(model_name)
        return tracker.acknowledge_alert(alert_id, user)

    def generate_performance_report(
        self,
        model_name: str,
        days: int = 30,
    ) -> dict:
        """
        生成模型性能报告

        Args:
            model_name: 模型名称
            days: 报告天数

        Returns:
            性能报告字典
        """
        tracker = self.get_performance_tracker(model_name)
        return tracker.generate_performance_report(days=days)

    def list_performance_trackers(self) -> list[str]:
        """
        列出所有性能追踪器

        Returns:
            模型名称列表
        """
        return list(self.performance_trackers.keys())
