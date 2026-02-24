"""
评估工具模块单元测试

测试IC/IR分析器、A股评估指标和模型验证器的功能。
"""

import unittest
import numpy as np
from datetime import date, datetime, timedelta

from vnpy_china_ml.evaluation.ic_ir import ICAnalyzer
from vnpy_china_ml.evaluation.metrics import ChinaMetrics
from vnpy_china_ml.evaluation.validator import ModelValidator
from vnpy_china_ml.utils.types import BacktestResult


class TestICAnalyzer(unittest.TestCase):
    """测试IC/IR分析器"""

    def setUp(self):
        """测试前准备"""
        np.random.seed(42)
        self.analyzer = ICAnalyzer()

    def test_calculate_ic_pearson(self):
        """测试皮尔逊相关系数IC计算"""
        # 完全正相关
        predictions = np.array([1, 2, 3, 4, 5])
        actuals = np.array([1, 2, 3, 4, 5])
        ic = self.analyzer.calculate_ic(predictions, actuals, method="pearson")
        self.assertAlmostEqual(ic, 1.0, places=5)

        # 完全负相关
        actuals_neg = np.array([5, 4, 3, 2, 1])
        ic_neg = self.analyzer.calculate_ic(predictions, actuals_neg, method="pearson")
        self.assertAlmostEqual(ic_neg, -1.0, places=5)

    def test_calculate_ic_spearman(self):
        """测试斯皮尔曼相关系数IC计算"""
        predictions = np.array([1, 2, 3, 4, 5])
        actuals = np.array([2, 4, 1, 5, 3])
        ic = self.analyzer.calculate_ic(predictions, actuals, method="spearman")
        self.assertAlmostEqual(ic, 0.3, places=1)

    def test_calculate_ic_length_mismatch(self):
        """测试长度不匹配时的错误处理"""
        predictions = np.array([1, 2, 3])
        actuals = np.array([1, 2])

        with self.assertRaises(ValueError) as context:
            self.analyzer.calculate_ic(predictions, actuals)
        self.assertIn("长度不匹配", str(context.exception))

    def test_calculate_ic_invalid_method(self):
        """测试无效方法时的错误处理"""
        predictions = np.array([1, 2, 3, 4, 5])
        actuals = np.array([1, 2, 3, 4, 5])

        with self.assertRaises(ValueError) as context:
            self.analyzer.calculate_ic(predictions, actuals, method="invalid")
        self.assertIn("未知的IC计算方法", str(context.exception))

    def test_calculate_rank_ic(self):
        """测试Rank IC计算"""
        predictions = np.array([3, 1, 4, 2, 5])
        actuals = np.array([2, 5, 1, 4, 3])
        rank_ic = self.analyzer.calculate_rank_ic(predictions, actuals)

        # Rank IC应该在-1到1之间
        self.assertGreaterEqual(rank_ic, -1.0)
        self.assertLessEqual(rank_ic, 1.0)

    def test_calculate_rank_ic_length_mismatch(self):
        """测试Rank IC长度不匹配"""
        predictions = np.array([1, 2, 3])
        actuals = np.array([1, 2])

        with self.assertRaises(ValueError):
            self.analyzer.calculate_rank_ic(predictions, actuals)

    def test_calculate_ic_series(self):
        """测试IC时间序列计算"""
        n = 100
        predictions = np.random.randn(n)
        actuals = predictions + np.random.randn(n) * 0.5

        ic_series = self.analyzer.calculate_ic_series(predictions, actuals, n_periods=5)

        self.assertEqual(len(ic_series), 5)

    def test_calculate_ir(self):
        """测试IR计算"""
        ic_series = np.array([0.05, 0.03, 0.06, 0.04, 0.05])
        ir = self.analyzer.calculate_ir(ic_series)

        # IR应该是IC均值除以IC标准差
        expected_ir = np.mean(ic_series) / np.std(ic_series, ddof=1)
        self.assertAlmostEqual(ir, expected_ir, places=5)

    def test_calculate_ir_empty(self):
        """测试空IC序列"""
        ic_series = np.array([])
        ir = self.analyzer.calculate_ir(ic_series)
        self.assertEqual(ir, 0.0)

    def test_calculate_ir_annualized(self):
        """测试年化IR"""
        ic_series = np.array([0.05, 0.03, 0.06, 0.04, 0.05])
        ir_annualized = self.analyzer.calculate_ir(ic_series, annualized=True, periods_per_year=12)

        # 年化IR应该等于IR乘以sqrt(12)
        ir = np.mean(ic_series) / np.std(ic_series, ddof=1)
        expected = ir * np.sqrt(12)
        self.assertAlmostEqual(ir_annualized, expected, places=5)

    def test_add_to_history(self):
        """测试添加历史记录"""
        self.analyzer.add_to_history(0.05, 0.04)
        self.analyzer.add_to_history(0.03, 0.02)

        self.assertEqual(len(self.analyzer.ic_history), 2)
        self.assertEqual(len(self.analyzer.rank_ic_history), 2)

    def test_get_ic_statistics(self):
        """测试获取IC统计信息"""
        ic_values = [0.05, 0.03, 0.06, 0.04, 0.05]
        for ic in ic_values:
            self.analyzer.add_to_history(ic)

        stats = self.analyzer.get_ic_statistics()

        self.assertIn("ic_mean", stats)
        self.assertIn("ic_std", stats)
        self.assertIn("ic_ir", stats)
        self.assertEqual(stats["ic_count"], 5)

    def test_clear_history(self):
        """测试清除历史记录"""
        self.analyzer.add_to_history(0.05, 0.04)
        self.analyzer.clear_history()

        self.assertEqual(len(self.analyzer.ic_history), 0)
        self.assertEqual(len(self.analyzer.rank_ic_history), 0)


