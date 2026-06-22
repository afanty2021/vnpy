# T+1 持仓记录持久化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `ChinaStockRulesEngine` 的 T+1 持仓记录在进程重启后可从 MySQL 流水表恢复，T+1 规则跨重启生效。

**Architecture:** 事件溯源 —— `t1_trade_flow` 表 append-only 记录每笔成交；`ChinaStockRulesEngine` 在 `__init__`（db 注入时）从流水重放重建 `T1RulesEngine` 的内存持仓；`on_trade` 先落库后更新内存。`T1RulesEngine` 零改动。

**Tech Stack:** Python 3.11 / pymysql+DBUtils（经 `vnpy_china_reporting.data_source.db.DataSourceDB`）/ unittest + unittest.mock / pytest 运行器

**Spec:** `docs/superpowers/specs/2026-06-16-t1-position-persistence-design.md`

**测试运行命令（统一）：**
```bash
conda run -n Quant-3.11 python -m pytest <path> -v
```

**提交约定：** 遵循项目 conventional commit + emoji 风格（见近期 commit）。

---

## 文件结构

| 文件 | 责任 | 动作 |
|---|---|---|
| `vnpy_china_rules/t1_store.py` | `t1_trade_flow` DDL + `T1PositionStore`（init_schema/append_trade/load_all） | 新建 |
| `vnpy_china_rules/engine.py` | `ChinaStockRulesEngine`：`__init__` 加 `db` 参数、新增 `_replay`、`on_trade` 双写 | 修改 |
| `vnpy_china_rules/tests/test_t1_store.py` | `T1PositionStore` 单测（mock db） | 新建 |
| `vnpy_china_rules/tests/test_engine.py` | 新增 `TestT1PersistenceReplay`（重放一致性/降级） | 修改 |
| `vnpy_china_rules/tests/test_t1_persistence_integration.py` | MySQL 端到端集成测试（默认跳过） | 新建 |
| `vnpy_china_rules/requirements.txt` | 记录可选依赖 pymysql/dbutils | 修改 |

`T1RulesEngine`（`engine.py:67-196`）**不改动** —— 重放复用其 `record_buy/record_sell`。

---

## Task 1: `t1_store.py` — DDL + `T1PositionStore` 骨架（init_schema + 协议校验）

**Files:**
- Create: `vnpy_china_rules/t1_store.py`
- Test: `vnpy_china_rules/tests/test_t1_store.py`

- [ ] **Step 1: 写失败测试**

创建 `vnpy_china_rules/tests/test_t1_store.py`：

```python
"""T1PositionStore 单元测试（mock db，不依赖真实 MySQL）"""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from vnpy_china_rules.t1_store import (
    T1PositionStore,
    T1_TRADE_FLOW_DDL,
    APPEND_TRADE_SQL,
    LOAD_ALL_SQL,
)


class TestT1PositionStore(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.execute.return_value = 1
        self.store = T1PositionStore(self.db)

    def test_init_schema_calls_execute_with_ddl(self):
        """init_schema 幂等建表，调用 db.execute(DDL)"""
        self.store.init_schema()
        self.db.execute.assert_called_once_with(T1_TRADE_FLOW_DDL)

    def test_rejects_db_missing_protocol(self):
        """db 缺 execute/query 方法时抛 TypeError"""
        with self.assertRaises(TypeError):
            T1PositionStore(object())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试，确认失败（ImportError：模块不存在）**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_store.py -v
```
Expected: FAIL / collection error（`t1_store` 不存在）

- [ ] **Step 3: 实现 `t1_store.py`（DDL + 骨架）**

创建 `vnpy_china_rules/t1_store.py`：

