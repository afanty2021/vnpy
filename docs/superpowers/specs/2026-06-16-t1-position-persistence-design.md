# T+1 持仓记录持久化设计

> 日期：2026-06-16
> 模块：`vnpy_china_rules`
> 状态：待实现（spec 已审定，待生成实现计划）

## 1. 背景与问题

`T1RulesEngine`（`engine.py:67-196`）当前用纯内存管理 T+1 持仓：

- 数据结构：`self.positions: Dict[str, List[PositionRecord]] = defaultdict(list)`
- `PositionRecord(symbol, volume, buy_datetime, available)`
- `record_buy` 追加批次，`record_sell` 按 FIFO 扣减 `available`，`get_sellable_volume` 用 `buy_datetime.date()` 判断可卖

**问题**：纯内存。进程重启后 `self.positions` 清空 → 当日买入记录丢失 → `get_sellable_volume` 返回 0 的保护失效 → **当日买入可立即卖出，T+1 规则失效**。对实盘风控而言是功能缺口。

## 2. 目标与非目标

**目标**
- 进程重启后，T+1 引擎从持久化存储恢复可卖数量，T+1 规则跨重启生效。
- 复用项目已有 MySQL 基础设施（`vnpy_china_reporting.data_source.db.DataSourceDB`），DRY。
- rules 模块保持 DB 可选，向后兼容纯内存模式（单测不依赖 DB）。

**非目标（YAGNI）**
- 不做多账户/多策略隔离（单账户级 T+1 语义）。
- 不做与 broker 真实持仓的对账。
- 不做 checkpoint/watermark 优化（全量重放，数据量增长后再议）。

## 3. 架构：事件溯源（Event Sourcing）

**核心思路**：成交是事实，持仓是派生态。

- 流水表 `t1_trade_flow` **append-only** 记录每笔成交（不可改、不可删，审计完整）。
- `T1RulesEngine.self.positions` 是流水的"投影"，启动时从流水重放重建。
- `record_buy/record_sell` 既是内存操作，也是重放入口 —— **零逻辑重复**（FIFO 扣减、可卖量计算仍由现有引擎逻辑完成，持久化层只负责"存成交 + 读成交"）。

**最小改动原则**：`T1RulesEngine` **不改动**（保持纯内存语义）。持久化协调全部由上层 `ChinaStockRulesEngine` 完成（持有 store、on_trade 双写、初始化重放）。

## 4. 数据模型

```sql
CREATE TABLE IF NOT EXISTS t1_trade_flow (
    id          BIGINT NOT NULL AUTO_INCREMENT,
    trade_id    VARCHAR(64) NOT NULL COMMENT '成交唯一键(trade.vt_tradeid)，幂等去重',
    symbol      VARCHAR(32) NOT NULL COMMENT '股票代码',
    direction   VARCHAR(8)  NOT NULL COMMENT 'Direction.value：多=买 / 空=卖',
    volume      INT NOT NULL COMMENT '成交数量',
    trade_time  DATETIME(3) NOT NULL COMMENT '成交时间(毫秒精度，重放排序依据)',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_trade_id (trade_id),   -- 幂等：重启重放已落库成交自动去重
    INDEX idx_symbol_time (symbol, trade_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='T+1成交流水（append-only事件源）'
```

- `trade_id` = `trade.vt_tradeid`（`f"{gateway_name}.{tradeid}"`，全局唯一），`INSERT IGNORE` + `uk_trade_id` 幂等。
- `direction` 存 `Direction.value`（中文 `"多"`/`"空"`），重放时用枚举值比较分派（`Direction.LONG.value`）。
- `trade_time` 用 `DATETIME(3)` 保留毫秒，保证重放排序确定性；排序键 `(trade_time, id)`，`id` 作同毫秒成交的稳定tiebreaker。

## 5. 组件设计

### 5.1 `T1PositionStore`（新增 · `vnpy_china_rules/t1_store.py`）

流水表 CRUD。**不硬依赖 `vnpy_china_reporting`** —— 接收一个满足协议（`execute(sql, args)->int`、`query(sql, args)->List[dict]`）的 db 对象（`DataSourceDB` 满足鸭子类型），由上层注入。rules 模块保持零新增硬依赖。

