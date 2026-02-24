"""
报表生成器基类

定义报表生成的基本接口和通用方法。
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Dict, Optional, Any

from ..core.models import ReportData, TradeRecord, PositionRecord, AccountData, PositionSide
from ..core.enums import ReportType


class BaseReportGenerator(ABC):
    """
    报表生成器基类

    定义报表生成的基本接口和通用方法。
    所有报表生成器应继承此类，实现统一的接口。
    """

    def __init__(self, main_engine: Optional[Any] = None) -> None:
        """
        初始化报表生成器

        Args:
            main_engine: 主引擎实例，用于获取交易数据
        """
        self.main_engine: Optional[Any] = main_engine
        self.data_cache: Dict[str, Any] = {}

    @abstractmethod
    def generate_daily(self, report_date: date) -> ReportData:
        """
        生成日报数据

        Args:
            report_date: 报表日期

        Returns:
            报表数据对象
        """
        pass

    def get_trades(self, start_date: date, end_date: date) -> List[TradeRecord]:
        """
        获取指定日期范围的交易记录

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易记录列表
        """
        # 从主引擎或缓存获取交易数据
        if not self.main_engine:
            return self._get_mock_trades(start_date, end_date)

        try:
            # 尝试从主引擎获取数据
            trades = self.main_engine.get_trades()
            result = []
            for trade in trades:
                trade_date = trade.timestamp.date() if hasattr(trade, 'timestamp') else None
                if trade_date and start_date <= trade_date <= end_date:
                    result.append(TradeRecord(
                        trade_id=str(id(trade)),
                        symbol=trade.symbol,
                        direction=trade.direction.value if hasattr(trade.direction, 'value') else trade.direction,
                        volume=trade.volume,
                        price=trade.price,
                        amount=trade.volume * trade.price,
                        commission=getattr(trade, 'commission', 0.0),
                        timestamp=trade.timestamp if hasattr(trade, 'timestamp') else datetime.now()
                    ))
            return result
        except Exception:
            return self._get_mock_trades(start_date, end_date)

    def _get_mock_trades(self, start_date: date, end_date: date) -> List[TradeRecord]:
        """
        获取模拟交易数据（用于测试）

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            空交易列表
        """
        return []

    def get_positions(self) -> List[PositionRecord]:
        """
        获取当前持仓

        Returns:
            持仓记录列表
        """
        # 从主引擎或缓存获取持仓数据
        if not self.main_engine:
            return self._get_mock_positions()

        try:
            positions = self.main_engine.get_positions()
            result = []
            for pos in positions:
                if pos.volume == 0:
                    continue

                market_value = pos.volume * pos.price
                pnl = (pos.price - pos.avg_price) * pos.volume
                pnl_ratio = pnl / (pos.avg_price * pos.volume) if pos.avg_price > 0 else 0.0

                result.append(PositionRecord(
                    symbol=pos.symbol,
                    name=getattr(pos, 'name', ''),
                    side=pos.side if hasattr(pos, 'side') else PositionSide.LONG,
                    volume=pos.volume,
                    avg_cost=pos.avg_price,
                    current_price=pos.price,
                    market_value=market_value,
                    unrealized_pnl=pnl,
                    unrealized_pnl_ratio=pnl_ratio
                ))
            return result
        except Exception:
            return self._get_mock_positions()

    def _get_mock_positions(self) -> List[PositionRecord]:
        """
        获取模拟持仓数据（用于测试）

        Returns:
            空持仓列表
        """
        return []

    def get_account(self) -> AccountData:
        """
        获取账户数据

        Returns:
            账户数据对象
        """
        # 从主引擎或缓存获取账户数据
        if not self.main_engine:
            return self._get_mock_account()

        try:
            account = self.main_engine.get_account()
            return AccountData(
                total_equity=getattr(account, 'balance', 1000000.0),
                available_cash=getattr(account, 'available', 500000.0),
                market_value=getattr(account, 'position_value', 500000.0),
                total_pnl=getattr(account, 'pnl', 0.0),
                total_pnl_ratio=getattr(account, 'pnl_ratio', 0.0),
                commission=getattr(account, 'commission', 0.0),
                timestamp=datetime.now()
            )
        except Exception:
            return self._get_mock_account()

    def _get_mock_account(self) -> AccountData:
        """
        获取模拟账户数据（用于测试）

        Returns:
            默认账户数据
        """
        return AccountData(
            total_equity=1000000.0,
            available_cash=500000.0,
            market_value=500000.0,
            total_pnl=0.0,
            total_pnl_ratio=0.0,
            commission=0.0,
            timestamp=datetime.now()
        )

    def calculate_daily_pnl(self, trades: List[TradeRecord]) -> float:
        """
        计算当日盈亏

        Args:
            trades: 交易记录列表

        Returns:
            当日盈亏金额
        """
        buy_amount = sum(t.amount for t in trades if t.direction == "buy")
        sell_amount = sum(t.amount for t in trades if t.direction == "sell")
        commission = sum(t.commission for t in trades)

        return sell_amount - buy_amount - commission

    def calculate_position_weights(
        self,
        positions: List[PositionRecord],
        total_value: float
    ) -> None:
        """
        计算持仓权重

        Args:
            positions: 持仓列表
            total_value: 总市值
        """
        if total_value == 0:
            return

        for pos in positions:
            pos.unrealized_pnl_ratio = pos.market_value / total_value

    def clear_cache(self) -> None:
        """清空数据缓存"""
        self.data_cache.clear()
