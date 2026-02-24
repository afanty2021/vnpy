# Web监控系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-012
> 优先级：P3
> 预计工时：8人天
> 实施周期：2周

---

## 1. 项目概述

### 1.1 需求背景

VeighNa量化交易系统目前主要提供桌面GUI界面，在移动办公和远程监控场景下存在不便。本项目旨在构建一个基于Web的监控与远程控制系统，实现：

- **实时监控**：通过浏览器实时查看行情、持仓、订单、策略状态
- **远程控制**：支持策略启停、参数调整、手动交易、紧急停止
- **移动端支持**：响应式设计，支持手机/平板访问
- **安全性**：JWT认证、权限控制、操作审计

### 1.2 技术选型

| 类别 | 技术方案 | 说明 |
|------|---------|------|
| 后端框架 | FastAPI | 现代异步Python Web框架 |
| WebSocket | FastAPI WebSocket | 实时双向通信 |
| RPC通信 | vnpy.rpc | VeighNa内置RPC服务 |
| 前端框架 | Vue.js 3 | 渐进式JavaScript框架 |
| UI组件 | Element Plus | Vue 3组件库 |
| 图表库 | ECharts | 数据可视化 |
| 认证 | JWT | 无状态认证 |
| 部署 | Docker/Docker Compose | 容器化部署 |

### 1.3 核心目标

1. **功能完整性**：覆盖核心监控和远程控制功能
2. **实时性**：WebSocket推送延迟 < 500ms
3. **易用性**：响应式设计，支持移动端
4. **安全性**：JWT认证 + HTTPS加密
5. **可扩展性**：模块化设计，易于扩展新功能

---