class TestChinaMetrics(unittest.TestCase):
    """测试A股评估指标"""

    def setUp(self):
        """测试前准备"""
        np.random.seed(42)
        self.metrics = ChinaMetrics(risk_free_rate=0.03)

    def test_calculate_alpha(self):
        """测试Alpha计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.025, 0.01])

        alpha = self.metrics.calculate_alpha(returns, benchmark_returns)

        # Alpha应该是超额收益的均值
        excess = returns - benchmark_returns
        expected_alpha = np.mean(excess) * 252
        self.assertAlmostEqual(alpha, expected_alpha, places=5)

    def test_calculate_beta(self):
        """测试Beta计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.025, 0.01])

        beta = self.metrics.calculate_beta(returns, benchmark_returns)

        # Beta应该在合理范围内
        self.assertGreater(beta, 0)

    def test_calculate_tracking_error(self):
        """测试跟踪误差计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.025, 0.01])

        te = self.metrics.calculate_tracking_error(returns, benchmark_returns)

        # 跟踪误差应该是非负的
        self.assertGreaterEqual(te, 0)

    def test_calculate_information_ratio(self):
        """测试信息比率计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.025, 0.01])

        ir = self.metrics.calculate_information_ratio(returns, benchmark_returns)

        # 信息比率应该是有限的数值
        self.assertTrue(np.isfinite(ir))

    def test_calculate_sharpe_ratio(self):
        """测试夏普比率计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015])

        sharpe = self.metrics.calculate_sharpe_ratio(returns)

        # 夏普比率应该是有限的数值
        self.assertTrue(np.isfinite(sharpe))

    def test_calculate_max_consecutive_wins(self):
        """测试最大连续盈利次数计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015, 0.02, 0.01, -0.02])

        max_wins = self.metrics.calculate_max_consecutive_wins(returns)

        # 应该是4（0.01, 0.02之后-0.01中断，然后0.03, 0.015, 0.02, 0.01连续4个正收益）
        self.assertEqual(max_wins, 4)

    def test_calculate_max_consecutive_losses(self):
        """测试最大连续亏损次数计算"""
        returns = np.array([-0.01, -0.02, 0.01, -0.03, -0.015, -0.02, 0.01, -0.02])

        max_losses = self.metrics.calculate_max_consecutive_losses(returns)

        # 应该是3（-0.03, -0.015, -0.02连续3个负收益）
        self.assertEqual(max_losses, 3)

    def test_calculate_win_rate(self):
        """测试胜率计算"""
        returns = np.array([0.01, -0.02, 0.01, -0.01, 0.03])

        win_rate = self.metrics.calculate_win_rate(returns)

        # 胜率应该是3/5 = 0.6
        self.assertAlmostEqual(win_rate, 0.6)

    def test_calculate_profit_loss_ratio(self):
        """测试盈亏比计算"""
        profits = np.array([0.02, 0.03, 0.01])
        losses = np.array([-0.01, -0.02, -0.015])
        returns = np.concatenate([profits, losses])

        pl_ratio = self.metrics.calculate_profit_loss_ratio(returns)

        # 盈亏比应该是 (0.02+0.03+0.01)/3 / (0.01+0.02+0.015)/3
        expected = np.mean(profits) / np.mean(np.abs(losses))
        self.assertAlmostEqual(pl_ratio, expected, places=5)

    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        returns = np.array([0.01, 0.02, -0.05, 0.03, 0.01, -0.10, 0.02])

        max_dd = self.metrics.calculate_max_drawdown(returns)

        # 最大回撤应该是正数
        self.assertGreater(max_dd, 0)

    def test_calculate_calmar_ratio(self):
        """测试Calmar比率计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015])

        calmar = self.metrics.calculate_calmar_ratio(returns)

        # Calmar比率应该是有限的数值
        self.assertTrue(np.isfinite(calmar))

    def test_calculate_all_metrics(self):
        """测试计算所有指标"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.015, 0.02, -0.02, 0.01])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.025, 0.01, 0.015, -0.01, 0.005])

        all_metrics = self.metrics.calculate_all_metrics(returns, benchmark_returns)

        # 应该包含所有关键指标
        self.assertIn("total_return", all_metrics)
        self.assertIn("annual_return", all_metrics)
        self.assertIn("sharpe_ratio", all_metrics)
        self.assertIn("alpha", all_metrics)
        self.assertIn("beta", all_metrics)
        self.assertIn("tracking_error", all_metrics)
        self.assertIn("information_ratio", all_metrics)


