"""T+1 持久化 MySQL 集成测试

默认跳过。启用方式（需 MySQL 在线、vnpy_china_config 已配置）：
    RUN_INTEGRATION=1 conda run -n Quant-3.11 python -m pytest \
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
            # 清理本测试残留（表可能尚未建立，任何失败视为环境不可用 → 跳过）
            self.db.execute(
                "DELETE FROM t1_trade_flow WHERE trade_id LIKE %s", ("TEST.INT.%",)
            )
        except Exception as e:
            self.skipTest(f"MySQL 环境不可用，跳过: {e}")

    def tearDown(self):
        try:
            self.db.execute(
                "DELETE FROM t1_trade_flow WHERE trade_id LIKE %s", ("TEST.INT.%",)
            )
        except Exception:
            pass

    def _make_trade(self, tradeid, direction, volume, dt):
        # vt_tradeid = f"{gateway_name}.{tradeid}" = "TEST.<tradeid>"
        return TradeData(
            gateway_name="TEST", symbol="000001", exchange=Exchange.SZSE,
            orderid="o1", tradeid=tradeid, direction=direction,
            offset=Offset.OPEN if direction == Direction.LONG else Offset.CLOSE,
            price=10.0, volume=volume, datetime=dt,
        )

    def test_append_then_replay_roundtrip(self):
        mock_dm = Mock(spec=DataSourceManager)

        # 引擎1：写入 3 笔（buy/buy/sell FIFO）。vt_tradeid = "TEST.INT.1/2/3"
        eng1 = ChinaStockRulesEngine(mock_dm, db=self.db)
        eng1.on_trade(self._make_trade("INT.1", Direction.LONG, 1000, datetime(2024, 2, 23, 9, 30)))
        eng1.on_trade(self._make_trade("INT.2", Direction.LONG, 500, datetime(2024, 2, 24, 9, 30)))
        eng1.on_trade(self._make_trade("INT.3", Direction.SHORT, 300, datetime(2024, 2, 24, 14, 0)))

        # 引擎2：新建实例，从 DB 重放
        eng2 = ChinaStockRulesEngine(mock_dm, db=self.db)

        # 内存持仓逐批次一致
        rp = eng1.t1_rules.positions["000001"]
        fp = eng2.t1_rules.positions["000001"]
        self.assertEqual(len(rp), len(fp))
        for r, f in zip(rp, fp):
            self.assertEqual((r.volume, r.available), (f.volume, f.available))
        # 数值锚点：第一笔 buy1000 被 sell300 FIFO 扣减 → available=700
        self.assertEqual(rp[0].available, 700)
        self.assertEqual(fp[0].available, 700)

    def test_idempotent_append_no_dup(self):
        """同一 vt_tradeid 重复 on_trade，DB 流水不翻倍、内存不虚增"""
        mock_dm = Mock(spec=DataSourceManager)
        eng = ChinaStockRulesEngine(mock_dm, db=self.db)
        # vt_tradeid = "TEST.INT.DUP"
        t = self._make_trade("INT.DUP", Direction.LONG, 1000, datetime(2024, 2, 24, 9, 30))
        eng.on_trade(t)
        eng.on_trade(t)   # 重复 → DB INSERT IGNORE 返回 0 → 内存跳过（幂等）

        # DB 流水仅 1 条
        rows = self.db.query(
            "SELECT COUNT(*) AS c FROM t1_trade_flow WHERE trade_id=%s",
            ("TEST.INT.DUP",),
        )
        self.assertEqual(int(rows[0]["c"]), 1)
        # 内存持仓不虚增（次日视角可卖量仍为 1000）
        self.assertEqual(
            eng.t1_rules.get_sellable_volume("000001", datetime(2024, 2, 25, 9, 0)),
            1000,
        )


if __name__ == "__main__":
    unittest.main()
