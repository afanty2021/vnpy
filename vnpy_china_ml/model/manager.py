"""A股机器学习模型管理器

负责管理训练好的模型，提供模型的加载、保存、查询和删除功能。
"""

import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .china_model import ChinaAlphaModel
from ..utils.types import ModelType, PredictionResult


@dataclass
class ModelMetadata:
    """模型元数据

    Attributes:
        model_id: 模型唯一标识
        model_name: 模型显示名称
        model_type: 模型类型
        is_trained: 是否已训练
        training_date: 训练时间
        accuracy: 准确率（如果是分类模型）
        feature_count: 特征数量
        status: 模型状态 (待部署/已部署)
        file_path: 模型文件路径
        description: 模型描述
        version: 语义化版本号
        parent_model_id: 父模型ID
        version_tag: 版本标签（production/staging/development）
        changelog: 变更日志
    """
    model_id: str
    model_name: str
    model_type: ModelType
    is_trained: bool
    training_date: Optional[datetime]
    accuracy: float = 0.0
    feature_count: int = 0
    status: str = "待部署"
    file_path: Optional[str] = None
    description: str = ""
    version: str = "1.0.0"
    parent_model_id: Optional[str] = None
    version_tag: str = "development"
    changelog: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "is_trained": self.is_trained,
            "training_date": self.training_date.strftime("%Y-%m-%d %H:%M:%S") if self.training_date else "",
            "accuracy": self.accuracy,
            "feature_count": self.feature_count,
            "status": self.status,
            "file_path": self.file_path,
            "description": self.description,
            "version": self.version,
            "parent_model_id": self.parent_model_id,
            "version_tag": self.version_tag,
            "changelog": self.changelog
        }


