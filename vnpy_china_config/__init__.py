"""
A股统一配置管理模块

提供 A 股交易系统的统一配置管理，包括：
- 配置基类和运行环境枚举
- 全局配置（数据库、日志、RPC、风控）
- 模块配置（数据、监控、策略、资金、分析、机器学习）
- 配置管理器和验证器

Quick Start:
    ```python
    from vnpy_china_config import (
        # 基础
        BaseConfig,
        Environment,
        ConfigManager,

        # 全局配置
        GlobalConfig,
        DatabaseConfig,
        LoggingConfig,
        RpcConfig,
        RiskGlobalConfig,

        # 模块配置
        DataModuleConfig,
        MonitorModuleConfig,
        StrategyModuleConfig,
        CapitalModuleConfig,
        AnalysisModuleConfig,
        MLModuleConfig,
    )

    # 使用配置管理器
    manager = ConfigManager()
    manager.set_environment(Environment.PRODUCTION)

    # 加载配置
    global_config = manager.load_global_config()
    data_config = manager.load_module_config("data", DataModuleConfig)

    # 访问配置
    print(f"MySQL Host: {global_config.database.mysql_host}")
    ```
"""

from .base import BaseConfig, Environment
from .global_config import (
    DatabaseConfig,
    GlobalConfig,
    LoggingConfig,
    RiskGlobalConfig,
    RpcConfig,
)
from .loader import ConfigManager
from .validator import ConfigValidator
from .module_configs.data_config import DataModuleConfig
from .module_configs.monitor_config import MonitorModuleConfig
from .module_configs.strategy_config import StrategyModuleConfig
from .module_configs.capital_config import CapitalModuleConfig
from .module_configs.analysis_config import AnalysisModuleConfig
from .module_configs.ml_config import MLModuleConfig

__version__ = "1.0.0"

__all__ = [
    # 基础
    "BaseConfig",
    "Environment",
    "ConfigManager",
    "ConfigValidator",
    # 全局配置
    "GlobalConfig",
    "DatabaseConfig",
    "LoggingConfig",
    "RpcConfig",
    "RiskGlobalConfig",
    # 模块配置
    "DataModuleConfig",
    "MonitorModuleConfig",
    "StrategyModuleConfig",
    "CapitalModuleConfig",
    "AnalysisModuleConfig",
    "MLModuleConfig",
]
