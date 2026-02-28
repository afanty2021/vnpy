"""ModelVersion 数据类单元测试"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径，确保优先加载项目中的 vnpy
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 使用 importlib.util 直接从文件加载模块
import importlib.util

version_file = Path("G:/Berton/vnpy/vnpy/alpha/model/version.py")
spec = importlib.util.spec_from_file_location("version_module", str(version_file))
version_module = importlib.util.module_from_spec(spec)

# 临时保存并替换 sys.modules
original_version = sys.modules.get("vnpy.alpha.model.version")
sys.modules["vnpy.alpha.model.version"] = version_module

spec.loader.exec_module(version_module)

ModelVersion = version_module.ModelVersion

# 恢复原始模块（如果存在）
if original_version:
    sys.modules["vnpy.alpha.model.version"] = original_version


def test_basic_creation():
    """测试基本创建"""
    now = datetime.now()
    version = ModelVersion(
        version_id="v1234567890",
        created_at=now,
        train_period=("2020-01-01", "2022-12-31"),
        valid_period=("2023-01-01", "2023-06-30"),
    )
    assert version.version_id == "v1234567890"
    assert version.created_at == now
    assert version.train_period == ("2020-01-01", "2022-12-31")
    assert version.valid_period == ("2023-01-01", "2023-06-30")
    assert version.n_samples == 0
    assert version.training_duration == 0.0
    assert version.train_loss is None
    assert version.valid_loss is None
    assert version.is_incremental is False
    assert version.base_version is None
    assert version.description == ""
    assert version.tags == []
    print("test_basic_creation PASSED")


def test_with_training_stats():
    """测试带训练统计的创建"""
    now = datetime.now()
    version = ModelVersion(
        version_id="v1234567890",
        created_at=now,
        train_period=("2020-01-01", "2022-12-31"),
        valid_period=("2023-01-01", "2023-06-30"),
        n_samples=10000,
        training_duration=120.5,
        train_loss=0.15,
        valid_loss=0.18,
    )
    assert version.n_samples == 10000
    assert version.training_duration == 120.5
    assert version.train_loss == 0.15
    assert version.valid_loss == 0.18
    print("test_with_training_stats PASSED")


def test_incremental_training():
    """测试增量训练"""
    now = datetime.now()
    version = ModelVersion(
        version_id="v1234567891",
        created_at=now,
        train_period=("2023-07-01", "2023-12-31"),
        valid_period=("2024-01-01", "2024-06-30"),
        is_incremental=True,
        base_version="v1234567890",
    )
    assert version.is_incremental is True
    assert version.base_version == "v1234567890"
    print("test_incremental_training PASSED")


def test_with_metadata():
    """测试带元数据的创建"""
    now = datetime.now()
    version = ModelVersion(
        version_id="v1234567890",
        created_at=now,
        train_period=("2020-01-01", "2022-12-31"),
        valid_period=("2023-01-01", "2023-06-30"),
        description="Initial model version",
        tags=["production", "lgb", "v1"],
    )
    assert version.description == "Initial model version"
    assert version.tags == ["production", "lgb", "v1"]
    print("test_with_metadata PASSED")


def test_version_id_validation():
    """测试版本 ID 验证"""
    now = datetime.now()

    # 测试无效的 version_id
    try:
        ModelVersion(
            version_id="1234567890",  # 缺少 'v' 前缀
            created_at=now,
            train_period=("2020-01-01", "2022-12-31"),
            valid_period=("2023-01-01", "2023-06-30"),
        )
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "version_id must start with 'v'" in str(e)
        print("test_version_id_validation PASSED")


def test_incremental_requires_base():
    """测试增量训练需要 base_version"""
    now = datetime.now()

    # 测试 is_incremental=True 但没有 base_version
    try:
        ModelVersion(
            version_id="v1234567891",
            created_at=now,
            train_period=("2023-07-01", "2023-12-31"),
            valid_period=("2024-01-01", "2024-06-30"),
            is_incremental=True,
            # 缺少 base_version
        )
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "base_version is required for incremental training" in str(e)
        print("test_incremental_requires_base PASSED")


def test_to_dict():
    """测试转换为字典"""
    now = datetime(2024, 1, 1, 12, 0, 0)
    version = ModelVersion(
        version_id="v1234567890",
        created_at=now,
        train_period=("2020-01-01", "2022-12-31"),
        valid_period=("2023-01-01", "2023-06-30"),
        n_samples=10000,
        training_duration=120.5,
        train_loss=0.15,
        valid_loss=0.18,
        description="Test model",
        tags=["test"],
    )

    result = version.to_dict()
    assert result["version_id"] == "v1234567890"
    assert result["created_at"] == "2024-01-01T12:00:00"
    assert result["train_period"] == ("2020-01-01", "2022-12-31")
    assert result["valid_period"] == ("2023-01-01", "2023-06-30")
    assert result["n_samples"] == 10000
    assert result["training_duration"] == 120.5
    assert result["train_loss"] == 0.15
    assert result["valid_loss"] == 0.18
    assert result["description"] == "Test model"
    assert result["tags"] == ["test"]
    print("test_to_dict PASSED")


def test_from_dict():
    """测试从字典创建"""
    now = datetime(2024, 1, 1, 12, 0, 0)
    data = {
        "version_id": "v1234567890",
        "created_at": "2024-01-01T12:00:00",
        "train_period": ("2020-01-01", "2022-12-31"),
        "valid_period": ("2023-01-01", "2023-06-30"),
        "n_samples": 10000,
        "training_duration": 120.5,
        "train_loss": 0.15,
        "valid_loss": 0.18,
        "is_incremental": False,
        "base_version": None,
        "description": "Test model",
        "tags": ["test"],
    }

    version = ModelVersion.from_dict(data)
    assert version.version_id == "v1234567890"
    assert version.created_at == now
    assert version.train_period == ("2020-01-01", "2022-12-31")
    assert version.n_samples == 10000
    assert version.description == "Test model"
    assert version.tags == ["test"]
    print("test_from_dict PASSED")


def test_roundtrip():
    """测试序列化往返"""
    now = datetime.now()
    original = ModelVersion(
        version_id="v1234567890",
        created_at=now,
        train_period=("2020-01-01", "2022-12-31"),
        valid_period=("2023-01-01", "2023-06-30"),
        n_samples=5000,
        training_duration=60.0,
        train_loss=0.2,
        valid_loss=0.25,
        is_incremental=True,
        base_version="v1234567889",
        description="Incremental training",
        tags=["production", "lgb"],
    )

    # 转换为字典再转换回来
    data = original.to_dict()
    restored = ModelVersion.from_dict(data)

    assert restored.version_id == original.version_id
    assert restored.created_at == original.created_at
    assert restored.train_period == original.train_period
    assert restored.valid_period == original.valid_period
    assert restored.n_samples == original.n_samples
    assert restored.training_duration == original.training_duration
    assert restored.train_loss == original.train_loss
    assert restored.valid_loss == original.valid_loss
    assert restored.is_incremental == original.is_incremental
    assert restored.base_version == original.base_version
    assert restored.description == original.description
    assert restored.tags == original.tags
    print("test_roundtrip PASSED")


if __name__ == "__main__":
    test_basic_creation()
    test_with_training_stats()
    test_incremental_training()
    test_with_metadata()
    test_version_id_validation()
    test_incremental_requires_base()
    test_to_dict()
    test_from_dict()
    test_roundtrip()
    print("\n=== All tests passed! ===")
