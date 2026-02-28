"""运行配置验证测试的简单脚本

不依赖pytest，直接运行测试验证功能。
"""

import sys
import os
import tempfile
import warnings
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("Starting config validation tests...")

# 导入配置类
try:
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
    print("[OK] Import config classes successful")
except Exception as e:
    print(f"[FAIL] Import config classes failed: {e}")
    exit(1)

# 测试计数器
total_tests = 0
passed_tests = 0
failed_tests = 0

def test_case(name, func):
    """运行测试用例"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    print(f"\nTest {total_tests}: {name}")
    try:
        func()
        print(f"  [PASS] OK")
        passed_tests += 1
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed_tests += 1
        return False


# ============ QmtConfig 测试 ============

def test_qmt_disabled_allows_empty():
    """测试禁用QMT时允许空配置"""
    config = QmtConfig(enabled=False)
    assert config.account_id == ""
    assert config.mini_path == ""

test_case("禁用QMT时允许空配置", test_qmt_disabled_allows_empty)


def test_qmt_enabled_requires_account_id():
    """测试启用QMT时account_id必填"""
    try:
        QmtConfig(
            enabled=True,
            account_id="",
            mini_path="D:/test/userdata_mini/"
        )
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "account_id" not in str(e):
            raise

test_case("启用QMT时account_id必填", test_qmt_enabled_requires_account_id)


def test_qmt_mini_path_warning():
    """测试mini_path路径格式警告"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        QmtConfig(
            enabled=False,
            account_id="40218291",
            mini_path="D:/QMT/"  # 缺少userdata_mini
        )
        warning_messages = [str(warning.message) for warning in w]
        assert any("路径可能不正确" in msg for msg in warning_messages), "应该有路径警告"

test_case("mini_path路径格式警告", test_qmt_mini_path_warning)


def test_qmt_path_must_exist():
    """测试启用QMT时路径必须存在"""
    try:
        QmtConfig(
            enabled=True,
            account_id="test_account",
            mini_path="D:/nonexistent/path/userdata_mini/"
        )
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "路径不存在" not in str(e):
            raise

test_case("启用QMT时路径必须存在", test_qmt_path_must_exist)


# ============ DatabaseConfig 测试 ============

def test_database_password_warning():
    """测试数据库密码警告"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        DatabaseConfig(
            enabled=True,
            mysql_password=""
        )
        warning_messages = [str(warning.message) for warning in w]
        assert any("空密码或默认密码" in msg for msg in warning_messages), "应该有密码警告"

test_case("数据库密码警告", test_database_password_warning)


def test_database_port_validation():
    """测试端口号验证"""
    try:
        DatabaseConfig(mysql_port=0)
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "端口号" not in str(e):
            raise

test_case("数据库端口号验证", test_database_port_validation)


def test_database_pool_size_validation():
    """测试连接池大小验证"""
    try:
        DatabaseConfig(pool_size=0)
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "连接池大小必须大于0" not in str(e):
            raise

test_case("数据库连接池大小验证", test_database_pool_size_validation)


# ============ GlobalConfig 测试 ============

def test_production_warnings():
    """测试生产环境配置警告"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        GlobalConfig(
            environment=Environment.PRODUCTION,
            database=DatabaseConfig(enabled=False),
            qmt=QmtConfig(enabled=False)
        )
        warning_messages = [str(warning.message) for warning in w]
        assert any("数据库" in msg for msg in warning_messages), "应该有数据库警告"

test_case("生产环境配置警告", test_production_warnings)


def test_validate_for_use_qmt_disabled():
    """测试validate_for_use - QMT未启用"""
    config = GlobalConfig(qmt=QmtConfig(enabled=False))
    try:
        config.validate_for_use("qmt")
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "QMT功能未启用" not in str(e):
            raise

test_case("validate_for_use - QMT未启用", test_validate_for_use_qmt_disabled)


def test_validate_for_use_qmt_incomplete():
    """测试validate_for_use - QMT配置不完整"""
    config = GlobalConfig(qmt=QmtConfig(enabled=False))
    config.qmt.enabled = True
    try:
        config.validate_for_use("qmt")
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "QMT配置不完整" not in str(e):
            raise

test_case("validate_for_use - QMT配置不完整", test_validate_for_use_qmt_incomplete)


