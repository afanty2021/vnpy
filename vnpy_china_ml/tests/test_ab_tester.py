"""模型A/B测试器单元测试"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
import unittest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy_china_ml.model.manager import ModelManager, ModelMetadata
from vnpy_china_ml.model.ab_tester import ModelABTester
from vnpy_china_ml.model.ab_test import ABTestConfig, ABTestResult
from vnpy_china_ml.model.china_model import ChinaAlphaModel
from vnpy_china_ml.utils.types import ModelType


class TestModelABTester(unittest.TestCase):
    """模型A/B测试器测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.model_dir = Path(self.temp_dir) / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 创建模型管理器
        self.model_manager = ModelManager(model_dir=str(self.model_dir))

        # 创建A/B测试器
        self.ab_tester = ModelABTester(model_manager=self.model_manager)

        # 创建测试模型
        self._create_test_models()

    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_models(self):
        """创建测试模型"""
        import numpy as np

        # 创建第一个模型（随机森林）
        model1 = ChinaAlphaModel(model_type=ModelType.RANDOM_FOREST)
        X = np.random.randn(100, 10)
        y = np.random.randn(100)
        model1.train(X, y, feature_names=[f"feature_{i}" for i in range(10)])
        self.model_id_1 = self.model_manager.register_model(
            model_name="random_forest_model",
            model=model1,
            accuracy=0.75,
            description="随机森林模型"
        )

        # 创建第二个模型（LightGBM）
        model2 = ChinaAlphaModel(model_type=ModelType.LIGHTGBM)
        model2.train(X, y, feature_names=[f"feature_{i}" for i in range(10)])
        self.model_id_2 = self.model_manager.register_model(
            model_name="lightgbm_model",
            model=model2,
            accuracy=0.78,
            description="LightGBM模型"
        )

    def test_create_test(self):
        """测试创建A/B测试"""
        config = ABTestConfig(
            test_name="test_comparison",
            model_ids=[self.model_id_1, self.model_id_2],
            test_data_start=date.today() - timedelta(days=30),
            test_data_end=date.today(),
            metrics=["accuracy", "ic"]
        )

        test_id = self.ab_tester.create_test(config)

        self.assertIsNotNone(test_id)
        self.assertTrue(test_id.startswith("ab_test_"))

        # 验证测试已添加到历史
        self.assertEqual(len(self.ab_tester.test_history), 1)

    def test_create_test_invalid_config(self):
        """测试创建无效配置的测试"""
        # 少于2个模型 - ABTestConfig会在初始化时验证并抛出ValueError
        with self.assertRaises(ValueError):
            config = ABTestConfig(
                test_name="invalid_test",
                model_ids=[self.model_id_1],  # 只有1个模型
                test_data_start=date.today() - timedelta(days=30),
                test_data_end=date.today()
            )

    def test_create_test_nonexistent_model(self):
        """测试使用不存在的模型创建测试"""
        config = ABTestConfig(
            test_name="invalid_test",
            model_ids=[self.model_id_1, "nonexistent_model_id"],
            test_data_start=date.today() - timedelta(days=30),
            test_data_end=date.today()
        )

        test_id = self.ab_tester.create_test(config)

        self.assertIsNone(test_id)

    def test_run_test(self):
        """测试运行A/B测试"""
        # 创建测试
        config = ABTestConfig(
            test_name="test_run",
            model_ids=[self.model_id_1, self.model_id_2],
            test_data_start=date.today() - timedelta(days=30),
            test_data_end=date.today(),
            metrics=["accuracy", "ic", "mse"]
        )

        test_id = self.ab_tester.create_test(config)
        self.assertIsNotNone(test_id)

        # 生成测试数据
        import numpy as np
        X = np.random.randn(200, 10)
        y = np.random.randn(200)

        # 运行测试
        result = self.ab_tester.run_test(test_id, X, y)

        self.assertIsNotNone(result)
        self.assertEqual(result.test_id, test_id)
        self.assertIn(self.model_id_1, result.model_results)
        self.assertIn(self.model_id_2, result.model_results)

        # 验证指标
        for model_id, metrics in result.model_results.items():
            self.assertIn("accuracy", metrics)
            self.assertIn("ic", metrics)
            self.assertIn("mse", metrics)

    def test_evaluate_model(self):
        """测试评估单个模型"""
        import numpy as np

        model = self.model_manager.load_model(self.model_id_1)
        X = np.random.randn(100, 10)
        y = np.random.randn(100)

        metrics = ["accuracy", "ic", "mse", "mae"]
        results = self.ab_tester.evaluate_model(model, X, y, metrics)

        self.assertIn("accuracy", results)
        self.assertIn("ic", results)
        self.assertIn("mse", results)
        self.assertIn("mae", results)

        # 验证指标值在合理范围内
        self.assertGreaterEqual(results["accuracy"], 0.0)
        self.assertLessEqual(results["accuracy"], 1.0)
        self.assertGreaterEqual(results["mse"], 0.0)

    def test_compare_models(self):
        """测试快速对比多个模型"""
        import numpy as np

        X = np.random.randn(100, 10)
        y = np.random.randn(100)

        results = self.ab_tester.compare_models(
            model_ids=[self.model_id_1, self.model_id_2],
            X=X,
            y=y,
            metrics=["accuracy", "ic"]
        )

        self.assertIn(self.model_id_1, results)
        self.assertIn(self.model_id_2, results)

        # 验证每个模型都有指标
        for model_id, metrics in results.items():
            self.assertIn("accuracy", metrics)
            self.assertIn("ic", metrics)

    def test_get_test_history(self):
        """测试获取测试历史"""
        # 创建多个测试
        config1 = ABTestConfig(
            test_name="test1",
            model_ids=[self.model_id_1, self.model_id_2],
            test_data_start=date.today() - timedelta(days=30),
            test_data_end=date.today()
        )

        config2 = ABTestConfig(
            test_name="test2",
            model_ids=[self.model_id_1, self.model_id_2],
            test_data_start=date.today() - timedelta(days=60),
            test_data_end=date.today() - timedelta(days=30)
        )

        self.ab_tester.create_test(config1)
        self.ab_tester.create_test(config2)

        # 获取历史
        history = self.ab_tester.get_test_history()

        self.assertEqual(len(history), 2)

    def test_get_test_result(self):
        """测试获取特定测试结果"""
        config = ABTestConfig(
            test_name="test_get",
            model_ids=[self.model_id_1, self.model_id_2],
            test_data_start=date.today() - timedelta(days=30),
            test_data_end=date.today()
        )

        test_id = self.ab_tester.create_test(config)

        # 获取结果
        result = self.ab_tester.get_test_result(test_id)

        self.assertIsNotNone(result)
        self.assertEqual(result.test_id, test_id)

        # 测试不存在的测试
        nonexistent = self.ab_tester.get_test_result("nonexistent_id")
        self.assertIsNone(nonexistent)

    def test_clear_history(self):
        """测试清空历史"""
        config = ABTestConfig(
            test_name="test_clear",
            model_ids=[self.model_id_1, self.model_id_2],
            test_data_start=date.today() - timedelta(days=30),
            test_data_end=date.today()
        )

        self.ab_tester.create_test(config)
        self.assertEqual(len(self.ab_tester.test_history), 1)

        # 清空历史
        self.ab_tester.clear_history()
        self.assertEqual(len(self.ab_tester.test_history), 0)

    def test_determine_winner(self):
        """测试确定获胜模型"""
        model_results = {
            "model_1": {"accuracy": 0.75, "ic": 0.05},
            "model_2": {"accuracy": 0.78, "ic": 0.06},
            "model_3": {"accuracy": 0.72, "ic": 0.04}
        }

        # 按准确率判断（越高越好）
        winner_acc = self.ab_tester._determine_winner(model_results, "accuracy")
        self.assertEqual(winner_acc, "model_2")

        # 按MSE判断（越低越好）
        model_results_mse = {
            "model_1": {"mse": 0.01},
            "model_2": {"mse": 0.008},
            "model_3": {"mse": 0.012}
        }
        winner_mse = self.ab_tester._determine_winner(model_results_mse, "mse")
        self.assertEqual(winner_mse, "model_2")

    def test_statistical_test(self):
        """测试统计显著性检验"""
        import numpy as np

        results_1 = np.random.randn(100)
        results_2 = np.random.randn(100)

        t_stat, p_value = self.ab_tester.statistical_test(results_1, results_2)

        # 验证返回值
        self.assertIsInstance(t_stat, float)
        self.assertIsInstance(p_value, float)
        self.assertGreaterEqual(p_value, 0.0)
        self.assertLessEqual(p_value, 1.0)


if __name__ == "__main__":
    unittest.main()
