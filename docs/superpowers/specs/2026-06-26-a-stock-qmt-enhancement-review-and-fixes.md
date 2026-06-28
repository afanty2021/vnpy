# A股 QMT 增强代码 审查与修复 记录文档

> 日期：2026-06-26
> 审查范围：`examples/client_server/`（run_qmt_client / run_qmt_server_full）、`patches/`（td / md / qmt_gateway / qmt_preheater）
> 分支：`fix/a-stock-qmt-enhancement-review`
> 状态：修复已落地本分支，**待 Windows 环境部署 + 集成验证**

## 1. 背景与目标

对近期 A股交易系统增强（持仓市值列+自动订阅、成交周期查询去重、量比缓存按交易日失效、日线预热进程隔离、配置收敛、日志落盘等）做一次面向召回的全面代码审查，定位**正确性 bug、并发/资源/错误处理、T+1 持仓与账号数据一致性、行情订阅与市值计算、复用/简化/效率**问题，并给出可执行的手术式修复。

## 2. 审查方法

- 6 路并行 finder（正确性×3 + 清理 + 深度 + 规范），每路 ≤6 候选；
- 框架源码逐条核验（`vnpy/trader/ui/widget.py`、`object.py`）确认 `TradeMonitor.data_key=""`、`TickData.limit_up` 默认 `0`、`TradeData.vt_tradeid` 存在等关键事实；
- 1 票核验、按严重度排序，正确性优先于清理。

## 3. 问题清单（10 项 + 清理）

| # | 严重度 | 文件:行 | 问题 | 状态 |
|---|--------|---------|------|------|
| 1 | 🔴P1 | `patches/td.py:194-222` | `on_stock_trade` 对"本地无 `self.orders` 记录"的成交（外部/手动/跨策略委托，`order_remark` 缺失）静默 `return` 丢弃；周期 `query_trade` 给出虚假安全感 | ✅已修 |
| 2 | 🔴P1 | `patches/md.py:110-167` | `on_tick` 全程无 try；`rsplit`/五档索引/字段缺失任一异常中断整批 tick | ✅已修 |
| 3 | 🔴P1 | `patches/md.py:161-162` | `tick.limit_up/down` 对未建池标的置 `None`（覆盖默认 0），下游涨跌停算术 TypeError | ✅已修 |
| 4 | 🔴P1 | `patches/td.py:171-192` | `on_stock_position` 的 pnl 计算无 None 防御，单坏行 TypeError 中断整批持仓回调 | ✅已修 |
| 5 | 🔴P1 | `run_qmt_client.py:453-464` | `subscribe_positions` 闭包无 try/except，异常逃逸进 Qt 事件循环，QTimer 每 10s 重复失败无日志无退避 | ✅已修 |
| 6 | 🟠P2 | `patches/qmt_preheater.py:131-167` | 预热一次性、无重试；miniQMT 启动期偶发慢则大量批次超时，量比全天为 0 直到重启 | ⏸️延后（见 §5） |
| 7 | 🟠P2 | `run_qmt_client.py:510-515` | 成交快照重推可能重复行（`TradeMonitor.data_key=""` 无去重） | ✅已修 |
| 8 | 🟠P2 | `patches/td.py:215-221` | `vt_tradeid` 去重用了全字段相等，改单/重发的成交会被双计 | ✅已修 |
| 9 | 🟠P2 | `patches/md.py:429` | `BarData(interval=...)` 在 RPC/dict 路径传入字符串，破坏 `Interval\|None` 类型契约且 period 兜底 1d | ✅已修 |
| 10 | 🟡P2 | `test_xtquant_direct.py:14-15` | 调试脚本硬编码真实资金账号 `40218291` + QMT 路径 | ✅已修（改读环境变量） |
| C1 | ♻️清理 | `run_qmt_client.py:354/427/488` | `ConfigManager` reset+reload 三处重复（反复失效单例 + 重读盘） | ✅已修 |
| C2 | ♻️清理 | `run_qmt_client.py:239` | `_resolve_contract_name` 与 `PositionMonitor._get_position_name` 逐字重复 | ⏸️延后 |
| C3 | ♻️清理 | `run_qmt_client.py:180-324` | Account/Order/Trade 四个近重复 patch 函数 | ⏸️延后 |
| C4 | ♻️清理 | `patches/md.py:335-369` | `query_history` 内 `import time/traceback` 重复 | ✅已修 |
| C5 | ♻️清理 | `patches/md.py:64-108` | `get_contract` 每标的两次 xtdata 往返无批量化 | ⏸️延后 |

## 4. 修复详情

### 4.1 `patches/td.py`（#1 / #4 / #8 + 现金告警）

- **#1 成交不丢弃**：`on_stock_trade` 移除 `if vn_oid is None: return` 与 `if order is None: return` 两个早退门；`orderid=vn_oid if vn_oid else trade.traded_id`（缺失时回退 `traded_id`，仅影响"成交→委托"关联展示，不再阻断推送）。`to_vn_contract` 加 try。
- **#8 去重改成员判定**：`if vt_tradeid in self.traders: return`（原 `old_trade == trade_` 全字段相等）。修改单/重发致 `price/volume` 变化不再被当新成交双计。
- **#4 持仓 None 防御**：`on_stock_position` 整体纳入 try，`market_value = position.market_value or 0`；单坏行 `write_log` 后跳过，不再中断 `on_stock_positions_callback` 整批。
- **现金回退告警**：`cash/available_cash/buying_power` 全缺时回退 `total_asset` 并 `write_log`，不再静默；`market_value` 缺失 `or 0`。

