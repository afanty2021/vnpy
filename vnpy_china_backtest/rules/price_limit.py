"""
涨跌停处理

功能：
1. 计算涨跌停价格
2. 判断是否涨停/跌停
3. 处理涨停无法买入、跌停无法卖出
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple
from vnpy.trader.constant import Direction


@dataclass
class LimitPrices:
    """涨跌停价格"""
    symbol: str
    trade_date: date
    prev_close: float          # 昨日收盘价
    limit_up: float            # 涨停价
    limit_down: float          # 跌停价
    is_limit_up: bool = False  # 是否涨停
    is_limit_down: bool = False  # 是否跌停


@dataclass
class OrderCheckResult:
    """订单检查结果"""
    can_execute: bool           # 是否可执行
    reason: str                 # 原因
    adjusted_price: float       # 调整后的价格
    fill_ratio: float = 1.0    # 成交比例


class PriceLimitEngine:
    """涨跌停引擎"""

    # 涨跌停比例配置
    LIMIT_RATIOS = {
        "main": 0.10,      # 主板: 10%
        "chinext": 0.20,  # 创业板: 20%
        "star": 0.20,     # 科创板: 20%
        "bse": 0.30,      # 北交所: 30%
        "st": 0.05,       # ST: 5%
    }

    def __init__(self, data_service=None):
        self.data_service = data_service
        self._limit_cache = {}  # 缓存涨跌停价格
        self._prev_closes = {}  # 缓存昨日收盘价

    def set_prev_close(self, symbol: str, trade_date: date, prev_close: float) -> None:
        """设置昨日收盘价"""
        self._prev_closes[(symbol, trade_date)] = prev_close

    def get_prev_close(self, symbol: str, trade_date: date) -> Optional[float]:
        """获取昨日收盘价"""
        return self._prev_closes.get((symbol, trade_date))

    def get_limit_prices(
        self,
        symbol: str,
        trade_date: date,
        prev_close: float,
        current_price: Optional[float] = None
    ) -> LimitPrices:
        """获取涨跌停价格

        Args:
            symbol: 股票代码
            trade_date: 交易日期
            prev_close: 昨日收盘价
            current_price: 当前价格（用于判断是否涨跌停）

        Returns:
            LimitPrices: 涨跌停价格
        """
        # 判断股票类型
        market_type = self._get_market_type(symbol)

        # 获取涨跌停比例
        ratio = self.LIMIT_RATIOS.get(market_type, 0.10)

        # 计算涨跌停价
        limit_up = round(prev_close * (1 + ratio), 2)
        limit_down = round(prev_close * (1 - ratio), 2)

        # 判断是否涨停/跌停（根据当前价格）
        is_limit_up = False
        is_limit_down = False

        if current_price is not None:
            # 如果当前价格达到涨停价
            if current_price >= limit_up:
                is_limit_up = True
            # 如果当前价格达到跌停价
            elif current_price <= limit_down:
                is_limit_down = True

        return LimitPrices(
            symbol=symbol,
            trade_date=trade_date,
            prev_close=prev_close,
            limit_up=limit_up,
            limit_down=limit_down,
            is_limit_up=is_limit_up,
            is_limit_down=is_limit_down
        )

    def check_order(
        self,
        symbol: str,
        direction: Direction,
        price: float,
        volume: int,
        limit_prices: LimitPrices,
        allow_limit_up: bool = False,
        allow_limit_down: bool = False
    ) -> OrderCheckResult:
        """检查订单是否可执行

        Args:
            symbol: 股票代码
            direction: 交易方向
            price: 委托价格
            volume: 委托数量
            limit_prices: 涨跌停价格
            allow_limit_up: 是否允许涨停买入
            allow_limit_down: 是否允许跌停卖出

        Returns:
            OrderCheckResult: 检查结果
        """
        # 涨停时无法买入
        if direction == Direction.LONG:
            if limit_prices.is_limit_up and not allow_limit_up:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"涨停板无法买入",
                    adjusted_price=limit_prices.limit_up,
                    fill_ratio=0.0
                )

            # 买入价格不能超过涨停价
            if price > limit_prices.limit_up:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"买入价格{price}超过涨停价{limit_prices.limit_up}",
                    adjusted_price=limit_prices.limit_up,
                    fill_ratio=0.0
                )

        # 跌停时无法卖出
        else:
            if limit_prices.is_limit_down and not allow_limit_down:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"跌停板无法卖出",
                    adjusted_price=limit_prices.limit_down,
                    fill_ratio=0.0
                )

            # 卖出价格不能低于跌停价
            if price < limit_prices.limit_down:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"卖出价格{price}低于跌停价{limit_prices.limit_down}",
                    adjusted_price=limit_prices.limit_down,
                    fill_ratio=0.0
                )

        return OrderCheckResult(
            can_execute=True,
            reason="可执行",
            adjusted_price=price,
            fill_ratio=1.0
        )

    def _get_market_type(self, symbol: str) -> str:
        """判断市场类型

        Args:
            symbol: 股票代码

        Returns:
            str: 市场类型 ("main", "chinext", "star", "bse", "st")
        """
        # 移除可能的前缀
        clean_symbol = symbol.replace("SH.", "").replace("SZ.", "")

        # 判断ST
        if clean_symbol.startswith("ST") or "ST" in clean_symbol:
            return "st"

        # 判断科创板 (688开头)
        if clean_symbol.startswith("688"):
            return "star"

        # 判断北交所 (8或4开头)
        if clean_symbol.startswith("8") or clean_symbol.startswith("4"):
            return "bse"

        # 判断创业板 (300开头)
        if clean_symbol.startswith("300"):
            return "chinext"

        # 主板默认
        return "main"


class PriceLimitHandler:
    """涨跌停处理器（简化版）"""

    def __init__(self, price_limit_engine: Optional[PriceLimitEngine] = None):
        self.engine = price_limit_engine or PriceLimitEngine()

    def set_prev_close(self, symbol: str, trade_date: date, prev_close: float) -> None:
        """设置昨日收盘价"""
        self.engine.set_prev_close(symbol, trade_date, prev_close)

    def process_order(
        self,
        symbol: str,
        direction: Direction,
        price: float,
        volume: int,
        trade_date: date,
        prev_close: float,
        current_price: Optional[float] = None,
        allow_limit_up: bool = False,
        allow_limit_down: bool = False
    ) -> Tuple[bool, str, float, int]:
        """处理订单

        Args:
            symbol: 股票代码
            direction: 交易方向
            price: 委托价格
            volume: 委托数量
            trade_date: 交易日期
            prev_close: 昨日收盘价
            current_price: 当前价格（可选）
            allow_limit_up: 是否允许涨停买入
            allow_limit_down: 是否允许跌停卖出

        Returns:
            Tuple[bool, str, float, int]: (是否成交, 原因, 成交价格, 成交数量)
        """
        limit_prices = self.engine.get_limit_prices(
            symbol, trade_date, prev_close, current_price
        )
        result = self.engine.check_order(
            symbol, direction, price, volume, limit_prices,
            allow_limit_up, allow_limit_down
        )

        if not result.can_execute:
            return False, result.reason, price, 0

        # 部分成交处理（简化：全部成交或全部不成交）
        return True, "成交", result.adjusted_price, int(volume * result.fill_ratio)

    def is_limit_up(self, symbol: str, trade_date: date, prev_close: float, current_price: float) -> bool:
        """判断是否涨停"""
        limit_prices = self.engine.get_limit_prices(symbol, trade_date, prev_close, current_price)
        return limit_prices.is_limit_up

    def is_limit_down(self, symbol: str, trade_date: date, prev_close: float, current_price: float) -> bool:
        """判断是否跌停"""
        limit_prices = self.engine.get_limit_prices(symbol, trade_date, prev_close, current_price)
        return limit_prices.is_limit_down
