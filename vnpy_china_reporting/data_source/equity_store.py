"""
权益快照存储

提供每日权益快照的写入与查询。权益变化法盈亏 = 期末权益 - 期初权益，
其中期初权益即取自上一交易日的快照。
"""

from datetime import date
from typing import Optional
import logging

from .db import DataSourceDB

logger = logging.getLogger(__name__)


class EquitySnapshotStore:
    """每日权益快照 CRUD"""

    def __init__(self, db: DataSourceDB):
        """
        Args:
            db: 数据源连接
        """
        self.db = db

    def save_snapshot(
        self,
        snapshot_date: date,
        account_id: str,
        total_equity: float,
        available_cash: float = 0.0,
        market_value: float = 0.0,
    ) -> int:
        """保存/更新当日权益快照（ON DUPLICATE KEY UPDATE，幂等）

        同一 (snapshot_date, account_id) 重复写入会覆盖，适合收盘后定时刷新。

        Args:
            snapshot_date: 快照日期
            account_id: 账户ID
            total_equity: 总权益（balance）
            available_cash: 可用资金
            market_value: 持仓市值

        Returns:
            受影响行数
        """
        sql = """
            INSERT INTO equity_snapshot
                (snapshot_date, account_id, total_equity, available_cash, market_value)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_equity   = VALUES(total_equity),
                available_cash = VALUES(available_cash),
                market_value   = VALUES(market_value)
        """
        return self.db.execute(sql, (
            snapshot_date, account_id, total_equity, available_cash, market_value
        ))

    def get_equity(
        self,
        snapshot_date: date,
        account_id: Optional[str] = None
    ) -> Optional[float]:
        """取指定日期的总权益

        Args:
            snapshot_date: 日期
            account_id: 账户ID；为 None 时取任意一条

        Returns:
            总权益；无记录返回 None
        """
        if account_id:
            rows = self.db.query(
                "SELECT total_equity FROM equity_snapshot "
                "WHERE snapshot_date=%s AND account_id=%s",
                (snapshot_date, account_id),
            )
        else:
            rows = self.db.query(
                "SELECT total_equity FROM equity_snapshot "
                "WHERE snapshot_date=%s ORDER BY account_id LIMIT 1",
                (snapshot_date,),
            )
        return float(rows[0]["total_equity"]) if rows else None

    def get_latest_before(
        self,
        before_date: date,
        account_id: Optional[str] = None
    ) -> Optional[float]:
        """取 before_date 之前（不含）最近一个交易日的总权益，用作期初权益

        Args:
            before_date: 截止日期（不含）
            account_id: 账户ID；为 None 时取任意一条

        Returns:
            总权益；无记录返回 None
        """
        if account_id:
            rows = self.db.query(
                "SELECT total_equity FROM equity_snapshot "
                "WHERE snapshot_date < %s AND account_id=%s "
                "ORDER BY snapshot_date DESC LIMIT 1",
                (before_date, account_id),
            )
        else:
            rows = self.db.query(
                "SELECT total_equity FROM equity_snapshot "
                "WHERE snapshot_date < %s "
                "ORDER BY snapshot_date DESC, account_id LIMIT 1",
                (before_date,),
            )
        return float(rows[0]["total_equity"]) if rows else None
