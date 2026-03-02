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

# 项目标识文件（用于验证是否是有效的vnpy_china项目）
PROJECT_INDICATORS = [
    "setup.py",           # Python项目标准文件
    "setup.cfg",          # 另一种项目配置
    "pyproject.toml",     # 现代Python项目文件
    "requirements.txt",   # 依赖文件
    ".vntrader_china",    # vnpy_china配置目录本身
    "vnpy",               # vnpy核心模块（如果是子目录）
    "CLAUDE.md",          # AI项目文档
    "README.md",          # 项目说明文档
]


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
            self._project_root: Path = self._detect_project_root()
            self._initialized = True

    def _is_valid_project_directory(self, dir_path: Path) -> bool:
        """验证是否是有效的项目目录

        检查目录中是否包含项目标识文件。

        Args:
            dir_path: 待验证的目录路径

        Returns:
            bool: True表示是有效的项目目录
        """
        # 首先检查目录是否存在
        if not dir_path.exists():
            return False

        if not dir_path.is_dir():
            return False

        # 检查是否有任何项目标识文件
        for indicator in PROJECT_INDICATORS:
            if (dir_path / indicator).exists():
                return True

        # 检查是否有vnpy_china相关模块
        try:
            for child in dir_path.iterdir():
                if child.is_dir() and child.name.startswith("vnpy_china"):
                    return True
        except (PermissionError, FileNotFoundError):
            # 如果没有权限访问或目录在检查时被删除
            return False

        return False

    def _has_config_files(self, config_path: Path) -> bool:
        """检查配置目录是否有配置文件

        Args:
            config_path: 配置目录路径

        Returns:
            bool: True表示目录中有配置文件
        """
        if not config_path.is_dir():
            return False

        # 检查是否有任何YAML配置文件
        for yaml_file in config_path.glob("*.yaml"):
            if yaml_file.is_file():
                return True

        return False

    def _find_config_path(self) -> Path:
        """查找配置文件路径

        按优先级查找：
        1. 当前目录下的 .vntrader_china/config
        2. 向上递归查找项目根目录（带项目标识验证）
        3. 用户主目录下的 .vntrader_china/config（最后才使用）

        Returns:
            配置文件路径
        """
        current_path = Path.cwd()

        # 1. 尝试当前目录
        config_path = current_path / ".vntrader_china/config"
        if config_path.exists() and self._has_config_files(config_path):
            return config_path

        # 2. 向上查找项目根目录（带项目标识验证）
        project_config_path = None
        search_path = current_path

        for _ in range(10):  # 最多向上查找10层
            check_path = search_path / ".vntrader_china/config"

            if check_path.exists() and self._has_config_files(check_path):
                # 验证这是否是有效的项目目录
                if self._is_valid_project_directory(search_path):
                    project_config_path = check_path
                    break
                else:
                    # 跳过非项目目录的配置
                    pass

            parent = search_path.parent
            if parent == search_path:  # 到达根目录
                break
            search_path = parent

        # 如果找到项目配置，优先使用
        if project_config_path:
            return project_config_path

        # 3. 使用用户主目录（作为最后的fallback）
        home_config = Path.home() / ".vntrader_china/config"
        if home_config.exists() and self._has_config_files(home_config):
            return home_config

        # 默认使用当前目录（稍后会创建）
        return current_path / ".vntrader_china/config"

    def _detect_project_root(self) -> Path:
        """检测项目根目录

        向上查找包含项目标识的目录。

        Returns:
            项目根目录路径
        """
        search_path = Path.cwd()

        for _ in range(10):
            if self._is_valid_project_directory(search_path):
                return search_path

            parent = search_path.parent
            if parent == search_path:  # 到达根目录
                break
            search_path = parent

        # 默认返回当前目录
        return Path.cwd()

    def get_config_info(self) -> Dict[str, str]:
        """获取配置信息（用于调试）

        Returns:
            配置信息字典
        """
        return {
            "environment": self._environment.value,
            "config_path": str(self._config_path),
            "project_root": str(self._detect_project_root()),
            "config_exists": str(self._config_path.exists()),
            "has_config_files": str(self._has_config_files(self._config_path) if self._config_path.exists() else False),
        }

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

    @property
    def project_root(self) -> Path:
        """获取项目根目录"""
        return self._project_root

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

        Raises:
            ValueError: 配置文件验证失败时抛出，包含友好的错误信息
        """
        if not force_reload and "global" in self._configs:
            return self._configs["global"]

        from .global_config import GlobalConfig
        import logging

        logger = logging.getLogger(__name__)
        config_file = self._config_path / f"global_{self._environment.value}.yaml"

        if config_file.exists():
            try:
                config = GlobalConfig.from_file(config_file)
            except Exception as e:
                # 配置验证失败，提供友好错误信息
                raise ValueError(
                    f"配置文件 {config_file} 验证失败:\n{e}\n\n"
                    f"请检查配置文件格式和必填字段。\n"
                    f"配置文件路径: {config_file.absolute()}"
                )
        else:
            # 创建默认配置并保存
            config = GlobalConfig()
            config.environment = self._environment
            config.to_file(config_file)
            logger.warning(
                f"配置文件不存在，已创建默认配置: {config_file}\n"
                f"请根据需要修改配置。"
            )

        self._configs["global"] = config
        return config

    def load_qmt_gateway_config(self, force_reload: bool = False) -> "GlobalConfig":
        """加载服务端配置

        优先从 qmt_gateway.yaml 加载，如果不存在则从 global_{env}.yaml 加载。

        Args:
            force_reload: 是否强制重新加载

        Returns:
            服务端配置对象
        """
        if not force_reload and "server" in self._configs:
            return self._configs["server"]

        from .global_config import GlobalConfig
        import logging
        logger = logging.getLogger(__name__)

        # 优先尝试 qmt_gateway.yaml
        server_config_file = self._config_path / "qmt_gateway.yaml"

        if server_config_file.exists():
            try:
                config = GlobalConfig.from_file(server_config_file)
                # 服务端默认使用本地QMT
                config.qmt.use_rpc = False
            except Exception as e:
                raise ValueError(f"服务端配置文件 {server_config_file} 验证失败:\n{e}")
        else:
            # 回退到 global 配置
            config = self.load_global_config(force_reload)
            # 服务端默认使用本地QMT
            config.qmt.use_rpc = False
            logger.info("未找到 qmt_gateway.yaml，使用全局配置")

        self._configs["server"] = config
        return config

    def load_config(self, force_reload: bool = False) -> "GlobalConfig":
        """加载客户端配置

        优先从 config.yaml 加载，如果不存在则从 global_{env}.yaml 加载。

        Args:
            force_reload: 是否强制重新加载

        Returns:
            客户端配置对象
        """
        if not force_reload and "client" in self._configs:
            return self._configs["client"]

        from .global_config import GlobalConfig
        import logging
        logger = logging.getLogger(__name__)

        # 优先尝试 config.yaml
        client_config_file = self._config_path / "config.yaml"

        if client_config_file.exists():
            try:
                config = GlobalConfig.from_file(client_config_file)
                # 客户端默认使用RPC模式
                config.qmt.use_rpc = True
                config.qmt.enabled = False  # 客户端不需要本地QMT
            except Exception as e:
                raise ValueError(f"客户端配置文件 {client_config_file} 验证失败:\n{e}")
        else:
            # 回退到 global 配置
            config = self.load_global_config(force_reload)
            logger.info("未找到 config.yaml，使用全局配置")

        self._configs["client"] = config
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

    def validate_config_for_feature(self, feature: str) -> None:
        """验证功能所需配置

        在使用特定功能前调用，确保配置正确。

        Args:
            feature: 功能名称（qmt, database, rpc_server等）

        Raises:
            ValueError: 配置不满足要求

        Example:
            ```python
            manager = ConfigManager()
            config = manager.load_global_config()

            # 启动QMT前验证
            manager.validate_config_for_feature("qmt")

            # 启动数据库前验证
            manager.validate_config_for_feature("database")
            ```
        """
        config = self.get_config("global")
        if config is None:
            raise ValueError(
                "全局配置未加载，请先调用 load_global_config()。\n"
                "示例:\n"
                "  manager = ConfigManager()\n"
                "  config = manager.load_global_config()\n"
                "  manager.validate_config_for_feature('qmt')"
            )

        if hasattr(config, 'validate_for_use'):
            config.validate_for_use(feature)
        else:
            # 向后兼容旧版本配置
            if feature == "qmt":
                if not config.qmt.enabled:
                    raise ValueError("QMT功能未启用")

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        with cls._lock:
            cls._instance = None
