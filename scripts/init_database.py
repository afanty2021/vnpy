#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库表初始化脚本

创建VeighNa A股数据服务所需的数据库表。

功能：
1. 创建K线数据表 (db_bar_data)
2. 创建股票信息表 (db_stock_info)
3. 显示数据库统计信息

使用方法：
    python scripts/init_database.py

配置：
    通过环境变量或配置文件设置MySQL连接参数
    也可以直接修改本脚本中的默认配置
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_mysql_config():
    """获取MySQL配置

    优先级：环境变量 > 配置文件 > 默认值
    """
    import os

    # 尝试从配置文件读取
    try:
        from vnpy_china_config import ConfigManager
        cfg = ConfigManager()
        global_config = cfg.load_global_config()

        if global_config and hasattr(global_config, "database"):
            db = global_config.database
            print(f"✓ 从配置文件读取MySQL配置")
            return {
                "host": db.mysql_host,
                "port": db.mysql_port,
                "user": db.mysql_user,
                "password": db.mysql_password,
                "database": db.mysql_database,
                "charset": "utf8mb4",
            }
    except Exception as e:
        print(f"⚠️  从配置文件读取失败: {e}")

    # 尝试从环境变量读取
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "vnpy"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "vnpy_china"),
        "charset": "utf8mb4",
    }

    if not config["password"]:
        print("⚠️  警告: MySQL密码未设置")
        print("请通过环境变量 MYSQL_PASSWORD 或配置文件设置密码")

    return config


def test_connection(config):
    """测试数据库连接"""
    try:
        import pymysql
        from pymysql.err import OperationalError

        print("正在测试MySQL连接...")
        print(f"  主机: {config['host']}:{config['port']}")
        print(f"  数据库: {config['database']}")
        print(f"  用户: {config['user']}")

        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        # 测试查询
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()

        cursor.close()
        conn.close()

        print(f"✓ 连接成功 (MySQL {version[0]})")
        return True

    except OperationalError as e:
        error_code = e.args[0]
        error_msg = e.args[1]

        if error_code == 1045:
            print(f"✗ 认证失败: 用户名或密码错误")
        elif error_code == 2003:
            print(f"✗ 连接失败: 无法连接到MySQL服务器")
        elif error_code == 1049:
            print(f"✗ 数据库不存在: {config['database']}")
            print(f"  提示: 请先创建数据库 CREATE DATABASE {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        else:
            print(f"✗ 连接错误 ({error_code}): {error_msg}")

        return False

    except ImportError:
        print("✗ 未安装 pymysql 库")
        print("  安装命令: pip install pymysql")
        return False

    except Exception as e:
        print(f"✗ 连接异常: {e}")
        return False


def create_tables(config):
    """创建数据库表"""
    from vnpy_china_data.database import MySQLDatabaseLayer

    print("\n" + "=" * 70)
    print("开始创建数据库表")
    print("=" * 70)

    # 创建数据库层
    db = MySQLDatabaseLayer(**config)

    # 连接数据库
    if not db.connect():
        print("✗ 数据库连接失败")
        return False

    print("✓ 数据库连接成功")

    # 创建所有表
    success = db.create_all_tables()

    if success:
        print("\n✓ 所有表创建成功")
    else:
        print("\n⚠️  部分表创建失败，请检查日志")

    # 显示统计信息
    stats = db.get_database_stats()
    if stats:
        print("\n" + "=" * 70)
        print("数据库统计信息")
        print("=" * 70)
        print(f"数据库: {stats['database']}")
        print(f"表数量: {stats['table_count']}")
        print(f"总行数: {stats['total_rows']:,}")
        print(f"总大小: {stats['total_size_mb']:.2f} MB ({stats['total_size_gb']:.2f} GB)")

        if stats['tables']:
            print("\n表详情:")
            print(f"{'表名':<30} {'行数':<15} {'大小(MB)':<15} {'说明'}")
            print("-" * 80)
            for table in stats['tables']:
                rows_val = table.get('table_rows') or 0
                rows = f"{rows_val:,}"
                size_val = table.get('size_mb') or 0
                size = f"{size_val:.2f}"
                comment = table.get('table_comment') or '-'
                # 转义 % 字符防止格式化错误
                comment = str(comment).replace('%', '%%')
                print(f"{table['table_name']:<30} {rows:<15} {size:<15} {comment}")

    # 关闭连接
    db.close()

    return success


def main():
    """主函数"""
    print("=" * 70)
    print("VeighNa A股数据服务 - 数据库表初始化")
    print("=" * 70)
    print(f"执行时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 获取配置
    config = get_mysql_config()

    # 测试连接
    if not test_connection(config):
        print("\n" + "=" * 70)
        print("数据库连接测试失败")
        print("=" * 70)
        print("\n请检查:")
        print("1. MySQL服务是否运行")
        print("2. 用户名和密码是否正确")
        print("3. 数据库是否已创建")
        print("4. 网络连接是否正常")
        return

    # 创建表
    success = create_tables(config)

    # 总结
    print("\n" + "=" * 70)
    if success:
        print("✓ 初始化完成！数据库表已成功创建。")
        print("\n下一步:")
        print("1. 下载历史数据: python download_history_data_batch.py")
        print("2. 运行测试脚本: python test_download_history.py")
    else:
        print("⚠️  初始化未完全成功，请检查错误信息。")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n初始化已中断")
    except Exception as e:
        print(f"\n\n初始化出错: {e}")
        import traceback
        traceback.print_exc()
