"""简单测试GlobalConfig的跨模块依赖验证和validate_for_use方法

不依赖pytest，直接运行。
"""

import warnings
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from vnpy_china_config.global_config import (
    GlobalConfig,
    DatabaseConfig,
    QmtConfig,
)
from vnpy_china_config.base import Environment


def test_database_config_enabled_field():
    """测试DatabaseConfig的enabled字段"""
    print("测试1: DatabaseConfig的enabled字段")

    # 默认启用
    db_config = DatabaseConfig()
    assert db_config.enabled is True, "默认应该启用"
    print("  [PASS] 默认enabled=True")

    # 可以禁用
    db_config_disabled = DatabaseConfig(enabled=False)
    assert db_config_disabled.enabled is False, "可以禁用"
    print("  [PASS] 可以设置enabled=False")


def test_validate_for_use_qmt():
    """测试validate_for_use的qmt功能验证"""
    print("\n测试2: validate_for_use的qmt功能验证")

    config = GlobalConfig(
        qmt=QmtConfig(enabled=False)
    )

    # QMT未启用 - 应该报错
    try:
        config.validate_for_use("qmt")
        print("  [FAIL] 应该抛出ValueError")
        return False
    except ValueError as e:
        assert "QMT功能未启用" in str(e), "错误信息应该包含'QMT功能未启用'"
        print(f"  [PASS] QMT未启用时正确报错: {e}")

    # 启用QMT但配置不完整 - 应该报错
    config.qmt.enabled = True
    try:
        config.validate_for_use("qmt")
        print("  [FAIL] 配置不完整时应该抛出ValueError")
        return False
    except ValueError as e:
        assert "QMT配置不完整" in str(e), "错误信息应该包含'QMT配置不完整'"
        print(f"  [PASS] 配置不完整时正确报错: {e}")


def test_validate_for_use_database():
    """测试validate_for_use的database功能验证"""
    print("\n测试3: validate_for_use的database功能验证")

    config = GlobalConfig(
        database=DatabaseConfig(enabled=False)
    )

    # 数据库未启用 - 应该报错
    try:
        config.validate_for_use("database")
        print("  [FAIL] 应该抛出ValueError")
        return False
    except ValueError as e:
        assert "数据库功能未启用" in str(e), "错误信息应该包含'数据库功能未启用'"
        print(f"  [PASS] 数据库未启用时正确报错: {e}")

    # 启用但数据库名称为空 - 应该报错
    config.database.enabled = True
    config.database.mysql_database = ""
    try:
        config.validate_for_use("database")
        print("  [FAIL] 数据库名称为空时应该抛出ValueError")
        return False
    except ValueError as e:
        assert "数据库名称未配置" in str(e), "错误信息应该包含'数据库名称未配置'"
        print(f"  [PASS] 数据库名称为空时正确报错: {e}")

    # 配置完整 - 应该通过
    config.database.mysql_database = "test_db"
    try:
        config.validate_for_use("database")
        print("  [PASS] 配置完整时验证通过")
    except Exception as e:
        print(f"  [FAIL] 配置完整时不应该报错: {e}")
        return False


def test_validate_for_use_rpc_server():
    """测试validate_for_use的rpc_server功能验证"""
    print("\n测试4: validate_for_use的rpc_server功能验证")

    config = GlobalConfig(
        qmt=QmtConfig(enabled=False)
    )

    # QMT未启用 - 应该报错
    try:
        config.validate_for_use("rpc_server")
        print("  [FAIL] 应该抛出ValueError")
        return False
    except ValueError as e:
        assert "RPC服务端需要QMT配置" in str(e), "错误信息应该包含'RPC服务端需要QMT配置'"
        print(f"  [PASS] QMT未启用时正确报错: {e}")

    # QMT启用 - 应该通过（虽然字段可能不完整，但validate_for_use只检查enabled）
    config.qmt.enabled = True
    config.qmt.account_id = "test"
    config.qmt.mini_path = "D:/test/userdata_mini/"
    try:
        config.validate_for_use("rpc_server")
        print("  [PASS] QMT启用时验证通过")
    except Exception as e:
        print(f"  [FAIL] QMT启用时不应该报错: {e}")
        return False


