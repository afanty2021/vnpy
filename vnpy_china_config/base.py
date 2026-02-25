"""
配置基类模块

定义配置基类和运行环境枚举。
提供统一的配置加载和保存接口。
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Environment(str, Enum):
    """运行环境枚举

    定义系统运行的不同环境：
    - DEVELOPMENT: 开发环境
    - TESTING: 测试环境
    - PRODUCTION: 生产环境
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    def __str__(self) -> str:
        return self.value


class BaseConfig(BaseModel):
    """配置基类

    所有配置类的基类，提供统一的配置加载和保存功能。
    使用 Pydantic 进行类型验证，确保配置的类型安全。

    Features:
        - 支持从 JSON/YAML 文件加载配置
        - 支持将配置保存为 JSON/YAML 文件
        - 支持字段别名和自动验证
        - 支持嵌套配置模型
        - 枚举类型自动序列化为字符串

    Example:
        ```python
        class MyConfig(BaseConfig):
            name: str = "default"
            value: int = 0

        # 从文件加载
        config = MyConfig.from_file(Path("config.json"))

        # 保存到文件
        config.to_file(Path("output.yaml"))
        ```
    """

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "str_to_lower": False,
    }

    @field_validator("*", mode="before")
    @classmethod
    def _convert_path_to_string(cls, v: Any) -> Any:
        """将 Path 对象转换为字符串"""
        if isinstance(v, Path):
            return str(v)
        return v

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "BaseConfig":
        """从文件加载配置

        根据文件扩展名自动识别格式并加载配置。

        Args:
            config_path: 配置文件路径，支持 .json, .yaml, .yml 格式

        Returns:
            配置对象实例

        Raises:
            ValueError: 不支持的配置文件格式

        Example:
            ```python
            config = GlobalConfig.from_file("config.json")
            config = GlobalConfig.from_file("config.yaml")
            ```
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        suffix = config_path.suffix.lower()

        if suffix == ".json":
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif suffix in [".yaml", ".yml"]:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {suffix}，仅支持 .json, .yaml, .yml")

        return cls(**data)

    def to_file(self, config_path: Union[str, Path], format: Optional[str] = None) -> None:
        """保存配置到文件

        根据文件扩展名自动选择保存格式。

        Args:
            config_path: 配置文件路径
            format: 强制指定格式，可选 "json" 或 "yaml"，默认根据扩展名自动判断

        Example:
            ```python
            config.to_file("config.json")
            config.to_file("config.yaml")
            config.to_file("output.json", format="json")
            ```
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 确定格式
        if format:
            suffix = f".{format}"
        else:
            suffix = config_path.suffix.lower()

        if suffix == ".json":
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
        elif suffix in [".yaml", ".yml"]:
            import yaml

            # 使用 SafeSerializer 自定义处理
            class SafeSerializer:
                @staticmethod
                def represent_str(dumper: Any, data: str) -> Any:
                    """安全表示字符串"""
                    if "\n" in data:
                        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
                    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

            yaml.add_representer(str, SafeSerializer.represent_str)

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.model_dump(mode='json'),
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        else:
            raise ValueError(f"不支持的配置文件格式: {suffix}，仅支持 .json, .yaml, .yml")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            配置字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串

        Returns:
            JSON 格式字符串
        """
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseConfig":
        """从字典创建配置

        Args:
            data: 配置字典

        Returns:
            配置对象实例
        """
        return cls(**data)

    def update(self, **kwargs) -> "BaseConfig":
        """更新配置字段

        Args:
            **kwargs: 要更新的字段和值

        Returns:
            更新后的配置对象

        Example:
            ```python
            config = config.update(name="new_name", value=10)
            ```
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self
