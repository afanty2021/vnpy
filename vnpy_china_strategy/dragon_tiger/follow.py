"""
龙虎榜跟随策略

跟随近期多次上榜的股票，在回调时买入。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.dragon_tiger.models import DragonTigerRecord
from vnpy_china_strategy.config import DragonTigerConfig


class FollowStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """龙虎榜跟随策略

    策略逻辑：
    1. 获取近期多次上榜的股票
    2. 上榜后持续跟踪
    3. 在回调时买入

    参数：
    - appear_count: 上榜次数
    - follow_days: 跟随天数
    - pullback_ratio: 回调买入比例
    - holding_days: 持有天数
    """

    parameters = [
        "appear_count",
        "follow_days",
        "pullback_ratio",
        "holding_days",
        "position_ratio",
    ]

    variables = [
        "signal_count",
        "positions",
        "follow_stocks",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.appear_count = setting.get("appear_count", 2)
        self.follow_days = setting.get("follow_days", 10)
        self.pullback_ratio = setting.get("pullback_ratio", 0.05)  # 5%回调
        self.holding_days = setting.get("holding_days", 5)
        self.position_ratio = setting.get("position_ratio", 0.08)

        # 策略变量
        self.signal_count = 0
        self.positions: Dict[str, int] = {}
        self.follow_stocks: Dict[str, Dict] = {}  # 跟踪的股票

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = DragonTigerConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("龙虎榜跟随策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("龙虎榜跟随策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取近期龙虎榜数据
        recent_data = self._get_recent_dragon_tiger(days=20)
        if not recent_data:
            return

        # 统计上榜次数
        stock_appears = self._count_stock_appears(recent_data)

        # 更新跟踪列表
        self._update_follow_stocks(stock_appears)

        # 筛选买入信号
        buy_signals = self._check_buy_signals()
        for symbol in buy_signals:
            self._execute_buy(symbol)

        # 检查卖出信号
        self._check_sell_signals(bar.datetime)

    def _get_recent_dragon_tiger(
        self,
        days: int
    ) -> List[DragonTigerRecord]:
        """获取近期龙虎榜数据"""
        if not self.data_service:
            return []

        all_data = []
        current = date.today()

        for i in range(days):
            trade_date = current - timedelta(days=i)
            try:
                data_list = self.data_service.get_dragon_tiger_data(trade_date)
                records = [DragonTigerRecord.from_dict(d) for d in data_list]
                all_data.extend(records)
            except Exception:
                continue

        return all_data

    def _count_stock_appears(
        self,
        records: List[DragonTigerRecord]
    ) -> Dict[str, int]:
        """统计股票上榜次数"""
        stock_appears = defaultdict(int)
        latest_date = None

        for record in records:
            stock_appears[record.symbol] += 1
            if not latest_date or record.trade_date > latest_date:
                latest_date = record.trade_date

        return {
            "appears": dict(stock_appears),
            "latest_date": latest_date
        }

    def _update_follow_stocks(
        self,
        stock_appears: Dict[str, any]
    ):
        """更新跟踪股票列表"""
        appears = stock_appears.get("appears", {})
        latest_date = stock_appears.get("latest_date")

        for symbol, count in appears.items():
            if count >= self.appear_count:
                if symbol not in self.follow_stocks:
                    # 新增跟踪
                    self.follow_stocks[symbol] = {
                        "appear_count": count,
                        "first_seen_date": latest_date,
                        "last_price": 0.0,
                        "entry_date": None,
                    }
                else:
                    # 更新
                    self.follow_stocks[symbol]["appear_count"] = count
            else:
                # 移除
                if symbol in self.follow_stocks:
                    del self.follow_stocks[symbol]

    def _check_buy_signals(self) -> List[str]:
        """检查买入信号

        回调买入条件：
        1. 在跟踪列表中
        2. 出现回调（跌幅 > pullback_ratio）
        3. 未持仓
        """
        signals = []

        for symbol, info in self.follow_stocks.items():
            # 排除已持仓
            if symbol in self.positions:
                continue

            # 获取当前价格
            price = self.get_current_price(symbol)
            if not price:
                continue

            # 获取历史价格
            last_price = info.get("last_price", 0)
            if last_price <= 0:
                info["last_price"] = price
                continue

            # 检查回调
            pullback = (last_price - price) / last_price
            if pullback >= self.pullback_ratio:
                signals.append(symbol)

            # 更新价格
            info["last_price"] = price

        return signals

    def _execute_buy(self, symbol: str):
        """执行买入"""
        if symbol not in self.follow_stocks:
            return

        if not self.is_tradeable(symbol):
            return

        price = self.get_current_price(symbol)
        if not price:
            return

        # 计算仓位
        account = self.cta_engine.get_account() if self.cta_engine else None
        if account:
            risk_amount = account.available * self.position_ratio
            size = self.calculate_position_size(price, risk_amount)
        else:
            size = 100

        if size <= 0:
            return

        # 执行买入
        exchange = self._get_exchange_from_symbol(symbol)
        vt_symbol = f"{symbol}.{exchange.value}"

        if hasattr(self, "buy"):
            self.buy(price, size, vt_symbol)

        # 记录持仓
        self.positions[symbol] = 0
        self.position_manager.add_position(
            symbol, size, price, datetime.now()
        )

        self.signal_count += 1

        # 取消跟踪
        if symbol in self.follow_stocks:
            info = self.follow_stocks[symbol]
            self.write_log(
                f"跟随买入: {symbol}, "
                f"上榜次数: {info.get('appear_count', 0)}"
            )

    def _check_sell_signals(self, current_time: datetime):
        """检查卖出信号"""
        to_close = []

        for symbol, days in list(self.positions.items()):
            if days >= self.holding_days:
                to_close.append(symbol)

        for symbol in to_close:
            self._execute_sell(symbol)

        # 更新持仓天数
        for symbol in self.positions:
            self.positions[symbol] += 1

    def _execute_sell(self, symbol: str):
        """执行卖出"""
        if symbol not in self.positions:
            return

        price = self.get_current_price(symbol)
        if not price:
            return

        position = self.position_manager.get_position(symbol)
        volume = position.get("volume", 0) if position else 0

        if volume <= 0:
            return

        exchange = self._get_exchange_from_symbol(symbol)
        vt_symbol = f"{symbol}.{exchange.value}"

        if hasattr(self, "sell"):
            self.sell(price, volume, vt_symbol)

        del self.positions[symbol]
        self.position_manager.remove_position(symbol)