```python
"""
T+1 持仓成交流水持久化

事件溯源：append-only 记录每笔成交，启动时重放重建内存持仓。
依赖注入 db（鸭子类型：execute(sql,args)->int, query(sql,args)->List[dict]），
典型实现为 vnpy_china_reporting.data_source.db.DataSourceDB。
"""

from typing import List, Dict, Any
from datetime import datetime

from loguru import logger


T1_TRADE_FLOW_DDL = """
CREATE TABLE IF NOT EXISTS t1_trade_flow (
    id          BIGINT NOT NULL AUTO_INCREMENT,
    trade_id    VARCHAR(64) NOT NULL COMMENT '成交唯一键(trade.vt_tradeid)，幂等去重',
    symbol      VARCHAR(32) NOT NULL COMMENT '股票代码',
    direction   VARCHAR(8)  NOT NULL COMMENT 'Direction.value：多=买 / 空=卖',
    volume      INT NOT NULL COMMENT '成交数量',
    trade_time  DATETIME(3) NOT NULL COMMENT '成交时间(毫秒精度，重放排序依据)',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_trade_id (trade_id),
    INDEX idx_symbol_time (symbol, trade_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='T+1成交流水（append-only事件源）'
"""

APPEND_TRADE_SQL = """
INSERT IGNORE INTO t1_trade_flow (trade_id, symbol, direction, volume, trade_time)
VALUES (%s, %s, %s, %s, %s)
"""

LOAD_ALL_SQL = """
SELECT symbol, direction, volume, trade_time
FROM t1_trade_flow
ORDER BY trade_time, id
"""


class T1PositionStore:
    """T+1 成交流水存储（append-only 事件源）"""

    def __init__(self, db):
        """
        Parameters
        ----------
        db : 协议对象
            需实现 execute(sql, args)->int 与 query(sql, args)->List[dict]
            （vnpy_china_reporting.data_source.db.DataSourceDB 满足）
        """
        if not (hasattr(db, "execute") and hasattr(db, "query")):
            raise TypeError(
                "db 必须实现 execute(sql, args)->int 与 query(sql, args)->List[dict]"
            )
        self.db = db

    def init_schema(self) -> None:
        """幂等建表"""
        self.db.execute(T1_TRADE_FLOW_DDL)
        logger.info("T+1流水表已就绪: t1_trade_flow")
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_store.py -v
```
Expected: PASS（2 个测试）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_rules/t1_store.py vnpy_china_rules/tests/test_t1_store.py
git commit -m "✨ feat(vnpy_china_rules): 新增T1PositionStore骨架与t1_trade_flow DDL"
```

---

## Task 2: `append_trade`（INSERT IGNORE 幂等）

**Files:**
- Modify: `vnpy_china_rules/t1_store.py`（`T1PositionStore` 增 `append_trade`）
- Test: `vnpy_china_rules/tests/test_t1_store.py`

- [ ] **Step 1: 追加失败测试**

在 `TestT1PositionStore` 类内追加：

```python
    def test_append_trade_uses_insert_ignore_and_correct_args(self):
        """append_trade 用 INSERT IGNORE 且参数正确"""
        dt = datetime(2024, 2, 24, 9, 30, 0, 123000)
        rows = self.store.append_trade("TEST.t1", "000001", "多", 1000, dt)
        self.assertEqual(rows, 1)
        self.db.execute.assert_called_once_with(
            APPEND_TRADE_SQL,
            ("TEST.t1", "000001", "多", 1000, dt),
        )

    def test_append_trade_duplicate_returns_zero(self):
        """重复 trade_id 时 INSERT IGNORE 返回 0"""
        self.db.execute.return_value = 0
        rows = self.store.append_trade("TEST.t1", "000001", "多", 1000, datetime(2024, 2, 24))
        self.assertEqual(rows, 0)
```

- [ ] **Step 2: 跑测试，确认失败（AttributeError: append_trade）**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_store.py::TestT1PositionStore::test_append_trade_uses_insert_ignore_and_correct_args -v
```
Expected: FAIL

- [ ] **Step 3: 实现 `append_trade`**

在 `t1_store.py` 的 `T1PositionStore.init_schema` 方法后插入：

```python
    def append_trade(
        self,
        trade_id: str,
        symbol: str,
        direction: str,
        volume: int,
        trade_time: datetime,
    ) -> int:
        """追加成交流水（INSERT IGNORE 幂等）

        Returns
        -------
        int
            受影响行数（0 表示重复 trade_id 已忽略）
        """
        return self.db.execute(
            APPEND_TRADE_SQL,
            (trade_id, symbol, direction, volume, trade_time),
        )
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_store.py -v
```
Expected: PASS（4 个测试）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_rules/t1_store.py vnpy_china_rules/tests/test_t1_store.py
git commit -m "✨ feat(vnpy_china_rules): T1PositionStore.append_trade 幂等写入流水"
```

---

## Task 3: `load_all`（按 trade_time, id 排序）

**Files:**
- Modify: `vnpy_china_rules/t1_store.py`（增 `load_all`）
- Test: `vnpy_china_rules/tests/test_t1_store.py`

- [ ] **Step 1: 追加失败测试**

在 `TestT1PositionStore` 类内追加：

```python
    def test_load_all_uses_ordered_sql_and_returns_rows(self):
        """load_all 用含 ORDER BY 的 SQL，原样返回 db.query 结果"""
        rows_from_db = [
            {"symbol": "000001", "direction": "多", "volume": 800,
             "trade_time": datetime(2024, 2, 24, 9, 30)},
            {"symbol": "000001", "direction": "多", "volume": 500,
             "trade_time": datetime(2024, 2, 23, 9, 30)},
        ]
        self.db.query.return_value = rows_from_db
        rows = self.store.load_all()
        self.db.query.assert_called_once_with(LOAD_ALL_SQL)
        self.assertEqual(rows, rows_from_db)
