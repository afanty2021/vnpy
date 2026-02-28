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
from .dataset import AlphaDataset, to_datetime
from .model import AlphaModel, ModelVersion
from .model.version_manager import ModelVersionManager


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
        from .model.models import LgbModel, LassoModel, MlpModel
        import time

        # 检查是否存在现有模型
        existing_version: ModelVersion | None = self.version_manager.get_current_version(model_name)
        existing_model: AlphaModel | None = None

        if existing_version:
            existing_model = self.version_manager.load_model(model_name)

        # 确定训练模式
        use_incremental: bool
        if incremental is not None:
            use_incremental = incremental
        elif existing_model is not None and existing_model.supports_incremental:
            use_incremental = True
        else:
            use_incremental = False

        # 创建模型实例
        model: AlphaModel
        if model_type == "lgb":
            model = LgbModel(dataset)
        elif model_type == "lasso":
            model = LassoModel(dataset)
        elif model_type == "mlp":
            model = MlpModel(dataset)
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
            model.train_model(model_type)

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
        train_period = dataset.data_periods.get("train", ("", ""))
        valid_period = dataset.data_periods.get("valid", ("", ""))

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
        train_period = dataset.data_periods.get("train", ("", ""))
        valid_period = dataset.data_periods.get("valid", ("", ""))

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
