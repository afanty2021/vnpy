# Web监控系统设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-012
> 优先级：P3
> 预计工时：8人天

---

## 1. 设计目标

构建Web监控与远程控制模块：

1. **Web界面**：实时行情、持仓查询、交易记录、策略状态
2. **远程控制**：策略启停、参数调整、手动交易、紧急停止
3. **移动端支持**：响应式设计、移动端告警、简化界面

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Web监控系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│  【前端层】                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Vue.js     │  │   React      │  │   移动端    │        │
│  │ (Web界面)    │  │  (Web界面)   │  │   (响应式)  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【API网关层】                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  REST API    │  │  WebSocket   │  │   认证中间件 │        │
│  │  (HTTP接口)  │  │  (实时推送)  │  │   (JWT/Token)│        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【业务服务层】                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  MarketSvc  │  │   TradeSvc   │  │  StrategySvc │        │
│  │  (行情服务)  │  │  (交易服务)  │  │  (策略服务)  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【RPC通信层】                                                  │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │  RpcClient   │  │  Connection  │                          │
│  │  (RPC客户端) │  │  Manager     │                          │
│  └──────────────┘  └──────────────┘                          │
├─────────────────────────────────────────────────────────────────┤
│  【VeighNa核心】                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  MainEngine  │  │   Gateway    │  │    Apps     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_web/
├── __init__.py
├── server/
│   ├── __init__.py
│   ├── app.py                 # FastAPI应用
│   ├── config.py              # 配置管理
│   └── middleware.py         # 中间件
├── api/
│   ├── __init__.py
│   ├── market.py             # 行情API
│   ├── trade.py              # 交易API
│   ├── position.py           # 持仓API
│   ├── strategy.py           # 策略API
│   └── auth.py               # 认证API
├── websocket/
│   ├── __init__.py
│   ├── manager.py            # WebSocket管理器
│   ├── handlers.py           # 消息处理器
│   └── events.py             # 事件定义
├── rpc/
│   ├── __init__.py
│   ├── client.py             # RPC客户端封装
│   └── connection.py          # 连接管理
├── services/
│   ├── __init__.py
│   ├── market_service.py     # 行情服务
│   ├── trade_service.py      # 交易服务
│   └── strategy_service.py    # 策略服务
└── frontend/
    ├── index.html
    ├── static/
    │   ├── css/
    │   ├── js/
    │   └── images/
    └── templates/
        └── dashboard.html
```

---

## 3. 核心类设计

### 3.1 RPC客户端封装

```python
import json
from typing import Any, Dict, Optional, Callable
from datetime import datetime
import threading


class RpcClientWrapper:
    """RPC客户端封装类"""

    def __init__(self, rep_address: str = "tcp://127.0.0.1:2014"):
        self.rep_address = rep_address
        self.pub_address = "tcp://127.0.0.1:4102"
        self.rpc_client: Optional[Any] = None
        self.connected = False
        self._callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def connect(self):
        """连接到RPC服务"""
        from vnpy.rpc import RpcClient

        self.rpc_client = RpcClient()
        self.rpc_client.connect(self.rep_address, self.pub_address)
        self.rpc_client.register(self._handle_push)
        self.connected = True

    def _handle_push(self, topic: str, data: Any):
        """处理推送消息"""
        with self._lock:
            callback = self._callbacks.get(topic)
            if callback:
                callback(data)

    def subscribe(self, topic: str, callback: Callable):
        """订阅主题"""
        with self._lock:
            self._callbacks[topic] = callback

    def call(self, method: str, **kwargs) -> Any:
        """RPC调用"""
        if not self.connected:
            raise ConnectionError("RPC not connected")

        request = {
            "method": method,
            "params": kwargs,
            "timestamp": datetime.now().isoformat()
        }

        response = self.rpc_client.call(json.dumps(request))
        return json.loads(response)

    def get_account(self) -> Dict:
        """获取账户信息"""
        return self.call("get_account")

    def get_position(self, vt_symbol: str = None) -> Dict:
        """获取持仓信息"""
        return self.call("get_position", vt_symbol=vt_symbol)

    def get_orders(self, vt_orderid: str = None) -> List[Dict]:
        """获取委托信息"""
        return self.call("get_orders", vt_orderid=vt_orderid)

    def send_order(self, vt_symbol: str, direction: str,
                   volume: float, price: float = 0,
                   order_type: str = "limit") -> str:
        """发送委托"""
        return self.call("send_order",
                         vt_symbol=vt_symbol,
                         direction=direction,
                         volume=volume,
                         price=price,
                         order_type=order_id)

    def cancel_order(self, vt_orderid: str):
        """撤销委托"""
        return self.call("cancel_order", vt_orderid=vt_orderid)

    def start_strategy(self, strategy_name: str):
        """启动策略"""
        return self.call("start_strategy", strategy_name=strategy_name)

    def stop_strategy(self, strategy_name: str):
        """停止策略"""
        return self.call("stop_strategy", strategy_name=strategy_name)