```

> 注：排序由 SQL `ORDER BY trade_time, id` 保证（见 `LOAD_ALL_SQL`），store 不在 Python 层重排。

- [ ] **Step 2: 跑测试，确认失败**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_store.py::TestT1PositionStore::test_load_all_uses_ordered_sql_and_returns_rows -v
```
Expected: FAIL（AttributeError: load_all）

- [ ] **Step 3: 实现 `load_all`**

在 `t1_store.py` 的 `T1PositionStore.append_trade` 方法后插入：

```python
    def load_all(self) -> List[Dict[str, Any]]:
        """读取全部流水，按 (trade_time, id) 排序"""
        return self.db.query(LOAD_ALL_SQL)
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_store.py -v
```
Expected: PASS（5 个测试）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_rules/t1_store.py vnpy_china_rules/tests/test_t1_store.py
git commit -m "✨ feat(vnpy_china_rules): T1PositionStore.load_all 按时间排序读流水"
```

---

## Task 4: `ChinaStockRulesEngine` 注入 `db`（向后兼容）

**Files:**
- Modify: `vnpy_china_rules/engine.py:729-747`（`__init__`）
- Test: `vnpy_china_rules/tests/test_engine.py`

- [ ] **Step 1: 追加失败测试**

在 `vnpy_china_rules/tests/test_engine.py` 末尾追加新测试类（文件顶部已 `from unittest.mock import Mock, MagicMock, patch`，已 import `TradeData/Direction/Offset/Exchange`）：

```python
class TestT1PersistenceEngineInit(unittest.TestCase):
    """T+1持久化：db 注入与向后兼容"""

    def test_no_db_keeps_store_none_and_existing_behavior(self):
        """db=None 时 store 为 None，维持纯内存（现有行为不破坏）"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)
        self.assertIsNone(engine.store)

    def test_db_injected_creates_store_and_init_schema(self):
        """db 注入时创建 store、调用 init_schema、空流水重放无副作用"""
        mock_dm = Mock(spec=DataSourceManager)
        db = MagicMock()
        db.query.return_value = []  # 空流水
        engine = ChinaStockRulesEngine(mock_dm, db=db)
        self.assertIsNotNone(engine.store)
        # init_schema 触发过 execute(DDL)
        self.assertTrue(db.execute.called)

    def test_db_protocol_mismatch_falls_back_to_inmemory(self):
        """db 不满足协议时降级 store=None，不抛异常"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm, db=object())  # object() 无 execute/query
        self.assertIsNone(engine.store)
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit -v
```
Expected: FAIL（`ChinaStockRulesEngine` 不接受 `db` 参数 / 无 `store` 属性）

- [ ] **Step 3: 改造 `__init__`**

替换 `vnpy_china_rules/engine.py` 中 `ChinaStockRulesEngine.__init__`（729-747 行）。

原代码：
```python
    def __init__(self, datasource_manager: DataSourceManager) -> None:
        """
        初始化A股交易规则引擎

        Parameters
        ----------
        datasource_manager : DataSourceManager
            数据源管理器
        """
        self.dm = datasource_manager

        # 初始化子规则引擎
        self.t1_rules = T1RulesEngine(self)
        self.price_limit_rules = PriceLimitRulesEngine(self)
        self.time_rules = TimeRulesEngine(self)
        self.unit_rules = UnitRulesEngine(self)
        self.ipo_rules = IpoRulesEngine(self)

        logger.info("A股交易规则引擎初始化成功")
