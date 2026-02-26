"""
RPC QMT数据适配器

通过RPC连接到Windows服务器上的QMT服务，实现跨平台数据访问。
适用于Mac/Linux客户端访问Windows上的QMT数据。
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, date
from threading import Thread, Event, Lock
from collections import defaultdict

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.event import EventEngine
from vnpy.rpc import RpcClient

from .base import BaseDataAdapter


class RpcQmtDataAdapter(BaseDataAdapter):
    """RPC QMT数据适配器

    通过RPC连接到Windows服务器上的QMT服务，提供：
    - 实时行情订阅
    - Tick数据获取
    - 跨平台访问（Mac/Linux 访问 Windows QMT）

    架构：
    Mac/Linux客户端 --RPC--> Windows服务器(QMT服务)
    """

    def __init__(
        self,
        req_address: str = "tcp://127.0.0.1:2014",
        sub_address: str = "tcp://127.0.0.1:4102",
        event_engine: Optional[EventEngine] = None,
    ):
        """初始化RPC QMT适配器

        Args:
            req_address: RPC请求地址
            sub_address: RPC订阅地址
            event_engine: 事件引擎（用于发布行情事件）
        """
        super().__init__()
        self.req_address = req_address
        self.sub_address = sub_address
        self.event_engine = event_engine

        # RPC客户端
        self._rpc_client: Optional["CustomRpcClient"] = None

        # 订阅管理
        self._subscribed_symbols: set = set()
        self._symbol_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # Tick数据缓存
        self._tick_cache: Dict[str, TickData] = {}

        # 运行控制
        self._stop_event = Event()
        self._reconnect_thread: Optional[Thread] = None
        self._reconnect_interval = 30

        # 统计信息
        self._tick_count = 0
        self._last_tick_time: Optional[datetime] = None
        self._lock = Lock()

    def connect(self) -> bool:
        """连接RPC QMT服务"""
        try:
            # 创建自定义RPC客户端
            self._rpc_client = CustomRpcClient()
            self._rpc_client.callback = self._on_callback

            # 启动RPC客户端
            self._rpc_client.start(self.req_address, self.sub_address)

            # 等待一小段时间确保连接建立
            import time
            time.sleep(0.5)

            self._connected = True
            print(f"RPC QMT适配器已连接: {self.req_address}")
            return True

        except Exception as e:
            print(f"RPC QMT连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开RPC连接"""
        self._stop_event.set()

        # 停止RPC客户端
        if self._rpc_client:
            self._rpc_client.stop()
            self._rpc_client.join()
            self._rpc_client = None

        # 停止重连线程
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=5)

        # 清理状态
        self._subscribed_symbols.clear()
        self._tick_cache.clear()
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
        """获取K线数据（通过RPC）

        Note: RPC QMT主要用于实时数据，历史数据建议使用Tushare
        """
        if not self._connected or not self._rpc_client:
            return []

        try:
            # 调用远程RPC方法
            result = self._rpc_client.get_bar_data(
                symbol=symbol,
                exchange=exchange.value,
                interval=interval.value,
                start=start,
                end=end,
                timeout=10000
            )
            return result if result else []
        except Exception as e:
            print(f"RPC获取K线数据失败: {e}")
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
        if not self._connected or not self._rpc_client:
            return False

        try:
            # 调用远程RPC订阅方法
            self._rpc_client.subscribe(symbols=symbols, timeout=5000)

            for symbol in symbols:
                self._subscribed_symbols.add(symbol)

            return True

        except Exception as e:
            print(f"RPC订阅失败: {e}")
            return False

    def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅"""
        if not self._connected or not self._rpc_client:
            return False

        try:
            # 调用远程RPC取消订阅方法
            self._rpc_client.unsubscribe(symbols=symbols, timeout=5000)

            for symbol in symbols:
                self._subscribed_symbols.discard(symbol)

            return True

        except Exception as e:
            print(f"RPC取消订阅失败: {e}")
            return False

    def register_callback(
        self,
        symbol: str,
        callback: Callable[[TickData], None]
    ) -> None:
        """注册Tick回调"""
        self._symbol_callbacks[symbol].append(callback)

    def _on_callback(self, topic: str, data: Any) -> None:
        """处理RPC回调数据"""
        try:
            if topic == "tick":
                # 处理Tick数据
                tick: TickData = data
                self._on_tick(tick)
            elif topic == "bar":
                # 处理K线数据
                bar: BarData = data
                self._on_bar(bar)
        except Exception as e:
            print(f"处理RPC回调失败: {e}")

    def _on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        with self._lock:
            # 更新缓存
            self._tick_cache[tick.vt_symbol] = tick
            self._tick_count += 1
            self._last_tick_time = datetime.now()

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

    def _on_bar(self, bar: BarData) -> None:
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


class CustomRpcClient(RpcClient):
    """自定义RPC客户端

    继承自vnpy.rpc.RpcClient，添加可配置的callback功能。
    """

    def __init__(self):
        """初始化"""
        super().__init__()
        self.callback = None

    def run(self) -> None:
        """运行RPC客户端循环"""
        from vnpy.rpc.common import HEARTBEAT_TOLERANCE
        import zmq

        pull_tolerance: int = HEARTBEAT_TOLERANCE * 1000

        while self._active:
            if not self._socket_sub.poll(pull_tolerance):
                self.on_disconnected()
                continue

            # Receive data from subscribe socket
            topic, data = self._socket_sub.recv_pyobj(flags=zmq.NOBLOCK)

            if topic == "heartbeat":
                self._last_received_ping = data
            else:
                # Process data by callable function
                if self.callback:
                    self.callback(topic, data)

        # Close socket
        self._socket_req.close()
        self._socket_sub.close()
