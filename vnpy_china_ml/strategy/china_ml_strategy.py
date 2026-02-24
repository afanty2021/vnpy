"""
A股机器学习策略基类模块

本模块提供了A股机器学习策略的基类实现，支持：
- 多种机器学习模型（LightGBM、XGBoost、RandomForest等）
- 因子管理
- 信号生成
- 模型重训练

主要类：
- ChinaMLStrategy: A股机器学习策略基类
"""

from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime

from ..model.china_model import ChinaAlphaModel
from ..model.adapters import ChinaTradingAdapter
from ..factors.base import BaseFactor
from ..utils.types import ModelType, SignalType


class ChinaMLStrategy:
    """A股机器学习策略基类

    提供A股机器学习策略的通用框架，包括：
    - 模型管理：支持多种机器学习模型
    - 因子管理：支持多种因子组合
    - 信号生成：基于模型预测生成交易信号
    - 交易适配：集成A股交易规则（T+1、涨跌停）

    Attributes:
        model: 机器学习模型实例
        trading_adapter: A股交易规则适配器
        factors: 因子列表
        is_initialized: 是否已初始化
        last_retrain_date: 最后重训练日期
        retrain_interval_days: 重训练间隔（天）

    Example:
        >>> from vnpy_china_ml.strategy import ChinaMLStrategy
        >>> from vnpy_china_ml.utils.types import ModelType
        >>>
        >>> # 创建策略实例
        >>> strategy = ChinaMLStrategy(model_type=ModelType.LIGHTGBM)
        >>>
        >>> # 初始化
        >>> strategy.initialize()
        >>>
        >>> # 处理K线数据
        >>> bar = {"symbol": "000001.SZ", "close": 10.5, "volume": 1000000}
        >>> signal = strategy.on_bar(bar)
    """

    def __init__(
        self,
        model_type: ModelType = ModelType.LIGHTGBM,
        retrain_interval_days: int = 30
    ):
        """初始化策略

        Args:
            model_type: 机器学习模型类型，默认为LIGHTGBM
            retrain_interval_days: 模型重训练间隔天数，默认30天
        """
        self.model: ChinaAlphaModel = ChinaAlphaModel(model_type)
        self.trading_adapter: ChinaTradingAdapter = ChinaTradingAdapter()
        self.factors: List[BaseFactor] = []
        self.is_initialized: bool = False
        self.last_retrain_date: Optional[datetime] = None
        self.retrain_interval_days: int = retrain_interval_days
        self._current_symbol: Optional[str] = None

    def initialize(self) -> bool:
        """初始化策略

        策略启动时调用，用于：
        - 加载历史数据
        - 初始化模型
        - 预计算因子

        Returns:
            bool: 初始化是否成功
        """
        self.is_initialized = True
        return True

    def add_factor(self, factor: BaseFactor) -> None:
        """添加因子

        Args:
            factor: 因子实例
        """
        if factor not in self.factors:
            self.factors.append(factor)

    def remove_factor(self, factor: BaseFactor) -> None:
        """移除因子

        Args:
            factor: 因子实例
        """
        if factor in self.factors:
            self.factors.remove(factor)

    def get_factors(self) -> List[BaseFactor]:
        """获取所有因子

        Returns:
            List[BaseFactor]: 因子列表
        """
        return self.factors.copy()

    def on_bar(self, bar: Dict) -> Optional[SignalType]:
        """K线数据回调

        每当收到新的调用此方法，进行K线数据时信号处理。

        Args:
            bar: K线数据字典，应包含以下键：
                - symbol: 股票代码（如 '000001.SZ'）
                - datetime: 数据时间
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量

        Returns:
            Optional[SignalType]: 交易信号，如果没有信号则返回None
        """
        if not self.is_initialized:
            return None

        # 保存当前处理的股票
        self._current_symbol = bar.get("symbol")

        # 准备特征
        features = self.prepare_features(bar)

        if len(features) == 0:
            return SignalType.HOLD

        # 预测信号
        return self.predict_signal(features)

    def prepare_features(self, bar: Dict) -> np.ndarray:
        """准备特征

        从K线数据中提取特征向量。

        Args:
            bar: K线数据字典

        Returns:
            np.ndarray: 特征向量
        """
        if not self.factors:
            # 如果没有因子，返回空数组
            return np.array([])

        # TODO: 实际实现需要从数据库或缓存获取历史数据
        # 这里返回空数组作为占位符
        return np.array([])

    def predict_signal(self, features: np.ndarray) -> SignalType:
        """预测信号

        基于特征向量进行预测并生成交易信号。

        Args:
            features: 特征向量

        Returns:
            SignalType: 交易信号
        """
        if len(features) == 0:
            return SignalType.HOLD

        if not self.model.is_trained:
            return SignalType.HOLD

        try:
            # 模型预测
            prediction = self.model.predict(features.reshape(1, -1))
            predicted_return = prediction[0]

            # 根据预测收益率生成信号
            if predicted_return > 0.02:  # 2%阈值
                return SignalType.BUY
            elif predicted_return < -0.02:
                return SignalType.SELL
            else:
                return SignalType.HOLD
        except Exception:
            return SignalType.HOLD

    def should_retrain(self) -> bool:
        """是否需要重新训练模型

        根据重训练间隔和最后训练时间判断是否需要重新训练。

        Returns:
            bool: 是否需要重新训练
        """
        if not self.model.is_trained:
            return True

        if self.last_retrain_date is None:
            return True

        # 计算距离上次训练的天数
        days_since_train = (datetime.now() - self.last_retrain_date).days

        return days_since_train >= self.retrain_interval_days

    def retrain_model(
        self,
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None
    ) -> bool:
        """重新训练模型

        使用新数据重新训练机器学习模型。

        Args:
            X: 特征矩阵，如果为None则使用模型内置数据
            y: 目标变量，如果为None则使用模型内置数据
            feature_names: 特征名称列表

        Returns:
            bool: 训练是否成功
        """
        if X is None or y is None:
            # 如果没有提供训练数据，返回失败
            return False

        try:
            self.model.train(X, y, feature_names=feature_names)
            self.last_retrain_date = datetime.now()
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            Dict[str, Any]: 模型信息字典
        """
        info = self.model.get_model_info()
        info["is_initialized"] = self.is_initialized
        info["last_retrain_date"] = (
            self.last_retrain_date.isoformat() if self.last_retrain_date else None
        )
        info["retrain_interval_days"] = self.retrain_interval_days
        info["n_factors"] = len(self.factors)
        return info

    def get_position(self, symbol: str) -> int:
        """获取持仓数量

        Args:
            symbol: 股票代码

        Returns:
            int: 持仓数量
        """
        holdings = self.trading_adapter.get_holdings()
        return holdings.get(symbol, 0)

    def can_buy(self, symbol: str, current_price: float, target_price: float) -> bool:
        """检查是否可以买入

        Args:
            symbol: 股票代码
            current_price: 当前价格
            target_price: 目标买入价格

        Returns:
            bool: 是否可以买入
        """
        return self.trading_adapter.can_buy(symbol, current_price, target_price)

    def can_sell(
        self,
        symbol: str,
        current_price: float,
        target_price: float,
        volume: int
    ) -> bool:
        """检查是否可以卖出

        Args:
            symbol: 股票代码
            current_price: 当前价格
            target_price: 目标卖出价格
            volume: 卖出数量

        Returns:
            bool: 是否可以卖出
        """
        return self.trading_adapter.can_sell(
            symbol, datetime.now(), current_price, target_price, volume
        )

    def record_buy(self, symbol: str, volume: int) -> None:
        """记录买入操作

        Args:
            symbol: 股票代码
            volume: 买入数量
        """
        self.trading_adapter.record_buy(symbol, datetime.now(), volume)

    def record_sell(self, symbol: str, volume: int) -> int:
        """记录卖出操作

        Args:
            symbol: 股票代码
            volume: 卖出数量

        Returns:
            int: 实际卖出数量
        """
        return self.trading_adapter.record_sell(symbol, volume)

    def update_limit_status(
        self,
        symbol: str,
        is_limit_up: bool,
        is_limit_down: bool = False
    ) -> None:
        """更新涨跌停状态

        Args:
            symbol: 股票代码
            is_limit_up: 是否涨停
            is_limit_down: 是否跌停
        """
        self.trading_adapter.update_limit_status(symbol, is_limit_up, is_limit_down)

    def reset(self) -> None:
        """重置策略状态

        清空持仓、涨跌停记录等信息。
        """
        self.trading_adapter.reset()
        self._current_symbol = None

    def __repr__(self) -> str:
        """返回策略的字符串表示"""
        return (
            f"ChinaMLStrategy("
            f"model={self.model.model_type.value}, "
            f"initialized={self.is_initialized}, "
            f"factors={len(self.factors)}, "
            f"retrain_interval={self.retrain_interval_days}days)"
        )
