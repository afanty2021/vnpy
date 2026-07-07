"""模型A/B测试器

提供模型对比测试功能，支持多模型性能评估和统计显著性检验。
"""

import uuid
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from .manager import ModelManager
from .china_model import ChinaAlphaModel
from .ab_test import ABTestConfig, ABTestResult


class ModelABTester:
    """模型A/B测试器

    负责执行多模型对比测试，计算评估指标并进行统计显著性检验。
    """

    def __init__(self, model_manager: ModelManager):
        """初始化A/B测试器

        Args:
            model_manager: 模型管理器实例
        """
        self.model_manager = model_manager
        self.test_history: List[ABTestResult] = []

    def create_test(self, config: ABTestConfig) -> Optional[str]:
        """创建A/B测试

        Args:
            config: 测试配置

        Returns:
            测试ID，如果创建失败返回None
        """
        # 验证模型存在
        for model_id in config.model_ids:
            if model_id not in self.model_manager._models:
                print(f"模型不存在: {model_id}")
                return None

        # 生成测试ID
        test_id = f"ab_test_{uuid.uuid4().hex[:8]}"

        # 创建空结果对象
        result = ABTestResult(
            test_id=test_id,
            test_name=config.test_name,
            timestamp=datetime.now(),
            model_results={},
            test_config=config
        )

        self.test_history.append(result)
        return test_id

    def run_test(
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
            metrics: 评估指标列表（默认使用准确率、IC等）

        Returns:
            测试结果
        """
        # 查找测试配置
        test_result = None
        for result in self.test_history:
            if result.test_id == test_id:
                test_result = result
                break

        if not test_result or not test_result.test_config:
            print(f"测试不存在或缺少配置: {test_id}")
            return None

        config = test_result.test_config
        metrics = metrics or config.metrics

        # 验证数据
        if len(X) < config.min_samples:
            print(f"测试数据不足：{len(X)} < {config.min_samples}")
            return None

        # 评估所有模型
        model_results = {}
        predictions_dict = {}

        for model_id in config.model_ids:
            model = self.model_manager.load_model(model_id)
            if model is None:
                print(f"加载模型失败: {model_id}")
                continue

            # 评估模型
            eval_results = self.evaluate_model(model, X, y, metrics)
            model_results[model_id] = eval_results

            # 保存预测结果用于统计检验
            predictions_dict[model_id] = model.predict(X)

        if len(model_results) < 2:
            print("至少需要2个模型进行对比")
            return None

        # 更新结果
        test_result.model_results = model_results

        # 进行统计显著性检验
        if len(model_results) == 2 and SCIPY_AVAILABLE:
            model_ids = list(model_results.keys())
            pred_1 = predictions_dict[model_ids[0]]
            pred_2 = predictions_dict[model_ids[1]]

            # 使用t检验比较预测误差
            errors_1 = np.abs(pred_1 - y)
            errors_2 = np.abs(pred_2 - y)

            t_stat, p_value = stats.ttest_rel(errors_1, errors_2)
            test_result.significance = p_value

        # 确定获胜模型（默认使用第一个指标）
        if metrics:
            primary_metric = metrics[0]
            winner = self._determine_winner(model_results, primary_metric)
            test_result.winner = winner

        # 生成对比信息
        test_result.comparison = self._generate_comparison(model_results)

        return test_result

    def evaluate_model(
        self,
        model: ChinaAlphaModel,
        X: np.ndarray,
        y: np.ndarray,
        metrics: List[str]
    ) -> Dict[str, float]:
        """评估单个模型

        Args:
            model: 模型实例
            X: 特征矩阵
            y: 目标变量
            metrics: 评估指标列表

        Returns:
            指标结果字典
        """
        results = {}

        # 进行预测
        predictions = model.predict(X)

        # 计算各种指标
        for metric in metrics:
            metric_lower = metric.lower()

            if metric_lower in ["accuracy", "acc"]:
                results[metric] = self._calculate_accuracy(y, predictions)
            elif metric_lower == "ic":
                results[metric] = self._calculate_ic(y, predictions)
            elif metric_lower == "rank_ic":
                results[metric] = self._calculate_rank_ic(y, predictions)
            elif metric_lower in ["mse", "mean_squared_error"]:
                results[metric] = self._calculate_mse(y, predictions)
            elif metric_lower in ["mae", "mean_absolute_error"]:
                results[metric] = self._calculate_mae(y, predictions)
            elif metric_lower in ["rmse", "root_mean_squared_error"]:
                results[metric] = np.sqrt(self._calculate_mse(y, predictions))
            elif metric_lower == "sharpe_ratio":
                results[metric] = self._calculate_sharpe(predictions)

        return results

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
        if metrics is None:
            metrics = ["accuracy", "ic", "mse"]

        results = {}
        for model_id in model_ids:
            model = self.model_manager.load_model(model_id)
            if model:
                results[model_id] = self.evaluate_model(model, X, y, metrics)

        return results

    def statistical_test(
        self,
        results_1: np.ndarray,
        results_2: np.ndarray
    ) -> Tuple[float, float]:
        """统计显著性检验（t检验）

        Args:
            results_1: 模型1的结果数组
            results_2: 模型2的结果数组

        Returns:
            (t统计量, p值) 元组
        """
        if not SCIPY_AVAILABLE:
            return 0.0, 1.0

        if len(results_1) != len(results_2):
            print("警告：两个结果数组长度不一致")

        min_len = min(len(results_1), len(results_2))
        results_1 = results_1[:min_len]
        results_2 = results_2[:min_len]

        # 配对t检验
        t_stat, p_value = stats.ttest_rel(results_1, results_2)
        return float(t_stat), float(p_value)

    def get_test_history(self) -> List[ABTestResult]:
        """获取测试历史

        Returns:
            所有测试结果列表
        """
        return self.test_history.copy()

    def get_test_result(self, test_id: str) -> Optional[ABTestResult]:
        """获取测试结果

        Args:
            test_id: 测试ID

        Returns:
            测试结果
        """
        for result in self.test_history:
            if result.test_id == test_id:
                return result
        return None

    def clear_history(self) -> None:
        """清空测试历史"""
        self.test_history.clear()

    def _calculate_accuracy(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """计算方向准确率"""
        y_direction = (y_true > 0).astype(int)
        pred_direction = (y_pred > 0).astype(int)
        return float((y_direction == pred_direction).mean())

    def _calculate_ic(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """计算IC（相关系数）"""
        if len(y_true) < 2:
            return 0.0

        if SCIPY_AVAILABLE:
            ic, _ = stats.pearsonr(y_pred, y_true)
            return float(ic)
        else:
            # 简单的皮尔逊相关系数
            return float(np.corrcoef(y_pred, y_true)[0, 1])

    def _calculate_rank_ic(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """计算Rank IC（秩相关系数）"""
        if len(y_true) < 2:
            return 0.0

        if SCIPY_AVAILABLE:
            ric, _ = stats.spearmanr(y_pred, y_true)
            return float(ric)
        else:
            # 纯 numpy 秩计算（scipy 不可用时的 fallback，不得再 import scipy）
            def _rank(a):
                return np.argsort(np.argsort(a)).astype(float)
            return float(np.corrcoef(_rank(y_pred), _rank(y_true))[0, 1])

    def _calculate_mse(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """计算均方误差"""
        return float(np.mean((y_true - y_pred) ** 2))

    def _calculate_mae(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """计算平均绝对误差"""
        return float(np.mean(np.abs(y_true - y_pred)))

    def _calculate_sharpe(self, predictions: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """计算夏普比率"""
        if len(predictions) < 2:
            return 0.0

        returns = predictions
        excess_returns = returns - risk_free_rate

        if np.std(excess_returns) == 0:
            return 0.0

        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return float(sharpe)

    def _determine_winner(
        self,
        model_results: Dict[str, Dict[str, float]],
        metric: str
    ) -> Optional[str]:
        """确定获胜模型

        Args:
            model_results: 模型结果字典
            metric: 评估指标

        Returns:
            获胜模型ID
        """
        # 判断指标是否越高越好
        higher_better = metric.lower() not in ["mse", "mae", "rmse"]

        best_model = None
        best_value = None

        for model_id, results in model_results.items():
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

    def _generate_comparison(
        self,
        model_results: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """生成模型对比信息

        Args:
            model_results: 模型结果字典

        Returns:
            对比信息字典
        """
        comparison = {
            "model_count": len(model_results),
            "metrics": {},
            "summary": []
        }

        # 获取所有指标
        all_metrics = set()
        for results in model_results.values():
            all_metrics.update(results.keys())

        # 对每个指标进行对比
        for metric in all_metrics:
            values = []
            for model_id, results in model_results.items():
                if metric in results:
                    values.append({
                        "model_id": model_id,
                        "value": results[metric]
                    })

            # 排序
            higher_better = metric.lower() not in ["mse", "mae", "rmse"]
            values.sort(key=lambda x: x["value"], reverse=higher_better)

            comparison["metrics"][metric] = {
                "best": values[0]["model_id"] if values else None,
                "best_value": values[0]["value"] if values else None,
                "worst": values[-1]["model_id"] if values else None,
                "worst_value": values[-1]["value"] if values else None,
                "diff": (values[0]["value"] - values[-1]["value"]) if len(values) > 1 else 0
            }

        # 生成摘要
        for model_id, results in model_results.items():
            summary = {
                "model_id": model_id,
                "metrics": results
            }
            comparison["summary"].append(summary)

        return comparison


__all__ = ["ModelABTester"]
