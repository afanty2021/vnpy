"""
A股交易规则适配器模块

本模块提供了针对A股市场交易规则的适配器实现：
- T1RuleAdapter: T+1交易规则适配器（当日买入，次日才能卖出）
- PriceLimitAdapter: 涨跌停规则适配器

这些适配器用于确保策略符合A股市场的交易规则。
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta


class T1RuleAdapter:
    """T+1交易规则适配器

    A股市场实行T+1交易制度，即当日买入的股票只能在次日（含）之后卖出。
    本适配器用于跟踪和管理持仓，确保卖出操作符合T+1规则。

    Attributes:
        last_buy_date: 记录每只股票最后买入日期的字典
        holdings: 记录每只股票当前持仓数量的字典
    """

    def __init__(self):
        """初始化T+1规则适配器"""
        self.last_buy_date: Dict[str, datetime] = {}
        self.holdings: Dict[str, int] = {}

    def can_sell(self, symbol: str, current_date: datetime) -> bool:
        """检查是否可以卖出指定股票

        根据T+1规则，只有在买入后至少一个交易日才能卖出。

        Args:
            symbol: 股票代码（如 '000001.SZ'）
            current_date: 当前日期/时间

        Returns:
            如果可以卖出返回True，否则返回False
        """
        # 如果没有该股票的买入记录，则可以卖出
        if symbol not in self.last_buy_date:
            return True

        # 检查是否满足T+1条件
        buy_date = self.last_buy_date[symbol]
        days_diff = (current_date.date() - buy_date.date()).days

        # 至少需要间隔1个交易日
        return days_diff >= 1

    def can_sell_volume(self, symbol: str, current_date: datetime, volume: int) -> int:
        """计算可以卖出的数量

        根据T+1规则，计算在指定日期可以卖出的最大数量。

        Args:
            symbol: 股票代码
            current_date: 当前日期
            volume: 尝试卖出的数量

        Returns:
            可以卖出的实际数量
        """
        if not self.can_sell(symbol, current_date):
            return 0
        return min(volume, self.get_holdable_volume(symbol, current_date))

    def record_buy(self, symbol: str, date: datetime, volume: int) -> None:
        """记录买入操作

        Args:
            symbol: 股票代码
            date: 买入日期
            volume: 买入数量
        """
        # 更新最后买入日期
        self.last_buy_date[symbol] = date
        # 更新持仓数量
        self.holdings[symbol] = self.holdings.get(symbol, 0) + volume

    def record_sell(self, symbol: str, volume: int) -> int:
        """记录卖出操作

        Args:
            symbol: 股票代码
            volume: 卖出数量

        Returns:
            实际卖出的数量
        """
        if symbol not in self.holdings:
            return 0

        actual_sell = min(volume, self.holdings[symbol])
        self.holdings[symbol] -= actual_sell

        # 如果持仓为0，移除记录
        if self.holdings[symbol] <= 0:
            del self.holdings[symbol]

        return actual_sell

    def get_holdable_volume(self, symbol: str, current_date: Optional[datetime] = None) -> int:
        """获取可卖出数量

        返回当前可以卖出的持仓数量（受T+1限制的数量）。

        Args:
            symbol: 股票代码
            current_date: 当前日期，如果为None则使用系统当前时间

        Returns:
            可以卖出的数量
        """
        # 如果没有持仓，返回0
        if symbol not in self.holdings:
            return 0

        # 如果没有买入记录，返回全部持仓
        if symbol not in self.last_buy_date:
            return self.holdings[symbol]

        # 检查是否满足T+1条件
        if current_date is None:
            current_date = datetime.now()

        if self.can_sell(symbol, current_date):
            return self.holdings[symbol]

        return 0

    def get_all_holdings(self) -> Dict[str, int]:
        """获取所有持仓

        Returns:
            股票代码到持仓数量的字典
        """
        return self.holdings.copy()

    def get_buy_date(self, symbol: str) -> Optional[datetime]:
        """获取指定股票的买入日期

        Args:
            symbol: 股票代码

        Returns:
            买入日期，如果不存在则返回None
        """
        return self.last_buy_date.get(symbol)

    def can_sell_all(self, symbols: List[str], current_date: datetime) -> Dict[str, bool]:
        """批量检查是否可以卖出

        Args:
            symbols: 股票代码列表
            current_date: 当前日期

        Returns:
            股票代码到是否可卖出的字典
        """
        return {symbol: self.can_sell(symbol, current_date) for symbol in symbols}

    def reset(self) -> None:
        """重置所有记录"""
        self.last_buy_date.clear()
        self.holdings.clear()

    def __repr__(self) -> str:
        return f"T1RuleAdapter(holdings={len(self.holdings)}, tracking={len(self.last_buy_date)})"


class PriceLimitAdapter:
    """涨跌停规则适配器

    A股市场有涨跌停板制度：
    - 普通股票：涨跌幅为10%
    - ST股票：涨跌幅为5%
    - 科创板/创业板：涨跌幅为20%

    本适配器用于跟踪和管理涨跌停状态，防止在涨停时买入或跌停时卖出。

    Attributes:
        limit_up_ratio: 涨停涨幅比例（默认为10%）
        limit_down_ratio: 跌停跌幅比例（默认为10%）
        limit_up_stocks: 当前涨停的股票集合
        limit_down_stocks: 当前跌停的股票集合
    """

    # 股票板块类型
    class StockType:
        NORMAL = "normal"  # 普通股票（10%）
        ST = "st"  # ST股票（5%）
        STAR_MARKET = "star_market"  # 科创板（20%）
        CHINEXT = "chinext"  # 创业板（20%）

    def __init__(
        self,
        limit_up_ratio: float = 0.10,
        limit_down_ratio: float = 0.10
    ):
        """初始化涨跌停适配器

        Args:
            limit_up_ratio: 涨停涨幅比例，默认10%
            limit_down_ratio: 跌停跌幅比例，默认10%
        """
        self.limit_up_ratio: float = limit_up_ratio
        self.limit_down_ratio: float = limit_down_ratio

        self.limit_up_stocks: set = set()
        self.limit_down_stocks: set = set()

        # 股票板块类型映射
        self.stock_type_map: Dict[str, str] = {}

    def set_stock_type(self, symbol: str, stock_type: str) -> None:
        """设置股票板块类型

        Args:
            symbol: 股票代码
            stock_type: 板块类型，使用StockType常量
        """
        self.stock_type_map[symbol] = stock_type

    def _get_limit_ratios(self, symbol: str) -> tuple:
        """获取股票的涨跌停比例

        Args:
            symbol: 股票代码

        Returns:
            (涨停比例, 跌停比例) 元组
        """
        stock_type = self.stock_type_map.get(symbol, self.StockType.NORMAL)

        if stock_type == self.StockType.ST:
            return (0.05, 0.05)
        elif stock_type in (self.StockType.STAR_MARKET, self.StockType.CHINEXT):
            return (0.20, 0.20)
        else:
            return (self.limit_up_ratio, self.limit_down_ratio)

    def is_limit_up(self, symbol: str) -> bool:
        """检查是否涨停

        Args:
            symbol: 股票代码

        Returns:
            如果涨停返回True
        """
        return symbol in self.limit_up_stocks

    def is_limit_down(self, symbol: str) -> bool:
        """检查是否跌停

        Args:
            symbol: 股票代码

        Returns:
            如果跌停返回True
        """
        return symbol in self.limit_down_stocks

    def is_limited(self, symbol: str) -> bool:
        """检查是否涨跌停

        Args:
            symbol: 股票代码

        Returns:
            如果涨跌停返回True
        """
        return self.is_limit_up(symbol) or self.is_limit_down(symbol)

    def can_buy(self, symbol: str, current_price: float, target_price: float) -> bool:
        """检查是否可以买入

        涨停时不能买入（因为卖单极少，难以成交）。

        Args:
            symbol: 股票代码
            current_price: 当前价格
            target_price: 目标买入价格

        Returns:
            如果可以买入返回True
        """
        # 涨停时不能买入
        if self.is_limit_up(symbol):
            return False

        # 目标价格不能超过涨停价
        limit_up_price = current_price * (1 + self._get_limit_ratios(symbol)[0])
        return target_price <= limit_up_price

    def can_sell(self, symbol: str, current_price: float, target_price: float) -> bool:
        """检查是否可以卖出

        跌停时不能卖出（因为买单极少，难以成交）。

        Args:
            symbol: 股票代码
            current_price: 当前价格
            target_price: 目标卖出价格

        Returns:
            如果可以卖出返回True
        """
        # 跌停时不能卖出
        if self.is_limit_down(symbol):
            return False

        # 目标价格不能低于跌停价
        limit_down_price = current_price * (1 - self._get_limit_ratios(symbol)[1])
        return target_price >= limit_down_price

    def update_limit_status(
        self,
        symbol: str,
        is_limit_up: bool,
        is_limit_down: bool = False
    ) -> None:
        """更新涨跌停状态

        Args:
            symbol: 股票代码
            is_limit_up: 是否涨停
            is_limit_down: 是否跌停
        """
        if is_limit_up:
            self.limit_up_stocks.add(symbol)
            self.limit_down_stocks.discard(symbol)
        elif is_limit_down:
            self.limit_down_stocks.add(symbol)
            self.limit_up_stocks.discard(symbol)
        else:
            # 解除涨跌停状态
            self.limit_up_stocks.discard(symbol)
            self.limit_down_stocks.discard(symbol)

    def update_limit_status_by_price(
        self,
        symbol: str,
        current_price: float,
        previous_close: float
    ) -> bool:
        """根据价格更新涨跌停状态

        Args:
            symbol: 股票代码
            current_price: 当前价格
            previous_close: 前一交易日收盘价

        Returns:
            是否发生涨跌停（状态发生变化）
        """
        limit_up_ratio, limit_down_ratio = self._get_limit_ratios(symbol)

        limit_up_price = previous_close * (1 + limit_up_ratio)
        limit_down_price = previous_close * (1 - limit_down_ratio)

        was_limited = self.is_limited(symbol)

        if abs(current_price - limit_up_price) < 0.01:
            # 涨停
            self.update_limit_status(symbol, is_limit_up=True, is_limit_down=False)
        elif abs(current_price - limit_down_price) < 0.01:
            # 跌停
            self.update_limit_status(symbol, is_limit_up=False, is_limit_down=True)
        else:
            # 未涨跌停
            self.update_limit_status(symbol, is_limit_up=False, is_limit_down=False)

        return self.is_limited(symbol) != was_limited

    def get_limit_price(self, symbol: str, previous_close: float, is_buy: bool = True) -> float:
        """获取涨跌停价格

        Args:
            symbol: 股票代码
            previous_close: 前一交易日收盘价
            is_buy: True表示获取涨停价（买入参考），False表示获取跌停价（卖出参考）

        Returns:
            涨跌停价格
        """
        limit_up_ratio, limit_down_ratio = self._get_limit_ratios(symbol)

        if is_buy:
            return previous_close * (1 + limit_up_ratio)
        else:
            return previous_close * (1 - limit_down_ratio)

    def get_all_limit_up_stocks(self) -> List[str]:
        """获取所有涨停股票

        Returns:
            涨停股票代码列表
        """
        return list(self.limit_up_stocks)

    def get_all_limit_down_stocks(self) -> List[str]:
        """获取所有跌停股票

        Returns:
            跌停股票代码列表
        """
        return list(self.limit_down_stocks)

    def get_limit_info(self, symbol: str) -> Dict[str, any]:
        """获取股票的涨跌停信息

        Args:
            symbol: 股票代码

        Returns:
            涨跌停信息字典
        """
        return {
            "symbol": symbol,
            "is_limit_up": self.is_limit_up(symbol),
            "is_limit_down": self.is_limit_down(symbol),
            "limit_up_ratio": self._get_limit_ratios(symbol)[0],
            "limit_down_ratio": self._get_limit_ratios(symbol)[1]
        }

    def clear(self) -> None:
        """清除所有涨跌停记录"""
        self.limit_up_stocks.clear()
        self.limit_down_stocks.clear()

    def reset(self) -> None:
        """重置所有状态"""
        self.clear()
        self.stock_type_map.clear()

    def __repr__(self) -> str:
        return f"PriceLimitAdapter(limit_up={len(self.limit_up_stocks)}, limit_down={len(self.limit_down_stocks)})"


class ChinaTradingAdapter:
    """A股交易综合适配器

    整合T+1规则和涨跌停规则的综合性适配器，
    用于在实盘交易或回测中确保交易符合A股市场规则。

    Attributes:
        t1_adapter: T+1规则适配器
        price_limit_adapter: 涨跌停适配器
    """

    def __init__(
        self,
        limit_up_ratio: float = 0.10,
        limit_down_ratio: float = 0.10
    ):
        """初始化综合适配器

        Args:
            limit_up_ratio: 涨停比例
            limit_down_ratio: 跌停比例
        """
        self.t1_adapter = T1RuleAdapter()
        self.price_limit_adapter = PriceLimitAdapter(limit_up_ratio, limit_down_ratio)

    def can_buy(
        self,
        symbol: str,
        current_price: float,
        target_price: float
    ) -> bool:
        """检查是否可以买入

        Args:
            symbol: 股票代码
            current_price: 当前价格
            target_price: 目标买入价格

        Returns:
            如果可以买入返回True
        """
        return self.price_limit_adapter.can_buy(symbol, current_price, target_price)

    def can_sell(
        self,
        symbol: str,
        current_date: datetime,
        current_price: float,
        target_price: float,
        volume: int
    ) -> bool:
        """检查是否可以卖出

        需要同时满足T+1规则和涨跌停规则。

        Args:
            symbol: 股票代码
            current_date: 当前日期
            current_price: 当前价格
            target_price: 目标卖出价格
            volume: 卖出数量

        Returns:
            如果可以卖出返回True
        """
        # 检查T+1规则
        if not self.t1_adapter.can_sell(symbol, current_date):
            return False
        if not self.t1_adapter.can_sell_volume(symbol, current_date, volume) > 0:
            return False

        # 检查涨跌停规则
        if not self.price_limit_adapter.can_sell(symbol, current_price, target_price):
            return False

        return True

    def record_buy(self, symbol: str, date: datetime, volume: int) -> None:
        """记录买入操作

        Args:
            symbol: 股票代码
            date: 买入日期
            volume: 买入数量
        """
        self.t1_adapter.record_buy(symbol, date, volume)

    def record_sell(self, symbol: str, volume: int) -> int:
        """记录卖出操作

        Args:
            symbol: 股票代码
            volume: 卖出数量

        Returns:
            实际卖出的数量
        """
        return self.t1_adapter.record_sell(symbol, volume)

    def get_holdings(self) -> Dict[str, int]:
        """获取所有持仓

        Returns:
            持仓字典
        """
        return self.t1_adapter.get_all_holdings()

    def update_limit_status(
        self,
        symbol: str,
        is_limit_up: bool,
        is_limit_down: bool = False
    ) -> None:
        """更新涨跌停状态

        Args:
            symbol: 股票代码
            is_limit_up: 是否涨停
            is_limit_down: 是否跌停
        """
        self.price_limit_adapter.update_limit_status(symbol, is_limit_up, is_limit_down)

    def reset(self) -> None:
        """重置所有适配器状态"""
        self.t1_adapter.reset()
        self.price_limit_adapter.reset()

    def __repr__(self) -> str:
        return f"ChinaTradingAdapter(t1={repr(self.t1_adapter)}, price_limit={repr(self.price_limit_adapter)})"
