"""
vnpy_china_backtest - A股增强回测模块

在VeighNa现有回测系统基础上增加A股特色交易模拟功能：
1. 交易成本模拟：佣金、印花税、过户费、经手费
2. 滑点模拟：固定、百分比、冲击成本
3. 涨跌停处理：涨停无法买入、跌停无法卖出
4. T+1规则模拟：当日买入次日才能卖出
5. 回测报告增强：A股特有指标
"""

from vnpy_china_backtest.cost import (
    CostCalculator,
    CostConfig,
    TradingCost,
    AStockCost,
    CostCalculatorFactory
)

from vnpy_china_backtest.slippage import (
    SlippageModel,
    FixedSlippage,
    PercentSlippage,
    ImpactCostSlippage,
    AdaptiveSlippage,
    SlippageModelFactory,
    SlippageConfig
)

from vnpy_china_backtest.rules import (
    PriceLimitHandler,
    PriceLimitEngine,
    LimitPrices,
    OrderCheckResult,
    T1Simulator,
    BuyRecord,
    PositionRecord
)

from vnpy_china_backtest.report import (
    MetricsCalculator,
    EnhancedMetrics
)

from vnpy_china_backtest.engine import (
    EnhancedBacktestEngine,
    create_engine
)

from vnpy_china_backtest.config import (
    BacktestConfig,
    default_config,
    get_config,
    update_config
)

__version__ = "1.0.0"

__all__ = [
    # 版本
    "__version__",

    # 成本计算
    "CostCalculator",
    "CostConfig",
    "TradingCost",
    "AStockCost",
    "CostCalculatorFactory",

    # 滑点模型
    "SlippageModel",
    "FixedSlippage",
    "PercentSlippage",
    "ImpactCostSlippage",
    "AdaptiveSlippage",
    "SlippageModelFactory",
    "SlippageConfig",

    # 交易规则
    "PriceLimitHandler",
    "PriceLimitEngine",
    "LimitPrices",
    "OrderCheckResult",
    "T1Simulator",
    "BuyRecord",
    "PositionRecord",

    # 报告
    "MetricsCalculator",
    "EnhancedMetrics",

    # 引擎
    "EnhancedBacktestEngine",
    "create_engine",

    # 配置
    "BacktestConfig",
    "default_config",
    "get_config",
    "update_config",
]
