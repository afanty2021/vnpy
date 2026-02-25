"""机器学习监控服务

为 vnpy_china_monitor 提供机器学习模型监控服务。
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from vnpy_china_monitor.web.services.strategy_service import StrategyService

from ..monitoring import ModelPerformanceMonitor, PerformanceMetric
from ..online_learning import OnlineLearningManager, OnlineLearningConfig
from ..model.manager import ModelManager


logger = logging.getLogger(__name__)


class MLMonitorService:
    """机器学习监控服务

    提供模型性能监控、在线学习管理等服务。
    """

    def __init__(
        self,
        model_manager: ModelManager,
        alert_engine: Optional[Any] = None,
        event_engine: Optional[Any] = None
    ):
        """初始化ML监控服务

        Args:
            model_manager: 模型管理器
            alert_engine: 告警引擎
            event_engine: 事件引擎
        """
        self.model_manager = model_manager
        self.alert_engine = alert_engine
        self.event_engine = event_engine

        # 创建性能监控器
        self.performance_monitor = ModelPerformanceMonitor(
            model_manager=model_manager,
            alert_engine=alert_engine,
            event_engine=event_engine
        )

        # 创建在线学习管理器
        self.online_learning_manager = OnlineLearningManager(
            model_manager=model_manager
        )

        logger.info("ML监控服务已初始化")

    # ==================== 模型性能监控 ====================

    def record_prediction(
        self,
        model_id: str,
        predictions: List[Any]
    ) -> None:
        """记录预测结果

        Args:
            model_id: 模型ID
            predictions: 预测结果列表
        """
        from ..utils.types import PredictionResult

        # 转换为 PredictionResult
        pred_results = []
        for pred in predictions:
            if isinstance(pred, dict):
                from ..utils.types import SignalType
                pred_result = PredictionResult(
                    symbol=pred.get("symbol", ""),
                    datetime=pred.get("datetime", datetime.now()),
                    predicted_return=pred.get("predicted_return", 0.0),
                    confidence=pred.get("confidence", 0.5),
                    signal=SignalType(pred.get("signal", "hold")),
                    model_name=pred.get("model_name", model_id)
                )
                pred_results.append(pred_result)

        self.performance_monitor.record_prediction(model_id, pred_results)

    def update_actual_returns(
        self,
        model_id: str,
        symbol: str,
        actual_return: float
    ) -> None:
        """更新实际收益率

        Args:
            model_id: 模型ID
            symbol: 股票代码
            actual_return: 实际收益率
        """
        self.performance_monitor.update_actual_returns(
            model_id, symbol, actual_return
        )

        # 同步到在线学习管理器
        self.online_learning_manager.record_prediction_result(
            model_id,
            predicted_return=0.0,  # 需要从缓存中获取
            actual_return=actual_return
        )

    def check_performance(
        self,
        model_id: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """检查模型性能

        Args:
            model_id: 模型ID，None表示检查所有

        Returns:
            性能结果字典
        """
        return self.performance_monitor.check_performance(model_id)

    def generate_performance_report(
        self,
        model_id: str
    ) -> Dict[str, Any]:
        """生成性能报告

        Args:
            model_id: 模型ID

        Returns:
            性能报告
        """
        return self.performance_monitor.generate_report(model_id)

    def detect_performance_decay(
        self,
        model_id: str,
        metric: str = "direction_accuracy",
        threshold: float = 0.1
    ) -> tuple:
        """检测性能衰减

        Args:
            model_id: 模型ID
            metric: 指标名称
            threshold: 衰减阈值

        Returns:
            (是否衰减, 衰减率)
        """
        metric_enum = PerformanceMetric(metric)
        return self.performance_monitor.detect_performance_decay(
            model_id, metric_enum, threshold
        )

    # ==================== 模型管理 ====================

    def get_all_models(self) -> List[Dict[str, Any]]:
        """获取所有模型

        Returns:
            模型信息列表
        """
        models = self.model_manager.get_all_models()

        return [
            {
                "model_id": m.model_id,
                "model_name": m.model_name,
                "model_type": m.model_type.value,
                "is_trained": m.is_trained,
                "training_date": m.training_date.isoformat() if m.training_date else None,
                "accuracy": m.accuracy,
                "status": m.status
            }
            for m in models
        ]

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息

        Args:
            model_id: 模型ID

        Returns:
            模型信息
        """
        metadata = self.model_manager.get_model_metadata(model_id)
        if not metadata:
            return None

        return {
            "model_id": metadata.model_id,
            "model_name": metadata.model_name,
            "model_type": metadata.model_type.value,
            "is_trained": metadata.is_trained,
            "training_date": metadata.training_date.isoformat() if metadata.training_date else None,
            "feature_count": metadata.feature_count,
            "accuracy": metadata.accuracy,
            "status": metadata.status
        }

    def get_all_model_ids(self) -> List[str]:
        """获取所有模型ID

        Returns:
            模型ID列表
        """
        return [m.model_id for m in self.model_manager.get_all_models()]

    # ==================== 在线学习 ====================

    def register_online_learning(
        self,
        model_id: str,
        config: Optional[OnlineLearningConfig] = None
    ) -> bool:
        """注册在线学习

        Args:
            model_id: 模型ID
            config: 在线学习配置

        Returns:
            是否注册成功
        """
        return self.online_learning_manager.register_model(model_id, config)

    def add_training_sample(
        self,
        model_id: str,
        features: List[float],
        label: float,
        **kwargs
    ) -> None:
        """添加训练样本

        Args:
            model_id: 模型ID
            features: 特征向量
            label: 标签值
            **kwargs: 其他参数
        """
        import numpy as np

        self.online_learning_manager.add_sample(
            model_id,
            np.array(features),
            label,
            **kwargs
        )

    def check_and_update_models(
        self,
        model_id: Optional[str] = None
    ) -> Dict[str, Dict]:
        """检查并更新模型

        Args:
            model_id: 模型ID

        Returns:
            更新结果字典
        """
        return self.online_learning_manager.check_and_update(model_id)

    def get_online_learning_info(
        self,
        model_id: str
    ) -> Optional[Dict]:
        """获取在线学习信息

        Args:
            model_id: 模型ID

        Returns:
            学习器信息
        """
        return self.online_learning_manager.get_learner_info(model_id)

    def get_all_online_learning_info(self) -> Dict[str, Dict]:
        """获取所有在线学习信息

        Returns:
            学习器信息字典
        """
        return self.online_learning_manager.get_all_learner_info()

    # ==================== 统计信息 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息

        Returns:
            统计信息字典
        """
        monitor_stats = self.performance_monitor.get_stats()

        return {
            "monitor": monitor_stats,
            "online_learners": len(self.online_learning_manager._learners),
            "total_models": len(self.model_manager.get_all_models())
        }

    # ==================== 服务接口（兼容 StrategyService）====================

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略（兼容接口）

        Returns:
            策略列表
        """
        return self.get_all_models()

    def format_strategy(self, strategy: Dict) -> Dict:
        """格式化策略信息（兼容接口）

        Args:
            strategy: 策略信息

        Returns:
            格式化后的策略信息
        """
        return strategy


def create_ml_monitor_service(
    model_manager: ModelManager,
    alert_engine: Optional[Any] = None,
    event_engine: Optional[Any] = None
) -> MLMonitorService:
    """创建ML监控服务

    Args:
        model_manager: 模型管理器
        alert_engine: 告警引擎
        event_engine: 事件引擎

    Returns:
        ML监控服务实例
    """
    return MLMonitorService(
        model_manager=model_manager,
        alert_engine=alert_engine,
        event_engine=event_engine
    )


__all__ = [
    "MLMonitorService",
    "create_ml_monitor_service",
]
