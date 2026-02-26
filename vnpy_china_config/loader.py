"""
配置加载器模块

提供配置管理器和配置文件的加载、保存、热更新功能。
"""

import os
import threading
from pathlib import Path
from typing import Dict, Optional, Type, TypeVar, Union

from .base import BaseConfig, Environment

T = TypeVar("T", bound=BaseConfig)


class ConfigManager:
    """配置管理器（单例模式）

    统一管理系统所有配置，支持配置加载、保存、热更新和环境切换。
    采用线程安全的单例模式确保全局唯一实例。

    Attributes:
        environment: 当前运行环境
        config_path: 配置文件根目录

    Features:
        - 单例模式，全局唯一实例
        - 线程安全的配置访问
        - 支持 JSON/YAML 格式配置文件
        - 支持配置热更新
        - 支持环境自动切换

    Example:
        ```python
        # 获取配置管理器实例
        manager = ConfigManager()

        # 设置运行环境
        manager.set_environment(Environment.PRODUCTION)

        # 加载全局配置
        global_config = manager.load_global_config()

        # 加载模块配置
        data_config = manager.load_module_config(
            "data",
            DataModuleConfig
        )

        # 更新配置
        manager.update_config("global", logging_level="DEBUG")

        # 保存配置
        manager.save_config("global")

        # 热更新
        manager.reload_config("global")
        ```
    """

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ConfigManager":
        """线程安全的单例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """初始化配置管理器"""
        if not self._initialized:
            self._configs: Dict[str, BaseConfig] = {}
            self._config_path: Path = self._find_config_path()
            self._environment: Environment = self._detect_environment()
            self._initialized = True

    def _find_config_path(self) -> Path:
        """查找配置文件路径

        按优先级查找：
        1. 当前目录下的 .vntrader_china/config
        2. 向上递归查找项目根目录
        3. 用户主目录下的 .vntrader_china/config（最后才使用）

        Returns:
            配置文件路径
        """
        from pathlib import Path

        # 尝试当前目录
        config_path = Path(".vntrader_china/config")
        if config_path.exists():
            return config_path

        # 尝试向上查找项目根目录（包含 .vntrader_china 的目录）
        # 优先使用项目目录下的配置，而不是用户主目录
        current_path = Path.cwd()
        original_path = current_path
        project_config_path = None

        for _ in range(10):  # 最多向上查找10层
            check_path = current_path / ".vntrader_china/config"
            if check_path.exists():
                # 检查是否有配置文件（而不是空目录）
                if (check_path / "global_development.yaml").exists():
                    project_config_path = check_path
                    break
                # 或者有 global_production.yaml
                if (check_path / "global_production.yaml").exists():
                    project_config_path = check_path
                    break
                # 或者有 global_testing.yaml
                if (check_path / "global_testing.yaml").exists():
                    project_config_path = check_path
                    break

            parent = current_path.parent
            if parent == current_path:  # 到达根目录
                break
            current_path = parent

        # 如果找到项目配置，优先使用
        if project_config_path:
            return project_config_path

        # 使用用户主目录（作为最后的fallback）
        home_config = Path.home() / ".vntrader_china/config"
        if home_config.exists():
            return home_config

        # 默认使用当前目录（稍后会创建）
        return Path(".vntrader_china/config")

    def _detect_environment(self) -> Environment:
        """自动检测运行环境

        优先级：
        1. 环境变量 VNPY_ENV
        2. 根据配置文件路径判断

        Returns:
            运行环境枚举
        """
        # 优先使用环境变量
        env_value = os.getenv("VNPY_ENV", "").lower()
        if env_value:
            for env in Environment:
                if env.value == env_value:
                    return env

        # 默认开发环境
        return Environment.DEVELOPMENT

    @property
    def environment(self) -> Environment:
        """获取当前运行环境"""
        return self._environment

    @property
    def config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path

    def set_environment(self, env: Union[Environment, str]) -> None:
        """设置运行环境

        Args:
            env: 运行环境枚举或字符串
        """
        if isinstance(env, str):
            env = Environment(env)
        self._environment = env

    def set_config_path(self, path: Union[str, Path]) -> None:
        """设置配置文件根目录

        Args:
            path: 配置文件根目录路径
        """
        self._config_path = Path(path)
        self._config_path.mkdir(parents=True, exist_ok=True)

    def load_global_config(self, force_reload: bool = False) -> BaseConfig:
        """加载全局配置

        Args:
            force_reload: 是否强制重新加载

        Returns:
            全局配置对象
        """
        if not force_reload and "global" in self._configs:
            return self._configs["global"]

        from .global_config import GlobalConfig

        config_file = self._config_path / f"global_{self._environment.value}.yaml"

        if config_file.exists():
            config = GlobalConfig.from_file(config_file)
        else:
            # 创建默认配置并保存
            config = GlobalConfig()
            config.environment = self._environment
            config.to_file(config_file)

        self._configs["global"] = config
        return config

    def load_module_config(
        self,
        module_name: str,
        config_class: Type[T],
        filename: Optional[str] = None,
        force_reload: bool = False,
    ) -> T:
        """加载模块配置

        Args:
            module_name: 模块名称
            config_class: 配置类类型
            filename: 配置文件名，默认使用 {module_name}_{environment}.yaml
            force_reload: 是否强制重新加载

        Returns:
            模块配置对象
        """
        if not force_reload and module_name in self._configs:
            return self._configs[module_name]  # type: ignore

        if filename is None:
            filename = f"{module_name}_{self._environment.value}.yaml"

        config_file = self._config_path / filename

        if config_file.exists():
            config = config_class.from_file(config_file)
        else:
            # 创建默认配置并保存
            config = config_class()
            config.to_file(config_file)

        self._configs[module_name] = config
        return config

    def get_config(self, name: str) -> Optional[BaseConfig]:
        """获取已加载的配置

        Args:
            name: 配置名称（global 或模块名）

        Returns:
            配置对象，不存在则返回 None
        """
        return self._configs.get(name)

    def reload_config(self, name: str) -> BaseConfig:
        """重新加载配置（热更新）

        Args:
            name: 配置名称

        Returns:
            重新加载后的配置对象

        Raises:
            ValueError: 配置不存在
        """
        if name == "global":
            return self.load_global_config(force_reload=True)

        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"配置不存在: {name}")

        # 获取配置类类型
        config_class = type(config)
        return self.load_module_config(name, config_class, force_reload=True)

    def save_config(self, name: str) -> None:
        """保存配置到文件

        Args:
            name: 配置名称

        Raises:
            ValueError: 配置不存在
        """
        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"配置不存在: {name}")

        if name == "global":
            filename = f"global_{self._environment.value}.yaml"
        else:
            filename = f"{name}_{self._environment.value}.yaml"

        config_file = self._config_path / filename
        config.to_file(config_file)

    def update_config(self, name: str, **kwargs) -> None:
        """更新配置字段

        Args:
            name: 配置名称
            **kwargs: 要更新的字段和值

        Raises:
            ValueError: 配置不存在或字段无效
        """
        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"配置不存在: {name}")

        for key, value in kwargs.items():
            if not hasattr(config, key):
                raise ValueError(f"配置 {name} 没有字段: {key}")
            setattr(config, key, value)

    def get_all_configs(self) -> Dict[str, BaseConfig]:
        """获取所有已加载的配置

        Returns:
            配置字典
        """
        return self._configs.copy()

    def clear_cache(self) -> None:
        """清除配置缓存"""
        self._configs.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        with cls._lock:
            cls._instance = None
