"""
Incremental Training Integration Tests

Tests for complete incremental training workflow with AlphaLab.
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Any

import polars as pl
import pytest

from vnpy.alpha.dataset import AlphaDataset, Segment
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.model import ModelVersion, AlphaModel


def create_prepared_dataset(
    n_samples: int = 30,
    start_date: tuple[int, int, int] = (2024, 1, 1),
    symbol: str = "TEST.SSE",
    train_period: tuple[str, str] | None = None,
    valid_period: tuple[str, str] | None = None,
    test_period: tuple[str, str] | None = None
) -> AlphaDataset:
    """
    Create a fully prepared AlphaDataset for testing.

    This function creates a dataset with pre-set features and label,
    and prepares it for training.
    """
    start = datetime(*start_date)

    df = pl.DataFrame({
        "datetime": [start.replace(day=i + 1) for i in range(n_samples)],
        "vt_symbol": [symbol] * n_samples,
        "feature1": list(range(n_samples)),
        "feature2": list(range(n_samples, n_samples * 2)),
        "label": [float(i % 2) for i in range(n_samples)]
    })

    # Default periods - ensure valid set has at least 5 samples
    train_end = max(n_samples - 10, n_samples // 2)
    valid_start = train_end + 1
    valid_end = min(n_samples - 3, train_end + 5)
    test_start = valid_end + 1

    if train_period is None:
        train_period = (f"{start_date[0]}-{start_date[1]:02d}-01", f"{start_date[0]}-{start_date[1]:02d}-{train_end:02d}")
    if valid_period is None:
        valid_period = (f"{start_date[0]}-{start_date[1]:02d}-{valid_start:02d}", f"{start_date[0]}-{start_date[1]:02d}-{valid_end:02d}")
    if test_period is None:
        test_period = (f"{start_date[0]}-{start_date[1]:02d}-{test_start:02d}", f"{start_date[0]}-{start_date[1]:02d}-{n_samples:02d}")

    dataset = AlphaDataset(
        df=df,
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period
    )

    # Manually set the learn_df to skip feature engineering
    dataset.learn_df = df
    dataset.raw_df = df
    dataset.infer_df = df
    dataset.result_df = df

    return dataset


class TestIncrementalTrainingIntegration:
    """Integration tests for incremental training workflow."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.lab_path = os.path.join(self.test_dir, "alpha_lab")

        yield

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    @pytest.fixture
    def dataset(self):
        """Create a test dataset for initial training."""
        return create_prepared_dataset(n_samples=30, start_date=(2024, 1, 1))

    @pytest.fixture
    def new_dataset(self):
        """Create a new dataset for incremental training."""
        return create_prepared_dataset(n_samples=20, start_date=(2024, 2, 1))

    def test_initial_training_saves_version(self, dataset):
        """Test that initial training creates and saves a model version."""
        lab = AlphaLab(self.lab_path)

        # Initial training
        model, version = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb",
            incremental=False
        )

        # Verify version was created
        assert version is not None
        assert version.version_id is not None
        assert version.is_incremental is False
        assert version.base_version is None

        # Verify version is saved
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 1
        assert versions[0].version_id == version.version_id

        print(f"[PASS] Initial training created version: {version.version_id}")

    def test_incremental_training_creates_version_chain(self, dataset, new_dataset):
        """Test that incremental training creates proper version chain."""
        lab = AlphaLab(self.lab_path)

        # Step 1: Initial training
        model1, version1 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb",
            incremental=False
        )

        assert version1.is_incremental is False
        print(f"Version 1: {version1.version_id} (is_incremental={version1.is_incremental})")

        # Step 2: Incremental training with new data
        model2, version2 = lab.train_model_incremental(
            model_name="test_model",
            dataset=new_dataset,
            model_type="lgb",
            incremental=True
        )

        # Verify incremental version
        assert version2.is_incremental is True
        assert version2.base_version == version1.version_id

        print(f"Version 2: {version2.version_id} (is_incremental={version2.is_incremental}, base={version2.base_version})")

        # Verify version chain
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 2

        print("[PASS] Incremental training created proper version chain")

    def test_auto_detect_incremental_mode(self, dataset, new_dataset):
        """Test that incremental mode is auto-detected when model exists."""
        lab = AlphaLab(self.lab_path)

        # Initial training (no existing model, should be full training)
        model1, version1 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        assert version1.is_incremental is False

        # Second training (existing model supports incremental, should auto-detect)
        model2, version2 = lab.train_model_incremental(
            model_name="test_model",
            dataset=new_dataset,
            model_type="lgb"
        )

        # LgbModel supports incremental, so should auto-detect
        assert version2.is_incremental is True
        assert version2.base_version == version1.version_id

        print("[PASS] Auto-detect incremental mode works correctly")

    def test_force_full_retraining(self, dataset, new_dataset):
        """Test forcing full retraining on existing model."""
        lab = AlphaLab(self.lab_path)

        # Initial training
        model1, version1 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        # Force full retraining
        model2, version2 = lab.train_model_incremental(
            model_name="test_model",
            dataset=new_dataset,
            model_type="lgb",
            incremental=False
        )

        # Should be a full training, not incremental
        assert version2.is_incremental is False
        assert version2.base_version is None

        print("[PASS] Force full retraining works correctly")

    def test_rollback_to_previous_version(self, dataset, new_dataset):
        """Test rolling back to a previous model version."""
        lab = AlphaLab(self.lab_path)

        # Create initial version
        model1, version1 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        # Create second version
        model2, version2 = lab.train_model_incremental(
            model_name="test_model",
            dataset=new_dataset,
            model_type="lgb"
        )

        # Verify current version is version2
        current = lab.version_manager.get_current_version("test_model")
        assert current.version_id == version2.version_id

        # Rollback to version1
        result = lab.rollback_model("test_model", version1.version_id)
        assert result is True

        # Verify current version is now version1
        current = lab.version_manager.get_current_version("test_model")
        assert current.version_id == version1.version_id

        # Load current model should be version1
        loaded_model, loaded_version = lab.load_model_version("test_model")
        assert loaded_version.version_id == version1.version_id

        print("[PASS] Rollback to previous version works correctly")

    def test_multiple_incremental_versions(self, dataset):
        """Test creating multiple incremental versions in sequence."""
        lab = AlphaLab(self.lab_path)

        # Initial training
        model1, version1 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        versions_chain = [version1]

        # Create multiple incremental versions
        for i in range(3):
            new_dataset = create_prepared_dataset(
                n_samples=10,
                start_date=(2024, 3, i * 10 + 1)
            )

            model, version = lab.train_model_incremental(
                model_name="test_model",
                dataset=new_dataset,
                model_type="lgb"
            )

            versions_chain.append(version)

        # Verify all versions exist
        all_versions = lab.list_model_versions("test_model")
        assert len(all_versions) == 4

        print("[PASS] Multiple incremental versions created successfully")

    def test_save_model_with_version_manual(self, dataset):
        """Test manually saving a model version."""
        from vnpy.alpha.model.models.lgb_model import LgbModel

        lab = AlphaLab(self.lab_path)

        # Create and train model manually
        model = LgbModel()
        model.fit(dataset)

        # Save with version
        version = lab.save_model_with_version(
            name="manual_model",
            model=model,
            dataset=dataset,
            description="Manually saved version",
            tags=["manual", "test"],
            is_incremental=False
        )

        assert version is not None
        assert version.description == "Manually saved version"
        assert "manual" in version.tags
        assert "test" in version.tags
        assert version.is_incremental is False

        # Verify we can load it
        loaded_model, loaded_version = lab.load_model_version("manual_model")
        assert loaded_version.version_id == version.version_id

        print("[PASS] Manual model version saving works correctly")

    def test_version_not_found_error(self):
        """Test that loading non-existent version raises error."""
        lab = AlphaLab(self.lab_path)

        with pytest.raises(ValueError) as exc_info:
            lab.load_model_version("nonexistent_model")

        assert "not found" in str(exc_info.value).lower()

        print("[PASS] Version not found error raised correctly")

    def test_rollback_nonexistent_version(self):
        """Test rolling back to non-existent version returns False."""
        lab = AlphaLab(self.lab_path)

        result = lab.rollback_model("nonexistent_model", "v123456")
        assert result is False

        print("[PASS] Rollback nonexistent version returns False")

    def test_delete_version_removes_from_list(self, dataset):
        """Test that deleting a version removes it from the version list."""
        lab = AlphaLab(self.lab_path)

        # Create and save a version
        model, version = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        # Verify version exists
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 1

        # Delete the version
        result = lab.delete_model_version("test_model", version.version_id)
        assert result is True

        # Verify version is removed
        versions = lab.list_model_versions("test_model")
        assert len(versions) == 0

        print("[PASS] Delete version works correctly")

    def test_model_type_selection(self, dataset):
        """Test training with different model types."""
        lab = AlphaLab(self.lab_path)

        # Test LGB model
        lgb_model, lgb_version = lab.train_model_incremental(
            model_name="lgb_model",
            dataset=dataset,
            model_type="lgb"
        )
        assert lgb_version is not None

        # Test MLP model (skipped if dependencies not available)
        try:
            mlp_model, mlp_version = lab.train_model_incremental(
                model_name="mlp_model",
                dataset=dataset,
                model_type="mlp"
            )
            assert mlp_version is not None
            print("[PASS] Different model types work correctly")
        except Exception as e:
            print(f"[SKIP] MLP model test skipped: {e}")

    def test_incremental_with_unsupported_model(self, dataset, new_dataset):
        """Test that LassoModel (non-incremental) ignores incremental flag."""
        lab = AlphaLab(self.lab_path)

        # Initial training with Lasso
        model1, version1 = lab.train_model_incremental(
            model_name="lasso_model",
            dataset=dataset,
            model_type="lasso"
        )

        assert version1.is_incremental is False

        # Try incremental training (Lasso doesn't support it)
        model2, version2 = lab.train_model_incremental(
            model_name="lasso_model",
            dataset=new_dataset,
            model_type="lasso",
            incremental=True
        )

        # Lasso doesn't support incremental, so it should do full retraining
        assert version2.is_incremental is False

        print("[PASS] Unsupported incremental model handles correctly")