## 2. 实施架构

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web监控系统实施架构                            │
├─────────────────────────────────────────────────────────────────┤
│  【前端层 - vnpy_china_web/frontend】                            │
│  ├── SPA单页应用 (Vue.js 3)                                     │
│  ├── 响应式布局 (Element Plus)                                  │
│  └── 实时图表 (ECharts)                                         │
├─────────────────────────────────────────────────────────────────┤
│  【API层 - vnpy_china_web/api】                                  │
│  ├── REST API (FastAPI路由)                                     │
│  ├── WebSocket (实时推送)                                       │
│  └── 认证中间件 (JWT)                                           │
├─────────────────────────────────────────────────────────────────┤
│  【服务层 - vnpy_china_web/services】                            │
│  ├── MarketService (行情服务)                                   │
│  ├── TradeService (交易服务)                                    │
│  ├── StrategyService (策略服务)                                 │
│  └── AlertService (告警服务)                                    │
├─────────────────────────────────────────────────────────────────┤
│  【RPC层 - vnpy_china_web/rpc】                                  │
│  ├── RpcClientWrapper (RPC封装)                                 │
│  └── ConnectionManager (连接管理)                               │
├─────────────────────────────────────────────────────────────────┤
│  【VeighNa核心】                                                 │
│  ├── MainEngine (主引擎)                                        │
│  ├── RpcService (RPC服务)                                       │
│  └── Apps (策略/数据/风控应用)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_web/
├── __init__.py
├── server/
│   ├── __init__.py
│   ├── app.py                 # FastAPI应用入口
│   ├── config.py              # 配置管理
│   ├── security.py            # 安全认证
│   └── middleware.py          # 中间件
├── api/
│   ├── __init__.py
│   ├── market.py              # 行情API路由
│   ├── trade.py               # 交易API路由
│   ├── position.py            # 持仓API路由
│   ├── strategy.py            # 策略API路由
│   ├── alert.py               # 告警API路由
│   └── auth.py                # 认证API路由
├── websocket/
│   ├── __init__.py
│   ├── manager.py             # 连接管理器
│   ├── handlers.py            # 消息处理器
│   ├── events.py              # 事件定义
│   └── broadcaster.py         # 广播器
├── rpc/
│   ├── __init__.py
│   ├── client.py              # RPC客户端封装
│   ├── connection.py          # 连接管理
│   └── events.py              # RPC事件处理
├── services/
│   ├── __init__.py
│   ├── market_service.py      # 行情业务服务
│   ├── trade_service.py       # 交易业务服务
│   ├── strategy_service.py    # 策略业务服务
│   ├── alert_service.py       # 告警业务服务
│   └── data_service.py        # 数据聚合服务
├── models/
│   ├── __init__.py
│   ├── request.py             # 请求模型
│   ├── response.py            # 响应模型
│   └── events.py              # 事件模型
├── frontend/
│   ├── src/
│   │   ├── main.js            # 入口文件
│   │   ├── App.vue            # 根组件
│   │   ├── router/            # 路由配置
│   │   ├── store/             # 状态管理
│   │   ├── views/             # 页面组件
│   │   │   ├── Dashboard.vue  # 仪表盘
│   │   │   ├── Market.vue     # 行情页面
│   │   │   ├── Trade.vue      # 交易页面
│   │   │   ├── Position.vue   # 持仓页面
│   │   │   ├── Strategy.vue   # 策略页面
│   │   │   └── Settings.vue   # 设置页面
│   │   ├── components/        # 通用组件
│   │   │   ├── MarketCard.vue # 行情卡片
│   │   │   ├── OrderBook.vue  # 订单簿
│   │   │   ├── PositionTable.vue  # 持仓表格
│   │   │   └── ChartCard.vue  # 图表卡片
│   │   └── utils/             # 工具函数
│   │       ├── api.js         # API封装
│   │       ├── websocket.js   # WebSocket封装
│   │       └── auth.js        # 认证工具
│   ├── public/                # 静态资源
│   ├── package.json           # 依赖配置
│   └── vite.config.js         # Vite配置
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API测试
│   ├── test_websocket.py      # WebSocket测试
│   ├── test_services.py       # 服务测试
│   └── test_frontend.py       # 前端测试
├── deployments/
│   ├── Dockerfile             # 后端镜像
│   ├── Dockerfile.frontend    # 前端镜像
│   └── docker-compose.yml     # 编排配置
└── requirements.txt           # Python依赖
```

---

## 3. 实施阶段

### 阶段1：项目基础设施 (1人天)

**目标**：搭建项目骨架和开发环境

**任务列表**：

1. **创建项目结构**
   - 创建vnpy_china_web模块目录
   - 初始化Python包结构
   - 配置开发工具（ruff, mypy）

2. **配置管理**
   - 实现配置加载（YAML/环境变量）
   - RPC连接配置
   - JWT密钥配置
   - CORS配置

3. **RPC客户端封装**
   - 实现RpcClientWrapper类
   - 自动重连机制
   - 错误处理
   - 日志记录

**交付物**：
- 项目目录结构
- config.py配置模块
- rpc/client.py RPC客户端
- requirements.txt依赖文件

**验收标准**：
- ✅ 可以成功连接VeighNa RPC服务
- ✅ 配置可以通过环境变量覆盖
- ✅ RPC调用有完整的错误处理

---

### 阶段2：WebSocket服务 (1人天)

**目标**：实现实时数据推送基础设施

**任务列表**：

1. **连接管理器**
   - 实现ConnectionManager类
   - 连接生命周期管理
   - 主题订阅管理
   - 心跳机制

2. **消息处理**
   - 实现消息路由
   - 事件广播
   - 个人消息推送
   - 消息序列化

3. **RPC事件订阅**
   - 订阅VeighNa事件引擎
   - 事件格式转换
   - 实时推送行情/交易/策略事件

**交付物**：
- websocket/manager.py连接管理器
- websocket/handlers.py消息处理器
- websocket/events.py事件定义
- websocket/broadcaster.py广播器

**验收标准**：
- ✅ 支持100+并发WebSocket连接
- ✅ 消息推送延迟 < 100ms
- ✅ 连接断开后自动清理订阅

---

### 阶段3：业务服务层 (2人天)

**目标**：实现核心业务逻辑服务

**任务列表**：

1. **行情服务 (MarketService)**
   - 行情订阅管理
   - 实时行情缓存
   - K线数据查询
   - 行情数据格式化

2. **交易服务 (TradeService)**
   - 委托下单
   - 委托撤销
   - 持仓查询
   - 成交查询
   - 资金查询
   - 交易数据格式化

3. **策略服务 (StrategyService)**
   - 策略列表
   - 策略启停
   - 参数修改
   - 策略状态监控
   - 策略日志查询

4. **告警服务 (AlertService)**
   - 告警规则配置
   - 告警检测
   - 告警推送
   - 告警历史查询

**交付物**：
- services/market_service.py
- services/trade_service.py
- services/strategy_service.py
- services/alert_service.py

**验收标准**：
- ✅ 所有服务方法有完整错误处理
- ✅ 数据格式统一规范
- ✅ 支持A股交易规则（T+1、涨跌停、交易单位）

---

### 阶段4：REST API (1.5人天)

**目标**：实现HTTP RESTful API接口

**任务列表**：

1. **认证API**
   - 用户登录
   - Token刷新
   - 登出

2. **行情API**
   - GET /api/market/tick/:symbol - 获取实时行情
   - GET /api/market/bars/:symbol - 获取K线数据
   - GET /api/market/subscribed - 获取订阅列表
   - POST /api/market/subscribe - 订阅行情
   - DELETE /api/market/unsubscribe - 取消订阅

3. **交易API**
   - GET /api/account - 获取账户资金
   - GET /api/positions - 获取持仓列表
   - GET /api/orders - 获取委托列表
   - GET /api/trades - 获取成交列表
   - POST /api/order/send - 发送委托
   - POST /api/order/cancel - 撤销委托

4. **策略API**
   - GET /api/strategies - 获取策略列表
   - GET /api/strategy/:name - 获取策略详情
   - POST /api/strategy/:name/start - 启动策略
   - POST /api/strategy/:name/stop - 停止策略
   - PUT /api/strategy/:name/param - 修改策略参数
   - GET /api/strategy/:name/log - 获取策略日志

5. **告警API**
   - GET /api/alerts - 获取告警列表
   - GET /api/alerts/rules - 获取告警规则
   - POST /api/alerts/rules - 创建告警规则
   - PUT /api/alerts/rules/:id - 更新告警规则
   - DELETE /api/alerts/rules/:id - 删除告警规则

**交付物**：
- api/auth.py
- api/market.py
- api/trade.py
- api/strategy.py
- api/alert.py
- models/request.py
- models/response.py

**验收标准**：
- ✅ 所有接口有OpenAPI文档
- ✅ 请求参数验证完整
- ✅ 错误响应格式统一
- ✅ API响应时间 < 200ms

---

### 阶段5：Web前端 (1.5人天)

**目标**：实现响应式Web前端界面

**任务列表**：

1. **项目初始化**
   - Vite + Vue.js 3项目搭建
   - Element Plus集成
   - ECharts集成
   - 路由配置
   - 状态管理（Pinia）

2. **通用组件**
   - MarketCard - 行情卡片
   - OrderBook - 订单簿
   - PositionTable - 持仓表格
   - ChartCard - K线图表
   - TradePanel - 交易面板
   - StrategyCard - 策略卡片

3. **页面开发**
   - Dashboard - 仪表盘（总览）
   - Market - 行情页面（自选股/行情列表）
   - Trade - 交易页面（下单/撤单/查询）
   - Position - 持仓页面（持仓/盈亏分析）
   - Strategy - 策略页面（策略管理/参数调整）
   - Settings - 设置页面（系统配置）

4. **WebSocket集成**
   - 实时行情更新
   - 订单状态推送
   - 持仓变化推送
   - 策略事件推送
   - 告警实时通知

5. **响应式设计**
   - 移动端适配
   - 触摸操作优化
   - 简化移动端界面

**交付物**：
- frontend/src完整前端代码
- frontend/dist生产构建
- 前端使用文档

**验收标准**：
- ✅ 支持Chrome/Firefox/Safari最新版
- ✅ 支持iOS Safari/Android Chrome
- ✅ WebSocket断线自动重连
- ✅ 页面加载时间 < 2s

---

### 阶段6：测试与优化 (1人天)

**目标**：完善测试覆盖和性能优化

**任务列表**：

1. **单元测试**
   - API接口测试
   - 服务层测试
   - WebSocket测试
   - 工具函数测试

2. **集成测试**
   - RPC通信测试
   - 端到端测试
   - 并发测试
   - 压力测试

3. **安全测试**
   - 认证绕过测试
   - SQL注入测试
   - XSS攻击测试
   - CSRF攻击测试

4. **性能优化**
   - 数据库查询优化
   - WebSocket推送优化
   - 前端渲染优化
   - 缓存策略优化

**交付物**：
- tests/完整测试套件
- 测试覆盖率报告
- 性能测试报告
- 安全测试报告

**验收标准**：
- ✅ 测试覆盖率 > 80%
- ✅ 支持100+并发用户
- ✅ 无高危安全漏洞

---

## 4. 详细设计

### 4.1 RPC客户端封装

```python
"""
vnpy_china_web/rpc/client.py
"""

