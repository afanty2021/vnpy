"""
VeighNa A股行情数据分析模块

提供专业的A股市场行情数据分析能力，包括：
- Level-2行情分析（十档行情、逐笔成交、主力动向）
- 资金流向分析
- 技术指标增强（涨跌停统计、板块指数）
- 集合竞价分析

主要类：
- Level2Analyzer: Level-2综合分析器
- MoneyFlowAnalyzer: 资金流向分析器
- TechnicalAnalyzer: 技术指标分析器
- AuctionAnalyzer: 集合竞价分析器
- QmtDataAdapter: QMT数据适配器
- TushareDataAdapter: Tushare数据适配器
"""

from .base import BaseAnalyzer, RealtimeAnalyzer, HistoricalAnalyzer

# Level-2行情分析
from .level2 import (
    Level2Analyzer,
    OrderQueueAnalyzer,
    TickFlowAnalyzer,
    MainForceAnalyzer
)

# 资金流向分析
from .money_flow import (
    MoneyFlowAnalyzer,
    MoneyFlowClassifier,
    MoneyFlowIndicator
)

# 技术指标增强
from .technical import (
    TechnicalAnalyzer,
    LimitStatsAnalyzer,
    SectorIndexAnalyzer
)

# 集合竞价分析
from .auction import (
    AuctionAnalyzer,
    VolumeRatioCalculator,
    OpenPricePredictor
)

# 数据适配器
from .adapters import (
    QmtDataAdapter,
    TushareDataAdapter
)

# 工具函数
from .utils import (
    format_money,
    format_volume,
    calculate_change_pct,
    get_trading_status,
    normalize_symbol,
)

# 数据类型
from .objects import (
    MoneyFlowLevel,
    LimitType,
    TradeDirection,
    OrderQueueData,
    TickFlowData,
    MainForceData,
    MoneyFlowData,
    LimitStats,
    SectorIndexData,
    AuctionData,
    AnalysisSignal,
)

# GUI应用
from .app import ChinaAnalysisApp
from .engine import ChinaAnalysisEngine

__version__ = "1.0.0"

__all__ = [
    # 基类
    "BaseAnalyzer",
    "RealtimeAnalyzer",
    "HistoricalAnalyzer",
    # Level-2
    "Level2Analyzer",
    "OrderQueueAnalyzer",
    "TickFlowAnalyzer",
    "MainForceAnalyzer",
    # 资金流向
    "MoneyFlowAnalyzer",
    "MoneyFlowClassifier",
    "MoneyFlowIndicator",
    # 技术指标
    "TechnicalAnalyzer",
    "LimitStatsAnalyzer",
    "SectorIndexAnalyzer",
    # 集合竞价
    "AuctionAnalyzer",
    "VolumeRatioCalculator",
    "OpenPricePredictor",
    # 适配器
    "QmtDataAdapter",
    "TushareDataAdapter",
    # 工具函数
    "format_money",
    "format_volume",
    "calculate_change_pct",
    "get_trading_status",
    "normalize_symbol",
    # 数据类型
    "MoneyFlowLevel",
    "LimitType",
    "TradeDirection",
    "OrderQueueData",
    "TickFlowData",
    "MainForceData",
    "MoneyFlowData",
    "LimitStats",
    "SectorIndexData",
    "AuctionData",
    "AnalysisSignal",
    # GUI应用
    "ChinaAnalysisApp",
    "ChinaAnalysisEngine",
]
