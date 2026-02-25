"""模型性能监控器

监控机器学习模型的预测性能，检测性能衰减并触发告警。
"""

import numpy as np
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from vnpy.event import EventEngine, Event
from vnpy_china_monitor.alert.engine import AlertEngine
from vnpy_china_monitor.alert.types import AlertSeverity, AlertPriority

from ..model.manager import ModelManager
from ..utils.types import PredictionResult, SignalType


class PerformanceMetric(Enum):
    """性能指标类型"""
    DIRECTION_ACCURACY = "direction_accuracy"  # 方向准确率
    IC = "ic"  # 信息系数
    RANK_IC = "rank_ic"  # 排名信息系数
    SHARPE = "sharpe"  # 夏普比率
    MAX_DRAWDOWN = "max_drawdown"  # 最大回撤
    WIN_RATE = "win_rate"  # 胜率


@dataclass
class ModelPerformanceSnapshot:
    """模型性能快照

    Attributes:
        model_id: 模型ID
        model_name: 模型名称
        timestamp: 快照时间
        actual_returns: 实际收益率序列
        predicted_returns: 预测收益率序列
        directions: 预测方向序列
        confidence_scores: 置信度序列
    """
    model_id: str
    model_name: str
    timestamp: datetime
    actual_returns: np.ndarray = field(default_factory=lambda: np.array([]))
    predicted_returns: np.ndarray = field(default_factory=lambda: np.array([]))
    directions: List[SignalType] = field(default_factory=list)
    confidence_scores: np.ndarray = field(default_factory=lambda: np.array([]))

    def calculate_metrics(self) -> Dict[str, float]:
        """计算性能指标

        Returns:
            性能指标字典
        """
        if len(self.actual_returns) == 0 or len(self.predicted_returns) == 0:
            return {}

        metrics = {}

        # 方向准确率
        if len(self.directions) > 0:
            actual_directions = np.sign(self.actual_returns)
            pred_directions = np.array([
                1 if d == SignalType.BUY else (-1 if d == SignalType.SELL else 0)
                for d in self.directions
            ])
            # 只考虑非持仓方向的预测
            valid_mask = pred_directions != 0
            if valid_mask.sum() > 0:
                accuracy = (actual_directions[valid_mask] == pred_directions[valid_mask]).mean()
                metrics[PerformanceMetric.DIRECTION_ACCURACY.value] = float(accuracy)

        # IC (信息系数)
        if len(self.actual_returns) == len(self.predicted_returns):
            try:
                ic = np.corrcoef(self.actual_returns, self.predicted_returns)[0, 1]
                if not np.isnan(ic):
                    metrics[PerformanceMetric.IC.value] = float(ic)
            except Exception:
                pass

        # 胜率
        if len(self.actual_returns) > 0:
            win_rate = (self.actual_returns > 0).mean()
            metrics[PerformanceMetric.WIN_RATE.value] = float(win_rate)

        # 平均置信度
        if len(self.confidence_scores) > 0:
            avg_confidence = float(self.confidence_scores.mean())
            metrics["avg_confidence"] = avg_confidence

        return metrics


@dataclass
class PerformanceThreshold:
    """性能阈值配置

    Attributes:
        metric: 指标类型
        warning_threshold: 警告阈值
        critical_threshold: 严重阈值
        enabled: 是否启用
    """
    metric: PerformanceMetric
    warning_threshold: float
    critical_threshold: float
    enabled: bool = True


