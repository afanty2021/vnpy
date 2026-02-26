"""模型版本管理器单元测试"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import unittest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy_china_ml.model.manager import ModelManager, ModelMetadata
from vnpy_china_ml.model.version_manager import ModelVersionManager
from vnpy_china_ml.model.china_model import ChinaAlphaModel
from vnpy_china_ml.utils.types import ModelType


class TestModelVersionManager(unittest.TestCase):
    """模型版本管理器测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.model_dir = Path(self.temp_dir) / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 创建模型管理器
        self.model_manager = ModelManager(model_dir=str(self.model_dir))

        # 创建版本管理器
        self.version_manager = ModelVersionManager(
            model_manager=self.model_manager,
            model_dir=str(self.model_dir)
        )

        # 创建一个测试模型
        self._create_test_model()

    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_model(self):
        """创建测试模型"""
        import numpy as np

        # 创建模型
        model = ChinaAlphaModel(model_type=ModelType.RANDOM_FOREST)

        # 训练模型
        X = np.random.randn(100, 10)
        y = np.random.randn(100)

        model.train(X, y, feature_names=[f"feature_{i}" for i in range(10)])

        # 注册模型
        self.test_model_id = self.model_manager.register_model(
            model_name="test_model",
            model=model,
            accuracy=0.75,
            description="测试模型"
        )

    def test_create_version(self):
        """测试创建版本"""
        # 创建版本
        version_id = self.version_manager.create_version(
            model_name="test_model",
            version="1.0.1",
            tag="development",
            changelog="第一次版本迭代"
        )

        self.assertIsNotNone(version_id)
        self.assertIn("1_0_1", version_id)

        # 验证版本信息已保存
        version_info = self.version_manager._load_version_info(version_id)
        self.assertIsNotNone(version_info)
        self.assertEqual(version_info.version, "1.0.1")
        self.assertEqual(version_info.version_tag, "development")
        self.assertEqual(version_info.changelog, "第一次版本迭代")

    def test_create_version_with_parent(self):
        """测试创建带父版本的版本"""
        # 创建第一个版本
        version_id_1 = self.version_manager.create_version(
            model_name="test_model",
            version="1.0.0",
            tag="production",
            changelog="初始版本"
        )

        # 创建第二个版本，以第一个为父版本
        version_id_2 = self.version_manager.create_version(
            model_name="test_model",
            version="1.1.0",
            parent_id=version_id_1,
            tag="staging",
            changelog="优化准确率"
        )

        self.assertIsNotNone(version_id_2)

        # 验证父子关系
        version_info_2 = self.version_manager._load_version_info(version_id_2)
        self.assertEqual(version_info_2.parent_model_id, version_id_1)

    def test_get_version_history(self):
        """测试获取版本历史"""
        # 创建多个版本
        self.version_manager.create_version("test_model", "1.0.0")
        self.version_manager.create_version("test_model", "1.0.1")
        self.version_manager.create_version("test_model", "1.1.0")

        # 获取版本历史
        history = self.version_manager.get_version_history("test_model")

        self.assertGreaterEqual(len(history), 3)  # 至少有3个版本

        # 验证按时间倒序排列
        if len(history) >= 2:
            self.assertGreaterEqual(
                history[0].training_date or datetime.min,
                history[1].training_date or datetime.min
            )

    def test_get_version_tree(self):
        """测试获取版本树"""
        # 创建版本
        self.version_manager.create_version("test_model", "1.0.0")
        self.version_manager.create_version("test_model", "1.0.1")

        # 获取版本树
        tree = self.version_manager.get_version_tree("test_model")

        self.assertGreaterEqual(len(tree), 2)

        # 验证版本树结构
        for item in tree:
            self.assertIn("model_id", item)
            self.assertIn("version", item)
            self.assertIn("parent_id", item)
            self.assertIn("tag", item)
            self.assertIn("created_at", item)

    def test_tag_version(self):
        """测试打标签"""
        # 创建版本
        version_id = self.version_manager.create_version("test_model", "1.0.0")

        # 打标签
        result = self.version_manager.tag_version(version_id, "production")

        self.assertTrue(result)

        # 验证标签已更新
        version_info = self.version_manager._load_version_info(version_id)
        self.assertEqual(version_info.version_tag, "production")
        self.assertTrue(version_info.is_production)

    def test_set_production_version(self):
        """测试设置生产版本"""
        # 创建两个版本
        version_id_1 = self.version_manager.create_version("test_model", "1.0.0")
        version_id_2 = self.version_manager.create_version("test_model", "1.0.1")

        # 设置第二个为生产版本
        result = self.version_manager.set_production_version(version_id_2)

        self.assertTrue(result)

        # 验证生产版本
        production = self.version_manager.get_production_version("test_model")
        self.assertIsNotNone(production)
        self.assertIn(production.model_id, [version_id_2])

    def test_compare_versions(self):
        """测试版本对比"""
        # 创建两个版本
        version_id_1 = self.version_manager.create_version("test_model", "1.0.0")
        version_id_2 = self.version_manager.create_version("test_model", "1.0.1")

        # 对比版本
        comparison = self.version_manager.compare_versions(version_id_1, version_id_2)

        self.assertIn("model_1", comparison)
        self.assertIn("model_2", comparison)
        self.assertIn("differences", comparison)

    def test_rollback_to_version(self):
        """测试版本回滚"""
        # 创建版本
        version_id = self.version_manager.create_version("test_model", "1.0.0")

        # 回滚到该版本
        result = self.version_manager.rollback_to_version(version_id)

        self.assertTrue(result)

        # 验证创建了新版本
        history = self.version_manager.get_version_history("test_model")
        self.assertGreater(len(history), 1)

    def test_get_all_version_tags(self):
        """测试获取所有版本标签"""
        # 创建不同标签的版本
        v1 = self.version_manager.create_version("test_model", "1.0.0", tag="production")
        v2 = self.version_manager.create_version("test_model", "1.1.0", tag="staging")
        v3 = self.version_manager.create_version("test_model", "1.2.0", tag="development")

        # 获取所有标签
        tags = self.version_manager.get_all_version_tags()

        self.assertIn("production", tags)
        self.assertIn("staging", tags)
        self.assertIn("development", tags)


if __name__ == "__main__":
    unittest.main()
