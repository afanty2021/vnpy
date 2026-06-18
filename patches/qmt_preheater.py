# -*- coding: utf-8 -*-
"""
QMT 日线数据预热器：服务端启动时后台增量下载全市场（A股+ETF）日线，
保证 md._get_avg_daily_vol 计算量比时有近 5 日日均量数据可读。

设计文档：docs/superpowers/specs/2026-06-17-qmt-daily-bar-preheater-design.md
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

from xtquant import xtdata


class QmtDailyBarPreheater:
    """QMT 日线数据预热器：启动时后台增量下载全市场日线。"""

    # 显式列举全部所需板块 + set 去重，不依赖"沪深A股是否含子板块"的假设
    SECTORS: list[str] = ["沪深A股", "创业板", "科创板", "沪深ETF"]
    PERIOD: str = "1d"          # 量比只需日线（md._get_avg_daily_vol 消费 1d）
    LOOKBACK_DAYS: int = 30
    BATCH_SIZE: int = 100
    # 批间等待（秒）：子进程退出后再起下一批，留微小缓冲避免密集请求 miniQMT。
    BATCH_SLEEP: float = 0.2
    # 单批下载超时（秒）：每批在独立子进程内执行，超时则 kill 硬杀（OS 级，不受 GIL 限制），
    # 跳过本批下次启动增量补。实测正常批 ~10s + 子进程 setup 2.5s ≈ 12.5s，60s ≈ 5x 冗余
    # （旧线程版 30s/6x 在 GIL 阻塞下兜底失效）；进程隔离后 kill 可靠，冗余可按需收紧。
    BATCH_TIMEOUT: float = 60.0

    def __init__(self, main_engine=None):
        self.main_engine = main_engine

    def _log(self, msg: str) -> None:
        """同时写 stdout 与 main_engine 日志（客户端可见）。

        日志写入 best-effort：main_engine 为 None 或 write_log 失败时静默降级，
        不影响预热主流程（stdout 始终可见）。
        """
        print(f"[preheater] {msg}")
        if self.main_engine is not None:
            try:
                self.main_engine.write_log(msg)
            except Exception:
                pass

    def _collect_symbols(self) -> tuple[list[str], dict[str, set[str]]]:
        """枚举各板块成分并去重。

        前置条件：SECTORS 非空（类常量保证），故 sector_members 必非空。

        Returns:
            (去重排序后的标的列表, {板块名: 成分集合})。后者供 _log_sector_stats
            复用，避免二次调用 get_stock_list_in_sector（DRY）。
        """
        sector_members: dict[str, set[str]] = {}
        for sector in self.SECTORS:
            try:
                members = xtdata.get_stock_list_in_sector(sector_name=sector) or []
            except Exception as e:
                self._log(f"枚举板块 {sector} 失败: {e}")
                members = []
            sector_members[sector] = set(members)
        all_set: set[str] = set().union(*sector_members.values())
        return sorted(all_set), sector_members

    def _log_sector_stats(self, sector_members: dict[str, set[str]]) -> None:
        """打印各板块成分数量与子集关系（运行时实测留痕）。"""
        parts = [f"{s}={len(m)}" for s, m in sector_members.items()]
        a = sector_members.get("沪深A股", set())
        gem = sector_members.get("创业板", set())
        star = sector_members.get("科创板", set())
        total = len(set().union(*sector_members.values()))
        self._log(
            f"板块成分：{' '.join(parts)} | "
            f"创业板⊂沪深A股={gem.issubset(a)} 科创板⊂沪深A股={star.issubset(a)} | "
            f"去重后总数={total}"
        )

    def _calc_start_time(self) -> str:
        """近 LOOKBACK_DAYS 个自然日，格式 YYYYMMDD。end_time 不传（用 API 默认今天）。"""
        start = datetime.now() - timedelta(days=self.LOOKBACK_DAYS)
        return start.strftime("%Y%m%d")

    def _download_batch(self, batch: list[str], start_time: str) -> bool:
        """下载一批日线到独立子进程，返回是否成功。

        fresh-subprocess-per-batch：每批 Popen 一个子进程跑 _worker_main，超时则 kill 硬杀。
        进程隔离保证个别标的触发 download_history_data2 同步阻塞（曾实测卡 1450s）时不会
        拖垮预热线程——线程版 join(timeout) 在子线程独占 GIL 时兜底失效，进程级 kill
        （Windows TerminateProcess）不受 GIL 限制，超时必然生效。失败批次不重试，
        下次启动由 download_history_data2 原生增量下载自动补齐。
        """
        cmd = [
            sys.executable, "-u", os.path.abspath(__file__), "--worker",
            ",".join(batch), self.PERIOD, start_time,
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            self._log(f"启动下载子进程失败（{len(batch)}只）: {e}")
            return False
        try:
            out, err = proc.communicate(timeout=self.BATCH_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.communicate()  # 回收已 kill 的子进程，避免僵尸/管道残留
            except Exception:
                pass
            self._log(
                f"批次下载超时 {self.BATCH_TIMEOUT}s，硬杀子进程，"
                f"跳过 {len(batch)} 只（下次启动增量补）"
            )
            return False

        parsed = _parse_worker_json(out)
        if parsed is None:
            self._log(
                f"批次子进程输出无法解析（{len(batch)}只）: "
                f"stdout={out[:200]!r} stderr={err[:200]!r}"
            )
            return False
        if not parsed.get("ok"):
            self._log(f"批次下载失败（{len(batch)}只）: {parsed.get('error')}")
            return False
        return True

    def preheat(self) -> None:
        """主流程：枚举+留痕 → 分批下载 → 进度 → 汇总。任何异常都不抛出。"""
        try:
            self._log("日线预热开始")
            symbols, sector_members = self._collect_symbols()
            self._log_sector_stats(sector_members)

            total = len(symbols)
            if total == 0:
                self._log("无可预热标的（板块返回空，请检查 miniQMT 是否运行）")
                return

            start_time = self._calc_start_time()
            batches_ok = 0
            batches_fail = 0
            done = 0
            t0 = time.time()

            for i in range(0, total, self.BATCH_SIZE):
                batch = symbols[i:i + self.BATCH_SIZE]
                if self._download_batch(batch, start_time):
                    batches_ok += 1
                else:
                    batches_fail += 1
                done += len(batch)
                self._log(f"日线预热进度 {done}/{total}")
                if i + self.BATCH_SIZE < total:
                    time.sleep(self.BATCH_SLEEP)

            elapsed = self._format_elapsed(time.time() - t0)
            self._log(
                f"日线预热完成：batches_ok={batches_ok} batches_fail={batches_fail} "
                f"symbols={total} elapsed={elapsed}"
            )
        except Exception as e:
            self._log(f"日线预热异常（不影响交易）: {e}")

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        """秒数格式化为 NmNs（机器友好）。"""
        s = int(seconds)
        return f"{s // 60}m{s % 60}s"


def _parse_worker_json(stdout: bytes) -> dict | None:
    """解析子进程 stdout，取最后一行 JSON（跳过 banner/非 JSON 行）。无则 None。"""
    try:
        text = stdout.decode("utf-8", "ignore")
    except Exception:
        return None
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                continue
    return None


def _worker_main(argv: list[str] | None = None) -> None:
    """子进程入口：下载一批日线，输出一行 JSON {ok, error, elapsed} 到 stdout。

    argv: ["--worker", "<symbols 逗号分隔>", "<period>", "<start_time>"]。
    父进程 Popen 调 `python qmt_preheater.py --worker ...` 触发本函数。
    任何异常都捕获并写入 JSON（ok=false），保证父进程总能解析到结果。
    """
    argv = sys.argv[1:] if argv is None else argv
    symbols = argv[1].split(",") if len(argv) > 1 and argv[1] else []
    period = argv[2] if len(argv) > 2 else "1d"
    start_time = argv[3] if len(argv) > 3 else ""

    result: dict = {"ok": True, "error": None, "elapsed": 0.0}
    t0 = time.time()
    try:
        xtdata.enable_hello = False  # 静默 banner，保持 stdout 纯 JSON
        xtdata.connect()
        xtdata.download_history_data2(symbols, period, start_time)
    except Exception as e:
        result["ok"] = False
        result["error"] = repr(e)
    result["elapsed"] = round(time.time() - t0, 2)

    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    # 子进程入口：python qmt_preheater.py --worker <symbols> <period> <start_time>
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker_main()