class ModelPerformanceMonitor:
    """模型性能监控器

    持续监控机器学习模型的预测性能，检测性能衰减并触发告警。

    Features:
    - 实时跟踪预测结果与实际收益
    - 计算多种性能指标（准确率、IC、夏普比率等）
    - 检测性能衰减趋势
    - 触发告警当性能低于阈值
    - 生成性能报告
    """

    # 事件定义
    EVENT_MODEL_PERFORMANCE_UPDATE = "eModelPerformanceUpdate"
    EVENT_MODEL_PERFORMANCE_ALERT = "eModelPerformanceAlert"

    def __init__(
        self,
        model_manager: ModelManager,
        alert_engine: Optional[AlertEngine] = None,
        event_engine: Optional[EventEngine] = None,
        window_size: int = 100,
        check_interval: int = 3600
    ):
        """初始化性能监控器

        Args:
            model_manager: 模型管理器
            alert_engine: 告警引擎（可选）
            event_engine: 事件引擎（可选）
            window_size: 性能计算窗口大小
            check_interval: 检查间隔（秒）
        """
        self.model_manager = model_manager
        self.alert_engine = alert_engine
        self.event_engine = event_engine

        self.window_size = window_size
        self.check_interval = check_interval

        # 预测结果缓存 {model_id: deque of predictions}
        self._predictions_cache: Dict[str, deque] = {}

        # 性能历史 {model_id: list of snapshots}
        self._performance_history: Dict[str, List[ModelPerformanceSnapshot]] = {}

        # 性能阈值配置
        self._thresholds: List[PerformanceThreshold] = [
            PerformanceThreshold(
                PerformanceMetric.DIRECTION_ACCURACY,
                warning_threshold=0.55,
                critical_threshold=0.50
            ),
            PerformanceThreshold(
                PerformanceMetric.IC,
                warning_threshold=0.05,
                critical_threshold=0.02
            ),
            PerformanceThreshold(
                PerformanceMetric.WIN_RATE,
                warning_threshold=0.50,
                critical_threshold=0.45
            ),
        ]

        # 运行状态
        self._running = False

    def record_prediction(
        self,
        model_id: str,
        predictions: List[PredictionResult]
    ) -> None:
        """记录预测结果

        Args:
            model_id: 模型ID
            predictions: 预测结果列表
        """
        if model_id not in self._predictions_cache:
            self._predictions_cache[model_id] = deque(maxlen=self.window_size)

        for pred in predictions:
            self._predictions_cache[model_id].append({
                "symbol": pred.symbol,
                "datetime": pred.datetime,
                "predicted_return": pred.predicted_return,
                "signal": pred.signal,
                "confidence": pred.confidence,
                "actual_return": None,  # 等待后续更新
            })

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
        if model_id not in self._predictions_cache:
            return

        # 查找匹配的预测记录
        for record in reversed(self._predictions_cache[model_id]):
            if record["symbol"] == symbol and record["actual_return"] is None:
                record["actual_return"] = actual_return
                break

    def check_performance(self, model_id: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """检查模型性能

        Args:
            model_id: 模型ID，None表示检查所有模型

        Returns:
            模型性能字典 {model_id: {metric: value}}
        """
        if model_id:
            model_ids = [model_id]
        else:
            model_ids = list(self._predictions_cache.keys())

        performance_results = {}

        for mid in model_ids:
            if mid not in self._predictions_cache:
                continue

            # 获取有实际收益的预测
            records = [
                r for r in self._predictions_cache[mid]
                if r["actual_return"] is not None
            ]

            if not records:
                continue

            # 构建快照
            snapshot = ModelPerformanceSnapshot(
                model_id=mid,
                model_name=self._get_model_name(mid),
                timestamp=datetime.now(),
                actual_returns=np.array([r["actual_return"] for r in records]),
                predicted_returns=np.array([r["predicted_return"] for r in records]),
                directions=[r["signal"] for r in records],
                confidence_scores=np.array([r["confidence"] for r in records])
            )

            # 计算指标
            metrics = snapshot.calculate_metrics()

            if metrics:
                performance_results[mid] = metrics

                # 保存到历史
                if mid not in self._performance_history:
                    self._performance_history[mid] = []
                self._performance_history[mid].append(snapshot)

                # 检查阈值并触发告警
                self._check_thresholds(mid, metrics)

                # 发送更新事件
                self._emit_performance_event(mid, metrics)

        return performance_results

    def _check_thresholds(self, model_id: str, metrics: Dict[str, float]) -> None:
        """检查性能阈值

        Args:
            model_id: 模型ID
            metrics: 性能指标字典
        """
        if not self.alert_engine:
            return

        model_name = self._get_model_name(model_id)

        for threshold in self._thresholds:
            if not threshold.enabled:
                continue

            metric_value = metrics.get(threshold.metric.value)
            if metric_value is None:
                continue

            # 检查是否低于阈值
            if metric_value <= threshold.critical_threshold:
                self.alert_engine.send_alert(
                    title=f"模型性能严重告警: {model_name}",
                    message=f"模型 {model_name} 的 {threshold.metric.value} 指标为 {metric_value:.4f}，低于严重阈值 {threshold.critical_threshold:.4f}",
                    severity=AlertSeverity.CRITICAL,
                    priority=AlertPriority.HIGH,
                    source="ml_performance",
                    data={
                        "model_id": model_id,
                        "metric": threshold.metric.value,
                        "value": metric_value,
                        "threshold": threshold.critical_threshold
                    }
                )
            elif metric_value <= threshold.warning_threshold:
                self.alert_engine.send_alert(
                    title=f"模型性能警告: {model_name}",
                    message=f"模型 {model_name} 的 {threshold.metric.value} 指标为 {metric_value:.4f}，低于警告阈值 {threshold.warning_threshold:.4f}",
                    severity=AlertSeverity.WARNING,
                    priority=AlertPriority.NORMAL,
                    source="ml_performance",
                    data={
                        "model_id": model_id,
                        "metric": threshold.metric.value,
                        "value": metric_value,
                        "threshold": threshold.warning_threshold
                    }
                )

    def get_performance_history(
        self,
        model_id: str,
        limit: int = 100
    ) -> List[ModelPerformanceSnapshot]:
        """获取性能历史

        Args:
            model_id: 模型ID
            limit: 返回数量限制

        Returns:
            性能快照列表
        """
        if model_id not in self._performance_history:
            return []

        return self._performance_history[model_id][-limit:]

    def get_performance_trend(
        self,
        model_id: str,
        metric: PerformanceMetric,
        window: int = 10
    ) -> Optional[np.ndarray]:
        """获取性能趋势

        Args:
            model_id: 模型ID
            metric: 指标类型
            window: 趋势窗口大小

        Returns:
            趋势数组
        """
        history = self.get_performance_history(model_id, limit=window)

        if not history:
            return None

        values = []
        for snapshot in history:
            metrics = snapshot.calculate_metrics()
            value = metrics.get(metric.value)
            if value is not None:
                values.append(value)

        return np.array(values) if values else None

    def detect_performance_decay(
        self,
        model_id: str,
        metric: PerformanceMetric = PerformanceMetric.DIRECTION_ACCURACY,
        threshold: float = 0.1
    ) -> Tuple[bool, float]:
        """检测性能衰减

        比较最近N天的性能与历史平均性能，判断是否存在性能衰减。

        Args:
            model_id: 模型ID
            metric: 监控的指标
            threshold: 衰减阈值（相对下降比例）

        Returns:
            (is_decaying, decay_rate) 是否衰减，衰减率
        """
        history = self.get_performance_history(model_id, limit=50)

        if len(history) < 10:
            return False, 0.0

        # 计算历史平均
        all_values = []
        for snapshot in history:
            metrics = snapshot.calculate_metrics()
            value = metrics.get(metric.value)
            if value is not None:
                all_values.append(value)

        if not all_values:
            return False, 0.0

        # 最近5个值的平均 vs 历史平均
        recent_values = all_values[-5:]
        historical_avg = np.mean(all_values[:-5]) if len(all_values) > 5 else np.mean(all_values)
        recent_avg = np.mean(recent_values)

        if historical_avg == 0:
            return False, 0.0

        decay_rate = (historical_avg - recent_avg) / abs(historical_avg)
        is_decaying = decay_rate > threshold

        if is_decaying and self.alert_engine:
            model_name = self._get_model_name(model_id)
            self.alert_engine.send_alert(
                title=f"模型性能衰减检测: {model_name}",
                message=f"模型 {model_name} 的 {metric.value} 指标出现衰减，历史平均 {historical_avg:.4f}，最近平均 {recent_avg:.4f}，衰减率 {decay_rate:.2%}",
                severity=AlertSeverity.WARNING,
                priority=AlertPriority.HIGH,
                source="ml_performance",
                data={
                    "model_id": model_id,
                    "metric": metric.value,
                    "historical_avg": historical_avg,
                    "recent_avg": recent_avg,
                    "decay_rate": decay_rate
                }
            )

        return is_decaying, decay_rate

    def generate_report(self, model_id: str) -> Dict[str, Any]:
        """生成性能报告

        Args:
            model_id: 模型ID

        Returns:
            性能报告字典
        """
        model_name = self._get_model_name(model_id)
        current_metrics = self.check_performance(model_id).get(model_id, {})
        history = self.get_performance_history(model_id)

        # 计算统计信息
        if history:
            all_metrics = [s.calculate_metrics() for s in history]
            ic_values = [m.get(PerformanceMetric.IC.value) for m in all_metrics if PerformanceMetric.IC.value in m]
            accuracy_values = [m.get(PerformanceMetric.DIRECTION_ACCURACY.value) for m in all_metrics if PerformanceMetric.DIRECTION_ACCURACY.value in m]

            stats = {
                "ic_mean": float(np.mean(ic_values)) if ic_values else None,
                "ic_std": float(np.std(ic_values)) if ic_values else None,
                "accuracy_mean": float(np.mean(accuracy_values)) if accuracy_values else None,
                "accuracy_std": float(np.std(accuracy_values)) if accuracy_values else None,
                "total_predictions": len(self._predictions_cache.get(model_id, [])),
                "snapshots_count": len(history),
            }
        else:
            stats = {
                "total_predictions": len(self._predictions_cache.get(model_id, [])),
                "snapshots_count": 0,
            }

        return {
            "model_id": model_id,
            "model_name": model_name,
            "current_metrics": current_metrics,
            "statistics": stats,
            "thresholds": {
                t.metric.value: {
                    "warning": t.warning_threshold,
                    "critical": t.critical_threshold
                }
                for t in self._thresholds if t.enabled
            },
            "generated_at": datetime.now().isoformat()
        }

    def set_threshold(
        self,
        metric: PerformanceMetric,
        warning_threshold: float,
        critical_threshold: float
    ) -> None:
        """设置性能阈值

        Args:
            metric: 指标类型
            warning_threshold: 警告阈值
            critical_threshold: 严重阈值
        """
        # 查找并更新或添加
        for t in self._thresholds:
            if t.metric == metric:
                t.warning_threshold = warning_threshold
                t.critical_threshold = critical_threshold
                return

        # 添加新阈值
        self._thresholds.append(PerformanceThreshold(
            metric, warning_threshold, critical_threshold
        ))

    def get_all_model_ids(self) -> List[str]:
        """获取所有监控的模型ID

        Returns:
            模型ID列表
        """
        return list(self._predictions_cache.keys())

    def _get_model_name(self, model_id: str) -> str:
        """获取模型名称

        Args:
            model_id: 模型ID

        Returns:
            模型名称
        """
        metadata = self.model_manager.get_model_metadata(model_id)
        if metadata:
            return metadata.model_name
        return model_id

    def _emit_performance_event(self, model_id: str, metrics: Dict[str, float]) -> None:
        """发送性能更新事件

        Args:
            model_id: 模型ID
            metrics: 性能指标
        """
        if not self.event_engine:
            return

        event = Event(
            self.EVENT_MODEL_PERFORMANCE_UPDATE,
            {
                "model_id": model_id,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
        )
        self.event_engine.put(event)

    def clear_cache(self, model_id: Optional[str] = None) -> None:
        """清空缓存

        Args:
            model_id: 模型ID，None表示清空所有
        """
        if model_id:
            self._predictions_cache.pop(model_id, None)
            self._performance_history.pop(model_id, None)
        else:
            self._predictions_cache.clear()
            self._performance_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息

        Returns:
            统计信息字典
        """
        total_predictions = sum(
            len(cache) for cache in self._predictions_cache.values()
        )

        total_snapshots = sum(
            len(history) for history in self._performance_history.values()
        )

        return {
            "monitored_models": len(self._predictions_cache),
            "total_predictions": total_predictions,
            "total_snapshots": total_snapshots,
            "window_size": self.window_size,
            "check_interval": self.check_interval,
            "running": self._running
        }


__all__ = [
    "ModelPerformanceMonitor",
    "PerformanceMetric",
    "PerformanceThreshold",
    "ModelPerformanceSnapshot",
]
