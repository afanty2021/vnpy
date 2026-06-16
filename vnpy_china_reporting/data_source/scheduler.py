"""
每日定时调度器

基于 threading 实现每日固定时刻触发回调，用于权益快照落库等定时任务。
由 vnpy 主进程启动时实例化并 start()，主进程退出时 stop()。

示例（每日 18:30 落库权益快照）：
    scheduler = DailyScheduler("18:30", callback=lambda: collector.collect())
    scheduler.start()
"""

import threading
import datetime
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class DailyScheduler:
    """每日定时触发器（后台守护线程）"""

    def __init__(
        self,
        target_time: str = "18:30",
        callback: Optional[Callable[[], None]] = None,
        skip_weekend: bool = True,
    ):
        """
        Args:
            target_time: 每日触发时刻，格式 "HH:MM"
            callback: 触发回调（无参）
            skip_weekend: 是否跳过周六日（A股非交易日，默认跳过）
        """
        self.target_time = target_time
        self.callback = callback
        self.skip_weekend = skip_weekend
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _parse_time(self) -> datetime.time:
        h, m = self.target_time.split(":")
        return datetime.time(int(h), int(m))

    def _seconds_until_next(self, now: datetime.datetime) -> float:
        """计算到下一个有效触发时刻的秒数"""
        target = self._parse_time()
        next_run = now.replace(
            hour=target.hour, minute=target.minute, second=0, microsecond=0
        )
        if next_run <= now:
            next_run += datetime.timedelta(days=1)
        # 跳过周末
        if self.skip_weekend:
            while next_run.weekday() >= 5:  # 5=周六, 6=周日
                next_run += datetime.timedelta(days=1)
        return (next_run - now).total_seconds()

    def _run(self) -> None:
        logger.info(
            "DailyScheduler 启动: 每日 %s 触发%s",
            self.target_time,
            "（跳过周末）" if self.skip_weekend else "",
        )
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            wait = self._seconds_until_next(now)
            # 分段等待以便及时响应 stop
            if self._stop_event.wait(wait):
                break
            if self.callback:
                try:
                    self.callback()
                except Exception as e:
                    logger.error("DailyScheduler 回调执行失败: %s", e)

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
        """查询下一次触发时刻（调试用）"""
        if not self._thread or not self._thread.is_alive():
            return None
        now = datetime.datetime.now()
        wait = self._seconds_until_next(now)
        return now + datetime.timedelta(seconds=wait)