class ModelManager:
    """模型管理器

    负责管理所有训练好的模型，提供模型的加载、保存、查询和删除功能。
    同时管理模型的元数据信息。
    """

    def __init__(self, model_dir: str = "models"):
        """初始化模型管理器

        Args:
            model_dir: 模型存储目录
        """
        self.model_dir: Path = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 存储模型元数据
        self._models: Dict[str, ModelMetadata] = {}

        # 加载已保存的元数据
        self._load_metadata()

    def _load_metadata(self) -> None:
        """从文件加载模型元数据（向后兼容旧版本）"""
        metadata_file = self.model_dir / "metadata.pkl"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'rb') as f:
                    loaded_models = pickle.load(f)

                # 确保向后兼容：为旧元数据添加新字段
                for model_id, metadata in loaded_models.items():
                    # 检查是否有新增字段，没有则添加默认值
                    if not hasattr(metadata, 'version'):
                        metadata.version = "1.0.0"
                    if not hasattr(metadata, 'parent_model_id'):
                        metadata.parent_model_id = None
                    if not hasattr(metadata, 'version_tag'):
                        metadata.version_tag = "development"
                    if not hasattr(metadata, 'changelog'):
                        metadata.changelog = ""

                self._models = loaded_models
            except Exception as e:
                print(f"加载模型元数据失败: {e}")
                self._models = {}

    def _save_metadata(self) -> None:
        """保存模型元数据到文件"""
        metadata_file = self.model_dir / "metadata.pkl"
        try:
            with open(metadata_file, 'wb') as f:
                pickle.dump(self._models, f)
        except Exception as e:
            print(f"保存模型元数据失败: {e}")

    def register_model(
        self,
        model_name: str,
        model: ChinaAlphaModel,
        accuracy: float = 0.0,
        description: str = ""
    ) -> str:
        """注册新模型

        Args:
            model_name: 模型名称
            model: 模型实例
            accuracy: 准确率
            description: 模型描述

        Returns:
            模型ID
        """
        # 生成模型ID
        model_id = f"{model.model_type.value}_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 保存模型文件
        file_path = self.model_dir / f"{model_id}.pkl"
        model.save_model(str(file_path))

        # 创建元数据
        metadata = ModelMetadata(
            model_id=model_id,
            model_name=model_name,
            model_type=model.model_type,
            is_trained=model.is_trained,
            training_date=model.training_date,
            accuracy=accuracy,
            feature_count=len(model.feature_names),
            status="待部署",
            file_path=str(file_path),
            description=description
        )

        self._models[model_id] = metadata
        self._save_metadata()

        return model_id

    def load_model(self, model_id: str) -> Optional[ChinaAlphaModel]:
        """加载模型

        Args:
            model_id: 模型ID

        Returns:
            模型实例，如果加载失败返回None
        """
        if model_id not in self._models:
            return None

        metadata = self._models[model_id]
        if not metadata.file_path or not os.path.exists(metadata.file_path):
            return None

        try:
            model = ChinaAlphaModel(model_type=metadata.model_type)
            if model.load_model(metadata.file_path):
                return model
        except Exception as e:
            print(f"加载模型失败: {e}")

        return None

    def get_model(self, model_id: str) -> Optional[ChinaAlphaModel]:
        """获取模型（带缓存）

        Args:
            model_id: 模型ID

        Returns:
            模型实例
        """
        return self.load_model(model_id)

    def delete_model(self, model_id: str) -> bool:
        """删除模型

        Args:
            model_id: 模型ID

        Returns:
            是否删除成功
        """
        if model_id not in self._models:
            return False

        metadata = self._models[model_id]

        # 删除模型文件
        if metadata.file_path and os.path.exists(metadata.file_path):
            try:
                os.remove(metadata.file_path)
            except Exception as e:
                print(f"删除模型文件失败: {e}")

        # 删除元数据
        del self._models[model_id]
        self._save_metadata()

        return True

    def get_all_models(self) -> List[ModelMetadata]:
        """获取所有模型

        Returns:
            模型元数据列表
        """
        return list(self._models.values())

    def get_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """获取模型元数据

        Args:
            model_id: 模型ID

        Returns:
            模型元数据
        """
        return self._models.get(model_id)

    def update_model_status(self, model_id: str, status: str) -> bool:
        """更新模型状态

        Args:
            model_id: 模型ID
            status: 新状态

        Returns:
            是否更新成功
        """
        if model_id not in self._models:
            return False

        self._models[model_id].status = status
        self._save_metadata()

        return True

    def get_models_by_type(self, model_type: ModelType) -> List[ModelMetadata]:
        """根据类型获取模型

        Args:
            model_type: 模型类型

        Returns:
            模型元数据列表
        """
        return [m for m in self._models.values() if m.model_type == model_type]

    def get_trained_models(self) -> List[ModelMetadata]:
        """获取所有已训练的模型

        Returns:
            已训练模型的元数据列表
        """
        return [m for m in self._models.values() if m.is_trained]

    def has_preset_models(self) -> bool:
        """检查是否有预置模型

        Returns:
            是否存在预置模型
        """
        return any(m.description.startswith("[预置]") for m in self._models.values())

    def create_preset_models(self) -> int:
        """创建预置模型（用于首次使用或演示）

        使用模拟数据创建简单预训练模型，让用户可以快速体验功能。

        Returns:
            创建的模型数量
        """
        import numpy as np

        created_count = 0
        preset_configs = [
            {
                "name": "random_forest_preset",
                "type": ModelType.RANDOM_FOREST,
                "description": "[预置] 随机森林模型 - 使用模拟数据训练",
                "accuracy": 0.65
            },
            {
                "name": "lightgbm_preset",
                "type": ModelType.LIGHTGBM,
                "description": "[预置] LightGBM模型 - 使用模拟数据训练",
                "accuracy": 0.68
            },
            {
                "name": "lasso_preset",
                "type": ModelType.LASSO,
                "description": "[预置] Lasso回归模型 - 使用模拟数据训练",
                "accuracy": 0.62
            }
        ]

        for config in preset_configs:
            # 检查是否已存在同名预置模型
            existing = [m for m in self._models.values()
                       if m.model_name == config["name"] and m.description.startswith("[预置]")]
            if existing:
                continue

            try:
                # 创建模型
                model = ChinaAlphaModel(model_type=config["type"])

                # 生成模拟训练数据
                n_samples = 1000
                n_features = 20
                X = np.random.randn(n_samples, n_features)
                y = np.random.randn(n_samples) * 0.02

                # 训练模型
                feature_names = [f"feature_{i}" for i in range(n_features)]
                model.train(X, y, feature_names=feature_names)

                # 注册模型
                model_id = self.register_model(
                    model_name=config["name"],
                    model=model,
                    accuracy=config["accuracy"],
                    description=config["description"]
                )

                if model_id:
                    created_count += 1

            except Exception as e:
                print(f"创建预置模型失败 {config['name']}: {e}")

        return created_count

    def clear_all(self) -> None:
        """清空所有模型"""
        # 删除所有模型文件
        for metadata in self._models.values():
            if metadata.file_path and os.path.exists(metadata.file_path):
                try:
                    os.remove(metadata.file_path)
                except Exception as e:
                    print(f"删除模型文件失败: {e}")

        self._models.clear()
        self._save_metadata()


__all__ = ["ModelManager", "ModelMetadata"]
