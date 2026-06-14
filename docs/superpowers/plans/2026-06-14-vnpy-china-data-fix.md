# vnpy_china_data 审查问题修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `vnpy_china_data` 模块审查报告核实的 P0-P3 全部真实问题，采用 TDD 流程，每批独立可验证可提交。

**Architecture:** 按优先级分 4 批 11 个任务。每个逻辑修复点先写失败测试 → 验证失败 → 最小实现 → 验证通过 → 提交。死代码删除/配置补全等非逻辑改动用导入与 Grep 验证。

**Tech Stack:** Python 3.11（conda 环境 `Quant-3.11`）、pytest、unittest.mock、pymysql/DBUtils、xtquant、vnpy 4.4.0

**测试运行命令：** `conda run -n Quant-3.11 python -m pytest <path> -v`

**参考设计文档：** `docs/superpowers/specs/2026-06-14-vnpy-china-data-fix-design.md`

---

## 文件结构

| 文件 | 责任 | 操作 |
|---|---|---|
| `vnpy_china_data/validator.py` | 数据校验器 | 修改（Task 1） |
| `vnpy_china_data/database.py` | MySQL 持久化层 | 修改（Task 2/3/7） |
| `vnpy_china_data/adapter/qmt_adapter.py` | QMT 本地数据适配器 | 修改（Task 4） |
| `vnpy_china_data/service.py` | 数据服务主类 | 修改（Task 5/11） |
| `vnpy_china_data/cache.py` | Redis 缓存 | 修改（Task 6） |
| `vnpy_china_data/gui_engine.py` | GUI 引擎 | 修改（Task 8/9） |
| `vnpy_china_data/requirements.txt` | 依赖声明 | 修改（Task 10） |
| `vnpy_china_data/tests/test_validator.py` | validator 单元测试 | 新建（Task 1） |
| `vnpy_china_data/tests/test_qmt_adapter.py` | QMT 适配器测试 | 扩展（Task 4） |
| `vnpy_china_data/tests/test_gui_engine.py` | GUI 引擎测试 | 扩展（Task 8/9） |
| `vnpy_china_data/tests/test_database.py` | 数据库层测试 | 新建（Task 3/7） |
| `vnpy_china_data/tests/test_service.py` | 服务层测试 | 新建（Task 11） |

---

## 第 1 批：P0 — validator 修复 + 接入数据校验

### Task 1: 修复 validator.py 语法错误与逻辑反转

**Files:**
- Modify: `vnpy_china_data/validator.py:23-57`（validate_bar_data）、`:142-161`（validate_interval）、`:126-140`（validate_exchange）
- Test: `vnpy_china_data/tests/test_validator.py`（新建）

- [ ] **Step 1: 写失败测试**

创建 `vnpy_china_data/tests/test_validator.py`：

```python
"""数据验证器单元测试"""

from datetime import datetime

import pytest

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval

from vnpy_china_data.validator import DataValidator


def make_bar(
    symbol: str = "000001",
    open_price: float = 10.0,
    high_price: float = 11.0,
    low_price: float = 9.0,
    close_price: float = 10.5,
    volume: float = 1000.0,
) -> BarData:
    """构造测试用 BarData"""
    return BarData(
        gateway_name="TEST",
        symbol=symbol,
        exchange=Exchange.SZSE,
        datetime=datetime(2024, 1, 1),
        interval=Interval.DAILY,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
    )


class TestDataValidator:
    """DataValidator 测试"""

    def test_valid_bar(self):
        """合法 bar 返回 True"""
        assert DataValidator.validate_bar_data(make_bar()) is True

    def test_volume_negative_rejected(self):
        """volume<0 拒绝"""
        assert DataValidator.validate_bar_data(make_bar(volume=-1)) is False

    def test_volume_zero_allowed(self):
        """volume==0 放行（停牌/空 bar）"""
        assert DataValidator.validate_bar_data(make_bar(volume=0)) is True

    def test_price_zero_rejected(self):
        """任一价格<=0 拒绝"""
        assert DataValidator.validate_bar_data(make_bar(open_price=0)) is False
        assert DataValidator.validate_bar_data(make_bar(high_price=0)) is False
        assert DataValidator.validate_bar_data(make_bar(low_price=-1)) is False
        assert DataValidator.validate_bar_data(make_bar(close_price=0)) is False

    def test_high_lt_low_rejected(self):
        """high<low 拒绝"""
        assert DataValidator.validate_bar_data(
            make_bar(high_price=8.0, low_price=9.0)
        ) is False

    def test_empty_symbol_rejected(self):
        """空 symbol 拒绝"""
        assert DataValidator.validate_bar_data(make_bar(symbol="")) is False

    def test_validate_bar_list_filters_invalid(self):
        """validate_bar_list 过滤混合列表"""
        bars = [
            make_bar(symbol="000001"),                       # 有效
            make_bar(symbol="000002", volume=-5),            # 无效
            make_bar(symbol="000003"),                       # 有效
            make_bar(symbol="000004", high_price=1, low_price=9),  # 无效
        ]
        valid = DataValidator.validate_bar_list(bars)
        assert len(valid) == 2
        assert valid[0].symbol == "000001"
        assert valid[1].symbol == "000003"

    def test_validate_exchange_hk_connect(self):
        """validate_exchange 支持港股通"""
        assert DataValidator.validate_exchange(Exchange.SHHK) is True
        assert DataValidator.validate_exchange(Exchange.SZHK) is True
        assert DataValidator.validate_exchange(Exchange.SEHK) is True
        assert DataValidator.validate_exchange(Exchange.SSE) is True
        assert DataValidator.validate_exchange(Exchange.SZSE) is True

    def test_validate_interval_actual_enums(self):
        """validate_interval 使用实际 Interval 枚举"""
        assert DataValidator.validate_interval(Interval.MINUTE) is True
        assert DataValidator.validate_interval(Interval.HOUR) is True
        assert DataValidator.validate_interval(Interval.DAILY) is True
        assert DataValidator.validate_interval(Interval.WEEKLY) is True
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_validator.py -v`

