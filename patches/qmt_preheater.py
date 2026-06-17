# -*- coding: utf-8 -*-
"""
QMT 日线数据预热器：服务端启动时后台增量下载全市场（A股+ETF）日线，
保证 md._get_avg_daily_vol 计算量比时有近 5 日日均量数据可读。

设计文档：docs/superpowers/specs/2026-06-17-qmt-daily-bar-preheater-design.md
"""
import threading
import time
from datetime import datetime, timedelta

from xtquant import xtdata


class QmtDailyBarPreheater:
    """QMT 日线数据预热器：启动时后台增量下载全市场日线。"""

    # 显式列举全部所需板块 + set 去重，不依赖"沪深A股是否含子板块"的假设
    SECTORS: list[str] = ["沪深A股", "创业板", "科创板", "沪深ETF"]
    LOOKBACK_DAYS: int = 30
    BATCH_SIZE: int = 100
    # 批间等待（秒）：实测 download_history_data2 返回即落盘可读，sleep 非为等异步落盘；
    # 保留微小缓冲避免密集请求 miniQMT。真实耗时由下载重写开销主导（实测约 0.05s/只）。
    BATCH_SLEEP: float = 0.2
    # 单批下载超时（秒）：防止个别标的致 download_history_data2 同步阻塞卡死全局。
    # 正常 100 只约 5s，30s 为 6 倍冗余；超时则跳过本批，下次启动增量补。
    BATCH_TIMEOUT: float = 30.0

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
        """下载一批日线，返回是否成功。带超时保护（防止个别标阻塞全局）。

        download_history_data2 是异步 API（返回空 dict {}），但极端情况下
        个别标的可能触发同步等待。用线程隔离 + join(timeout) 兜底。
        """
        result: dict = {"ok": True, "error": None}

        def _do() -> None:
            try:
                xtdata.download_history_data2(
                    stock_list=batch,
                    period="1d",
                    start_time=start_time,
                    callback=lambda: None,
                )
            except Exception as e:
                result["ok"] = False
                result["error"] = e

        t = threading.Thread(target=_do, daemon=True)
        t.start()
        t.join(timeout=self.BATCH_TIMEOUT)

        if t.is_alive():
            self._log(
                f"批次下载超时 {self.BATCH_TIMEOUT}s，"
                f"跳过 {len(batch)} 只（下次启动增量补）"
            )
            return False
        if not result["ok"]:
            self._log(f"批次下载失败（{len(batch)}只）: {result['error']}")
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
