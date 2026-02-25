"""
工具函数模块

提供配置相关的工具函数，包括 JSON 编码器、配置合并和环境变量解析。
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Union


class NumpyEncoder(json.JSONEncoder):
    """NumPy 类型 JSON 编码器

    扩展 JSONEncoder 以支持 NumPy 类型和常用 Python 类型的序列化。

    Supported Types:
        - numpy.integer -> int
        - numpy.floating -> float
        - numpy.ndarray -> list
        - datetime -> ISO format string
        - date -> ISO format string
        - Path -> string

    Example:
        ```python
        import numpy as np

        data = {
            "value": np.int64(42),
            "array": np.array([1, 2, 3]),
            "timestamp": datetime.now()
        }

        json_str = json.dumps(data, cls=NumpyEncoder)
        ```
    """

    def default(self, obj: Any) -> Any:
        """序列化对象

        Args:
            obj: 要序列化的对象

        Returns:
            序列化的值
        """
        # NumPy 类型
        try:
            import numpy as np

            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass

        # 日期时间类型
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()

        # Path 类型
        if isinstance(obj, Path):
            return str(obj)

        # 未知类型，交给父类处理
        return super().default(obj)


def merge_configs(
    base_config: Dict[str, Any],
    override_config: Dict[str, Any],
) -> Dict[str, Any]:
    """合并配置

    深度合并两个配置字典，override_config 的值会覆盖 base_config 的值。
    如果两个配置中都有字典类型的值，会递归合并。

    Args:
        base_config: 基础配置
        override_config: 覆盖配置（优先级更高）

    Returns:
        合并后的配置字典

    Example:
        ```python
        base = {
            "database": {"host": "localhost", "port": 3306},
            "logging": {"level": "INFO"}
        }

        override = {
            "database": {"port": 3307},
            "cache": {"enabled": True}
        }

        result = merge_configs(base, override)
        # result = {
        #     "database": {"host": "localhost", "port": 3307},
        #     "logging": {"level": "INFO"},
        #     "cache": {"enabled": True}
        # }
        ```
    """
    result = base_config.copy()

    for key, value in override_config.items():
        if key in result:
            # 如果两者都是字典，递归合并
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_configs(result[key], value)
            else:
                # 否则直接覆盖
                result[key] = value
        else:
            # 新键直接添加
            result[key] = value

    return result


def resolve_env_variables(
    config: Union[Dict[str, Any], str],
) -> Union[Dict[str, Any], str]:
    """解析环境变量引用

    递归遍历配置字典，将 ${VAR_NAME} 格式的环境变量引用替换为实际值。

    Args:
        config: 配置字典或字符串

    Returns:
        解析后的配置

    Example:
        ```python
        os.environ["MYSQL_HOST"] = "localhost"

        config = {
            "host": "${MYSQL_HOST}",
            "port": 3306
        }

        result = resolve_env_variables(config)
        # result = {"host": "localhost", "port": 3306}
        ```
    """
    if isinstance(config, str):
        # 检查是否为环境变量引用格式 ${VAR_NAME}
        if config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            # 支持默认值，如 ${VAR_NAME:-default_value}
            if ":-" in env_var:
                var_name, default_value = env_var.split(":-", 1)
                return os.environ.get(var_name, default_value)
            return os.environ.get(env_var, "")
        return config

    if isinstance(config, dict):
        result: Dict[str, Any] = {}
        for key, value in config.items():
            result[key] = resolve_env_variables(value)
        return result

    if isinstance(config, list):
        return [resolve_env_variables(item) for item in config]

    return config


def load_config_with_env(
    config_path: Union[str, Path],
    resolve_env: bool = True,
) -> Dict[str, Any]:
    """加载配置并解析环境变量

    加载配置文件（JSON 或 YAML），并可选地解析其中的环境变量引用。

    Args:
        config_path: 配置文件路径
        resolve_env: 是否解析环境变量

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 不支持的配置文件格式
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    suffix = config_path.suffix.lower()

    if suffix == ".json":
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    elif suffix in [".yaml", ".yml"]:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        raise ValueError(f"不支持的配置文件格式: {suffix}")

    if resolve_env:
        config = resolve_env_variables(config)

    return config


def save_config_with_format(
    config: Dict[str, Any],
    config_path: Union[str, Path],
    format: str = "yaml",
) -> None:
    """保存配置到文件

    将配置字典保存为 JSON 或 YAML 格式。

    Args:
        config: 配置字典
        config_path: 配置文件路径
        format: 保存格式，"json" 或 "yaml"

    Raises:
        ValueError: 不支持的格式
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
    elif format == "yaml":
        import yaml

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
    else:
        raise ValueError(f"不支持的格式: {format}，仅支持 json 和 yaml")


def validate_config_schema(
    config: Dict[str, Any],
    required_keys: list[str],
) -> Dict[str, Any]:
    """验证配置 schema

    检查配置字典是否包含所有必需的键。

    Args:
        config: 配置字典
        required_keys: 必需的键列表

    Returns:
        验证结果字典

    Example:
        ```python
        config = {"host": "localhost", "port": 3306}
        required = ["host", "port", "database"]

        result = validate_config_schema(config, required)
        # result = {
        #     "valid": False,
        #     "errors": ["缺少必需键: database"]
        # }
        ```
    """
    errors: list[str] = []

    for key in required_keys:
        if key not in config:
            errors.append(f"缺少必需键: {key}")
        elif config[key] is None or (isinstance(config[key], str) and not config[key].strip()):
            errors.append(f"必需键 '{key}' 不能为空")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
