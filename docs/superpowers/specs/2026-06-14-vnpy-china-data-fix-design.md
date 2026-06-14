# vnpy_china_data 审查问题修复设计

> 日期：2026-06-14
> 模块：`vnpy_china_data`
> 状态：待实现
> 依据：代码审查报告（已逐项核实源码）

## 1. 背景

针对 `vnpy_china_data` 模块的代码审查报告列出 11 项问题。本设计基于对源码的逐文件核实（含 `python ast.parse` 语法验证与全库 Grep 调用链分析），剔除误报、修正夸大描述，保留所有真实问题，按 TDD 流程修复并补充单元测试。

### 1.1 审查报告核实结论

| # | 报告说法 | 实际核实 | 结论 |
|---|---|---|---|
| 1 | validator 缩进致"逻辑反转" | `ast.parse` 实测：整文件 `IndentationError`（第 59 行），**模块完全无法 import**；且 `DataValidator` 全库无外部引用 | 比报告更严重 |
| 2a | gui_engine `result["errors"]` 自引用覆盖 | 当前 `gui_engine.py` 的 `result` dict 无 error_count/errors 字段 | **误报**（代码不存在） |
| 3 | get_connection 连接泄漏 | 被广泛调用（`download_history_full.py`、`train_alpha_model.py`、`examples/`、`tests/` 共 9+ 处） | 真实且影响运行（升危） |
| 4 | service 日期参数类型不安全 | 已用 `isinstance(datetime)` + `isinstance(date)` 处理（service.py:1105-1111） | 夸大（已处理） |
| 9 | connect() 失败后查询"崩溃" | `base.py:22` 初始化 `_connected=False`，`qmt_adapter.connected` 返回 False 不崩溃；仅 `print` 不一致属实 | 部分误报 |
| 8 | requirements.txt 可能缺失 | 文件存在，含主要依赖，缺 `requests`/`openpyxl` | 部分准确 |
| 10 | get_sector_index 抛 AttributeError | `hasattr` 保护下静默返回空列表（非崩溃），但实现逻辑整体错误 | 危害描述不准 |
| 11 | 三指数成分股"完全相同" | ZZ500 实际不同；HS300/ZZ1000 相似；HS300 内 `000333.SZ` 重复 | 部分准确 |

## 2. 修复范围与原则

**决策（已与用户确认）：**
- 范围：全面修复 + 补充单元测试（TDD）
- validator.py：修复 + 接入数据校验流程
- get_sector_index：修复 QMT 本地实现

**通用原则：**
- TDD：每个修复点先写失败测试 → 改实现 → 测试转绿
- 按优先级分批（P0 → P1 → P2 → P3），每批独立可验证、可提交
- 最小改动：不重构无关代码，不顺带改风格
- YAGNI：成分股不接入 Tushare 真实数据源（无明确需求）

## 3. 详细修复项

### P0 — validator.py 无法导入 + 接入数据校验

**根因：** 第 57 行 `return False` 为 4 空格缩进（类体级别），导致 `IndentationError`，整模块不可加载。

**修复内容：**
1. 修正缩进：`validate_bar_data` 末尾 `return False` 归位到方法体（8 空格）
2. 修正逻辑反转：`if bar.volume < 0: return True` → `return False`
3. 修正 `validate_interval` 枚举：移除不存在的 `MINUTE_1/HOUR_1` 等，改为实际枚举 `[MINUTE, HOUR, DAILY, WEEKLY]`
4. 修正 `validate_exchange`：补 `Exchange.SHHK/SZHK/SEHK`
5. **接入数据流：** `database.save_bar_data` 入口增加 `bars = DataValidator.validate_bar_list(bars)` 过滤无效 bar，被过滤数量记 `logger.warning`

**校验白名单规则（明确放行/拒绝边界）：**

| 条件 | 判定 |
|---|---|
| `volume < 0` | 拒绝（数据错误） |
| 任一价格 `<= 0`（open/high/low/close） | 拒绝 |
| `high < low` | 拒绝 |
| `high < open` 或 `high < close` | 拒绝 |
| `low > open` 或 `low > close` | 拒绝 |
| `volume == 0`（停牌/空 bar） | **放行**（正常状态） |
| `volume > 0` 且价格合法 | 放行 |

