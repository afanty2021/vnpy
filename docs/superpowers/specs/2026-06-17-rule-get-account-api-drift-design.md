# 风控规则 get_account API 漂移适配 设计

> 日期：2026-06-17 | 状态：待 review（v2，补 manager.py:240 + 修正 helper 路径）| 模块：`vnpy_china_rules/risk`

## 背景

`vnpy_china_rules/risk/` 下多处调用 `main_engine.get_account()` **无参**，但 vnpy 4.4.0 的 `OmsEngine.get_account(vt_accountid: str)` **需要 vt_accountid 参数**（`vnpy/trader/engine.py:486`）。运行时抛 `TypeError: missing 1 required positional argument 'vt_accountid'`。

2026-06-17 装 vnpy_riskmanager 后跑 `RUN_INTEGRATION=1` 集成测试时暴露——规则的 `on_timer` 在后台 EventEngine 线程异步触发该错误（pytest 捕获为 `PytestUnhandledThreadExceptionWarning`，不影响测试通过但回调失效）。此前因 vnpy_riskmanager 未安装、规则注册路径未真正运行而长期隐藏。

## 目标

适配 8 处 `get_account()` 无参调用（3 个规则的 7 处 + manager.py 的 1 处），使其在 vnpy 4.4.0 下正常工作。账户获取策略：**取首个账户**（A股单账户场景），无账户返回 None（现有 `if not account` 逻辑跳过检查）。

## 接口约束（vnpy 4.4.0 源码确认）

```python
# vnpy/trader/engine.py:486
def get_account(self, vt_accountid: str) -> AccountData | None:
    return self.accounts.get(vt_accountid, None)

# vnpy/trader/engine.py:528
def get_all_accounts(self) -> list[AccountData]:
    return list(self.accounts.values())
```

`get_tick(vt_symbol)` / `get_contract(vt_symbol)` 签名未变，规则已正确传参，无需适配。

## 漂移点清单（8 处）

| 文件 | 行 | 方法 | 说明 |
|---|---|---|---|
| `capital_risk_rule.py` | 83 | `on_trade` | 规则 |
| `capital_risk_rule.py` | 109 | `on_timer` | 规则 |
| `capital_risk_rule.py` | 145 | `_check_capital_usage` | 规则 |
| `position_control_rule.py` | 134 | `_check_single_position_limit` | 规则 |
| `position_control_rule.py` | 169 | `_check_total_position_limit` | 规则 |
| `position_control_rule.py` | 207 | `_check_industry_limit` | 规则 |
| `stop_profit_loss_rule.py` | 172 | `on_timer` | 规则 |
| `manager.py` | 240 | `get_risk_status`（AStockRiskManager） | 管理器，带虚假 hasattr 守卫 |

## 设计

### 1. 新增共享 helper（`vnpy_china_rules/risk/_helpers.py`）

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

**路径选择**：放 `risk/_helpers.py`（**非** `risk/rules/_helpers.py`）。原因：`manager.py` import 时不能触发 `risk/rules/__init__.py` 的 `from vnpy_riskmanager.template import RuleTemplate`（会破坏 manager.py 在 vnpy_riskmanager 缺失时的降级）。`risk/_helpers.py` 是独立模块，不依赖 vnpy_riskmanager，manager.py 和规则都能安全 import。

### 2. 替换 8 处 `get_account()`（3 规则 7 处 + manager.py 1 处）

**3 个规则**（7 处）：每个规则文件顶部加 `from vnpy_china_rules.risk._helpers import get_first_account`，统一替换：

```python
# 替换前
account = self.risk_engine.main_engine.get_account()
# 替换后
account = get_first_account(self.risk_engine.main_engine)
```

规则现有的 `if not account: return` / `if not account: return False` / `if account:` 逻辑**原样保留**——helper 返回 None 时这些守卫自然跳过检查。

**manager.py:240**（`get_risk_status`）：顶部加 `from vnpy_china_rules.risk._helpers import get_first_account`，替换并**删除虚假的 hasattr 守卫**（`hasattr(self.main_engine, "get_account")` 恒为 True——vnpy MainEngine 必有该方法，守卫防不住无参调用的 TypeError）：

```python
# 替换前
account = self.main_engine.get_account() if hasattr(self.main_engine, "get_account") else None
# 替换后
account = get_first_account(self.main_engine)
```

### 3. TradingLimitRule 无需改

`get_tick(req.vt_symbol)` / `get_contract(vt_symbol)` 签名 vnpy 4.4.0 未变，规则已正确传参。

## 测试策略

### helper 单测（新建 `vnpy_china_rules/tests/test_rules_helpers.py`，不需 vnpy_riskmanager）

- `test_get_first_account_returns_first`：`get_all_accounts` 返回多账户时，返回首个
- `test_get_first_account_empty_returns_none`：`get_all_accounts` 返回 `[]` 时，返回 None
- 用 `MagicMock` 模拟 main_engine

### 集成验证（已有 `test_risk_integration.py`，`RUN_INTEGRATION=1`）

修复后重跑集成测试，确认 `on_timer` 的 `TypeError` warning **消失**（无账户时 helper 返回 None → 规则 `if not account` 跳过 → 不再调 `account.balance` 等）。

## 验收标准

- [ ] 新增 `risk/_helpers.py` + `get_first_account` helper
- [ ] 3 个规则 7 处 + manager.py:240 共 8 处 `get_account()` 替换为 `get_first_account(...)`
- [ ] manager.py:240 删除虚假的 hasattr 守卫
- [ ] 现有 `if not account` 守卫保留
- [ ] helper 单测全绿（2 用例，不需 vnpy_riskmanager）
- [ ] 集成测试 `RUN_INTEGRATION=1`：3 passed，**on_timer TypeError warning 消失**
- [ ] TradingLimitRule 未改
- [ ] 全量回归无新增失败（既有 10 pre-existing 不变）

## 范围外（YAGNI）

- 不改规则的风控逻辑（阈值、检查算法）
- 不适配多账户（单账户 helper；多账户需 vt_accountid 配置驱动，列为未来改进）
- 不改 TradingLimitRule
- 不改 `get_tick` / `get_contract`（签名未变）

## 变更记录

- **v2**（本次）：(1) 漂移点清单补 `manager.py:240` `get_risk_status`（第 8 处，含虚假 hasattr 守卫删除）；(2) helper 路径从 `risk/rules/_helpers.py` 改为 `risk/_helpers.py`，避免 manager.py import 触发 `risk/rules/__init__.py` 的 RuleTemplate 加载而破坏降级
- **v1**：初版（7 处规则漂移）
