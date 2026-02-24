"""
优化结果数据类

定义了优化过程中使用的各种数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class OptimizationStatus(Enum):
    """优化状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OptimizationMetrics:
    """优化指标"""
    return_value: float           # 总收益率
    sharpe_ratio: float           # 夏普比率
    max_drawdown: float           # 最大回撤
    calmar_ratio: float = 0.0     # 卡玛比率
    sortino_ratio: float = 0.0    # 索提诺比率
    win_rate: float = 0.0         # 胜率
    profit_loss_ratio: float = 0.0  # 盈亏比
    total_trades: int = 0         # 总交易次数
    avg_trade_return: float = 0.0  # 平均每笔收益

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "return_value": self.return_value,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "calmar_ratio": self.calmar_ratio,
            "sortino_ratio": self.sortino_ratio,
            "win_rate": self.win_rate,
            "profit_loss_ratio": self.profit_loss_ratio,
            "total_trades": self.total_trades,
            "avg_trade_return": self.avg_trade_return,
        }


@dataclass
class OptimizationResult:
    """单次优化结果"""
    # 参数
    params: Dict[str, Any]

    # 指标
    metrics: OptimizationMetrics

    # 元数据
    status: OptimizationStatus = OptimizationStatus.COMPLETED
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    # 样本外测试结果
    out_sample_metrics: Optional[OptimizationMetrics] = None

    @property
    def score(self) -> float:
        """综合评分（默认使用夏普比率）"""
        return self.metrics.sharpe_ratio

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "params": self.params,
            "metrics": self.metrics.to_dict(),
            "score": self.score,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


@dataclass
class OptimizationSummary:
    """优化汇总"""
    # 总体信息
    total_evaluations: int           # 总评估次数
    best_score: float                # 最优分数
    worst_score: float               # 最差分数
    avg_score: float                 # 平均分数

    # 最优参数
    best_params: Dict[str, Any]
    best_metrics: OptimizationMetrics

    # 所有结果
    all_results: List[OptimizationResult] = field(default_factory=list)

    # 收敛信息
    converged: bool = False
    convergence_iteration: int = 0

    def get_top_n(self, n: int = 10) -> List[OptimizationResult]:
        """获取前N个结果"""
        return sorted(
            self.all_results,
            key=lambda x: x.score,
            reverse=True
        )[:n]

    def get_parameter_ranking(self, param_name: str) -> Dict[Any, float]:
        """获取参数排名"""
        param_scores: Dict[Any, List[float]] = {}

        for result in self.all_results:
            param_value = result.params.get(param_name)
            if param_value not in param_scores:
                param_scores[param_value] = []
            param_scores[param_value].append(result.score)

        # 计算平均分
        return {
            k: sum(v) / len(v) for k, v in param_scores.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_evaluations": self.total_evaluations,
            "best_score": self.best_score,
            "worst_score": self.worst_score,
            "avg_score": self.avg_score,
            "best_params": self.best_params,
            "best_metrics": self.best_metrics.to_dict(),
            "converged": self.converged,
            "convergence_iteration": self.convergence_iteration,
        }
