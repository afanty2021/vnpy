"""模型版本管理器

提供模型版本管理功能，包括版本创建、历史查询、版本回滚等。
"""

import os
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .manager import ModelManager, ModelMetadata
from .ab_test import ModelVersionInfo


class ModelVersionManager:
    """模型版本管理器

    负责管理模型的版本历史，提供版本追踪、回滚和对比功能。
    """

    def __init__(self, model_manager: ModelManager, model_dir: str = "models"):
        """初始化版本管理器

        Args:
            model_manager: 模型管理器实例
            model_dir: 模型存储目录
        """
        self.model_manager = model_manager
        self.model_dir: Path = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 版本树结构: parent_id -> [child_ids]
        self.version_tree: Dict[str, List[str]] = {}

        # 模型名称到版本列表的映射
        self.model_versions: Dict[str, List[str]] = {}

        # 加载版本树数据
        self._load_version_tree()

    def _load_version_tree(self) -> None:
        """从文件加载版本树"""
        version_tree_file = self.model_dir / "version_tree.pkl"
        if version_tree_file.exists():
            try:
                with open(version_tree_file, 'rb') as f:
                    data = pickle.load(f)
                    self.version_tree = data.get("version_tree", {})
                    self.model_versions = data.get("model_versions", {})
            except Exception as e:
                print(f"加载版本树失败: {e}")
                self.version_tree = {}
                self.model_versions = {}

    def _save_version_tree(self) -> None:
        """保存版本树到文件"""
        version_tree_file = self.model_dir / "version_tree.pkl"
        try:
            with open(version_tree_file, 'wb') as f:
                pickle.dump({
                    "version_tree": self.version_tree,
                    "model_versions": self.model_versions
                }, f)
        except Exception as e:
            print(f"保存版本树失败: {e}")

    def create_version(
        self,
        model_name: str,
        version: str,
        parent_id: Optional[str] = None,
        tag: str = "development",
        changelog: str = ""
    ) -> Optional[str]:
        """创建新版本

        Args:
            model_name: 模型名称
            version: 版本号（语义化版本，如 "1.0.0"）
            parent_id: 父模型ID（可选）
            tag: 版本标签
            changelog: 变更日志

        Returns:
            新版本模型ID，如果创建失败返回None
        """
        # 验证父模型存在
        if parent_id and parent_id not in self.model_manager._models:
            print(f"父模型不存在: {parent_id}")
            return None

        # 获取现有模型元数据
        parent_metadata = None
        if parent_id:
            parent_metadata = self.model_manager.get_model_metadata(parent_id)
            if parent_metadata:
                model_name = parent_metadata.model_name

        # 生成新版本ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_id = f"{model_name}_v{version.replace('.', '_')}_{timestamp}"

        # 如果没有父模型，从现有模型中查找同名模型的最新版本
        if not parent_id:
            if model_name in self.model_versions:
                versions = self.model_versions[model_name]
                if versions:
                    parent_id = versions[-1]  # 使用最新版本作为父版本
                    parent_metadata = self.model_manager.get_model_metadata(parent_id)
            else:
                # 第一次创建版本，从model_manager中查找同名模型
                for mid, metadata in self.model_manager._models.items():
                    if metadata.model_name == model_name:
                        parent_id = mid
                        parent_metadata = metadata
                        break

        # 复制父模型文件
        if parent_metadata and parent_metadata.file_path:
            try:
                import shutil
                old_file = Path(parent_metadata.file_path)
                new_file = self.model_dir / f"{model_id}.pkl"
                shutil.copy2(old_file, new_file)

                # 创建新元数据
                version_info = ModelVersionInfo(
                    version=version,
                    parent_model_id=parent_id,
                    version_tag=tag,
                    changelog=changelog
                )

                # 更新元数据
                new_metadata = ModelMetadata(
                    model_id=model_id,
                    model_name=model_name,
                    model_type=parent_metadata.model_type,
                    is_trained=parent_metadata.is_trained,
                    training_date=parent_metadata.training_date,
                    accuracy=parent_metadata.accuracy,
                    feature_count=parent_metadata.feature_count,
                    status=parent_metadata.status,
                    file_path=str(new_file),
                    description=changelog or parent_metadata.description
                )

                # 添加到模型管理器
                self.model_manager._models[model_id] = new_metadata
                self.model_manager._save_metadata()

                # 更新版本树
                if parent_id:
                    if parent_id not in self.version_tree:
                        self.version_tree[parent_id] = []
                    self.version_tree[parent_id].append(model_id)

                # 更新模型版本列表
                if model_name not in self.model_versions:
                    self.model_versions[model_name] = []
                self.model_versions[model_name].append(model_id)

                # 保存版本树
                self._save_version_tree()

                # 保存版本信息
                self._save_version_info(model_id, version_info)

                return model_id

            except Exception as e:
                print(f"创建版本失败: {e}")
                return None

        print(f"无法创建版本：未找到父模型")
        return None

    def _get_version_info_file(self, model_id: str) -> Path:
        """获取版本信息文件路径"""
        # 使用模型ID的哈希作为文件名，避免文件名过长
        hash_id = hashlib.md5(model_id.encode()).hexdigest()[:8]
        return self.model_dir / f"version_{hash_id}.pkl"

    def _save_version_info(self, model_id: str, version_info: ModelVersionInfo) -> None:
        """保存版本信息"""
        info_file = self._get_version_info_file(model_id)
        try:
            with open(info_file, 'wb') as f:
                pickle.dump(version_info, f)
        except Exception as e:
            print(f"保存版本信息失败: {e}")

    def _load_version_info(self, model_id: str) -> Optional[ModelVersionInfo]:
        """加载版本信息"""
        info_file = self._get_version_info_file(model_id)
        if info_file.exists():
            try:
                with open(info_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"加载版本信息失败: {e}")
        return None

    def get_version_history(self, model_name: str) -> List[ModelMetadata]:
        """获取模型版本历史

        Args:
            model_name: 模型名称

        Returns:
            版本历史列表（按时间排序）
        """
        if model_name not in self.model_versions:
            return []

        versions = []
        for model_id in self.model_versions[model_name]:
            metadata = self.model_manager.get_model_metadata(model_id)
            if metadata:
                versions.append(metadata)

        # 按训练时间排序
        versions.sort(key=lambda m: m.training_date or datetime.min, reverse=True)
        return versions

    def get_version_tree(self, model_name: str) -> List[Dict]:
        """获取模型版本树

        Args:
            model_name: 模型名称

        Returns:
            版本树列表（包含父子关系）
        """
        if model_name not in self.model_versions:
            return []

        tree = []
        for model_id in self.model_versions[model_name]:
            version_info = self._load_version_info(model_id)
            metadata = self.model_manager.get_model_metadata(model_id)

            if metadata:
                tree.append({
                    "model_id": model_id,
                    "version": version_info.version if version_info else "1.0.0",
                    "parent_id": version_info.parent_model_id if version_info else None,
                    "tag": version_info.version_tag if version_info else "development",
                    "changelog": version_info.changelog if version_info else "",
                    "created_at": version_info.created_at if version_info else metadata.training_date,
                    "is_production": version_info.is_production if version_info else False,
                    "accuracy": metadata.accuracy,
                    "training_date": metadata.training_date
                })

        # 按创建时间排序
        tree.sort(key=lambda x: x["created_at"] or datetime.min)
        return tree

    def rollback_to_version(self, model_id: str) -> bool:
        """回滚到指定版本

        Args:
            model_id: 目标版本模型ID

        Returns:
            是否回滚成功
        """
        # 检查目标模型存在
        metadata = self.model_manager.get_model_metadata(model_id)
        if not metadata:
            print(f"目标模型不存在: {model_id}")
            return False

        try:
            # 创建新版本作为回滚版本
            version_info = self._load_version_info(model_id)
            current_version = version_info.version if version_info else "1.0.0"

            # 解析版本号并递增补丁版本
            parts = current_version.split(".")
            if len(parts) == 3:
                patch = int(parts[2]) + 1
                new_version = f"{parts[0]}.{parts[1]}.{patch}"
            else:
                new_version = f"{current_version}.1"

            # 创建回滚版本
            new_id = self.create_version(
                model_name=metadata.model_name,
                version=new_version,
                parent_id=model_id,
                tag=version_info.version_tag if version_info else "development",
                changelog=f"回滚到版本 {current_version}"
            )

            return new_id is not None

        except Exception as e:
            print(f"回滚失败: {e}")
            return False

    def compare_versions(self, model_id_1: str, model_id_2: str) -> Dict:
        """对比两个版本

        Args:
            model_id_1: 模型1 ID
            model_id_2: 模型2 ID

        Returns:
            对比结果字典
        """
        metadata_1 = self.model_manager.get_model_metadata(model_id_1)
        metadata_2 = self.model_manager.get_model_metadata(model_id_2)

        if not metadata_1 or not metadata_2:
            return {"error": "模型不存在"}

        version_info_1 = self._load_version_info(model_id_1)
        version_info_2 = self._load_version_info(model_id_2)

        return {
            "model_1": {
                "model_id": model_id_1,
                "version": version_info_1.version if version_info_1 else "1.0.0",
                "accuracy": metadata_1.accuracy,
                "feature_count": metadata_1.feature_count,
                "training_date": metadata_1.training_date,
                "tag": version_info_1.version_tag if version_info_1 else "development"
            },
            "model_2": {
                "model_id": model_id_2,
                "version": version_info_2.version if version_info_2 else "1.0.0",
                "accuracy": metadata_2.accuracy,
                "feature_count": metadata_2.feature_count,
                "training_date": metadata_2.training_date,
                "tag": version_info_2.version_tag if version_info_2 else "development"
            },
            "differences": {
                "accuracy": metadata_1.accuracy - metadata_2.accuracy,
                "feature_count": metadata_1.feature_count - metadata_2.feature_count,
                "days_diff": (
                    (metadata_1.training_date - metadata_2.training_date).days
                    if metadata_1.training_date and metadata_2.training_date
                    else None
                )
            }
        }

    def tag_version(self, model_id: str, tag: str) -> bool:
        """为版本打标签

        Args:
            model_id: 模型ID
            tag: 标签

        Returns:
            是否打标签成功
        """
        if model_id not in self.model_manager._models:
            return False

        version_info = self._load_version_info(model_id)
        if version_info:
            version_info.version_tag = tag
            version_info.is_production = (tag == "production")
            self._save_version_info(model_id, version_info)
            return True

        # 创建新的版本信息
        new_version_info = ModelVersionInfo(version_tag=tag)
        self._save_version_info(model_id, new_version_info)
        return True

    def get_production_version(self, model_name: str) -> Optional[ModelMetadata]:
        """获取生产版本

        Args:
            model_name: 模型名称

        Returns:
            生产版本的元数据
        """
        if model_name not in self.model_versions:
            return None

        for model_id in reversed(self.model_versions[model_name]):
            version_info = self._load_version_info(model_id)
            if version_info and version_info.is_production:
                return self.model_manager.get_model_metadata(model_id)

        return None

    def set_production_version(self, model_id: str) -> bool:
        """设置生产版本

        Args:
            model_id: 模型ID

        Returns:
            是否设置成功
        """
        metadata = self.model_manager.get_model_metadata(model_id)
        if not metadata:
            return False

        # 先取消其他版本的生产标记
        model_name = metadata.model_name
        if model_name in self.model_versions:
            for other_id in self.model_versions[model_name]:
                version_info = self._load_version_info(other_id)
                if version_info and version_info.is_production:
                    version_info.is_production = False
                    version_info.version_tag = "staging"
                    self._save_version_info(other_id, version_info)

        # 设置新生产版本
        return self.tag_version(model_id, "production")

    def get_all_version_tags(self) -> Dict[str, List[str]]:
        """获取所有版本标签

        Returns:
            标签到模型ID列表的映射
        """
        tags = {"production": [], "staging": [], "development": []}

        for model_name, model_ids in self.model_versions.items():
            for model_id in model_ids:
                version_info = self._load_version_info(model_id)
                if version_info:
                    tag = version_info.version_tag
                    if tag in tags:
                        tags[tag].append(model_id)

        return tags

    def delete_version(self, model_id: str) -> bool:
        """删除版本（不影响父版本）

        Args:
            model_id: 模型ID

        Returns:
            是否删除成功
        """
        # 检查是否有子版本
        if model_id in self.version_tree and self.version_tree[model_id]:
            print(f"无法删除版本：存在子版本")
            return False

        # 从版本树中移除
        for parent_id in list(self.version_tree.keys()):
            if model_id in self.version_tree[parent_id]:
                self.version_tree[parent_id].remove(model_id)

        # 从模型版本列表中移除
        for model_name in list(self.model_versions.keys()):
            if model_id in self.model_versions[model_name]:
                self.model_versions[model_name].remove(model_id)
                if not self.model_versions[model_name]:
                    del self.model_versions[model_name]

        # 删除版本信息文件
        info_file = self._get_version_info_file(model_id)
        if info_file.exists():
            try:
                info_file.unlink()
            except Exception as e:
                print(f"删除版本信息文件失败: {e}")

        # 删除模型
        result = self.model_manager.delete_model(model_id)

        if result:
            self._save_version_tree()

        return result


__all__ = ["ModelVersionManager"]
