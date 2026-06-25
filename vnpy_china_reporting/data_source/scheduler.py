"""
每日定时调度器

基于墙钟（datetime.now()）短轮询实现每日固定时刻触发回调，用于权益快照
落库等定时任务。由 vnpy 主进程启动时实例化并 start()，主进程退出时 stop()。

为何用墙钟轮询而非 threading.Event.wait(timeout) 的长等待：
    Event.wait 的超时基于 time.monotonic()，系统睡眠/休眠期间单调时钟
    冻结，长等待的真实返回时刻会被推迟等量的睡眠时长——client 常驻但下午
    电脑睡眠时，18:30 的触发会被无限推后，导致权益快照漏落库。改用墙钟
    每分钟轮询：进程从睡眠唤醒后，墙钟立即跳回真实时间，下一次轮询即可
    补判"已过 18:30"并触发，对系统睡眠鲁棒。

示例（每日 18:30 落库权益快照）：
    scheduler = DailyScheduler("18:30", callback=lambda: collector.collect())
    scheduler.start()
"""

import threading
import datetime
import logging
from typing import Callable, Optional, Set

logger = logging.getLogger(__name__)


class DailyScheduler:
    """每日定时触发器（墙钟短轮询，后台守护线程）"""

    # 周末 weekday：5=周六, 6=周日
    _WEEKEND = {5, 6}

    def __init__(
        self,
        target_time: str = "18:30",
        callback: Optional[Callable[[], None]] = None,
        skip_weekend: bool = True,
        poll_interval: float = 60.0,
    ):
        """
        Args:
            target_time: 每日触发时刻，格式 "HH:MM"
            callback: 触发回调（无参）
            skip_weekend: 是否跳过周六日（A股非交易日，默认跳过）
            poll_interval: 轮询间隔秒数（默认 60s；越小越精确，CPU 开销越大）
        """
        self.target_time = target_time
        self.callback = callback
        self.skip_weekend = skip_weekend
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        # 已触发日期（yyyy-mm-dd），防同日重复触发；进程重启后清空，
        # 配合落库的 ON DUPLICATE KEY UPDATE，重复触发幂等无副作用。
        self._fired_dates: Set[datetime.date] = set()

    def _parse_time(self) -> datetime.time:
        h, m = self.target_time.split(":")
        return datetime.time(int(h), int(m))

    def _now(self) -> datetime.datetime:
        """当前墙钟时间（测试可覆写）"""
        return datetime.datetime.now()

    def _is_due(self, now: datetime.datetime) -> bool:
        """是否应触发：墙钟已过当日目标时刻，且（若跳周末）当日非周末"""
        if self.skip_weekend and now.weekday() in self._WEEKEND:
            return False
        target = datetime.datetime.combine(now.date(), self._parse_time())
        return now >= target

    def _run(self) -> None:
        logger.info(
            "DailyScheduler 启动: 每日 %s 触发%s",
            self.target_time,
            "（跳过周末）" if self.skip_weekend else "",
        )
        while not self._stop_event.is_set():
            now = self._now()
            # 墙钟已过点且当日尚未触发 → 触发并标记当日（无论成功失败都标记，
            # 避免失败回调每分钟重试）。睡眠唤醒后首帧 here 即可补判触发。
            if now.date() not in self._fired_dates and self._is_due(now):
                try:
                    if self.callback:
                        self.callback()
                except Exception as e:
                    logger.error("DailyScheduler 回调执行失败: %s", e)
                self._fired_dates.add(now.date())
            # 短轮询：睡眠期间 wait 同样冻结，但唤醒后立即返回进入下一帧，
            # 由 _now() 墙钟重新判定，不依赖 wait 的精确时长。
            self._stop_event.wait(self.poll_interval)

    def start(self) -> None:
        """启动调度器"""
        if self._thread and self._thread.is_alive():
            logger.warning("DailyScheduler 已在运行")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="ReportingDailyScheduler"
        )
        self._thread.start()

    def stop(self) -> None:
        """停止调度器"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("DailyScheduler 已停止")

    def next_run_at(self) -> Optional[datetime.datetime]:
        """查询下一次触发时刻（调试用）

        今日未到点且未触发 → 今日目标时刻；否则顺延到下一个工作日。
        """
        if not self._thread or not self._thread.is_alive():
            return None
        now = self._now()
        candidate = datetime.datetime.combine(now.date(), self._parse_time())
        if now.date() in self._fired_dates or now >= candidate:
            candidate += datetime.timedelta(days=1)
        if self.skip_weekend:
            while candidate.weekday() in self._WEEKEND:
                candidate += datetime.timedelta(days=1)
        return candidate