```

新代码：
```python
    def __init__(self, datasource_manager: DataSourceManager, db: Optional[Any] = None) -> None:
        """
        初始化A股交易规则引擎

        Parameters
        ----------
        datasource_manager : DataSourceManager
            数据源管理器
        db : Optional[Any]
            可选持久化连接（需实现 execute(sql,args)->int、query(sql,args)->List[dict]，
            如 vnpy_china_reporting.data_source.db.DataSourceDB）。为 None 时纯内存模式。
        """
        self.dm = datasource_manager

        # 初始化子规则引擎
        self.t1_rules = T1RulesEngine(self)
        self.price_limit_rules = PriceLimitRulesEngine(self)
        self.time_rules = TimeRulesEngine(self)
        self.unit_rules = UnitRulesEngine(self)
        self.ipo_rules = IpoRulesEngine(self)

        # T+1 持久化（可选）：db 注入时建表并重放，失败降级纯内存
        self.store = None
        if db is not None:
            try:
                from vnpy_china_rules.t1_store import T1PositionStore
                self.store = T1PositionStore(db)
                self.store.init_schema()
                self._replay()
            except Exception as e:
                self.store = None
                logger.warning(f"T+1持久化初始化失败，降级纯内存模式: {e}")

        logger.info("A股交易规则引擎初始化成功")
```

> `Optional`、`Any` 已在 `engine.py:14` 导入（`from typing import List, Optional, Dict, Any`）。

同时，在 `__init__` 方法之后、`check_order` 之前插入 `_replay` 的**临时空实现**（真实重放逻辑在 Task 5 填充；此处占位以保证 Task 4 的 `__init__` 能正常调用）：

```python
    def _replay(self) -> None:
        """从流水重放重建T+1内存持仓（Task 5 填充真实逻辑）"""
        pass
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit -v
```
Expected: PASS（3 个测试）

- [ ] **Step 5: 跑现有 T1 全量测试，确认无回归**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py -v
```
Expected: 全部 PASS（现有测试 + 新增 3 个）

- [ ] **Step 6: 提交**

```bash
git add vnpy_china_rules/engine.py vnpy_china_rules/tests/test_engine.py
git commit -m "✨ feat(vnpy_china_rules): ChinaStockRulesEngine 支持可选db注入与降级"
```

---

## Task 5: `_replay` 启动重放（重放一致性）

**Files:**
- Modify: `vnpy_china_rules/engine.py`（`_replay` 真实实现）
- Test: `vnpy_china_rules/tests/test_engine.py`

- [ ] **Step 1: 追加失败测试**

在 `test_engine.py` 的 `TestT1PersistenceEngineInit` 类内追加：

```python
    def test_replay_rebuilds_same_as_continuous_record(self):
        """重放结果与连续 record_buy/sell 等价（含 FIFO 扣减）"""
        flow = [
            {"symbol": "000001", "direction": Direction.LONG.value,
             "volume": 1000, "trade_time": datetime(2024, 2, 23, 9, 30)},
            {"symbol": "000001", "direction": Direction.LONG.value,
             "volume": 500, "trade_time": datetime(2024, 2, 24, 9, 30)},
            {"symbol": "000001", "direction": Direction.SHORT.value,
             "volume": 300, "trade_time": datetime(2024, 2, 24, 14, 0)},
        ]
        mock_dm = Mock(spec=DataSourceManager)
        db = MagicMock()
        db.query.return_value = flow

        replayed = ChinaStockRulesEngine(mock_dm, db=db)

        # 参考引擎：连续 record
        ref = ChinaStockRulesEngine(mock_dm)
        ref.t1_rules.record_buy("000001", 1000, datetime(2024, 2, 23, 9, 30))
        ref.t1_rules.record_buy("000001", 500, datetime(2024, 2, 24, 9, 30))
        ref.t1_rules.record_sell("000001", 300, datetime(2024, 2, 24, 14, 0))

        # positions 逐批次相等
        rp = replayed.t1_rules.positions["000001"]
        fp = ref.t1_rules.positions["000001"]
        self.assertEqual(len(rp), len(fp))
        for r, f in zip(rp, fp):
            self.assertEqual((r.volume, r.available, r.buy_datetime),
                             (f.volume, f.available, f.buy_datetime))

        # 可卖量一致（2/25 视角：前日批次均可卖）
        self.assertEqual(
            replayed.t1_rules.get_sellable_volume("000001", datetime(2024, 2, 25, 9, 0)),
            ref.t1_rules.get_sellable_volume("000001", datetime(2024, 2, 25, 9, 0)),
        )
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit::test_replay_rebuilds_same_as_continuous_record -v
```
Expected: FAIL（`_replay` 是空 pass，positions 为空）

