"""
A股特有指标计算

包含基础收益指标和A股特有指标
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, date
import math

from vnpy.trader.object import TradeData, BarData
from vnpy.trader.constant import Direction


@dataclass
class EnhancedMetrics:
    """增强回测指标"""

    # 基础收益指标
    total_return: float = 0.0           # 总收益率
    annual_return: float = 0.0          # 年化收益率
    max_drawdown: float = 0.0           # 最大回撤
    sharpe_ratio: float = 0.0           # 夏普比率
    sortino_ratio: float = 0.0         # 索提诺比率
    calmar_ratio: float = 0.0           # 卡玛比率

    # A股特有指标
    win_rate: float = 0.0               # 胜率
    profit_loss_ratio: float = 0.0     # 盈亏比
    avg_holding_days: float = 0.0      # 平均持股天数
    avg_positions: float = 0.0         # 平均持仓数
    avg_capital_usage: float = 0.0     # 平均资金使用率
    max_positions: int = 0             # 最大持仓数

    # 交易统计
    total_trades: int = 0               # 总交易次数
    buy_trades: int = 0                # 买入次数
    sell_trades: int = 0               # 卖出次数
    max_consecutive_wins: int = 0       # 最大连续盈利
    max_consecutive_losses: int = 0     # 最大连续亏损

    # 成本统计
    total_cost: float = 0.0            # 总交易成本
    cost_rate: float = 0.0             # 成本费率
    avg_cost_per_trade: float = 0.0    # 笔均成本

    # 月度收益
    monthly_returns: Dict[str, float] = field(default_factory=dict)

    # 其他
    trading_days: int = 0              # 交易天数
    initial_capital: float = 0.0       # 初始资金
    final_capital: float = 0.0         # 最终资金


class MetricsCalculator:
    """指标计算器"""

    def __init__(self, annual_days: int = 240):
        """初始化

        Args:
            annual_days: 年交易日天数，默认240
        """
        self.annual_days = annual_days

    def calculate(
        self,
        trades: List[TradeData],
        equity_curve: List[float],
        trading_days: int,
        initial_capital: float,
        final_capital: float,
        total_cost: float = 0.0
    ) -> EnhancedMetrics:
        """计算所有指标

        Args:
            trades: 成交列表
            equity_curve: 权益曲线
            trading_days: 交易天数
            initial_capital: 初始资金
            final_capital: 最终资金
            total_cost: 总交易成本

        Returns:
            EnhancedMetrics: 增强指标
        """
        metrics = EnhancedMetrics()
        metrics.initial_capital = initial_capital
        metrics.final_capital = final_capital
        metrics.trading_days = trading_days
        metrics.total_cost = total_cost

        # 基础指标
        self._calculate_basic_metrics(
            metrics, equity_curve, trading_days, initial_capital, final_capital
        )

        # A股特有指标
        self._calculate_china_metrics(metrics, trades, equity_curve, initial_capital)

        # 交易统计
        self._calculate_trade_stats(metrics, trades)

        # 成本统计
        self._calculate_cost_stats(metrics, trades)

        # 月度收益
        metrics.monthly_returns = self._calculate_monthly_returns(equity_curve, trading_days)

        return metrics

    def _calculate_basic_metrics(
        self,
        metrics: EnhancedMetrics,
        equity_curve: List[float],
        trading_days: int,
        initial_capital: float,
        final_capital: float
    ) -> None:
        """计算基础指标"""
        if not equity_curve or initial_capital <= 0:
            return

        # 总收益率
        metrics.total_return = (final_capital - initial_capital) / initial_capital

        # 年化收益率
        if trading_days > 0:
            years = trading_days / self.annual_days
            if years > 0:
                metrics.annual_return = (final_capital / initial_capital) ** (1 / years) - 1

        # 最大回撤
        max_value = equity_curve[0]
        max_drawdown = 0.0

        for value in equity_curve:
            if value > max_value:
                max_value = value
            drawdown = (max_value - value) / max_value
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        metrics.max_drawdown = max_drawdown

        # 夏普比率（简化版）
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                returns.append(ret)

            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = self._std(returns)

                if std_return > 0:
                    # 假设无风险利率为0
                    metrics.sharpe_ratio = (avg_return * self.annual_days) / (std_return * math.sqrt(self.annual_days))

        # 卡玛比率
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annual_return / metrics.max_drawdown

    def _calculate_china_metrics(
        self,
        metrics: EnhancedMetrics,
        trades: List[TradeData],
        equity_curve: List[float],
        initial_capital: float
    ) -> None:
        """计算A股特有指标"""
        if not trades:
            return

        # 按股票分组计算盈亏
        stock_trades: Dict[str, List[TradeData]] = {}
        for trade in trades:
            if trade.symbol not in stock_trades:
                stock_trades[trade.symbol] = []
            stock_trades[trade.symbol].append(trade)

        # 计算胜率
        wins = 0
        total = 0
        for symbol, symbol_trades in stock_trades.items():
            pnl = self._calculate_stock_pnl(symbol_trades)
            total += 1
            if pnl > 0:
                wins += 1

        metrics.win_rate = wins / total if total > 0 else 0.0

        # 计算盈亏比
        profits = []
        losses = []
        for symbol, symbol_trades in stock_trades.items():
            pnl = self._calculate_stock_pnl(symbol_trades)
            if pnl > 0:
                profits.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))

        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        metrics.profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        # 平均持股天数（简化估算）
        holding_periods = []
        for symbol, symbol_trades in stock_trades.items():
            symbol_trades.sort(key=lambda x: x.datetime or datetime.now())
            buys = [t for t in symbol_trades if t.direction == Direction.LONG]
            sells = [t for t in symbol_trades if t.direction == Direction.SHORT]

            for buy in buys:
                for sell in sells:
                    if sell.datetime and buy.datetime and sell.datetime > buy.datetime:
                        days = (sell.datetime - buy.datetime).days
                        if days > 0:
                            holding_periods.append(days)
                            break

        metrics.avg_holding_days = sum(holding_periods) / len(holding_periods) if holding_periods else 0.0

        # 平均资金使用率
        if equity_curve:
            # 简化：假设平均使用50%资金
            metrics.avg_capital_usage = 0.5

    def _calculate_trade_stats(
        self,
        metrics: EnhancedMetrics,
        trades: List[TradeData]
    ) -> None:
        """计算交易统计"""
        if not trades:
            return

        metrics.total_trades = len(trades)
        metrics.buy_trades = len([t for t in trades if t.direction == Direction.LONG])
        metrics.sell_trades = len([t for t in trades if t.direction == Direction.SHORT])

        # 按股票分组计算连续盈亏
        stock_pnls: Dict[str, float] = {}
        for trade in trades:
            if trade.symbol not in stock_pnls:
                stock_pnls[trade.symbol] = 0.0
            if trade.direction == Direction.SHORT:
                stock_pnls[trade.symbol] += trade.volume * trade.price
            else:
                stock_pnls[trade.symbol] -= trade.volume * trade.price

        # 计算最大连续盈亏
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for pnl in stock_pnls.values():
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0

        metrics.max_consecutive_wins = max_consecutive_wins
        metrics.max_consecutive_losses = max_consecutive_losses

    def _calculate_cost_stats(
        self,
        metrics: EnhancedMetrics,
        trades: List[TradeData]
    ) -> None:
        """计算成本统计"""
        if not trades:
            return

        total_turnover = 0.0
        for trade in trades:
            total_turnover += trade.price * trade.volume

        if total_turnover > 0:
            metrics.cost_rate = metrics.total_cost / total_turnover

        if metrics.total_trades > 0:
            metrics.avg_cost_per_trade = metrics.total_cost / metrics.total_trades

    def _calculate_stock_pnl(self, trades: List[TradeData]) -> float:
        """计算单只股票的盈亏（简化版）"""
        if not trades:
            return 0.0

        # 简化：只考虑卖出时的收益
        buy_value = 0.0
        sell_value = 0.0

        for trade in trades:
            value = trade.price * trade.volume
            if trade.direction == Direction.LONG:
                buy_value += value
            else:
                sell_value += value

        return sell_value - buy_value

    def _calculate_monthly_returns(
        self,
        equity_curve: List[float],
        trading_days: int
    ) -> Dict[str, float]:
        """计算月度收益"""
        # 简化实现
        return {}

    def _std(self, values: List[float]) -> float:
        """计算标准差"""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)


def calculate_default_metrics(
    trades: List[TradeData],
    initial_capital: float = 1_000_000,
    final_capital: float = 1_000_000,
    total_cost: float = 0.0
) -> EnhancedMetrics:
    """便捷函数：计算默认指标

    Args:
        trades: 成交列表
        initial_capital: 初始资金
        final_capital: 最终资金
        total_cost: 总交易成本

    Returns:
        EnhancedMetrics: 增强指标
    """
    calculator = MetricsCalculator()
    equity_curve = [initial_capital, final_capital]

    return calculator.calculate(
        trades=trades,
        equity_curve=equity_curve,
        trading_days=240,
        initial_capital=initial_capital,
        final_capital=final_capital,
        total_cost=total_cost
    )