class TestModelValidator(unittest.TestCase):
    """测试模型验证器"""

    def setUp(self):
        """测试前准备"""
        np.random.seed(42)
        self.validator = ModelValidator()

    def test_cross_validate_without_model(self):
        """测试不提供模型时的交叉验证"""
        X = np.random.randn(100, 5)
        y = np.random.randn(100)

        result = self.validator.cross_validate(X, y, n_splits=5)

        self.assertIn("note", result)
        self.assertIn("n_splits", result)

    def test_cross_validate_with_model(self):
        """测试提供模型时的交叉验证"""
        from sklearn.ensemble import RandomForestClassifier

        # 生成分类数据
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        result = self.validator.cross_validate(X, y, n_splits=3, model=model, scoring="accuracy")

        self.assertIn("mean_score", result)
        self.assertIn("std_score", result)
        self.assertIn("scores", result)

    def test_walk_forward_validation(self):
        """测试滚动向前验证"""
        from sklearn.ensemble import RandomForestClassifier

        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        result = self.validator.walk_forward_validation(X, y, train_size=50, model=model)

        self.assertIn("mean_score", result)
        self.assertIn("n_iterations", result)

    def test_backtest(self):
        """测试回测验证"""
        predictions = np.random.randn(100) * 0.01
        actuals = predictions + np.random.randn(100) * 0.005

        result = self.validator.backtest(predictions, actuals, initial_capital=1000000)

        # 验证返回的是BacktestResult对象
        self.assertIsInstance(result, BacktestResult)
        self.assertIsInstance(result.start_date, date)
        self.assertIsInstance(result.end_date, date)

    def test_backtest_with_signals(self):
        """测试带信号回测"""
        predictions = np.random.randn(50) * 0.01
        actuals = predictions + np.random.randn(50) * 0.005
        dates = [date.today() - timedelta(days=50-i) for i in range(50)]

        result = self.validator.backtest_with_signals(predictions, actuals, dates)

        # 验证返回的字典包含所有必要字段
        self.assertIn("total_return", result)
        self.assertIn("annual_return", result)
        self.assertIn("sharpe_ratio", result)
        self.assertIn("max_drawdown", result)
        self.assertIn("win_rate", result)
        self.assertIn("ic", result)
        self.assertIn("rank_ic", result)

    def test_validate_stability(self):
        """测试稳定性验证"""
        scores = [0.6, 0.55, 0.65, 0.58, 0.62]

        result = self.validator.validate_stability(scores, threshold=0.15)

        self.assertIn("is_stable", result)
        self.assertIn("cv", result)
        self.assertIn("mean", result)
        self.assertIn("std", result)

    def test_validate_stability_empty(self):
        """测试空得分的稳定性验证"""
        result = self.validator.validate_stability([])

        self.assertIn("is_stable", result)
        self.assertFalse(result["is_stable"])

    def test_validate_with_ic(self):
        """测试IC验证"""
        predictions = np.random.randn(100) * 0.01
        actuals = predictions + np.random.randn(100) * 0.005

        result = self.validator.validate_with_ic(predictions, actuals)

        self.assertIn("ic", result)
        self.assertIn("rank_ic", result)
        self.assertIn("ir", result)

    def test_get_validation_summary(self):
        """测试获取验证总结"""
        # 先进行一些验证
        from sklearn.ensemble import RandomForestClassifier
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.validator.cross_validate(X, y, n_splits=3, model=model)

        summary = self.validator.get_validation_summary()

        self.assertIn("total_validations", summary)
        self.assertGreater(summary["total_validations"], 0)

    def test_clear_results(self):
        """测试清除结果"""
        from sklearn.ensemble import RandomForestClassifier
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.validator.cross_validate(X, y, n_splits=3, model=model)

        self.validator.clear_results()

        self.assertEqual(len(self.validator.validation_results), 0)


if __name__ == "__main__":
    unittest.main()