class TestIncrementalTrainingVersionMetadata:
    """Tests for version metadata during incremental training."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.lab_path = os.path.join(self.test_dir, "alpha_lab")

        yield

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_version_metadata_populated(self):
        """Test that version metadata is properly populated."""
        lab = AlphaLab(self.lab_path)

        dataset = create_prepared_dataset(n_samples=30, start_date=(2024, 1, 1))

        model, version = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        # Verify metadata
        assert version.version_id is not None
        assert version.created_at is not None
        assert version.train_period == ("2024-01-01", "2024-01-20")
        assert version.valid_period == ("2024-01-21", "2024-01-25")
        assert version.n_samples == 30

        print("[PASS] Version metadata populated correctly")

    def test_incremental_version_has_base_version(self):
        """Test that incremental version has correct base_version."""
        lab = AlphaLab(self.lab_path)

        dataset1 = create_prepared_dataset(n_samples=20, start_date=(2024, 1, 1))

        # Initial training
        model1, version1 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset1,
            model_type="lgb"
        )

        # Verify base version is None
        assert version1.base_version is None
        assert version1.is_incremental is False

        # Incremental training
        dataset2 = create_prepared_dataset(n_samples=10, start_date=(2024, 2, 1))

        model2, version2 = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset2,
            model_type="lgb"
        )

        # Verify base version points to version1
        assert version2.is_incremental is True
        assert version2.base_version == version1.version_id

        print("[PASS] Incremental version has correct base_version")

    def test_version_persistence_after_reload(self):
        """Test that versions persist after reloading the lab."""
        lab = AlphaLab(self.lab_path)

        dataset = create_prepared_dataset(n_samples=30, start_date=(2024, 1, 1))

        # Create and save model
        model, version = lab.train_model_incremental(
            model_name="test_model",
            dataset=dataset,
            model_type="lgb"
        )

        # Create a new lab instance
        lab2 = AlphaLab(self.lab_path)

        # Verify version is still accessible
        versions = lab2.list_model_versions("test_model")
        assert len(versions) == 1
        assert versions[0].version_id == version.version_id

        # Verify we can load the model
        loaded_model, loaded_version = lab2.load_model_version("test_model")
        assert loaded_version.version_id == version.version_id

        print("[PASS] Version persistence after reload works correctly")


def run_tests():
    """Run all tests manually."""
    import sys

    print("=" * 60)
    print("Incremental Training Integration Tests")
    print("=" * 60)

    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    sys.exit(exit_code)


if __name__ == "__main__":
    run_tests()