```

### 3.2 WebSocket连接管理器

```python
from typing import Dict, Set, List
from datetime import datetime
import asyncio
import json


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 连接集合
        self.active_connections: Set[Any] = set()

        # 主题订阅关系
        self.subscriptions: Dict[str, Set[Any]] = {
            "market": set(),
            "trade": set(),
            "position": set(),
            "order": set(),
            "strategy": set(),
            "account": set(),
        }

        # 连接元数据
        self.connection_info: Dict[Any, Dict] = {}

    async def connect(self, websocket: Any, client_id: str):
        """新连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now(),
            "subscriptions": set()
        }

    def disconnect(self, websocket: Any):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # 清理订阅
        info = self.connection_info.pop(websocket, {})
        for topic in info.get("subscriptions", []):
            if topic in self.subscriptions:
                self.subscriptions[topic].discard(websocket)

    def subscribe(self, websocket: Any, topic: str):
        """订阅主题"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()

        self.subscriptions[topic].add(websocket)

        if websocket in self.connection_info:
            self.connection_info[websocket]["subscriptions"].add(topic)

    def unsubscribe(self, websocket: Any, topic: str):
        """取消订阅"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(websocket)

    async def broadcast(self, topic: str, message: Dict):
        """广播消息到订阅者"""
        if topic not in self.subscriptions:
            return

        message["topic"] = topic
        message["timestamp"] = datetime.now().isoformat()

        for connection in self.subscriptions[topic]:
            try:
                await connection.send_json(message)
            except Exception:
                # 移除无效连接
                self.disconnect(connection)

    async def send_personal(self, websocket: Any, message: Dict):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)
```

### 3.3 行情服务

```python
from typing import Dict, List, Optional
from datetime import datetime
from collections import deque


class MarketService:
    """行情服务"""

    def __init__(self, rpc_client: RpcClientWrapper):
        self.rpc_client = rpc_client

        # 实时行情缓存
        self.tick_cache: Dict[str, Dict] = {}

        # K线数据缓存
        self.bar_cache: Dict[str, deque] = {}

        # 订阅的合约列表
        self.subscribed_symbols: Set[str] = set()

    def subscribe(self, vt_symbol: str):
        """订阅行情"""
        self.subscribed_symbols.add(vt_symbol)
        # 通过RPC订阅行情
        self.rpc_client.call("subscribe", vt_symbol=vt_symbol)

    def unsubscribe(self, vt_symbol: str):
        """取消订阅"""
        self.subscribed_symbols.discard(vt_symbol)
        self.rpc_client.call("unsubscribe", vt_symbol=vt_symbol)

    def get_tick(self, vt_symbol: str) -> Optional[Dict]:
        """获取最新行情"""
        return self.tick_cache.get(vt_symbol)

    def get_history_bars(
        self,
        vt_symbol: str,
        interval: str,
        count: int = 100
    ) -> List[Dict]:
        """获取历史K线"""
        return self.rpc_client.call(
            "get_history_bars",
            vt_symbol=vt_symbol,
            interval=interval,
            count=count
        )

    def update_tick(self, tick_data: Dict):
        """更新行情数据"""
        vt_symbol = tick_data.get("vt_symbol")
        if vt_symbol:
            self.tick_cache[vt_symbol] = {
                **tick_data,
                "update_time": datetime.now().isoformat()
            }

    def format_tick(self, vt_symbol: str) -> Optional[Dict]:
        """格式化行情数据给前端"""
        tick = self.tick_cache.get(vt_symbol)
        if not tick:
            return None

        return {
            "symbol": tick.get("symbol"),
            "exchange": tick.get("exchange"),
            "last_price": tick.get("last_price"),
            "open_price": tick.get("open_price"),
            "high_price": tick.get("high_price"),
            "low_price": tick.get("low_price"),
            "volume": tick.get("volume"),
            "turnover": tick.get("turnover"),
            "bid_price_1": tick.get("bid_price_1"),
            "ask_price_1": tick.get("ask_price_1"),
            "bid_volume_1": tick.get("bid_volume_1"),
            "ask_volume_1": tick.get("ask_volume_1"),
            "update_time": tick.get("update_time")
        }
```

### 3.4 交易服务

```python
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """委托类型"""
    LIMIT = "limit"          # 限价委托
    MARKET = "market"        # 市价委托
    STOP = "stop"            # 止损委托
    FAK = "fak"             # 五档即成剩余撤
    FOK = "fok"             # 五档即成全撤


class TradeService:
    """交易服务"""

    def __init__(self, rpc_client: RpcClientWrapper):
        self.rpc_client = rpc_client

        # 委托缓存
        self.order_cache: Dict[str, Dict] = {}

        # 成交缓存
        self.trade_cache: Dict[str, Dict] = {}

    def send_order(
        self,
        vt_symbol: str,
        direction: str,
        volume: float,
        price: float = 0,
        order_type: str = "limit"
    ) -> str:
        """发送委托"""
        return self.rpc_client.send_order(
            vt_symbol=vt_symbol,
            direction=direction,
            volume=volume,
            price=price,
            order_type=order_type
        )

    def cancel_order(self, vt_orderid: str):
        """撤销委托"""
        return self.rpc_client.cancel_order(vt_orderid)

    def get_orders(self, vt_orderid: str = None) -> List[Dict]:
        """查询委托"""
        return self.rpc_client.get_orders(vt_orderid)

    def get_trades(self, vt_orderid: str = None) -> List[Dict]:
        """查询成交"""
        return self.rpc_client.get_trades(vt_orderid)

    def get_account(self) -> Dict:
        """获取账户资金"""
        return self.rpc_client.get_account()

    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        return self.rpc_client.get_position()

    def format_order(self, order: Dict) -> Dict:
        """格式化委托给前端"""
        return {
            "vt_orderid": order.get("vt_orderid"),
            "symbol": order.get("symbol"),
            "exchange": order.get("exchange"),
            "direction": order.get("direction"),
            "order_type": order.get("order_type"),
            "volume": order.get("volume"),
            "traded": order.get("traded"),
            "price": order.get("price"),
            "status": order.get("status"),
            "order_time": order.get("order_time"),
            "cancel_time": order.get("cancel_time")
        }

    def format_position(self, position: Dict) -> Dict:
        """格式化持仓给前端"""
        return {
            "vt_symbol": position.get("vt_symbol"),
            "symbol": position.get("symbol"),
            "exchange": position.get("exchange"),
            "direction": position.get("direction"),
            "volume": position.get("volume"),
            "yd_volume": position.get("yd_volume"),
            "frozen": position.get("frozen"),
            "price": position.get("price"),
            "pnl": position.get("pnl"),
            "update_time": position.get("update_time")
        }
```

### 3.5 策略服务

```python
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class StrategyStatus(Enum):
    """策略状态"""
    RUNNING = "running"
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    EXCEPTION = "exception"


class StrategyService:
    """策略服务"""

    def __init__(self, rpc_client: RpcClientWrapper):
        self.rpc_client = rpc_client

        # 策略状态缓存
        self.strategy_status: Dict[str, Dict] = {}

        # 策略参数缓存
        self.strategy_params: Dict[str, Dict] = {}

    def start_strategy(self, strategy_name: str) -> bool:
        """启动策略"""
        result = self.rpc_client.start_strategy(strategy_name)
        if result.get("success"):
            self.strategy_status[strategy_name] = {
                "status": StrategyStatus.RUNNING.value,
                "start_time": datetime.now().isoformat()
            }
        return result.get("success", False)

    def stop_strategy(self, strategy_name: str) -> bool:
        """停止策略"""
        result = self.rpc_client.stop_strategy(strategy_name)
        if result.get("success"):
            self.strategy_status[strategy_name] = {
                "status": StrategyStatus.STOPPED.value,
                "stop_time": datetime.now().isoformat()
            }
        return result.get("success", False)

    def get_strategy_status(self, strategy_name: str) -> Optional[Dict]:
        """获取策略状态"""
        return self.strategy_status.get(strategy_name)

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略"""
        return self.rpc_client.call("get_all_strategies")

    def set_strategy_param(
        self,
        strategy_name: str,
        param_name: str,
        value: Any
    ) -> bool:
        """设置策略参数"""
        result = self.rpc_client.call(
            "set_strategy_param",
            strategy_name=strategy_name,
            param_name=param_name,
            value=value
        )

        if result.get("success"):
            if strategy_name not in self.strategy_params:
                self.strategy_params[strategy_name] = {}
            self.strategy_params[strategy_name][param_name] = value

        return result.get("success", False)

    def get_strategy_params(self, strategy_name: str) -> Dict:
        """获取策略参数"""
        return self.strategy_params.get(strategy_name, {})

    def format_strategy(self, strategy: Dict) -> Dict:
        """格式化策略给前端"""
        return {
            "name": strategy.get("name"),
            "class_name": strategy.get("class_name"),
            "vt_symbol": strategy.get("vt_symbol"),
            "status": strategy.get("status"),
            "params": strategy.get("params", {}),
            "var_names": strategy.get("var_names", []),
            "var_values": strategy.get("var_values", {})
        }
