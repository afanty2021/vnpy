"""
Unit tests for ModelVersionManager.
"""

import os
import shutil
import tempfile
from datetime import datetime

import pytest

from vnpy.alpha.model import AlphaModel, ModelVersion, ModelVersionManager


# Simple mock model for testing
class MockModel(AlphaModel):
    """Mock model for testing purposes."""

    def __init__(self, name: str = "mock", accuracy: float = 0.0) -> None:
        """Initialize mock model."""
        self.name = name
        self.accuracy = accuracy
        self._trained = False

    def fit(self, dataset) -> None:
        """Mock fit method."""
        self._trained = True

    def predict(self, dataset, segment) -> list:
        """Mock predict method."""
        return [0.5] * 10


class TestModelVersionManager:
    """Test suite for ModelVersionManager."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.test_dir, "model")

        yield

        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_init(self):
        """Test initialization of ModelVersionManager."""
        manager = ModelVersionManager(self.model_path)

        # versions.json is created lazily when first version is saved
        assert manager.versions == {}

    def test_create_version(self):
        """Test creating a new model version."""
        manager = ModelVersionManager(self.model_path)

        # Create mock model
        model = MockModel(name="test_model", accuracy=0.95)

        # Create version metadata
        version = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime.now(),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31"),
            n_samples=10000,
            train_loss=0.01,
            valid_loss=0.02,
            is_incremental=False,
            description="Test version"
        )

        # Create version
        created_version = manager.create_version("my_model", version, model)

        assert created_version.version_id == "v20260228_100000"
        assert "my_model" in manager.versions
        assert manager.versions["my_model"]["current_version"] == "v20260228_100000"

    def test_get_version(self):
        """Test retrieving a specific version."""
        manager = ModelVersionManager(self.model_path)

        # Create a version first
        model = MockModel(name="test_model", accuracy=0.95)
        version = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime.now(),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version, model)

        # Get the version
        retrieved_version = manager.get_version("my_model", "v20260228_100000")

        assert retrieved_version is not None
        assert retrieved_version.version_id == "v20260228_100000"

    def test_get_current_version(self):
        """Test getting current version."""
        manager = ModelVersionManager(self.model_path)

        # Create first version
        model1 = MockModel(name="test_model", accuracy=0.90)
        version1 = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime(2026, 2, 28, 10, 0, 0),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version1, model1)

        # Create second version
        model2 = MockModel(name="test_model", accuracy=0.95)
        version2 = ModelVersion(
            version_id="v20260228_140000",
            created_at=datetime(2026, 2, 28, 14, 0, 0),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version2, model2)

        # Get current version
        current = manager.get_current_version("my_model")

        assert current is not None
        assert current.version_id == "v20260228_140000"

    def test_list_versions(self):
        """Test listing all versions."""
        manager = ModelVersionManager(self.model_path)

        # Create multiple versions with different times
        base_time = datetime(2026, 2, 28, 10, 0, 0)
        for i in range(3):
            model = MockModel(name="test_model", accuracy=0.90 + i * 0.02)
            version = ModelVersion(
                version_id=f"v20260228_{i:06d}",
                created_at=base_time.replace(minute=i),  # Different minutes
                train_period=("2020-01-01", "2025-12-31"),
                valid_period=("2023-01-01", "2023-12-31")
            )
            manager.create_version("my_model", version, model)

        # List versions
        versions = manager.list_versions("my_model")

        assert len(versions) == 3
        # Should be sorted by created_at, newest first
        # version with i=2 has created_at with minute=2, which is newest
        assert versions[0].version_id == "v20260228_000002"

    def test_delete_version(self):
        """Test deleting a version."""
        manager = ModelVersionManager(self.model_path)

        # Create a version
        model = MockModel(name="test_model", accuracy=0.95)
        version = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime.now(),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version, model)

        # Delete the version
        result = manager.delete_version("my_model", "v20260228_100000")

        assert result is True
        assert len(manager.versions["my_model"]["versions"]) == 0

    def test_rollback(self):
        """Test rolling back to a specific version."""
        manager = ModelVersionManager(self.model_path)

        # Create first version
        model1 = MockModel(name="test_model", accuracy=0.90)
        version1 = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime(2026, 2, 28, 10, 0, 0),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version1, model1)

        # Create second version
        model2 = MockModel(name="test_model", accuracy=0.95)
        version2 = ModelVersion(
            version_id="v20260228_140000",
            created_at=datetime(2026, 2, 28, 14, 0, 0),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version2, model2)

        # Rollback to first version
        result = manager.rollback("my_model", "v20260228_100000")

        assert result is True
        assert manager.versions["my_model"]["current_version"] == "v20260228_100000"

    def test_load_model(self):
        """Test loading a model."""
        manager = ModelVersionManager(self.model_path)

        # Create a version with known accuracy
        model = MockModel(name="test_model", accuracy=0.95)
        version = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime.now(),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version, model)

        # Load model
        loaded_model = manager.load_model("my_model", "v20260228_100000")

        assert loaded_model is not None
        assert loaded_model.accuracy == 0.95

    def test_load_current_model(self):
        """Test loading current model (backward compatibility)."""
        manager = ModelVersionManager(self.model_path)

        # Create a version
        model = MockModel(name="test_model", accuracy=0.95)
        version = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime.now(),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31")
        )
        manager.create_version("my_model", version, model)

        # Load current model
        current_model = manager.load_model("my_model")

        assert current_model is not None
        assert current_model.accuracy == 0.95

    def test_version_not_found(self):
        """Test getting a non-existent version."""
        manager = ModelVersionManager(self.model_path)

        version = manager.get_version("nonexistent", "v00000000_000000")
        assert version is None

    def test_incremental_version(self):
        """Test creating an incremental version."""
        manager = ModelVersionManager(self.model_path)

        # Create base version
        model1 = MockModel(name="test_model", accuracy=0.90)
        version1 = ModelVersion(
            version_id="v20260228_100000",
            created_at=datetime.now(),
            train_period=("2020-01-01", "2025-12-31"),
            valid_period=("2023-01-01", "2023-12-31"),
            is_incremental=False
        )
        manager.create_version("my_model", version1, model1)

        # Create incremental version
        model2 = MockModel(name="test_model", accuracy=0.95)
        version2 = ModelVersion(
            version_id="v20260228_140000",
            created_at=datetime.now(),
            train_period=("2025-01-01", "2025-12-31"),
            valid_period=("2025-01-01", "2025-12-31"),
            is_incremental=True,
            base_version="v20260228_100000"
        )
        manager.create_version("my_model", version2, model2)

        # Verify incremental version
        retrieved = manager.get_version("my_model", "v20260228_140000")

        assert retrieved is not None
        assert retrieved.is_incremental is True
        assert retrieved.base_version == "v20260228_100000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