> 关键：`volume == 0` 必须放行，避免误删停牌日的合法 bar。

**save_bar_data 过滤日志格式：** `logger.warning(f"save_bar_data 过滤 {filtered_count}/{total} 条无效 bar，示例: {示例symbol列表[:5]}")`，含数量与示例符号，便于观察误杀。不接入 GUI `write_log`——避免 database 层越权依赖 `main_engine`，破坏分层。

**测试（新建 `tests/test_validator.py`）：**
- `validate_bar_data`：正常 bar 通过、volume<0 拒绝、价格<=0 拒绝、high<low 拒绝
- `validate_bar_list`：混合列表正确过滤
- `validate_exchange`：含港股通枚举通过
- `validate_interval`：含实际枚举通过
- 集成：`save_bar_data` 传入含脏数据列表，仅存有效项

### P1 — get_connection 连接泄漏 + get_sector_index 错误

#### P1a. 连接泄漏（database.py:150）

**根因：** `get_connection` 上下文管理器 `finally: pass` 不归还连接，依赖 GC 延迟回收。该方法被 9+ 处 `with db.get_connection() as conn:` 调用，连接池仅 15 条（pool_size=5 + max_overflow=10），高频使用易耗尽。

**修复：** `finally: pass` → `finally: conn.close()`。所有现有调用方自动受益，无需改动调用点。

**测试：** mock `self._pool.connection()` 返回的连接对象，验证 with 块结束后 `close()` 被调用。

#### P1b. get_sector_index（qmt_adapter.py:1059）

**根因：** 调 `self._qmt_api.download_history_data`（`self._qmt_api` 是 `xtquant` 模块，无此方法），且假设返回 bars 列表（实际 `download_history_data` 是异步下载，不返回数据）。

**RPC 路径验证（已读取 rpc_qmt_adapter.py:555-578）：** RPC 路径实现正确——通过 `self._rpc_client.call("get_sector_index", ...)` 调用服务端，将返回的 dict 列表反序列化为 `BarData`。该路径不动，仅修复 QMT 本地路径。

**修复：** 参照同文件 `get_bar_data`（qmt_adapter.py:132）的两步下载模式重写：
1. `xtdata.download_history_data2` 异步下载到本地
2. `xtdata.get_local_data` 读取本地数据
3. 转换为 `BarData` 列表

**测试：** mock xtdata 模块，验证调用链 `download_history_data2` → `get_local_data`，返回正确 BarData 列表。

### P2 — print 不一致 + MemoryCache 死代码

- **service.py:164：** `print(f"数据服务连接失败: {e}")` → `logger.error(...)`，与模块其他位置统一
- **cache.py：** 删除 `MemoryCache` 类。删除前已核实：① 全库 Grep 无 `MemoryCache` 实例化与 import；② `__init__.py` 的 `__all__` 仅导出 `DataQueryCache`，未导出 `MemoryCache`，删除不影响模块公共 API。service.py Redis 连接失败时保持降级直连 API（合理设计，不强行加进程内内存兜底）

**测试：** 无需新增（删除死代码）；print→logger 通过现有日志断言覆盖。

### P3 — 低危清理与语义改进

| 项 | 文件 | 修复 |
|---|---|---|
| 表名拼接 | database.py:1251 | `get_database_stats` 增加表名白名单校验（正则 `^db_[a-z_]+$`），不匹配则跳过 |
| _parse_exchange 冗余 | gui_engine.py:424-436 | 移除 `or ".XXX" in symbol` 冗余分支，仅保留 `endswith` |
| 指数成分股 | gui_engine.py:374-395 | 删除 HS300 内 `000333.SZ` 重复项；加注释明确"占位示例数据，真实数据待接入 Tushare index_weight" |
| requirements | requirements.txt | 补 `requests`、`openpyxl`；`vnpy` 锁定为 `>=4.4.0`（对齐 CLAUDE.md 当前版本） |