```

### 3.6 FastAPI应用

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json

from .websocket.manager import ConnectionManager
from .rpc.client import RpcClientWrapper
from .services.market_service import MarketService
from .services.trade_service import TradeService
from .services.strategy_service import StrategyService


# 创建应用
app = FastAPI(title="VeighNa Web API")

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
rpc_client = RpcClientWrapper()
connection_manager = ConnectionManager()
market_service = MarketService(rpc_client)
trade_service = TradeService(rpc_client)
strategy_service = StrategyService(rpc_client)


# WebSocket端点
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接"""
    await connection_manager.connect(websocket, client_id)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            await handle_websocket_message(websocket, message)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, message: Dict):
    """处理WebSocket消息"""
    msg_type = message.get("type")
    data = message.get("data", {})

    if msg_type == "subscribe":
        # 订阅主题
        topic = data.get("topic")
        connection_manager.subscribe(websocket, topic)

    elif msg_type == "unsubscribe":
        # 取消订阅
        topic = data.get("topic")
        connection_manager.unsubscribe(websocket, topic)

    elif msg_type == "ping":
        # 心跳
        await connection_manager.send_personal(websocket, {
            "type": "pong",
            "timestamp": data.get("timestamp")
        })


# REST API端点

# 行情
@app.get("/api/market/tick/{vt_symbol}")
async def get_tick(vt_symbol: str):
    """获取实时行情"""
    return market_service.format_tick(vt_symbol)


@app.get("/api/market/bars/{vt_symbol}")
async def get_bars(vt_symbol: str, interval: str = "1m", count: int = 100):
    """获取历史K线"""
    bars = market_service.get_history_bars(vt_symbol, interval, count)
    return {"vt_symbol": vt_symbol, "interval": interval, "bars": bars}


# 交易
@app.get("/api/account")
async def get_account():
    """获取账户资金"""
    account = trade_service.get_account()
    return trade_service.format_account(account)


@app.get("/api/positions")
async def get_positions():
    """获取持仓"""
    positions = trade_service.get_positions()
    return [trade_service.format_position(p) for p in positions]


@app.get("/api/orders")
async def get_orders(vt_orderid: str = None):
    """获取委托"""
    orders = trade_service.get_orders(vt_orderid)
    return [trade_service.format_order(o) for o in orders]


@app.post("/api/order/send")
async def send_order(order_req: OrderRequest):
    """发送委托"""
    vt_orderid = trade_service.send_order(
        vt_symbol=order_req.vt_symbol,
        direction=order_req.direction,
        volume=order_req.volume,
        price=order_req.price,
        order_type=order_req.order_type
    )
    return {"vt_orderid": vt_orderid}


@app.post("/api/order/cancel")
async def cancel_order(vt_orderid: str):
    """撤销委托"""
    success = trade_service.cancel_order(vt_orderid)
    return {"success": success}


# 策略
@app.get("/api/strategies")
async def get_strategies():
    """获取所有策略"""
    strategies = strategy_service.get_all_strategies()
    return [strategy_service.format_strategy(s) for s in strategies]


@app.post("/api/strategy/{strategy_name}/start")
async def start_strategy(strategy_name: str):
    """启动策略"""
    success = strategy_service.start_strategy(strategy_name)
    return {"success": success}


@app.post("/api/strategy/{strategy_name}/stop")
async def stop_strategy(strategy_name: str):
    """停止策略"""
    success = strategy_service.stop_strategy(strategy_name)
    return {"success": success}


@app.post("/api/strategy/{strategy_name}/param")
async def set_strategy_param(
    strategy_name: str,
    param_name: str,
    value: Any
):
    """设置策略参数"""
    success = strategy_service.set_strategy_param(
        strategy_name, param_name, value
    )
    return {"success": success}


# 启动时连接RPC
@app.on_event("startup")
async def startup_event():
    rpc_client.connect()


# 关闭时断开RPC
@app.on_event("shutdown")
async def shutdown_event():
    rpc_client.disconnect()
```

