"""
RPC QMT数据适配器

通过RPC连接到Windows服务器上的QMT服务，实现跨平台数据访问。
适用于Mac/Linux客户端访问Windows上的QMT数据。
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, date, time
from threading import Thread, Event, Lock
from collections import defaultdict
from enum import Enum
import logging

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.event import EventEngine
from vnpy.rpc import RpcClient

from vnpy_china_config.logging_config import get_logger
from .base import BaseDataAdapter

logger = get_logger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


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
            logger.info(f"RPC QMT适配器已连接: {self.req_address}")
            return True

        except Exception as e:
            logger.error(f"RPC QMT连接失败: {e}", exc_info=True)
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

    def get_connection_status(self) -> Dict[str, Any]:
        """获取RPC连接状态

        Returns:
            连接状态信息字典，包含：
            - state: 连接状态
            - connected: 是否已连接
            - time_since_heartbeat_ms: 距离上次心跳的时间（毫秒）
            - is_timeout: 是否超时
        """
        if not self._rpc_client:
            return {
                "state": "not_initialized",
                "connected": False,
            }

        return self._rpc_client.connection_info

    def is_healthy(self) -> bool:
        """检查连接是否健康

        Returns:
            bool: True表示连接健康，False表示异常
        """
        if not self._connected:
            return False

        if not self._rpc_client:
            return False

        info = self._rpc_client.connection_info
        return not info.get("is_timeout", True)

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

        策略：
        - 交易时段：返回空列表，避免干扰实时数据，让系统 fallback 到 Tushare
        - 盘后时段：通过 RPC 调用 QMT 网关的 query_history 方法获取历史数据

        这样设计的原因：
        1. QMT 在交易时段需要处理实时行情，不宜进行大量历史数据查询
        2. 盘后时段可以充分利用 QMT 的历史数据补充功能
        3. Tushare 作为备用数据源，随时可用
        """

        # 检查是否在交易时段
        if self._is_trading_time():
            logger.debug(
                f"当前处于交易时段，RPC QMT 跳过历史数据查询 ({symbol})。"
                "系统将使用 Tushare 数据源。"
            )
            return []

        # 盘后时段：尝试通过 RPC 获取历史数据
        if not self._connected or not self._rpc_client:
            return []

        try:
            # 调用远程 RPC 的 query_history 方法
            # VeighNa RPC 服务会自动将请求转发到 QMT 网关

            # 去除 symbol 的交易所后缀（QMT 网关期望纯代码）
            # 例如：将 "0700.SHHK" 转换为 "0700"
            clean_symbol = symbol.split(".")[0] if "." in symbol else symbol

            # 创建 HistoryRequest 对象
            from vnpy.trader.object import HistoryRequest
            req = HistoryRequest(
                symbol=clean_symbol,
                exchange=exchange,
                start=start,
                end=end,
                interval=interval
            )

            # MainEngine.query_history 需要 (req, gateway_name) 两个参数
            result = self._rpc_client.query_history(req, "QMT", timeout=60000)

            # 成功获取数据后更新心跳时间戳（防止心跳超时）
            if result:
                from time import time as current_time
                self._last_heartbeat_ms = int(current_time() * 1000)

            return result if result else []

        except Exception as e:
            error_msg = str(e)

            # 错误分类：不同错误类型使用不同日志级别
            if "Operation cannot be accomplished in current state" in error_msg:
                # QMT 不支持的股票代码（如新上市港股）
                logger.debug(
                    f"QMT 不支持该股票代码 ({symbol}.{exchange.value})，"
                    f"可能是新上市股票或数据源未覆盖。系统将使用 Tushare。"
                )
            elif "timeout" in error_msg.lower() or "超时" in error_msg:
                logger.warning(f"RPC QMT 查询超时 ({symbol})，系统将使用 Tushare")
            elif "连接" in error_msg or "connect" in error_msg.lower():
                logger.warning(f"RPC QMT 连接异常 ({symbol})，系统将使用 Tushare")
            else:
                logger.warning(f"RPC QMT 获取历史数据失败 ({symbol}): {e}，系统将使用 Tushare")

            return []

    def _is_trading_time(self) -> bool:
        """判断是否在交易时段

        A 股交易时段：
        - 上午：9:30 - 11:30
        - 下午：13:00 - 15:00

        Returns:
            True 表示在交易时段，False 表示盘后
        """
        from datetime import time

        now = datetime.now().time()
        weekday = datetime.now().weekday()

        # 周末不交易
        if weekday >= 5:  # 5=周六, 6=周日
            return False

        # 上午时段：9:30 - 11:30
        morning_start = time(9, 30)
        morning_end = time(11, 30)

        # 下午时段：13:00 - 15:00
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)

        # 判断是否在交易时段
        is_morning = morning_start <= now <= morning_end
        is_afternoon = afternoon_start <= now <= afternoon_end

        return is_morning or is_afternoon

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
            logger.error(f"RPC订阅失败: {e}", exc_info=True)
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
            logger.error(f"RPC取消订阅失败: {e}", exc_info=True)
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
            logger.error(f"处理RPC回调失败: {e}", exc_info=True)

    def _on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        with self._lock:
            # 增强Tick数据，添加A股特有字段
            self._enhance_tick_data(tick)

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
                    logger.error(f"回调执行失败: {e}", exc_info=True)

            # 发布事件
            if self.event_engine:
                self.event_engine.put(tick)

    def _enhance_tick_data(self, tick: TickData) -> None:
        """增强Tick数据，添加A股特有字段

        添加字段：
        - turnover: 成交额
        - volume_ratio: 量比
        - change_pct: 涨跌幅
        - avg_price: 分时均价
        """
        # 成交额 = 成交量 * 最新价
        if not hasattr(tick, 'turnover') or tick.turnover == 0:
            turnover = tick.volume * tick.last_price
            setattr(tick, 'turnover', turnover)

        # 涨跌幅 = (最新价 - 昨收) / 昨收 * 100
        if not hasattr(tick, 'change_pct'):
            if tick.pre_close and tick.pre_close > 0:
                change_pct = (tick.last_price - tick.pre_close) / tick.pre_close * 100
                setattr(tick, 'change_pct', change_pct)
            else:
                setattr(tick, 'change_pct', 0.0)

        # 分时均价 = 成交额 / 成交量
        if not hasattr(tick, 'avg_price'):
            if tick.volume > 0:
                avg_price = getattr(tick, 'turnover', 0) / tick.volume
                setattr(tick, 'avg_price', avg_price)
            else:
                setattr(tick, 'avg_price', tick.last_price)

        # 量比需要累积数据，暂时设为1.0
        if not hasattr(tick, 'volume_ratio'):
            setattr(tick, 'volume_ratio', 1.0)

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

    # ========== 板块数据 ==========

    def get_sector_list(self) -> List:
        """获取板块列表

        通过RPC调用QMT服务获取板块列表。
        如果RPC调用失败，返回硬编码的板块列表作为fallback。
        """
        # 首先尝试RPC调用
        try:
            if self._rpc_client and self._connected:
                result = self._rpc_client.call("get_sector_list")
                if result:
                    from ..models.sector import SectorData
                    return [SectorData.from_dict(d) if isinstance(d, dict) else d for d in result]
        except Exception as e:
            pass  # Fallback到硬编码列表

        # Fallback: 返回硬编码的申万行业板块
        try:
            from ..models.sector import SectorData

            sector_list = []
            sw_sectors = {
                "801010": "农林牧渔",
                "801020": "采掘",
                "801030": "化工",
                "801040": "钢铁",
                "801050": "有色金属",
                "801080": "电子",
                "801110": "家用电器",
                "801120": "食品饮料",
                "801130": "纺织服装",
                "801140": "轻工制造",
                "801150": "医药生物",
                "801160": "公用事业",
                "801170": "交通运输",
                "801180": "房地产",
                "801200": "商业贸易",
                "801210": "休闲服务",
                "801230": "综合",
                "801710": "建筑材料",
                "801720": "建筑装饰",
                "801730": "电气设备",
                "801740": "国防军工",
                "801750": "计算机",
                "801760": "传媒",
                "801770": "通信",
                "801780": "银行",
                "801790": "非银金融",
                "801880": "汽车",
                "801890": "机械设备",
            }

            for code, name in sw_sectors.items():
                sector = SectorData(
                    sector_code=code,
                    sector_name=name,
                    trade_date=datetime.now().date(),
                    change_pct=0.0,
                )
                sector_list.append(sector)

            return sector_list

        except Exception as e:
            logger.error(f"获取板块列表失败: {e}", exc_info=True)
            return []

    def get_sector_index(
        self,
        sector_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取板块指数数据

        通过RPC调用QMT服务获取板块指数。

        Args:
            sector_code: 板块代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        """
        try:
            if self._rpc_client:
                result = self._rpc_client.call("get_sector_index", sector_code, start_date, end_date)
                if result:
                    return [BarData(**d) if isinstance(d, dict) else d for d in result]
            return []
        except Exception as e:
            logger.error(f"RPC获取板块指数失败: {e}", exc_info=True)
            return []

    # ========== 港股通数据 ==========

    def get_hk_sh_symbols(self, date: str = None) -> List[str]:
        """获取沪港通标的列表

        通过RPC调用QMT服务获取沪港通可交易的港股列表。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SHHK", "2318.SHHK"]）

        Examples:
            >>> adapter = RpcQmtDataAdapter()
            >>> adapter.connect()
            >>> symbols = adapter.get_hk_sh_symbols()
            >>> print(symbols[:5])  # ['0700.SHHK', '09988.SHHK', ...]
        """
        if not self._connected or not self._rpc_client:
            logger.warning("RPC QMT 未连接，无法获取沪港通标的列表")
            return []

        try:
            result = self._rpc_client.call("get_hk_sh_symbols", date)
            if result:
                return result
            return []
        except Exception as e:
            logger.error(f"RPC获取沪港通标的列表失败: {e}", exc_info=True)
            return []

    def get_hk_sz_symbols(self, date: str = None) -> List[str]:
        """获取深港通标的列表

        通过RPC调用QMT服务获取深港通可交易的港股列表。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SZHK", "2318.SZHK"]）

        Examples:
            >>> adapter = RpcQmtDataAdapter()
            >>> adapter.connect()
            >>> symbols = adapter.get_hk_sz_symbols()
            >>> print(symbols[:5])  # ['0700.SZHK', '09988.SZHK', ...]
        """
        if not self._connected or not self._rpc_client:
            logger.warning("RPC QMT 未连接，无法获取深港通标的列表")
            return []

        try:
            result = self._rpc_client.call("get_hk_sz_symbols", date)
            if result:
                return result
            return []
        except Exception as e:
            logger.error(f"RPC获取深港通标的列表失败: {e}", exc_info=True)
            return []


class CustomRpcClient(RpcClient):
    """自定义RPC客户端

    继承自vnpy.rpc.RpcClient，添加可配置的callback功能。
    """

    # 心跳配置常量（毫秒）
    HEARTBEAT_TOLERANCE_MS = 30000  # 30秒
    POLL_INTERVAL_MS = 1000
    FAST_POLL_INTERVAL_MS = 100
    WARNING_COOLDOWN_MS = 60000  # 60秒（减少日志输出频率）

    def __init__(self):
        """初始化"""
        super().__init__()
        self.callback = None

        # 心跳时间跟踪（毫秒）
        self._last_heartbeat_ms: int = 0
        self._last_warning_ms: int = 0

        # 连接状态
        self._connection_state: ConnectionState = ConnectionState.DISCONNECTED

    @property
    def connection_info(self) -> Dict[str, Any]:
        """返回连接状态信息（用于调试）"""
        return {
            "state": self._connection_state.value,
            "last_heartbeat_ms": self._last_heartbeat_ms,
            "last_warning_ms": self._last_warning_ms,
            "active": getattr(self, "_active", False),
        }

    def _check_heartbeat(self, current_ms: int) -> bool:
        """检查心跳是否正常

        Args:
            current_ms: 当前时间（毫秒）

        Returns:
            True 表示心跳正常，False 表示超时
        """
        if self._last_heartbeat_ms == 0:
            self._last_heartbeat_ms = current_ms
            return True

        time_since_heartbeat = current_ms - self._last_heartbeat_ms
        return time_since_heartbeat <= self.HEARTBEAT_TOLERANCE_MS

    def _handle_disconnection(self, current_ms: int) -> None:
        """处理连接断开事件（带冷却时间）

        Args:
            current_ms: 当前时间（毫秒）
        """
        time_since_warning = current_ms - self._last_warning_ms
        if time_since_warning >= self.WARNING_COOLDOWN_MS:
            self._last_warning_ms = current_ms
            logger.debug(f"RPC心跳超时，已触发断线处理。当前状态: {self.connection_info}")
            self.on_disconnected()

    def run(self) -> None:
        """运行RPC客户端循环"""
        from time import time as current_time
        import zmq

        # 设置连接状态为已连接
        self._connection_state = ConnectionState.CONNECTED

        while self._active:
            # 获取当前时间（秒）并转换为毫秒
            now = current_time()
            current_ms = int(now * 1000)

            # 检查心跳是否正常
            if not self._check_heartbeat(current_ms):
                self._handle_disconnection(current_ms)

            # 计算轮询超时时间
            if self._last_heartbeat_ms > 0:
                time_since_heartbeat = current_ms - self._last_heartbeat_ms
                poll_timeout = min(self.POLL_INTERVAL_MS, self.HEARTBEAT_TOLERANCE_MS - time_since_heartbeat)
                poll_timeout = max(poll_timeout, self.FAST_POLL_INTERVAL_MS)
            else:
                poll_timeout = self.POLL_INTERVAL_MS

            if not self._socket_sub.poll(poll_timeout):
                continue

            # Receive data from subscribe socket
            try:
                topic, data = self._socket_sub.recv_pyobj(flags=zmq.NOBLOCK)

                # 收到任何消息都更新心跳时间戳
                self._last_heartbeat_ms = int(current_time() * 1000)

                if topic == "heartbeat":
                    pass  # 心跳消息
                else:
                    # Process data by callable function
                    if self.callback:
                        self.callback(topic, data)
            except zmq.ZMQError as e:
                # 接收错误，忽略并继续
                pass

        # 关闭连接时设置状态
        self._connection_state = ConnectionState.DISCONNECTED

        # Close socket
        self._socket_req.close()
        self._socket_sub.close()