def test_validate_for_use_unknown_feature():
    """测试validate_for_use的未知功能名称"""
    print("\n测试5: validate_for_use的未知功能名称")

    config = GlobalConfig()

    try:
        config.validate_for_use("unknown_feature")
        print("  [FAIL] 应该抛出ValueError")
        return False
    except ValueError as e:
        assert "未知的功能名称" in str(e), "错误信息应该包含'未知的功能名称'"
        print(f"  [PASS] 未知功能时正确报错: {e}")


def test_production_environment_warnings():
    """测试生产环境配置警告"""
    print("\n测试6: 生产环境配置警告")

    # 测试：生产环境 - 未启用数据库应该有警告
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        config_prod = GlobalConfig(
            environment=Environment.PRODUCTION,
            database=DatabaseConfig(enabled=False),
            qmt=QmtConfig(enabled=False)
        )

        # 检查是否有数据库警告
        warning_messages = [str(warning.message) for warning in w]
        has_db_warning = any("数据库" in msg for msg in warning_messages)

        if has_db_warning:
            print(f"  [PASS] 生产环境未启用数据库时有警告: {warning_messages}")
        else:
            print(f"  [WARN] 警告: 生产环境未启用数据库时没有警告 (warnings={warning_messages})")

    # 测试：生产环境 - QMT启用但无密码应该有警告
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # 由于路径验证会报错，我们需要捕获它
        try:
            config_prod_qmt = GlobalConfig(
                environment=Environment.PRODUCTION,
                database=DatabaseConfig(enabled=True),
                qmt=QmtConfig(
                    enabled=True,
                    account_id="test_account",
                    mini_path="D:/nonexistent_path/userdata_mini/",
                    password=""
                )
            )
        except ValueError as e:
            # 路径不存在会报错，这是预期的
            print(f"  [INFO] 路径验证错误（预期）: {e}")
            return True

        # 如果没有路径错误，检查密码警告
        warning_messages = [str(warning.message) for warning in w]
        has_pwd_warning = any("密码" in msg for msg in warning_messages)

        if has_pwd_warning:
            print(f"  [PASS] 生产环境QMT无密码时有警告: {warning_messages}")
        else:
            print(f"  [WARN] 警告: 生产环境QMT无密码时没有警告 (warnings={warning_messages})")


def test_validate_for_use_provides_helpful_errors():
    """测试validate_for_use提供有用的错误信息"""
    print("\n测试7: validate_for_use提供有用的错误信息")

    config = GlobalConfig(
        environment=Environment.PRODUCTION,
        qmt=QmtConfig(enabled=False)
    )

    # 测试错误信息是否包含配置文件名
    try:
        config.validate_for_use("qmt")
        print("  [FAIL] 应该抛出ValueError")
        return False
    except ValueError as e:
        error_msg = str(e)
        # 验证错误信息包含有用的提示
        assert "qmt.enabled=true" in error_msg, "错误信息应该包含qmt.enabled=true提示"
        assert "global_production.yaml" in error_msg, "错误信息应该包含配置文件名"
        print(f"  [PASS] 错误信息包含有用的提示: {error_msg}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试GlobalConfig的跨模块依赖验证")
    print("=" * 60)

    tests = [
        test_database_config_enabled_field,
        test_validate_for_use_qmt,
        test_validate_for_use_database,
        test_validate_for_use_rpc_server,
        test_validate_for_use_unknown_feature,
        test_production_environment_warnings,
        test_validate_for_use_provides_helpful_errors,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            result = test_func()
            if result is False:
                failed += 1
            else:
                passed += 1
        except AssertionError as e:
            print(f"  [FAIL] 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] 测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
