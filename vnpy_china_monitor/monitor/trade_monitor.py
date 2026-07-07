"""
交易监控器

监控成交记录、委托状态、持仓变化、资金变化和日盈亏统计
"""

from datetime import datetime, time
from typing import Dict, List, Optional, Any
from collections import defaultdict
import threading

from loguru import logger

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Direction
from vnpy.trader.object import TradeData, OrderData, AccountData, PositionData
from vnpy.trader.event import EVENT_TRADE, EVENT_ORDER, EVENT_POSITION, EVENT_ACCOUNT

from vnpy_china_monitor.monitor.engine import MonitorEngine, MonitorType
from vnpy_china_monitor.event import EVENT_MONITOR_DATA


class TradeMonitor:
    """交易监控器

    监控成交、委托、持仓、资金变化和日盈亏统计
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine, monitor_engine: MonitorEngine):
        """初始化交易监控器

        Args:
            main_engine: 主引擎
            event_engine: 事件引擎
            monitor_engine: 监控引擎
        """
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.monitor_engine = monitor_engine

        # 历史数据
        self._trade_history: List[TradeData] = []
        self._order_history: List[OrderData] = []
        self._max_trade_history = 10000
        self._max_order_history = 5000

        # 当日报表数据
        self._today_trades: List[TradeData] = []
        self._today_order_count: Dict[str, int] = defaultdict(int)
        self._today_trade_count: Dict[str, int] = defaultdict(int)
        # 当日日期标记：事件回调检测跨日时重置 _today_* 计数器
        self._current_day = datetime.now().date()

        # 最后更新的持仓和资金快照
        self._last_positions: Dict[str, PositionData] = {}
        self._last_account: Optional[AccountData] = None
        self._last_update_time: Optional[datetime] = None

        # 运行状态
        self._running = False
        self._lock = threading.Lock()

        # 注册事件
        self._register_events()

        logger.info("TradeMonitor 初始化完成")

    def _register_events(self) -> None:
        """注册交易事件"""
        self.event_engine.register(EVENT_TRADE, self.on_trade)
        self.event_engine.register(EVENT_ORDER, self.on_order)
        self.event_engine.register(EVENT_POSITION, self.on_position)
        self.event_engine.register(EVENT_ACCOUNT, self.on_account)
        logger.debug("交易事件注册完成")

    def on_trade(self, event: Event) -> None:
        """成交推送回调

        Args:
            event: 事件对象
        """
        trade: TradeData = event.data

        with self._lock:
            # 跨日重置当日计数器（_today_* 不应跨日累积）
            self._maybe_reset_daily(trade.datetime)

            # 添加到历史记录
            self._trade_history.append(trade)
            if len(self._trade_history) > self._max_trade_history:
                self._trade_history.pop(0)

            # 检查是否当日成交
            if self._is_today(trade.datetime):
                self._today_trades.append(trade)
                self._today_trade_count[trade.vt_symbol] += 1

        # 更新监控数据
        self._update_trade_monitor(trade)

        logger.debug(
            f"成交推送: {trade.vt_symbol} {trade.direction.value} "
            f"{trade.volume}@{trade.price}"
        )

    def on_order(self, event: Event) -> None:
        """委托推送回调

        Args:
            event: 事件对象
        """
        order: OrderData = event.data

        with self._lock:
            # 跨日重置当日计数器
            self._maybe_reset_daily(order.datetime)

            # 添加到历史记录
            self._order_history.append(order)
            if len(self._order_history) > self._max_order_history:
                self._order_history.pop(0)

            # 检查是否当日委托
            if self._is_today(order.datetime):
                self._today_order_count[order.vt_symbol] += 1

        logger.debug(
            f"委托推送: {order.vt_symbol} {order.direction.value} "
            f"{order.volume}@{order.price} {order.status.value}"
        )

    def on_position(self, event: Event) -> None:
        """持仓推送回调

        Args:
            event: 事件对象
        """
        position: PositionData = event.data

        with self._lock:
            self._last_positions[position.vt_symbol] = position
            self._last_update_time = datetime.now()

        # 更新持仓监控
        self._update_position_monitor(position)

    def on_account(self, event: Event) -> None:
        """账户推送回调

        Args:
            event: 事件对象
        """
        account: AccountData = event.data

        with self._lock:
            self._last_account = account
            self._last_update_time = datetime.now()

        # 更新资金监控
        self._update_account_monitor(account)

    def _update_trade_monitor(self, trade: TradeData) -> None:
        """更新成交监控数据"""
        self.monitor_engine.update_monitor(
            name=f"trade_{trade.vt_symbol}",
            monitor_type=MonitorType.TRADE,
            value=f"{trade.volume}@{trade.price}",
            status="normal",
            unit="",
            description=f"{trade.direction.value} {trade.offset.value}",
        )

    def _update_position_monitor(self, position: PositionData) -> None:
        """更新持仓监控数据"""
        # 净持仓
        net_position = position.volume - position.yd_volume
        if net_position > 0:
            status = "long"
        elif net_position < 0:
            status = "short"
        else:
            status = "flat"

        self.monitor_engine.update_monitor(
            name=f"position_{position.vt_symbol}",
            monitor_type=MonitorType.TRADE,
            value=net_position,
            status=status,
            unit="股",
            description=f"持仓: {position.volume}, 昨仓: {position.yd_volume}, "
                        f"冻结: {position.frozen}",
        )

        # 持仓盈亏
        if position.pnl != 0:
            pnl_status = "profit" if position.pnl > 0 else "loss"
            self.monitor_engine.update_monitor(
                name=f"pnl_{position.vt_symbol}",
                monitor_type=MonitorType.TRADE,
                value=position.pnl,
                status=pnl_status,
                unit="元",
                description=f"持仓盈亏: {position.pnl:.2f}",
            )

    def _update_account_monitor(self, account: AccountData) -> None:
        """更新账户监控数据"""
        # 资金余额
        self.monitor_engine.update_monitor(
            name="account_balance",
            monitor_type=MonitorType.TRADE,
            value=account.balance,
            status="normal",
            unit="元",
            description=f"账户余额: {account.balance:.2f}",
        )

        # 可用资金
        self.monitor_engine.update_monitor(
            name="account_available",
            monitor_type=MonitorType.TRADE,
            value=account.available,
            status="normal",
            unit="元",
            description=f"可用资金: {account.available:.2f}",
        )

        # 冻结资金
        if account.frozen > 0:
            self.monitor_engine.update_monitor(
                name="account_frozen",
                monitor_type=MonitorType.TRADE,
                value=account.frozen,
                status="normal",
                unit="元",
                description=f"冻结资金: {account.frozen:.2f}",
            )

    def get_positions(self) -> List[PositionData]:
        """获取当前持仓列表

        Returns:
            持仓列表
        """
        with self._lock:
            return list(self._last_positions.values())

    def get_position(self, vt_symbol: str) -> Optional[PositionData]:
        """获取指定合约的持仓

        Args:
            vt_symbol: 合约代码

        Returns:
            持仓数据或None
        """
        with self._lock:
            return self._last_positions.get(vt_symbol)

    def get_account(self) -> Optional[AccountData]:
        """获取账户数据

        Returns:
            账户数据或None
        """
        with self._lock:
            return self._last_account

    def get_daily_stats(self) -> Dict[str, Any]:
        """获取当日统计数据

        Returns:
            当日统计字典
        """
        with self._lock:
            # 过滤当日成交
            today_trades = [t for t in self._trade_history if self._is_today(t.datetime)]

            # 计算成交统计
            total_buy = 0
            total_sell = 0
            buy_amount = 0.0
            sell_amount = 0.0
            sell_cost = 0.0  # 卖出对应的持仓成本（监控层用持仓均价近似）

            for trade in today_trades:
                # 用枚举比较，避免依赖 direction.value 的字符串（vnpy Direction.LONG.value 为"多"）
                if trade.direction == Direction.LONG:
                    total_buy += trade.volume
                    buy_amount += trade.volume * trade.price
                else:
                    total_sell += trade.volume
                    sell_amount += trade.volume * trade.price
                    # 卖出对应持仓成本：用当前持仓均价，无持仓记录则回退当前价（盈亏为0）
                    pos = self._last_positions.get(trade.vt_symbol)
                    cost_price = pos.price if pos else trade.price
                    sell_cost += trade.volume * cost_price

            # 手续费（万3 双边）+ 印花税（卖出单边万5，自 2023-08-28 起）
            commission = (buy_amount + sell_amount) * 0.0003
            stamp_duty = sell_amount * 0.0005

            # 持仓盈亏
            position_pnl = 0.0
            for pos in self._last_positions.values():
                position_pnl += pos.pnl

            # 平仓盈亏：卖出收入 - 卖出对应持仓成本 - 手续费 - 印花税
            closed_pnl = sell_amount - sell_cost - commission - stamp_duty

            return {
                "date": datetime.now().date().isoformat(),
                "trade_count": len(today_trades),
                "order_count": sum(self._today_order_count.values()),
                "buy_volume": total_buy,
                "sell_volume": total_sell,
                "buy_amount": buy_amount,
                "sell_amount": sell_amount,
                "commission": commission,
                "stamp_duty": stamp_duty,
                "closed_pnl": closed_pnl,
                "position_pnl": position_pnl,
                "total_pnl": closed_pnl + position_pnl,
            }

    def get_position_summary(self) -> Dict[str, Any]:
        """获取持仓汇总

        Returns:
            持仓汇总字典
        """
        with self._lock:
            total_volume = 0
            total_pnl = 0.0
            long_count = 0
            short_count = 0

            for pos in self._last_positions.values():
                if pos.volume > 0:
                    long_count += 1
                elif pos.volume < 0:
                    short_count += 1

                total_volume += abs(pos.volume)
                total_pnl += pos.pnl

            return {
                "total_positions": len(self._last_positions),
                "long_positions": long_count,
                "short_positions": short_count,
                "total_volume": total_volume,
                "total_pnl": total_pnl,
            }

    def get_order_stats(self) -> Dict[str, Any]:
        """获取委托统计

        Returns:
            委托统计字典
        """
        with self._lock:
            # 按状态分类统计
            status_count = defaultdict(int)
            direction_count = defaultdict(int)

            for order in self._order_history:
                status_count[order.status.value] += 1
                direction_count[order.direction.value] += 1

            return {
                "total_orders": len(self._order_history),
                "by_status": dict(status_count),
                "by_direction": dict(direction_count),
            }

    def get_trade_history(self, limit: int = 100) -> List[TradeData]:
        """获取成交历史

        Args:
            limit: 返回数量限制

        Returns:
            成交历史列表
        """
        with self._lock:
            return self._trade_history[-limit:]

    def get_order_history(self, limit: int = 100) -> List[OrderData]:
        """获取委托历史

        Args:
            limit: 返回数量限制

        Returns:
            委托历史列表
        """
        with self._lock:
            return self._order_history[-limit:]

    def _maybe_reset_daily(self, dt: Optional[datetime]) -> None:
        """检测跨日并重置当日计数器

        _today_trades / _today_order_count / _today_trade_count 在长期运行的
        监控器中若不重置，跨交易日后昨日计数会持续累积为"今日"数据。
        """
        today = (dt or datetime.now()).date()
        if today != self._current_day:
            self._today_trades.clear()
            self._today_order_count.clear()
            self._today_trade_count.clear()
            self._current_day = today

    def _is_today(self, dt: Optional[datetime]) -> bool:
        """判断是否当日

        Args:
            dt: 日期时间

        Returns:
            是否当日
        """
        if dt is None:
            return False

        today = datetime.now().date()
        return dt.date() == today

    def start(self) -> None:
        """启动交易监控"""
        if self._running:
            logger.warning("交易监控已在运行中")
            return

        self._running = True
        logger.info("交易监控已启动")

        # 初始化时获取当前持仓和账户数据
        self._init_snapshot()

    def stop(self) -> None:
        """停止交易监控"""
        if not self._running:
            logger.warning("交易监控未在运行")
            return

        self._running = False
        logger.info("交易监控已停止")

    def _init_snapshot(self) -> None:
        """初始化快照数据"""
        try:
            # 获取当前持仓
            positions = self.main_engine.get_all_positions()
            with self._lock:
                for pos in positions:
                    if pos.volume != 0 or pos.yd_volume != 0:
                        self._last_positions[pos.vt_symbol] = pos

            # 获取账户数据
            accounts = self.main_engine.get_all_accounts()
            if accounts:
                with self._lock:
                    self._last_account = accounts[0]

            logger.info(f"持仓快照已初始化: {len(self._last_positions)} 个合约")

        except Exception as e:
            logger.error(f"初始化快照数据失败: {e}")
