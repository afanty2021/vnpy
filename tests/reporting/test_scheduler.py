# -*- coding:utf-8 -*-
"""DailyScheduler 单元测试

验证墙钟驱动的触发语义：进程从系统睡眠中唤醒后（墙钟已跳过目标时刻），
仍能在下一次轮询补判触发；且同日不重复触发、跳过周末、回调异常不杀线程。

这是 6/23~6/25 权益快照漏落库的回归防护——旧实现基于 time.monotonic 的
长 wait，系统睡眠期间单调时钟冻结，18:30 触发被无限推迟，导致即便 client
进程常驻也从未在 18:30 落库。
"""
from datetime import datetime
from unittest.mock import MagicMock

from vnpy_china_reporting.data_source.scheduler import DailyScheduler


def _dt(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi)


class _FakeClock:
    """受控墙钟：每次调用返回序列中的下一个时刻（耗尽后停留末值）。"""

    def __init__(self, times):
        self._times = list(times)
        self._i = 0

    def __call__(self):
        t = self._times[min(self._i, len(self._times) - 1)]
        self._i += 1
        return t


def _drive(scheduler, monkeypatch, times, body_rounds):
    """同步驱动 _run：注入受控墙钟与受控 _stop_event。

    body_rounds = 循环体执行次数。is_set 前 body_rounds 次返回 False（进入循环），
    第 body_rounds+1 次返回 True（退出）；wait 不阻塞、不触发停止。
    替换整个 _stop_event 而非 patch 其方法，避免 threading.Event 实例方法
    无法被 monkeypatch 覆盖导致真实等待 60s。
    """
    monkeypatch.setattr(scheduler, "_now", _FakeClock(times))
    fake_stop = MagicMock()
    fake_stop.is_set.side_effect = [False] * body_rounds + [True]
    fake_stop.wait.return_value = False
    monkeypatch.setattr(scheduler, "_stop_event", fake_stop)
    scheduler._run()


# 2026-06-24 周二、2026-06-25 周三（交易日），2026-06-28 周六（周末）

def test_fires_after_wall_clock_crosses_target(monkeypatch):
    """墙钟从 18:00 跳到 18:31（模拟睡眠错过 18:30）后，应触发回调一次"""
    cb = MagicMock()
    sch = DailyScheduler("18:30", callback=cb, skip_weekend=True)
    _drive(sch, monkeypatch,
           [_dt(2026, 6, 24, 18, 0), _dt(2026, 6, 24, 18, 31)],
           body_rounds=2)
    cb.assert_called_once()


def test_does_not_fire_before_target(monkeypatch):
    """墙钟始终在 18:30 之前，不应触发"""
    cb = MagicMock()
    sch = DailyScheduler("18:30", callback=cb, skip_weekend=True)
    _drive(sch, monkeypatch,
           [_dt(2026, 6, 24, 10, 0), _dt(2026, 6, 24, 12, 0), _dt(2026, 6, 24, 18, 29)],
           body_rounds=3)
    cb.assert_not_called()


def test_fires_only_once_per_day(monkeypatch):
    """同日多次轮询（墙钟停在 19:00）只触发一次，防同日重复落库"""
    cb = MagicMock()
    sch = DailyScheduler("18:30", callback=cb, skip_weekend=True)
    _drive(sch, monkeypatch,
           [_dt(2026, 6, 24, 19, 0)] * 4,
           body_rounds=4)
    assert cb.call_count == 1


def test_skips_weekend(monkeypatch):
    """周六过点不触发（A股非交易日）"""
    cb = MagicMock()
    sch = DailyScheduler("18:30", callback=cb, skip_weekend=True)
    _drive(sch, monkeypatch,
           [_dt(2026, 6, 28, 19, 0), _dt(2026, 6, 28, 20, 0)],
           body_rounds=2)
    cb.assert_not_called()


def test_callback_exception_keeps_loop_alive(monkeypatch):
    """回调抛异常不杀线程：异常被吞并标记当日已触发，下一交易日仍能正常触发"""
    cb = MagicMock(side_effect=[RuntimeError("boom"), None])
    sch = DailyScheduler("18:30", callback=cb, skip_weekend=True)
    _drive(sch, monkeypatch,
           [_dt(2026, 6, 24, 19, 0), _dt(2026, 6, 25, 19, 0)],
           body_rounds=2)
    assert cb.call_count == 2
