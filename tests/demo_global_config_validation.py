"""演示GlobalConfig的跨模块依赖验证和validate_for_use方法的使用

这个脚本演示了如何使用新添加的验证功能。
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from vnpy_china_config.global_config import GlobalConfig, DatabaseConfig, QmtConfig
from vnpy_china_config.base import Environment


def demo_validate_for_use():
    """演示validate_for_use方法的使用"""
    print("=" * 60)
    print("演示: validate_for_use方法")
    print("=" * 60)

    # 创建一个禁用QMT的配置
    config = GlobalConfig(
        environment=Environment.DEVELOPMENT,
        qmt=QmtConfig(enabled=False)
    )

    print("\n1. 尝试使用QMT功能（未启用）:")
    try:
        config.validate_for_use("qmt")
    except ValueError as e:
        print(f"   错误: {e}")

    print("\n2. 启用QMT但配置不完整:")
    config.qmt.enabled = True
    try:
        config.validate_for_use("qmt")
    except ValueError as e:
        print(f"   错误: {e}")

    print("\n3. 完善QMT配置后:")
    config.qmt.account_id = "40218291"
    config.qmt.mini_path = "D:/国金证券QMT交易端/userdata_mini/"
    try:
        # 注意：由于路径可能不存在，可能会报错
        # 但validate_for_use不会检查路径存在性，只检查字段不为空
        config.validate_for_use("qmt")
        print("   验证通过！")
    except ValueError as e:
        print(f"   错误: {e}")


def demo_database_validation():
    """演示数据库验证"""
    print("\n" + "=" * 60)
    print("演示: 数据库验证")
    print("=" * 60)

    # 创建一个禁用数据库的配置
    config = GlobalConfig(
        database=DatabaseConfig(enabled=False)
    )

    print("\n1. 尝试使用数据库功能（未启用）:")
    try:
        config.validate_for_use("database")
    except ValueError as e:
        print(f"   错误: {e}")

    print("\n2. 启用数据库:")
    config.database.enabled = True
    config.database.mysql_database = "my_trading_db"
    try:
        config.validate_for_use("database")
        print("   验证通过！")
        print(f"   MySQL DSN: {config.get_mysql_dsn()}")
        print(f"   Redis URL: {config.get_redis_url()}")
    except ValueError as e:
        print(f"   错误: {e}")


def demo_production_warnings():
    """演示生产环境警告"""
    print("\n" + "=" * 60)
    print("演示: 生产环境警告")
    print("=" * 60)

    import warnings

    print("\n1. 生产环境未启用数据库:")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        config = GlobalConfig(
            environment=Environment.PRODUCTION,
            database=DatabaseConfig(enabled=False),
            qmt=QmtConfig(enabled=False)
        )
        if w:
            for warning in w:
                print(f"   警告: {warning.message}")

    print("\n2. 生产环境QMT未设置密码:")
    # 注意：由于路径验证，这可能会报错
    print("   (跳过此演示，因为路径验证会先触发错误)")


def demo_rpc_server_validation():
    """演示RPC服务端验证"""
    print("\n" + "=" * 60)
    print("演示: RPC服务端验证")
    print("=" * 60)

    config = GlobalConfig(
        qmt=QmtConfig(enabled=False)
    )

    print("\n1. 尝试使用RPC服务端（QMT未启用）:")
    try:
        config.validate_for_use("rpc_server")
    except ValueError as e:
        print(f"   错误: {e}")

    print("\n2. 启用QMT后:")
    config.qmt.enabled = True
    config.qmt.account_id = "test_account"
    config.qmt.mini_path = "D:/test/userdata_mini/"
    try:
        config.validate_for_use("rpc_server")
        print("   验证通过！")
    except ValueError as e:
        print(f"   错误: {e}")


def demo_unknown_feature():
    """演示未知功能验证"""
    print("\n" + "=" * 60)
    print("演示: 未知功能验证")
    print("=" * 60)

    config = GlobalConfig()

    print("\n尝试验证未知功能:")
    try:
        config.validate_for_use("unknown_feature")
    except ValueError as e:
        print(f"错误: {e}")


def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("GlobalConfig验证功能演示")
    print("=" * 60)

    demo_validate_for_use()
    demo_database_validation()
    demo_production_warnings()
    demo_rpc_server_validation()
    demo_unknown_feature()

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
