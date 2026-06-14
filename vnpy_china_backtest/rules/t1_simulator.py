"""
T+1规则模拟器

A股T+1规则：
- 当日买入的股票，次日才能卖出
- 当日卖出股票的资金，可以立即使用
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class BuyRecord:
    """买入记录"""
    symbol: str
    volume: int                  # 买入数量
    price: float                 # 买入价格
    buy_date: date              # 买入日期
    sold_volume: int = 0        # 已卖出数量


@dataclass
class PositionRecord:
    """持仓记录"""
    symbol: str
    volume: int                 # 总持仓
    available: int              # 可卖出数量
    frozen: int                 # 冻结数量（当日买入）
    avg_price: float            # 平均成本


class T1Simulator:
    """T+1规则模拟器"""

    def __init__(self):
        # 买入记录: {symbol: [BuyRecord, ...]}
        self._buy_records: Dict[str, List[BuyRecord]] = {}

        # 当前持仓: {symbol: PositionRecord}
        self._positions: Dict[str, PositionRecord] = {}

        # 已实现盈亏累计 {symbol: pnl}，由 _process_sell 在 FIFO 匹配时累加
        self._realized_pnl: Dict[str, float] = {}

    def record_buy(
        self,
        symbol: str,
        volume: int,
        price: float,
        trade_date: date
    ) -> None:
        """记录买入

        Args:
            symbol: 股票代码
            volume: 买入数量
            price: 买入价格
            trade_date: 交易日期
        """
        # 记录买入
        if symbol not in self._buy_records:
            self._buy_records[symbol] = []

        self._buy_records[symbol].append(BuyRecord(
            symbol=symbol,
            volume=volume,
            price=price,
            buy_date=trade_date
        ))

        # 更新持仓
        self._update_position(symbol, volume, price, is_buy=True)

    def record_sell(
        self,
        symbol: str,
        volume: int,
        price: float,
        trade_date: date
    ) -> Tuple[bool, str, int]:
        """记录卖出

        Args:
            symbol: 股票代码
            volume: 卖出数量
            price: 卖出价格
            trade_date: 交易日期

        Returns:
            Tuple[bool, str, int]: (是否成功, 原因, 实际卖出数量)
        """
        # 检查可卖出数量
        sellable = self.get_sellable_volume(symbol, trade_date)

        if sellable == 0:
            return False, f"T+1限制：{symbol}当前无可卖出股票", 0

        if volume > sellable:
            # 尝试卖出超过可卖出数量的部分
            return False, f"卖出数量{volume}超过可卖出数量{sellable}", 0

        # 记录卖出（使用FIFO原则）—— 传入卖出价供盈亏累加
        self._process_sell(symbol, volume, trade_date, sell_price=price)

        # 更新持仓（传入回测日期以正确计算 T+1 冻结量）
        self._update_position(symbol, volume, price, is_buy=False, trade_date=trade_date)

        return True, "卖出成功", volume

    def get_sellable_volume(self, symbol: str, trade_date: date) -> int:
        """获取可卖出数量

        Args:
            symbol: 股票代码
            trade_date: 当前日期

        Returns:
            int: 可卖出数量（T+1：当日之前买入的股票）
        """
        if symbol not in self._buy_records:
            return 0

        total_available = 0
        for record in self._buy_records[symbol]:
            # T+1: 必须是前一天及之前买入的
            if record.buy_date < trade_date:
                available = record.volume - record.sold_volume
                total_available += available

        return total_available

    def get_position(self, symbol: str) -> Optional[PositionRecord]:
        """获取持仓

        Args:
            symbol: 股票代码

        Returns:
            Optional[PositionRecord]: 持仓记录
        """
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, PositionRecord]:
        """获取所有持仓"""
        return self._positions.copy()

    def get_total_position_value(self, current_prices: Dict[str, float]) -> float:
        """计算总持仓市值

        Args:
            current_prices: 当前价格字典

        Returns:
            float: 总持仓市值
        """
        total = 0.0
        for symbol, pos in self._positions.items():
            if pos.volume > 0 and symbol in current_prices:
                total += pos.volume * current_prices[symbol]
        return total

    def get_total_cost(self, symbol: str) -> float:
        """获取持仓总成本

        Args:
            symbol: 股票代码

        Returns:
            float: 持仓总成本
        """
        if symbol not in self._buy_records:
            return 0.0

        total_cost = 0.0
        for record in self._buy_records[symbol]:
            remaining = record.volume - record.sold_volume
            if remaining > 0:
                total_cost += remaining * record.price
        return total_cost

    def get_realized_pnl(self, symbol: str) -> float:
        """获取已实现盈亏（由 _process_sell 在 FIFO 匹配时累加）

        Args:
            symbol: 股票代码

        Returns:
            float: 已实现盈亏
        """
        return self._realized_pnl.get(symbol, 0.0)

    def _process_sell(self, symbol: str, volume: int, trade_date: date, sell_price: float) -> None:
        """处理卖出（FIFO原则），同时累加已实现盈亏"""
        if symbol not in self._buy_records:
            return

        self._realized_pnl.setdefault(symbol, 0.0)
        remaining = volume
        for record in self._buy_records[symbol]:
            if remaining <= 0:
                break

            # 必须是T+1的持仓
            if record.buy_date >= trade_date:
                continue

            available = record.volume - record.sold_volume
            if available > 0:
                sold = min(remaining, available)
                record.sold_volume += sold
                # 在同一次 FIFO 匹配中累加已实现盈亏（避免二次匹配）
                self._realized_pnl[symbol] += sold * (sell_price - record.price)
                remaining -= sold

    def _update_position(
        self,
        symbol: str,
        volume: int,
        price: float,
        is_buy: bool,
        trade_date: Optional[date] = None
    ) -> None:
        """更新持仓

        Args:
            trade_date: 回测交易日期，卖出时用于判定 T+1 冻结量；
                        为空（如非回测直接调用）时回退系统日期
        """
        if symbol not in self._positions:
            self._positions[symbol] = PositionRecord(
                symbol=symbol,
                volume=0,
                available=0,
                frozen=0,
                avg_price=0.0
            )

        pos = self._positions[symbol]

        if is_buy:
            # 买入：增加持仓
            old_volume = pos.volume
            pos.volume += volume
            # 新买入的股票冻结（T+1）
            pos.frozen += volume
            # 更新平均成本
            if old_volume > 0:
                pos.avg_price = (pos.avg_price * old_volume + price * volume) / pos.volume
            else:
                pos.avg_price = price
        else:
            # 卖出：减少持仓
            pos.volume -= volume
            # 重新计算冻结量：用回测日期判断当日买入（T+1 冻结），
            # 替代此前的 date.today()（系统日期会污染回测判定）
            today = trade_date or date.today()
            frozen_after_sell = 0
            for rec in self._buy_records.get(symbol, []):
                if rec.buy_date >= today:
                    frozen_after_sell += (rec.volume - rec.sold_volume)
            pos.frozen = frozen_after_sell

            if pos.volume == 0:
                pos.avg_price = 0.0

        # 更新可用数量
        pos.available = pos.volume - pos.frozen

    def reset(self) -> None:
        """重置模拟器"""
        self._buy_records.clear()
        self._positions.clear()
        self._realized_pnl.clear()

    def get_buy_records(self, symbol: str) -> List[BuyRecord]:
        """获取买入记录

        Args:
            symbol: 股票代码

        Returns:
            List[BuyRecord]: 买入记录列表
        """
        return self._buy_records.get(symbol, []).copy()