- [ ] **Step 3: 实现 `_replay`**

替换 Task 4 中插入的临时空 `_replay`：

原代码：
```python
    def _replay(self) -> None:
        """从流水重放重建T+1内存持仓（Task 5 填充真实逻辑）"""
        pass
```

新代码：
```python
    def _replay(self) -> None:
        """从流水重放重建T+1内存持仓

        读取 t1_trade_flow 全表（已按 trade_time, id 排序），逐条喂给
        record_buy/record_sell，与正常成交路径复用同一逻辑。
        """
        if self.store is None:
            return
        count = 0
        for row in self.store.load_all():
            symbol = row["symbol"]
            volume = int(row["volume"])
            dt = row["trade_time"]
            if row["direction"] == Direction.LONG.value:      # "多"
                self.t1_rules.record_buy(symbol, volume, dt)
            elif row["direction"] == Direction.SHORT.value:   # "空"
                self.t1_rules.record_sell(symbol, volume, dt)
            # NET 或异常值：跳过（不应出现在成交流水）
            count += 1
        logger.info(f"T+1持仓重放完成，共 {count} 条流水")
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit -v
```
Expected: PASS（4 个测试）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_rules/engine.py vnpy_china_rules/tests/test_engine.py
git commit -m "✨ feat(vnpy_china_rules): 启动时从流水重放重建T+1内存持仓"
```

---

## Task 6: `on_trade` 双写（DB 优先 + 降级 + 时间戳幂等）

**Files:**
- Modify: `vnpy_china_rules/engine.py:810-838`（`on_trade`）
- Test: `vnpy_china_rules/tests/test_engine.py`

- [ ] **Step 1: 追加失败测试**

在 `test_engine.py` 的 `TestT1PersistenceEngineInit` 类内追加（需构造 `TradeData`，参考现有 `test_engine.py` 的 OrderData/TradeData 构造风格）：

```python
    def _make_trade(self, symbol, direction, volume, dt, tradeid):
        return TradeData(
            gateway_name="TEST",
            symbol=symbol,
            exchange=Exchange.SZSE,
            orderid="o1",
            tradeid=tradeid,
            direction=direction,
            offset=Offset.OPEN if direction == Direction.LONG else Offset.CLOSE,
            price=10.0,
            volume=volume,
            datetime=dt,
        )

    def test_on_trade_appends_to_store_then_memory(self):
        """on_trade 先落库后内存，DB 与内存共用同一 trade_time"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)   # store=None
        engine.store = MagicMock()                # 注入可验证 mock
        engine.store.append_trade.return_value = 1

        dt = datetime(2024, 2, 24, 9, 30)
        trade = self._make_trade("000001", Direction.LONG, 1000, dt, "t1")
        engine.on_trade(trade)

        # vt_tradeid = f"{gateway_name}.{tradeid}" = "TEST.t1"
        engine.store.append_trade.assert_called_once_with(
            "TEST.t1", "000001", Direction.LONG.value, 1000, dt
        )
        # 内存已更新且 buy_datetime == trade_time（共用，非 now()）
        rec = engine.t1_rules.positions["000001"][0]
        self.assertEqual(rec.volume, 1000)
        self.assertEqual(rec.buy_datetime, dt)

    def test_on_trade_store_failure_falls_back_to_memory(self):
        """store 写入抛异常时，内存仍更新，on_trade 不阻断"""
        mock_dm = Mock(spec=DataSourceManager)
        engine = ChinaStockRulesEngine(mock_dm)
        engine.store = MagicMock()
        engine.store.append_trade.side_effect = RuntimeError("db down")

        dt = datetime(2024, 2, 24, 9, 30)
        trade = self._make_trade("000001", Direction.LONG, 1000, dt, "t1")
        engine.on_trade(trade)   # 不抛异常

        self.assertEqual(engine.t1_rules.positions["000001"][0].volume, 1000)
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit::test_on_trade_appends_to_store_then_memory vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit::test_on_trade_store_failure_falls_back_to_memory -v
```
Expected: FAIL（现有 `on_trade` 不调用 `store.append_trade`）

- [ ] **Step 3: 改造 `on_trade`**

替换 `vnpy_china_rules/engine.py` 中 `ChinaStockRulesEngine.on_trade` 方法体（810-838 行）。

原代码：
```python
    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调

        更新T+1持仓记录。

        Parameters
        ----------
        trade : TradeData
            成交数据
        """
        # 买入成交：记录持仓
        if trade.direction == Direction.LONG:
            self.t1_rules.record_buy(
                symbol=trade.symbol,
                volume=int(trade.volume),
                datetime=trade.datetime or datetime.now()
            )

        # 卖出成交：扣减持仓
        elif trade.direction == Direction.SHORT:
            self.t1_rules.record_sell(
                symbol=trade.symbol,
                volume=int(trade.volume),
                datetime=trade.datetime or datetime.now()
            )

        logger.debug(f"成交回调处理完成: {trade.symbol} {trade.direction.value} {trade.volume}股")
