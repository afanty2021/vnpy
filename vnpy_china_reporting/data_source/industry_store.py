"""
股票行业映射存储

行业数据来自 miniQMT 板块反查（get_instrument_detail 不含行业字段）。
报表的持仓行业分析读此映射填充 PositionRecord.industry。
"""

from typing import Optional, List, Tuple, Dict
import logging

from .db import DataSourceDB

logger = logging.getLogger(__name__)


class IndustryStore:
    """股票行业映射 CRUD"""

    def __init__(self, db: DataSourceDB):
        """
        Args:
            db: 数据源连接
        """
        self.db = db

    def upsert(self, symbol: str, exchange: str, industry: str) -> int:
        """写入/更新单条行业映射（幂等）"""
        sql = """
            INSERT INTO stock_industry (symbol, exchange, industry)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE industry = VALUES(industry)
        """
        return self.db.execute(sql, (symbol, exchange, industry))

    def batch_upsert(self, records: List[Tuple[str, str, str]]) -> int:
        """批量 upsert

        Args:
            records: [(symbol, exchange, industry), ...]

        Returns:
            受影响行数
        """
        if not records:
            return 0
        sql = """
            INSERT INTO stock_industry (symbol, exchange, industry)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE industry = VALUES(industry)
        """
        return self.db.executemany(sql, records)

    def get_industry(self, symbol: str, exchange: Optional[str] = None) -> Optional[str]:
        """查询单只股票的行业

        Returns:
            行业名；无记录返回 None
        """
        if exchange:
            rows = self.db.query(
                "SELECT industry FROM stock_industry WHERE symbol=%s AND exchange=%s",
                (symbol, exchange),
            )
        else:
            rows = self.db.query(
                "SELECT industry FROM stock_industry WHERE symbol=%s LIMIT 1",
                (symbol,),
            )
        return rows[0]["industry"] if rows else None

    def get_industry_map(self, symbols: List[str]) -> Dict[str, str]:
        """批量查询股票→行业映射

        Args:
            symbols: 股票代码列表

        Returns:
            {symbol: industry}（缺失的不包含在结果中）
        """
        if not symbols:
            return {}
        placeholders = ",".join(["%s"] * len(symbols))
        rows = self.db.query(
            f"SELECT symbol, industry FROM stock_industry WHERE symbol IN ({placeholders})",
            symbols,
        )
        return {r["symbol"]: r["industry"] for r in rows}