Expected: FAIL，错误为 `IndentationError` 或 `ImportError: cannot import name 'DataValidator'`（validator.py 无法导入）

- [ ] **Step 3: 修复 validate_bar_data（语法+逻辑）**

修改 `vnpy_china_data/validator.py:53-57`，将：

```python
        # 检查成交量
        if bar.volume < 0:
            return True

    return False

        @staticmethod
    def validate_bar_list(bars: List[BarData]) -> List[BarData]:
```

替换为：

```python
        # 检查成交量
        if bar.volume < 0:
            return False

        return True

    @staticmethod
    def validate_bar_list(bars: List[BarData]) -> List[BarData]:
```

关键修正：① `volume<0` 改为 `return False`（逻辑反转）；② 末尾 `return False` 改为 `return True` 并归位到方法体内（8 空格缩进，原 4 空格位于类体致 IndentationError）；③ 移除 `@staticmethod` 前的异常缩进。

- [ ] **Step 4: 修复 validate_exchange（补港股通枚举）**

修改 `vnpy_china_data/validator.py:136-140`，将：

```python
        return exchange in [
            Exchange.SSE,   # 上交所
            Exchange.SZSE,  # 深交所
            Exchange.BSE,   # 北交所
        ]
```

替换为：

```python
        return exchange in [
            Exchange.SSE,   # 上交所
            Exchange.SZSE,  # 深交所
            Exchange.BSE,   # 北交所
            Exchange.SHHK,  # 沪港通
            Exchange.SZHK,  # 深港通
            Exchange.SEHK,  # 香港联交所
        ]
```

- [ ] **Step 5: 修复 validate_interval（用实际枚举）**

修改 `vnpy_china_data/validator.py:152-161`，将：

```python
        return interval in [
            Interval.MINUTE_1,
            Interval.MINUTE_5,
            Interval.MINUTE_15,
            Interval.MINUTE_30,
            Interval.HOUR_1,
            Interval.DAILY,
            Interval.WEEKLY,
            Interval.MONTHLY,
        ]
```

替换为：

```python
        return interval in [
            Interval.MINUTE,
            Interval.HOUR,
            Interval.DAILY,
            Interval.WEEKLY,
        ]
```

- [ ] **Step 6: 验证语法与导入**

Run: `conda run -n Quant-3.11 python -c "from vnpy_china_data.validator import DataValidator; print('IMPORT_OK')"`

Expected: 输出 `IMPORT_OK`

- [ ] **Step 7: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_validator.py -v`

Expected: 9 passed

- [ ] **Step 8: 提交**

```bash
git add vnpy_china_data/validator.py vnpy_china_data/tests/test_validator.py
git commit -m "🐛 fix(vnpy_china_data): 修复validator.py语法错误与逻辑反转

- 修正validate_bar_data缩进致IndentationError无法导入
- volume<0返回True逻辑反转为False
- 末尾return归位方法体并改为returnTrue
- validate_interval使用实际Interval枚举(MINUTE/HOUR/DAILY/WEEKLY)
- validate_exchange补充港股通SHHK/SZHK/SEHK"
```

---

### Task 2: save_bar_data 接入数据校验

**Files:**
- Modify: `vnpy_china_data/database.py:199-259`（save_bar_data）
- Test: `vnpy_china_data/tests/test_validator.py`（追加集成测试）

- [ ] **Step 1: 写失败测试**

在 `vnpy_china_data/tests/test_validator.py` 末尾追加：

```python
class TestSaveBarDataValidation:
    """save_bar_data 接入校验的集成测试"""

    def test_save_bar_data_filters_invalid_bars(self):
        """save_bar_data 过滤无效 bar，仅存有效项"""
        from unittest.mock import MagicMock
        from vnpy_china_data.database import MySQLDatabaseLayer

        db = MySQLDatabaseLayer(
            host="localhost", port=3306, user="root",
            password="", database="test"
        )

        # mock 连接池与游标（is_connected property 会调 pool.connection().ping()，
        # mock 默认不抛异常，自然返回 True，无需覆盖 property）
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool
        db._connected = True

        # 混合数据：2 有效 + 2 无效
        bars = [
            make_bar(symbol="000001"),                                 # 有效
            make_bar(symbol="BAD01", volume=-1),                       # 无效
            make_bar(symbol="000002"),                                 # 有效
            make_bar(symbol="BAD02", high_price=1, low_price=9),       # 无效
        ]

        result = db.save_bar_data(bars)

        assert result is True
        # executemany 只接收有效的 2 条
        mock_cursor.executemany.assert_called_once()
        executed_values = mock_cursor.executemany.call_args[0][1]
        assert len(executed_values) == 2
        assert executed_values[0][0] == "000001"
        assert executed_values[1][0] == "000002"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_validator.py::TestSaveBarDataValidation -v`

Expected: FAIL，`executemany` 接收 4 条而非 2 条（当前未过滤）

- [ ] **Step 3: 在 save_bar_data 接入校验**

修改 `vnpy_china_data/database.py`，在 `save_bar_data` 方法的 `if not bars: return True` 之后、`if not self._ensure_connection()` 之前插入校验。定位 `save_bar_data` 方法体开头（约第 208-212 行）：

```python
        if not bars:
            return True

        if not self._ensure_connection():
            return False