```

新代码：
```python
    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调

        先落 T+1 流水（崩溃恢复权威），再更新内存持仓（T+1 检查权威）。
        DB 与内存共用单次计算的 trade_time，保证原始执行与重放一致。

        Parameters
        ----------
        trade : TradeData
            成交数据
        """
        # 单次计算时间戳，DB 与内存共用（避免 now() 不幂等导致重放漂移）
        trade_time = trade.datetime or datetime.now()

        # 先落库；失败降级纯内存，不阻断成交回调
        if self.store is not None:
            try:
                self.store.append_trade(
                    trade.vt_tradeid, trade.symbol,
                    trade.direction.value, int(trade.volume), trade_time,
                )
            except Exception as e:
                logger.warning(f"T+1流水写入失败，降级纯内存: {e}")

        # 再更新内存（T+1 检查权威）
        if trade.direction == Direction.LONG:
            self.t1_rules.record_buy(
                symbol=trade.symbol,
                volume=int(trade.volume),
                datetime=trade_time,
            )
        elif trade.direction == Direction.SHORT:
            self.t1_rules.record_sell(
                symbol=trade.symbol,
                volume=int(trade.volume),
                datetime=trade_time,
            )

        logger.debug(f"成交回调处理完成: {trade.symbol} {trade.direction.value} {trade.volume}股")
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py::TestT1PersistenceEngineInit -v
```
Expected: PASS（6 个测试）

- [ ] **Step 5: 跑现有 `TestChinaStockRulesEngine` 全量，确认无回归**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_engine.py -v
```
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add vnpy_china_rules/engine.py vnpy_china_rules/tests/test_engine.py
git commit -m "✨ feat(vnpy_china_rules): on_trade 双写流水+内存，时间戳幂等，DB失败降级"
```

---

## Task 7: MySQL 集成测试（默认跳过）

**Files:**
- Create: `vnpy_china_rules/tests/test_t1_persistence_integration.py`

- [ ] **Step 1: 创建集成测试文件**

创建 `vnpy_china_rules/tests/test_t1_persistence_integration.py`：

```python
"""T+1 持久化 MySQL 集成测试

默认跳过。启用方式（需 MySQL 在线、vnpy_china_config 已配置）：
    conda run -n Quant-3.11 python -m pytest \
        vnpy_china_rules/tests/test_t1_persistence_integration.py -v
