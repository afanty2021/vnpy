"""
核心枚举类型定义
"""

from enum import Enum


class ReportType(Enum):
    """报表类型"""
    DAILY = "daily"       # 日报
    MONTHLY = "monthly"   # 月报
    YEARLY = "yearly"     # 年报


class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"         # 多头
    SHORT = "short"       # 空头


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"           # 低风险
    MEDIUM = "medium"     # 中风险
    HIGH = "high"         # 高风险


class TradeDirection(Enum):
    """交易方向"""
    BUY = "buy"           # 买入
    SELL = "sell"         # 卖出
