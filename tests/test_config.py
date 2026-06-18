"""
统一配置管理系统单元测试

测试配置基类、环境枚举、全局配置、模块配置、配置管理器和验证器的功能。
"""

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# 设置测试环境变量
os.environ["VNPY_ENV"] = "testing"

from vnpy_china_config import (
    # 基础
    BaseConfig,
    Environment,
    ConfigManager,
    ConfigValidator,
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


class TestEnvironment(unittest.TestCase):
    """测试环境枚举"""

    def test_environment_values(self):
        """测试环境枚举值"""
        self.assertEqual(Environment.DEVELOPMENT.value, "development")
        self.assertEqual(Environment.TESTING.value, "testing")
        self.assertEqual(Environment.PRODUCTION.value, "production")

    def test_environment_str(self):
        """测试环境字符串表示"""
        self.assertEqual(str(Environment.DEVELOPMENT), "development")


class TestBaseConfig(unittest.TestCase):
    """测试配置基类"""

    def test_base_config_creation(self):
        """测试配置创建"""

        class TestConfig(BaseConfig):
            name: str = "test"
            value: int = 0

        config = TestConfig()
        self.assertEqual(config.name, "test")
        self.assertEqual(config.value, 0)

    def test_base_config_validation(self):
        """测试配置验证"""

        class TestConfig(BaseConfig):
            name: str = "test"
            value: int = 0

        # 测试类型验证
        config = TestConfig(name="hello", value=42)
        self.assertEqual(config.name, "hello")
        self.assertEqual(config.value, 42)

    def test_to_dict(self):
        """测试转换为字典"""

        class TestConfig(BaseConfig):
            name: str = "test"

        config = TestConfig(name="hello")
        data = config.to_dict()
        self.assertEqual(data["name"], "hello")

    def test_update(self):
        """测试更新配置"""

        class TestConfig(BaseConfig):
            name: str = "test"

        config = TestConfig()
        config.update(name="updated")
        self.assertEqual(config.name, "updated")


class TestDatabaseConfig(unittest.TestCase):
    """测试数据库配置"""

    def test_default_values(self):
        """测试默认值"""
        config = DatabaseConfig()
        self.assertEqual(config.mysql_host, "localhost")
        self.assertEqual(config.mysql_port, 3306)
        self.assertEqual(config.redis_host, "localhost")
        self.assertEqual(config.redis_port, 6379)

    def test_custom_values(self):
        """测试自定义值"""
        config = DatabaseConfig(
            mysql_host="db.example.com",
            mysql_port=3307,
            mysql_user="admin",
            mysql_password="secret",
            mysql_database="test_db",
        )
        self.assertEqual(config.mysql_host, "db.example.com")
        self.assertEqual(config.mysql_port, 3307)
        self.assertEqual(config.mysql_user, "admin")
        self.assertEqual(config.mysql_password, "secret")
        self.assertEqual(config.mysql_database, "test_db")

    def test_port_validation(self):
        """测试端口验证"""
        with self.assertRaises(ValueError):
            DatabaseConfig(mysql_port=0)

        with self.assertRaises(ValueError):
            DatabaseConfig(mysql_port=70000)


class TestLoggingConfig(unittest.TestCase):
    """测试日志配置"""

    def test_default_values(self):
        """测试默认值"""
        config = LoggingConfig()
        self.assertEqual(config.level, "INFO")
        self.assertTrue(config.file_enabled)
        self.assertTrue(config.console_enabled)

    def test_level_validation(self):
        """测试日志级别验证"""
        config = LoggingConfig(level="debug")
        self.assertEqual(config.level, "DEBUG")

        with self.assertRaises(ValueError):
            LoggingConfig(level="INVALID")

    def test_format(self):
        """测试日志格式"""
        config = LoggingConfig()
        self.assertIn("asctime", config.format)
        self.assertIn("levelname", config.format)


class TestRpcConfig(unittest.TestCase):
    """测试 RPC 配置"""

    def test_default_values(self):
        """测试默认值"""
        config = RpcConfig()
        self.assertEqual(config.rep_address, "tcp://127.0.0.1:2014")
        self.assertEqual(config.pub_address, "tcp://127.0.0.1:4102")
        self.assertEqual(config.timeout, 5000)

    def test_timeout_validation(self):
        """测试超时验证"""
        with self.assertRaises(ValueError):
            RpcConfig(timeout=0)


class TestRiskGlobalConfig(unittest.TestCase):
    """测试风控配置"""

    def test_default_values(self):
        """测试默认值"""
        config = RiskGlobalConfig()
        self.assertEqual(config.max_position_ratio, 0.8)
        self.assertEqual(config.max_single_position_ratio, 0.2)
        self.assertEqual(config.max_daily_loss_ratio, 0.05)
        self.assertEqual(config.max_consecutive_losses, 5)

    def test_ratio_validation(self):
        """测试比例验证"""
        with self.assertRaises(ValueError):
            RiskGlobalConfig(max_position_ratio=1.5)

        with self.assertRaises(ValueError):
            RiskGlobalConfig(max_position_ratio=-0.1)


class TestGlobalConfig(unittest.TestCase):
    """测试全局配置"""

    def test_creation(self):
        """测试创建"""
        config = GlobalConfig()
        self.assertEqual(config.environment, Environment.DEVELOPMENT)
        self.assertIsInstance(config.database, DatabaseConfig)
        self.assertIsInstance(config.logging, LoggingConfig)
        self.assertIsInstance(config.rpc, RpcConfig)
        self.assertIsInstance(config.risk, RiskGlobalConfig)

    def test_get_mysql_dsn(self):
        """测试 MySQL DSN"""
        config = GlobalConfig()
        config.database.mysql_host = "localhost"
        config.database.mysql_user = "user"
        config.database.mysql_password = "pass"
        config.database.mysql_port = 3306
        config.database.mysql_database = "test"

        dsn = config.get_mysql_dsn()
        self.assertIn("mysql", dsn)
        self.assertIn("localhost", dsn)

    def test_get_redis_url(self):
        """测试 Redis URL"""
        config = GlobalConfig()
        url = config.get_redis_url()
        self.assertIn("redis://", url)


class TestDataModuleConfig(unittest.TestCase):
    """测试数据模块配置"""

    def test_default_values(self):
        """测试默认值"""
        config = DataModuleConfig()
        self.assertEqual(config.tushare_rate_limit, 200)
        self.assertEqual(config.cache_bar_ttl, 300)
        self.assertTrue(config.auto_update_enabled)


class TestMonitorModuleConfig(unittest.TestCase):
    """测试监控模块配置"""

    def test_default_values(self):
        """测试默认值"""
        config = MonitorModuleConfig()
        self.assertTrue(config.enable_system_monitor)
        self.assertTrue(config.enable_trade_monitor)
        self.assertTrue(config.enable_alert)
        self.assertEqual(config.cpu_threshold, 80.0)


class TestStrategyModuleConfig(unittest.TestCase):
    """测试策略模块配置"""

    def test_default_values(self):
        """测试默认值"""
        config = StrategyModuleConfig()
        self.assertEqual(config.backtest_start_date, "2020-01-01")
        self.assertEqual(config.backtest_end_date, "2024-12-31")
        self.assertFalse(config.trading_enabled)


class TestCapitalModuleConfig(unittest.TestCase):
    """测试资金管理配置"""

    def test_default_values(self):
        """测试默认值"""
        config = CapitalModuleConfig()
        self.assertEqual(config.max_position_count, 10)
        self.assertEqual(config.default_position_type, "equal_weight")
        self.assertEqual(config.max_drawdown, 0.15)


class TestAnalysisModuleConfig(unittest.TestCase):
    """测试行情分析配置"""

    def test_default_values(self):
        """测试默认值"""
        config = AnalysisModuleConfig()
        self.assertFalse(config.level2_enabled)
        self.assertEqual(config.sector_count, 30)


class TestMLModuleConfig(unittest.TestCase):
    """测试机器学习配置"""

    def test_default_values(self):
        """测试默认值"""
        config = MLModuleConfig()
        self.assertEqual(config.default_model_type, "lightgbm")
        self.assertEqual(config.train_test_split, 0.8)
        self.assertEqual(config.ic_threshold, 0.05)


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""

    def setUp(self):
        """设置测试环境"""
        # 重置单例
        ConfigManager.reset_instance()
        self.manager = ConfigManager()

    def test_singleton(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        self.assertIs(manager1, manager2)

    def test_set_environment(self):
        """测试设置环境"""
        self.manager.set_environment(Environment.PRODUCTION)
        self.assertEqual(self.manager.environment, Environment.PRODUCTION)

    def test_set_config_path(self):
        """测试设置配置路径"""
        temp_path = Path(tempfile.gettempdir()) / "test_config"
        self.manager.set_config_path(temp_path)
        self.assertEqual(self.manager.config_path, temp_path)

    def test_load_global_config(self):
        """测试加载全局配置（单环境收敛后优先 config.yaml，environment 固定为 development）"""
        config = self.manager.load_global_config()
        self.assertIsInstance(config, GlobalConfig)
        self.assertEqual(config.environment, Environment.DEVELOPMENT)

    def test_get_config(self):
        """测试获取配置"""
        self.manager.load_global_config()
        config = self.manager.get_config("global")
        self.assertIsInstance(config, GlobalConfig)

    def test_update_config(self):
        """测试更新配置"""
        self.manager.load_global_config()
        self.manager.update_config("global", **{"logging": LoggingConfig(level="DEBUG")})
        config = self.manager.get_config("global")
        self.assertEqual(config.logging.level, "DEBUG")


class TestConfigValidator(unittest.TestCase):
    """测试配置验证器"""

    def setUp(self):
        """设置测试环境"""
        self.validator = ConfigValidator()

    def test_validate_required_fields(self):
        """测试必需字段验证"""
        config = DatabaseConfig()
        result = self.validator.validate_required_fields(
            config, ["mysql_host", "mysql_port"]
        )
        self.assertTrue(result["valid"])

        result = self.validator.validate_required_fields(
            config, ["mysql_host", "nonexistent_field"]
        )
        self.assertFalse(result["valid"])

    def test_validate_range(self):
        """测试数值范围验证"""
        config = RiskGlobalConfig()
        result = self.validator.validate_range(
            config, "max_position_ratio", min_val=0.0, max_val=1.0
        )
        self.assertTrue(result["valid"])

        config.max_position_ratio = 1.5
        result = self.validator.validate_range(
            config, "max_position_ratio", min_val=0.0, max_val=1.0
        )
        self.assertFalse(result["valid"])

    def test_validate_enum(self):
        """测试枚举值验证"""
        config = LoggingConfig()
        result = self.validator.validate_enum(
            config, "level", ["DEBUG", "INFO", "WARNING", "ERROR"]
        )
        self.assertTrue(result["valid"])

        # 测试不在列表中的值
        config.level = "INVALID_LEVEL"
        result = self.validator.validate_enum(
            config, "level", ["DEBUG", "INFO"]
        )
        self.assertFalse(result["valid"])

    def test_validate_dependencies(self):
        """测试依赖验证"""
        config = MonitorModuleConfig()
        config.email_enabled = True

        rules = {
            "email_enabled": ["smtp_host", "email_username", "email_password"]
        }
        result = self.validator.validate_dependencies(config, rules)
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
