# -*- coding: utf-8 -*-
"""
多线程并行下载实验：探查 xtdata.download_history_data2 的并发安全性 / 加速比 / 多连接可行性。

背景：
  qmt_preheater 当前串行分批下载全市场日线（实测 ~10s/批，69 批约 11 分钟，
  叠加一次 GIL 卡死膨胀到 34 分钟）。本实验回答三件事：

  1. 并发安全：多线程同时调 download_history_data2 时，各线程返回的 status（含每只
     start/end_time 的 dict）是否只含本线程输入的标的（即 on_progress 回调不串台）。
  2. 加速比：并行 vs 串行的墙钟对比（注意：增量下载场景下命中本地缓存会很快，
     加速比仅供参考；若想测真实下载耗时差异需换未缓存的周期/历史）。
  3. 多连接：本脚本作为独立进程连 miniQMT（与服务端第二个连接），能跑通即说明
     "多客户端连同一 miniQMT" 可行 —— 这是进程隔离方案的前置条件。

前置：miniQMT 已运行（127.0.0.1:58610）。下载为增量，只增不破坏本地数据。
"""
import time
import threading
from datetime import datetime, timedelta

from xtquant import xtdata


# 12 只活跃标的（A股+ETF）。串行/并行各用一半，避免一组下完另一组命中缓存。
ALL_SYMBOLS = [
    "000001.SZ", "000002.SZ", "000333.SZ", "000858.SZ", "002594.SZ", "600000.SH",
    "600036.SH", "600519.SH", "600276.SH", "510050.SH", "510300.SH", "159915.SZ",
]
SERIAL_SYMBOLS = ALL_SYMBOLS[:6]
PARALLEL_SYMBOLS = ALL_SYMBOLS[6:]

PERIOD = "1d"
START = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
N_THREADS = 3


def chunked(lst, n):
    """均分列表为 n 块（余数依次补给前几块）。"""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def verify_local(symbols):
    """验证每只能否从本地读到近 5 日日线（落盘正确性兜底）。"""
    ok, miss = [], []
    for s in symbols:
        try:
            data = xtdata.get_local_data(field_list=[], stock_list=[s],
                                         period=PERIOD, count=5)
            bars = data.get(s) if isinstance(data, dict) else None
            (ok if bars is not None and len(bars) > 0 else miss).append(s)
        except Exception:
            miss.append(s)
    return ok, miss


def run_serial(symbols):
    """串行：一次性提交全部标的。返回 (墙钟, 返回值)。"""
    t0 = time.time()
    ret = xtdata.download_history_data2(symbols, PERIOD, START)
    return time.time() - t0, ret


def run_parallel(symbols, n_threads):
    """并行：n 个线程各下一块。返回 (墙钟, [每线程返回值], [每线程异常], [每线程耗时])。"""
    chunks = chunked(symbols, n_threads)
    rets = [None] * n_threads
    errs = [None] * n_threads
    tels = [0.0] * n_threads

    def worker(i, chunk):
        t0 = time.time()
        try:
            rets[i] = xtdata.download_history_data2(chunk, PERIOD, START)
        except Exception as e:
            errs[i] = repr(e)
        tels[i] = time.time() - t0

    threads = [threading.Thread(target=worker, args=(i, c), name=f"dl-{i}")
               for i, c in enumerate(chunks)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.time() - t0, rets, errs, tels, chunks


def keys_of(ret):
    """download_history_data2 返回 status[4]：{标的: {start_time,end_time,...}}。"""
    return list(ret.keys()) if isinstance(ret, dict) else ret


def main():
    print("连接 miniQMT（本进程即第 2 个客户端）...")
    xtdata.connect()
    print(f"周期={PERIOD} start={START} 线程数={N_THREADS}")

    # ---- 串行基线 ----
    print(f"\n[1] 串行基线：一次性 {len(SERIAL_SYMBOLS)} 只 -> {SERIAL_SYMBOLS}")
    s_wall, s_ret = run_serial(SERIAL_SYMBOLS)
    print(f"    耗时 {s_wall:.2f}s | 返回 keys={keys_of(s_ret)}")

    # ---- 并行 ----
    print(f"\n[2] 并行：{N_THREADS} 线程各下 {len(PARALLEL_SYMBOLS)//N_THREADS} 只")
    p_wall, p_rets, p_errs, p_tels, chunks = run_parallel(PARALLEL_SYMBOLS, N_THREADS)
    for i in range(N_THREADS):
        print(f"    worker{i} 输入={chunks[i]} 耗时={p_tels[i]:.2f}s "
              f"返回keys={keys_of(p_rets[i])} err={p_errs[i]}")

    # ---- 串台判据 ----
    print("\n[3] 串台判据：worker 返回的标的应仅含本线程输入")
    safe = True
    for i in range(N_THREADS):
        ret = p_rets[i]
        if isinstance(ret, dict):
            extra = set(ret.keys()) - set(chunks[i])
            missing = set(chunks[i]) - set(ret.keys())
            if extra:
                safe = False
            print(f"    worker{i}: {'OK' if not extra else '!!串台!!'} "
                  f"extra={sorted(extra) or '-'} missing={sorted(missing) or '-'}")
        else:
            print(f"    worker{i}: 返回非 dict({ret})，无法判定串台")
    crashed = any(p_errs)
    print(f"    => 并发{'安全' if safe and not crashed else '不安全/有异常'}")

    # ---- 加速比 ----
    print(f"\n[4] 加速比：串行 {s_wall:.2f}s / 并行 {p_wall:.2f}s = "
          f"{s_wall/p_wall:.2f}x（增量命中缓存时此值不反映真实下载差异）")

    # ---- 落盘验证 ----
    print("\n[5] 本地落盘验证（get_local_data count=5，覆盖全部 12 只）")
    ok, miss = verify_local(ALL_SYMBOLS)
    print(f"    可读 {len(ok)}/{len(ALL_SYMBOLS)} | 缺失={miss or '-'}")

    # ---- 结论 ----
    print("\n=== 结论 ===")
    print(f"  多连接可行（本进程作为第2客户端跑通）: 是")
    print(f"  并发安全（无串台/无异常）           : {'是' if safe and not crashed else '否'}")
    print(f"  加速有效（>1.3x）                   : "
          f"{'是' if s_wall/p_wall > 1.3 else '不明显（增量太快测不准）'}")


if __name__ == "__main__":
    main()
