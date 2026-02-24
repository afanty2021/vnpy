"""
核心数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional
from .enums import ReportType, PositionSide, RiskLevel


@dataclass
class TradeRecord:
    """交易记录

    Attributes:
        trade_id: 交易ID，唯一标识每一笔交易
        symbol: 股票代码，如 '000001'
        direction: 交易方向，'buy' 或 'sell'
        volume: 成交量，手数
        price: 成交价格
        amount: 成交金额
        commission: 手续费
        timestamp: 成交时间
    """
    trade_id: str                         # 交易ID
    symbol: str                           # 股票代码
    direction: str                        # 交易方向买入/卖出
    volume: int                           # 成交量
    price: float                          # 成交价格
    amount: float                         # 成交金额
    commission: float                     # 手续费
    timestamp: datetime                   # 成交时间


@dataclass
class PositionRecord:
    """持仓记录

    Attributes:
        symbol: 股票代码
        name: 股票名称
        side: 持仓方向，多头或空头
        volume: 持仓数量
        avg_cost: 平均成本价
        current_price: 当前价格
        market_value: 市值
        unrealized_pnl: 未实现盈亏
        unrealized_pnl_ratio: 未实现盈亏比例
    """
    symbol: str                           # 股票代码
    name: str                             # 股票名称
    side: PositionSide                    # 持仓方向
    volume: int                           # 持仓数量
    avg_cost: float                       # 平均成本
    current_price: float                  # 当前价格
    market_value: float                   # 市值
    unrealized_pnl: float                 # 未实现盈亏
    unrealized_pnl_ratio: float          # 未实现盈亏比例


@dataclass
class AccountData:
    """账户数据

    Attributes:
        total_equity: 总权益（可用资金 + 持仓市值 + 盈亏）
        available_cash: 可用资金
        market_value: 持仓市值
        total_pnl: 总盈亏（已实现 + 未实现）
        total_pnl_ratio: 总盈亏比例
        commission: 手续费合计
        timestamp: 数据更新时间
    """
    total_equity: float                   # 总权益
    available_cash: float                 # 可用资金
    market_value: float                   # 持仓市值
    total_pnl: float                      # 总盈亏
    total_pnl_ratio: float               # 总盈亏比例
    commission: float                     # 手续费合计
    timestamp: datetime                   # 更新时间


@dataclass
class ReportData:
    """报表数据

    包含完整报表所需的所有数据，包括账户信息、持仓列表、交易记录等

    Attributes:
        report_type: 报表类型（日报/月报/年报）
        start_date: 统计开始日期
        end_date: 统计结束日期
        account: 账户数据
        positions: 持仓列表
        trades: 交易列表
        daily_pnl: 当期盈亏（统计期间的盈亏）
        daily_pnl_ratio: 当期盈亏比例
    """
    report_type: ReportType              # 报表类型
    start_date: date                     # 开始日期
    end_date: date                       # 结束日期
    account: AccountData                  # 账户数据
    positions: List[PositionRecord] = field(default_factory=list)   # 持仓列表
    trades: List[TradeRecord] = field(default_factory=list)          # 交易列表
    daily_pnl: float = 0.0               # 当期盈亏
    daily_pnl_ratio: float = 0.0         # 当期盈亏比例


@dataclass
class PositionAnalysis:
    """持仓分析结果

    Attributes:
        total_positions: 总持仓数量
        total_market_value: 总市值
        top_holdings: 重点持仓列表（按市值排序的前N只股票）
        concentration: 集中度（前N只股票市值占比）
        industry_distribution: 行业分布统计
    """
    total_positions: int                 # 总持仓数
    total_market_value: float            # 总市值
    top_holdings: List[Dict] = field(default_factory=list)   # 重点持仓
    concentration: float = 0.0           # 集中度
    industry_distribution: Dict = field(default_factory=dict) # 行业分布


@dataclass
class RiskMetrics:
    """风险指标

    Attributes:
        var_95: 95% VaR（Value at Risk），在95%置信度下的最大可能损失
        volatility: 波动率（年化）
        sharpe_ratio: 夏普比率（风险调整后收益）
        max_drawdown: 最大回撤
        risk_level: 风险等级
    """
    var_95: float                       # 95% VaR
    volatility: float                   # 波动率
    sharpe_ratio: float                 # 夏普比率
    max_drawdown: float                 # 最大回撤
    risk_level: RiskLevel               # 风险等级


@dataclass
class DailySummary:
    """每日交易摘要

    Attributes:
        date: 日期
        total_trades: 总成交笔数
        buy_trades: 买入笔数
        sell_trades: 卖出笔数
        total_volume: 总成交量
        total_amount: 总成交金额
        total_commission: 总手续费
        net_pnl: 净盈亏
    """
    date: date                          # 日期
    total_trades: int = 0               # 总成交笔数
    buy_trades: int = 0                 # 买入笔数
    sell_trades: int = 0                # 卖出笔数
    total_volume: int = 0               # 总成交量
    total_amount: float = 0.0           # 总成交金额
    total_commission: float = 0.0       # 总手续费
    net_pnl: float = 0.0                # 净盈亏


@dataclass
class MonthlySummary:
    """月度统计摘要

    Attributes:
        year: 年份
        month: 月份
        trading_days: 交易天数
        total_pnl: 月度总盈亏
        total_commission: 月度总手续费
        total_trades: 月度总成交笔数
        avg_daily_pnl: 日均盈亏
        win_rate: 胜率
    """
    year: int                           # 年份
    month: int                          # 月份
    trading_days: int = 0               # 交易天数
    total_pnl: float = 0.0              # 月度总盈亏
    total_commission: float = 0.0      # 月度总手续费
    total_trades: int = 0              # 月度总成交笔数
    avg_daily_pnl: float = 0.0          # 日均盈亏
    win_rate: float = 0.0               # 胜率
