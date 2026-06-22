# 风控规则 get_account API 漂移适配 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 适配 8 处 `get_account()` 无参调用（3 规则 7 处 + manager.py 1 处），使其在 vnpy 4.4.0（`get_account(vt_accountid)` 需参数）下正常工作。

**Architecture:** 新增 `risk/_helpers.py` 的 `get_first_account(main_engine)`（`get_all_accounts()[0]`，无账户返回 None）；3 个规则 + manager.py 的 8 处 `get_account()` 替换为 `get_first_account(...)`，保留 `if not account` 守卫；manager.py:240 删除虚假 hasattr 守卫。

**Tech Stack:** Python 3.11 / unittest + unittest.mock / pytest / vnpy_riskmanager（集成验证）

**Spec:** `docs/superpowers/specs/2026-06-17-rule-get-account-api-drift-design.md`

**测试运行命令（统一）：**
```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest <path> -v
```

**提交约定：** 遵循项目 conventional commit + emoji。**output style：未获用户明确指示不主动 git 提交**——commit 步骤在执行时由用户授权后进行。

---

## 文件结构

| 文件 | 责任 | 动作 |
|---|---|---|
| `vnpy_china_rules/risk/_helpers.py` | `get_first_account(main_engine)` helper | 新建 |
| `vnpy_china_rules/tests/test_rules_helpers.py` | helper 单测 | 新建 |
| `vnpy_china_rules/risk/rules/capital_risk_rule.py` | 3 处 get_account 替换 | 修改 |
| `vnpy_china_rules/risk/rules/position_control_rule.py` | 3 处 get_account 替换 | 修改 |
| `vnpy_china_rules/risk/rules/stop_profit_loss_rule.py` | 1 处 get_account 替换 | 修改 |
| `vnpy_china_rules/risk/manager.py` | get_risk_status 的 get_account 替换 + 删 hasattr 守卫 | 修改 |

---

## Task 1: `_helpers.py` + `get_first_account` 单测

**Files:**
- Create: `vnpy_china_rules/risk/_helpers.py`
- Test: `vnpy_china_rules/tests/test_rules_helpers.py`

- [ ] **Step 1: 写失败测试**

创建 `vnpy_china_rules/tests/test_rules_helpers.py`：

```python
"""风控 helper 单测（不需 vnpy_riskmanager）"""

import unittest
from unittest.mock import MagicMock

from vnpy_china_rules.risk._helpers import get_first_account


class TestGetFirstAccount(unittest.TestCase):
    def test_returns_first_when_multiple(self):
        """多账户时返回首个"""
        a1 = MagicMock(name="account1")
        a2 = MagicMock(name="account2")
        main_engine = MagicMock()
        main_engine.get_all_accounts.return_value = [a1, a2]
        self.assertIs(get_first_account(main_engine), a1)

    def test_returns_none_when_empty(self):
        """无账户时返回 None"""
        main_engine = MagicMock()
        main_engine.get_all_accounts.return_value = []
        self.assertIsNone(get_first_account(main_engine))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_rules_helpers.py -v
```
Expected: FAIL（`ImportError: No module named 'vnpy_china_rules.risk._helpers'`）

- [ ] **Step 3: 实现 `_helpers.py`**

创建 `vnpy_china_rules/risk/_helpers.py`：

```python
"""风控共享 helper（vnpy 4.4.0 API 适配）"""

from typing import Optional

from vnpy.trader.object import AccountData


def get_first_account(main_engine) -> Optional[AccountData]:
    """获取首个账户（A股单账户场景）。

    vnpy 4.4.0 的 MainEngine.get_account(vt_accountid) 需要 vt_accountid，
    规则运行时无此信息，故用 get_all_accounts() 取首个。无账户返回 None
    （调用方现有 `if not account` 逻辑会跳过检查）。
    """
    accounts = main_engine.get_all_accounts()
    return accounts[0] if accounts else None
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_rules_helpers.py -v
```
Expected: PASS（2 个测试）

- [ ] **Step 5: 提交**（待用户授权）

```bash
git add vnpy_china_rules/risk/_helpers.py vnpy_china_rules/tests/test_rules_helpers.py
git commit -m "✨ feat(vnpy_china_rules): 新增get_first_account helper适配vnpy4.4.0 get_account签名"
```

---

## Task 2: 3 个规则替换 7 处 `get_account()`

**Files:**
- Modify: `vnpy_china_rules/risk/rules/capital_risk_rule.py`（顶部 import + 3 处: on_trade/on_timer/_check_capital_usage）
- Modify: `vnpy_china_rules/risk/rules/position_control_rule.py`（顶部 import + 3 处: 3 个仓位检查）
- Modify: `vnpy_china_rules/risk/rules/stop_profit_loss_rule.py`（顶部 import + 1 处: on_timer）

- [ ] **Step 1: 改 `capital_risk_rule.py`**

顶部 import 区（`from vnpy_riskmanager.template import RuleTemplate` 之后）加：

```python
from vnpy_china_rules.risk._helpers import get_first_account
```

替换 3 处（grep `main_engine.get_account()` 定位，均在 `self.risk_engine.main_engine.get_account()` 形式）：

```python
# 替换前（on_trade / on_timer / _check_capital_usage 各一处）
account = self.risk_engine.main_engine.get_account()
# 替换后
account = get_first_account(self.risk_engine.main_engine)
```

**保留**每处后续的 `if not account: return` / `if not account: return False` 守卫不变。

- [ ] **Step 2: 改 `position_control_rule.py`**

顶部 import 区加：

```python
from vnpy_china_rules.risk._helpers import get_first_account
```