```

替换为：

```python
        if not bars:
            return True

        # 数据校验：过滤无效 bar
        from .validator import DataValidator
        original_count = len(bars)
        bars = DataValidator.validate_bar_list(bars)
        filtered_count = original_count - len(bars)
        if filtered_count > 0:
            sample_symbols = [b.symbol for b in bars[:5]] if bars else []
            logger.warning(
                f"save_bar_data 过滤 {filtered_count}/{original_count} 条无效 bar，"
                f"保留示例: {sample_symbols}"
            )

        if not bars:
            return True

        if not self._ensure_connection():
            return False
```

- [ ] **Step 4: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_validator.py -v`

Expected: 全部 passed（含 Task 1 的 9 个 + 本任务 1 个集成测试）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/database.py vnpy_china_data/tests/test_validator.py
git commit -m "✨ feat(vnpy_china_data): save_bar_data接入DataValidator数据校验

- 入口调用validate_bar_list过滤无效bar
- 过滤数量与示例符号记logger.warning便于观察误杀
- volume==0放行，仅拒绝volume<0/价格非法/高低价倒挂"
```

---

## 第 2 批：P1 — 连接泄漏 + get_sector_index

### Task 3: 修复 get_connection 连接归还

**Files:**
- Modify: `vnpy_china_data/database.py:150-164`（get_connection）
- Test: `vnpy_china_data/tests/test_database.py`（新建）

- [ ] **Step 1: 写失败测试**

创建 `vnpy_china_data/tests/test_database.py`：

```python
"""数据库层单元测试"""

from unittest.mock import MagicMock

import pytest

from vnpy_china_data.database import MySQLDatabaseLayer


@pytest.fixture
def db():
    """构造未连接的数据库层实例"""
    return MySQLDatabaseLayer(
        host="localhost", port=3306, user="root",
        password="", database="test"
    )


class TestGetConnection:
    """get_connection 连接归还测试"""

    def test_get_connection_closes_conn_after_with_block(self, db):
        """with 块结束后连接应归还（close 被调用）"""
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool

        with db.get_connection() as conn:
            assert conn is mock_conn

        mock_conn.close.assert_called_once()

    def test_get_connection_closes_conn_on_exception(self, db):
        """with 块内抛异常时连接仍应归还"""
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool

        with pytest.raises(ValueError):
            with db.get_connection() as conn:
                raise ValueError("test")

        mock_conn.close.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_database.py -v`

Expected: 2 failed，`mock_conn.close.assert_called_once()` 不满足（当前 `finally: pass` 不调用 close）

- [ ] **Step 3: 修复 get_connection**

修改 `vnpy_china_data/database.py:159-164`，将：

```python
        conn = self._pool.connection()
        try:
            yield conn
        finally:
            # 连接自动归还到池中，无需显式关闭
            pass
```

替换为：

```python
        conn = self._pool.connection()
        try:
            yield conn
        finally:
            # 显式归还连接到池（DBUtils 的 close() 是归还而非物理关闭）
            conn.close()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_database.py -v`

Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/database.py vnpy_china_data/tests/test_database.py
git commit -m "🐛 fix(vnpy_china_data): 修复get_connection连接未归还连接池

- finally:pass改为conn.close()显式归还
- DBUtils的close()是归还而非物理关闭，语义匹配
- 该方法被9+处with db.get_connection()调用，修复连接泄漏"
```

---

### Task 4: 重写 get_sector_index 为两步下载模式

**Files:**
- Modify: `vnpy_china_data/adapter/qmt_adapter.py:1059-1108`（get_sector_index）
- Test: `vnpy_china_data/tests/test_qmt_adapter.py`（扩展）

- [ ] **Step 1: 写失败测试**

在 `vnpy_china_data/tests/test_qmt_adapter.py` 的 `TestQMTAdapterHistoryData` 类内追加：

```python
    def test_get_sector_index_two_step_download(self, adapter):
        """测试 get_sector_index 两步下载模式"""
        from unittest.mock import MagicMock
        import sys

        # mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.download_history_data2 = MagicMock(return_value=None)

        mock_df = MagicMock()
        mock_df.iterrows = MagicMock(return_value=[
            (0, {
                'time': '20240101',
                'open': 100.0,
                'high': 110.0,
                'low': 95.0,
                'close': 105.0,
                'volume': 10000,
                'amount': 1000000.0,
            })
        ])
        mock_df.__len__ = MagicMock(return_value=1)
        mock_xtdata.get_local_data = MagicMock(return_value=mock_df)

        mock_xtquant = MagicMock()
        mock_xtquant.xtdata = mock_xtdata

        original_xtquant = sys.modules.get('xtquant')
        sys.modules['xtquant'] = mock_xtquant

        try:
            adapter._connected = True

            bars = adapter.get_sector_index(
                sector_code="801010",
                start_date="20240101",
                end_date="20240131"
            )

            # 验证返回 1 条 BarData
            assert len(bars) == 1
            assert bars[0].symbol == "801010"
            assert bars[0].open_price == 100.0
            assert bars[0].close_price == 105.0
            assert bars[0].interval == Interval.DAILY

            # 验证两步调用链
            mock_xtdata.download_history_data2.assert_called_once()
            mock_xtdata.get_local_data.assert_called_once()

        finally:
            if original_xtquant:
                sys.modules['xtquant'] = original_xtquant
            else:
                sys.modules.pop('xtquant', None)

    def test_get_sector_index_not_connected(self, adapter):
        """未连接时返回空列表"""
        adapter._connected = False

        bars = adapter.get_sector_index(
            sector_code="801010",
            start_date="20240101",
            end_date="20240131"
        )
        assert bars == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_qmt_adapter.py::TestQMTAdapterHistoryData::test_get_sector_index_two_step_download -v`

