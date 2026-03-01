#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查历史数据下载进度
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy.trader.constant import Interval
from vnpy_china_data.service import ChinaDataService


def main():
    """主函数"""
    print("=" * 70)
    print("历史数据下载进度检查")
    print("=" * 70)

    service = ChinaDataService()

    try:
        service.connect()
        print("✓ 数据库连接成功\n")
    except Exception as e:
        print(f"✗ 数据库连接失败：{e}")
        return

    # 获取数据库统计
    stats = service.database.get_database_stats()
    if stats:
        print("数据库概览:")
        print(f"  数据库名：{stats['database']}")
        print(f"  表数量：{stats['table_count']}")
        print(f"  总行数：{stats['total_rows']:,}")
        print(f"  总大小：{stats['total_size_mb']:.2f} MB\n")

        if 'tables' in stats:
            print("表详情:")
            for table in stats['tables']:
                print(f"  {table['table_name']}:")
                print(f"    行数：{table.get('table_rows', 0):,}")
                print(f"    大小：{table.get('data_length_mb', 0):.2f} MB")
            print()

    # 获取已下载股票统计
    try:
        cursor = service.database._connection.cursor()
        cursor.execute("""
            SELECT exchange, COUNT(DISTINCT symbol) as stock_count, COUNT(*) as bar_count
            FROM db_bar_data
            WHERE `interval` = 'd'
            GROUP BY exchange
        """)
        rows = cursor.fetchall()
        cursor.close()

        print("已下载股票统计 (日线):")
        total_stocks = 0
        for row in rows:
            exchange, stock_count, bar_count = row
            # exchange 可能是字符串或 Exchange 枚举
            exchange_name = exchange.value if hasattr(exchange, 'value') else exchange
            print(f"  {exchange_name}: {stock_count:,} 只 ({bar_count:,} 条 K 线)")
            total_stocks += stock_count
        print(f"  合计：{total_stocks:,} 只")
        print()

        # 获取数据日期范围
        cursor = service.database._connection.cursor()
        cursor.execute("""
            SELECT MIN(datetime), MAX(datetime)
            FROM db_bar_data
            WHERE `interval` = 'd'
        """)
        date_range = cursor.fetchone()
        cursor.close()

        if date_range and date_range[0]:
            print("数据日期范围:")
            print(f"  最早：{date_range[0].date()}")
            print(f"  最晚：{date_range[1].date() if date_range[1] else 'N/A'}")
            print()

    except Exception as e:
        print(f"获取统计信息失败：{e}")

    service.disconnect()
    print("✓ 检查完成")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n出错：{e}")
        import traceback
        traceback.print_exc()