### 3.7 请求模型

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Direction(str, Enum):
    """交易方向"""
    LONG = "long"
    SHORT = "short"


class OrderRequest(BaseModel):
    """委托请求"""
    vt_symbol: str
    direction: str
    volume: float
    price: float = 0
    order_type: str = "limit"


class CancelRequest(BaseModel):
    """撤单请求"""
    vt_orderid: str


class StrategyControlRequest(BaseModel):
    """策略控制请求"""
    strategy_name: str
    action: str  # start/stop


class ParamUpdateRequest(BaseModel):
    """参数更新请求"""
    strategy_name: str
    param_name: str
    value: Any
```

---

## 4. 前端设计

### 4.1 页面结构

```
┌─────────────────────────────────────────────────────────┐
│                      Dashboard                          │
├────────────┬────────────────────────────────────────────┤
│            │  ┌────────────────────────────────────────┐ │
│  侧边栏     │  │           实时行情展示                │ │
│            │  │  (行情卡片/涨跌幅排序/K线图)          │ │
│ - 仪表盘    │  └────────────────────────────────────────┘ │
│ - 行情     │  ┌────────────────────────────────────────┐ │
│ - 交易     │  │           账户资产概览                 │ │
│ - 持仓     │  │  (总资产/持仓/可用资金/今日盈亏)      │ │
│ - 策略     │  └────────────────────────────────────────┘ │
│ - 设置     │  ┌────────────────────────────────────────┐ │
│            │  │           策略状态监控                  │ │
│            │  │  (运行状态/信号/持仓/盈亏)             │ │
│            │  └────────────────────────────────────────┘ │
└────────────┴────────────────────────────────────────────┘
```

### 4.2 核心组件

```javascript
// 行情卡片组件
const MarketCard = {
  props: ['vtSymbol'],
  data() {
    return {
      tick: null
    }
  },
  template: `
    <div class="market-card">
      <div class="symbol">{{ vtSymbol }}</div>
      <div class="price" :class="priceClass">
        {{ tick.lastPrice }}
      </div>
      <div class="change" :class="changeClass">
        {{ tick.change }}%
      </div>
    </div>
  `,
  computed: {
    priceClass() {
      return this.tick?.change >= 0 ? 'up' : 'down'
    },
    changeClass() {
      return this.tick?.change >= 0 ? 'up' : 'down'
    }
  }
}

// WebSocket连接管理
class WebSocketClient {
  constructor(url) {
    this.url = url
    this.ws = null
    this.subscriptions = new Set()
    this.reconnectInterval = 3000
  }

  connect() {
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.resubscribe()
    }

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this.handleMessage(message)
    }

    this.ws.onclose = () => {
      setTimeout(() => this.connect(), this.reconnectInterval)
    }
  }

  subscribe(topic) {
    this.subscriptions.add(topic)
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        topic: topic
      }))
    }
  }

  handleMessage(message) {
    const topic = message.topic
    // 分发到对应处理器
    EventBus.emit(topic, message.data)
  }
}
```

---

## 5. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和RPC客户端封装 | 1人天 |
| 2 | 实现WebSocket管理器 | 1人天 |
| 3 | 实现业务服务层 | 2人天 |
| 4 | 实现REST API | 1.5人天 |
| 5 | 开发Web前端界面 | 1.5人天 |
| 6 | 集成测试 | 1人天 |
| 合计 | | **8人天** |

---

## 6. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
