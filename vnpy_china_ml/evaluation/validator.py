"""
模型验证器模块

本模块提供模型性能验证功能，包括：
- 交叉验证: K折交叉验证和时间序列交叉验证
- 滚动向前验证: 模拟真实交易场景的验证方法
- 回测验证: 基于历史数据的策略回测
- 稳定性分析: 模型性能的稳定性评估
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, datetime, timedelta
from sklearn.model_selection import cross_val_score, TimeSeriesSplit, KFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)

from .ic_ir import ICAnalyzer
from .metrics import ChinaMetrics
from ..utils.types import BacktestResult


class ModelValidator:
    """模型验证器

    提供模型性能评估、交叉验证、稳定性分析等功能：
    - K折交叉验证
    - 时间序列交叉验证
    - 滚动向前验证
    - 回测验证
    - 稳定性分析

    Attributes:
        ic_analyzer: IC分析器实例
        metrics: A股评估指标计算器实例
        validation_results: 验证结果历史记录
    """

    def __init__(self) -> None:
        """初始化验证器"""
        self.ic_analyzer = ICAnalyzer()
        self.metrics = ChinaMetrics()
        self.validation_results: List[Dict] = []

    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5,
        model: Optional[Any] = None,
        scoring: str = "accuracy"
    ) -> Dict:
        """K折交叉验证

        将数据分成K个折叠，轮流使用K-1个折叠训练，1个折叠验证。

        Args:
            X: 特征数据
            y: 标签数据
            n_splits: 折数，默认5
            model: 机器学习模型（如果为None，返回验证器配置信息）
            scoring: 评分指标

        Returns:
            验证结果字典
        """
        if n_splits < 2:
            raise ValueError("n_splits必须大于等于2")

        if X.shape[0] != y.shape[0]:
            raise ValueError("特征和标签样本数不匹配")

        if X.shape[0] < n_splits:
            n_splits = X.shape[0]

        if model is None:
            # 返回验证器配置信息
            return {
                "mean_score": 0.0,
                "std_score": 0.0,
                "scores": [],
                "n_splits": n_splits,
                "note": "未提供模型，请提供模型进行验证"
            }

        # 使用时间序列交叉验证（更适合金融数据）
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = []

        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                if scoring == "accuracy":
                    score = accuracy_score(y_test, y_pred)
                elif scoring == "f1":
                    score = f1_score(y_test, y_pred, average='weighted', zero_division=0)
                elif scoring == "neg_mean_squared_error":
                    score = -mean_squared_error(y_test, y_pred)
                else:
                    score = accuracy_score(y_test, y_pred)

                scores.append(score)
            except Exception:
                continue

        if not scores:
            return {
                "mean_score": 0.0,
                "std_score": 0.0,
                "scores": [],
                "n_splits": n_splits
            }

        scores_array = np.array(scores)

        result = {
            "mean_score": float(np.mean(scores_array)),
            "std_score": float(np.std(scores_array)),
            "scores": scores,
            "n_splits": n_splits
        }

        # 保存到历史记录
        self.validation_results.append(result)

        return result

    def walk_forward_validation(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_size: int = 100,
        step_size: Optional[int] = None,
        model: Optional[Any] = None
    ) -> Dict:
        """滚动向前验证

        模拟真实交易场景，每次使用固定大小的训练窗口，
        然后向前滚动一步进行验证。

        Args:
            X: 特征数据
            y: 标签数据
            train_size: 训练集大小
            step_size: 每次向前滚动的步数，默认train_size的一半
            model: 机器学习模型

        Returns:
            验证结果字典
        """
        if train_size >= len(X):
            raise ValueError("训练集大小必须小于样本数量")

        if step_size is None:
            step_size = max(1, train_size // 2)

        if model is None:
            return {
                "mean_score": 0.0,
                "n_iterations": 0,
                "note": "未提供模型，请提供模型进行验证"
            }

        scores = []
        n_iterations = 0

        # 滚动向前验证
        start_idx = 0
        while start_idx + train_size < len(X):
            end_idx = start_idx + train_size
            test_end_idx = min(end_idx + step_size, len(X))

            X_train = X[start_idx:end_idx]
            y_train = y[start_idx:end_idx]
            X_test = X[end_idx:test_end_idx]
            y_test = y[end_idx:test_end_idx]

            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                # 计算准确率
                score = accuracy_score(y_test, y_pred)
                scores.append(score)
                n_iterations += 1
            except Exception:
                pass

            start_idx = end_idx

        if not scores:
            return {
                "mean_score": 0.0,
                "std_score": 0.0,
                "n_iterations": 0
            }

        scores_array = np.array(scores)

        result = {
            "mean_score": float(np.mean(scores_array)),
            "std_score": float(np.std(scores_array)),
            "scores": scores,
            "n_iterations": n_iterations
        }

        # 保存到历史记录
        self.validation_results.append(result)

        return result

    def backtest(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        initial_capital: float = 1000000.0,
        transaction_cost: float = 0.0003
    ) -> BacktestResult:
        """回测验证

        基于预测结果和实际结果进行回测，计算各项绩效指标。

        Args:
            predictions: 预测收益率序列
            actuals: 实际收益率序列
            initial_capital: 初始资金
            transaction_cost: 交易成本（手续费率）

        Returns:
            BacktestResult对象
        """
        if len(predictions) != len(actuals):
            raise ValueError("预测值和实际值长度不匹配")

        if len(predictions) == 0:
            # 返回空结果
            return BacktestResult(
                start_date=date.today(),
                end_date=date.today(),
                total_return=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                total_trades=0
            )

        # 生成交易信号：预测上涨买入，预测下跌卖出
        signals = np.sign(predictions)

        # 计算实际收益（考虑交易成本）
        returns = actuals.copy()

        # 扣除交易成本（当信号改变时）
        position_changes = np.abs(np.diff(signals))
        costs = position_changes * transaction_cost
        returns = returns - np.insert(costs, 0, 0)

        # 计算累计收益
        cumulative_returns = np.cumprod(1 + returns)

        # 资金曲线
        equity = initial_capital * cumulative_returns

        # 计算绩效指标
        total_return = (equity[-1] - initial_capital) / initial_capital

        # 年化收益率（假设252个交易日）
        n_days = len(returns)
        n_years = n_days / 252.0
        if n_years > 0:
            annual_return = (1 + total_return) ** (1 / n_years) - 1
        else:
            annual_return = 0.0

        # 夏普比率
        daily_returns = returns
        if np.std(daily_returns) > 0:
            sharpe_ratio = (np.mean(daily_returns) - 0.03 / 252) / np.std(daily_returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # 最大回撤
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(np.min(drawdown))

        # 胜率
        winning_trades = np.sum(returns > 0)
        total_trades = n_days
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # 估计交易次数（假设每天调仓一次）
        position_changes_total = np.sum(np.abs(np.diff(signals))) // 2

        result = BacktestResult(
            start_date=date.today() - timedelta(days=n_days),
            end_date=date.today(),
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=int(position_changes_total)
        )

        return result

    def backtest_with_signals(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        dates: Optional[List[date]] = None,
        initial_capital: float = 1000000.0,
        transaction_cost: float = 0.0003
    ) -> Dict:
        """带日期的回测验证

        基于预测结果和实际结果进行回测，支持指定日期。

        Args:
            predictions: 预测收益率序列
            actuals: 实际收益率序列
            dates: 日期序列（可选）
            initial_capital: 初始资金
            transaction_cost: 交易成本（手续费率）

        Returns:
            包含回测结果的字典
        """
        if len(predictions) != len(actuals):
            raise ValueError("预测值和实际值长度不匹配")

        if dates is None:
            dates = [date.today() - timedelta(days=len(predictions) - i) for i in range(len(predictions))]

        if len(dates) != len(predictions):
            raise ValueError("日期数量与数据长度不匹配")

        # 生成交易信号
        signals = np.sign(predictions)

        # 计算收益
        returns = actuals.copy()

        # 扣除交易成本
        position_changes = np.abs(np.diff(signals))
        costs = position_changes * transaction_cost
        returns = returns - np.insert(costs, 0, 0)

        # 计算绩效指标
        total_return = np.sum(returns)
        annual_return = np.mean(returns) * 252

        # 最大回撤
        cumulative_returns = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = abs(np.min(drawdown))

        # 夏普比率
        if np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) - 0.03 / 252) / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # 胜率
        win_rate = np.mean(returns > 0)

        # Calmar比率
        if max_drawdown > 0:
            calmar_ratio = annual_return / max_drawdown
        else:
            calmar_ratio = 0.0

        # 盈亏比
        profits = returns[returns > 0]
        losses = returns[returns < 0]
        if len(losses) > 0 and np.mean(np.abs(losses)) > 0:
            profit_loss_ratio = np.mean(profits) / np.mean(np.abs(losses)) if len(profits) > 0 else 0.0
        else:
            profit_loss_ratio = 0.0

        # 交易次数
        total_trades = int(np.sum(np.abs(np.diff(signals))) // 2)

        # IC分析
        ic = self.ic_analyzer.calculate_ic(predictions, actuals)
        rank_ic = self.ic_analyzer.calculate_rank_ic(predictions, actuals)

        return {
            "start_date": dates[0].isoformat() if dates else date.today().isoformat(),
            "end_date": dates[-1].isoformat() if dates else date.today().isoformat(),
            "total_return": float(total_return),
            "annual_return": float(annual_return),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "calmar_ratio": float(calmar_ratio),
            "win_rate": float(win_rate),
            "profit_loss_ratio": float(profit_loss_ratio),
            "total_trades": total_trades,
            "ic": ic,
            "rank_ic": rank_ic,
            "equity_curve": cumulative_returns.tolist()
        }

    def validate_stability(
        self,
        scores: List[float],
        threshold: float = 0.15
    ) -> Dict:
        """验证稳定性

        通过变异系数（CV = 标准差/均值）评估模型稳定性。

        Args:
            scores: 验证得分列表
            threshold: 稳定性阈值，CV小于此值认为稳定

        Returns:
            稳定性分析结果字典
        """
        if not scores:
            return {
                "is_stable": False,
                "cv": 0.0,
                "mean": 0.0,
                "std": 0.0,
                "note": "没有足够的数据进行稳定性分析"
            }

        scores_array = np.array(scores)
        mean_score = np.mean(scores_array)
        std_score = np.std(scores_array, ddof=1)

        # 变异系数
        if mean_score != 0:
            cv = std_score / mean_score
        else:
            cv = float('inf')

        is_stable = cv < threshold

        return {
            "is_stable": bool(is_stable),
            "cv": float(cv),
            "mean": float(mean_score),
            "std": float(std_score),
            "min": float(np.min(scores_array)),
            "max": float(np.max(scores_array)),
            "threshold": threshold
        }

    def validate_with_ic(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray
    ) -> Dict:
        """使用IC指标验证模型

        Args:
            predictions: 预测收益率序列
            actuals: 实际收益率序列

        Returns:
            IC验证结果字典
        """
        # 计算IC
        ic = self.ic_analyzer.calculate_ic(predictions, actuals)
        rank_ic = self.ic_analyzer.calculate_rank_ic(predictions, actuals)

        # 计算IC时间序列
        ic_series = self.ic_analyzer.calculate_ic_series(predictions, actuals)

        # 计算IR
        ir = self.ic_analyzer.calculate_ir(ic_series)

        return {
            "ic": ic,
            "rank_ic": rank_ic,
            "ir": ir,
            "ic_series": ic_series.tolist(),
            "ic_mean": float(np.mean(ic_series)) if len(ic_series) > 0 else 0.0,
            "ic_std": float(np.std(ic_series)) if len(ic_series) > 0 else 0.0,
            "ic_positive_ratio": float(np.mean(ic_series > 0)) if len(ic_series) > 0 else 0.0
        }

    def get_validation_summary(self) -> Dict:
        """获取验证总结

        Returns:
            验证结果总结字典
        """
        if not self.validation_results:
            return {
                "total_validations": 0,
                "note": "没有验证记录"
            }

        all_scores = []
        for result in self.validation_results:
            if "scores" in result:
                all_scores.extend(result["scores"])

        if not all_scores:
            return {
                "total_validations": len(self.validation_results),
                "note": "没有有效的得分记录"
            }

        scores_array = np.array(all_scores)

        return {
            "total_validations": len(self.validation_results),
            "total_scores": len(all_scores),
            "mean_score": float(np.mean(scores_array)),
            "std_score": float(np.std(scores_array)),
            "min_score": float(np.min(scores_array)),
            "max_score": float(np.max(scores_array))
        }

    def clear_results(self) -> None:
        """清除验证结果"""
        self.validation_results.clear()
