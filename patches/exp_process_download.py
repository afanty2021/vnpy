# -*- coding: utf-8 -*-
"""
Process-isolated parallel download experiment (validates Plan-1).

Why: multithreaded sharing of the global xtdata __client deadlocks (see
exp_parallel_download.py: serial 0.6s vs multithread hung >85s). Each process
owns an independent __client, so there is no shared-state contention, and a
stuck worker can be hard-terminated at the OS level (not GIL-limited).

Checks:
  - 3 worker processes run concurrently without deadlock.
  - Each connects its own client to the same miniQMT (multi-connection already
    proven feasible by the 2nd-client connect in the threaded experiment).
  - Rough speedup vs serial (incremental-cache caveat applies: all symbols are
    already local, so absolute times are floor values, not real download cost).

Note: output is ASCII to avoid console GBK garbling.
"""
import time
from datetime import datetime, timedelta
from multiprocessing import Process, Queue

PERIOD = "1d"
START = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

# three disjoint groups; each proc owns its set
GROUP_A = ["000001.SZ", "000002.SZ", "000333.SZ", "000858.SZ"]
GROUP_B = ["600000.SH", "600036.SH", "600519.SH", "600276.SH"]
GROUP_C = ["510050.SH", "510300.SH", "159915.SZ", "002594.SZ"]
GROUPS = [GROUP_A, GROUP_B, GROUP_C]
JOIN_TIMEOUT = 60  # per-process join timeout (s)


def worker(name, chunk, q):
    try:
        from xtquant import xtdata
        xtdata.connect()
        t0 = time.time()
        ret = xtdata.download_history_data2(chunk, PERIOD, START)
        keys = list(ret.keys()) if isinstance(ret, dict) else ret
        q.put((name, "ok", round(time.time() - t0, 2), keys))
    except Exception as e:
        q.put((name, "err", -1, repr(e)))


def main():
    print(f"PERIOD={PERIOD} START={START} groups={len(GROUPS)}")

    from xtquant import xtdata
    xtdata.connect()

    # serial baseline (main process, all 12 at once)
    all_s = GROUP_A + GROUP_B + GROUP_C
    t0 = time.time()
    xtdata.download_history_data2(all_s, PERIOD, START)
    s_wall = time.time() - t0
    print(f"[serial]      {len(all_s)} syms -> {s_wall:.2f}s")

    # parallel: 3 processes, each independent client
    q = Queue()
    procs = [Process(target=worker, args=(f"P{i}", g, q), name=f"P{i}")
             for i, g in enumerate(GROUPS)]
    t0 = time.time()
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=JOIN_TIMEOUT)
    p_wall = time.time() - t0

    alive = [p.name for p in procs if p.is_alive()]
    for p in procs:
        if p.is_alive():
            p.terminate()
    print(f"[parallel-3p] wall={p_wall:.2f}s still_alive={alive or 'none'}")

    results = []
    while not q.empty():
        results.append(q.get())
    for r in sorted(results):
        print(f"  {r}")

    print(f"speedup        = {s_wall / p_wall:.2f}x (incremental cache caveat)")
    print(f"deadlock-free  = {'YES' if not alive else 'NO'}")


if __name__ == "__main__":
    main()
