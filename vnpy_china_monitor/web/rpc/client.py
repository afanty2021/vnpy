"""
RPC客户端封装

提供到VeighNa RPC服务的连接封装，包括：
- 自动重连机制
- 请求超时控制
- 错误处理
- 事件订阅
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RpcConnectionState(Enum):
    """RPC连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class RpcRequest:
    """RPC请求数据结构"""
    method: str
    params: Dict[str, Any]
    timestamp: str
    request_id: str


@dataclass
class RpcResponse:
    """RPC响应数据结构"""
    success: bool
    data: Any
    error: Optional[str]
    timestamp: str
    request_id: str


class RpcClientWrapper:
    """RPC客户端封装类

    提供到VeighNa RPC服务的连接封装，支持：
    - 自动重连
    - 请求超时
    - 错误处理
    - 事件订阅
    """

    def __init__(
        self,
        rep_address: str = "tcp://127.0.0.1:2014",
        pub_address: str = "tcp://127.0.0.1:4102",
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        request_timeout: int = 30,
        max_retries: int = 3,
    ):
        """初始化RPC客户端

        Args:
            rep_address: RPC请求地址
            pub_address: RPC发布地址
            auto_reconnect: 是否自动重连
            reconnect_interval: 重连间隔(秒)
            request_timeout: 请求超时(秒)
            max_retries: 最大重试次数
        """
        self.rep_address = rep_address
        self.pub_address = pub_address
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.request_timeout = request_timeout
        self.max_retries = max_retries

        # 连接状态
        self._state: RpcConnectionState = RpcConnectionState.DISCONNECTED
        self._rpc_client: Optional[Any] = None
        self._state_lock = threading.Lock()

        # 事件回调
        self._callbacks: Dict[str, Callable] = {}
        self._callback_lock = threading.Lock()

        # 请求ID生成
        self._request_counter = 0
        self._request_counter_lock = threading.Lock()

        # 重连控制
        self._reconnecting = False
        self._stop_reconnect = False

        logger.info(
            f"RpcClientWrapper initialized: rep_address={rep_address}, "
            f"pub_address={pub_address}, auto_reconnect={auto_reconnect}"
        )

    @property
    def state(self) -> RpcConnectionState:
        """获取连接状态"""
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, value: RpcConnectionState) -> None:
        """设置连接状态"""
        with self._state_lock:
            old_state = self._state
            self._state = value
            if old_state != value:
                logger.info(f"RPC connection state changed: {old_state} -> {value}")

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self.state == RpcConnectionState.CONNECTED

    def _generate_request_id(self) -> str:
        """生成请求ID"""
        with self._request_counter_lock:
            self._request_counter += 1
            return f"{int(time.time() * 1000)}_{self._request_counter}"

    def connect(self) -> bool:
        """连接到RPC服务

        Returns:
            是否连接成功
        """
        if self.connected:
            logger.warning("RPC client already connected")
            return True

        self.state = RpcConnectionState.CONNECTING

        try:
            from vnpy.rpc import RpcClient

            self._rpc_client = RpcClient()
            self._rpc_client.connect(self.rep_address, self.pub_address)

            # 注册推送回调
            self._rpc_client.register(self._handle_push)

            self.state = RpcConnectionState.CONNECTED
            logger.info(f"RPC client connected successfully: {self.rep_address}")

            # 启动重连监听
            if self.auto_reconnect:
                self._start_reconnect_monitor()

            return True

        except Exception as e:
            logger.error(f"RPC client connection failed: {e}")
            self.state = RpcConnectionState.ERROR
            self._rpc_client = None

            # 尝试自动重连
            if self.auto_reconnect:
                self._schedule_reconnect()

            return False

    def disconnect(self) -> None:
        """断开RPC连接"""
        self._stop_reconnect = True

        if self._rpc_client:
            try:
                self._rpc_client.close()
            except Exception as e:
                logger.error(f"Error closing RPC client: {e}")
            finally:
                self._rpc_client = None

        self.state = RpcConnectionState.DISCONNECTED
        logger.info("RPC client disconnected")

    def _handle_push(self, topic: str, data: Any) -> None:
        """处理RPC推送消息

        Args:
            topic: 推送主题
            data: 推送数据
        """
        try:
            # 解析JSON数据
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    pass

            logger.debug(f"RPC push received: topic={topic}, data={data}")

            # 查找并调用回调
            with self._callback_lock:
                callback = self._callbacks.get(topic)

            if callback:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in RPC push callback for topic '{topic}': {e}")

        except Exception as e:
            logger.error(f"Error handling RPC push: {e}")

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """订阅RPC推送主题

        Args:
            topic: 订阅主题
            callback: 回调函数
        """
        with self._callback_lock:
            self._callbacks[topic] = callback
        logger.info(f"Subscribed to RPC topic: {topic}")

    def unsubscribe(self, topic: str) -> None:
        """取消订阅

        Args:
            topic: 订阅主题
        """
        with self._callback_lock:
            self._callbacks.pop(topic, None)
        logger.info(f"Unsubscribed from RPC topic: {topic}")

    def call(self, method: str, **kwargs) -> Any:
        """RPC方法调用

        Args:
            method: RPC方法名
            **kwargs: 方法参数

        Returns:
            RPC调用结果

        Raises:
            ConnectionError: RPC未连接
            TimeoutError: 请求超时
        """
        if not self.connected:
            raise ConnectionError("RPC client not connected")

        request = RpcRequest(
            method=method,
            params=kwargs,
            timestamp=datetime.now().isoformat(),
            request_id=self._generate_request_id(),
        )

        request_data = json.dumps({
            "method": request.method,
            "params": request.params,
            "timestamp": request.timestamp,
            "request_id": request.request_id,
        })

        last_error = None

        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"RPC call (attempt {attempt + 1}): method={method}, params={kwargs}")

                # 发送请求
                response_str = self._rpc_client.call(request_data)

                # 解析响应
                if response_str:
                    response_data = json.loads(response_str) if isinstance(response_str, str) else response_str
                else:
                    response_data = {}

                return response_data

            except Exception as e:
                last_error = e
                logger.warning(
                    f"RPC call failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"method={method}, error={e}"
                )

                # 最后一次尝试失败后才等待
                if attempt < self.max_retries - 1:
                    time.sleep(1)

        # 所有重试都失败
        raise TimeoutError(
            f"RPC call failed after {self.max_retries} attempts: "
            f"method={method}, error={last_error}"
        )

    def _start_reconnect_monitor(self) -> None:
        """启动重连监听线程"""
        def monitor():
            while not self._stop_reconnect:
                time.sleep(5)

                if not self.connected and not self._reconnecting:
                    if self.auto_reconnect:
                        self._schedule_reconnect()

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.info("RPC reconnect monitor started")

    def _schedule_reconnect(self) -> None:
        """调度重连"""
        if self._reconnecting or self._stop_reconnect:
            return

        self._reconnecting = True

        def reconnect():
            while not self._stop_reconnect:
                if self.connected:
                    self._reconnecting = False
                    break

                logger.info(f"Attempting to reconnect RPC in {self.reconnect_interval}s...")
                time.sleep(self.reconnect_interval)

                if self._stop_reconnect:
                    break

                if self.connect():
                    self._reconnecting = False
                    logger.info("RPC reconnection successful")
                    break
                else:
                    logger.warning("RPC reconnection failed, will retry...")

            self._reconnecting = False

        thread = threading.Thread(target=reconnect, daemon=True)
        thread.start()

    # 便捷方法 - 账户相关

    def get_account(self) -> Dict:
        """获取账户信息

        Returns:
            账户信息字典
        """
        return self.call("get_account")

    # 便捷方法 - 持仓相关

    def get_position(self, vt_symbol: Optional[str] = None) -> List[Dict]:
        """获取持仓信息

        Args:
            vt_symbol: 合约代码，None表示所有持仓

        Returns:
            持仓列表
        """
        return self.call("get_position", vt_symbol=vt_symbol)

    # 便捷方法 - 委托相关

    def get_orders(self, vt_orderid: Optional[str] = None) -> List[Dict]:
        """获取委托信息

        Args:
            vt_orderid: 委托ID，None表示所有委托

        Returns:
            委托列表
        """
        return self.call("get_orders", vt_orderid=vt_orderid)

    def send_order(
        self,
        vt_symbol: str,
        direction: str,
        volume: float,
        price: float = 0,
        order_type: str = "limit",
    ) -> str:
        """发送委托

        Args:
            vt_symbol: 合约代码
            direction: 方向（long/short）
            volume: 数量
            price: 价格（0表示市价）
            order_type: 委托类型

        Returns:
            委托ID
        """
        return self.call(
            "send_order",
            vt_symbol=vt_symbol,
            direction=direction,
            volume=volume,
            price=price,
            order_type=order_type,
        )

    def cancel_order(self, vt_orderid: str) -> bool:
        """撤销委托

        Args:
            vt_orderid: 委托ID

        Returns:
            是否成功
        """
        return self.call("cancel_order", vt_orderid=vt_orderid)

    # 便捷方法 - 策略相关

    def start_strategy(self, strategy_name: str) -> bool:
        """启动策略

        Args:
            strategy_name: 策略名称

        Returns:
            是否成功
        """
        return self.call("start_strategy", strategy_name=strategy_name)

    def stop_strategy(self, strategy_name: str) -> bool:
        """停止策略

        Args:
            strategy_name: 策略名称

        Returns:
            是否成功
        """
        return self.call("stop_strategy", strategy_name=strategy_name)

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略

        Returns:
            策略列表
        """
        return self.call("get_all_strategies")

    def set_strategy_param(
        self,
        strategy_name: str,
        param_name: str,
        value: Any,
    ) -> bool:
        """设置策略参数

        Args:
            strategy_name: 策略名称
            param_name: 参数名称
            value: 参数值

        Returns:
            是否成功
        """
        return self.call(
            "set_strategy_param",
            strategy_name=strategy_name,
            param_name=param_name,
            value=value,
        )

    # 便捷方法 - 数据相关

    def get_history_bars(
        self,
        vt_symbol: str,
        interval: str,
        count: int = 100,
    ) -> List[Dict]:
        """获取历史K线

        Args:
            vt_symbol: 合约代码
            interval: K线周期（1m/5m/15m/30m/1h/1d）
            count: 数量

        Returns:
            K线数据列表
        """
        return self.call(
            "get_history_bars",
            vt_symbol=vt_symbol,
            interval=interval,
            count=count,
        )
