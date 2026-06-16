"""
报表数据源 - 表结构定义与初始化

权益变化法盈亏需要期初权益快照（vnpy 不提供历史权益），行业分析需要股票→行业
映射（miniQMT 板块反查）。两表均为幂等建表。
"""

import logging
from .db import DataSourceDB

logger = logging.getLogger(__name__)


EQUITY_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS equity_snapshot (
    snapshot_date  DATE NOT NULL COMMENT '快照日期（交易日）',
    account_id     VARCHAR(64) NOT NULL COMMENT '账户ID',
    total_equity   DECIMAL(20,4) NOT NULL COMMENT '总权益（balance）',
    available_cash DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '可用资金',
    market_value   DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '持仓市值',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    PRIMARY KEY (snapshot_date, account_id),
    INDEX idx_account_date (account_id, snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日权益快照（权益变化法期初权益源）'
"""

STOCK_INDUSTRY_DDL = """
CREATE TABLE IF NOT EXISTS stock_industry (
    symbol     VARCHAR(32) NOT NULL COMMENT '股票代码',
    exchange   VARCHAR(16) NOT NULL DEFAULT '' COMMENT '交易所',
    industry   VARCHAR(64) NOT NULL DEFAULT '' COMMENT '行业（miniQMT板块反查）',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (symbol, exchange),
    INDEX idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票行业映射（miniQMT板块反查缓存）'
"""


def init_schema(db: DataSourceDB) -> None:
    """创建所有数据源表（幂等）

    Args:
        db: DataSourceDB 实例
    """
    db.execute(EQUITY_SNAPSHOT_DDL)
    db.execute(STOCK_INDUSTRY_DDL)
    logger.info("报表数据源表已就绪: equity_snapshot, stock_industry")
