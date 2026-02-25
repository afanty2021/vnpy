"""
因子组合模块单元测试

测试因子组合、权重分配、正交化等功能。
"""

import unittest
import numpy as np
import polars as pl
from datetime import datetime, date
from unittest.mock import patch

from vnpy_china_ml.factors.combination import (
    FactorCombiner,
    FactorTimer,
    FactorCombinationConfig,
    FactorTimingConfig,
    FactorWeight,
    WeightMethod,
    OrthogonalMethod,
    create_factor_combiner,
)


class TestFactorWeight(unittest.TestCase):
    """测试因子权重数据类"""

    def test_create_factor_weight(self):
        """测试创建因子权重"""
        weight = FactorWeight(
            factor_name="Return_5d",
            weight=0.5,
            ic=0.03,
            ir=1.2
        )

        self.assertEqual(weight.factor_name, "Return_5d")
        self.assertEqual(weight.weight, 0.5)
        self.assertEqual(weight.ic, 0.03)
        self.assertEqual(weight.ir, 1.2)


class TestFactorCombinationConfig(unittest.TestCase):
    """测试因子组合配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = FactorCombinationConfig(
            factors=["Return_5d", "Volume_Ratio", "RSI_14"]
        )

        self.assertEqual(config.factors, ["Return_5d", "Volume_Ratio", "RSI_14"])
        self.assertIsNone(config.weights)
        self.assertEqual(config.weight_method, WeightMethod.IC_WEIGHTED)
        self.assertEqual(config.orthogonal_method, OrthogonalMethod.NONE)
        self.assertTrue(config.normalize)
        self.assertTrue(config.winsorize)
        self.assertEqual(config.winsorize_method, "mad")

    def test_custom_config(self):
        """测试自定义配置"""
        custom_weights = {"Return_5d": 0.6, "Volume_Ratio": 0.3, "RSI_14": 0.1}

        config = FactorCombinationConfig(
            factors=["Return_5d", "Volume_Ratio", "RSI_14"],
            weights=custom_weights,
            weight_method=WeightMethod.CUSTOM,
            orthogonal_method=OrthogonalMethod.GRAM_SCHMIDT,
            normalize=False,
            winsorize=False
        )

        self.assertEqual(config.weights, custom_weights)
        self.assertEqual(config.weight_method, WeightMethod.CUSTOM)
        self.assertEqual(config.orthogonal_method, OrthogonalMethod.GRAM_SCHMIDT)
        self.assertFalse(config.normalize)
        self.assertFalse(config.winsorize)


class TestFactorTimingConfig(unittest.TestCase):
    """测试因子择时配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = FactorTimingConfig()

        self.assertFalse(config.enable_timing)
        self.assertEqual(config.lookback_window, 20)
        self.assertEqual(config.ic_threshold, 0.02)
        self.assertTrue(config.volatility_adjust)
        self.assertFalse(config.regime_switch)