Expected: FAIL，`len(bars) == 1` 不满足（当前实现调用不存在的 `self._qmt_api.download_history_data`，hasattr 保护下返回空）

- [ ] **Step 3: 重写 get_sector_index**

将 `vnpy_china_data/adapter/qmt_adapter.py:1059-1108` 整个 `get_sector_index` 方法替换为：

```python
    def get_sector_index(
        self,
        sector_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取板块指数数据

        使用 miniQMT 两步下载流程（与 get_bar_data 一致）：
        1. download_history_data2 异步下载到本地
        2. get_local_data 读取本地数据

        Args:
            sector_code: 板块代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            K线数据列表
        """
        import time
        import logging

        logger = logging.getLogger("vnpy_china_data")

        if not self._connected:
            logger.debug("QMT未连接，无法获取板块指数数据")
            return []

        try:
            from xtquant import xtdata

            logger.debug(
                f"QMT正在下载板块指数: {sector_code}, "
                f"start={start_date}, end={end_date}"
            )

            # 第1步：异步下载数据到本地
            if hasattr(xtdata, 'download_history_data2'):
                xtdata.download_history_data2(
                    stock_list=[sector_code],
                    period="1d",
                    start_time=start_date,
                    end_time=end_date
                )
                time.sleep(3)
            else:
                logger.warning("xtdata不支持download_history_data2方法")
                return []

            # 第2步：读取本地数据
            if hasattr(xtdata, 'get_local_data'):
                data_list = xtdata.get_local_data(
                    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[sector_code],
                    period="1d",
                    start_time=start_date,
                    end_time=end_date
                )
            else:
                logger.warning("xtdata不支持get_local_data方法")
                return []

            if data_list is None or len(data_list) == 0:
                logger.debug(f"QMT未获取到板块指数数据: {sector_code}")
                return []

            # 第3步：转换为 BarData 列表
            result: List[BarData] = []
            if hasattr(data_list, 'iterrows'):
                for _, row in data_list.iterrows():
                    bar = BarData(
                        gateway_name="QMT",
                        symbol=sector_code,
                        exchange=Exchange.SSE if sector_code.startswith("80") else Exchange.SZSE,
                        datetime=self._parse_qmt_time(row.get('time')),
                        interval=Interval.DAILY,
                        open_price=float(row.get('open', 0)),
                        high_price=float(row.get('high', 0)),
                        low_price=float(row.get('low', 0)),
                        close_price=float(row.get('close', 0)),
                        volume=float(row.get('volume', 0)),
                        turnover=float(row.get('amount', 0)),
                    )
                    result.append(bar)

            logger.debug(f"QMT获取板块指数: {sector_code}, 共{len(result)}条")
            return result

        except ImportError:
            logger.warning("xtdata模块未安装，无法获取板块指数数据")
            return []
        except Exception as e:
            logger.warning(f"QMT获取板块指数失败: {e}")
            return []
```

- [ ] **Step 4: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_qmt_adapter.py -v`

Expected: 全部 passed（含原有 + 2 个新测试）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/adapter/qmt_adapter.py vnpy_china_data/tests/test_qmt_adapter.py
git commit -m "🐛 fix(vnpy_china_data): 重写get_sector_index为两步下载模式

- 原实现调用xtquant不存在的download_history_data且假设返回bars
- 参照get_bar_data重写:download_history_data2异步下载+get_local_data读取
- RPC路径(rpc_qmt_adapter.py)实现正确,不动"
```

---

## 第 3 批：P2 — print/logger + MemoryCache 死代码

### Task 5: connect 异常改用 logger 替代 print

**Files:**
- Modify: `vnpy_china_data/service.py:122-165`（connect 方法）

- [ ] **Step 1: 修改 print 为 logger**

修改 `vnpy_china_data/service.py:163-165`，将：

```python
        except Exception as e:
            print(f"数据服务连接失败: {e}")
            return False
```

替换为：

```python
        except Exception as e:
            logger.error(f"数据服务连接失败: {e}")
            return False
```

> 注：`logger` 已在 `connect` 方法开头定义（service.py:124-125：`import logging; logger = logging.getLogger("vnpy_china_data")`），无需新增导入。

- [ ] **Step 2: 验证模块导入与 connect 可调用**

Run: `conda run -n Quant-3.11 python -c "import ast; ast.parse(open('vnpy_china_data/service.py', encoding='utf-8').read()); print('SYNTAX_OK')"`

Expected: `SYNTAX_OK`

- [ ] **Step 3: 提交**

```bash
git add vnpy_china_data/service.py
git commit -m "🔧 refactor(vnpy_china_data): connect异常改用logger替代print

统一异常日志方式,与模块其他位置一致"
```