```python
class T1PositionStore:
    def __init__(self, db):           # db: 协议对象（DataSourceDB 等）
        self.db = db

    def init_schema(self) -> None:
        """幂等建表（CREATE TABLE IF NOT EXISTS）"""

    def append_trade(self, trade_id, symbol, direction, volume, trade_time) -> int:
        """INSERT IGNORE，返回受影响行数（0=重复已忽略）"""

    def load_all(self) -> List[dict]:
        """SELECT 全表，ORDER BY trade_time, id；每行含
        symbol/direction/volume/trade_time"""
```

### 5.2 `T1RulesEngine`（**不改动**）

保持现有纯内存实现。重放时由上层调用其 `record_buy/record_sell`，逻辑与正常成交完全一致。

### 5.3 `ChinaStockRulesEngine`（改造）

- `__init__` 增加 `db: Optional = None` 参数。
  - `db` 提供：`self.store = T1PositionStore(db)` → `init_schema()` → `self._replay()`（重放后再接受新成交）。
  - `db` 为 None：`self.store = None`，纯内存模式（现有行为）。
- `on_trade`：先 `store.append_trade(...)`（try/except 降级），再 `self.t1_rules.record_buy/sell(...)`。
- `_replay()`：`for row in self.store.load_all():` 按 direction 分派 `record_buy`/`record_sell`。

### 5.4 schema 初始化

`init_schema` 在 `ChinaStockRulesEngine.__init__`（db 注入时）调用，幂等。DDL 常量定义在 `t1_store.py`（表归属 rules）。

## 6. 数据流

### 6.1 成交写入（`on_trade`，DB 优先）

```
on_trade(trade):
    # 单次计算时间戳，DB 与内存共用，避免 now() 不幂等（原始执行与重放 trade_time 漂移）
    trade_time = trade.datetime or datetime.now()
    if self.store:
        try:
            self.store.append_trade(trade.vt_tradeid, trade.symbol,
                                    trade.direction.value, int(trade.volume),
                                    trade_time)
        except Exception as e:
            logger.warning(f"T+1流水写入失败，降级纯内存: {e}")
    # 无论 DB 是否成功，内存都更新（T+1 检查的权威），使用同一 trade_time
    if trade.direction == Direction.LONG:
        self.t1_rules.record_buy(trade.symbol, int(trade.volume), trade_time)
    elif trade.direction == Direction.SHORT:
        self.t1_rules.record_sell(trade.symbol, int(trade.volume), trade_time)
```

**先 DB 后内存**：DB 是崩溃恢复的权威，先落库保证重启不丢；内存是检查权威，紧随更新。
**时间戳幂等**：`trade_time` 在 `on_trade` 内单次计算、DB 与内存共用。重放时只读 DB 已落库的 `trade_time`（不重新 `now()`），保证原始执行与重放结果一致。

### 6.2 启动重放（`ChinaStockRulesEngine.__init__` 末尾，db 注入时）

```
def _replay(self):
    for row in self.store.load_all():
        dt = row["trade_time"]   # datetime
        if row["direction"] == Direction.LONG.value:      # "多"
            self.t1_rules.record_buy(row["symbol"], int(row["volume"]), dt)
        elif row["direction"] == Direction.SHORT.value:   # "空"
            self.t1_rules.record_sell(row["symbol"], int(row["volume"]), dt)
        # NET 或异常值：跳过（不应出现在成交流水，与 on_trade 一致）
```

内存从空重建；重放**只读 DB、写内存**，不回写 DB（无双写冲突）。

### 6.3 重放范围

默认全表（T+1 需知老批次是否卖完，须从最早重放）。数据量显著增长后再加 watermark 优化（非本期）。

## 7. 错误处理与边界

| 场景 | 策略 |
|---|---|
| MySQL 不可用（未装/连不上） | `db=None`，`store=None`，退化为纯内存，`logger.warning` 告警"T+1持久化不可用，重启将丢失记录"，**不阻断交易**。与 `vnpy_china_reporting` 的 `_DB_AVAILABLE` 降级模式一致 |
| `on_trade` 写 DB 失败 | catch 异常、告警，内存仍更新（当前会话 T+1 有效；仅丢失跨重启持久化） |
| 重复成交（重启重放） | `uk_trade_id` + `INSERT IGNORE` 幂等去重 |
| 并发 | 单 rules 实例/单账户；多策略共用实例 → 流水按账户总持仓算 T+1（符合 A 股账户级语义）；并发写由 `DataSourceDB` 连接池兜底 |