**`_parse_exchange` 修改安全性（已 Grep 全库确认）：** `gui_engine._parse_exchange` 的所有调用方（`gui_engine.py:160` 内部调用 + `test_gui_engine.py`、`test_integration_real.py`、`test_integration_hk_connect.py` 共 4 处测试）均使用标准 `symbol.exchange` 格式（如 `"00700.SHHK"`、`"600000.SH"`），**无倒序格式**（如 `"SHHK.00700"`）。`endswith` 修改不影响标准格式行为。注：`vnpy_china_rules/strategy.py` 的 `ChinaStockStrategy._parse_exchange` 是不同类的方法，不受影响。

**新增 P3 项 — #7 download_bar_data 失败语义化（审查报告 #7）：**

**问题：** `service.download_bar_data` 返回空列表时，调用方无法区分「回补无新数据」与「API 实际失败」。

**修复：** 在 `service.download_bar_data` 返回空列表时，根据双数据源连接状态记录区分性日志（与 `_fetch_bars_from_api` 的 QMT→Tushare 回退链对应）：
- QMT 与 Tushare 均未连接 → `logger.warning("下载失败: {symbol} 数据源均未连接")`
- 至少一个数据源已连接但无数据 → `logger.info("无新数据: {symbol} 该区间无回补")`

> 注：`_fetch_bars_from_api` 在 API 调用异常时已 `logger.warning`（service.py:285/309），本项补的是「连接正常但返回空」的区分性日志，不改动 `_fetch_bars_from_api` 返回语义。

**测试：**
- `_parse_exchange`（纯函数，9 种后缀用例，含纯 symbol 无后缀分支）
- `get_index_symbols` 返回值无重复
- `download_bar_data` 空返回时：mock adapter 未连接 → 验证 warning；已连接 → 验证 info

## 4. 不在本次范围（YAGNI）

- **#2a error_count 自引用：** 当前代码不存在，误报，无需修复
- **#4 日期参数：** 已正确处理，仅加防御性类型校验注释
- **#9 connect 崩溃：** base.py 已初始化 `_connected`，不崩溃，仅修 print
- 接入 Tushare 真实指数成分股
- UI 层（`ui/widget.py`）测试（需 Qt 环境，成本高、无明确需求）

## 5. 测试策略

- **框架：** pytest（项目现有测试位于 `vnpy_china_data/tests/`）
- **新增测试文件：** `vnpy_china_data/tests/test_validator.py`
- **扩展测试文件：** `vnpy_china_data/tests/test_gui_engine.py`、`vnpy_china_data/tests/test_qmt_adapter.py`（已有，补充用例）
- **mock 策略：** xtdata、连接池等外部依赖用 `unittest.mock`
- **TDD 顺序：** 每个修复点先写失败测试，确认失败原因符合预期，再改实现

## 6. 实施分批顺序

| 批次 | 内容 | 可独立验证 |
|---|---|---|
| 第 1 批 | P0 validator 修复 + 接入 + 测试 | `import DataValidator` 成功；validator 测试绿 |
| 第 2 批 | P1a 连接泄漏 + P1b get_sector_index + 测试 | 连接归还测试绿；qmt_adapter 测试绿 |
| 第 3 批 | P2 print→logger + MemoryCache 删除 | 模块导入无报错；Grep 确认 MemoryCache 已移除 |
| 第 4 批 | P3 表名白名单 + _parse_exchange + 成分股 + requirements + download_bar_data 语义化日志 | 相关测试绿 |

## 7. 验收标准

1. `python -c "import ast; ast.parse(open('vnpy_china_data/validator.py').read())"` 通过
2. `from vnpy_china_data.validator import DataValidator` 可导入
3. `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/` 全绿
4. 连接池验证：循环调用 `get_connection` 100 次后，池中空闲连接数不下降
5. `get_sector_index` mock 测试验证两步调用链
6. 全库 Grep 无 `MemoryCache` 残留引用

## 8. 风险与回滚

- **save_bar_data 接入 validator 风险：** 若校验逻辑过严，可能误删合法数据。缓解：校验规则已明确为 P0 白名单规则表（`volume==0` 放行，仅 `volume<0`/价格非法/高低价倒挂拒绝）；接入后通过 `save_bar_data 过滤 N/M 条` 的 logger.warning 观察误杀量。
- **get_sector_index 重写风险：** 依赖 xtdata API，本地无 QMT 环境时无法实测。缓解：用 mock 覆盖，真实环境留待用户验证。
- **回滚：** 每批独立提交（用户批准后），可按批回滚。
