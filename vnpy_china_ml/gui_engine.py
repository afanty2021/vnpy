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
from .model.version_manager import ModelVersionManager
from .model.ab_tester import ModelABTester
from .model.ab_test import ABTestConfig, ABTestResult, ModelVersionInfo
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

        # 版本管理器
        self.version_manager: ModelVersionManager = ModelVersionManager(
            model_manager=self.model_manager
        )

        # A/B测试器
        self.ab_tester: ModelABTester = ModelABTester(
            model_manager=self.model_manager
        )

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
            # 获取数据服务实例（单例）
            from vnpy_china_data import get_data_service
            self.data_service = get_data_service()

            # 如果未连接，尝试连接
            if not self.data_service.connected:
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
            # 处理 model_type 可能是字符串的情况
            if isinstance(model_type, str):
                try:
                    model_type = ModelType(model_type)
                except ValueError:
                    raise ValueError(f"无效的模型类型: {model_type}")

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

        Raises:
            RuntimeError: 当数据加载失败时
        """
        # 导入数据集模块
        try:
            from vnpy_china_ml.dataset import create_alpha_dataset
        except ImportError as e:
            raise RuntimeError(
                f"数据集模块不可用: {e}\n"
                f"请确保已正确安装 vnpy_china_ml 模块"
            )

        self._log("从数据库加载历史数据...")

        # 默认股票列表
        symbols = [
            "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
            "600000.SH", "600036.SH", "600519.SH", "600887.SH",
            "601318.SH", "601398.SH", "601857.SH", "601988.SH"
        ]

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

        self._log(f"数据加载完成: {len(X)}样本, {len(feature_names)}特征")

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
            error_msg = f"模型未找到: {model_id}，请先训练模型"
            self._log(error_msg)
            raise RuntimeError(error_msg)

        try:
            self._log(f"使用模型 {model_id} 进行预测...")

            # 准备预测数据（不使用模拟数据）
            X, symbols_list, names_list = self._prepare_prediction_data(symbols, predict_date)

            if X is None or len(X) == 0:
                raise RuntimeError("预测数据准备失败")

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

        except RuntimeError as e:
            # 重新抛出运行时错误（包含详细信息）
            raise
        except Exception as e:
            error_msg = f"预测失败: {e}\n请检查数据源配置和模型状态"
            self._log(error_msg)
            raise RuntimeError(error_msg) from e

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

        Raises:
            RuntimeError: 当真实数据加载失败时
        """
        # 股票名称映射
        symbol_names = {
            "000001.SZ": "平安银行", "000002.SZ": "万科A",
            "600000.SH": "浦发银行", "600036.SH": "招商银行",
            "600519.SH": "贵州茅台"
        }

        # 导入数据加载模块
        try:
            from vnpy_china_ml.dataset import ChinaDataLoader, Alpha158Calculator
        except ImportError as e:
            raise RuntimeError(
                f"数据集模块不可用: {e}\n"
                f"请确保已安装 vnpy.alpha 模块\n"
                f"安装命令: pip install vnpy-alpha"
            )

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

        # 获取有效的股票列表
        valid_symbols = latest_df["vt_symbol"].to_list()
        valid_names = [symbol_names.get(s, s) for s in valid_symbols]

        self._log(f"预测数据准备完成: {len(X)}只股票, {len(feature_cols)}个特征")

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

        Raises:
            RuntimeError: 当数据加载失败时
        """
        # 尝试使用真实数据计算因子
        from vnpy_china_ml.dataset import ChinaDataLoader, Alpha158Calculator

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

        # 提取特征列
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

    # ==================== 版本管理 ====================

    def get_model_versions(self, model_name: str) -> List[ModelMetadata]:
        """获取模型的所有版本

        Args:
            model_name: 模型名称

        Returns:
            版本历史列表
        """
        return self.version_manager.get_version_history(model_name)

    def get_version_tree(self, model_name: str) -> List[Dict]:
        """获取模型版本树

        Args:
            model_name: 模型名称

        Returns:
            版本树列表（包含父子关系）
        """
        return self.version_manager.get_version_tree(model_name)

    def create_model_version(
        self,
        model_name: str,
        version: str,
        tag: str = "development",
        changelog: str = ""
    ) -> Optional[str]:
        """创建模型新版本

        Args:
            model_name: 模型名称
            version: 版本号（如 "1.0.0"）
            tag: 版本标签
            changelog: 变更日志

        Returns:
            新版本模型ID
        """
        new_id = self.version_manager.create_version(
            model_name=model_name,
            version=version,
            tag=tag,
            changelog=changelog
        )

        if new_id:
            self._log(f"已创建新版本: {model_name} v{version} ({new_id})")
        else:
            self._log(f"创建版本失败: {model_name} v{version}")

        return new_id

    def rollback_model(self, model_id: str) -> bool:
        """回滚模型到指定版本

        Args:
            model_id: 目标版本模型ID

        Returns:
            是否回滚成功
        """
        result = self.version_manager.rollback_to_version(model_id)

        if result:
            self._log(f"已回滚到版本: {model_id}")
        else:
            self._log(f"回滚失败: {model_id}")

        return result

    def compare_model_versions(self, model_id_1: str, model_id_2: str) -> Dict:
        """对比两个模型版本

        Args:
            model_id_1: 模型1 ID
            model_id_2: 模型2 ID

        Returns:
            对比结果字典
        """
        return self.version_manager.compare_versions(model_id_1, model_id_2)

    def set_production_version(self, model_id: str) -> bool:
        """设置生产版本

        Args:
            model_id: 模型ID

        Returns:
            是否设置成功
        """
        result = self.version_manager.set_production_version(model_id)

        if result:
            self._log(f"已设置生产版本: {model_id}")
        else:
            self._log(f"设置生产版本失败: {model_id}")

        return result

    def get_production_version(self, model_name: str) -> Optional[ModelMetadata]:
        """获取生产版本

        Args:
            model_name: 模型名称

        Returns:
            生产版本的元数据
        """
        return self.version_manager.get_production_version(model_name)

    def tag_model_version(self, model_id: str, tag: str) -> bool:
        """为模型版本打标签

        Args:
            model_id: 模型ID
            tag: 标签（production/staging/development）

        Returns:
            是否打标签成功
        """
        result = self.version_manager.tag_version(model_id, tag)

        if result:
            self._log(f"已为版本打标签: {model_id} -> {tag}")
        else:
            self._log(f"打标签失败: {model_id}")

        return result

    # ==================== A/B测试 ====================

    def create_ab_test(
        self,
        test_name: str,
        model_ids: List[str],
        start_date: date,
        end_date: date,
        metrics: Optional[List[str]] = None
    ) -> Optional[str]:
        """创建A/B测试

        Args:
            test_name: 测试名称
            model_ids: 参与测试的模型ID列表
            start_date: 测试数据开始日期
            end_date: 测试数据结束日期
            metrics: 评估指标列表

        Returns:
            测试ID
        """
        config = ABTestConfig(
            test_name=test_name,
            model_ids=model_ids,
            test_data_start=start_date,
            test_data_end=end_date,
            metrics=metrics or ["accuracy", "ic"]
        )

        test_id = self.ab_tester.create_test(config)

        if test_id:
            self._log(f"已创建A/B测试: {test_name} ({test_id})")
        else:
            self._log(f"创建A/B测试失败: {test_name}")

        return test_id

    def run_ab_test(
        self,
        test_id: str,
        X: np.ndarray,
        y: np.ndarray,
        metrics: Optional[List[str]] = None
    ) -> Optional[ABTestResult]:
        """运行A/B测试

        Args:
            test_id: 测试ID
            X: 测试特征矩阵
            y: 测试目标变量
            metrics: 评估指标列表

        Returns:
            测试结果
        """
        self._log(f"正在运行A/B测试: {test_id}...")

        result = self.ab_tester.run_test(test_id, X, y, metrics)

        if result:
            self._log(f"A/B测试完成: {result.test_name}")
            if result.winner:
                self._log(f"推荐模型: {result.winner}")
            if result.significance is not None:
                sig_status = "显著" if result.is_significant() else "不显著"
                self._log(f"统计显著性: {sig_status} (p={result.significance:.4f})")
        else:
            self._log(f"A/B测试失败: {test_id}")

        return result

    def get_ab_test_results(self, test_id: str) -> Optional[ABTestResult]:
        """获取A/B测试结果

        Args:
            test_id: 测试ID

        Returns:
            测试结果
        """
        return self.ab_tester.get_test_result(test_id)

    def get_ab_test_history(self) -> List[ABTestResult]:
        """获取A/B测试历史

        Returns:
            所有测试结果列表
        """
        return self.ab_tester.get_test_history()

    def compare_models(
        self,
        model_ids: List[str],
        X: np.ndarray,
        y: np.ndarray,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """快速对比多个模型

        Args:
            model_ids: 模型ID列表
            X: 特征矩阵
            y: 目标变量
            metrics: 评估指标列表

        Returns:
            模型ID到指标结果的映射
        """
        return self.ab_tester.compare_models(model_ids, X, y, metrics)


__all__ = ["ChinaMlGuiEngine"]
