"""
Model version manager for tracking and managing model versions.

This module provides version management functionality for AlphaModel,
including version creation, retrieval, listing, deletion, and rollback.
"""

import json
import pickle
from datetime import datetime
from pathlib import Path

from vnpy.alpha.logger import logger
from vnpy.alpha.model import AlphaModel, ModelVersion


def _load_pickle_file(path: Path) -> AlphaModel | None:
    """
    Load a pickle file and return the AlphaModel.

    Args:
        path: Path to the pickle file

    Returns:
        AlphaModel instance if loaded successfully, None otherwise
    """
    try:
        with open(path, mode="rb") as f:
            return pickle.load(f)
    except (pickle.UnpicklingError, OSError, IOError) as e:
        logger.error(f"Failed to load pickle file {path}: {e}")
        return None


class ModelVersionManager:
    """
    Model version manager for managing multiple versions of trained models.

    This manager provides functionality to:
    - Create new model versions with metadata
    - Retrieve specific versions or current version
    - List all versions of a model
    - Delete specific versions
    - Rollback to a previous version

    Directory structure:
        lab_path/
        ├── model/
        │   ├── my_model.pkl              # Current version (backward compatible)
        │   ├── versions.json             # Version index
        │   └── my_model/                 # Historical versions
        │       ├── v20260215_100000.pkl
        │       └── v20260228_143022.pkl
    """

    def __init__(self, model_path: Path) -> None:
        """
        Initialize the model version manager.

        Args:
            model_path: Path to the model directory
        """
        self.model_path: Path = Path(model_path)
        self.versions_file: Path = self.model_path / "versions.json"
        self.versions: dict = self._load_versions()

    def _load_versions(self) -> dict:
        """
        Load version index from JSON file.

        Returns:
            Dictionary containing all version information
        """
        if not self.versions_file.exists():
            return {}

        try:
            with open(self.versions_file, encoding="UTF-8") as f:
                versions: dict = json.load(f)
                return versions
        except (json.JSONDecodeError, OSError, IOError) as e:
            logger.error(f"Failed to load versions file: {e}")
            return {}

    def _save_versions(self) -> None:
        """Save version index to JSON file."""
        try:
            # Ensure parent directory exists
            self.model_path.mkdir(parents=True, exist_ok=True)

            with open(self.versions_file, mode="w+", encoding="UTF-8") as f:
                json.dump(
                    self.versions,
                    f,
                    indent=4,
                    ensure_ascii=False
                )
        except (OSError, IOError) as e:
            logger.error(f"Failed to save versions file: {e}")
            raise

    def _generate_version_id(self) -> str:
        """
        Generate a unique version ID based on timestamp.

        Returns:
            Version ID in format v{YYYYMMDD}_{HHMMSS}
        """
        return f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _get_model_subdir(self, name: str) -> Path:
        """
        Get the directory for storing model version files.

        Args:
            name: Model name

        Returns:
            Path to the model version directory
        """
        subdir: Path = self.model_path / name
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir

    def create_version(
        self,
        name: str,
        version: ModelVersion,
        model: AlphaModel
    ) -> ModelVersion:
        """
        Create a new model version.

        Args:
            name: Model name
            version: ModelVersion instance containing version metadata
            model: AlphaModel instance to be saved

        Returns:
            The created ModelVersion instance

        Raises:
            ValueError: If model name is invalid or version already exists
        """
        if not name:
            raise ValueError("Model name cannot be empty")

        # Generate version ID if not provided
        if not version.version_id:
            version.version_id = self._generate_version_id()

        # Ensure model directory exists
        model_subdir: Path = self._get_model_subdir(name)

        # Save model to version file
        version_file: Path = model_subdir / f"{version.version_id}.pkl"
        try:
            with open(version_file, mode="wb") as f:
                pickle.dump(model, f)
        except (pickle.PicklingError, OSError, IOError) as e:
            logger.error(f"Failed to save model version: {e}")
            raise

        # Also save as current version for backward compatibility
        current_file: Path = self.model_path / f"{name}.pkl"
        try:
            with open(current_file, mode="wb") as f:
                pickle.dump(model, f)
        except (pickle.PicklingError, OSError, IOError) as e:
            logger.error(f"Failed to save current model: {e}")
            # Rollback: delete the version file that was just created
            if version_file.exists():
                version_file.unlink()
            raise

        # Update version index
        if name not in self.versions:
            self.versions[name] = {
                "current_version": version.version_id,
                "versions": []
            }

        # Add version to list
        version_data: dict = version.to_dict()
        version_data["file_path"] = f"{name}/{version.version_id}.pkl"

        self.versions[name]["versions"].append(version_data)
        self.versions[name]["current_version"] = version.version_id

        self._save_versions()

        logger.info(f"Created model version {version.version_id} for {name}")
        return version

    def get_version(self, name: str, version_id: str) -> ModelVersion | None:
        """
        Get a specific model version.

        Args:
            name: Model name
            version_id: Version ID to retrieve

        Returns:
            ModelVersion instance if found, None otherwise
        """
        if name not in self.versions:
            logger.warning(f"Model {name} not found")
            return None

        # Find version in list
        version_data: dict | None = None
        for v in self.versions[name]["versions"]:
            if v["version_id"] == version_id:
                version_data = v
                break

        if not version_data:
            logger.warning(f"Version {version_id} not found for model {name}")
            return None

        # Remove file_path before creating ModelVersion
        version_dict = {k: v for k, v in version_data.items() if k != "file_path"}
        return ModelVersion.from_dict(version_dict)

    def get_current_version(self, name: str) -> ModelVersion | None:
        """
        Get the current version of a model.

        Args:
            name: Model name

        Returns:
            ModelVersion instance if found, None otherwise
        """
        if name not in self.versions:
            logger.warning(f"Model {name} not found")
            return None

        current_version_id: str = self.versions[name].get("current_version")
        if not current_version_id:
            logger.warning(f"No current version for model {name}")
            return None

        return self.get_version(name, current_version_id)

    def list_versions(self, name: str) -> list[ModelVersion]:
        """
        List all versions of a model.

        Args:
            name: Model name

        Returns:
            List of ModelVersion instances, sorted by creation time (newest first)
        """
        if name not in self.versions:
            logger.warning(f"Model {name} not found")
            return []

        versions: list[ModelVersion] = []
        for version_data in self.versions[name]["versions"]:
            # Remove file_path before creating ModelVersion
            version_dict = {k: v for k, v in version_data.items() if k != "file_path"}
            versions.append(ModelVersion.from_dict(version_dict))

        # Sort by creation time (newest first), then by version_id (reverse) for stable sort
        versions.sort(key=lambda v: (v.created_at, v.version_id), reverse=True)

        return versions

    def delete_version(self, name: str, version_id: str) -> bool:
        """
        Delete a specific model version.

        Args:
            name: Model name
            version_id: Version ID to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if name not in self.versions:
            logger.warning(f"Model {name} not found")
            return False

        # Find and remove version from list
        version_data: dict | None = None
        versions_list: list = self.versions[name]["versions"]

        for i, v in enumerate(versions_list):
            if v["version_id"] == version_id:
                version_data = v
                versions_list.pop(i)
                break

        if not version_data:
            logger.warning(f"Version {version_id} not found for model {name}")
            return False

        # Delete model file
        model_subdir: Path = self._get_model_subdir(name)
        version_file: Path = model_subdir / f"{version_id}.pkl"

        if version_file.exists():
            try:
                version_file.unlink()
            except OSError as e:
                logger.error(f"Failed to delete version file {version_file}: {e}")
                # Restore version to the list since file deletion failed
                versions_list.insert(
                    next(i for i, v in enumerate(versions_list) if v["version_id"] > version_id),
                    version_data
                )
                return False

        # Update current version if needed
        if self.versions[name]["current_version"] == version_id:
            if versions_list:
                # Set to most recent version
                versions_list.sort(
                    key=lambda v: v.get("created_at", ""),
                    reverse=True
                )
                self.versions[name]["current_version"] = versions_list[0]["version_id"]
            else:
                # No versions left
                self.versions[name]["current_version"] = ""

        self._save_versions()

        logger.info(f"Deleted version {version_id} of model {name}")
        return True

    def rollback(self, name: str, version_id: str) -> bool:
        """
        Rollback to a specific model version.

        This will:
        1. Load the model from the specified version
        2. Save it as the current version
        3. Update the current version pointer

        Args:
            name: Model name
            version_id: Version ID to rollback to

        Returns:
            True if rollback was successful, False otherwise
        """
        if name not in self.versions:
            logger.warning(f"Model {name} not found")
            return False

        # Verify version exists
        version: ModelVersion | None = self.get_version(name, version_id)
        if not version:
            logger.warning(f"Version {version_id} not found for model {name}")
            return False

        # Load model from version file
        model_subdir: Path = self._get_model_subdir(name)
        version_file: Path = model_subdir / f"{version_id}.pkl"

        if not version_file.exists():
            logger.error(f"Model file not found: {version_file}")
            return False

        model: AlphaModel | None = _load_pickle_file(version_file)
        if model is None:
            logger.error(f"Failed to load model version from {version_file}")
            return False

        # Save as current version
        current_file: Path = self.model_path / f"{name}.pkl"
        try:
            with open(current_file, mode="wb") as f:
                pickle.dump(model, f)
        except (pickle.PicklingError, OSError, IOError) as e:
            logger.error(f"Failed to save current model: {e}")
            return False

        # Update current version pointer
        self.versions[name]["current_version"] = version_id
        self._save_versions()

        logger.info(f"Rolled back model {name} to version {version_id}")
        return True

    def load_model(self, name: str, version_id: str | None = None) -> AlphaModel | None:
        """
        Load a model from the specified version or current version.

        Args:
            name: Model name
            version_id: Version ID to load, None for current version

        Returns:
            AlphaModel instance if found, None otherwise
        """
        # Get version ID
        if version_id is None:
            version: ModelVersion | None = self.get_current_version(name)
            if version:
                version_id = version.version_id
            else:
                # Fallback to loading from current file
                return self._load_current_model(name)

        if version_id:
            # Load from version file
            model_subdir: Path = self._get_model_subdir(name)
            version_file: Path = model_subdir / f"{version_id}.pkl"

            if not version_file.exists():
                logger.error(f"Version file not found: {version_file}")
                return None

            return _load_pickle_file(version_file)

        return self._load_current_model(name)

    def _load_current_model(self, name: str) -> AlphaModel | None:
        """
        Load model from current version file (backward compatibility).

        Args:
            name: Model name

        Returns:
            AlphaModel instance if found, None otherwise
        """
        current_file: Path = self.model_path / f"{name}.pkl"

        if not current_file.exists():
            logger.error(f"Model file not found: {current_file}")
            return None

        return _load_pickle_file(current_file)