### 冷启动边界（已确认默认策略）

**场景**：rules 引擎**首次启用**持久化时，账户已有历史持仓，但其买入日期不在 `t1_trade_flow` 中。

**默认策略：流水为准，历史持仓视为已过 T+1（可卖）**
- 理由：rules 只管控自身记录的成交；存量持仓假定非当日（本就可卖），且大概率早已过 T+1。
- 局限：启用当天若有账户外手动买入，T+1 无法拦截 —— 但那本就不在 rules 管控范围。

## 8. 测试策略

### 8.1 单元测试（纯内存 + mock，CI 必跑）

| 测试对象 | 验证点 |
|---|---|
| `T1PositionStore`（mock db） | `append_trade` 生成 `INSERT IGNORE` + 正确参数；`load_all` 按 `(trade_time, id)` 排序返回；`init_schema` 调用 DDL 且幂等 |
| 重放一致性 | 注入 mock store 返回预设流水 → 重放后 `t1_rules.positions` 与"连续 record 同样成交"的纯内存实例**逐字段相等**（含 FIFO 扣减后的 available） |
| 降级兼容 | `db=None` 时行为 = 现有纯内存；现有 `test_engine.py` 的 T1 用例**全绿不破坏** |
| `on_trade` 写 DB 失败 | mock store 抛异常 → 告警日志 + 内存仍更新（不阻断） |

### 8.2 集成测试（需 MySQL，`@pytest.mark.integration`，默认跳过）

- 真实 `DataSourceDB` → append 3 笔（buy/buy/sell FIFO）→ 新建引擎实例 `load_all` 重放 → 内存持仓与原实例一致。
- 幂等：同一 `trade_id` 重复 append，`load_all` 不翻倍。

### 8.3 文件落点
- 扩展 `vnpy_china_rules/tests/test_engine.py`（重放/降级用例）
- 新增 `vnpy_china_rules/tests/test_t1_store.py`（Store 单测，mock db）
- 新增 `vnpy_china_rules/tests/test_t1_persistence_integration.py`（集成，标记跳过）

mock 用标准库 `unittest.mock`，不引入新依赖。

## 9. 集成点与依赖

- **db 来源**：上层（`app.py`/`gui_engine.py` 或实盘启动代码）用 `DataSourceDB.from_global_config(config)` 创建，注入 `ChinaStockRulesEngine(db=...)`。rules 模块不创建 db（依赖注入，解耦）。
- **DataSourceDB 协议已核实**：`execute(sql, args)->int`、`query(sql, args)->List[dict]`（`vnpy_china_reporting/data_source/db.py:113-130`），与 `T1PositionStore` 期望一致。实现时 `T1PositionStore.__init__` 仍加 `hasattr(db, "execute") and hasattr(db, "query")` 防御性校验，缺则告警降级。
- **配置**：复用 `vnpy_china_config.GlobalConfig` 的 database 字段（MySQL 连接信息），与 `vnpy_china_reporting` 同源。
- **运行时依赖（可选）**：`pymysql`、`dbutils` —— 已被 `vnpy_china_reporting` 声明，复用；rules 模块本身**不新增硬依赖**（db=None 时不触发 import）。

## 10. 风险与权衡

| 点 | 取舍 |
|---|---|
| 事件溯源 vs 持仓批次表 | 选事件溯源：审计完整、逻辑零重复（复用 record_*）。代价：重启全量重放（低频小数据量可接受） |
| 全量重放 | 多年累积后重启变慢。缓解：本期不做，数据量增长后加 checkpoint（YAGNI） |
| DB 可选注入 | rules 保持零硬依赖、可独立单测。代价：实盘需上层正确注入 db |
| 冷启动历史持仓 | 默认视为可卖。接受"账户外当日手动买入不被拦截"的局限（不在 rules 管控范围） |
