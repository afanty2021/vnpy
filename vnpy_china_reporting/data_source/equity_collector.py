"""
权益快照采集器

从主引擎（vnpy MainEngine）采集当日账户权益并落库，作为权益变化法盈亏的
期初权益源。由定时任务/主进程在每日收盘后调用 collect()。
"""

from datetime import date
from typing import Optional, Any
import logging

from .db import DataSourceDB
from .equity_store import EquitySnapshotStore

logger = logging.getLogger(__name__)


class EquitySnapshotCollector:
    """采集主引擎当日权益快照并落库"""

    def __init__(self, db: DataSourceDB, main_engine: Optional[Any] = None):
        """
        Args:
            db: 数据源连接
            main_engine: vnpy MainEngine 实例
        """
        self.db = db
        self.main_engine = main_engine
        self.store = EquitySnapshotStore(db)

    def collect(self, snapshot_date: Optional[date] = None) -> int:
        """采集并落库当日权益快照

        Args:
            snapshot_date: 快照日期，默认今天

        Returns:
            落库的账户数

        Raises:
            ValueError: main_engine 未注入
        """
        if self.main_engine is None:
            raise ValueError("main_engine 未注入，无法采集权益快照")

        snapshot_date = snapshot_date or date.today()

        try:
            accounts = self.main_engine.get_all_accounts()
        except Exception as e:
            logger.error("获取账户数据失败: %s", e)
            return 0

        if not accounts:
            logger.warning("无账户数据，跳过权益快照采集: %s", snapshot_date)
            return 0

        count = 0
        for acc in accounts:
            account_id = (
                getattr(acc, "vt_accountid", None) or getattr(acc, "accountid", "")
            )
            # A股 QMT 网关将真实可用现金/持仓市值放入 extra（见 patches/td.py:on_stock_asset）；
            # vnpy 原生 available=balance-frozen 在A股下≈总资产，不可直接用作可用现金。
            extra = getattr(acc, "extra", None) or {}
            available_cash = float(extra.get("cash", getattr(acc, "available", 0.0)))
            market_value = float(extra.get("market_value", 0.0))
            if "cash" not in extra:
                logger.warning(
                    "账户 %s 缺少 extra['cash']，可用现金回退到 available（A股下可能不准）",
                    account_id,
                )
            self.store.save_snapshot(
                snapshot_date=snapshot_date,
                account_id=account_id,
                total_equity=float(getattr(acc, "balance", 0.0)),
                available_cash=available_cash,
                market_value=market_value,
            )
            count += 1

        logger.info("权益快照采集完成: %s, %d 个账户", snapshot_date, count)
        return count
