"""A/B测试数据类

定义了模型A/B测试所需的配置和结果数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional


@dataclass
class ABTestConfig:
    """A/B测试配置

    Attributes:
        test_name: 测试名称
        model_ids: 参与测试的模型ID列表
        test_data_start: 测试数据开始日期
        test_data_end: 测试数据结束日期
        metrics: 评估指标列表（如 ["accuracy", "ic", "sharpe_ratio"]）
        min_samples: 最小样本数量要求
        description: 测试描述
    """
    test_name: str
    model_ids: List[str]
    test_data_start: date
    test_data_end: date
    metrics: List[str] = field(default_factory=lambda: ["accuracy", "ic"])
    min_samples: int = 100
    description: str = ""

    def __post_init__(self) -> None:
        """验证配置有效性"""
        if not self.test_name:
            raise ValueError("test_name不能为空")
        if len(self.model_ids) < 2:
            raise ValueError("至少需要2个模型进行A/B测试")
        if self.test_data_start >= self.test_data_end:
            raise ValueError("test_data_start必须早于test_data_end")
        if self.min_samples <= 0:
            raise ValueError("min_samples必须大于0")

    @property
    def test_period_days(self) -> int:
        """测试周期天数"""
        return (self.test_data_end - self.test_data_start).days

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "test_name": self.test_name,
            "model_ids": self.model_ids,
            "test_data_start": self.test_data_start.isoformat(),
            "test_data_end": self.test_data_end.isoformat(),
            "metrics": self.metrics,
            "min_samples": self.min_samples,
            "description": self.description
        }


@dataclass
class ABTestResult:
    """A/B测试结果

    Attributes:
        test_id: 测试唯一ID
        test_name: 测试名称
        timestamp: 测试时间戳
        model_results: 模型ID -> 指标结果字典的映射
        winner: 获胜模型ID（根据主要指标判断）
        significance: 统计显著性p值
        test_config: 测试配置
        comparison: 模型间对比结果
        created_at: 结果创建时间
    """
    test_id: str
    test_name: str
    timestamp: datetime
    model_results: Dict[str, Dict[str, float]]
    winner: Optional[str] = None
    significance: Optional[float] = None
    test_config: Optional[ABTestConfig] = None
    comparison: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """初始化创建时间"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_best_model_by_metric(self, metric: str, higher_better: bool = True) -> Optional[str]:
        """根据指定指标获取最佳模型

        Args:
            metric: 指标名称
            higher_better: 是否越高越好

        Returns:
            最佳模型ID
        """
        best_model = None
        best_value = None

        for model_id, results in self.model_results.items():
            if metric in results:
                value = results[metric]
                if best_value is None:
                    best_value = value
                    best_model = model_id
                else:
                    if higher_better:
                        if value > best_value:
                            best_value = value
                            best_model = model_id
                    else:
                        if value < best_value:
                            best_value = value
                            best_model = model_id

        return best_model

    def get_metric_difference(self, model_id_1: str, model_id_2: str, metric: str) -> Optional[float]:
        """获取两个模型在指定指标上的差异

        Args:
            model_id_1: 模型1 ID
            model_id_2: 模型2 ID
            metric: 指标名称

        Returns:
            指标差异（model_id_1 - model_id_2）
        """
        if model_id_1 not in self.model_results or model_id_2 not in self.model_results:
            return None

        if metric not in self.model_results[model_id_1] or metric not in self.model_results[model_id_2]:
            return None

        return self.model_results[model_id_1][metric] - self.model_results[model_id_2][metric]

    def is_significant(self, alpha: float = 0.05) -> bool:
        """判断结果是否统计显著

        Args:
            alpha: 显著性水平

        Returns:
            是否显著
        """
        if self.significance is None:
            return False
        return self.significance < alpha

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "timestamp": self.timestamp.isoformat(),
            "model_results": self.model_results,
            "winner": self.winner,
            "significance": self.significance,
            "comparison": self.comparison,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "test_config": self.test_config.to_dict() if self.test_config else None
        }

    def get_summary(self) -> str:
        """获取测试结果摘要"""
        summary = f"A/B测试: {self.test_name}\n"
        summary += f"测试时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary += f"参与模型: {', '.join(self.model_results.keys())}\n\n"

        if self.winner:
            summary += f"推荐模型: {self.winner}\n"

        if self.significance is not None:
            sig_status = "显著" if self.is_significant() else "不显著"
            summary += f"统计显著性: {sig_status} (p={self.significance:.4f})\n"

        summary += "\n## 模型指标对比:\n"

        # 获取所有指标
        all_metrics = set()
        for results in self.model_results.values():
            all_metrics.update(results.keys())

        for metric in sorted(all_metrics):
            summary += f"\n{metric}:\n"
            for model_id, results in self.model_results.items():
                if metric in results:
                    summary += f"  {model_id}: {results[metric]:.4f}\n"

        return summary


@dataclass
class ModelVersionInfo:
    """模型版本信息

    Attributes:
        version: 语义化版本号（如 "1.0.0"）
        parent_model_id: 父模型ID（用于版本继承）
        version_tag: 版本标签（production/staging/development）
        changelog: 变更日志
        created_at: 版本创建时间
        is_production: 是否为生产版本
    """
    version: str = "1.0.0"
    parent_model_id: Optional[str] = None
    version_tag: str = "development"  # production, staging, development
    changelog: str = ""
    created_at: Optional[datetime] = None
    is_production: bool = False

    def __post_init__(self) -> None:
        """初始化创建时间"""
        if self.created_at is None:
            self.created_at = datetime.now()
        # 根据tag自动设置is_production
        if self.version_tag == "production":
            self.is_production = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "version": self.version,
            "parent_model_id": self.parent_model_id,
            "version_tag": self.version_tag,
            "changelog": self.changelog,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_production": self.is_production
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ModelVersionInfo":
        """从字典创建实例"""
        created_at = data.get("created_at")
        if created_at:
            created_at = datetime.fromisoformat(created_at)

        return ModelVersionInfo(
            version=data.get("version", "1.0.0"),
            parent_model_id=data.get("parent_model_id"),
            version_tag=data.get("version_tag", "development"),
            changelog=data.get("changelog", ""),
            created_at=created_at,
            is_production=data.get("is_production", False)
        )


__all__ = ["ABTestConfig", "ABTestResult", "ModelVersionInfo"]
