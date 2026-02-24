"""
数据类型定义模块

定义行情分析系统所需的所有数据结构和枚举类型。
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional
from enum import Enum


class MoneyFlowLevel(Enum):
    """资金流向级别"""
    SUPER_LARGE = "super_large"    # 超大单 > 100万
    LARGE = "large"                # 大单 20-100万
    MEDIUM = "medium"              # 中单 5-20万
    SMALL = "small"                # 小单 < 5万


class LimitType(Enum):
    """涨跌停类型"""
    LIMIT_UP = "limit_up"          # 涨停
    LIMIT_DOWN = "limit_down"      # 跌停
    NORMAL = "normal"              # 正常


class TradeDirection(Enum):
    """交易方向"""
    BUY = "buy"                    # 买入
    SELL = "sell"                 # 卖出
    NEUTRAL = "neutral"           # 中性


@dataclass
class OrderQueueData:
    """委托队列数据

    记录十档买卖盘的委托队列信息。
    """
    symbol: str
    datetime: datetime

    # 卖盘队列（10档）
    ask_prices: List[float] = field(default_factory=list)       # 卖价 [ask1...ask10]
    ask_volumes: List[int] = field(default_factory=list)        # 卖量
    ask_queue: List[List[int]] = field(default_factory=list)    # 各档位委托明细

    # 买盘队列（10档）
    bid_prices: List[float] = field(default_factory=list)       # 买价 [bid1...bid10]
    bid_volumes: List[int] = field(default_factory=list)        # 买量
    bid_queue: List[List[int]] = field(default_factory=list)    # 各档位委托明细


@dataclass
class TickFlowData:
    """逐笔成交数据

    记录每一笔成交的详细信息。
    """
    symbol: str
    datetime: datetime
    price: float
    volume: int
    amount: float                   # 成交金额
    direction: str                 # buy/sell
    function_code: int = 0         # 成交性质


@dataclass
class MainForceData:
    """主力动向数据

    统计主力资金的买卖情况。
    """
    symbol: str
    datetime: datetime
    buy_volume: float = 0.0        # 买入成交量
    sell_volume: float = 0.0       # 卖出成交量
    net_volume: float = 0.0        # 净成交量
    main_force_ratio: float = 0.0  # 主力净流入比例
    direction: str = "neutral"     # 主力方向 buy/sell/neutral


@dataclass
class MoneyFlowData:
    """资金流向数据

    分类统计各级别资金的流向情况。
    """
    symbol: str
    datetime: datetime

    # 分类资金流向（元）
    super_large_inflow: float = 0.0   # 超大单净流入
    large_inflow: float = 0.0         # 大单净流入
    medium_inflow: float = 0.0        # 中单净流入
    small_inflow: float = 0.0         # 小单净流入

    # 汇总指标
    main_inflow: float = 0.0          # 主力净流入 (超大+大单)
    retail_inflow: float = 0.0        # 散户净流入 (中+小单)
    net_inflow: float = 0.0          # 总净流入


@dataclass
class LimitStats:
    """涨跌停统计

    记录股票的涨跌停情况。
    """
    symbol: str
    date: date
    limit_up_days: int = 0          # 连续涨停天数
    limit_down_days: int = 0        # 连续跌停天数
    is_limit_up: bool = False       # 今日涨停
    is_limit_down: bool = False     # 今日跌停
    limit_up_count: int = 0         # 历史涨停次数
    limit_down_count: int = 0       # 历史跌停次数


@dataclass
class SectorIndexData:
    """板块指数数据

    记录板块的整体行情数据。
    """
    sector_code: str                # 板块代码
    sector_name: str                # 板块名称
    datetime: datetime
    index_value: float = 0.0        # 指数值
    change_pct: float = 0.0         # 涨跌幅
    volume: float = 0.0             # 成交量
    turnover: float = 0.0          # 换手率
    leading_stocks: List[str] = field(default_factory=list)  # 领涨股票


@dataclass
class AuctionData:
    """集合竞价数据

    记录集合竞价期间的各项数据。
    """
    symbol: str
    date: date

    # 基础数据
    pre_close: float = 0.0          # 昨收
    auction_price: float = 0.0      # 竞价成交价
    auction_volume: int = 0         # 竞价成交量
    auction_amount: float = 0.0     # 竞价成交额

    # 委托数据
    total_buy_volume: int = 0       # 总买委托量
    total_sell_volume: int = 0     # 总卖委托量
    buy_orders: int = 0             # 买委托笔数
    sell_orders: int = 0            # 卖委托笔数

    # 计算指标
    volume_ratio: float = 0.0       # 量比（竞价量/平均量）
    amplitude: float = 0.0         # 竞价振幅
    buy_sell_ratio: float = 0.0    # 买卖比
    open_prediction: float = 0.0   # 开盘价预测


@dataclass
class AnalysisSignal:
    """分析信号

    统一的分析信号输出格式。
    """
    symbol: str
    datetime: datetime
    signal_type: str                # 信号类型
    signal_value: float = 0.0       # 信号值
    confidence: float = 0.0          # 信号置信度
    reason: str = ""                # 信号原因


# 类型别名
Level2Data = Dict[str, any]         # Level-2原始数据字典
MarketData = Dict[str, any]         # 市场数据字典
