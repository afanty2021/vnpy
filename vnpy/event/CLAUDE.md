[根目录](../../../CLAUDE.md) > [vnpy](../../) > **event**

# Event - 事件驱动引擎

> 更新时间：2025-12-09 11:33:34

## 模块职责

Event模块提供了轻量级但功能强大的事件驱动框架，是VeighNa架构的核心基础设施。它实现了事件的发布-订阅模式，支持异步事件处理和定时器功能，确保各模块间的松耦合通信。

## 入口与启动

### 主要入口
- `EventEngine` - 事件引擎，管理事件的分发和处理
- `Event` - 事件对象，包含事件类型和数据

### 基本使用
```python
from vnpy.event import EventEngine, Event

# 创建事件引擎
event_engine = EventEngine(interval=1)

# 注册事件处理器
def handler(event):
    print(f"收到事件: {event.type}, 数据: {event.data}")

event_engine.register(EVENT_TYPE, handler)

# 发送事件
event_engine.put(Event(EVENT_TYPE, {"data": "test"}))

# 启动引擎
event_engine.start()
```

## 对外接口

### EventEngine接口
- `start()` - 启动事件引擎
- `stop()` - 停止事件引擎
- `put()` - 向队列中放入事件
- `register()` - 注册事件处理器
- `unregister()` - 注销事件处理器
- `register_general()` - 注册通用处理器（处理所有事件）

### Event对象
- `type` - 事件类型（字符串）
- `data` - 事件数据（任意对象）

## 关键依赖与配置

### 依赖项
- Python内置模块：
  - `queue` - 事件队列
  - `threading` - 多线程支持
  - `collections` - 数据结构

### 配置选项
- `interval` - 定时器事件间隔（秒），默认1秒

## 数据模型

### 内置事件类型
- `EVENT_TIMER` - 定时器事件，每interval秒触发一次

### 自定义事件类型
交易相关事件定义在`vnpy.trader.event`中：
- `EVENT_TICK` - Tick行情事件
- `EVENT_BAR` - K线事件
- `EVENT_ORDER` - 委托事件
- `EVENT_TRADE` - 成交事件
- `EVENT_POSITION` - 持仓事件
- `EVENT_ACCOUNT` - 账户事件
- `EVENT_CONTRACT` - 合约事件
- `EVENT_LOG` - 日志事件

## 实现机制

### 线程模型
- 事件引擎运行在独立线程中
- 事件处理器在事件引擎线程中同步执行
- 避免了复杂的线程同步问题

### 事件分发流程
1. 生产者调用`put()`将事件放入队列
2. 事件引擎线程从队列中取出事件
3. 根据事件类型查找已注册的处理器
4. 调用所有处理器处理事件
5. 定时器事件通过sleep实现

## 性能特点

### 优势
- 轻量级实现，无外部依赖
- 支持任意类型的处理器
- 定时器事件精度可配置
- 线程安全的队列操作

### 注意事项
- 事件处理器应避免耗时操作
- 处理器中的异常不会中断引擎运行
- 事件按顺序处理，非并发

## 常见问题 (FAQ)

### Q: 如何确保事件处理的性能？
A: 避免在处理器中执行耗时操作，如有需要可使用线程池。

### Q: 可以跨线程使用事件引擎吗？
A: 可以，`put()`方法是线程安全的。

### Q: 如何实现事件的优先级？
A: 可以通过不同的事件类型来实现优先级，或使用多个事件引擎。

## 相关文件清单

- `__init__.py` - 模块导出定义
- `engine.py` - EventEngine和Event实现

## 变更记录 (Changelog)

### 2025-12-09 11:33:34
- ✨ 创建event模块文档
- 📊 整理事件驱动架构设计
- 🔧 说明核心接口和使用方法
- 📝 添加性能注意事项和FAQ

---

*提示：事件引擎是VeighNa框架的通信总线，所有模块间的数据交换都通过事件进行。*