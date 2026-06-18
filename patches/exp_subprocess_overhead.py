# -*- coding: utf-8 -*-
"""
Plan-A subprocess per-batch overhead probe.

Question: if qmt_preheater delegates each batch to a fresh subprocess (so a
stuck download can be hard-killed at the OS level), what is the per-batch
setup cost?

Decomposes ONE subprocess invocation into:
  - t_spawn   : python interpreter startup (measured as residual = total - phases)
  - t_import  : import xtquant (C extension load)
  - t_connect : xtdata.connect() to miniQMT
  - t_download: download_history_data2 (incremental, floor value)

Runs the subprocess N times SERIALLY (one at a time). This also validates that
serial subprocess delegation connects + downloads stably -- the actual usage
pattern in Plan-A. (Concurrent spawning was already shown unreliable by
exp_process_download.py.)

Single file, two modes: parent runs the loop; child triggered via --worker.
Child prints one JSON line; output is ASCII to dodge console GBK garbling.
"""
import sys
import time
import json
import subprocess

PYTHON = sys.executable
SYMBOLS = ["000001.SZ", "000002.SZ", "000333.SZ", "600519.SH", "510300.SH"]
PERIOD = "1d"
START = "20260519"
N_RUNS = 3
CHILD_TIMEOUT = 120  # seconds per child


def worker():
    """Child entry: emit one JSON line of phase timings on stdout."""
    t0 = time.time()
    from xtquant import xtdata
    t_import = time.time() - t0

    xtdata.enable_hello = False  # silence banner so stdout stays clean JSON
    t0 = time.time()
    xtdata.connect()
    t_connect = time.time() - t0

    t0 = time.time()
    xtdata.download_history_data2(SYMBOLS, PERIOD, START)
    t_download = time.time() - t0

    sys.stdout.write(json.dumps({
        "t_import": round(t_import, 3),
        "t_connect": round(t_connect, 3),
        "t_download": round(t_download, 3),
    }) + "\n")
    sys.stdout.flush()


def run_one():
    """Spawn one child, measure total wall, parse its phase JSON."""
    cmd = [PYTHON, "-u", __file__, "--worker"]
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = proc.communicate(timeout=CHILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return None, None, "TIMEOUT(>%ds)" % CHILD_TIMEOUT
    t_total = time.time() - t0

    parsed = None
    for line in out.decode("utf-8", "ignore").splitlines()[::-1]:
        line = line.strip()
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                break
            except Exception:
                pass
    if parsed is None:
        snippet = (out[:200] + b" |ERR| " + err[:200]).decode("utf-8", "ignore")
        return t_total, None, "PARSE_FAIL: %r" % snippet
    return t_total, parsed, None


def main():
    print("subprocess per-batch overhead probe (serial, %d runs)" % N_RUNS)
    print("PYTHON=%s SYMBOLS=%d PERIOD=%s START=%s\n"
          % (PYTHON, len(SYMBOLS), PERIOD, START))

    rows = []
    for i in range(N_RUNS):
        t_total, ph, err = run_one()
        if err:
            print("run#%d: ERROR %s" % (i, err))
            continue
        t_phases = ph["t_import"] + ph["t_connect"] + ph["t_download"]
        t_spawn = t_total - t_phases
        rows.append((t_total, ph["t_import"], ph["t_connect"],
                     ph["t_download"], t_spawn))
        print("run#%d: total=%.2fs  import=%.2fs  connect=%.2fs  "
              "download=%.2fs  spawn(residual)=%.2fs"
              % (i, t_total, ph["t_import"], ph["t_connect"],
                 ph["t_download"], t_spawn))

    if not rows:
        print("\nno successful runs")
        return

    n = len(rows)
    avg = lambda k: sum(r[k] for r in rows) / n
    tot_avg = avg(0); imp_avg = avg(1); con_avg = avg(2)
    dl_avg = avg(3); sp_avg = avg(4)
    setup = sp_avg + imp_avg + con_avg

    print("\n=== averages over %d runs ===" % n)
    print("  spawn (python startup) : %.2fs" % sp_avg)
    print("  import xtquant         : %.2fs" % imp_avg)
    print("  connect miniQMT        : %.2fs" % con_avg)
    print("  download (incremental) : %.2fs" % dl_avg)
    print("  setup subtotal         : %.2fs   <- per-batch tax if each batch "
          "is a fresh subprocess" % setup)
    print("  total per invocation   : %.2fs" % tot_avg)

    print("\n=== extrapolation to preheater (69 batches) ===")
    print("  extra setup cost if EVERY batch is a fresh subprocess: "
          "%.0f s = %.1f min" % (setup * 69, setup * 69 / 60))
    print("  current serial download baseline ~ 11 min (no isolation)")
    print("  => Plan-A fresh-subprocess-per-batch total ~ %.1f min"
          % (setup * 69 / 60 + 11))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker()
    else:
        main()
