"""测试配置验证功能

这是P0-2 Task 5的测试脚本。
测试ConfigManager的验证功能和配置类的验证逻辑。
"""

import tempfile
import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

from vnpy_china_config.global_config import (
    QmtConfig,
    DatabaseConfig,
    GlobalConfig,
    LoggingConfig,
    RpcConfig,
    RiskGlobalConfig,
)
from vnpy_china_config.base import Environment
from vnpy_china_config.loader import ConfigManager


class TestQmtConfigValidation:
    """测试QmtConfig验证"""

    def test_qmt_config_disabled_allows_empty(self):
        """测试禁用QMT时允许空配置"""
        config = QmtConfig(enabled=False)
        assert config.account_id == ""
        assert config.mini_path == ""
        # 验证成功，不抛出异常

    def test_qmt_config_enabled_requires_account_id(self):
        """测试启用QMT时account_id必填"""
        # 启用QMT但account_id为空
        with pytest.raises(ValueError, match="account_id.*不能为空"):
            QmtConfig(
                enabled=True,
                account_id="",
                mini_path="D:/test/userdata_mini/"
            )

    def test_qmt_config_enabled_requires_mini_path(self):
        """测试启用QMT时mini_path必填"""
        # 启用QMT但mini_path为空
        with pytest.raises(ValueError, match="mini_path.*不能为空"):
            QmtConfig(
                enabled=True,
                account_id="test_account",
                mini_path=""
            )

    def test_qmt_config_enabled_requires_all_fields(self):
        """测试启用QMT时所有必填字段验证"""
        # 启用QMT但所有必填字段都为空
        with pytest.raises(ValueError, match="account_id 在启用QMT时不能为空"):
            QmtConfig(
                enabled=True,
                account_id="",
                mini_path=""
            )

    def test_qmt_config_mini_path_validation_warning(self):
        """测试mini_path路径格式警告"""
        # 正确路径格式 - 不应该有警告
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = QmtConfig(
                enabled=False,  # 禁用时不检查路径存在性
                account_id="40218291",
                mini_path="D:/QMT/userdata_mini/"
            )
            # 路径格式正确，不应该有警告
            warning_messages = [str(warning.message) for warning in w]
            assert not any("路径可能不正确" in msg for msg in warning_messages)

        # 错误路径格式（缺少userdata_mini）- 应该有警告
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = QmtConfig(
                enabled=False,  # 禁用时不检查路径存在性
                account_id="40218291",
                mini_path="D:/QMT/"  # 缺少userdata_mini
            )
            # 应该有路径警告
            warning_messages = [str(warning.message) for warning in w]
            assert any("路径可能不正确" in msg for msg in warning_messages)

    def test_qmt_config_path_must_exist_when_enabled(self):
        """测试启用QMT时路径必须存在"""
        # 使用不存在的路径
        with pytest.raises(ValueError, match="miniQMT 路径不存在"):
            QmtConfig(
                enabled=True,
                account_id="test_account",
                mini_path="D:/nonexistent/path/userdata_mini/"
            )

    def test_qmt_config_valid_configuration(self):
        """测试有效的QMT配置"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            mini_path = Path(tmpdir) / "userdata_mini"
            mini_path.mkdir(parents=True, exist_ok=True)

            # 有效配置
            config = QmtConfig(
                enabled=True,
                account_id="40218291",
                mini_path=str(mini_path),
                session_id=0,
                password="test_password"
            )

            assert config.enabled is True
            assert config.account_id == "40218291"
            assert config.mini_path == str(mini_path)


class TestDatabaseConfigValidation:
    """测试DatabaseConfig验证"""

    def test_database_config_enabled_default(self):
        """测试数据库配置默认启用"""
        config = DatabaseConfig()
        assert config.enabled is True

    def test_database_config_port_validation(self):
        """测试端口号验证"""
        # 有效端口号
        config = DatabaseConfig(mysql_port=3306, redis_port=6379)
        assert config.mysql_port == 3306
        assert config.redis_port == 6379

        # 无效端口号 - 超出范围
        with pytest.raises(ValueError, match="端口号必须在 1-65535"):
            DatabaseConfig(mysql_port=0)

        with pytest.raises(ValueError, match="端口号必须在 1-65535"):
            DatabaseConfig(redis_port=70000)

    def test_database_config_pool_size_validation(self):
        """测试连接池大小验证"""
        # 有效连接池大小
        config = DatabaseConfig(pool_size=10, max_overflow=20)
        assert config.pool_size == 10
        assert config.max_overflow == 20

        # 无效连接池大小 - 必须>0
        with pytest.raises(ValueError, match="连接池大小必须大于0"):
            DatabaseConfig(pool_size=0)

        with pytest.raises(ValueError, match="连接池大小必须大于0"):
            DatabaseConfig(max_overflow=0)

        # 无效连接池大小 - 不应超过100
        with pytest.raises(ValueError, match="连接池大小不应超过100"):
            DatabaseConfig(pool_size=101)

    def test_database_config_password_warning(self):
        """测试数据库密码警告"""
        # 空密码警告
        with pytest.warns(UserWarning, match="空密码或默认密码"):
            DatabaseConfig(
                enabled=True,
                mysql_password=""
            )

        # 默认密码警告
        with pytest.warns(UserWarning, match="空密码或默认密码"):
            DatabaseConfig(
                enabled=True,
                mysql_password="password"
            )


class TestGlobalConfigValidation:
    """测试GlobalConfig验证"""

    def test_global_config_production_warnings(self):
        """测试生产环境配置警告"""
        # 生产环境 - 未启用数据库
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = GlobalConfig(
                environment=Environment.PRODUCTION,
                database=DatabaseConfig(enabled=False),
                qmt=QmtConfig(enabled=False)
            )
            # 应该有数据库警告
            warning_messages = [str(warning.message) for warning in w]
            assert any("数据库" in msg for msg in warning_messages)

        # 生产环境 - QMT启用但无密码
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # 创建临时目录
            with tempfile.TemporaryDirectory() as tmpdir:
                mini_path = Path(tmpdir) / "userdata_mini"
                mini_path.mkdir(parents=True, exist_ok=True)

                config = GlobalConfig(
                    environment=Environment.PRODUCTION,
                    database=DatabaseConfig(enabled=True),
                    qmt=QmtConfig(
                        enabled=True,
                        account_id="test",
                        mini_path=str(mini_path),
                        password=""
                    )
                )
                # 应该有密码警告
                warning_messages = [str(warning.message) for warning in w]
                assert any("密码" in msg for msg in warning_messages)

    def test_validate_for_use_qmt_disabled(self):
        """测试validate_for_use - QMT未启用"""
        config = GlobalConfig(
            qmt=QmtConfig(enabled=False)
        )

        with pytest.raises(ValueError, match="QMT功能未启用"):
            config.validate_for_use("qmt")

    def test_validate_for_use_qmt_incomplete(self):
        """测试validate_for_use - QMT配置不完整"""
        config = GlobalConfig(
            qmt=QmtConfig(enabled=False)
        )

        # 启用QMT但配置不完整
        config.qmt.enabled = True

        with pytest.raises(ValueError, match="QMT配置不完整"):
            config.validate_for_use("qmt")

    def test_validate_for_use_qmt_complete(self):
        """测试validate_for_use - QMT配置完整"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            mini_path = Path(tmpdir) / "userdata_mini"
            mini_path.mkdir(parents=True, exist_ok=True)

            config = GlobalConfig(
                qmt=QmtConfig(
                    enabled=True,
                    account_id="test_account",
                    mini_path=str(mini_path)
                )
            )

            # 应该通过验证
            config.validate_for_use("qmt")  # 不应该抛出异常

    def test_validate_for_use_database_disabled(self):
        """测试validate_for_use - 数据库未启用"""
        config = GlobalConfig(
            database=DatabaseConfig(enabled=False)
        )

        with pytest.raises(ValueError, match="数据库功能未启用"):
            config.validate_for_use("database")

    def test_validate_for_use_database_no_database_name(self):
        """测试validate_for_use - 数据库名称为空"""
        config = GlobalConfig(
            database=DatabaseConfig(enabled=True, mysql_database="")
        )

        with pytest.raises(ValueError, match="数据库名称未配置"):
            config.validate_for_use("database")

    def test_validate_for_use_database_complete(self):
        """测试validate_for_use - 数据库配置完整"""
        config = GlobalConfig(
            database=DatabaseConfig(
                enabled=True,
                mysql_database="test_db"
            )
        )

        # 应该通过验证
        config.validate_for_use("database")  # 不应该抛出异常

    def test_validate_for_use_rpc_server_requires_qmt(self):
        """测试validate_for_use - RPC服务端需要QMT"""
        config = GlobalConfig(
            qmt=QmtConfig(enabled=False)
        )

        with pytest.raises(ValueError, match="RPC服务端需要QMT配置"):
            config.validate_for_use("rpc_server")

    def test_validate_for_use_rpc_server_with_qmt(self):
        """测试validate_for_use - RPC服务端与QMT配置"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            mini_path = Path(tmpdir) / "userdata_mini"
            mini_path.mkdir(parents=True, exist_ok=True)

            config = GlobalConfig(
                qmt=QmtConfig(
                    enabled=True,
                    account_id="test",
                    mini_path=str(mini_path)
                )
            )

            # 应该通过验证
            config.validate_for_use("rpc_server")  # 不应该抛出异常

    def test_validate_for_use_unknown_feature(self):
        """测试validate_for_use - 未知功能名称"""
        config = GlobalConfig()

        with pytest.raises(ValueError, match="未知的功能名称"):
            config.validate_for_use("unknown_feature")


class TestConfigManagerValidation:
    """测试ConfigManager验证功能"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置单例
        ConfigManager.reset_instance()

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 重置单例
        ConfigManager.reset_instance()

    def test_config_manager_load_valid_config(self):
        """测试ConfigManager加载有效配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_path.mkdir(parents=True, exist_ok=True)

            # 创建配置管理器
            manager = ConfigManager()
            manager.set_config_path(config_path)
            manager.set_environment(Environment.DEVELOPMENT)

            # 创建配置文件
            config_file = config_path / "global_development.yaml"
            config = GlobalConfig(
                environment=Environment.DEVELOPMENT,
                database=DatabaseConfig(enabled=True),
                qmt=QmtConfig(enabled=False)
            )
            config.to_file(config_file)

            # 加载配置
            loaded_config = manager.load_global_config()

            assert loaded_config is not None
            assert loaded_config.environment == Environment.DEVELOPMENT

    def test_config_manager_load_invalid_config_friendly_error(self):
        """测试ConfigManager加载无效配置时提供友好错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_path.mkdir(parents=True, exist_ok=True)

            # 创建配置管理器
            manager = ConfigManager()
            manager.set_config_path(config_path)
            manager.set_environment(Environment.DEVELOPMENT)

            # 创建无效的配置文件
            config_file = config_path / "global_development.yaml"
            config_file.write_text("""
environment: development
database:
  mysql_port: -1  # 无效端口号
""")

            # 加载配置应该抛出ValueError
            with pytest.raises(ValueError) as exc_info:
                manager.load_global_config()

            # 验证错误信息友好
            error_msg = str(exc_info.value)
            assert "验证失败" in error_msg
            assert str(config_file) in error_msg
            assert "请检查配置文件格式" in error_msg

    def test_config_manager_validate_config_for_feature_qmt(self):
        """测试ConfigManager.validate_config_for_feature - QMT"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_path.mkdir(parents=True, exist_ok=True)

            # 创建配置管理器
            manager = ConfigManager()
            manager.set_config_path(config_path)
            manager.set_environment(Environment.DEVELOPMENT)

            # 创建配置文件（QMT未启用）
            config_file = config_path / "global_development.yaml"
            config = GlobalConfig(
                environment=Environment.DEVELOPMENT,
                qmt=QmtConfig(enabled=False)
            )
            config.to_file(config_file)

            # 加载配置
            manager.load_global_config()

            # 验证QMT功能应该失败
            with pytest.raises(ValueError, match="QMT功能未启用"):
                manager.validate_config_for_feature("qmt")

    def test_config_manager_validate_config_for_feature_database(self):
        """测试ConfigManager.validate_config_for_feature - database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_path.mkdir(parents=True, exist_ok=True)

            # 创建配置管理器
            manager = ConfigManager()
            manager.set_config_path(config_path)
            manager.set_environment(Environment.DEVELOPMENT)

            # 创建配置文件（数据库未启用）
            config_file = config_path / "global_development.yaml"
            config = GlobalConfig(
                environment=Environment.DEVELOPMENT,
                database=DatabaseConfig(enabled=False)
            )
            config.to_file(config_file)

            # 加载配置
            manager.load_global_config()

            # 验证数据库功能应该失败
            with pytest.raises(ValueError, match="数据库功能未启用"):
                manager.validate_config_for_feature("database")

    def test_config_manager_validate_config_without_loading(self):
        """测试ConfigManager.validate_config_for_feature - 未加载配置"""
        manager = ConfigManager()

        # 未加载配置就验证应该失败
        with pytest.raises(ValueError, match="全局配置未加载"):
            manager.validate_config_for_feature("qmt")

    def test_config_manager_creates_default_config(self):
        """测试ConfigManager创建默认配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_path.mkdir(parents=True, exist_ok=True)

            # 创建配置管理器
            manager = ConfigManager()
            manager.set_config_path(config_path)
            manager.set_environment(Environment.DEVELOPMENT)

            # 配置文件不存在，应该创建默认配置（单环境收敛后默认创建到 config.yaml）
            config_file = config_path / "config.yaml"
            assert not config_file.exists()

            # 加载配置会创建默认配置文件
            config = manager.load_global_config()

            # 验证配置文件已创建
            assert config_file.exists()

            # 验证配置内容
            assert config.environment == Environment.DEVELOPMENT


class TestOtherConfigValidation:
    """测试其他配置类的验证"""

    def test_logging_config_level_validation(self):
        """测试LoggingConfig日志级别验证"""
        # 有效日志级别
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

        # 无效日志级别
        with pytest.raises(ValueError, match="无效的日志级别"):
            LoggingConfig(level="INVALID")

    def test_logging_config_max_bytes_validation(self):
        """测试LoggingConfig日志文件大小验证"""
        # 有效值
        config = LoggingConfig(max_bytes=1024)
        assert config.max_bytes == 1024

        # 无效值 - 必须>0
        with pytest.raises(ValueError, match="max_bytes 必须大于 0"):
            LoggingConfig(max_bytes=0)

    def test_logging_config_backup_count_validation(self):
        """测试LoggingConfig日志文件保留数量验证"""
        # 有效值
        config = LoggingConfig(backup_count=5)
        assert config.backup_count == 5

        # 无效值 - 不能为负数
        with pytest.raises(ValueError, match="backup_count 不能为负数"):
            LoggingConfig(backup_count=-1)

    def test_rpc_config_timeout_validation(self):
        """测试RpcConfig超时时间验证"""
        # 有效值
        config = RpcConfig(timeout=5000)
        assert config.timeout == 5000

        # 无效值 - 必须>0
        with pytest.raises(ValueError, match="timeout 必须大于 0"):
            RpcConfig(timeout=0)

    def test_risk_config_ratio_validation(self):
        """测试RiskGlobalConfig比例值验证"""
        # 有效值
        config = RiskGlobalConfig(
            max_position_ratio=0.8,
            max_single_position_ratio=0.2,
            max_daily_loss_ratio=0.05
        )
        assert config.max_position_ratio == 0.8

        # 无效值 - 超出范围
        with pytest.raises(ValueError, match="比例值必须在 0-1"):
            RiskGlobalConfig(max_position_ratio=1.5)

        with pytest.raises(ValueError, match="比例值必须在 0-1"):
            RiskGlobalConfig(max_single_position_ratio=-0.1)

    def test_risk_config_consecutive_losses_validation(self):
        """测试RiskGlobalConfig连续亏损次数验证"""
        # 有效值
        config = RiskGlobalConfig(max_consecutive_losses=5)
        assert config.max_consecutive_losses == 5

        # 无效值 - 不能为负数
        with pytest.raises(ValueError, match="max_consecutive_losses 不能为负数"):
            RiskGlobalConfig(max_consecutive_losses=-1)


if __name__ == "__main__":
    # 运行测试
    print("开始测试配置验证功能...")
    pytest.main([__file__, "-v", "--tb=short"])