---

### Task 6: 删除未使用的 MemoryCache 死代码

**Files:**
- Modify: `vnpy_china_data/cache.py:248-296`（删除 MemoryCache 类）

- [ ] **Step 1: 删除 MemoryCache 类**

删除 `vnpy_china_data/cache.py` 第 247-296 行（`class MemoryCache:` 整个类定义，从空行后的类定义到文件末尾）。保留文件顶部的 `DataQueryCache` 类完整。

具体：删除从第 248 行 `class MemoryCache:` 到文件末尾（第 296 行 `return self.get(key) is not None`）的全部内容。删除后文件应以 `DataQueryCache` 类的最后一个方法 `ping` 结尾。

- [ ] **Step 2: 验证导入正常**

Run: `conda run -n Quant-3.11 python -c "from vnpy_china_data.cache import DataQueryCache; print('IMPORT_OK')"`

Expected: `IMPORT_OK`

- [ ] **Step 3: 验证无残留引用**

Run: `conda run -n Quant-3.11 python -c "import vnpy_china_data; print('PACKAGE_OK')"`

Expected: `PACKAGE_OK`（无 ImportError）

并用 Grep 工具搜索全库 `MemoryCache`，确认仅可能在注释/历史文档中出现，源码与 `__init__.py` 无引用。

- [ ] **Step 4: 提交**

```bash
git add vnpy_china_data/cache.py
git commit -m "🔥 chore(vnpy_china_data): 删除未使用的MemoryCache死代码

- MemoryCache全库无实例化与import
- __init__.py的__all__仅导出DataQueryCache,删除不影响公共API
- Redis失败时保持降级直连API(合理设计)"
```

---

## 第 4 批：P3 — 低危清理与语义改进

### Task 7: get_database_stats 表名白名单校验

**Files:**
- Modify: `vnpy_china_data/database.py:1219-1285`（get_database_stats，提取白名单校验）
- Test: `vnpy_china_data/tests/test_database.py`（扩展）

- [ ] **Step 1: 写失败测试**

在 `vnpy_china_data/tests/test_database.py` 追加：

```python
import re


class TestDatabaseStatsTableNameValidation:
    """get_database_stats 表名白名单校验测试"""

    def test_valid_table_names_accepted(self):
        """合法表名通过白名单"""
        assert MySQLDatabaseLayer._is_valid_table_name("db_bar_data") is True
        assert MySQLDatabaseLayer._is_valid_table_name("db_stock_info") is True
        assert MySQLDatabaseLayer._is_valid_table_name("db_hk_connect_stocks") is True

    def test_invalid_table_names_rejected(self):
        """恶意表名被白名单拒绝"""
        # SQL 注入尝试
        assert MySQLDatabaseLayer._is_valid_table_name("db_evil; DROP TABLE x") is False
        assert MySQLDatabaseLayer._is_valid_table_name("db_x'); --") is False
        assert MySQLDatabaseLayer._is_valid_table_name("db_x` OR 1=1") is False
        # 非法前缀
        assert MySQLDatabaseLayer._is_valid_table_name("information_schema") is False
        assert MySQLDatabaseLayer._is_valid_table_name("mysql.user") is False
        # 含大写/特殊字符
        assert MySQLDatabaseLayer._is_valid_table_name("db_BarData") is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_database.py::TestDatabaseStatsTableNameValidation -v`

Expected: FAIL，`AttributeError: 'MySQLDatabaseLayer' has no attribute '_is_valid_table_name'`

- [ ] **Step 3: 添加白名单校验方法并接入 get_database_stats**

在 `vnpy_china_data/database.py` 的 `MySQLDatabaseLayer` 类内、`get_database_stats` 方法之前（约第 1219 行前）插入静态方法：

```python
    @staticmethod
    def _is_valid_table_name(table_name: str) -> bool:
        """校验表名是否合法（白名单：仅允许 db_ 前缀的小写字母与下划线）

        Args:
            table_name: 待校验的表名

        Returns:
            是否合法
        """
        if not table_name or not isinstance(table_name, str):
            return False
        return bool(re.match(r"^db_[a-z_]+$", table_name))
```

并在文件顶部 `database.py` 的 import 区（`from datetime import datetime` 附近）补充 `re` 导入：

```python
from datetime import datetime
import re
```

然后修改 `get_database_stats` 内的循环（database.py:1248-1256），将：

```python
            tables = []
            for table_name, size_mb in size_rows:
                try:
                    count_sql = f"SELECT COUNT(*) FROM `{table_name}`"
                    cursor.execute(count_sql)
                    row_count = cursor.fetchone()[0]
                except Exception:
                    row_count = 0
```

替换为：

```python
            tables = []
            for table_name, size_mb in size_rows:
                # 白名单校验：拒绝非 db_ 前缀或含特殊字符的表名
                if not self._is_valid_table_name(table_name):
                    logger.warning(f"get_database_stats 跳过非法表名: {table_name}")
                    continue
                try:
                    count_sql = f"SELECT COUNT(*) FROM `{table_name}`"
                    cursor.execute(count_sql)
                    row_count = cursor.fetchone()[0]
                except Exception:
                    row_count = 0
```

- [ ] **Step 4: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_database.py -v`

Expected: 全部 passed（含 Task 3 的 2 个 + 本任务 2 个）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/database.py vnpy_china_data/tests/test_database.py
git commit -m "🔒️ security(vnpy_china_data): get_database_stats表名白名单校验