### 4.2 `patches/md.py`（#2 / #3 / #9 + C4）

- **#2 on_tick 异常隔离**：抽 `_build_tick(symbol, exchange, data)`；`on_tick` 按 code（`ValueError/KeyError`）与按 data（`IndexError/KeyError/TypeError`）两层 try，单点异常只 `write_log` + 跳过本条，不波及同批其余 tick。
- **#3 涨跌停默认 0**：`tick.limit_up = self.limit_ups.get(tick.vt_symbol, 0)`（原默认 `None`）。
- **#9 interval 枚举化**：新增模块级 `_PERIOD_TO_INTERVAL`，`query_history` 中 `if not isinstance(interval, Interval): interval = _PERIOD_TO_INTERVAL.get(period, Interval.DAILY)`，`BarData.interval` 必为枚举。
- **C4**：顶层 `import time`/`import traceback`，移除 `query_history` 内 4 处重复 import。

### 4.3 `examples/client_server/run_qmt_client.py`（#5 / #7 + C1）

- **#5 订阅异常防护**：`subscribe_positions` 闭包 `try/except Exception` + `print` 日志；断线时不再每 10s 静默重复失败。
- **#7 成交去重**：`TradeMonitor.data_key = "vt_tradeid"`（已核 `widget.py:355-358` 走 insert-once/update 分支）；根治快照重推与"实时成交先到→重推再插"竞态产生的重复行。
- **C1 配置单次加载**：新增 `_load_global_config()`，`load_rpc_config(config=None)` 支持复用；`start_gui_with_rpc` 顶部加载一次，日志/RPC/报表三处共享，`reset_instance` 由 3 次降到 1 次。
- 显示：`AccountMonitor` 的 `cash`/缺省值 `0 → 0.0`，保持 `_new_set_content` 的浮点格式化。

### 4.4 测试 / 安全（#10）

- `test_xtquant_direct.py`：`account_id`/`mini_path` 改读 `QMT_ACCOUNT_ID`/`QMT_MINI_PATH` 环境变量，缺失则提示退出，杜绝硬编码账号入库。
- `test_td_trade_dedup.py`：新增用例 [5]/[5b]——`order_remark=None` 且无缓存 order 的成交仍推送、重复按 `traded_id` 去重，锁定 #1 修复行为。

## 5. 主动延后项（避免重写工作正常的代码）

| 项 | 原因 |
|----|------|
| #6 预热失败重试 | 需设计"失败批次再轮询 + 按需补"策略，且需 Windows 实测调参；本轮不动 |
| C2 Order/TradeMonitor 子类化复用 `_get_position_name` | 较大重构，触及工作正常的 patch；收益有限 |
| C3 Account/Order/Trade patch 参数化 | 同上，四个近重复函数统一为子类化 |
| C5 `get_contract` 批量化 | 上游 vnpy_qmt 既有代码，非本次增强引入；改 `to_vn_product` 推导有行为风险 |
| `query_history` 的 `time.sleep(2)` | 异步下载完成的兜底，贸然删除可能读空；保留 |

## 6. 验证

**已完成（macOS）：**
- ✅ 5 文件 `python -m py_compile` 全通过
- ✅ 沙箱单测（`test_td_trade_dedup.py` 用 `importlib` 按文件路径直接加载 `patches/td.py`，依赖已安装的 `xtquant` 与上游 `vnpy_qmt.utils`；不依赖 site-packages 部署）6/6 通过：无缓存 order 推送、重复/改单去重、带 remark 推送、`market_value=None` 不崩
- ✅ `grep` 确认 `md.py` 内已无残留 inline `import time/traceback`

**Windows 待做（用户）：**
- [ ] `python patches/deploy_vnpy_qmt_fix.py` 部署 td.py / md.py 到 site-packages
- [ ] `python examples/client_server/test_td_trade_dedup.py` —— 用例 [1]-[5] 全 PASS（含新增 [5] 无缓存 order）
- [ ] 实盘/模拟盘验证：外部委托成交能在 TradeMonitor 显示；停牌标的 tick 不再中断行情；市值/可用现金列显示正常

## 7. 部署与回滚

- **部署**：`patches/` 的修复须用 `patches/deploy_vnpy_qmt_fix.py` 写入 Windows site-packages 的 `vnpy_qmt/` 方才生效（运行时读 site-packages，不读 `patches/`）。`run_qmt_client.py` 在 Mac 客户端运行，随分支更新即可。
- **回滚**：`git checkout master`（或 `git revert` 本分支相应提交）+ 用 `patches/backups/` 或重装 `vnpy_qmt==0.3.3` 还原 site-packages。
- **提交规则**：本分支提交已经用户批准；后续 push、部署 site-packages 仍需显式确认。

## 8. 提交结构

1. `📝 docs(review): A股QMT增强代码审查问题清单与修复方案`
2. `🐛 fix(qmt_td): 成交不再丢弃/去重改tradeid/持仓None防御/现金回退告警`
3. `🐛 fix(qmt_md): on_tick异常隔离+涨跌停默认0+interval枚举化+清理重复import`
4. `🐛 fix(qmt_client): 订阅异常防护+成交去重+配置单次加载+cash浮点`
5. `✅ test(qmt_td): 补无缓存order成交回归用例 + 调试脚本账号脱敏`
