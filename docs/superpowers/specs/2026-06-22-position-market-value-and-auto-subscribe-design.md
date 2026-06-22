# 持仓市值列 + 自动订阅行情 设计文档

> 日期：2026-06-22
> 涉及文件：`examples/client_server/run_qmt_client.py`（唯一改动文件）
> 目标 GUI：`run_qmt_client.py`（RPC 客户端，连接 Windows QMT 服务端）

## 1. 背景与目标

当前 RPC 客户端的持仓列表（`PositionMonitor`）展示：代码 / 名称 / 数量 / 昨仓 / 成本价 / 盈亏 / 接口，**没有市值列**，且**持仓股不会自动订阅行情**。用户希望：

1. 持仓列表新增「市值」列：市值 = 当前最新价 × 持仓股数
2. 持仓股自动全部订阅行情（这样最新价才有来源，市值才能实时刷新）

两个需求耦合：必须先订阅 → tick 流入 `main_engine.ticks` 缓存 → 才能计算实时市值。

## 2. 关键事实（代码调研）

| 事实 | 位置 / 说明 |
|------|-------------|
| `PositionMonitor` 仅监听 `EVENT_POSITION` | `vnpy/trader/ui/widget.py:564`；持仓事件本身不带最新价（`PositionData.price` 是成本价） |
| `TickData.last_price` 为最新价 | `vnpy/trader/object.py:46` |
| 取最新 tick | `main_engine.get_tick(vt_symbol) -> TickData \| None`（`engine.py:462`） |
| 订阅 API | `main_engine.subscribe(SubscribeRequest(symbol, exchange), gateway_name)`（`engine.py:244`） |
| 持仓来源 | `main_engine.get_all_positions() -> list[PositionData]`（`engine.py:522`） |
| `MainWindow` 创建 monitor 的类引用 | `vnpy/trader/ui/mainwindow.py:90` 用 `PositionMonitor`（自 `widget` import），故子类需 patch `mainwindow.PositionMonitor` |
| `BaseMonitor.register_event` 机制 | `widget.py:331`；`signal` 为类级 `QtCore.Signal(Event)`，子类新增 tick 通道须同样在类级声明 |
| 现有数值格式化 | `run_qmt_client.py:26` 的 `_new_set_content`：≥1亿→「X.XX亿」，≥1万→「X.XX万」，其余 2 位小数；`_sort_value` 保留原值供数值排序 |
| RPC 时序 | `RpcGateway.connect` 内 `query_all` 同步执行，connect 返回后持仓已缓存到 `main_engine.positions`（见 memory `rpc-client-trade-order-not-display`） |
| 网关名 | `add_gateway(RpcGateway, "RPC")`（`run_qmt_client.py:336`），订阅须用 `"RPC"` |

## 3. 设计

### 3.1 持仓列表新增「市值」列（tick 事件驱动）

**实现方式：子类化 `PositionMonitor`**，替代当前 `run_qmt_client.py:48-60` 的 `headers` monkey-patch。

```python
class PositionMonitorMV(PositionMonitor):
    tick_signal = QtCore.Signal(Event)      # Qt Signal 须类级声明

    headers = {
        "symbol":       {"display": "代码",   "cell": widget.BaseCell, "update": False},
        "name":         {"display": "名称",   "cell": widget.BaseCell, "update": False},
        "volume":       {"display": "数量",   "cell": widget.BaseCell, "update": True},
        "yd_volume":    {"display": "昨仓",   "cell": widget.BaseCell, "update": True},
        "price":        {"display": "成本价", "cell": widget.BaseCell, "update": True},
        "market_value": {"display": "市值",   "cell": widget.BaseCell, "update": True},   # 新增
        "pnl":          {"display": "盈亏",   "cell": widget.PnlCell,  "update": True},
        "gateway_name": {"display": "接口",   "cell": widget.BaseCell, "update": False},
    }

    def __init__(self, main_engine, event_engine):
        self._symbol_positionids: dict[str, list[str]] = {}  # vt_symbol -> [vt_positionid]
        self._positions: dict[str, PositionData] = {}        # vt_positionid -> 最新持仓
        super().__init__(main_engine, event_engine)

    def register_event(self):
        super().register_event()                              # EVENT_POSITION
        self.tick_signal.connect(self.process_tick_event)
        self.event_engine.register(EVENT_TICK, self.tick_signal.emit)
```

**市值计算与刷新（insert / update 职责分离，防止 `_symbol_positionids` 重复膨胀）：**

- `insert_new_row`（仅新增行时调用一次，由 `BaseMonitor.process_event` 的 `key not in cells` 保证）：
  - 登记反向映射：`_symbol_positionids.setdefault(pos.vt_symbol, []).append(pos.vt_positionid)`
  - 缓存持仓：`_positions[pos.vt_positionid] = pos`
  - `market_value` 列调 `_calc_market_value(pos)`
  - `name` 列走 `_get_position_name`
  - 其余列用 `_get_attr`（避免 `__getattribute__("market_value")` 抛 `AttributeError`，因 `PositionData` 无此字段）
