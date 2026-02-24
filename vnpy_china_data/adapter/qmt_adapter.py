"""
QMT数据适配器

实现QMT证券客户端的数据获取和实时行情订阅功能。
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, date
from threading import Thread, Event, Lock
from collections import defaultdict

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.event import EventEngine

from .base import BaseDataAdapter


class QMTDataAdapter(BaseDataAdapter):
    """QMT数据适配器

    封装QMT证券客户端API，提供：
    - 实时行情订阅
    - Tick数据获取
    - 实时K线生成
    """

    def __init__(
        self,
        qmt_path: str = "",
        account_id: str = "",
        event_engine: Optional[EventEngine] = None,
    ):
        """初始化QMT适配器

        Args:
            qmt_path: QMT Mini路径
            account_id: 账户ID
            event_engine: 事件引擎（用于发布行情事件）
        """
        super().__init__()
        self.qmt_path = qmt_path
        self.account_id = account_id
        self.event_engine = event_engine

        # QMT API对象（动态导入）
        self._qmt_api = None
        self._session_id: Optional[int] = None

        # 订阅管理
        self._subscribed_symbols: set = set()
        self._symbol_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # Tick数据缓存
        self._tick_cache: Dict[str, TickData] = {}

        # 实时K线生成器
        self._bar_generators: Dict[str, "RealtimeBarGenerator"] = {}

        # 运行控制
        self._stop_event = Event()
        self._reconnect_thread: Optional[Thread] = None
        self._reconnect_interval = 30

        # 统计信息
        self._tick_count = 0
        self._last_tick_time: Optional[datetime] = None
        self._lock = Lock()

    def connect(self) -> bool:
        """连接QMT"""
        try:
            # 尝试导入xtquant
            try:
                from xtquant import xtquant
                from xtquant.xttype import Stock
                self._qmt_api = xtquant
            except ImportError:
                print("警告: 未安装xtquant库，QMT适配器无法使用")
                return False

            # 尝试连接
            if self.qmt_path and self._qmt_api:
                # 创建session
                self._session_id = 1
                # 注意：实际连接需要QMT客户端运行
                self._connected = True
                return True

            return False

        except Exception as e:
            print(f"QMT连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开QMT连接"""
        self._stop_event.set()

        # 停止重连线程
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=5)

        # 取消所有订阅
        if self._subscribed_symbols:
            self.unsubscribe(list(self._subscribed_symbols))

        # 清理状态
        self._subscribed_symbols.clear()
        self._tick_cache.clear()
        self._bar_generators.clear()
        self._connected = False

    def _start_reconnect_thread(self) -> None:
        """启动重连线程"""
        self._stop_event = Event()
        self._reconnect_thread = Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        """重连循环"""
        while not self._stop_event.is_set():
            if not self._connected:
                self.connect()
            self._stop_event.wait(self._reconnect_interval)

    # ========== 行情数据实现 ==========

    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取K线数据

        Note: QMT主要用于实时数据，历史数据建议使用Tushare
        """
        # 如果连接了QMT，可以尝试获取
        # 这里简化处理，返回空列表
        return []

    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """获取Tick数据"""
        # 返回缓存的Tick数据
        vt_symbol = f"{symbol}.{exchange.value}"
        tick = self._tick_cache.get(vt_symbol)

        if tick:
            return [tick]
        return []

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息

        Note: QMT不提供此功能，需要使用Tushare
        """
        return None

    # ========== 实时行情订阅 ==========

    def subscribe(self, symbols: List[str]) -> bool:
        """订阅实时行情"""
        if not self._connected:
            return False

        try:
            for symbol in symbols:
                if symbol not in self._subscribed_symbols:
                    # 实际订阅逻辑
                    # self._qmt_api.subscribe_stock(symbol)
                    self._subscribed_symbols.add(symbol)

                    # 创建实时K线生成器
                    for interval in [Interval.MINUTE_1, Interval.MINUTE_5]:
                        key = f"{symbol}.{interval.value}"
                        if key not in self._bar_generators:
                            self._bar_generators[key] = RealtimeBarGenerator(
                                symbol, interval, self._on_bar_generated
                            )

            return True

        except Exception as e:
            print(f"QMT订阅失败: {e}")
            return False

    def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅"""
        try:
            for symbol in symbols:
                if symbol in self._subscribed_symbols:
                    # 实际取消订阅逻辑
                    # self._qmt_api.unsubscribe_stock(symbol)
                    self._subscribed_symbols.discard(symbol)

            return True

        except Exception as e:
            print(f"QMT取消订阅失败: {e}")
            return False

    def register_callback(
        self,
        symbol: str,
        callback: Callable[[TickData], None]
    ) -> None:
        """注册Tick回调"""
        self._symbol_callbacks[symbol].append(callback)

    def _on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        with self._lock:
            # 更新缓存
            self._tick_cache[tick.vt_symbol] = tick
            self._tick_count += 1
            self._last_tick_time = datetime.now()

            # 更新K线生成器
            for generator in self._bar_generators.values():
                if tick.symbol in generator.symbol:
                    generator.update_tick(tick)

            # 执行回调
            callbacks = self._symbol_callbacks.get(tick.symbol, [])
            for callback in callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    print(f"回调执行失败: {e}")

            # 发布事件
            if self.event_engine:
                self.event_engine.put(tick)

    def _on_bar_generated(self, bar: BarData) -> None:
        """K线生成回调"""
        if self.event_engine:
            self.event_engine.put(bar)

    # ========== 订单簿功能 ==========

    def get_order_book(self, symbol: str) -> Optional[Dict]:
        """获取订单簿"""
        tick = self._tick_cache.get(symbol)
        if not tick:
            return None

        return {
            "bid_price_1": tick.bid_price_1,
            "bid_volume_1": tick.bid_volume_1,
            "bid_price_2": tick.bid_price_2,
            "bid_volume_2": tick.bid_volume_2,
            "bid_price_3": tick.bid_price_3,
            "bid_volume_3": tick.bid_volume_3,
            "bid_price_4": tick.bid_price_4,
            "bid_volume_4": tick.bid_volume_4,
            "bid_price_5": tick.bid_price_5,
            "bid_volume_5": tick.bid_volume_5,
            "ask_price_1": tick.ask_price_1,
            "ask_volume_1": tick.ask_volume_1,
            "ask_price_2": tick.ask_price_2,
            "ask_volume_2": tick.ask_volume_2,
            "ask_price_3": tick.ask_price_3,
            "ask_volume_3": tick.ask_volume_3,
            "ask_price_4": tick.ask_price_4,
            "ask_volume_4": tick.ask_volume_4,
            "ask_price_5": tick.ask_price_5,
            "ask_volume_5": tick.ask_volume_5,
        }

    def get_bid_ask_spread(self, symbol: str) -> Optional[float]:
        """获取买卖价差"""
        order_book = self.get_order_book(symbol)
        if order_book:
            return order_book.get("ask_price_1", 0) - order_book.get("bid_price_1", 0)
        return None

    # ========== 统计信息 ==========

    @property
    def tick_count(self) -> int:
        """Tick总数"""
        return self._tick_count

    @property
    def last_tick_time(self) -> Optional[datetime]:
        """最后Tick时间"""
        return self._last_tick_time

    @property
    def subscribed_count(self) -> int:
        """订阅数量"""
        return len(self._subscribed_symbols)


class RealtimeBarGenerator:
    """实时K线生成器

    从Tick数据实时生成K线数据。
    """

    def __init__(
        self,
        symbol: str,
        interval: Interval,
        callback: Optional[Callable[[BarData], None]] = None
    ):
        self.symbol = symbol
        self.interval = interval
        self.callback = callback

        # 当前K线数据
        self._current_bar: Optional[BarData] = None
        self._last_tick: Optional[TickData] = None

        # 周期转换
        self._interval_seconds = self._get_interval_seconds(interval)

    def update_tick(self, tick: TickData) -> Optional[BarData]:
        """更新Tick数据，生成K线"""
        # 初始化或创建新K线
        if not self._current_bar:
            self._create_new_bar(tick)
            return None

        # 检查是否需要创建新K线
        current_time = tick.datetime
        bar_time = self._current_bar.datetime

        # 计算时间差
        if self._is_new_bar(current_time, bar_time):
            # 返回完成的K线，创建新K线
            finished_bar = self._current_bar
            self._create_new_bar(tick)
            return finished_bar

        # 更新当前K线
        self._update_bar(tick)
        return None

    def _create_new_bar(self, tick: TickData) -> None:
        """创建新K线"""
        self._current_bar = BarData(
            symbol=tick.symbol,
            exchange=tick.exchange,
            interval=self.interval,
            datetime=self._get_bar_time(tick.datetime),
            open_price=tick.last_price,
            high_price=tick.last_price,
            low_price=tick.last_price,
            close_price=tick.last_price,
            volume=tick.volume,
            turnover=tick.turnover
        )

    def _update_bar(self, tick: TickData) -> None:
        """更新当前K线"""
        if not self._current_bar:
            return

        # 更新收盘价
        self._current_bar.close_price = tick.last_price

        # 更新最高价
        if tick.last_price > self._current_bar.high_price:
            self._current_bar.high_price = tick.last_price

        # 更新最低价
        if tick.last_price < self._current_bar.low_price:
            self._current_bar.low_price = tick.last_price

        # 累加成交量
        if tick.volume and self._last_tick:
            self._current_bar.volume += (tick.volume - self._last_tick.volume)

        # 累加成交额
        if tick.turnover and self._last_tick:
            self._current_bar.turnover += (tick.turnover - self._last_tick.turnover)

        self._last_tick = tick

    def _is_new_bar(self, current_time: datetime, bar_time: datetime) -> bool:
        """判断是否新K线"""
        if self.interval == Interval.MINUTE_1:
            return current_time.minute != bar_time.minute
        elif self.interval == Interval.MINUTE_5:
            return (current_time - bar_time).seconds >= 300
        elif self.interval == Interval.MINUTE_15:
            return (current_time - bar_time).seconds >= 900
        elif self.interval == Interval.MINUTE_30:
            return (current_time - bar_time).seconds >= 1800

        return False

    def _get_bar_time(self, tick_time: datetime) -> datetime:
        """获取K线时间"""
        if self.interval == Interval.MINUTE_1:
            return tick_time.replace(second=0, microsecond=0)
        elif self.interval == Interval.MINUTE_5:
            minute = (tick_time.minute // 5) * 5
            return tick_time.replace(minute=minute, second=0, microsecond=0)
        elif self.interval == Interval.MINUTE_15:
            minute = (tick_time.minute // 15) * 15
            return tick_time.replace(minute=minute, second=0, microsecond=0)
        elif self.interval == Interval.MINUTE_30:
            minute = (tick_time.minute // 30) * 30
            return tick_time.replace(minute=minute, second=0, microsecond=0)

        return tick_time

    @staticmethod
    def _get_interval_seconds(interval: Interval) -> int:
        """获取周期秒数"""
        mapping = {
            Interval.MINUTE_1: 60,
            Interval.MINUTE_5: 300,
            Interval.MINUTE_15: 900,
            Interval.MINUTE_30: 1800,
            Interval.HOUR_1: 3600,
        }
        return mapping.get(interval, 60)
