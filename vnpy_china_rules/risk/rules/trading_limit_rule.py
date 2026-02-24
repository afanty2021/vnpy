"""
交易限制风控规则

实现频率/撤单/价格偏离/连续亏损等检查
"""

from vnpy.trader.object import OrderRequest, OrderData, TradeData
from vnpy.trader.constant import Direction, Status
from vnpy_riskmanager.template import RuleTemplate
from datetime import datetime, timedelta


class TradingLimitRule(RuleTemplate):
    """交易限制风控规则"""

    name: str = "A股交易限制"

    parameters: dict[str, str] = {
        "max_orders_per_minute": "每分钟最大委托数",
        "max_orders_per_day": "每日最大委托数",
        "max_cancel_ratio": "最大撤单比例",
        "max_price_deviation": "最大价格偏离比例",
        "max_consecutive_losses": "最大连续亏损次数",
    }

    variables: dict[str, str] = {
        "minute_order_count": "分钟委托数",
        "daily_order_count": "日委托数",
        "cancel_ratio": "撤单比例",
        "consecutive_losses": "连续亏损次数",
    }

    def on_init(self) -> None:
        """初始化"""
        self.max_orders_per_minute: int = 10
        self.max_orders_per_day: int = 100
        self.max_cancel_ratio: float = 0.5
        self.max_price_deviation: float = 0.02
        self.max_consecutive_losses: int = 5

        # 运行时状态
        self.minute_orders: list[datetime] = []
        self.daily_orders: list[datetime] = []
        self.cancel_count: int = 0
        self.order_count: int = 0
        self.consecutive_losses: int = 0
        self.last_date: datetime = datetime.now()  # 上次检查日期

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """检查是否允许委托"""
        # 1. 检查分钟频率限制
        if self._check_minute_limit():
            return False

        # 2. 检查日频率限制
        if self._check_daily_limit():
            return False

        # 3. 检查价格偏离
        if self._check_price_deviation(req):
            return False

        # 4. 检查撤单比例
        if self._check_cancel_ratio():
            return False

        # 5. 检查连续亏损
        if self._check_consecutive_losses():
            return False

        return True

    def on_order(self, order: OrderData) -> None:
        """委托推送"""
        self.order_count += 1
        self.daily_orders.append(order.datetime)
        self.minute_orders.append(order.datetime)

        # 记录撤单
        if order.status == Status.CANCELLED:
            self.cancel_count += 1

        self.put_event()

    def on_trade(self, trade: TradeData) -> None:
        """成交推送"""
        # 检查连续亏损
        # 这里需要结合持仓和盈亏计算
        self.put_event()

    def on_timer(self) -> None:
        """定时清理"""
        now = datetime.now()

        # 清理一分钟前的委托记录
        cutoff = now - timedelta(minutes=1)
        self.minute_orders = [t for t in self.minute_orders if t > cutoff]

        # 清理昨天的委托记录
        if now.date() > self.last_date.date():
            self.daily_orders.clear()
            self.order_count = 0
            self.cancel_count = 0
            self.last_date = now

        self.put_event()

    def _check_minute_limit(self) -> bool:
        """检查分钟频率"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        recent_orders = [t for t in self.minute_orders if t > cutoff]

        if len(recent_orders) >= self.max_orders_per_minute:
            self.write_log(
                f"分钟委托数{len(recent_orders)}达到上限{self.max_orders_per_minute}"
            )
            return True
        return False

    def _check_daily_limit(self) -> bool:
        """检查日频率"""
        if self.order_count >= self.max_orders_per_day:
            self.write_log(
                f"日委托数{self.order_count}达到上限{self.max_orders_per_day}"
            )
            return True
        return False

    def _check_price_deviation(self, req: OrderRequest) -> bool:
        """检查价格偏离"""
        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 获取最新行情
        tick = self.risk_engine.main_engine.get_tick(req.vt_symbol)
        if not tick:
            return False

        # 计算偏离比例
        if req.direction == Direction.LONG:
            # 买入，检查卖价
            deviation = abs(req.price - tick.ask_price_1) / tick.ask_price_1
        else:
            # 卖出，检查买价
            deviation = abs(req.price - tick.bid_price_1) / tick.bid_price_1

        if deviation > self.max_price_deviation:
            self.write_log(
                f"价格偏离比例{deviation:.2%}超过上限{self.max_price_deviation:.2%}"
            )
            return True
        return False

    def _check_consecutive_losses(self) -> bool:
        """检查连续亏损"""
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.write_log(
                f"连续亏损{self.consecutive_losses}次达到上限{self.max_consecutive_losses}，"
                f"禁止开仓"
            )
            return True
        return False

    def _check_cancel_ratio(self) -> bool:
        """检查撤单比例"""
        if self.order_count == 0:
            return False

        cancel_ratio = self.cancel_count / self.order_count

        if cancel_ratio > self.max_cancel_ratio:
            self.write_log(
                f"撤单比例{cancel_ratio:.2%}超过上限{self.max_cancel_ratio:.2%}"
            )
            return True
        return False