import json
import threading
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from enum import Enum


class RpcConnectionState(Enum):
    """RPC连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class RpcClientWrapper:
    """RPC客户端封装类

    提供到VeighNa RPC服务的连接封装，包括：
    - 自动重连机制
    - 请求超时控制
    - 错误处理
    - 事件订阅
    """

    def __init__(
        self,
        rep_address: str = "tcp://127.0.0.1:2014",
        pub_address: str = "tcp://127.0.0.1:4102",
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        request_timeout: int = 30
    ):
        """初始化RPC客户端

        Args:
            rep_address: RPC请求地址
            pub_address: RPC发布地址
            auto_reconnect: 是否自动重连
            reconnect_interval: 重连间隔(秒)
            request_timeout: 请求超时(秒)
        """
        self.rep_address = rep_address
        self.pub_address = pub_address
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.request_timeout = request_timeout

        # 连接状态
        self._state: RpcConnectionState = RpcConnectionState.DISCONNECTED
        self._rpc_client: Optional[Any] = None

        # 事件订阅
        self._callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

        # 日志
        self.logger = logging.getLogger(__name__)

    @property
    def state(self) -> RpcConnectionState:
        """获取连接状态"""
        return self._state

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._state == RpcConnectionState.CONNECTED

    def connect(self) -> bool:
        """连接到RPC服务

        Returns:
            是否连接成功
        """
        try:
            self._state = RpcConnectionState.CONNECTING

            from vnpy.rpc import RpcClient

            self._rpc_client = RpcClient()
            self._rpc_client.connect(self.rep_address, self.pub_address)
            self._rpc_client.register(self._handle_push)

            self._state = RpcConnectionState.CONNECTED
            self.logger.info(
                f"RPC connected: {self.rep_address}, {self.pub_address}"
            )
            return True

        except Exception as e:
            self._state = RpcConnectionState.ERROR
            self.logger.error(f"RPC connect failed: {e}")

            if self.auto_reconnect:
                self._start_reconnect()

            return False

    def disconnect(self):
        """断开RPC连接"""
        self._state = RpcConnectionState.DISCONNECTED

        if self._rpc_client:
            try:
                self._rpc_client.close()
            except Exception as e:
                self.logger.error(f"RPC disconnect error: {e}")

            self._rpc_client = None

    def _start_reconnect(self):
        """启动重连线程"""
        def reconnect():
            import time
            while self._state != RpcConnectionState.CONNECTED:
                time.sleep(self.reconnect_interval)
                self.logger.info("RPC reconnecting...")
                if self.connect():
                    break

        thread = threading.Thread(target=reconnect, daemon=True)
        thread.start()

    def _handle_push(self, topic: str, data: Any):
        """处理RPC推送消息

        Args:
            topic: 消息主题
            data: 消息数据
        """
        with self._lock:
            callback = self._callbacks.get(topic)
            if callback:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(
                        f"RPC callback error [{topic}]: {e}"
                    )

    def subscribe(self, topic: str, callback: Callable):
        """订阅RPC事件

        Args:
            topic: 事件主题
            callback: 回调函数
        """
        with self._lock:
            self._callbacks[topic] = callback
        self.logger.debug(f"RPC subscribe: {topic}")

    def unsubscribe(self, topic: str):
        """取消订阅

        Args:
            topic: 事件主题
        """
        with self._lock:
            self._callbacks.pop(topic, None)
        self.logger.debug(f"RPC unsubscribe: {topic}")

    def call(self, method: str, **kwargs) -> Any:
        """RPC调用

        Args:
            method: 调用方法名
            **kwargs: 调用参数

        Returns:
            调用结果

        Raises:
            ConnectionError: RPC未连接
            TimeoutError: 调用超时
        """
        if not self.connected:
            raise ConnectionError(
                f"RPC not connected, state: {self._state.value}"
            )

        request = {
            "method": method,
            "params": kwargs,
            "timestamp": datetime.now().isoformat()
        }

        try:
            response_str = self._rpc_client.call(json.dumps(request))
            response = json.loads(response_str)

            # 检查响应状态
            if isinstance(response, dict) and not response.get("success", True):
                error_msg = response.get("error", "Unknown error")
                raise RuntimeError(f"RPC call failed: {error_msg}")

            return response

        except Exception as e:
            self.logger.error(f"RPC call error [{method}]: {e}")
            raise

    # 便捷方法 - 账户
    def get_account(self) -> Dict:
        """获取账户信息"""
        return self.call("get_account")

    # 便捷方法 - 持仓
    def get_position(self, vt_symbol: str = None) -> Dict:
        """获取持仓信息"""
        return self.call("get_position", vt_symbol=vt_symbol)

    def get_positions(self) -> list:
        """获取所有持仓"""
        return self.call("get_positions")

    # 便捷方法 - 委托
    def get_orders(self, vt_orderid: str = None) -> list:
        """获取委托信息"""
        return self.call("get_orders", vt_orderid=vt_orderid)

    def get_active_orders(self, vt_symbol: str = None) -> list:
        """获取活动委托"""
        return self.call("get_active_orders", vt_symbol=vt_symbol)

    # 便捷方法 - 成交
    def get_trades(self) -> list:
        """获取成交信息"""
        return self.call("get_trades")

    # 便捷方法 - 交易
    def send_order(
        self,
        vt_symbol: str,
        direction: str,
        offset: str,
        volume: float,
        price: float = 0,
        order_type: str = "limit"
    ) -> str:
        """发送委托"""
        return self.call(
            "send_order",
            vt_symbol=vt_symbol,
            direction=direction,
            offset=offset,
            volume=volume,
            price=price,
            order_type=order_type
        )

    def cancel_order(self, vt_orderid: str):
        """撤销委托"""
        return self.call("cancel_order", vt_orderid=vt_orderid)

    def cancel_orders(self, vt_symbol: str):
        """撤销所有委托"""
        return self.call("cancel_orders", vt_symbol=vt_symbol)

    # 便捷方法 - 策略
    def get_all_strategies(self) -> list:
        """获取所有策略"""
        return self.call("get_all_strategies")

    def get_strategy(self, strategy_name: str) -> Dict:
        """获取单个策略"""
        return self.call(
            "get_strategy",
            strategy_name=strategy_name
        )

    def start_strategy(self, strategy_name: str) -> Dict:
        """启动策略"""
        return self.call(
            "start_strategy",
            strategy_name=strategy_name
        )

    def stop_strategy(self, strategy_name: str) -> Dict:
        """停止策略"""
        return self.call(
            "stop_strategy",
            strategy_name=strategy_name
        )

    def set_strategy_param(
        self,
        strategy_name: str,
        param_name: str,
        value: Any
    ) -> Dict:
        """设置策略参数"""
        return self.call(
            "set_strategy_param",
            strategy_name=strategy_name,
            param_name=param_name,
            value=value
        )

    def get_strategy_params(self, strategy_name: str) -> Dict:
        """获取策略参数"""
        return self.call(
            "get_strategy_params",
            strategy_name=strategy_name
        )

    # 便捷方法 - 数据
    def get_history_bars(
        self,
        vt_symbol: str,
        interval: str,
        start_date: str = None,
        end_date: str = None
    ) -> list:
        """获取历史K线"""
        return self.call(
            "get_history_bars",
            vt_symbol=vt_symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date
        )
```

---

### 4.2 WebSocket连接管理器

```python
"""
vnpy_china_web/websocket/manager.py
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
from collections import defaultdict


