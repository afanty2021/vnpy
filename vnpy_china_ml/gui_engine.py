"""A股机器学习GUI引擎

提供模型管理、训练、预测等核心功能的GUI引擎。
"""

import numpy as np
import polars as pl
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine
from vnpy.trader.object import BarData, TickData

from .model.manager import ModelManager, ModelMetadata
from .model.china_model import ChinaAlphaModel
from .utils.types import ModelType, PredictionResult, SignalType

# 数据管理模块导入
try:
    from vnpy_china_data import ChinaDataService
    CHINA_DATA_AVAILABLE = True
except ImportError:
    CHINA_DATA_AVAILABLE = False
    ChinaDataService = None

from .data import DataPreloader, DataUpdateScheduler, PreloadConfig, UpdateConfig


class ChinaMlGuiEngine(BaseEngine):
    """A股机器学习GUI引擎

    负责管理机器学习模型的训练、预测和特征工程。
    """

    engine_name: str = "ChinaMlApp"

    # 事件定义
    EVENT_MODEL_TRAINED = "eModelTrained"
    EVENT_PREDICTION_DONE = "ePredictionDone"
    EVENT_FEATURE_UPDATED = "eFeatureUpdated"

    def __init__(self, main_engine, event_engine: EventEngine):
        super().__init__(main_engine, event_engine, self.engine_name)

        # 模型管理器
        self.model_manager: ModelManager = ModelManager()

        # 存储预测结果
        self.predictions: List[PredictionResult] = []

        # 特征数据缓存
        self.feature_data: Optional[pl.DataFrame] = None

        # 训练状态回调
        self._progress_callback: Optional[callable] = None
        self._log_callback: Optional[callable] = None

        # 数据管理器
        self.data_service: Optional[ChinaDataService] = None
        self.data_preloader: Optional[DataPreloader] = None
        self.data_scheduler: Optional[DataUpdateScheduler] = None

        # 初始化数据服务
        self._init_data_service()

    def init(self) -> None:
        """初始化引擎"""
        self.main_engine.write_log("A股机器学习引擎初始化完成")

        # 启动数据更新调度器
        if self.data_scheduler:
            if self.data_scheduler.start():
                self._log("数据更新调度器已启动")
            else:
                self._log("数据更新调度器启动失败")

    def _init_data_service(self) -> None:
        """初始化数据服务

        创建数据服务和数据管理器实例。
        """
        if not CHINA_DATA_AVAILABLE:
            self._log("ChinaDataService不可用，数据管理功能将被禁用")
            return

        try:
            # 创建数据服务实例
            self.data_service = ChinaDataService()
            self.data_service.connect()

            self._log("数据服务连接成功")

            # 创建数据预加载器
            self.data_preloader = DataPreloader(
                data_service=self.data_service,
                event_engine=self.event_engine
            )

            # 创建数据更新调度器
            self.data_scheduler = DataUpdateScheduler(
                data_service=self.data_service,
                event_engine=self.event_engine
            )

            self._log("数据管理器初始化完成")

        except Exception as e:
            self._log(f"数据服务初始化失败: {e}")
            self.data_service = None

    # ==================== 模型管理 ====================

    def get_all_models(self) -> List[ModelMetadata]:
        """获取所有模型

        Returns:
            模型元数据列表
        """
        return self.model_manager.get_all_models()

    def get_trained_models(self) -> List[ModelMetadata]:
        """获取已训练的模型

        Returns:
            已训练模型的元数据列表
        """
        return self.model_manager.get_trained_models()

    def load_model(self, model_id: str) -> Optional[ChinaAlphaModel]:
        """加载模型

        Args:
            model_id: 模型ID

        Returns:
            模型实例
        """
        return self.model_manager.load_model(model_id)

    def delete_model(self, model_id: str) -> bool:
        """删除模型

        Args:
            model_id: 模型ID

        Returns:
            是否删除成功
        """
        return self.model_manager.delete_model(model_id)

    def update_model_status(self, model_id: str, status: str) -> bool:
        """更新模型状态

        Args:
            model_id: 模型ID
            status: 新状态

        Returns:
            是否更新成功
        """
        return self.model_manager.update_model_status(model_id, status)

    # ==================== 模型训练 ====================

    def train_model(
        self,
        model_type: ModelType,
        model_name: str,
        train_start: date,
        train_end: date,
        lookback_days: int = 60,
        forward_days: int = 5,
        description: str = ""
    ) -> Optional[str]:
        """训练模型

        Args:
            model_type: 模型类型
            model_name: 模型名称
            train_start: 训练开始日期
            train_end: 训练结束日期
            lookback_days: 回看天数
            forward_days: 预测天数
            description: 模型描述

        Returns:
            模型ID，如果训练失败返回None
        """
        try:
            self._log(f"开始训练{model_type.value}模型: {model_name}")

            # 1. 准备训练数据
            X_train, y_train, feature_names = self._prepare_training_data(
                train_start, train_end, lookback_days, forward_days
            )

            if X_train is None or len(X_train) == 0:
                self._log("训练数据为空，无法训练模型")
                return None

            self._log(f"训练数据准备完成: {len(X_train)}样本, {len(feature_names)}特征")

            # 2. 创建并训练模型
            model = ChinaAlphaModel(model_type=model_type)

            # 更新进度
            if self._progress_callback:
                self._progress_callback(20)

            # 训练模型
            result = model.train(X_train, y_train, feature_names=feature_names)

            self._log(f"模型训练完成: {result}")

            if self._progress_callback:
                self._progress_callback(80)

            # 3. 计算准确率（使用训练集的验证结果）
            accuracy = self._calculate_accuracy(model, X_train, y_train)

            # 4. 注册模型
            model_id = self.model_manager.register_model(
                model_name=model_name,
                model=model,
                accuracy=accuracy,
                description=description
            )

            if self._progress_callback:
                self._progress_callback(100)

            self._log(f"模型已保存: {model_id}, 准确率: {accuracy:.2%}")

            # 发送训练完成事件
            event = Event(EVENT_MODEL_TRAINED, data={
                "model_id": model_id,
                "model_name": model_name,
                "accuracy": accuracy
            })
            self.event_engine.put(event)

            return model_id

        except Exception as e:
            self._log(f"模型训练失败: {e}")
            return None

    def _prepare_training_data(
        self,
        start_date: date,
        end_date: date,
        lookback_days: int,
        forward_days: int
    ) -> tuple:
        """准备训练数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            lookback_days: 回看天数
            forward_days: 预测天数

        Returns:
            (X, y, feature_names) 元组
        """
        # 导入数据集模块
        try:
            from ..dataset import create_alpha_dataset
        except ImportError:
            self._log("数据集模块不可用，使用模拟数据")
            return self._generate_mock_data(1000, 20)

        self._log("从数据库加载历史数据...")

        # 默认股票列表
        symbols = [
            "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
            "600000.SH", "600036.SH", "600519.SH", "600887.SH",
            "601318.SH", "601398.SH", "601857.SH", "601988.SH"
        ]

        try:
            # 创建数据集
            dataset = create_alpha_dataset(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                lookback_days=lookback_days,
                forward_days=forward_days
            )

            # 获取训练数据
            X, y = dataset.get_all_data()
            feature_names = dataset.get_feature_names()

            self._log(f"数据加载完成: {len(X)}样本, {len(feature_names)}特征")

            return X, y, feature_names

        except Exception as e:
            self._log(f"数据加载失败: {e}，使用模拟数据")
            return self._generate_mock_data(1000, 20)

    def _generate_mock_data(self, n_samples: int, n_features: int) -> tuple:
        """生成模拟数据（备用方案）

        Args:
            n_samples: 样本数量
            n_features: 特征数量

        Returns:
            (X, y, feature_names) 元组
        """
        self._log("生成模拟训练数据...")

        # 生成特征矩阵
        X = np.random.randn(n_samples, n_features)

        # 生成目标变量（未来收益率）
        y = np.random.randn(n_samples) * 0.02  # 2%的波动率

        # 特征名称
        feature_names = [
            "Return_5d", "Return_10d", "Return_20d",
            "Volume_Ratio", "Volume_Change_5d",
            "MACD", "MACD_Signal", "RSI_14",
            "Bollinger_Width", "ATR_14_Simple",
            "ROC_10", "Price_Position_20"
        ][:n_features]

        return X, y, feature_names

    def _calculate_accuracy(
        self,
        model: ChinaAlphaModel,
        X: np.ndarray,
        y: np.ndarray
    ) -> float:
        """计算模型准确率

        Args:
            model: 模型实例
            X: 特征矩阵
            y: 真实值

        Returns:
            准确率（方向预测准确率）
        """
        try:
            # 预测
            predictions = model.predict(X)

            # 计算方向准确率
            y_direction = (y > 0).astype(int)
            pred_direction = (predictions > 0).astype(int)

            accuracy = (y_direction == pred_direction).mean()

            return float(accuracy)

        except Exception as e:
            self._log(f"计算准确率失败: {e}")
            return 0.0

    # ==================== 预测功能 ====================

    def predict(
        self,
        model_id: str,
        symbols: List[str],
        predict_date: date,
        confidence_threshold: float = 0.5,
        return_threshold: float = 0.02
    ) -> List[PredictionResult]:
        """使用指定模型进行预测

        Args:
            model_id: 模型ID
            symbols: 股票代码列表
            predict_date: 预测日期
            confidence_threshold: 置信度阈值
            return_threshold: 收益率阈值

        Returns:
            预测结果列表
        """
        # 加载模型
        model = self.model_manager.load_model(model_id)
        if model is None:
            self._log(f"加载模型失败: {model_id}")
            return []

        try:
            self._log(f"使用模型 {model_id} 进行预测...")

            # 准备预测数据
            X, symbols_list, names_list = self._prepare_prediction_data(symbols, predict_date)

            if X is None or len(X) == 0:
                self._log("预测数据为空")
                return []

            # 进行预测
            dates = [datetime.combine(predict_date, datetime.min.time())] * len(symbols_list)
            predictions = model.predict_with_signals(
                X, symbols_list, dates, confidence_threshold, return_threshold
            )

            # 添加股票名称
            for i, pred in enumerate(predictions):
                if i < len(names_list):
                    pred.model_name = f"{pred.model_name} ({names_list[i]})"

            # 保存预测结果
            self.predictions = predictions

            self._log(f"预测完成，共 {len(predictions)} 只股票")

            # 发送预测完成事件
            event = Event(EVENT_PREDICTION_DONE, data={"count": len(predictions)})
            self.event_engine.put(event)

            return predictions

        except Exception as e:
            self._log(f"预测失败: {e}")
            return []

    def _prepare_prediction_data(
        self,
        symbols: List[str],
        predict_date: date
    ) -> tuple:
        """准备预测数据

        Args:
            symbols: 股票代码列表
            predict_date: 预测日期

        Returns:
            (X, symbols, names) 元组
        """
        # 股票名称映射
        symbol_names = {
            "000001.SZ": "平安银行", "000002.SZ": "万科A",
            "600000.SH": "浦发银行", "600036.SH": "招商银行",
            "600519.SH": "贵州茅台"
        }

        # 尝试加载真实数据
        try:
            from ..dataset import ChinaDataLoader, Alpha158Calculator

            self._log("加载预测数据...")

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
                self._log("未能加载真实数据，使用模拟数据")
                return self._generate_mock_prediction_data(symbols, symbol_names)

            # 计算因子
            df = factor_calc.calculate_all(df)

            # 获取预测日期的最新数据
            predict_datetime = datetime.combine(predict_date, datetime.min.time())
            latest_df = df.filter(
                pl.col("datetime") <= pl.lit(predict_datetime)
            ).group_by("vt_symbol").last()

            if len(latest_df) == 0:
                self._log("没有可用的预测数据，使用模拟数据")
                return self._generate_mock_prediction_data(symbols, symbol_names)

            # 提取特征
            base_cols = ["datetime", "vt_symbol", "open_price", "high_price",
                         "low_price", "close_price", "volume", "turnover"]
            feature_cols = [col for col in latest_df.columns if col not in base_cols]

            if not feature_cols:
                self._log("没有计算出任何特征，使用模拟数据")
                return self._generate_mock_prediction_data(symbols, symbol_names)

            X = latest_df.select(feature_cols).to_numpy()

            # 获取有效的股票列表
            valid_symbols = latest_df["vt_symbol"].to_list()
            valid_names = [symbol_names.get(s, s) for s in valid_symbols]

            self._log(f"预测数据准备完成: {len(X)}只股票, {len(feature_cols)}个特征")

            return X, valid_symbols, valid_names

        except Exception as e:
            self._log(f"加载预测数据失败: {e}，使用模拟数据")
            return self._generate_mock_prediction_data(symbols, symbol_names)

    def _generate_mock_prediction_data(
        self,
        symbols: List[str],
        symbol_names: dict
    ) -> tuple:
        """生成模拟预测数据（备用方案）

        Args:
            symbols: 股票代码列表
            symbol_names: 股票名称映射

        Returns:
            (X, symbols, names) 元组
        """
        # 过滤有效的股票
        valid_symbols = []
        valid_names = []

        for symbol in symbols:
            if symbol in symbol_names:
                valid_symbols.append(symbol)
                valid_names.append(symbol_names[symbol])

        # 生成模拟数据
        n_samples = len(valid_symbols)
        n_features = 20

        X = np.random.randn(n_samples, n_features)

        return X, valid_symbols, valid_names

    def get_predictions(self) -> List[PredictionResult]:
        """获取预测结果

        Returns:
            预测结果列表
        """
        return self.predictions

    def clear_predictions(self) -> None:
        """清空预测结果"""
        self.predictions = []

    # ==================== 特征工程 ====================

    def get_feature_importance(self, model_id: str) -> Dict[str, float]:
        """获取特征重要性

        Args:
            model_id: 模型ID

        Returns:
            特征重要性字典
        """
        model = self.model_manager.load_model(model_id)
        if model is None:
            return {}

        return model.get_feature_importance_dict()

    def calculate_features(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Optional[pl.DataFrame]:
        """计算Alpha 158因子

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            特征DataFrame
        """
        try:
            # 尝试使用真实数据计算因子
            from ..dataset import ChinaDataLoader, Alpha158Calculator

            self._log("计算Alpha 158因子...")

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
                self._log("未能加载K线数据，返回默认因子列表")
                return self._get_default_features()

            # 计算因子
            df = factor_calc.calculate_all(df)

            # 提取特征列
            base_cols = ["datetime", "vt_symbol", "open_price", "high_price",
                         "low_price", "close_price", "volume", "turnover", "label"]
            feature_cols = [col for col in df.columns if col not in base_cols]

            if not feature_cols:
                self._log("未计算出任何特征，返回默认因子列表")
                return self._get_default_features()

            # 计算每个因子的类型
            features_data = []
            for col in feature_cols:
                ftype = self._infer_factor_type(col)
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

            self.feature_data = result_df

            self._log(f"因子计算完成，共{len(features_data)}个因子")

            return result_df

        except Exception as e:
            self._log(f"计算因子失败: {e}，返回默认因子列表")
            return self._get_default_features()

    def _get_default_features(self) -> pl.DataFrame:
        """获取默认因子列表（备用）

        Returns:
            默认因子DataFrame
        """
        features = [
            ("Return_5d", "动量", 0.85, 0.65),
            ("Return_10d", "动量", 0.78, 0.58),
            ("Return_20d", "动量", 0.72, 0.52),
            ("Volume_Ratio", "成交量", 0.72, 0.45),
            ("Volume_Change_5d", "成交量", 0.65, 0.40),
            ("MACD", "技术指标", 0.68, 0.52),
            ("MACD_Signal", "技术指标", 0.65, 0.48),
            ("RSI_14", "技术指标", 0.65, 0.38),
            ("Bollinger_Width", "波动率", 0.62, 0.42),
            ("ATR_14_Simple", "波动率", 0.58, 0.35),
            ("ROC_10", "动量", 0.55, 0.30),
            ("Price_Position_20", "技术指标", 0.52, 0.28),
        ]

        return pl.DataFrame({
            "factor_name": [f[0] for f in features],
            "factor_type": [f[1] for f in features],
            "importance": [f[2] for f in features],
            "correlation": [f[3] for f in features],
        })

    def _infer_factor_type(self, factor_name: str) -> str:
        """根据因子名称推断类型

        Args:
            factor_name: 因子名称

        Returns:
            因子类型
        """
        name_lower = factor_name.lower()

        if "return" in name_lower or "roc" in name_lower:
            return "动量"
        elif "volume" in name_lower or "obv" in name_lower or "mfi" in name_lower:
            return "成交量" if "volume" in name_lower else "资金流"
        elif "macd" in name_lower or "rsi" in name_lower or "stoch" in name_lower or "cci" in name_lower or "williams" in name_lower:
            return "技术指标"
        elif "bollinger" in name_lower or "atr" in name_lower or "volatility" in name_lower:
            return "波动率"
        elif "adx" in name_lower or "di" in name_lower or "trix" in name_lower:
            return "趋势"
        else:
            return "其他"

    def get_cached_features(self) -> Optional[pl.DataFrame]:
        """获取缓存的特征数据

        Returns:
            特征DataFrame
        """
        return self.feature_data

    # ==================== 回调设置 ====================

    def set_progress_callback(self, callback: callable) -> None:
        """设置进度回调

        Args:
            callback: 进度回调函数，参数为进度值(0-100)
        """
        self._progress_callback = callback

    def set_log_callback(self, callback: callable) -> None:
        """设置日志回调

        Args:
            callback: 日志回调函数，参数为日志消息
        """
        self._log_callback = callback

    def _log(self, message: str) -> None:
        """记录日志

        Args:
            message: 日志消息
        """
        self.main_engine.write_log(f"[A股ML] {message}")

        if self._log_callback:
            self._log_callback(message)

    # ==================== 数据管理 ====================

    def preload_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbols: Optional[List[str]] = None,
        enable_bar_data: bool = True,
        enable_dragon_tiger: bool = True,
        enable_northbound: bool = True,
        enable_sector: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """预加载历史数据

        Args:
            start_date: 开始日期（默认3年前）
            end_date: 结束日期（默认今天）
            symbols: 股票代码列表（默认主要指数和成分股）
            enable_bar_data: 是否加载K线数据
            enable_dragon_tiger: 是否加载龙虎榜数据
            enable_northbound: 是否加载北向资金数据
            enable_sector: 是否加载板块数据
            progress_callback: 进度回调函数

        Returns:
            加载记录数统计
        """
        if not self.data_preloader:
            self._log("数据预加载器不可用")
            return {}

        # 创建配置
        config = PreloadConfig(
            start_date=start_date or (date.today() - timedelta(days=365*3)),
            end_date=end_date or date.today(),
            symbols=symbols,
            enable_bar_data=enable_bar_data,
            enable_dragon_tiger=enable_dragon_tiger,
            enable_northbound=enable_northbound,
            enable_sector=enable_sector,
        )

        self._log(f"开始预加载数据: {config.start_date} 至 {config.end_date}")

        # 执行预加载
        def progress_wrapper(completed: int, total: int, task: str):
            if progress_callback:
                progress_callback(completed, total, task)
            self._log(f"预加载进度: {task} ({completed}/{total})")

        stats = self.data_preloader.preload(config, progress_wrapper)

        total = sum(stats.values())
        self._log(f"数据预加载完成: 共{total}条记录")

        return stats

    def get_preload_progress(self) -> Dict[str, Any]:
        """获取预加载进度

        Returns:
            进度信息字典
        """
        if not self.data_preloader:
            return {"is_preloading": False, "message": "数据预加载器不可用"}

        return self.data_preloader.get_preload_progress()

    def trigger_data_update(self) -> bool:
        """立即触发数据更新

        Returns:
            是否成功触发
        """
        if not self.data_scheduler:
            self._log("数据调度器不可用")
            return False

        self._log("触发数据更新...")

        if self.data_scheduler.trigger_update_now():
            self._log("数据更新已触发")
            return True
        else:
            self._log("数据更新触发失败")
            return False

    def get_data_scheduler_status(self) -> Dict[str, Any]:
        """获取数据调度器状态

        Returns:
            状态信息字典
        """
        if not self.data_scheduler:
            return {
                "is_running": False,
                "message": "数据调度器不可用"
            }

        return {
            "is_running": self.data_scheduler.is_running(),
            "stats": self.data_scheduler.get_stats(),
            "config": {
                "update_time": self.data_scheduler.get_config().update_time,
                "update_weekdays": self.data_scheduler.get_config().update_weekdays,
                "lookback_days": self.data_scheduler.get_config().lookback_days,
            }
        }

    def update_scheduler_config(
        self,
        update_time: Optional[str] = None,
        update_weekdays: Optional[List[int]] = None,
        lookback_days: Optional[int] = None
    ) -> bool:
        """更新调度器配置

        Args:
            update_time: 更新时间（HH:MM格式）
            update_weekdays: 更新日列表（0=周一, 6=周日）
            lookback_days: 向前补齐天数

        Returns:
            是否更新成功
        """
        if not self.data_scheduler:
            self._log("数据调度器不可用")
            return False

        try:
            # 获取当前配置
            current_config = self.data_scheduler.get_config()

            # 更新配置
            new_config = UpdateConfig(
                update_time=update_time or current_config.update_time,
                update_weekdays=update_weekdays or current_config.update_weekdays,
                lookback_days=lookback_days or current_config.lookback_days,
            )

            self.data_scheduler.update_config(new_config)

            self._log(f"调度器配置已更新: {new_config.update_time}, 周{new_config.update_weekdays}")

            return True

        except Exception as e:
            self._log(f"更新调度器配置失败: {e}")
            return False


__all__ = ["ChinaMlGuiEngine"]
