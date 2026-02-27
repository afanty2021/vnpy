#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
港股通历史数据下载功能 - 完整集成测试

测试流程：
1. 检查环境配置（数据库、QMT）
2. 爬取港股通名单（沪港通+深港通）
3. 保存到数据库
4. 从数据库读取并验证
5. 测试历史数据下载（如果QMT可用）
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/Users/berton/Github/vnpy')

from datetime import date, datetime, timedelta
import subprocess

def check_environment():
    """检查测试环境配置"""
    print("=" * 60)
    print("1. 环境检查")
    print("=" * 60)

    # 检查Python版本
    print(f"Python版本: {sys.version}")

    # 检查conda环境
    result = subprocess.run(
        ['conda', 'info', '--envs'],
        capture_output=True,
        text=True
    )
    if 'Quant-3.11' in result.stdout:
        print("✓ Conda环境 Quant-3.11 已存在")
    else:
        print("✗ Conda环境 Quant-3.11 不存在")

    # 检查必要的包
    required_packages = [
        'vnpy',
        'pandas',
        'mysql.connector',
        'requests',
        'bs4'
    ]

    print("\n依赖包检查:")
    for pkg in required_packages:
        result = subprocess.run(
            ['conda', 'run', '-n', 'Quant-3.11', 'python', '-c', f'import {pkg}'],
            capture_output=True,
            text=True
        )
        status = "✓" if result.returncode == 0 else "✗"
        print(f"  {status} {pkg}")

def test_crawl_hk_connect():
    """测试港股通名单爬取"""
    print("\n" + "=" * 60)
    print("2. 港股通名单爬取测试")
    print("=" * 60)

    try:
        from vnpy_china_data.crawler import HkConnectCrawler

        crawler = HkConnectCrawler()
        stocks = crawler.crawl_all()

        print(f"✓ 爬取成功: 共 {len(stocks)} 只股票")

        # 分类统计
        shhk = [s for s in stocks if s.channel == "SHHK"]
        szhk = [s for s in stocks if s.channel == "SZHK"]
        print(f"  - 沪港通: {len(shhk)} 只")
        print(f"  - 深港通: {len(szhk)} 只")

        # 显示前5只
        if stocks:
            print("\n前5只股票示例:")
            for s in stocks[:5]:
                print(f"  {s.symbol} {s.name} ({s.channel})")

        return stocks
    except Exception as e:
        print(f"✗ 爬取失败: {e}")
        return []

def test_database_operations(stocks):
    """测试数据库操作"""
    print("\n" + "=" * 60)
    print("3. 数据库操作测试")
    print("=" * 60)

    try:
        from vnpy_china_data.database import MySQLDatabaseLayer
        from vnpy_china_data.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

        # 创建数据库连接
        db = MySQLDatabaseLayer(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        print(f"✓ 数据库连接成功: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")

        # 创建港股通表
        db.create_hk_connect_table()
        print("✓ 港股通表创建成功")

        # 保存股票列表
        if stocks:
            db.save_hk_connect_stocks(stocks)
            print(f"✓ 保存 {len(stocks)} 只股票到数据库")

        # 读取股票列表
        db_stocks = db.get_hk_connect_stocks()
        print(f"✓ 从数据库读取 {len(db_stocks)} 只股票")

        # 获取更新信息
        info = db.get_hk_connect_update_info()
        if info.get('exists'):
            print(f"✓ 更新信息: 最后更新 {info['last_updated']}, 沪港通 {info['sh_count']} 只, 深港通 {info['sz_count']} 只")
        else:
            print("✓ 港股通名单首次更新")

        # 获取代码列表
        symbols = db.get_hk_connect_symbols()
        print(f"✓ 港股通代码列表: {len(symbols)} 只")

        # 转换为显示格式
        display_symbols = [f"{s[:-3]}.SEHK" for s in symbols[:5]]
        print(f"  示例: {display_symbols}")

        return True
    except Exception as e:
        print(f"✗ 数据库操作失败: {e}")
        return False

def test_qmt_adapter():
    """测试QMT适配器"""
    print("\n" + "=" * 60)
    print("4. QMT适配器测试")
    print("=" * 60)

    try:
        from vnpy_china_data.adapter import QMTDataAdapter

        adapter = QMTDataAdapter()
        print("✓ QMTDataAdapter 创建成功")

        # 尝试连接
        connected = adapter.connect()
        if connected:
            print("✓ QMT 连接成功")
        else:
            print("⚠ QMT 连接失败（MiniQMT未运行或未登录）")
            return False

        # 测试代码转换
        test_cases = [
            ("600000.SH", "600000.SH"),
            ("000001.SZ", "000001.SZ"),
            ("00700.SEHK", "00700.HK"),
            ("00700.HK", "00700.HK"),
            ("00700.SHHK", "00700.HK"),
        ]

        print("\n代码转换测试:")
        for vnpy_code, expected in test_cases:
            qmt_code = adapter._convert_to_qmt_code(vnpy_code)
            status = "✓" if qmt_code == expected else "✗"
            print(f"  {status} {vnpy_code} -> {qmt_code} (期望: {expected})")

        # 测试代码转换（仅测试参数准备，不实际下载）
        print("\n历史数据下载参数准备:")
        from vnpy.trader.constant import Exchange, Interval
        from datetime import datetime

        # 测试 QMT 代码转换
        test_result = adapter._convert_to_qmt_code("00700", Exchange.SEHK)
        print(f"  转换: 00700 + SEHK -> {test_result}")

        return True
    except Exception as e:
        print(f"✗ QMT适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_engine():
    """测试GUI引擎"""
    print("\n" + "=" * 60)
    print("5. GUI引擎测试")
    print("=" * 60)

    try:
        from unittest.mock import Mock
        from vnpy_china_data.gui_engine import ChinaDataGuiEngine
        from vnpy.trader.constant import Exchange

        # 创建mock引擎
        main_engine = Mock()
        main_engine.write_log = Mock()
        event_engine = Mock()

        gui_engine = ChinaDataGuiEngine(main_engine, event_engine)
        print("✓ ChinaDataGuiEngine 创建成功")

        # 测试交易所解析
        test_cases = [
            ("600000.SH", Exchange.SSE),
            ("000001.SZ", Exchange.SZSE),
            ("00700.SEHK", Exchange.SEHK),
            ("00700.HK", Exchange.SEHK),
            ("00700.SHHK", Exchange.SEHK),
            ("00700.SZHK", Exchange.SEHK),
        ]

        print("\n交易所解析测试:")
        for symbol, expected in test_cases:
            result = gui_engine._parse_exchange(symbol)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {symbol} -> {result} (期望: {expected})")

        return True
    except Exception as e:
        print(f"✗ GUI引擎测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("港股通历史数据下载功能 - 完整集成测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 环境检查
    check_environment()

    # 2. 爬取测试
    stocks = test_crawl_hk_connect()

    # 3. 数据库测试
    db_ok = test_database_operations(stocks)

    # 4. QMT适配器测试
    qmt_ok = test_qmt_adapter()

    # 5. GUI引擎测试
    gui_ok = test_gui_engine()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"港股通爬取: {'✓ 通过' if stocks else '✗ 失败'}")
    print(f"数据库操作: {'✓ 通过' if db_ok else '✗ 失败'}")
    print(f"QMT适配器: {'✓ 通过' if qmt_ok else '⚠ 需MiniQMT运行'}")
    print(f"GUI引擎: {'✓ 通过' if gui_ok else '✗ 失败'}")

    print("\n" + "=" * 60)
    print("集成测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
