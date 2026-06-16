"""T1PositionStore 单元测试（mock db，不依赖真实 MySQL）"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

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

    def test_init_schema_idempotent_no_shortcut(self):
        """连续两次 init_schema 都调用 execute（无短路缓存导致第二次不建表）"""
        self.store.init_schema()
        self.store.init_schema()
        self.assertEqual(self.db.execute.call_count, 2)

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


if __name__ == "__main__":
    unittest.main()
