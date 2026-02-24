"""
WebSocket事件定义

定义WebSocket通信中使用的事件类型和数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """WebSocket事件类型"""

    # 订阅相关
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

    # 心跳
    PING = "ping"
    PONG = "pong"

    # 行情推送
    MARKET_TICK = "market_tick"
    MARKET_BAR = "market_bar"

    # 交易推送
    TRADE_ORDER = "trade_order"
    TRADE_TRADE = "trade_trade"
    TRADE_POSITION = "trade_position"
    TRADE_ACCOUNT = "trade_account"

    # 策略推送
    STRATEGY_STATUS = "strategy_status"
    STRATEGY_LOG = "strategy_log"
    STRATEGY_SIGNAL = "strategy_signal"

    # 告警推送
    ALERT = "alert"

    # 错误
    ERROR = "error"


@dataclass
class WebSocketEvent:
    """WebSocket事件数据结构"""

    type: EventType
    data: Dict[str, Any]
    topic: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }

        if self.topic:
            result["topic"] = self.topic

        if self.request_id:
            result["request_id"] = self.request_id

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketEvent":
        """从字典创建"""
        event_type = EventType(data.get("type", "error"))

        return cls(
            type=event_type,
            data=data.get("data", {}),
            topic=data.get("topic"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            request_id=data.get("request_id"),
        )


@dataclass
class MarketTickData:
    """行情Tick数据"""

    symbol: str
    exchange: str
    vt_symbol: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    turnover: float
    bid_price_1: float
    ask_price_1: float
    bid_volume_1: float
    ask_volume_1: float
    datetime: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "vt_symbol": self.vt_symbol,
            "last_price": self.last_price,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "volume": self.volume,
            "turnover": self.turnover,
            "bid_price_1": self.bid_price_1,
            "ask_price_1": self.ask_price_1,
            "bid_volume_1": self.bid_volume_1,
            "ask_volume_1": self.ask_volume_1,
            "datetime": self.datetime,
        }


@dataclass
class TradeOrderData:
    """委托数据"""

    vt_orderid: str
    symbol: str
    exchange: str
    vt_symbol: str
    direction: str
    order_type: str
    volume: float
    traded: float
    price: float
    status: str
    order_time: str
    cancel_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "vt_orderid": self.vt_orderid,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "vt_symbol": self.vt_symbol,
            "direction": self.direction,
            "order_type": self.order_type,
            "volume": self.volume,
            "traded": self.traded,
            "price": self.price,
            "status": self.status,
            "order_time": self.order_time,
            "cancel_time": self.cancel_time,
        }


@dataclass
class StrategyStatusData:
    """策略状态数据"""

    name: str
    class_name: str
    vt_symbol: str
    status: str
    params: Dict[str, Any]
    var_names: list[str]
    var_values: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "class_name": self.class_name,
            "vt_symbol": self.vt_symbol,
            "status": self.status,
            "params": self.params,
            "var_names": self.var_names,
            "var_values": self.var_values,
        }


@dataclass
class AlertData:
    """告警数据"""

    alert_id: str
    title: str
    message: str
    severity: str
    priority: str
    source: str
    timestamp: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "priority": self.priority,
            "source": self.source,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
        }
