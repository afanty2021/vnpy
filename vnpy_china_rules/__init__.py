"""
VeighNa A股交易规则适配模块

提供A股T+1、涨跌停等特有交易规则的适配功能。
"""

from vnpy_china_rules.datasource import (
    StockInfo,
    DataSource,
    QMTDataSource,
    TushareDataSource,
    DataSourceManager,
)

from vnpy_china_rules.engine import (
    RuleResult,
    PositionRecord,
    ChinaStockRulesEngine,
    T1RulesEngine,
    PriceLimitRulesEngine,
    TimeRulesEngine,
    UnitRulesEngine,
    IpoRulesEngine,
)

from vnpy_china_rules.filter import (
    ChinaStockRiskFilter,
    create_risk_filter,
)

from vnpy_china_rules.strategy import (
    ChinaStockStrategy,
    TradingRuleMixin,
    create_strategy_base,
)

# GUI应用
from vnpy_china_rules.app import ChinaRulesApp
from vnpy_china_rules.gui_engine import ChinaRulesGuiEngine


__all__ = [
    # 数据源
    "StockInfo",
    "DataSource",
    "QMTDataSource",
    "TushareDataSource",
    "DataSourceManager",
    # 规则引擎
    "RuleResult",
    "PositionRecord",
    "ChinaStockRulesEngine",
    "T1RulesEngine",
    "PriceLimitRulesEngine",
    "TimeRulesEngine",
    "UnitRulesEngine",
    "IpoRulesEngine",
    # 风控过滤器
    "ChinaStockRiskFilter",
    "create_risk_filter",
    # 策略基类
    "ChinaStockStrategy",
    "TradingRuleMixin",
    "create_strategy_base",
    # GUI应用
    "ChinaRulesApp",
    "ChinaRulesGuiEngine",
]


__version__ = "0.1.0"
__author__ = "VeighNa Team"
