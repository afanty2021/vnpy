# -*- coding: utf-8 -*-
"""QMT 日线预热器测试。开发期 import patches 源，mock qmt_preheater.xtdata。"""
import sys
from pathlib import Path
import time
from unittest.mock import MagicMock, patch

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "patches"))

import qmt_preheater  # noqa: E402
from qmt_preheater import QmtDailyBarPreheater  # noqa: E402


def _fake_get_stock_list(mapping):
    """构造 get_stock_list_in_sector 的 side_effect，按板块名返回成分列表。"""
    def _impl(sector_name=None):
        return mapping.get(sector_name, [])
    return _impl


# ===== _collect_symbols =====
def test_collect_symbols_dedup():
    ph = QmtDailyBarPreheater()
    mapping = {
        "沪深A股": ["000001.SZ", "300001.SZ", "688001.SH"],
        "创业板": ["300001.SZ"],
        "科创板": ["688001.SH"],
        "沪深ETF": ["510050.SH"],
    }
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _fake_get_stock_list(mapping)
    with patch("qmt_preheater.xtdata", fake_xt):
        symbols, sector_members = ph._collect_symbols()
    assert symbols == ["000001.SZ", "300001.SZ", "510050.SH", "688001.SH"]
    assert sector_members["沪深A股"] == {"000001.SZ", "300001.SZ", "688001.SH"}
    assert sector_members["创业板"] == {"300001.SZ"}
    assert sector_members["沪深ETF"] == {"510050.SH"}


def test_collect_symbols_sector_exception_isolated():
    ph = QmtDailyBarPreheater()
    def _impl(sector_name=None):
        if sector_name == "创业板":
            raise Exception("miniQMT 断开")
        return {"沪深A股": ["000001.SZ"], "科创板": [], "沪深ETF": []}.get(sector_name, [])
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _impl
    with patch("qmt_preheater.xtdata", fake_xt):
        symbols, sector_members = ph._collect_symbols()
    assert symbols == ["000001.SZ"]
    assert sector_members["创业板"] == set()


# ===== _log_sector_stats =====
def test_log_sector_stats_subset_relation(capsys):
    ph = QmtDailyBarPreheater()
    sector_members = {
        "沪深A股": {"000001.SZ", "300001.SZ", "688001.SH"},
        "创业板": {"300001.SZ"},
        "科创板": {"688001.SH"},
        "沪深ETF": {"510050.SH"},
    }
    ph._log_sector_stats(sector_members)
    out = capsys.readouterr().out
    assert "沪深A股=3" in out
    assert "创业板=1" in out
    assert "创业板⊂沪深A股=True" in out
    assert "科创板⊂沪深A股=True" in out
    assert "去重后总数=4" in out


def test_log_sector_stats_not_subset(capsys):
    ph = QmtDailyBarPreheater()
    sector_members = {
        "沪深A股": {"000001.SZ"},
        "创业板": set(),
        "科创板": {"688001.SH"},  # 不在沪深A股
        "沪深ETF": set(),
    }
    ph._log_sector_stats(sector_members)
    out = capsys.readouterr().out
    assert "科创板⊂沪深A股=False" in out


# ===== _calc_start_time =====
def test_calc_start_time_format_and_value():
    from datetime import datetime, timedelta
    ph = QmtDailyBarPreheater()
    start = ph._calc_start_time()
    assert len(start) == 8 and start.isdigit(), f"格式非 YYYYMMDD: {start}"
    expected = (datetime.now() - timedelta(days=ph.LOOKBACK_DAYS)).strftime("%Y%m%d")
    assert start == expected, f"期望 {expected} 实际 {start}"


def test_calc_start_time_custom_lookback():
    from datetime import datetime, timedelta
    ph = QmtDailyBarPreheater()
    ph.LOOKBACK_DAYS = 7
    start = ph._calc_start_time()
    expected = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    assert start == expected


# ===== _download_batch =====
def test_download_batch_success_with_callback():
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.download_history_data2.return_value = {}  # 真实异步 API 返回空 dict（非 bool）
    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ", "000002.SZ"], "20260518")
    assert ok is True
    fake_xt.download_history_data2.assert_called_once()
    kwargs = fake_xt.download_history_data2.call_args.kwargs
    assert kwargs["stock_list"] == ["000001.SZ", "000002.SZ"]
    assert kwargs["period"] == "1d"
    assert kwargs["start_time"] == "20260518"
    assert "callback" in kwargs


