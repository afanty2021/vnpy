#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量下载 A 股和港股通近 5 年日线数据（完整版）

支持断点续传，自动跳过已下载的股票。
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Tuple, Set, Dict
import time

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy.trader.constant import Exchange, Interval
from vnpy_china_data.service import ChinaDataService


def get_all_a_stocks(service: ChinaDataService) -> List[Tuple[str, Exchange, str]]:
    """获取所有 A 股股票

    Returns:
        [(代码，交易所，名称), ...]
    """
    print("=" * 70)
    print("步骤 1: 获取 A 股股票列表")
    print("=" * 70)

    try:
        stock_list = service.get_stock_list(list_status="L")
        a_stocks = []

        for stock in stock_list:
            ts_code = stock.get("ts_code", "")
            name = stock.get("name", "")
            market = stock.get("market", "")

            if market in ["主板", "科创板", "创业板", "北交所"]:
                if "." in ts_code:
                    code, exchange_str = ts_code.split(".")
                    exchange = Exchange.SSE if exchange_str == "SH" else Exchange.SZSE
                    a_stocks.append((code, exchange, name))

        print(f"✓ A 股总数：{len(a_stocks)} 只")
        return a_stocks

    except Exception as e:
        print(f"✗ 获取 A 股列表失败：{e}")
        return []


def get_hk_stocks(service: ChinaDataService) -> List[Tuple[str, Exchange, str]]:
    """获取港股通股票

    Returns:
        [(代码，交易所，名称), ...]
    """
    print("\n" + "=" * 70)
    print("步骤 2: 获取港股通股票列表")
    print("=" * 70)

    try:
        hk_symbols = service.database.get_hk_connect_symbols()
        hk_stocks = []

        for symbol in hk_symbols:
            if "." in symbol:
                code, _ = symbol.split(".")
                hk_stocks.append((code, Exchange.SEHK, f"{code}.HK"))

        print(f"✓ 港股通总数：{len(hk_stocks)} 只")
        return hk_stocks

    except Exception as e:
        print(f"✗ 获取港股通列表失败：{e}")
        return []


def get_downloaded_stocks(service: ChinaDataService) -> Set[str]:
    """获取已下载的股票集合

    Returns:
        {"code.exchange": ...}
    """
    downloaded = set()

    try:
        # 使用连接池获取连接（上下文管理器）
        with service.database.get_connection() as conn:
            cursor = conn.cursor()
            # 获取所有不同的 symbol+exchange 组合
            cursor.execute("""
                SELECT DISTINCT symbol, exchange FROM db_bar_data
            """)
            for row in cursor.fetchall():
                downloaded.add(f"{row[0]}.{row[1]}")
            cursor.close()

        print(f"✓ 已下载股票：{len(downloaded)} 只")

    except Exception as e:
        print(f"✗ 获取已下载股票失败：{e}")

    return downloaded


def download_stock(
    service: ChinaDataService,
    code: str,
    exchange: Exchange,
    name: str,
    start_date: date,
    end_date: date
) -> Tuple[bool, int]:
    """下载单只股票数据

    Returns:
        (是否成功，K 线数量)
    """
    try:
        bars = service.download_bar_data(
            symbol=code,
            exchange=exchange,
            interval=Interval.DAILY,
            start=datetime.combine(start_date, datetime.min.time()),
            end=datetime.combine(end_date, datetime.min.time())
        )

        if bars:
            service.database.save_bar_data(bars)
            return (True, len(bars))
        else:
            return (False, 0)

    except Exception as e:
        return (False, 0)