class ConnectionState:
    """连接状态信息"""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.subscriptions: Set[str] = set()
        self.last_ping = datetime.now()
        self.ip_address: Optional[str] = None


class ConnectionManager:
    """WebSocket连接管理器

    功能：
    - 连接生命周期管理
    - 主题订阅管理
    - 消息广播
    - 心跳检测
    """

    # 支持的订阅主题
    VALID_TOPICS = {
        "market",      # 行情数据
        "trade",       # 交易事件
        "order",       # 委托变化
        "position",    # 持仓变化
        "strategy",    # 策略事件
        "account",     # 账户变化
        "alert",       # 告警通知
    }

    def __init__(self, heartbeat_interval: int = 30, heartbeat_timeout: int = 60):
        """初始化连接管理器

        Args:
            heartbeat_interval: 心跳间隔(秒)
            heartbeat_timeout: 心跳超时(秒)
        """
        # 连接集合
        self.active_connections: Set[Any] = set()

        # 连接元数据
        self.connection_info: Dict[Any, ConnectionState] = {}

        # 主题订阅关系
        self.subscriptions: Dict[str, Set[Any]] = {
            topic: set() for topic in self.VALID_TOPICS
        }

        # 心跳配置
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        # 日志
        self.logger = logging.getLogger(__name__)

        # 启动心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: Any,
        client_id: str,
        ip_address: str = None
    ):
        """接受新连接

        Args:
            websocket: WebSocket连接对象
            client_id: 客户端ID
            ip_address: 客户端IP
        """
        await websocket.accept()

        self.active_connections.add(websocket)

        state = ConnectionState(client_id)
        state.ip_address = ip_address
        self.connection_info[websocket] = state

        self.logger.info(
            f"WebSocket connected: {client_id} from {ip_address}, "
            f"total: {len(self.active_connections)}"
        )

        # 发送连接确认
        await self.send_personal(websocket, {
            "type": "connected",
            "client_id": client_id,
            "server_time": datetime.now().isoformat(),
            "topics": list(self.VALID_TOPICS)
        })

    def disconnect(self, websocket: Any):
        """断开连接

        Args:
            websocket: WebSocket连接对象
        """
        if websocket not in self.active_connections:
            return

        info = self.connection_info.pop(websocket, None)
        if info:
            self.logger.info(
                f"WebSocket disconnected: {info.client_id}, "
                f"duration: {(datetime.now() - info.connected_at).seconds}s"
            )

        # 清理连接
        self.active_connections.discard(websocket)

        # 清理订阅
        if info:
            for topic in info.subscriptions:
                if topic in self.subscriptions:
                    self.subscriptions[topic].discard(websocket)

    def subscribe(self, websocket: Any, topic: str) -> bool:
        """订阅主题

        Args:
            websocket: WebSocket连接对象
            topic: 主题名称

        Returns:
            是否订阅成功
        """
        if topic not in self.VALID_TOPICS:
            self.logger.warning(f"Invalid topic: {topic}")
            return False

        if websocket not in self.active_connections:
            return False

        self.subscriptions[topic].add(websocket)

        if websocket in self.connection_info:
            self.connection_info[websocket].subscriptions.add(topic)

        self.logger.debug(
            f"Client {self.connection_info[websocket].client_id} "
            f"subscribed to {topic}"
        )
        return True

    def unsubscribe(self, websocket: Any, topic: str) -> bool:
        """取消订阅

        Args:
            websocket: WebSocket连接对象
            topic: 主题名称

        Returns:
            是否取消成功
        """
        if topic not in self.VALID_TOPICS:
            return False

        if websocket in self.subscriptions[topic]:
            self.subscriptions[topic].discard(websocket)

        if websocket in self.connection_info:
            self.connection_info[websocket].subscriptions.discard(topic)

        self.logger.debug(
            f"Client {self.connection_info[websocket].client_id} "
            f"unsubscribed from {topic}"
        )
        return True

    async def broadcast(self, topic: str, message: Dict):
        """广播消息到主题订阅者

        Args:
            topic: 主题名称
            message: 消息内容
        """
        if topic not in self.subscriptions:
            return

        # 添加元数据
        message["topic"] = topic
        message["timestamp"] = datetime.now().isoformat()

        # 获取订阅者
        subscribers = self.subscriptions[topic].copy()

        if not subscribers:
            return

        self.logger.debug(
            f"Broadcasting to {len(subscribers)} subscribers on {topic}"
        )

        # 并发发送
        tasks = []
        for connection in subscribers:
            tasks.append(self._send_safe(connection, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_personal(self, websocket: Any, message: Dict):
        """发送个人消息

        Args:
            websocket: WebSocket连接对象
            message: 消息内容
        """
        await self._send_safe(websocket, message)

    async def _send_safe(self, websocket: Any, message: Dict):
        """安全发送消息（带异常处理）

        Args:
            websocket: WebSocket连接对象
            message: 消息内容
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            self.disconnect(websocket)

    async def handle_ping(self, websocket: Any):
        """处理心跳

        Args:
            websocket: WebSocket连接对象
        """
        if websocket in self.connection_info:
            self.connection_info[websocket].last_ping = datetime.now()

        await self.send_personal(websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })

    async def start_heartbeat_check(self):
        """启动心跳检测任务"""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_heartbeat()

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        self.logger.info("Heartbeat check started")

    async def _check_heartbeat(self):
        """检查所有连接的心跳"""
        now = datetime.now()
        to_remove = []

        for websocket, state in self.connection_info.items():
            idle_time = (now - state.last_ping).seconds

            if idle_time > self.heartbeat_timeout:
                self.logger.warning(
                    f"Client {state.client_id} timeout, "
                    f"idle: {idle_time}s"
                )
                to_remove.append(websocket)

        # 清理超时连接
        for websocket in to_remove:
            await self.send_personal(websocket, {
                "type": "timeout",
                "message": f"Idle for {self.heartbeat_timeout}s, disconnecting"
            })
            self.disconnect(websocket)

    def get_statistics(self) -> Dict:
        """获取统计信息

        Returns:
            统计数据字典
        """
        return {
            "total_connections": len(self.active_connections),
            "topic_subscribers": {
                topic: len(conns)
                for topic, conns in self.subscriptions.items()
            },
            "connections": [
                {
                    "client_id": state.client_id,
                    "connected_at": state.connected_at.isoformat(),
                    "subscriptions": list(state.subscriptions),
                    "ip_address": state.ip_address,
                }
                for state in self.connection_info.values()
            ]
        }
```

---

### 4.3 行情服务实现

```python
"""
vnpy_china_web/services/market_service.py
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

from ..rpc.client import RpcClientWrapper


class MarketService:
    """行情服务

    功能：
    - 行情订阅管理
    - 实时行情缓存
    - K线数据查询
    - 行情数据格式化
    """

    # K线缓存长度
    BAR_CACHE_SIZE = 1000

    # 行情缓存过期时间
    TICK_CACHE_TTL = timedelta(minutes=5)

    def __init__(self, rpc_client: RpcClientWrapper):
        """初始化行情服务

        Args:
            rpc_client: RPC客户端
        """
        self.rpc_client = rpc_client

        # 实时行情缓存
        self.tick_cache: Dict[str, Dict] = {}
        self.tick_cache_time: Dict[str, datetime] = {}

        # K线数据缓存
        self.bar_cache: Dict[str, deque] = {}

        # 订阅的合约列表
        self.subscribed_symbols: set = set()

        # 日志
        self.logger = logging.getLogger(__name__)

    def subscribe(self, vt_symbol: str) -> bool:
        """订阅行情

        Args:
            vt_symbol: 合约代码

        Returns:
            是否订阅成功
        """
        try:
            self.rpc_client.call("subscribe", vt_symbol=vt_symbol)
            self.subscribed_symbols.add(vt_symbol)
            self.logger.info(f"Subscribed to {vt_symbol}")
            return True
        except Exception as e:
            self.logger.error(f"Subscribe failed: {e}")
            return False

    def unsubscribe(self, vt_symbol: str) -> bool:
        """取消订阅

        Args:
            vt_symbol: 合约代码

        Returns:
            是否取消成功
        """
        try:
            self.rpc_client.call("unsubscribe", vt_symbol=vt_symbol)
            self.subscribed_symbols.discard(vt_symbol)
            self.logger.info(f"Unsubscribed from {vt_symbol}")
            return True
        except Exception as e:
            self.logger.error(f"Unsubscribe failed: {e}")
            return False

    def get_tick(self, vt_symbol: str) -> Optional[Dict]:
        """获取最新行情

        Args:
            vt_symbol: 合约代码

        Returns:
            行情数据字典
        """
        # 检查缓存
        if vt_symbol in self.tick_cache:
            cache_time = self.tick_cache_time.get(vt_symbol)
            if cache_time and datetime.now() - cache_time < self.TICK_CACHE_TTL:
                return self.tick_cache[vt_symbol]

        # 从RPC获取
        try:
            tick_data = self.rpc_client.call("get_tick", vt_symbol=vt_symbol)
            if tick_data:
                self.update_tick(tick_data)
                return self.format_tick(tick_data)
        except Exception as e:
            self.logger.error(f"Get tick failed: {e}")

        return None

    def get_history_bars(
        self,
        vt_symbol: str,
        interval: str = "1m",
        count: int = 100
    ) -> List[Dict]:
        """获取历史K线

        Args:
            vt_symbol: 合约代码
            interval: K线周期
            count: 数据数量

        Returns:
            K线数据列表
        """
        cache_key = f"{vt_symbol}.{interval}"

        # 检查缓存
        if cache_key in self.bar_cache:
            cached = list(self.bar_cache[cache_key])
            if len(cached) >= count:
                return cached[-count:]

        # 从RPC获取
        try:
            bars = self.rpc_client.get_history_bars(
                vt_symbol=vt_symbol,
                interval=interval
            )

            if bars:
                # 更新缓存
                if cache_key not in self.bar_cache:
                    self.bar_cache[cache_key] = deque(
                        maxlen=self.BAR_CACHE_SIZE
                    )
                self.bar_cache[cache_key].extend(bars)

                return bars[-count:]

        except Exception as e:
            self.logger.error(f"Get history bars failed: {e}")

        return []

    def update_tick(self, tick_data: Dict):
        """更新行情数据

        Args:
            tick_data: 行情数据
        """
        vt_symbol = tick_data.get("vt_symbol")
        if vt_symbol:
            self.tick_cache[vt_symbol] = tick_data
            self.tick_cache_time[vt_symbol] = datetime.now()

    def format_tick(self, tick: Dict) -> Dict:
        """格式化行情数据给前端

        Args:
            tick: 原始行情数据

        Returns:
            格式化后的行情数据
        """
        if not tick:
            return {}

        # 计算涨跌
        last_price = tick.get("last_price", 0)
        open_price = tick.get("open_price", 0)
        change = 0
        change_pct = 0

        if open_price > 0:
            change = last_price - open_price
            change_pct = (change / open_price) * 100 if open_price > 0 else 0

        return {
            "vt_symbol": tick.get("vt_symbol"),
            "symbol": tick.get("symbol"),
            "exchange": tick.get("exchange"),
            "name": tick.get("name", ""),

            # 价格
            "last_price": last_price,
            "open_price": tick.get("open_price"),
            "high_price": tick.get("high_price"),
            "low_price": tick.get("low_price"),
            "pre_close_price": tick.get("pre_close_price"),

            # 涨跌
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),

            # 成交
            "volume": tick.get("volume", 0),
            "turnover": tick.get("turnover", 0),

            # 盘口
            "bid_price_1": tick.get("bid_price_1", 0),
            "bid_volume_1": tick.get("bid_volume_1", 0),
            "ask_price_1": tick.get("ask_price_1", 0),
            "ask_volume_1": tick.get("ask_volume_1", 0),

            # 五档
            "bid_prices": [
                tick.get(f"bid_price_{i}", 0) for i in range(1, 6)
            ],
            "bid_volumes": [
                tick.get(f"bid_volume_{i}", 0) for i in range(1, 6)
            ],
            "ask_prices": [
                tick.get(f"ask_price_{i}", 0) for i in range(1, 6)
            ],
            "ask_volumes": [
                tick.get(f"ask_volume_{i}", 0) for i in range(1, 6)
            ],

            # 时间
            "datetime": tick.get("datetime", ""),
            "update_time": datetime.now().isoformat()
        }

    def format_bar(self, bar: Dict) -> Dict:
        """格式化K线数据

        Args:
            bar: 原始K线数据

        Returns:
            格式化后的K线数据
        """
        if not bar:
            return {}

        return {
            "vt_symbol": bar.get("vt_symbol"),
            "symbol": bar.get("symbol"),
            "exchange": bar.get("exchange"),
            "interval": bar.get("interval"),

            # OHLCV
            "open_price": bar.get("open_price"),
            "high_price": bar.get("high_price"),
            "low_price": bar.get("low_price"),
            "close_price": bar.get("close_price"),
            "volume": bar.get("volume"),
            "turnover": bar.get("turnover"),

            # 时间
            "datetime": bar.get("datetime", ""),
        }

    def get_subscribed_symbols(self) -> List[str]:
        """获取已订阅的合约列表

        Returns:
            合约代码列表
        """
        return list(self.subscribed_symbols)

    def clear_cache(self, vt_symbol: str = None):
        """清理缓存

        Args:
            vt_symbol: 合约代码，None表示清理全部
        """
        if vt_symbol:
            self.tick_cache.pop(vt_symbol, None)
            self.tick_cache_time.pop(vt_symbol, None)

            for key in list(self.bar_cache.keys()):
                if key.startswith(vt_symbol):
                    self.bar_cache.pop(key, None)
        else:
            self.tick_cache.clear()
            self.tick_cache_time.clear()
            self.bar_cache.clear()
```

---

### 4.4 REST API实现

```python
"""
vnpy_china_web/api/market.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from ..services.market_service import MarketService
from ..models.request import MarketSubscribeRequest
from ..models.response import (
    TickResponse,
    BarResponse,
    ApiResponse
)


router = APIRouter(prefix="/api/market", tags=["market"])


# 依赖注入：获取行情服务
async def get_market_service() -> MarketService:
    """获取行情服务实例"""
    from ..server import get_app
    app = get_app()
    return app.market_service


@router.get("/tick/{vt_symbol}", response_model=TickResponse)
async def get_tick(
    vt_symbol: str,
    service: MarketService = Depends(get_market_service)
) -> TickResponse:
    """获取实时行情

    Args:
        vt_symbol: 合约代码（如 600000.SSE）

    Returns:
        实时行情数据
    """
    tick = service.get_tick(vt_symbol)

    if not tick:
        raise HTTPException(
            status_code=404,
            detail=f"Tick data not found for {vt_symbol}"
        )

    return TickResponse(data=tick)


@router.get("/bars", response_model=List[BarResponse])
async def get_bars(
    vt_symbol: str = Query(..., description="合约代码"),
    interval: str = Query("1m", description="K线周期"),
    count: int = Query(100, ge=1, le=1000, description="数据数量"),
    service: MarketService = Depends(get_market_service)
) -> List[BarResponse]:
    """获取历史K线

    Args:
        vt_symbol: 合约代码
        interval: K线周期 (1m/5m/15m/30m/1h/1d)
        count: 数据数量 (1-1000)

    Returns:
        K线数据列表
    """
    bars = service.get_history_bars(vt_symbol, interval, count)

    return [
        BarResponse(data=service.format_bar(bar))
        for bar in bars
    ]


@router.get("/subscribed", response_model=List[str])
async def get_subscribed(
    service: MarketService = Depends(get_market_service)
) -> List[str]:
    """获取已订阅的合约列表

    Returns:
        合约代码列表
    """
    return service.get_subscribed_symbols()


@router.post("/subscribe", response_model=ApiResponse)
async def subscribe(
    req: MarketSubscribeRequest,
    service: MarketService = Depends(get_market_service)
) -> ApiResponse:
    """订阅行情

    Args:
        req: 订阅请求

    Returns:
        操作结果
    """
    success = service.subscribe(req.vt_symbol)

    return ApiResponse(
        success=success,
        message=f"{'订阅成功' if success else '订阅失败'}: {req.vt_symbol}"
    )


@router.delete("/subscribe/{vt_symbol}", response_model=ApiResponse)
async def unsubscribe(
    vt_symbol: str,
    service: MarketService = Depends(get_market_service)
) -> ApiResponse:
    """取消订阅行情

    Args:
        vt_symbol: 合约代码

    Returns:
        操作结果
    """
    success = service.unsubscribe(vt_symbol)

    return ApiResponse(
        success=success,
        message=f"{'取消订阅成功' if success else '取消订阅失败'}: {vt_symbol}"
    )


@router.post("/cache/clear", response_model=ApiResponse)
async def clear_cache(
    vt_symbol: Optional[str] = Query(None, description="合约代码，不传则清空全部"),
    service: MarketService = Depends(get_market_service)
) -> ApiResponse:
    """清理行情缓存

    Args:
        vt_symbol: 合约代码，None表示清理全部

    Returns:
        操作结果
    """
    service.clear_cache(vt_symbol)

    return ApiResponse(
        success=True,
        message=f"缓存已清理: {vt_symbol or '全部'}"
    )
```

---

### 4.5 FastAPI应用主入口

```python
"""
vnpy_china_web/server/app.py
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from .config import Settings
from .security import create_access_token, verify_token
from ..rpc.client import RpcClientWrapper
from ..websocket.manager import ConnectionManager
from ..services.market_service import MarketService
from ..services.trade_service import TradeService
from ..services.strategy_service import StrategyService
from ..api import auth, market, trade, strategy


# 全局应用实例
_app: FastAPI = None


def get_app() -> FastAPI:
    """获取应用实例"""
    global _app
    return _app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logging.info("Starting VeighNa Web API...")

    # 初始化RPC客户端
    app.state.rpc_client = RpcClientWrapper(
        rep_address=Settings.RPC_REP_ADDRESS,
        pub_address=Settings.RPC_PUB_ADDRESS,
        auto_reconnect=True
    )

    # 连接RPC
    if not app.state.rpc_client.connect():
        logging.error("Failed to connect to RPC service")

    # 初始化WebSocket管理器
    app.state.ws_manager = ConnectionManager()

    # 初始化服务
    app.state.market_service = MarketService(app.state.rpc_client)
    app.state.trade_service = TradeService(app.state.rpc_client)
    app.state.strategy_service = StrategyService(app.state.rpc_client)

    # 启动心跳检测
    await app.state.ws_manager.start_heartbeat_check()

    logging.info("VeighNa Web API started")

    yield

    # 关闭
    logging.info("Shutting down VeighNa Web API...")

    # 断开RPC
    app.state.rpc_client.disconnect()

    logging.info("VeighNa Web API shutdown complete")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    global _app

    app = FastAPI(
        title="VeighNa Web API",
        description="VeighNa量化交易系统Web监控接口",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册API路由
    app.include_router(auth.router)
    app.include_router(market.router)
    app.include_router(trade.router)
    app.include_router(strategy.router)

    # WebSocket端点
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(
        websocket: WebSocket,
        client_id: str
    ):
        """WebSocket连接端点"""
        await app.state.ws_manager.connect(websocket, client_id)

        try:
            while True:
                # 接收消息
                data = await websocket.receive_json()
                await handle_ws_message(app, websocket, data)

        except WebSocketDisconnect:
            app.state.ws_manager.disconnect(websocket)
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            app.state.ws_manager.disconnect(websocket)

    async def handle_ws_message(app, websocket, message):
        """处理WebSocket消息"""
        msg_type = message.get("type")
        data = message.get("data", {})

        if msg_type == "subscribe":
            # 订阅主题
            topic = data.get("topic")
            app.state.ws_manager.subscribe(websocket, topic)

        elif msg_type == "unsubscribe":
            # 取消订阅
            topic = data.get("topic")
            app.state.ws_manager.unsubscribe(websocket, topic)

        elif msg_type == "ping":
            # 心跳
            await app.state.ws_manager.handle_ping(websocket)

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {
            "status": "ok",
            "rpc_connected": app.state.rpc_client.connected,
            "ws_connections": len(app.state.ws_manager.active_connections)
        }

    # 静态文件服务（前端）
    # app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")

    # 根路径返回前端
    # @app.get("/")
    # async def root():
    #     return FileResponse("frontend/dist/index.html")

    _app = app
    return app


def main():
    """启动Web服务器"""
    app = create_app()

    uvicorn.run(
        app,
        host=Settings.HOST,
        port=Settings.PORT,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
```

---

## 5. 测试计划

### 5.1 测试用例

| 模块 | 测试类型 | 测试用例数 | 覆盖目标 |
|------|---------|-----------|---------|
| RPC客户端 | 单元测试 | 15 | 90% |
| WebSocket | 单元测试 | 20 | 85% |
| 行情服务 | 单元测试 | 18 | 85% |
| 交易服务 | 单元测试 | 25 | 90% |
| 策略服务 | 单元测试 | 22 | 85% |
| API接口 | 集成测试 | 35 | 80% |
| 前端组件 | 单元测试 | 30 | 75% |
| 端到端测试 | 集成测试 | 15 | N/A |
| **合计** | | **180** | **85%** |

### 5.2 核心测试用例

**RPC客户端测试**：
```python
def test_rpc_connect():
    """测试RPC连接"""
    client = RpcClientWrapper()
    assert client.connect()
    assert client.connected
    client.disconnect()

def test_rpc_call():
    """测试RPC调用"""
    client = RpcClientWrapper()
    client.connect()
    account = client.get_account()
    assert isinstance(account, dict)

def test_rpc_reconnect():
    """测试自动重连"""
    client = RpcClientWrapper(auto_reconnect=True)
    # 模拟断开...
```

**WebSocket测试**：
```python
def test_ws_connect():
    """测试WebSocket连接"""
    manager = ConnectionManager()
    # 模拟连接...

def test_ws_subscribe():
    """测试主题订阅"""
    manager = ConnectionManager()
    # 模拟订阅...

def test_ws_broadcast():
    """测试消息广播"""
    manager = ConnectionManager()
    # 模拟广播...
```

**API接口测试**：
```python
def test_get_account():
    """测试获取账户信息"""
    response = client.get("/api/account")
    assert response.status_code == 200

def test_send_order():
    """测试发送委托"""
    response = client.post("/api/order/send", json={...})
    assert response.status_code == 200

def test_start_strategy():
    """测试启动策略"""
    response = client.post("/api/strategy/test/start")
    assert response.status_code == 200
```

---

## 6. 部署方案

### 6.1 Docker部署

**后端Dockerfile**：
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY vnpy_china_web/ ./vnpy_china_web/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "vnpy_china_web.server.app"]
```

**前端Dockerfile**：
```dockerfile
FROM node:20-alpine as builder

WORKDIR /app

# 安装依赖
COPY frontend/package*.json ./
RUN npm install

# 构建
COPY frontend/ ./
RUN npm run build

# 生产镜像
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**docker-compose.yml**：
```yaml
version: '3.8'

services:
  vnpy-web:
    build:
      context: .
      dockerfile: deployments/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - RPC_REP_ADDRESS=tcp://host.docker.internal:2014
      - RPC_PUB_ADDRESS=tcp://host.docker.internal:4102
    restart: unless-stopped

  vnpy-web-frontend:
    build:
      context: .
      dockerfile: deployments/Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - vnpy-web
    restart: unless-stopped
```

### 6.2 部署步骤

1. **构建镜像**
```bash
docker build -f deployments/Dockerfile -t vnpy-web:latest .
docker build -f deployments/Dockerfile.frontend -t vnpy-web-frontend:latest .
```

2. **启动服务**
```bash
docker-compose up -d
```

3. **验证部署**
```bash
curl http://localhost:8000/health
```

---

## 7. 风险管理

### 7.1 技术风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| RPC连接不稳定 | 高 | 中 | 自动重连机制、连接池、心跳检测 |
| WebSocket并发限制 | 中 | 低 | 负载均衡、连接数限制 |
| 前端性能问题 | 中 | 中 | 虚拟滚动、数据分页、懒加载 |
| 安全漏洞 | 高 | 低 | JWT认证、HTTPS、输入验证、CSRF防护 |

### 7.2 业务风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| 误操作风险 | 高 | 中 | 二次确认、操作审计、权限控制 |
| 数据泄露 | 高 | 低 | 加密传输、权限隔离、审计日志 |
| 系统不可用 | 高 | 低 | 健康检查、自动重启、故障转移 |

---

## 8. 验收标准

### 8.1 功能验收

- ✅ 支持实时行情查看（WebSocket推送延迟 < 500ms）
- ✅ 支持手动下单、撤单
- ✅ 支持策略启停、参数调整
- ✅ 支持持仓查询、盈亏统计
- ✅ 支持移动端响应式访问
- ✅ 支持告警实时推送

### 8.2 性能验收

- ✅ 支持100+并发WebSocket连接
- ✅ API平均响应时间 < 200ms
- ✅ 前端首屏加载时间 < 2s
- ✅ WebSocket消息推送延迟 < 500ms

### 8.3 安全验收

- ✅ JWT认证机制完整
- ✅ 所有API有权限控制
- ✅ 支持HTTPS加密传输
- ✅ 操作审计日志完整
- ✅ 无高危安全漏洞

### 8.4 质量验收

- ✅ 代码覆盖率 > 80%
- ✅ 通过所有测试用例
- ✅ 代码符合PEP 8规范
- ✅ API文档完整（OpenAPI）

---

## 9. 时间进度

| 周次 | 任务 | 工作量 |
|------|------|--------|
| 第1周 | 基础设施、WebSocket、服务层 | 4人天 |
| 第1周 | REST API | 1.5人天 |
| 第2周 | Web前端 | 1.5人天 |
| 第2周 | 测试与优化 | 1人天 |

**合计**: 8人天，2周完成

---

## 10. 依赖关系

### 10.1 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| vnpy | 4.3.0+ | 核心框架 |
| vnpy.rpcservice | 4.3.0+ | RPC服务 |
| fastapi | 0.109+ | Web框架 |
| uvicorn | 0.27+ | ASGI服务器 |
| websockets | 12.0+ | WebSocket支持 |

### 10.2 开发依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| pytest | 7.4+ | 测试框架 |
| pytest-asyncio | 0.21+ | 异步测试 |
| httpx | 0.26+ | HTTP客户端测试 |
| ruff | 0.1+ | 代码检查 |
| mypy | 1.8+ | 类型检查 |

---

## 11. 后续优化方向

1. **性能优化**
   - Redis缓存集成
   - 数据库查询优化
   - 前端SSR渲染

2. **功能扩展**
   - 多用户权限管理
   - 操作日志审计
   - 数据分析报表
   - 回测结果可视化

3. **监控告警**
   - 系统监控面板
   - 性能指标采集
   - 异常告警通知

4. **移动端**
   - 原生App开发（React Native/Flutter）
   - 推送通知集成
   - 离线功能支持
