# QMT 日线数据预热 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 服务端启动时后台异步预热全市场（A股+ETF）日线数据，保证 `md._get_avg_daily_vol` 量比计算对任意标的可读。

**Architecture:** 新建独立模块 `qmt_preheater.py`（单一职责：生产日线数据，与 md.py 消费解耦）。`run_qmt_server.py` 启动时起 daemon 线程调用其 `preheat()`：枚举板块成分去重 → 分批 `download_history_data2` 增量下载 → 进度/汇总日志。补丁双写（patches 源 + site-packages 运行时）。

**Tech Stack:** Python 3.11 · xtquant（xtdata）· unittest.mock · pytest

**关联 spec：** `docs/superpowers/specs/2026-06-17-qmt-daily-bar-preheater-design.md`

**项目规则：** 不自动 git commit；每个 Task 以测试通过为完成标志。

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `patches/qmt_preheater.py` | Create | 预热器源（单一事实源，开发期在此 TDD） |
| `site-packages/vnpy_qmt/qmt_preheater.py` | Create（Task 6 cp 同步） | 运行时实际加载版本 |
| `test_qmt_preheater.py` | Create（项目根） | 纯逻辑测试，mock xtdata |
| `examples/client_server/run_qmt_server.py` | Modify（start 方法） | 集成 daemon 预热线程 |
| `~/.claude/.../memory/qmt-patch-status.md` | Update | 补丁4 记录 |

**开发期 import 约定**：测试通过 `sys.path.insert(patches目录)` + `from qmt_preheater import ...` 加载源模块，故 mock 目标为 `qmt_preheater.xtdata`（模块命名空间内的 xtdata 引用）。Task 6 同步 site-packages 后，冒烟测试改用 `from vnpy_qmt.qmt_preheater import ...`。

**spec 接口的实现细化**：spec 4.1 写 `_collect_symbols() -> list[str]`；计划中细化为 `_collect_symbols() -> tuple[list[str], dict[str, set[str]]]`，返回各板块成分集合供 `_log_sector_stats` 复用，避免二次枚举（DRY）。职责（枚举+去重）不变。

**Python 环境**：所有命令用 `D:\Scoop\apps\miniconda3\current\envs\quant-3.11\python.exe`（下文记作 `$PY`）。

---

## Task 1: 模块骨架 + 标的枚举去重（`_collect_symbols`）

**Files:**
- Create: `patches/qmt_preheater.py`
- Create: `test_qmt_preheater.py`

- [ ] **Step 1: 写失败测试（test_qmt_preheater.py）**

```python
# -*- coding: utf-8 -*-
"""QMT 日线预热器测试。开发期 import patches 源，mock qmt_preheater.xtdata。"""
import sys
from pathlib import Path
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


def test_collect_symbols_dedup():
    """跨板块去重，并返回各板块成分集合（供留痕复用）。"""
    ph = QmtDailyBarPreheater()
    mapping = {
        "沪深A股": ["000001.SZ", "300001.SZ", "688001.SH"],   # 含创业板+科创板成分
        "创业板": ["300001.SZ"],                              # 与沪深A股重叠
        "科创板": ["688001.SH"],                              # 与沪深A股重叠
        "沪深ETF": ["510050.SH"],
    }
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _fake_get_stock_list(mapping)

    with patch("qmt_preheater.xtdata", fake_xt):
        symbols, sector_members = ph._collect_symbols()

    # 去重后 4 只，排序
    assert symbols == ["000001.SZ", "300001.SZ", "510050.SH", "688001.SH"]
    # 各板块成分集合正确
    assert sector_members["沪深A股"] == {"000001.SZ", "300001.SZ", "688001.SH"}
    assert sector_members["创业板"] == {"300001.SZ"}
    assert sector_members["沪深ETF"] == {"510050.SH"}


def test_collect_symbols_sector_exception_isolated():
    """单个板块枚举异常不影响其他板块，异常板块记空集。"""
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
    assert sector_members["创业板"] == set()  # 异常板块降级为空集


# 注意：含 capsys 等 pytest fixture 的用例（Task 2 起）仅支持 pytest 运行；
# python 直接执行本文件只跑下方无 fixture 的用例。完整测试用：$PY -m pytest test_qmt_preheater.py
if __name__ == "__main__":
    test_collect_symbols_dedup()
    test_collect_symbols_sector_exception_isolated()
    print("Task1 测试通过（完整测试请用 pytest）")
```