- `update_old_row`（已存在行，仅刷新）：**只更新** `_positions[pos.vt_positionid] = pos` 并重算 `market_value` 列，**绝不再动 `_symbol_positionids`**（否则 A 股每次成交触发的持仓事件都会对同一 `vt_positionid` 重复 append，列表无限增长 → 每个 tick 遍历含大量重复项并对同一 cell 反复 `set_content`，性能持续劣化 + 内存泄漏）
- `_calc_market_value(pos)`：`tick = main_engine.get_tick(pos.vt_symbol); return tick.last_price * pos.volume if tick else 0.0`（**`else 0.0` 用 float 而非 int 0**，确保无 tick 时也进入 `_new_set_content` 的 `isinstance(content, float)` 分支，统一显示「0.00」并写入 `_sort_value`，避免有/无 tick 时显示格式与排序行为不一致）
- `process_tick_event(event)`：取 `tick = event.data`，遍历 `_symbol_positionids.get(tick.vt_symbol, [])`，对每个 `vt_positionid` 取 `pos = _positions[vt_positionid]`，重算 `mv = tick.last_price * pos.volume`，更新对应 `market_value` cell（`cell.set_content(mv, pos)`）

**格式化：** 自动复用 monkey-patched `BaseCell.set_content`（`_new_set_content`），市值大数显示「亿/万」，且 `_sort_value` 保留原值支持数值排序。

**注入：** `mainwindow.PositionMonitor = PositionMonitorMV`（在 `MainWindow(...)` 构造前执行），使 `mainwindow.py:90` 创建的是带市值列的子类。

### 3.2 持仓自动订阅行情（连接后 + 周期补订）

在 `start_gui_with_rpc()` 内、`main_engine.connect(...)` 之后、`MainWindow(...)` 之前插入：

```python
from vnpy.trader.object import SubscribeRequest

_subscribed: set[str] = set()

def subscribe_positions() -> None:
    for pos in main_engine.get_all_positions():
        if pos.vt_symbol in _subscribed:
            continue
        main_engine.subscribe(SubscribeRequest(pos.symbol, pos.exchange), "RPC")
        _subscribed.add(pos.vt_symbol)

subscribe_positions()                                 # connect 后立即订阅（持仓已缓存）

sub_timer = QtCore.QTimer()
sub_timer.timeout.connect(subscribe_positions)
sub_timer.start(10_000)                               # 每 10 秒补订新增持仓
# sub_timer 保存为 start_gui_with_rpc 的局部变量（持有引用），并在 Qt 事件循环
# 退出后调用 sub_timer.stop()，与 reporting_svc 显式 start/stop 的生命周期管理一致。
# 避免无引用 + 无 stop 导致窗口关闭到函数返回间仍可能触发一次 subscribe_positions。
```

- 去重集合 `_subscribed` 避免重复订阅
- connect 后立即调用：`RpcGateway.connect` 内 `query_all` 同步完成，持仓已在 `main_engine.positions` 缓存
- 10 秒定时器兜底盘中新成交产生的新持仓

### 3.3 不改动的部分

- 账户（`AccountMonitor`）/ 委托（`OrderMonitor`）/ 成交（`TradeMonitor`）定制逻辑保持原样
- RPC 时序回补（`run_qmt_client.py:379-392`）不动
- `reporting_svc` 启停逻辑不动
- 布局恢复（`restore_submitted_layout`）不动

## 4. 数据流

```
connect(RPC)
  └─ query_all 同步返回 → main_engine.positions 缓存
subscribe_positions()  ← 立即订阅全部持仓 vt_symbol
  └─ RPC 服务端推送 tick → EVENT_TICK → main_engine.ticks 缓存
                                ↓
                  PositionMonitorMV.process_tick_event
                                ↓
                  _symbol_positionids[tick.vt_symbol] → 定位行
                                ↓
                  mv = tick.last_price * volume → market_value cell 刷新
```

## 5. 风险与边界

| 风险 | 处理 |
|------|------|
| 未订阅时 tick 缺失，市值显示 0 | 由需求 3.2 订阅解决；启动瞬间短暂为 0 可接受 |
| A 股一个 `vt_symbol` 可能对应多 `direction` 行（NET/LONG/SHORT） | `_symbol_positionids` 用 `list` 容纳，逐行更新 |
| `process_tick_event` 频繁调用性能 | A 股持仓数量有限（几只~几十只），映射 O(1) 定位，可接受 |
| `PositionData` 无 `market_value` 字段，`__getattribute__` 会抛错 | 用 `_get_attr` 安全取值，并特判 `market_value` 列走计算 |
| 子类 `Signal` 须类级声明 | `tick_signal` 在类体声明，不在方法内动态创建 |
| 持仓 volume 变动（成交）后市值仍正确 | `update_old_row` 触发 `market_value` 重算；tick 持续刷新 |

## 6. 验证

- 启动 `run_qmt_client.py` 连接 RPC 服务端
- 持仓列表出现「市值」列，数值 = 最新价 × 数量，盘中随 tick 实时变化
- 大市值股票显示「X.XX亿」/「X.XX万」，可数值排序
- 盘中下单成交产生新持仓 → 10 秒内自动订阅，市值列出现并刷新
- 其余表格（账户/委托/成交/行情）显示正常，不受影响