- 新增_is_valid_table_name静态方法(正则^db_[a-z_]+$)
- 循环内拒绝非法表名,防止information_schema返回的表名注入"
```

---

### Task 8: _parse_exchange 移除冗余 in 判断

**Files:**
- Modify: `vnpy_china_data/gui_engine.py:423-448`（_parse_exchange）
- Test: `vnpy_china_data/tests/test_gui_engine.py`（扩展边缘用例）

- [ ] **Step 1: 写边缘用例测试**

在 `vnpy_china_data/tests/test_gui_engine.py` 的 `TestChinaDataGuiEngineHkConnect` 类内追加（注意：`gui_engine` fixture 已在第 38-52 行定义）：

```python
    def test_parse_exchange_edge_cases(self, gui_engine):
        """测试 _parse_exchange 边缘用例（标准格式，纯 endswith 行为）"""
        # 港股通各后缀 → SEHK
        assert gui_engine._parse_exchange("0700.SHHK") == Exchange.SEHK
        assert gui_engine._parse_exchange("2318.SZHK") == Exchange.SEHK
        assert gui_engine._parse_exchange("09988.SEHK") == Exchange.SEHK
        assert gui_engine._parse_exchange("00700.HK") == Exchange.SEHK
        # A股各后缀
        assert gui_engine._parse_exchange("600000.SH") == Exchange.SSE
        assert gui_engine._parse_exchange("000001.SZ") == Exchange.SZSE
        # 无后缀纯代码（按首位判断）
        assert gui_engine._parse_exchange("600000") == Exchange.SSE
        assert gui_engine._parse_exchange("000001") == Exchange.SZSE
```

- [ ] **Step 2: 运行测试确认当前通过（基线）**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_gui_engine.py::TestChinaDataGuiEngineHkConnect::test_parse_exchange_edge_cases -v`

Expected: PASS（当前 `in` 与 `endswith` 对标准格式行为一致）。此步建立基线，确保简化后不回归。

- [ ] **Step 3: 简化 _parse_exchange**

修改 `vnpy_china_data/gui_engine.py:423-448`，将整个 `_parse_exchange` 方法替换为：

```python
    def _parse_exchange(self, symbol: str) -> Exchange:
        """从股票代码解析交易所

        重要：港股通股票（.SHHK/.SZHK）在历史数据下载时
        需要转换为香港本地交易所（.SEHK），因为港股通股票
        本身就是在香港联合交易所上市的。

        Args:
            symbol: 股票代码（如 "000001.SZ", "0700.SHHK", "0700.SEHK"）

        Returns:
            交易所枚举（港股通统一返回 SEHK）
        """
        # 港股通：沪港通/深港通/香港本地 → 统一 SEHK
        if symbol.endswith((".SHHK", ".SZHK", ".SEHK", ".HK")):
            return Exchange.SEHK
        # A股：上海/深圳
        elif symbol.endswith(".SH"):
            return Exchange.SSE
        elif symbol.endswith(".SZ"):
            return Exchange.SZSE
        else:
            # 默认按首位字符判断（A 股）
            if symbol.startswith("6"):
                return Exchange.SSE
            else:
                return Exchange.SZSE
```

- [ ] **Step 4: 运行全部 _parse_exchange 测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_gui_engine.py -v`

Expected: 全部 passed（含原有 `test_parse_exchange_hk_connect`、`test_parse_exchange_a股` + 新增 `test_parse_exchange_edge_cases`）

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/gui_engine.py vnpy_china_data/tests/test_gui_engine.py
git commit -m "🔧 refactor(vnpy_china_data): _parse_exchange移除冗余in判断

- 移除or '.XXX' in symbol冗余分支,仅保留endswith
- 港股通四后缀合并为元组endswith
- 全库确认调用方均用标准格式,行为不变"
```

---

### Task 9: 指数成分股去重并标注占位

**Files:**
- Modify: `vnpy_china_data/gui_engine.py:372-395`（get_index_symbols）
- Test: `vnpy_china_data/tests/test_gui_engine.py`（扩展）

- [ ] **Step 1: 写失败测试**

在 `vnpy_china_data/tests/test_gui_engine.py` 的 `TestChinaDataGuiEngineHkConnect` 类内追加：

```python
    def test_get_index_symbols_no_duplicates(self, gui_engine):
        """指数成分股列表无重复项"""
        for index in ["HS300", "ZZ500", "ZZ1000"]:
            symbols = gui_engine.get_index_symbols(index)
            assert len(symbols) == len(set(symbols)), \
                f"{index} 成分股存在重复: {symbols}"

    def test_get_index_symbols_unknown_returns_empty(self, gui_engine):
        """未知指数返回空列表"""
        assert gui_engine.get_index_symbols("UNKNOWN") == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_gui_engine.py::TestChinaDataGuiEngineHkConnect::test_get_index_symbols_no_duplicates -v`

Expected: FAIL，HS300 含 `000333.SZ` 重复（列表长度 != 集合长度）

- [ ] **Step 3: 去重并加占位注释**

修改 `vnpy_china_data/gui_engine.py:372-395`，将：