def test_download_batch_return_value_ignored():
    """download_history_data2 异步返回空 dict {}（实测），非 bool。
    成功判定不看返回值（bool({})=False 会误判），只看是否抛异常——返回 {} 仍判成功。"""
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.download_history_data2.return_value = {}  # 真实异步返回
    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    assert ok is True  # 未抛异常即成功，空 dict 不影响判定


def test_download_batch_exception_returns_false(capsys):
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.download_history_data2.side_effect = Exception("miniQMT 未运行")
    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    assert ok is False
    assert "批次下载失败" in capsys.readouterr().out


def test_download_batch_timeout():
    """超时保护：_do 线程无限阻塞 → join(timeout) 到期 → 返回 False + 日志。"""
    ph = QmtDailyBarPreheater()
    ph.BATCH_TIMEOUT = 0.1  # 0.1s 超时便于测试
    fake_xt = MagicMock()
    fake_xt.download_history_data2.side_effect = lambda **kwargs: time.sleep(5)  # 远长于 timeout
    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    assert ok is False
    # 超时时 join 到期 is_alive()=True → 记录超时日志
    # 注：_log 内部 print 不捕获（capsys 在超时测试可选，仅验证返回值），线程不被强制杀死但因 daemon=True 无害


# ===== preheat + _format_elapsed =====
def test_format_elapsed():
    assert QmtDailyBarPreheater._format_elapsed(0) == "0m0s"
    assert QmtDailyBarPreheater._format_elapsed(59) == "0m59s"
    assert QmtDailyBarPreheater._format_elapsed(60) == "1m0s"
    assert QmtDailyBarPreheater._format_elapsed(492) == "8m12s"


def test_preheat_batching_and_summary(capsys):
    ph = QmtDailyBarPreheater()
    ph.BATCH_SIZE = 2
    ph.BATCH_SLEEP = 0
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _fake_get_stock_list({
        "沪深A股": ["000001.SZ", "000002.SZ", "300001.SZ", "688001.SH"],
        "创业板": [], "科创板": [], "沪深ETF": ["510050.SH"],
    })
    fake_xt.download_history_data2.return_value = {}  # 真实异步返回
    with patch("qmt_preheater.xtdata", fake_xt):
        ph.preheat()
    assert fake_xt.download_history_data2.call_count == 3
    out = capsys.readouterr().out
    assert "batches_ok=3" in out
    assert "batches_fail=0" in out
    assert "symbols=5" in out
    assert "elapsed=" in out
    assert "日线预热进度 2/5" in out
    assert "日线预热进度 5/5" in out


def test_preheat_failure_tolerance(capsys):
    ph = QmtDailyBarPreheater()
    ph.BATCH_SIZE = 2
    ph.BATCH_SLEEP = 0
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _fake_get_stock_list({
        "沪深A股": ["A.SZ", "B.SZ", "C.SZ", "D.SZ"],
        "创业板": [], "科创板": [], "沪深ETF": [],
    })
    # 第1批正常（返回{}不抛异常→成功），第2批抛异常→失败；验证成功判定基于异常而非返回值
    fake_xt.download_history_data2.side_effect = [{}, Exception("第2批失败")]
    with patch("qmt_preheater.xtdata", fake_xt):
        ph.preheat()
    out = capsys.readouterr().out
    assert "batches_ok=1" in out
    assert "batches_fail=1" in out
    assert "symbols=4" in out


def test_preheat_empty_symbols(capsys):
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.return_value = []
    with patch("qmt_preheater.xtdata", fake_xt):
        ph.preheat()
    out = capsys.readouterr().out
    assert "无可预热标的" in out
    fake_xt.download_history_data2.assert_not_called()


def test_preheat_outer_exception_swallowed(capsys, monkeypatch):
    """外层兜底：_collect_symbols 自身抛异常（绕过其内部 try/except）时，preheat 不外泄。"""
    ph = QmtDailyBarPreheater()
    monkeypatch.setattr(
        ph, "_collect_symbols", MagicMock(side_effect=RuntimeError("catastrophic"))
    )
    ph.preheat()
    out = capsys.readouterr().out
    assert "日线预热开始" in out
    assert "日线预热异常（不影响交易）" in out