"""

import os
import unittest
from datetime import datetime
from unittest.mock import Mock

from vnpy.trader.constant import Exchange, Direction, Offset
from vnpy.trader.object import TradeData

from vnpy_china_rules.datasource import DataSourceManager
from vnpy_china_rules.engine import ChinaStockRulesEngine


@unittest.skipUnless(os.getenv("RUN_INTEGRATION"), "需 RUN_INTEGRATION=1 及在线 MySQL")
class TestT1PersistenceIntegration(unittest.TestCase):
    """端到端：真实 MySQL 流水写入 → 新引擎重放 → 内存一致"""

    def setUp(self):
        try:
            from vnpy_china_config import get_global_config
            from vnpy_china_reporting.data_source.db import DataSourceDB
            config = get_global_config()
            self.db = DataSourceDB.from_global_config(config)
            self.db.connect()
        except Exception as e:
            self.skipTest(f"MySQL 环境不可用，跳过: {e}")
        # 清理本测试残留
        self.db.execute(
            "DELETE FROM t1_trade_flow WHERE trade_id LIKE %s", ("TEST.INT.%",)
        )

    def tearDown(self):
        try:
            self.db.execute(
                "DELETE FROM t1_trade_flow WHERE trade_id LIKE %s", ("TEST.INT.%",)
            )
        except Exception:
            pass

    def _make_trade(self, tradeid, direction, volume, dt):
        return TradeData(
            gateway_name="TEST", symbol="000001", exchange=Exchange.SZSE,
            orderid="o1", tradeid=tradeid, direction=direction,
            offset=Offset.OPEN if direction == Direction.LONG else Offset.CLOSE,
            price=10.0, volume=volume, datetime=dt,
        )

    def test_append_then_replay_roundtrip(self):
        mock_dm = Mock(spec=DataSourceManager)

        # 引擎1：写入 3 笔（buy/buy/sell FIFO）
        eng1 = ChinaStockRulesEngine(mock_dm, db=self.db)
        eng1.on_trade(self._make_trade("TEST.INT.1", Direction.LONG, 1000, datetime(2024, 2, 23, 9, 30)))
        eng1.on_trade(self._make_trade("TEST.INT.2", Direction.LONG, 500, datetime(2024, 2, 24, 9, 30)))
        eng1.on_trade(self._make_trade("TEST.INT.3", Direction.SHORT, 300, datetime(2024, 2, 24, 14, 0)))

        # 引擎2：新建实例，从 DB 重放
        eng2 = ChinaStockRulesEngine(mock_dm, db=self.db)

        # 内存持仓一致
        rp = eng1.t1_rules.positions["000001"]
        fp = eng2.t1_rules.positions["000001"]
        self.assertEqual(len(rp), len(fp))
        for r, f in zip(rp, fp):
            self.assertEqual((r.volume, r.available), (f.volume, f.available))

    def test_idempotent_append_no_dup(self):
        """同一 vt_tradeid 重复 on_trade，流水不翻倍"""
        mock_dm = Mock(spec=DataSourceManager)
        eng = ChinaStockRulesEngine(mock_dm, db=self.db)
        t = self._make_trade("TEST.INT.DUP", Direction.LONG, 1000, datetime(2024, 2, 24, 9, 30))
        eng.on_trade(t)
        eng.on_trade(t)   # 重复
        rows = self.db.query(
            "SELECT COUNT(*) AS c FROM t1_trade_flow WHERE trade_id=%s",
            ("TEST.INT.DUP",),
        )
        self.assertEqual(int(rows[0]["c"]), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 确认默认跳过（无 RUN_INTEGRATION）**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_persistence_integration.py -v
```
Expected: 2 个测试 SKIPPED

- [ ] **Step 3: （可选，需 MySQL）启用集成测试**

```bash
RUN_INTEGRATION=1 conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/test_t1_persistence_integration.py -v
```
Expected: 2 个测试 PASS（或因 MySQL 未配置而 skipTest）

- [ ] **Step 4: 提交**

```bash
git add vnpy_china_rules/tests/test_t1_persistence_integration.py
git commit -m "✅ test(vnpy_china_rules): 新增T+1持久化MySQL集成测试(默认跳过)"
```

---

## Task 8: 依赖声明 + 全量回归

**Files:**
- Modify: `vnpy_china_rules/requirements.txt`

- [ ] **Step 1: 补充可选依赖说明**

在 `vnpy_china_rules/requirements.txt` 末尾的 vnpy_riskmanager 注释块后追加：

```
# T+1持仓持久化（vnpy_china_rules.t1_store）可选运行时依赖，启用 T+1 跨重启恢复时安装：
#   pip install pymysql dbutils
#   （复用 vnpy_china_reporting.data_source.db.DataSourceDB）
```

- [ ] **Step 2: 全量回归（不依赖 MySQL 的全部测试）**

```bash
conda run -n Quant-3.11 python -m pytest vnpy_china_rules/tests/ -v
```
Expected: 全部 PASS（集成测试 SKIPPED）

- [ ] **Step 3: 提交**

```bash
git add vnpy_china_rules/requirements.txt
git commit -m "📝 docs(vnpy_china_rules): requirements 声明T+1持久化可选依赖"
```

---

## 验收检查（实现完成后）

- [ ] `db=None` 时，`ChinaStockRulesEngine` 行为与改造前完全一致（现有 91 个测试全绿）
- [ ] `db` 注入时：`on_trade` 双写、启动重放、`store` 失败降级
- [ ] 重放结果与连续 `record_buy/sell` 逐字段相等（含 FIFO 扣减后 available）
- [ ] 重复 `vt_tradeid` 幂等（INSERT IGNORE）
- [ ] `T1RulesEngine` 源码零改动