```python
            # 沪深300成分股（前50只示例）
            if index == "HS300":
                symbols = [
                    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
                    "601318.SH", "601398.SH", "601857.SH", "601988.SH",
                    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
                    "000333.SZ", "000333.SZ", "000858.SZ", "002594.SZ",
                ]
            # 中证500成分股（前50只示例）
            elif index == "ZZ500":
                symbols = [
                    "600000.SH", "600004.SH", "600009.SH", "600010.SH",
                    "600016.SH", "600030.SH", "600104.SH", "600196.SH",
                    "000001.SZ", "000002.SZ", "000006.SZ", "000009.SZ",
                    "000012.SZ", "000025.SZ", "000027.SZ", "000030.SZ",
                ]
            # 中证1000成分股（前50只示例）
            elif index == "ZZ1000":
                symbols = [
                    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
                    "601318.SH", "601398.SH", "601857.SH", "601988.SH",
                    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
                    "000333.SZ", "000858.SZ", "002594.SZ", "300750.SZ",
                ]
            else:
                symbols = []
```

替换为：

```python
            # NOTE: 以下为占位示例数据（每指数 16 只），非真实成分股。
            # 真实数据待接入 Tushare index_weight / index_member API。
            # 沪深300成分股（占位示例）
            if index == "HS300":
                symbols = [
                    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
                    "601318.SH", "601398.SH", "601857.SH", "601988.SH",
                    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
                    "000333.SZ", "000858.SZ", "002594.SZ", "601166.SH",
                ]
            # 中证500成分股（占位示例）
            elif index == "ZZ500":
                symbols = [
                    "600000.SH", "600004.SH", "600009.SH", "600010.SH",
                    "600016.SH", "600030.SH", "600104.SH", "600196.SH",
                    "000001.SZ", "000002.SZ", "000006.SZ", "000009.SZ",
                    "000012.SZ", "000025.SZ", "000027.SZ", "000030.SZ",
                ]
            # 中证1000成分股（占位示例）
            elif index == "ZZ1000":
                symbols = [
                    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
                    "601318.SH", "601398.SH", "601857.SH", "601988.SH",
                    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
                    "000333.SZ", "000858.SZ", "002594.SZ", "300750.SZ",
                ]
            else:
                symbols = []
```

> 修正点：HS300 原列表中 `000333.SZ` 出现两次，第二次替换为 `601166.SH`（兴业银行），消除重复。

- [ ] **Step 4: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_gui_engine.py -v`

Expected: 全部 passed

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/gui_engine.py vnpy_china_data/tests/test_gui_engine.py
git commit -m "🐛 fix(vnpy_china_data): 指数成分股去重并标注占位

- HS300移除000333.SZ重复项(改为601166.SH)
- 三指数列表加NOTE注释明确为占位示例数据
- 真实数据待接入Tushare index_weight"
```

---

### Task 10: requirements 补全缺失依赖

**Files:**
- Modify: `vnpy_china_data/requirements.txt`

- [ ] **Step 1: 补全依赖**

将 `vnpy_china_data/requirements.txt` 全文替换为：

```txt
# A股数据服务模块依赖

# 数据库
pymysql>=1.0.0
DBUtils>=3.0.0

# 缓存
redis>=4.0.0

# 数据处理
pandas>=2.0.0
numpy>=1.24.0

# Tushare数据接口
tushare>=1.4.0

# HTTP请求（crawler 爬虫模块依赖）
requests>=2.28.0

# Excel解析（部分数据导入导出依赖）
openpyxl>=3.0.0

# A股交易相关
vnpy>=4.4.0
```

- [ ] **Step 2: 验证文件内容**

Run: `conda run -n Quant-3.11 python -c "import pathlib; t=pathlib.Path('vnpy_china_data/requirements.txt').read_text(encoding='utf-8'); assert 'requests' in t and 'openpyxl' in t and 'vnpy>=4.4.0' in t; print('REQUIREMENTS_OK')"`

Expected: `REQUIREMENTS_OK`

- [ ] **Step 3: 提交**

```bash
git add vnpy_china_data/requirements.txt
git commit -m "📝 docs(vnpy_china_data): requirements补全requests/openpyxl并锁定vnpy版本

- 补requests(crawler爬虫依赖)与openpyxl(Excel导入导出)
- vnpy锁定为>=4.4.0对齐CLAUDE.md当前版本"
```

---

### Task 11: download_bar_data 区分性日志

**Files:**
- Modify: `vnpy_china_data/service.py:213-249`（download_bar_data）
- Test: `vnpy_china_data/tests/test_service.py`（新建）

- [ ] **Step 1: 写失败测试**

创建 `vnpy_china_data/tests/test_service.py`：

```python
"""数据服务层单元测试"""

import logging
from datetime import date
from unittest.mock import Mock

import pytest

from vnpy.trader.constant import Exchange, Interval

from vnpy_china_data.service import ChinaDataService


def make_service_bypass_init(
    qmt_connected: bool,
    tushare_connected: bool = True,
):
    """绕过单例 __init__ 构造 service 实例（仅设置测试所需属性）"""
    service = ChinaDataService.__new__(ChinaDataService)
    service.qmt_adapter = Mock()
    service.qmt_adapter.connected = qmt_connected
    service.tushare_adapter = Mock()
    service.tushare_adapter.connected = tushare_connected
    service.database = Mock()
    # mock _fetch_bars_from_api 返回空（模拟无数据返回）
    service._fetch_bars_from_api = Mock(return_value=[])
    return service


class TestDownloadBarDataSemantics:
    """download_bar_data 区分性日志测试"""

    def test_warns_when_all_sources_disconnected(self, caplog):
        """两个数据源均未连接时记录 warning"""
        service = make_service_bypass_init(
            qmt_connected=False, tushare_connected=False
        )

        with caplog.at_level(logging.WARNING):
            result = service.download_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

        assert result == []
        assert "均未连接" in caplog.text

    def test_info_when_connected_but_no_data(self, caplog):
        """数据源已连接但无数据时记录 info（非 warning）"""
        service = make_service_bypass_init(qmt_connected=True)

        with caplog.at_level(logging.INFO):
            result = service.download_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

        assert result == []
        assert "无新数据" in caplog.text
        # 不应同时出现未连接 warning
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 0

    def test_info_when_qmt_down_but_tushare_up(self, caplog):
        """QMT未连接但Tushare可用时记info（仍可回退获取，非warning）"""
        service = make_service_bypass_init(
            qmt_connected=False, tushare_connected=True
        )

        with caplog.at_level(logging.INFO):
            result = service.download_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

        assert result == []
        assert "无新数据" in caplog.text
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_service.py -v`

