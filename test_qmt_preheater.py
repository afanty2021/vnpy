# -*- coding: utf-8 -*-
"""QMT 日线预热器测试。开发期 import patches 源，mock qmt_preheater.xtdata。"""
import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "patches"))

import qmt_preheater  # noqa: E402
from qmt_preheater import QmtDailyBarPreheater, _worker_main  # noqa: E402


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


# ===== _download_batch (subprocess 隔离) =====
# fresh-subprocess-per-batch：每批 Popen 子进程下载，超时硬杀，失败下次增量补。
# 单元测试 mock subprocess.Popen；preheat 集成测试见下方 mock _download_batch。
def _fake_proc(stdout=b"", stderr=b"", exc=None):
    """构造 fake Popen：communicate 返回 (stdout, stderr)，或抛 exc。"""
    proc = MagicMock()
    if exc is not None:
        proc.communicate.side_effect = exc
    else:
        proc.communicate.return_value = (stdout, stderr)
    return proc


def test_download_batch_success():
    """worker 输出 ok=true → 批次成功，Popen 被调一次。"""
    ph = QmtDailyBarPreheater()
    fake = _fake_proc(stdout=b'{"ok": true, "error": null, "elapsed": 0.5}\n')
    with patch("qmt_preheater.xtdata", MagicMock()), \
         patch("qmt_preheater.subprocess.Popen", return_value=fake) as mp:
        ok = ph._download_batch(["000001.SZ", "000002.SZ"], "20260518")
    assert ok is True
    mp.assert_called_once()


def test_download_batch_worker_failure_logged(capsys):
    """worker 内异常（ok=false）→ 返回 False 且日志含 error。"""
    ph = QmtDailyBarPreheater()
    fake = _fake_proc(stdout=b'{"ok": false, "error": "miniQMT down"}\n')
    with patch("qmt_preheater.xtdata", MagicMock()), \
         patch("qmt_preheater.subprocess.Popen", return_value=fake):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    out = capsys.readouterr().out
    assert ok is False
    assert "批次下载失败" in out
    assert "miniQMT down" in out


def test_download_batch_timeout_kills_subprocess(capsys):
    """超时 → communicate 抛 TimeoutExpired → kill 硬杀子进程 → 返回 False（核心价值）。"""
    ph = QmtDailyBarPreheater()
    ph.BATCH_TIMEOUT = 0.1
    fake = _fake_proc(exc=subprocess.TimeoutExpired(cmd=["x"], timeout=0.1))
    with patch("qmt_preheater.xtdata", MagicMock()), \
         patch("qmt_preheater.subprocess.Popen", return_value=fake):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    out = capsys.readouterr().out
    assert ok is False
    assert "超时" in out
    fake.kill.assert_called_once()  # 硬杀


def test_download_batch_unparseable_output_includes_stderr(capsys):
    """子进程输出非 JSON → 无法解析 → 返回 False，且日志附 stderr 尾行辅助诊断。

    worker 的 try/except 已把 connect/download 异常写入 stdout JSON；但当 worker 在
    json.dumps 之前崩溃（import 失败 / C 扩展 segfault / 进程异常终止）时 stdout 无 JSON，
    stderr 是此时唯一的诊断线索，应透出到日志。
    """
    ph = QmtDailyBarPreheater()
    fake = _fake_proc(stdout=b"garbage\n", stderr=b"FATAL: xtdata crash\nstack...\n")
    with patch("qmt_preheater.xtdata", MagicMock()), \
         patch("qmt_preheater.subprocess.Popen", return_value=fake):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    out = capsys.readouterr().out
    assert ok is False
    assert "无法解析" in out
    assert "xtdata crash" in out  # stderr 内容应透出到日志


def test_download_batch_popen_failure(capsys):
    """Popen 自身失败（python 路径错等）→ 返回 False。"""
    ph = QmtDailyBarPreheater()
    with patch("qmt_preheater.xtdata", MagicMock()), \
         patch("qmt_preheater.subprocess.Popen", side_effect=OSError("python not found")):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    out = capsys.readouterr().out
    assert ok is False
    assert "启动" in out


# ===== _worker_main (子进程入口) =====
def test_worker_main_success(capsys):
    """worker 正常：argv 解析 + connect/download + 输出 ok=true JSON。"""
    fake_xt = MagicMock()
    with patch("qmt_preheater.xtdata", fake_xt):
        _worker_main(["--worker", "000001.SZ,000002.SZ", "1d", "20260518"])
    out = capsys.readouterr().out
    data = json.loads(out.strip().splitlines()[-1])
    assert data["ok"] is True
    assert data["error"] is None
    assert data["elapsed"] >= 0
    fake_xt.connect.assert_called_once()
    fake_xt.download_history_data2.assert_called_once_with(
        ["000001.SZ", "000002.SZ"], "1d", "20260518"
    )


def test_worker_main_exception_written_as_json(capsys):
    """worker 内异常 → ok=false 且 error 含异常，stdout 仍是合法 JSON（父进程可解析）。"""
    fake_xt = MagicMock()
    fake_xt.download_history_data2.side_effect = RuntimeError("miniQMT down")
    with patch("qmt_preheater.xtdata", fake_xt):
        _worker_main(["--worker", "000001.SZ", "1d", "20260518"])
    out = capsys.readouterr().out
    data = json.loads(out.strip().splitlines()[-1])
    assert data["ok"] is False
    assert "miniQMT down" in data["error"]


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
    # 集成测试只验证 preheat 的分批/进度/汇总，下载委托给 _download_batch（此处 mock）
    with patch("qmt_preheater.xtdata", fake_xt), \
         patch.object(ph, "_download_batch", return_value=True) as mock_dl:
        ph.preheat()
    assert mock_dl.call_count == 3  # 5只 / BATCH_SIZE=2 → 3 批
    # 首批切分正确 + start_time 透传
    assert mock_dl.call_args_list[0].args[0] == ["000001.SZ", "000002.SZ"]
    assert mock_dl.call_args_list[0].args[1] == ph._calc_start_time()
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
    # 第1批成功，第2批失败：验证失败容错与计数（不中断后续，下次启动增量补）
    with patch("qmt_preheater.xtdata", fake_xt), \
         patch.object(ph, "_download_batch", side_effect=[True, False]):
        ph.preheat()
    out = capsys.readouterr().out
    assert "batches_ok=1" in out
    assert "batches_fail=1" in out
    assert "symbols=4" in out


def test_preheat_empty_symbols(capsys):
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.return_value = []
    with patch("qmt_preheater.xtdata", fake_xt), \
         patch.object(ph, "_download_batch") as mock_dl:
        ph.preheat()
    out = capsys.readouterr().out
    assert "无可预热标的" in out
    mock_dl.assert_not_called()  # 空标的不触发下载


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