class TestFactorCombiner(unittest.TestCase):
    """测试因子组合器"""

    def setUp(self):
        """设置测试环境"""
        self.factors = ["Return_5d", "Volume_Ratio", "RSI_14"]
        self.config = FactorCombinationConfig(factors=self.factors)
        self.combiner = FactorCombiner(self.config)

    def _create_test_data(self, n_samples: int = 1000):
        """创建测试数据

        Args:
            n_samples: 样本数量

        Returns:
            测试DataFrame
        """
        np.random.seed(42)

        symbols = [f"stock_{i % 50}" for i in range(n_samples)]
        dates = [datetime(2024, 1, (i % 20) + 1) for i in range(n_samples)]

        return pl.DataFrame({
            "datetime": dates,
            "symbol": symbols,
            "Return_5d": np.random.randn(n_samples) * 0.05,
            "Volume_Ratio": np.random.randn(n_samples) * 0.3 + 1.0,
            "RSI_14": np.random.rand(n_samples) * 100
        })

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.combiner.config.factors, self.factors)
        self.assertEqual(len(self.combiner.factor_weights), 0)
        self.assertFalse(self.combiner.orthogonalized)

    def test_combine_factors_equal_weight(self):
        """测试等权重组合"""
        config = FactorCombinationConfig(
            factors=self.factors,
            weight_method=WeightMethod.EQUAL
        )
        combiner = FactorCombiner(config)

        df = self._create_test_data()
        result = combiner.combine_factors(df)

        self.assertIn("combined_factor", result.columns)

        # 验证权重
        weights = combiner.get_weights()
        self.assertEqual(len(weights), 3)
        for w in weights:
            self.assertAlmostEqual(w.weight, 1.0 / 3, places=5)

    def test_combine_factors_ic_weighted(self):
        """测试IC加权组合"""
        config = FactorCombinationConfig(
            factors=self.factors,
            weight_method=WeightMethod.IC_WEIGHTED
        )
        combiner = FactorCombiner(config)

        df = self._create_test_data()

        ic_data = {"Return_5d": 0.05, "Volume_Ratio": 0.03, "RSI_14": 0.02}
        result = combiner.combine_factors(df, ic_data=ic_data)

        self.assertIn("combined_factor", result.columns)

        # 验证权重与IC成正比
        weights = combiner.get_weights()
        weight_dict = {w.factor_name: w.weight for w in weights}

        # Return_5d的IC最大，权重应该最大
        self.assertGreater(weight_dict["Return_5d"], weight_dict["RSI_14"])

    def test_combine_factors_custom_weight(self):
        """测试自定义权重"""
        custom_weights = {"Return_5d": 0.6, "Volume_Ratio": 0.3, "RSI_14": 0.1}

        config = FactorCombinationConfig(
            factors=self.factors,
            weights=custom_weights,
            weight_method=WeightMethod.CUSTOM
        )
        combiner = FactorCombiner(config)

        df = self._create_test_data()
        result = combiner.combine_factors(df)

        # 验证权重
        weights = combiner.get_weights()
        weight_dict = {w.factor_name: w.weight for w in weights}

        self.assertAlmostEqual(weight_dict["Return_5d"], 0.6, places=5)
        self.assertAlmostEqual(weight_dict["Volume_Ratio"], 0.3, places=5)
        self.assertAlmostEqual(weight_dict["RSI_14"], 0.1, places=5)

    def test_winsorize(self):
        """测试去极值"""
        data = np.array([1.0, 2.0, 3.0, 100.0, -50.0, 4.0, 5.0])  # 包含极值

        # MAD方法
        result_mad = self.combiner._winsorize(data, "mad")
        self.assertNotIn(100.0, result_mad)
        self.assertNotIn(-50.0, result_mad)

        # 标准差方法
        result_std = self.combiner._winsorize(data, "std")
        self.assertLessEqual(np.max(result_std), 100.0)
        self.assertGreaterEqual(np.min(result_std), -50.0)

        # 百分位方法
        result_pct = self.combiner._winsorize(data, "percentile")
        self.assertLessEqual(np.max(result_pct), 100.0)

    def test_zscore(self):
        """测试标准化"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        result = self.combiner._zscore(data)

        # 验证均值接近0，标准差接近1
        self.assertAlmostEqual(np.mean(result), 0.0, places=5)
        self.assertAlmostEqual(np.std(result), 1.0, places=5)

    def test_gram_schmidt_orthogonalization(self):
        """测试Gram-Schmidt正交化"""
        config = FactorCombinationConfig(
            factors=["factor1", "factor2"],
            orthogonal_method=OrthogonalMethod.GRAM_SCHMIDT
        )
        combiner = FactorCombiner(config)

        df = pl.DataFrame({
            "datetime": [datetime(2024, 1, i) for i in range(1, 11)],
            "symbol": ["A"] * 10,
            "factor1": np.arange(10),
            "factor2": np.arange(10) * 2 + np.random.randn(10) * 0.1  # 与factor1高度相关
        })

        result = combiner.combine_factors(df)

        self.assertTrue(combiner.orthogonalized)

    def test_pca_orthogonalization(self):
        """测试PCA正交化"""
        config = FactorCombinationConfig(
            factors=["factor1", "factor2"],
            orthogonal_method=OrthogonalMethod.PCA
        )
        combiner = FactorCombiner(config)

        df = pl.DataFrame({
            "datetime": [datetime(2024, 1, i) for i in range(1, 11)],
            "symbol": ["A"] * 10,
            "factor1": np.random.randn(10),
            "factor2": np.random.randn(10)
        })

        result = combiner.combine_factors(df)

        self.assertTrue(combiner.orthogonalized)

    def test_get_weights(self):
        """测试获取权重"""
        df = self._create_test_data()
        self.combiner.combine_factors(df)

        weights = self.combiner.get_weights()

        self.assertIsInstance(weights, list)
        self.assertEqual(len(weights), 3)

        for w in weights:
            self.assertIsInstance(w, FactorWeight)
            self.assertIn(w.factor_name, self.factors)
            self.assertGreaterEqual(w.weight, 0.0)
            self.assertLessEqual(w.weight, 1.0)


class TestFactorTimer(unittest.TestCase):
    """测试因子择时器"""

    def setUp(self):
        """设置测试环境"""
        config = FactorTimingConfig(
            enable_timing=True,
            lookback_window=10,
            ic_threshold=0.02
        )
        self.timer = FactorTimer(config)

    def test_initialization(self):
        """测试初始化"""
        # 配置中enable_timing默认是False，但测试中我们创建时传入的是True
        # 这里改为测试默认配置
        default_config = FactorTimingConfig()
        self.assertFalse(default_config.enable_timing)

        # 测试自定义配置的timer
        self.assertTrue(self.timer.config.enable_timing)
        self.assertEqual(self.timer.ic_history, {})

    def test_update_ic(self):
        """测试更新IC"""
        self.timer.update_ic("Return_5d", 0.05)
        self.timer.update_ic("Return_5d", 0.03)
        self.timer.update_ic("Volume_Ratio", 0.02)

        self.assertIn("Return_5d", self.timer.ic_history)
        self.assertEqual(len(self.timer.ic_history["Return_5d"]), 2)
        self.assertIn("Volume_Ratio", self.timer.ic_history)

    def test_ic_history_window_limit(self):
        """测试IC历史窗口限制"""
        # 添加超过窗口大小的IC值
        for i in range(15):
            self.timer.update_ic("Return_5d", 0.01 * i)

        # 窗口大小为10，应该只保留最近10个
        self.assertEqual(len(self.timer.ic_history["Return_5d"]), 10)

    def test_get_timing_weights_disabled(self):
        """测试禁用择时时的权重"""
        config = FactorTimingConfig(enable_timing=False)
        timer = FactorTimer(config)

        factors = ["Return_5d", "Volume_Ratio", "RSI_14"]
        weights = timer.get_timing_weights(factors)

        # 禁用择时时返回等权重
        self.assertEqual(len(weights), 3)
        for w in weights.values():
            self.assertAlmostEqual(w, 1.0 / 3, places=5)

    def test_get_timing_weights_enabled(self):
        """测试启用择时时的权重"""
        config = FactorTimingConfig(
            enable_timing=True,
            lookback_window=5,
            ic_threshold=0.02
        )
        timer = FactorTimer(config)

        # 更新IC历史
        for _ in range(5):
            timer.update_ic("Return_5d", 0.05)  # 高IC
            timer.update_ic("Volume_Ratio", 0.01)  # 低IC（低于阈值）
            timer.update_ic("RSI_14", -0.03)  # 负IC（绝对值高于阈值）

        factors = ["Return_5d", "Volume_Ratio", "RSI_14"]
        weights = timer.get_timing_weights(factors)

        # Volume_Ratio的IC低于阈值，权重应该为0
        self.assertEqual(weights["Volume_Ratio"], 0.0)

        # Return_5d和RSI_14应该有非零权重
        self.assertGreater(weights["Return_5d"], 0.0)
        self.assertGreater(weights["RSI_14"], 0.0)


class TestCreateFactorCombiner(unittest.TestCase):
    """测试因子组合器工厂函数"""

    def test_create_with_default_params(self):
        """测试使用默认参数创建"""
        combiner = create_factor_combiner(
            factors=["Return_5d", "Volume_Ratio"]
        )

        self.assertIsInstance(combiner, FactorCombiner)
        self.assertEqual(combiner.config.weight_method, WeightMethod.IC_WEIGHTED)

    def test_create_with_custom_params(self):
        """测试使用自定义参数创建"""
        custom_weights = {"Return_5d": 0.7, "Volume_Ratio": 0.3}

        combiner = create_factor_combiner(
            factors=["Return_5d", "Volume_Ratio"],
            weight_method="custom",
            orthogonal_method="gram_schmidt",
            custom_weights=custom_weights
        )

        self.assertEqual(combiner.config.weight_method, WeightMethod.CUSTOM)
        self.assertEqual(combiner.config.orthogonal_method, OrthogonalMethod.GRAM_SCHMIDT)
        self.assertEqual(combiner.config.weights, custom_weights)

    def test_create_with_enum_params(self):
        """测试使用枚举参数创建"""
        combiner = create_factor_combiner(
            factors=["Return_5d"],
            weight_method=WeightMethod.EQUAL,
            orthogonal_method=OrthogonalMethod.PCA
        )

        self.assertEqual(combiner.config.weight_method, WeightMethod.EQUAL)
        self.assertEqual(combiner.config.orthogonal_method, OrthogonalMethod.PCA)


if __name__ == "__main__":
    unittest.main()