- [ ] **Step 2: 跑测试确认失败**

```bash
$PY -m pytest test_qmt_preheater.py -v
```
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'qmt_preheater'`

- [ ] **Step 3: 实现模块骨架 + `_collect_symbols`（patches/qmt_preheater.py）**

```python
# -*- coding: utf-8 -*-
"""
QMT 日线数据预热器：服务端启动时后台增量下载全市场（A股+ETF）日线，
保证 md._get_avg_daily_vol 计算量比时有近 5 日日均量数据可读。

设计文档：docs/superpowers/specs/2026-06-17-qmt-daily-bar-preheater-design.md
"""
import time
from datetime import datetime, timedelta

from xtquant import xtdata


class QmtDailyBarPreheater:
    """QMT 日线数据预热器：启动时后台增量下载全市场日线。"""

    # 显式列举全部所需板块 + set 去重，不依赖"沪深A股是否含子板块"的假设
    SECTORS: list[str] = ["沪深A股", "创业板", "科创板", "沪深ETF"]
    LOOKBACK_DAYS: int = 30
    BATCH_SIZE: int = 100
    BATCH_SLEEP: float = 3.0

    def __init__(self, main_engine=None):
        self.main_engine = main_engine

    def _log(self, msg: str) -> None:
        """同时写 stdout 与 main_engine 日志（客户端可见）。"""
        print(f"[preheater] {msg}")
        if self.main_engine is not None:
            try:
                self.main_engine.write_log(msg)
            except Exception:
                pass

    def _collect_symbols(self) -> tuple[list[str], dict[str, set[str]]]:
        """枚举各板块成分并去重。

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
        all_set: set[str] = set().union(*sector_members.values()) if sector_members else set()
        return sorted(all_set), sector_members
```

- [ ] **Step 4: 跑测试确认通过**

```bash
$PY -m pytest test_qmt_preheater.py -v
```
Expected: `2 passed`（Task1 的两个 `_collect_symbols` 用例）

- [ ] **Step 5: 检查点** — `_collect_symbols` 去重与异常隔离验证通过。

---

## Task 2: 实测留痕日志（`_log_sector_stats`）

**Files:**
- Modify: `patches/qmt_preheater.py`（新增 `_log_sector_stats` 方法）
- Modify: `test_qmt_preheater.py`（追加测试）

- [ ] **Step 1: 追加失败测试**

在 `test_qmt_preheater.py` 的 `if __name__ == "__main__":` 之前追加：

```python
def test_log_sector_stats_subset_relation(capsys):
    """实测留痕：打印各板块数量 + 子集关系 + 去重总数。"""
    ph = QmtDailyBarPreheater()
    # 构造明确包含关系：创业板/科创板 ⊂ 沪深A股
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
    """科创板非子集时输出 False。"""
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
```

> 注：这两个用例用 pytest fixture `capsys` 捕获 stdout，必须用 `$PY -m pytest` 运行（不能 `python test.py` 直接跑）。

- [ ] **Step 2: 跑测试确认失败**

```bash
$PY -m pytest test_qmt_preheater.py::test_log_sector_stats_subset_relation -v
```
Expected: FAIL — `AttributeError: 'QmtDailyBarPreheater' object has no attribute '_log_sector_stats'`

- [ ] **Step 3: 实现 `_log_sector_stats`**

在 `patches/qmt_preheater.py` 的 `_collect_symbols` 方法之后追加：

```python
    def _log_sector_stats(self, sector_members: dict[str, set[str]]) -> None:
        """打印各板块成分数量与子集关系（运行时实测留痕）。

        解决设计阶段无法预确认的"沪深A股是否含创业板/科创板"问题：首次运行日志
        即为权威证据，未来可据此精简 SECTORS。
        """
        parts = [f"{s}={len(m)}" for s, m in sector_members.items()]
        a = sector_members.get("沪深A股", set())
        gem = sector_members.get("创业板", set())
        star = sector_members.get("科创板", set())
        total = len(set().union(*sector_members.values())) if sector_members else 0
        self._log(
            f"板块成分：{' '.join(parts)} | "
            f"创业板⊂沪深A股={gem.issubset(a)} 科创板⊂沪深A股={star.issubset(a)} | "
            f"去重后总数={total}"
        )
```

- [ ] **Step 4: 跑测试确认通过**

```bash
$PY -m pytest test_qmt_preheater.py::test_log_sector_stats_subset_relation test_qmt_preheater.py::test_log_sector_stats_not_subset -v
```
Expected: 2 passed

- [ ] **Step 5: 检查点** — 实测留痕日志（子集关系 True/False）正确。

---

## Task 3: 时间计算（`_calc_start_time`）

**Files:**
- Modify: `patches/qmt_preheater.py`（新增 `_calc_start_time`）
- Modify: `test_qmt_preheater.py`（追加测试）

- [ ] **Step 1: 追加失败测试**

```python
def test_calc_start_time_format_and_value():
    """start_time 为近 LOOKBACK_DAYS 自然日，格式 YYYYMMDD，不涉及 end_time。"""
    from datetime import datetime, timedelta
    ph = QmtDailyBarPreheater()
    start = ph._calc_start_time()
    # 格式校验
    assert len(start) == 8 and start.isdigit(), f"格式非 YYYYMMDD: {start}"
    # 值校验：等于今天减 30 天
    expected = (datetime.now() - timedelta(days=ph.LOOKBACK_DAYS)).strftime("%Y%m%d")
    assert start == expected, f"期望 {expected} 实际 {start}"


def test_calc_start_time_custom_lookback():
    """LOOKBACK_DAYS 可配置。"""
    from datetime import datetime, timedelta
    ph = QmtDailyBarPreheater()
    ph.LOOKBACK_DAYS = 7
    start = ph._calc_start_time()
    expected = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    assert start == expected
```

- [ ] **Step 2: 跑测试确认失败**

```bash
$PY -m pytest test_qmt_preheater.py::test_calc_start_time_format_and_value -v
```
Expected: FAIL — `AttributeError: ... has no attribute '_calc_start_time'`

- [ ] **Step 3: 实现 `_calc_start_time`**

在 `_log_sector_stats` 之后追加：

```python
    def _calc_start_time(self) -> str:
        """近 LOOKBACK_DAYS 个自然日，格式 YYYYMMDD。

        end_time 不传（让 API 用默认的"今天"），避免传入未来日期异常。
        """
        start = datetime.now() - timedelta(days=self.LOOKBACK_DAYS)
        return start.strftime("%Y%m%d")
```

- [ ] **Step 4: 跑测试确认通过**

```bash
$PY -m pytest test_qmt_preheater.py::test_calc_start_time_format_and_value test_qmt_preheater.py::test_calc_start_time_custom_lookback -v
```
Expected: 2 passed

- [ ] **Step 5: 检查点** — start_time 计算正确（格式 + 可配置）。

---

## Task 4: 单批下载（`_download_batch`）

**Files:**
- Modify: `patches/qmt_preheater.py`（新增 `_download_batch`）
- Modify: `test_qmt_preheater.py`（追加测试）

- [ ] **Step 1: 追加失败测试**

```python
def test_download_batch_success_with_callback():
    """成功下载：传 callback=lambda:None、period=1d、start_time，返回 True。"""
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.download_history_data2.return_value = True

    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ", "000002.SZ"], "20260518")

    assert ok is True
    fake_xt.download_history_data2.assert_called_once()
    kwargs = fake_xt.download_history_data2.call_args.kwargs
    assert kwargs["stock_list"] == ["000001.SZ", "000002.SZ"]
    assert kwargs["period"] == "1d"
    assert kwargs["start_time"] == "20260518"
    assert "callback" in kwargs  # 显式传 callback 保持 API 一致性


def test_download_batch_false_return():
    """返回 False 时判定为失败。"""
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.download_history_data2.return_value = False
    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    assert ok is False


def test_download_batch_exception_returns_false(capsys):
    """异常被捕获，返回 False，不外抛（保证不中断整体）。"""
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.download_history_data2.side_effect = Exception("miniQMT 未运行")
    with patch("qmt_preheater.xtdata", fake_xt):
        ok = ph._download_batch(["000001.SZ"], "20260518")
    assert ok is False
    assert "批次下载失败" in capsys.readouterr().out
```

- [ ] **Step 2: 跑测试确认失败**

```bash
$PY -m pytest test_qmt_preheater.py::test_download_batch_success_with_callback -v
```
Expected: FAIL — `AttributeError: ... has no attribute '_download_batch'`

- [ ] **Step 3: 实现 `_download_batch`**

在 `_calc_start_time` 之后追加：

```python
    def _download_batch(self, batch: list[str], start_time: str) -> bool:
        """下载一批日线，返回是否成功。

        - 显式传 callback=lambda:None（与 md.py 一致，满足 API 签名，避免不同
          QMT 版本省略 callback 时的行为差异）
        - 单批异常被捕获返回 False，不中断整体流程
        """
        try:
            result = xtdata.download_history_data2(
                stock_list=batch,
                period="1d",
                start_time=start_time,
                callback=lambda: None,
            )
            return bool(result)
        except Exception as e:
            self._log(f"批次下载失败（{len(batch)}只）: {e}")
            return False
```

- [ ] **Step 4: 跑测试确认通过**

```bash
$PY -m pytest test_qmt_preheater.py -k download_batch -v
```
Expected: 3 passed

- [ ] **Step 5: 检查点** — 单批下载（callback + 返回值判定 + 异常容错）正确。

---

## Task 5: 主流程（`preheat` + `_format_elapsed`）

**Files:**
- Modify: `patches/qmt_preheater.py`（新增 `preheat`、`_format_elapsed`）
- Modify: `test_qmt_preheater.py`（追加测试）

- [ ] **Step 1: 追加失败测试**

```python
def test_format_elapsed():
    assert QmtDailyBarPreheater._format_elapsed(0) == "0m0s"
    assert QmtDailyBarPreheater._format_elapsed(59) == "0m59s"
    assert QmtDailyBarPreheater._format_elapsed(60) == "1m0s"
    assert QmtDailyBarPreheater._format_elapsed(492) == "8m12s"


def test_preheat_batching_and_summary(capsys):
    """5 只标的、BATCH_SIZE=2 → 3 批；全部成功；汇总 batches_ok/symbols/elapsed。"""
    ph = QmtDailyBarPreheater()
    ph.BATCH_SIZE = 2
    ph.BATCH_SLEEP = 0  # 测试不等待
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _fake_get_stock_list({
        "沪深A股": ["000001.SZ", "000002.SZ", "300001.SZ", "688001.SH"],
        "创业板": [], "科创板": [], "沪深ETF": ["510050.SH"],
    })
    fake_xt.download_history_data2.return_value = True

    with patch("qmt_preheater.xtdata", fake_xt):
        ph.preheat()

    # 5 只 / 批 2 = 3 批 (2,2,1)
    assert fake_xt.download_history_data2.call_count == 3
    out = capsys.readouterr().out
    assert "batches_ok=3" in out
    assert "batches_fail=0" in out
    assert "symbols=5" in out
    assert "elapsed=" in out
    # 进度日志
    assert "日线预热进度 2/5" in out
    assert "日线预热进度 5/5" in out


def test_preheat_failure_tolerance(capsys):
    """第 2 批失败，后续批次仍执行；batches_ok/batches_fail 正确累计。"""
    ph = QmtDailyBarPreheater()
    ph.BATCH_SIZE = 2
    ph.BATCH_SLEEP = 0
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.side_effect = _fake_get_stock_list({
        "沪深A股": ["A.SZ", "B.SZ", "C.SZ", "D.SZ"],
        "创业板": [], "科创板": [], "沪深ETF": [],
    })
    # 4 只 / 批 2 = 2 批；第 1 批成功、第 2 批失败
    fake_xt.download_history_data2.side_effect = [True, False]

    with patch("qmt_preheater.xtdata", fake_xt):
        ph.preheat()

    out = capsys.readouterr().out
    assert "batches_ok=1" in out
    assert "batches_fail=1" in out
    assert "symbols=4" in out


def test_preheat_empty_symbols(capsys):
    """板块全空时提前返回，不调用下载。"""
    ph = QmtDailyBarPreheater()
    fake_xt = MagicMock()
    fake_xt.get_stock_list_in_sector.return_value = []
    with patch("qmt_preheater.xtdata", fake_xt):
        ph.preheat()
    out = capsys.readouterr().out
    assert "无可预热标的" in out
    fake_xt.download_history_data2.assert_not_called()


def test_preheat_outer_exception_swallowed(capsys, monkeypatch):
    """外层兜底：_collect_symbols 自身抛异常（绕过其内部 try/except）时，preheat 不外泄。

    用 monkeypatch 直接替换 _collect_symbols 使其抛异常——此异常不会被 _collect_symbols
    内部的 per-sector try/except 捕获，从而真正触达 preheat 的外层 try/except。
    """
    ph = QmtDailyBarPreheater()
    monkeypatch.setattr(
        ph, "_collect_symbols", MagicMock(side_effect=RuntimeError("catastrophic"))
    )
    ph.preheat()  # 不应抛异常
    out = capsys.readouterr().out
    assert "日线预热开始" in out                    # 确认进入了 preheat 主体
    assert "日线预热异常（不影响交易）" in out      # 确认外层 try/except 兜底并打印
```

- [ ] **Step 2: 跑测试确认失败**

```bash
$PY -m pytest test_qmt_preheater.py::test_format_elapsed -v
```
Expected: FAIL — `AttributeError: ... has no attribute '_format_elapsed'`

- [ ] **Step 3: 实现 `preheat` 与 `_format_elapsed`**

在 `_download_batch` 之后追加：

```python
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
```

- [ ] **Step 4: 跑全部测试确认通过**

```bash
$PY -m pytest test_qmt_preheater.py -v
```
Expected: 全部 passed（Task1-5 所有用例）

- [ ] **Step 5: 检查点** — 主流程（分批、进度、汇总、失败容错、空标的、外层兜底）全部正确。

---

## Task 6: 同步 site-packages + 集成 run_qmt_server.py + 冒烟

**Files:**
- Create: `site-packages/vnpy_qmt/qmt_preheater.py`（cp 自 patches）
- Modify: `examples/client_server/run_qmt_server.py`（start 方法加 daemon 线程）

- [ ] **Step 1: 同步 patches 源到 site-packages**

用 Python 复制 + MD5 校验（跨平台，避免依赖 `cp`/`diff`——Windows PowerShell 无原生 `diff`）：

```bash
$PY -c "from shutil import copyfile; copyfile('patches/qmt_preheater.py', r'D:/Scoop/apps/miniconda3/current/envs/quant-3.11/Lib/site-packages/vnpy_qmt/qmt_preheater.py')"
```

验证两文件 MD5 一致：
```bash
$PY -c "from hashlib import md5; s=open('patches/qmt_preheater.py','rb').read(); d=open(r'D:/Scoop/apps/miniconda3/current/envs/quant-3.11/Lib/site-packages/vnpy_qmt/qmt_preheater.py','rb').read(); print('一致' if md5(s).digest()==md5(d).digest() else '不一致')"
```
Expected: 输出 `一致`

- [ ] **Step 2: 冒烟测试 site-packages 版本可 import**

```bash
$PY -c "from vnpy_qmt.qmt_preheater import QmtDailyBarPreheater; ph=QmtDailyBarPreheater(); print('import OK, SECTORS=', ph.SECTORS)"
```
Expected: 输出 `import OK, SECTORS= ['沪深A股', '创业板', '科创板', '沪深ETF']`

- [ ] **Step 3: 集成到 run_qmt_server.py**

修改 `examples/client_server/run_qmt_server.py`：

(a) 在文件顶部 import 区（`from vnpy_qmt import QmtGateway` 附近）追加：
```python
import threading
from vnpy_qmt.qmt_preheater import QmtDailyBarPreheater
```

(b) 在 `QmtRpcServer.start()` 方法内，`self.rpc_engine.start(...)` 调用**之后**、`print("\n" + "=" * 60)` 提示块**之前**插入：
```python
        # 启动日线数据预热（后台 daemon 线程，不阻塞 RPC 服务；量比计算依赖近5日日线）
        def _preheat_in_background():
            try:
                QmtDailyBarPreheater(self.main_engine).preheat()
            except Exception as e:
                self.main_engine.write_log(f"日线预热异常（不影响交易）: {e}")

        threading.Thread(target=_preheat_in_background, daemon=True, name="qmt-preheater").start()
        print("日线预热已在后台启动（全市场 A股+ETF 增量下载，日志可见进度）")
```

- [ ] **Step 4: 语法检查 run_qmt_server.py**

```bash
$PY -m py_compile examples/client_server/run_qmt_server.py && echo "语法 OK"
```
Expected: 输出 `语法 OK`

- [ ] **Step 5: 检查点** — site-packages 同步、import 冒烟、server 集成语法均通过。

> 端到端验证（真实 miniQMT + 服务端启动 + 客户端订阅 → 量比显示）需用户在 Windows 服务端实际运行，本计划不覆盖（无 miniQMT 环境）。

---

## Task 7: 更新记忆

**Files:**
- Modify: `~/.claude/projects/D--Berton-vnpy/memory/qmt-patch-status.md`

- [ ] **Step 1: 追加补丁4记录**

在 `qmt-patch-status.md` 的"补丁功能"段之前插入：

```markdown
## 补丁文件4: qmt_preheater.py 日线预热

- **补丁源文件**: `patches/qmt_preheater.py`
- **安装目标**: `.../site-packages/vnpy_qmt/qmt_preheater.py`
- **作用**: 服务端启动时后台 daemon 线程增量下载全市场（沪深A股+创业板+科创板+沪深ETF）日线到 `datadir/{SH|SZ}/86400/*.DAT`，保证 [[qmt-patch-status]] 补丁3 的 `md._get_avg_daily_vol` 量比对任意标的可算
- **触发**: `run_qmt_server.py` 的 `start()` 起预热线程；不阻塞 RPC
- **设计**: 显式列举全部板块+set去重（不依赖"沪深A股是否含子板块"）；preheat 开头打印板块成分+子集关系作为实测留痕；分批100只+sleep3s；失败按批次容错
- **日志**: 进度 `日线预热进度 N/M`；汇总 `日线预热完成：batches_ok=X batches_fail=Y symbols=Z elapsed=NmNs`
- **参数**: SECTORS/LOOKBACK_DAYS=30/BATCH_SIZE=100/BATCH_SLEEP=3.0（类属性可调）
- **验证**: `test_qmt_preheater.py`（枚举去重/留痕/时间/单批/主流程容错）
```

- [ ] **Step 2: 检查点** — 记忆已更新，未来重装 vnpy_qmt 后知悉需重新同步 preheater。

---

## Self-Review 自审结果

**1. Spec 覆盖**：
- 4.1 模块/类/常量 → Task 1（骨架+常量）✓
- 4.2 标的枚举+实测留痕 → Task 1（_collect_symbols）+ Task 2（_log_sector_stats）✓
- 4.3 时间范围（start_time，end_time 不传）→ Task 3 ✓
- 4.4 分批下载（callback/容错/失败粒度）→ Task 4 + Task 5 ✓
- 4.5 日志（进度+汇总 batches_ok/batches_fail/symbols/elapsed）→ Task 5 ✓
- 4.6 错误处理 → Task 1（板块异常）+ Task 4（批次异常）+ Task 5（空标的/外层兜底）✓
- 5 集成 run_qmt_server.py → Task 6 ✓
- 6 测试策略 6 用例 → Task 1-5 全覆盖（枚举去重/留痕/分批/容错/start_time/汇总）✓
- 交付物 → Task 6（同步）+ Task 7（记忆）✓

**2. Placeholder 扫描**：无 TBD/TODO；所有代码步骤含完整代码；命令含预期输出。✓

**3. 类型一致性**：
- `_collect_symbols -> tuple[list[str], dict[str, set[str]]]`：Task 1 定义，Task 5 preheat 解包 `symbols, sector_members = self._collect_symbols()` 一致 ✓
- `_log_sector_stats(sector_members: dict)`：Task 2 定义签名，Task 5 调用传入 sector_members 一致 ✓
- `_download_batch(batch, start_time) -> bool`：Task 4 定义，Task 5 调用一致 ✓
- `_format_elapsed`：Task 5 定义并测试 ✓
- SECTORS/BATCH_SIZE/BATCH_SLEEP/LOOKBACK_DAYS：Task 1 定义，Task 3/5 测试中覆盖（改 BATCH_SIZE/BATCH_SLEEP/LOOKBACK_DAYS 验证可配置）✓

无类型/签名漂移。

---

## 执行说明

**项目规则**：本计划不含 `git commit` 步骤（遵循"不主动提交"规则）。每个 Task 以测试通过/检查点为完成标志。若需提交，由用户在完成全部 Task 后统一决定。

**Python 环境**：`$PY` = `D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe`。pytest 通过 `$PY -m pytest` 调用。
