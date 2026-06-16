"""
T+1 持仓成交流水持久化

事件溯源：append-only 记录每笔成交，启动时重放重建内存持仓。
依赖注入 db（鸭子类型：execute(sql,args)->int, query(sql,args)->List[dict]），
典型实现为 vnpy_china_reporting.data_source.db.DataSourceDB。
"""

from datetime import datetime
from typing import Any, Dict, List

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

# 以下 SQL 常量用于 T1PositionStore.append_trade / load_all 方法
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

    def load_all(self) -> List[Dict[str, Any]]:
        """读取全部流水，按 (trade_time, id) 排序"""
        return self.db.query(LOAD_ALL_SQL)
