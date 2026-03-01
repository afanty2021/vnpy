#!/usr/bin/env python3
"""
检查MySQL数据库中的QMT历史数据
"""

import pymysql
from datetime import datetime
import sys

# MySQL配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "vnpy",
    "password": "Vnpy2024!",
    "database": "vnpy_china",
    "charset": "utf8mb4",
}

def check_database():
    """检查数据库中的数据"""

    print("\n" + "="*70)
    print(" QMT历史数据检查")
    print("="*70)

    try:
        # 连接数据库
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # 1. 查看所有表
        print("\n[1] 数据库表列表:")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")

        # 2. 检查K线数据
        print("\n[2] K线数据统计:")
        cursor.execute("""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT symbol) as unique_symbols,
                MIN(`datetime`) as min_date,
                MAX(`datetime`) as max_date
            FROM db_bar_data
        """)
        result = cursor.fetchone()
        if result:
            print(f"  总记录数: {result[0]:,}")
            print(f"  股票数量: {result[1]:,}")
            print(f"  日期范围: {result[2]} ~ {result[3]}")

        # 3. 按 Interval 分组统计
        print("\n[3] 按K线类型统计:")
        cursor.execute("""
            SELECT
                `interval`,
                COUNT(*) as count,
                COUNT(DISTINCT symbol) as symbols
            FROM db_bar_data
            GROUP BY `interval`
            ORDER BY `interval`
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:8} : {row[1]:8,} 条记录, {row[2]:4} 只股票")

        # 4. 查看最近的股票代码
        print("\n[4] 股票代码示例 (前20个):")
        cursor.execute("""
            SELECT DISTINCT symbol
            FROM db_bar_data
            ORDER BY symbol
            LIMIT 20
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}", end="")
        print()

        # 5. 数据质量检查
        print("\n[5] 数据质量检查:")
        cursor.execute("""
            SELECT
                COUNT(*) as missing_close
            FROM db_bar_data
            WHERE close_price IS NULL
               OR open_price IS NULL
               OR high_price IS NULL
               OR low_price IS NULL
        """)
        missing = cursor.fetchone()[0]
        print(f"  缺失价格数据的记录: {missing}")

        cursor.close()
        conn.close()

        print("\n✓ 数据库检查完成")
        return True

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        return False

if __name__ == "__main__":
    check_database()
