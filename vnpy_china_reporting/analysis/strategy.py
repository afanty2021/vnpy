"""
策略分析器模块

提供策略表现分析、胜率计算、盈亏比分析等功能。
"""

from typing import List, Dict
from collections import defaultdict
from datetime import date, datetime
from ..core.models import TradeRecord


class StrategyAnalyzer:
    """
    策略分析器

    分析交易策略的表现，包括胜率、盈亏比等。
    """

    def _realized_pnls(self, trades: List[TradeRecord]) -> List[float]:
        """FIFO 配对买卖，返回每笔平仓的实现盈亏（卖出金额 - 对应买入成本）

        未平仓的买入不计入；卖出成交量按 FIFO 抵扣买入成本，部分平仓按
        实际配对数量计算盈亏。

        Args:
            trades: 交易记录

        Returns:
            实现盈亏列表（每笔有效平仓一项）
        """
        symbol_trades: Dict[str, List[TradeRecord]] = defaultdict(list)
        for trade in trades:
            symbol_trades[trade.symbol].append(trade)

        pnls: List[float] = []
        for symbol_trade_list in symbol_trades.values():
            symbol_trade_list.sort(key=lambda t: t.timestamp)
            buy_queue: List[List[float]] = []  # [price, remaining_volume]

            for trade in symbol_trade_list:
                direction = trade.direction.lower() if trade.direction else ""
                if direction == "buy":
                    buy_queue.append([trade.price, trade.volume])
                elif direction == "sell":
                    remaining = trade.volume
                    cost = 0.0
                    while remaining > 0 and buy_queue:
                        buy = buy_queue[0]
                        matched = min(buy[1], remaining)
                        cost += buy[0] * matched
                        buy[1] -= matched
                        remaining -= matched
                        if buy[1] <= 0:
                            buy_queue.pop(0)
                    matched_volume = trade.volume - remaining
                    if matched_volume > 0:
                        pnls.append(trade.price * matched_volume - cost)
        return pnls

    def calculate_win_rate(
        self,
        trades: List[TradeRecord]
    ) -> float:
        """计算胜率（基于 FIFO 配对的实现盈亏）

        Args:
            trades: 交易列表

        Returns:
            胜率（盈利平仓数 / 总平仓数）
        """
        pnls = self._realized_pnls(trades)
        if not pnls:
            return 0.0

        wins = sum(1 for p in pnls if p > 0)
        return wins / len(pnls)

    def calculate_profit_loss_ratio(
        self,
        trades: List[TradeRecord]
    ) -> float:
        """计算盈亏比（平均盈利 / 平均亏损，基于实现盈亏）

        Args:
            trades: 交易列表

        Returns:
            盈亏比
        """
        pnls = self._realized_pnls(trades)
        profits = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]

        avg_profit = sum(profits) / len(profits) if profits else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0

        if avg_loss == 0:
            return 0.0

        return avg_profit / avg_loss

    def calculate_summary(
        self,
        trades: List[TradeRecord]
    ) -> Dict:
        """计算策略摘要（基于 FIFO 配对的实现盈亏）

        Args:
            trades: 交易列表

        Returns:
            策略摘要
        """
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_loss_ratio": 0.0,
                "total_pnl": 0.0,
                "total_commission": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
            }

        pnls = self._realized_pnls(trades)
        profits = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]

        return {
            "total_trades": len(trades),
            "win_rate": self.calculate_win_rate(trades),
            "profit_loss_ratio": self.calculate_profit_loss_ratio(trades),
            "total_pnl": sum(pnls),
            "total_commission": sum(t.commission for t in trades),
            "winning_trades": len(profits),
            "losing_trades": len(losses),
            "avg_profit": sum(profits) / len(profits) if profits else 0.0,
            "avg_loss": sum(losses) / len(losses) if losses else 0.0,
        }

    def analyze_performance(
        self,
        trades: List[TradeRecord]
    ) -> Dict:
        """
        分析策略表现

        Args:
            trades: 交易记录列表

        Returns:
            策略表现字典
        """
        if not trades:
            return {
                "total_trades": 0,
                "paired_trades": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_return": 0.0
            }

        # 计算每笔交易的收益率
        paired_returns = self._pair_trades(trades)

        if not paired_returns:
            return {
                "total_trades": len(trades),
                "paired_trades": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_return": 0.0
            }

        # 胜率
        winning_trades = [r for r in paired_returns if r > 0]
        win_rate = len(winning_trades) / len(paired_returns)

        # 平均收益率
        avg_return = sum(paired_returns) / len(paired_returns)

        # 总收益率
        total_return = sum(paired_returns)

        return {
            "total_trades": len(trades),
            "paired_trades": len(paired_returns),
            "win_rate": win_rate,
            "avg_return": avg_return,
            "total_return": total_return,
            "best_return": max(paired_returns),
            "worst_return": min(paired_returns)
        }

    def _pair_trades(
        self,
        trades: List[TradeRecord]
    ) -> List[float]:
        """
        配对买卖交易，计算收益率

        Args:
            trades: 交易记录

        Returns:
            收益率列表
        """
        # 按股票分组
        symbol_trades: Dict[str, List[TradeRecord]] = defaultdict(list)
        for trade in trades:
            symbol_trades[trade.symbol].append(trade)

        returns: List[float] = []

        # 配对买卖
        for symbol, symbol_trade_list in symbol_trades.items():
            # 按时间排序
            symbol_trade_list.sort(key=lambda t: t.timestamp)

            buy_queue: List[TradeRecord] = []

            for trade in symbol_trade_list:
                if trade.direction.lower() == "buy":
                    buy_queue.append(trade)
                elif trade.direction.lower() == "sell":
                    if buy_queue:
                        buy_trade = buy_queue.pop(0)
                        # 计算收益率
                        cost = buy_trade.price * buy_trade.volume
                        revenue = trade.price * trade.volume
                        ret = (revenue - cost) / cost if cost > 0 else 0
                        returns.append(ret)

        return returns

    def analyze_by_month(
        self,
        trades: List[TradeRecord]
    ) -> Dict[str, Dict]:
        """
        按月分析策略表现

        Args:
            trades: 交易记录

        Returns:
            {月份: {统计数据}}
        """
        monthly_trades: Dict[str, List[TradeRecord]] = defaultdict(list)

        for trade in trades:
            month_key = trade.timestamp.strftime("%Y-%m")
            monthly_trades[month_key].append(trade)

        monthly_stats: Dict[str, Dict] = {}
        for month, month_trades in monthly_trades.items():
            monthly_stats[month] = self.analyze_performance(month_trades)

        return monthly_stats

    def analyze_by_symbol(
        self,
        trades: List[TradeRecord]
    ) -> Dict[str, Dict]:
        """
        按股票分析策略表现

        Args:
            trades: 交易记录

        Returns:
            {股票代码: {统计数据}}
        """
        symbol_trades: Dict[str, List[TradeRecord]] = defaultdict(list)

        for trade in trades:
            symbol_trades[trade.symbol].append(trade)

        symbol_stats: Dict[str, Dict] = {}
        for symbol, symbol_trade_list in symbol_trades.items():
            symbol_stats[symbol] = self.analyze_performance(symbol_trade_list)

        return symbol_stats

    def compare_strategies(
        self,
        strategies: Dict[str, List[TradeRecord]]
    ) -> Dict:
        """
        对比多个策略

        Args:
            strategies: {策略名: 交易记录}

        Returns:
            策略对比结果
        """
        comparison: Dict = {}

        for name, trades in strategies.items():
            comparison[name] = self.analyze_performance(trades)

        return comparison

    def get_trading_summary(
        self,
        trades: List[TradeRecord]
    ) -> Dict:
        """
        获取交易汇总

        Args:
            trades: 交易记录

        Returns:
            交易汇总字典
        """
        if not trades:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_volume": 0,
                "total_amount": 0.0,
                "total_commission": 0.0
            }

        buy_trades = [t for t in trades if t.direction.lower() == "buy"]
        sell_trades = [t for t in trades if t.direction.lower() == "sell"]

        return {
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_volume": sum(t.volume for t in trades),
            "total_amount": sum(t.amount for t in trades),
            "total_commission": sum(t.commission for t in trades),
            "avg_commission_per_trade": sum(t.commission for t in trades) / len(trades)
        }