替换 3 处（`_check_single_position_limit` / `_check_total_position_limit` / `_check_industry_limit` 各一处），替换模式同 Step 1。保留后续 `if not account: return False` 守卫。

- [ ] **Step 3: 改 `stop_profit_loss_rule.py`**

顶部 import 区（`from vnpy_riskmanager.template import RuleTemplate` 之后）加：

```python
from vnpy_china_rules.risk._helpers import get_first_account
```

替换 1 处（`on_timer` 内）：

```python
# 替换前
account = self.risk_engine.main_engine.get_account()
# 替换后
account = get_first_account(self.risk_engine.main_engine)
```

保留后续 `if account:` 守卫。

- [ ] **Step 4: 确认无残留 + 语法检查**

```bash
# 确认 3 个规则文件无残留的无参 get_account() 调用
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -c "import ast; [ast.parse(open(f).read()) for f in ['vnpy_china_rules/risk/rules/capital_risk_rule.py','vnpy_china_rules/risk/rules/position_control_rule.py','vnpy_china_rules/risk/rules/stop_profit_loss_rule.py']]; print('语法 OK')"
```
Expected: `语法 OK`（3 文件语法正确）

```bash
# grep 确认无残留 get_account() 无参调用（应只剩 get_first_account）
grep -n "get_account" vnpy_china_rules/risk/rules/*.py
```
Expected: 无 `.get_account()` 无参调用（`get_first_account` 不算）

- [ ] **Step 5: 提交**（待用户授权）

```bash
git add vnpy_china_rules/risk/rules/capital_risk_rule.py vnpy_china_rules/risk/rules/position_control_rule.py vnpy_china_rules/risk/rules/stop_profit_loss_rule.py
git commit -m "🐛 fix(vnpy_china_rules): 风控规则get_account无参调用适配vnpy4.4.0(改用get_first_account)"
```

---

## Task 3: `manager.py:240` 替换 + 删 hasattr 守卫

**Files:**
- Modify: `vnpy_china_rules/risk/manager.py`（顶部 import + `get_risk_status` 替换 + 删 hasattr）

- [ ] **Step 1: 顶部加 import**

在 `vnpy_china_rules/risk/manager.py` 顶部 import 区（`from vnpy_china_rules.datasource import DataSourceManager` 之后，或顶部 try/except 规则类导入之后）加：

```python
from vnpy_china_rules.risk._helpers import get_first_account
```

> 注：`_helpers` 是独立模块（不依赖 vnpy_riskmanager），manager.py 顶部 import 安全，不触发 `risk/rules/__init__.py` 的 RuleTemplate 加载。

- [ ] **Step 2: 替换 `get_risk_status` 的 get_account + 删 hasattr**

`get_risk_status` 方法（约 240 行）：

```python
# 替换前
account = self.main_engine.get_account() if hasattr(self.main_engine, "get_account") else None
# 替换后
account = get_first_account(self.main_engine)
```

删除虚假的 hasattr 守卫（vnpy MainEngine 必有 `get_account` 方法，hasattr 恒 True，防不住无参 TypeError）。保留后续 `if account:` 守卫。

- [ ] **Step 3: 语法 + 导入检查**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -c "from vnpy_china_rules.risk.manager import AStockRiskManager; print('manager import OK')"
```
Expected: `manager import OK`（无循环导入、语法正确）

- [ ] **Step 4: 全量回归**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/ -q
```
Expected: 新增 helper 单测（2）+ 既有 test_risk_manager（11）全绿；既有 10 pre-existing 失败不变；集成测试 3 skipped

- [ ] **Step 5: 提交**（待用户授权）

```bash
git add vnpy_china_rules/risk/manager.py
git commit -m "🐛 fix(vnpy_china_rules): get_risk_status适配vnpy4.4.0 get_account并删虚假hasattr守卫"
```

---

## Task 4: 集成验证（on_timer TypeError warning 消失）

**Files:** 无（仅验证）

- [ ] **Step 1: 跑集成测试（需 vnpy_riskmanager 已安装）**

```bash
RUN_INTEGRATION=1 D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_risk_integration.py -v
```
Expected: **3 passed**，且**无** `PytestUnhandledThreadExceptionWarning`（on_timer 的 `get_account()` TypeError 消失——无账户时 `get_first_account` 返回 None → 规则 `if not account` 跳过 → 不再调 `account.balance`）

- [ ] **Step 2: 对比修复前后的 warning**

修复前（v1 spec 记录）：3 passed + 1 warning（`TypeError: OmsEngine.get_account() missing 1 required positional argument: 'vt_accountid'`，来自 `capital_risk_rule.py:109` on_timer）

修复后：3 passed + **0 warning**（on_timer 不再因 get_account 崩溃）

若仍有 warning，定位其来源（可能其他 API 漂移），返回 Phase 1 调查。

- [ ] **Step 3: 无需提交**（本 task 仅验证，无代码改动）

---

## 验收检查（实现完成后）

- [ ] `risk/_helpers.py` 的 `get_first_account` helper 存在 + 2 单测全绿（Task 1）
- [ ] 3 个规则 7 处 + manager.py:240 共 8 处 `get_account()` 替换为 `get_first_account(...)`（Task 2/3）
- [ ] manager.py:240 虚假 hasattr 守卫已删（Task 3）
- [ ] 现有 `if not account` 守卫保留（Task 2/3）
- [ ] 集成测试 `RUN_INTEGRATION=1`：3 passed + **on_timer TypeError warning 消失**（Task 4）
- [ ] TradingLimitRule 未改
- [ ] 全量回归无新增失败（既有 10 pre-existing 不变）
