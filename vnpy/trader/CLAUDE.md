[根目录](../../../CLAUDE.md) > [vnpy](../../) > **trader**

# Trader - 交易核心框架

> 更新时间：2025-12-09 11:33:34

## 模块职责

Trader模块是VeighNa框架的核心，提供了完整的交易系统基础设施，包括事件处理、数据管理、交易接口、应用框架和用户界面组件。

## 入口与启动

### 主要入口
- `MainEngine` - 主引擎，负责协调所有组件
- `EventEngine` - 事件引擎（由event模块提供）
- `BaseApp` - 应用基类，所有功能模块的父类

### 启动流程
```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine

# 创建事件引擎和主引擎
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 添加交易接口和应用
main_engine.add_gateway(gateway_class)
main_engine.add_app(app_class)
```

## 对外接口

### 核心引擎接口

#### MainEngine
- `add_gateway()` - 添加交易接口
- `add_app()` - 添加应用模块
- `connect()` - 连接交易接口
- `subscribe()` - 订阅行情数据
- `send_order()` - 发送委托订单
- `cancel_order()` - 撤销委托订单
- `get_contract()` - 查询合约信息
- `get_position()` - 查询持仓信息
- `get_account()` - 查询账户信息

#### BaseGateway
- `on_tick()` - Tick行情推送
- `on_bar()` - K线行情推送
- `on_trade()` - 成交推送
- `on_order()` - 委托状态推送
- `on_position()` - 持持变化推送
- `on_account()` - 账户变化推送
- `send_order()` - 发送订单
- `cancel_order()` - 撤销订单
- `query_history()` - 查询历史数据

### 数据对象接口

#### 行情数据
- `TickData` - Tick行情数据
- `BarData` - K线数据
- `QuoteData` - 报价数据

#### 交易数据
- `OrderData` - 委托订单数据
- `TradeData` - 成交数据
- `PositionData` - 持仓数据
- `AccountData` - 账户数据
- `ContractData` - 合约数据

#### 请求对象
- `OrderRequest` - 委托请求
- `CancelRequest` - 撤单请求
- `SubscribeRequest` - 订阅请求
- `HistoryRequest` - 历史数据请求

## 关键依赖与配置

### 内部依赖
- `vnpy.event` - 事件引擎
- `PySide6` - GUI框架
- `pandas` - 数据处理
- `numpy` - 数值计算

### 配置系统
- 配置文件路径：`.vntrader/vt_setting.json`
- 全局配置对象：`SETTINGS`
- 支持的配置项：
  - 日志配置
  - 数据库配置
  - 代理配置
  - 各模块特定配置

### 数据库支持
- 默认：SQLite（内置）
- 可选：MySQL, PostgreSQL, MongoDB等

## 数据模型

### 核心数据结构

#### BaseData
所有数据对象的基类，包含：
- `gateway_name` - 数据来源网关
- `extra` - 扩展信息字典

#### 交易常量
- `Direction` - 方向（多/空/净）
- `Offset` - 开平（开/平/平今/平昨）
- `OrderType` - 订单类型
- `Status` - 订单状态
- `Product` - 产品类型
- `Exchange` - 交易所
- `Interval` - K线周期

## 测试与质量

### 测试文件
- 暂无专门的单元测试文件
- 通过examples目录下的示例进行功能验证

### 代码质量
- **Ruff**：用于代码风格检查
- **MyPy**：用于类型检查，配置为严格模式
- 编码规范：严格遵循PEP 8

## 常见问题 (FAQ)

### Q: 如何添加新的交易接口？
A: 继承`BaseGateway`类，实现必要的接口方法，然后通过`main_engine.add_gateway()`注册。

### Q: 如何自定义应用模块？
A: 继承`BaseApp`类，定义必要的类属性，实现`init()`和`stop()`方法。

### Q: 如何处理多账户交易？
A: 每个账户对应一个独立的`AccountData`对象，可以在策略中根据账户信息进行路由。

## 相关文件清单

### 核心文件
- `__init__.py` - 模块初始化
- `engine.py` - MainEngine主引擎实现
- `app.py` - BaseApp应用基类
- `gateway.py` - BaseGateway网关基类
- `object.py` - 所有数据对象定义
- `constant.py` - 常量枚举定义
- `setting.py` - 配置管理
- `utility.py` - 工具函数
- `converter.py` - 内外盘转换器
- `database.py` - 数据库接口
- `datafeed.py` - 数据服务接口
- `optimize.py` - 优化功能
- `logger.py` - 日志管理
- `event.py` - 事件定义

### UI组件
- `ui/__init__.py` - UI模块初始化
- `ui/mainwindow.py` - 主窗口
- `ui/widget.py` - 通用组件
- `ui/qt.py` - Qt相关
- `ui/ico/` - 图标资源

### 国际化
- `locale/__init__.py` - 国际化初始化
- `locale/build_hook.py` - 构建钩子
- `locale/en/LC_MESSAGES/vnpy.po` - 英文翻译文件

## 变更记录 (Changelog)

### 2025-12-09 11:33:34
- ✨ 创建trader模块文档
- 📊 梳理核心架构和接口设计
- 🔧 整理数据对象和常量定义
- 📝 提供开发指南和FAQ

---

*提示：该模块是VeighNa的核心，其他所有功能模块都基于此构建。*