Expected: 2 failed，日志中无 "未连接"/"无新数据"（当前 download_bar_data 空返回时无区分性日志）

- [ ] **Step 3: 在 download_bar_data 增加区分性日志**

修改 `vnpy_china_data/service.py:213-249`，将 `download_bar_data` 方法替换为：

```python
    def download_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: date,
        end: date
    ) -> List[BarData]:
        """下载并存储历史K线数据

        这个方法会强制从API获取数据并存储到数据库，跳过缓存。
        专门用于历史数据批量下载功能。

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期
            start: 开始日期
            end: 结束日期

        Returns:
            下载的K线数据列表
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 转换为datetime
        start_datetime = datetime.combine(start, datetime.min.time())
        end_datetime = datetime.combine(end, datetime.max.time())

        # 直接从API获取
        api_data = self._fetch_bars_from_api(
            symbol, exchange, interval, start_datetime, end_datetime
        )

        # 存储到数据库
        if api_data:
            self.database.save_bar_data(api_data)
        else:
            # 区分性日志：与 _fetch_bars_from_api 的 QMT→Tushare 回退链对应
            # 仅当两个数据源均未连接时才记 warning，否则视为"无新数据"
            qmt_ok = self.qmt_adapter and self.qmt_adapter.connected
            ts_ok = self.tushare_adapter and self.tushare_adapter.connected
            if not qmt_ok and not ts_ok:
                logger.warning(f"下载失败: {symbol} 数据源均未连接")
            else:
                logger.info(f"无新数据: {symbol} 该区间无回补")

        return api_data
```

- [ ] **Step 4: 运行测试验证通过**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/test_service.py -v`

Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add vnpy_china_data/service.py vnpy_china_data/tests/test_service.py
git commit -m "✨ feat(vnpy_china_data): download_bar_data区分性日志

- 空返回时按双数据源连接状态区分:均未连接→warning,否则→info
- 与_fetch_bars_from_api的QMT→Tushare回退链对应
- 调用方可从日志区分「API失败」与「回补无新数据」
- 不改_fetch_bars_from_api返回语义"
```

---

## 全量验证

### Task 12: 全量测试与验收

- [ ] **Step 1: 运行模块全部测试**

Run: `conda run -n Quant-3.11 python -m pytest vnpy_china_data/tests/ -v`

Expected: 全部 passed，无 error/failure

- [ ] **Step 2: 验收标准逐项确认**

```bash
# 1. validator.py 语法正确
conda run -n Quant-3.11 python -c "import ast; ast.parse(open('vnpy_china_data/validator.py', encoding='utf-8').read()); print('SYNTAX_OK')"

# 2. DataValidator 可导入
conda run -n Quant-3.11 python -c "from vnpy_china_data.validator import DataValidator; print('IMPORT_OK')"

# 3. 模块包可导入
conda run -n Quant-3.11 python -c "import vnpy_china_data; print('PACKAGE_OK')"
```

Expected: 全部输出 `_OK`

- [ ] **Step 3: Grep 确认无 MemoryCache 残留**

用 Grep 工具搜索 `MemoryCache`，确认源码（`vnpy_china_data/`）无定义与引用。

- [ ] **Step 4: 连接池归还验证（可选，需 MySQL 环境）**

若有 MySQL 环境，运行以下脚本验证连接归还：

```python
# verify_pool.py（手动创建运行）
from vnpy_china_data.database import MySQLDatabaseLayer
db = MySQLDatabaseLayer(host="localhost", port=3306, user="root",
                        password="", database="vnpy_china")
db.connect()
for _ in range(100):
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
# 若无连接泄漏，此处不阻塞
print("POOL_OK")
```

Expected: 输出 `POOL_OK` 且不阻塞（修复前会在第 ~15 次循环阻塞）

---

## 备注

- **设计文档笔误修正：** 设计文档 P0 第 1 点"末尾 `return False` 归位"应为 `return True`（validate_bar_data 语义是"有效返回 True"）。本计划 Task 1 Step 3 已用正确值，实现完成后可同步更新设计文档。
- **测试路径硬编码：** 现有测试文件含 `sys.path.insert(0, '/Users/erton/Github/vnpy')`（macOS 路径）。本计划新增测试不添加此行（依赖 conda 环境的包安装）。若运行时 ImportError，需确认 `vnpy_china_data` 已通过 `pip install -e .` 或 PYTHONPATH 可导入。
- **xtquant mock：** Task 4 测试通过 `sys.modules['xtquant']` 注入 mock，与现有 `test_get_bar_data_with_mock_xtdata` 模式一致。