def main():
    print("=" * 70)
    print("批量下载 A 股和港股通近 5 年日线数据（完整版）")
    print("=" * 70)

    # 时间范围
    end_date = date.today()
    start_date = end_date - timedelta(days=5*365)

    print(f"\n时间范围：{start_date} 至 {end_date}")
    print(f"K 线周期：日线")
    print(f"断点续传：支持\n")

    # 初始化
    service = ChinaDataService()
    service.connect()
    print("✓ 数据源连接成功\n")

    # 获取股票列表
    a_stocks = get_all_a_stocks(service)
    hk_stocks = get_hk_stocks(service)
    all_stocks = a_stocks + hk_stocks

    # 获取已下载的股票
    downloaded = get_downloaded_stocks(service)

    # 筛选需要下载的股票
    to_download = []
    for code, exchange, name in all_stocks:
        key = f"{code}.{exchange.value}"
        if key not in downloaded:
            to_download.append((code, exchange, name))

    print(f"✓ 需要下载：{len(to_download)} 只\n")

    if not to_download:
        print("✓ 所有股票已下载完成！")
        service.disconnect()
        return

    # 批量下载
    print("=" * 70)
    print("开始批量下载")
    print("=" * 70)

    result = {"success": 0, "failed": 0, "total_bars": 0, "skipped": len(downloaded)}
    failed_stocks = []  # 记录失败的股票
    start_time = time.time()

    for i, (code, exchange, name) in enumerate(to_download, 1):
        elapsed = time.time() - start_time
        progress = i / len(to_download) * 100
        eta = (elapsed / i) * (len(to_download) - i) / 60 if i > 0 else 0

        # 每 10 只或最后显示进度
        if i % 10 == 0 or i == 1 or i == len(to_download):
            print(f"[{i}/{len(to_download)}] ({progress:.1f}%) - "
                  f"成功 {result['success']} 只，"
                  f"失败 {result['failed']} 只，"
                  f"{result['total_bars']:,} 条，"
                  f"预计剩余 {eta:.0f} 分钟")

        success, bar_count = download_stock(service, code, exchange, name, start_date, end_date)

        if success:
            result["success"] += 1
            result["total_bars"] += bar_count
        else:
            result["failed"] += 1
            # 记录失败的股票
            failed_stocks.append({
                "code": code,
                "exchange": exchange.value,
                "name": name
            })

        # 限流
        time.sleep(0.1)

    # 总结
    print("\n" + "=" * 70)
    print("下载总结")
    print("=" * 70)
    print(f"  总股票数：{len(all_stocks)} 只")
    print(f"  已下载（本次前）: {result['skipped']} 只")
    print(f"  本次下载成功：{result['success']} 只")
    print(f"  本次下载失败：{result['failed']} 只")
    print(f"  新增 K 线数：{result['total_bars']:,} 条")

    # 失败股票统计
    if failed_stocks:
        print(f"\n失败股票详情 ({len(failed_stocks)} 只):")
        print("-" * 70)

        # 按交易所分组统计
        by_exchange: Dict[str, List[Dict]] = {}
        for stock in failed_stocks:
            exch = stock["exchange"]
            if exch not in by_exchange:
                by_exchange[exch] = []
            by_exchange[exch].append(stock)

        # 显示每个交易所的失败数量
        for exch, stocks in sorted(by_exchange.items()):
            print(f"  {exch}: {len(stocks)} 只")

        # 显示前 20 只失败股票
        print("\n失败股票列表（前20只）:")
        for i, stock in enumerate(failed_stocks[:20], 1):
            print(f"  {i}. {stock['code']}.{stock['exchange']} ({stock['name']})")

        if len(failed_stocks) > 20:
            print(f"  ... 还有 {len(failed_stocks) - 20} 只")

        # 将失败股票保存到文件
        failed_file = Path(__file__).parent / "failed_stocks.txt"
        with open(failed_file, "w", encoding="utf-8") as f:
            f.write(f"# 批量下载失败股票列表\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 总数: {len(failed_stocks)} 只\n\n")
            for stock in failed_stocks:
                f.write(f"{stock['code']}.{stock['exchange']},{stock['name']}\n")
        print(f"\n失败股票列表已保存到: {failed_file}")

    # 数据库统计
    stats = service.database.get_database_stats()
    if stats:
        print(f"\n数据库统计:")
        print(f"  总行数：{stats['total_rows']:,}")
        print(f"  总大小：{stats['total_size_mb']:.2f} MB")

    service.disconnect()
    print("\n✓ 下载任务完成！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n下载已中断")
    except Exception as e:
        print(f"\n\n下载出错：{e}")
        import traceback
        traceback.print_exc()
