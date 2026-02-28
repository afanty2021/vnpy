"""测试 AlphaLab 版本管理功能"""

import shutil
import tempfile
from datetime import datetime

import polars as pl
import pytest


class TestAlphaLabVersionManagement:
    """测试 AlphaLab 版本管理方法"""

    @pytest.fixture
    def temp_lab_path(self):
        """创建临时实验室路径"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def dataset(self):
        """创建测试数据集"""
        df = pl.DataFrame({
            "datetime": [datetime(2024, 1, i) for i in range(1, 31)],
            "feature1": list(range(30)),
            "feature2": list(range(30, 60)),
            "label": [i % 2 for i in range(30)]
        })

        from vnpy.alpha.dataset import AlphaDataset
        return AlphaDataset(
            df=df,
            train_period=("2024-01-01", "2024-01-20"),
            valid_period=("2024-01-21", "2024-01-25"),
            test_period=("2024-01-26", "2024-01-30")
        )

    def test_list_model_versions_empty(self, temp_lab_path):
        """测试列出不存在的模型版本"""
        from vnpy.alpha.lab import AlphaLab

        lab = AlphaLab(temp_lab_path)
        versions = lab.list_model_versions("nonexistent_model")
        assert versions == []

    def test_save_and_load_model_version(self, temp_lab_path, dataset):
        """测试保存和加载模型版本"""
        from vnpy.alpha.lab import AlphaLab
        from vnpy.alpha.model import ModelVersion
        from vnpy.alpha.model.models.lgb_model import LgbModel

        # 创建 AlphaLab 实例
        lab = AlphaLab(temp_lab_path)

        # 创建模型实例
        model = LgbModel(dataset)

        # 保存模型版本
        version = lab.save_model_with_version(
            name="test_model",
            model=model,
            dataset=dataset,
            description="测试版本",
            tags=["test"]
        )

        assert version is not None
        assert version.description == "测试版本"
        assert "test" in version.tags

        # 列出版本
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 1
        assert versions[0].version_id == version.version_id

        # 加载版本
        loaded_model, loaded_version = lab.load_model_version("test_model")
        assert loaded_version.version_id == version.version_id

    def test_load_model_version_with_version_id(self, temp_lab_path, dataset):
        """测试通过 version_id 加载指定版本"""
        from vnpy.alpha.lab import AlphaLab
        from vnpy.alpha.model.models.lgb_model import LgbModel

        lab = AlphaLab(temp_lab_path)

        # 创建并保存第一个版本
        model1 = LgbModel(dataset)
        version1 = lab.save_model_with_version("test_model", model1, dataset, "version 1")

        # 创建并保存第二个版本
        model2 = LgbModel(dataset)
        version2 = lab.save_model_with_version("test_model", model2, dataset, "version 2")

        # 列出所有版本
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 2

        # 加载第一个版本
        _, loaded_v1 = lab.load_model_version("test_model", version1.version_id)
        assert loaded_v1.version_id == version1.version_id
        assert loaded_v1.description == "version 1"

    def test_rollback_model(self, temp_lab_path, dataset):
        """测试回滚模型"""
        from vnpy.alpha.lab import AlphaLab
        from vnpy.alpha.model.models.lgb_model import LgbModel

        lab = AlphaLab(temp_lab_path)

        # 创建并保存第一个版本
        model1 = LgbModel(dataset)
        version1 = lab.save_model_with_version("test_model", model1, dataset, "version 1")

        # 创建并保存第二个版本
        model2 = LgbModel(dataset)
        version2 = lab.save_model_with_version("test_model", model2, dataset, "version 2")

        # 回滚到第一个版本
        result = lab.rollback_model("test_model", version1.version_id)
        assert result is True

        # 验证当前版本是第一个版本
        current = lab.version_manager.get_current_version("test_model")
        assert current.version_id == version1.version_id

    def test_delete_model_version(self, temp_lab_path, dataset):
        """测试删除模型版本"""
        from vnpy.alpha.lab import AlphaLab
        from vnpy.alpha.model.models.lgb_model import LgbModel

        lab = AlphaLab(temp_lab_path)

        # 创建并保存版本
        model = LgbModel(dataset)
        version = lab.save_model_with_version("test_model", model, dataset, "to delete")

        # 删除版本
        result = lab.delete_model_version("test_model", version.version_id)
        assert result is True

        # 验证版本已删除
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 0

    def test_load_model_version_nonexistent(self, temp_lab_path):
        """测试加载不存在的模型版本"""
        from vnpy.alpha.lab import AlphaLab

        lab = AlphaLab(temp_lab_path)

        # 应该抛出 ValueError
        with pytest.raises(ValueError) as exc_info:
            lab.load_model_version("nonexistent_model")

        assert "not found" in str(exc_info.value)

    def test_rollback_model_nonexistent(self, temp_lab_path):
        """测试回滚不存在的模型版本"""
        from vnpy.alpha.lab import AlphaLab

        lab = AlphaLab(temp_lab_path)

        # 应该返回 False
        result = lab.rollback_model("nonexistent_model", "v123456")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
