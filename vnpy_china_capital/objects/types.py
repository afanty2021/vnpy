"""
资金管理系统核心数据类型定义

定义仓位管理、订单管理、资金曲线和风险指标等核心数据结构。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PositionType(Enum):
    """仓位类型"""
    EQUAL_WEIGHT = "equal_weight"      # 等权重
    VALUE_WEIGHT = "value_weight"      # 市值加权
    RISK_PARITY = "risk_parity"        # 风险平价
    DYNAMIC = "dynamic"                # 动态仓位


class OrderBatchType(Enum):
    """订单批次类型"""
    EQUAL = "equal"                    # 等量分批
    PYRAMID_BUY = "pyramid_buy"        # 金字塔买入
    PYRAMID_SELL = "pyramid_sell"      # 金字塔卖出
    TWAP = "twap"                      # 时间加权
    VWAP = "vwap"                      # 成交量加权


@dataclass
class OrderBatch:
    """
    委托批次

    用于分批下单时的批次配置，包含价格时间和、数量、延迟批次类型。
    """
    price: float                       # 委托价格（0=市价）
    volume: int                        # 委托数量
    delay: int                         # 延迟秒数
    batch_type: OrderBatchType         # 批次类型


@dataclass
class PositionAllocation:
    """
    仓位分配结果

    记录单个股票的仓位分配结果，包括目标股数、目标金额、权重和分配原因。
    """
    symbol: str                        # 股票代码
    target_volume: int                 # 目标股数
    target_value: float                # 目标金额
    weight: float                      # 权重比例
    reason: str                        # 分配原因


@dataclass
class EquityPoint:
    """
    资金曲线点

    记录资金曲线的单个数据点，包含时间、资金值、回撤和收益率信息。
    """
    datetime: datetime                 # 时间点
    equity: float                      # 资金值
    drawdown: float = 0.0              # 回撤比例
    daily_return: float = 0.0          # 日收益率
    cumulative_return: float = 0.0     # 累计收益率


@dataclass
class RiskMetrics:
    """
    风险指标

    记录策略的风险评估指标，包括最大回撤、夏普比率等。
    """
    max_drawdown: float                # 最大回撤
    current_drawdown: float            # 当前回撤
    sharpe_ratio: float                # 夏普比率
    sortino_ratio: float               # 索提诺比率
    calmar_ratio: float                # 卡玛比率
    volatility: float                  # 波动率