def test_validate_for_use_database_disabled():
    """测试validate_for_use - 数据库未启用"""
    config = GlobalConfig(database=DatabaseConfig(enabled=False))
    try:
        config.validate_for_use("database")
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "数据库功能未启用" not in str(e):
            raise

test_case("validate_for_use - 数据库未启用", test_validate_for_use_database_disabled)


def test_validate_for_use_unknown_feature():
    """测试validate_for_use - 未知功能名称"""
    config = GlobalConfig()
    try:
        config.validate_for_use("unknown_feature")
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "未知的功能名称" not in str(e):
            raise

test_case("validate_for_use - 未知功能名称", test_validate_for_use_unknown_feature)


# ============ ConfigManager 测试 ============

def test_config_manager_load_invalid_config():
    """测试ConfigManager加载无效配置时提供友好错误"""
    ConfigManager.reset_instance()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config"
        config_path.mkdir(parents=True, exist_ok=True)

        manager = ConfigManager()
        manager.set_config_path(config_path)
        manager.set_environment(Environment.DEVELOPMENT)

        # 创建无效的配置文件
        config_file = config_path / "global_development.yaml"
        config_file.write_text("""
environment: development
database:
  mysql_port: -1
""")

        try:
            manager.load_global_config()
            raise AssertionError("应该抛出ValueError")
        except ValueError as e:
            error_msg = str(e)
            assert "验证失败" in error_msg, f"错误信息应包含'验证失败': {error_msg}"
            assert "请检查配置文件格式" in error_msg, f"错误信息应包含提示: {error_msg}"

test_case("ConfigManager加载无效配置时提供友好错误", test_config_manager_load_invalid_config)


def test_config_manager_validate_without_loading():
    """测试ConfigManager.validate_config_for_feature - 未加载配置"""
    ConfigManager.reset_instance()
    manager = ConfigManager()
    try:
        manager.validate_config_for_feature("qmt")
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "全局配置未加载" not in str(e):
            raise

test_case("ConfigManager.validate_config_for_feature - 未加载配置", test_config_manager_validate_without_loading)


def test_config_manager_creates_default_config():
    """测试ConfigManager创建默认配置"""
    ConfigManager.reset_instance()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config"
        config_path.mkdir(parents=True, exist_ok=True)

        manager = ConfigManager()
        manager.set_config_path(config_path)
        manager.set_environment(Environment.DEVELOPMENT)

        config_file = config_path / "global_development.yaml"
        assert not config_file.exists(), "配置文件不应存在"

        config = manager.load_global_config()
        assert config_file.exists(), "应该创建默认配置文件"
        assert config.environment == Environment.DEVELOPMENT

test_case("ConfigManager创建默认配置", test_config_manager_creates_default_config)


# ============ 其他配置类测试 ============

def test_logging_config_level_validation():
    """测试LoggingConfig日志级别验证"""
    try:
        LoggingConfig(level="INVALID")
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "无效的日志级别" not in str(e):
            raise

test_case("LoggingConfig日志级别验证", test_logging_config_level_validation)


def test_rpc_config_timeout_validation():
    """测试RpcConfig超时时间验证"""
    try:
        RpcConfig(timeout=0)
        raise AssertionError("应该抛出ValueError")
    except (ValueError, Exception) as e:
        # Pydantic 2.x 抛出 ValidationError
        error_msg = str(e)
        if "timeout" not in error_msg and "大于0" not in error_msg:
            raise

test_case("RpcConfig超时时间验证", test_rpc_config_timeout_validation)


def test_risk_config_ratio_validation():
    """测试RiskGlobalConfig比例值验证"""
    try:
        RiskGlobalConfig(max_position_ratio=1.5)
        raise AssertionError("应该抛出ValueError")
    except ValueError as e:
        if "比例值必须在 0-1" not in str(e):
            raise

test_case("RiskGlobalConfig比例值验证", test_risk_config_ratio_validation)


# ============ 总结 ============

print("\n" + "="*60)
print(f"Test Summary:")
print(f"  Total: {total_tests}")
print(f"  Passed: {passed_tests}")
print(f"  Failed: {failed_tests}")
print(f"  Success Rate: {passed_tests/total_tests*100:.1f}%")
print("="*60)

if failed_tests == 0:
    print("\n[PASS] All tests passed!")
    exit(0)
else:
    print(f"\n[FAIL] {failed_tests} test(s) failed")
    exit(1)
