# vnpy_china_analysis 代码审查修复方案

> 创建日期：2026-06-13
> 来源：模块代码审查报告（16 项）经逐行核实 + review 后的修复计划
> 状态：**已 review 通过，执行中**（v2 纳入 review 反馈）

---

## 0. 背景与范围

本文档针对 `vnpy_china_analysis` 模块的代码审查报告，记录核实结论与逐项修复方案。
**先核实、再修复**——审查报告中的判断并非全部成立，本文档已对每一条做了基于代码的核实，
并经一轮 review 调整为最终方案。

### 修复范围（5 项）

| 编号 | 对应 | 问题 | 文件 | 核实结论 |
|------|------|------|------|---------|
| A | #3 | UI 字段类型不匹配 → 运行时崩溃 | `ui/widget.py` | ✅ 属实，会崩 |
| B | #1/#4 | 资金流聚合失效 + tick 类型契约错 | `money_flow/analyzer.py` | ✅ 属实 |
| C | #6 | tick 事件分发失效 → 实时分析全链路断 | `engine.py` + 分析器 | ✅ 属实，影响最大 |
| D | #2 | 开盘价方向判断恒错 | `auction/open_predict.py` | ✅ 属实，逻辑错误 |
| E | #5 | 历史资金流金额双重换算 | `ui/widget.py` | ✅ 属实（review 确认单位为元） |

### 不修复项及理由

| 编号 | 报告判定 | 决定 | 理由 |
|------|---------|------|------|
| #7 | clear 逻辑反了 | **不修（误报）** | `if symbol is None: sector_index.clear_cache(None)` 合理——sector 按 `sector_code` 存储、与 symbol 无映射，单 symbol 清理时不动 sector 才正确。改为 `not None` 反而引入 bug |
| #8 | get_volume_ratio 存桩 | **暂不修** | 属 TODO 存桩，非缺陷；如需启用应单独提需求 |
| #9~#16 | 测试路径、覆盖率、类型注解等 | **部分顺带** | #9 硬编码路径顺带修；其余设计类问题另开测试加固专项 |

---

## 1. 核实结论（基于代码逐行确认）

### A. UI 字段类型不匹配（#3）— 属实，崩溃

- `level2/order_queue.py:87-92` `get_support_level()` 返回 **dict**：
  ```python
  return {"price": ..., "volume": ..., "strength": ..., "level": ...}
  ```
- `ui/widget.py:236-238` 把它当数值：`format_number(dict, 2)` → `f"{dict:,.2f}"` → **TypeError**
- 空数据返回 `{}`，同样崩溃。**只要有 `order_queue` 数据进入该分支必崩。**

> **Review（C.1 字段映射）：通过。** `support_level.price` 为委托量加权最强的买盘价位，匹配「支撑位」列；`price_depth.depth_ratio`（bid_total/ask_total）反映买卖力量对比，比单独展示总量更有信息量。映射语义一致。

### B. 资金流聚合失效（#1/#4）— 属实

- `money_flow/analyzer.py:121-125`：两分支结果相同，`tick_history` 恒为空。
- `flow_history` 存的是 `MoneyFlowData`（聚合快照），不是 `TickFlowData`（#4）。
  即便补上取数，类型也对不上。聚合逻辑彻底失效。

### C. tick 事件分发失效（#6）— 属实，影响最大

- `base.py` 的 `RealtimeAnalyzer` 只有 `update()`，**无 `on_tick()`**。
- engine 注册的 4 个 analyzer 均未实现 `on_tick`。
- `engine.py:259` `if hasattr(analyzer, "on_tick")` 恒为 `False`，tick 永不分发。
- **后果**：实时资金流向、Level2 实时数据永远为空。与 B 叠加，实时分析全链路断裂。

### D. 开盘价方向判断错误（#2）— 属实，逻辑错误

- `auction/open_predict.py:169` 死代码：`pred_change = p["predicted_price"] - p["predicted_price"]`（恒 0）
- 方向判断用 ±1% 价格接近度，与「方向」无关。
- `prediction_history` 未存 `pre_close`，方向判断缺基准。

### E. 历史资金流金额双重换算（#5）— 属实

**Review 已确认单位**（`vnpy_china_data/models/money_flow.py:91`）：
```python
@property
def main_net_amount(self) -> float:
    """主力净流入金额（元）= 超大单 + 大单"""
    return self.super_large_net_amount + self.large_net_amount
```
`super_large_net_amount` / `large_net_amount` 注释均为「单位：元」。

数据链路：
- `engine` 映射 `"main_net_amount": mf.main_net_amount`（**元**）
- 实时路径 `update_table`：`format_amount(main_inflow)` → 内部做 万/亿 转换 ✅
- 历史路径 `update_historical_table`：`data.get("main_net_amount", 0) / 10000` → 先转万元 → 再进 `format_amount`（又转一次）❌ **双重换算**

举例：1 亿主力净流入，历史路径 `100000000/10000=10000` → `format_amount(10000)` → 显示 `10000.00`（无后缀）；实时路径显示 `10000.00万`。量级错乱。

---

## 2. 逐项修复方案

### 修复 A — UI 字段类型不匹配

**文件**：`vnpy_china_analysis/ui/widget.py`
**位置**：`Level2AnalysisWidget.update_table()`，第 234-238 行

```python
if analysis:
    order_queue = analysis.get("order_queue", {})
    # support_level/resistance_level/price_depth 均为 dict，取语义字段
    support = order_queue.get("support_level") or {}
    resistance = order_queue.get("resistance_level") or {}
    depth = order_queue.get("price_depth") or {}

    self.setItemText(row, 1, self.format_number(support.get("price", 0), 2))
    self.setItemText(row, 2, self.format_number(resistance.get("price", 0), 2))
    self.setItemText(row, 3, self.format_number(depth.get("depth_ratio", 0), 2))

    main_force = analysis.get("main_force", {})
    self.setItemText(row, 4, main_force.get("action", _("未知")))

    tick_flow = analysis.get("tick_flow", {})
    self.setItemText(row, 5, str(tick_flow.get("large_trades", 0)))
else:
    for col in range(1, 6):
        self.setItemText(row, col, "-")
```

**字段映射**：支撑位/阻力位 → `price`；价格深度 → `depth_ratio`；`or {}` 让空数据走 `0` 兜底。

---

### 修复 B — 资金流聚合失效（新增 tick 缓冲区）

**文件**：`vnpy_china_analysis/money_flow/analyzer.py`

#### B.1 构造函数追加状态字段

```python
def __init__(self, thresholds: Optional[Dict[MoneyFlowLevel, float]] = None) -> None:
    self.classifier = MoneyFlowClassifier(thresholds)
    self.indicator = MoneyFlowIndicator()
    self.flow_history: Dict[str, List[MoneyFlowData]] = {}      # 聚合快照（供 get_flow_summary）
    self.tick_history: Dict[str, List[TickFlowData]] = {}       # 原始 tick 缓冲（供 update 聚合）
    self.max_tick_cache = 1000                                   # 单标的 tick 缓冲上限
    # Level1 方向推断 / 成交量差分所需状态（供 tick_adapter 复用）
    self._last_price: Dict[str, float] = {}
    self._last_dir: Dict[str, str] = {}
    self._last_volume: Dict[str, int] = {}
```

#### B.2 update()

```python
def update(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
    tick_flow = TickFlowData(
        symbol=symbol,
        datetime=data.get("datetime", datetime.now()),
        price=data.get("price", 0.0),
        volume=data.get("volume", 0),
        amount=data.get("amount", 0.0),
        direction=data.get("direction", "buy"),
        function_code=data.get("function_code", 1)
    )
    # 写入 tick 缓冲并限长
    buf = self.tick_history.setdefault(symbol, [])
    buf.append(tick_flow)
    if len(buf) > self.max_tick_cache:
        del buf[:-self.max_tick_cache]
    # 用窗口内全部 tick 聚合（analyze 内部按 window_minutes 过滤 datetime）
    result = self.analyze(symbol, buf)
    return {
        "symbol": symbol,
        "datetime": datetime.now(),
        "flow_data": result,
        "structure": self.get_flow_structure(symbol)
    }
```

#### B.3 clear()

```python
def clear(self, symbol: Optional[str] = None) -> None:
    if symbol:
        self.flow_history.pop(symbol, None)
        self.tick_history.pop(symbol, None)
        self._last_price.pop(symbol, None)
        self._last_dir.pop(symbol, None)
        self._last_volume.pop(symbol, None)
    else:
        self.flow_history.clear()
        self.tick_history.clear()
        self._last_price.clear()
        self._last_dir.clear()
        self._last_volume.clear()
    self.classifier.clear_cache(symbol)
    self.indicator.clear_cache(symbol)
```

---

### 修复 C — tick 事件分发失效（Level1 方向推断 + 成交量差分）

**决策**：实盘为 **Level1 数据**，`TickData` 无主动买卖方向，采用 **方向推断**。

**Review 关键发现（C.3）**：已核实 QMT gateway（`patches/vnpy_qmt/md.py:95`）只填 `volume`（累计量），**未填 `last_volume`**：
```python
tick = TickData(..., volume=data['volume'], ...)   # 累计成交量，非本笔
```
故 `tick.last_volume` 在 QMT 下为 `None/0`。若 `on_tick` 仅靠 `last_volume`，所有 tick 会被跳过、`tick_history` 永远为空。**方案必须在 adapter 内直接实现成交量差分 fallback**，不能等实盘接入再补。

#### C.1 新增 TickData→TickFlowData 适配器（双路径成交量 + 方向推断）

**文件**：新建 `vnpy_china_analysis/adapters/tick_adapter.py`

```python
"""TickData 适配器

将 vnpy TickData（Level1）转换为模块内部 TickFlowData。
Level1 无主动方向、QMT 不填 last_volume，故需：
1. 成交量：优先 last_volume，fallback 到累计 volume 差分
2. 方向：成交价 vs 最优买卖盘推断（内外盘法）
"""

from typing import Dict
from vnpy.trader.object import TickData
from ..objects.types import TickFlowData


def tick_to_flow(
    tick: TickData,
    last_price: Dict[str, float],
    last_dir: Dict[str, str],
    last_volume: Dict[str, int]
) -> TickFlowData:
    """TickData → TickFlowData（Level1 推断）

    Args:
        tick: vnpy TickData
        last_price: 各 symbol 上一笔价格（趋势兜底用，外部维护）
        last_dir: 各 symbol 上一笔方向（持平沿用用，外部维护）
        last_volume: 各 symbol 上一笔累计成交量（差分用，外部维护）

    Returns:
        TickFlowData
    """
    symbol = tick.symbol
    price = tick.last_price

    # 1. 成交量：优先 last_volume，fallback 到累计 volume 差分
    prev_vol = last_volume.get(symbol, 0)
    cur_vol = int(tick.volume or 0)
    if tick.last_volume and tick.last_volume > 0:
        trade_vol = int(tick.last_volume)
    else:
        trade_vol = cur_vol - prev_vol if cur_vol > prev_vol else 0
    last_volume[symbol] = cur_vol

    # 2. 方向：成交价 vs 最优买卖盘（内外盘法）
    if tick.ask_price_1 > 0 and price >= tick.ask_price_1:
        direction = "buy"          # 吃掉卖一 → 主动买
    elif tick.bid_price_1 > 0 and price <= tick.bid_price_1:
        direction = "sell"         # 砸给买一 → 主动卖
    else:
        prev = last_price.get(symbol)         # 盘口间成交：趋势兜底
        if prev is None or price == prev:
            direction = last_dir.get(symbol, "buy")   # 持平沿用
        else:
            direction = "buy" if price > prev else "sell"

    last_price[symbol] = price
    last_dir[symbol] = direction

    return TickFlowData(
        symbol=symbol,
        datetime=tick.datetime,
        price=price,
        volume=trade_vol,
        amount=price * trade_vol,
        direction=direction,
        function_code=0
    )
```

#### C.2 MoneyFlowAnalyzer 实现 on_tick

**文件**：`money_flow/analyzer.py`，新增方法

```python
def on_tick(self, tick: "TickData") -> None:
    """实时 Tick 驱动资金流分析（Level1）

    Args:
        tick: vnpy TickData
    """
    from ..adapters.tick_adapter import tick_to_flow
    flow = tick_to_flow(tick, self._last_price, self._last_dir, self._last_volume)

    # 跳过无新增成交量（避免 0 成交污染聚合）
    if flow.volume <= 0:
        return

    buf = self.tick_history.setdefault(tick.symbol, [])
    buf.append(flow)
    if len(buf) > self.max_tick_cache:
        del buf[:-self.max_tick_cache]

    self.analyze(tick.symbol, buf)
```

#### C.3 engine 分发保持不变

`engine.py:254-268` 的 `hasattr` 鸭子类型分发**无需改动**。analyzer 实现 `on_tick` 后分发自然生效。
后续若 `Level2Analyzer`/`TechnicalAnalyzer` 需实时 tick，各自实现 `on_tick` 即可（OCP）。

---

### 修复 D — 开盘价方向判断错误

**文件**：`vnpy_china_analysis/auction/open_predict.py`

#### D.1 predict() 补存 pre_close（第 109-114 行）

```python
self.prediction_history[symbol].append({
    "datetime": datetime.now(),
    "predicted_price": predicted_price,
    "pre_close": pre_close,          # 新增：方向判断基准
    "actual_price": None,
    "confidence": confidence
})
```

#### D.2 get_prediction_accuracy() 真方向判断 + None 兼容（第 164-175 行）

> **Review 修正**：`pre_close=0` 会让 `(actual_price - 0) > 0` 恒 True，方向判断退化为「只要预测价>0 且实际价>0 即正确」，**虚高准确率**。改用 `None` 检查，跳过无基准记录。

```python
for p in predictions:
    error = abs(p["predicted_price"] - p["actual_price"]) / p["actual_price"]
    errors.append(error)

    # 方向判断：必须有有效基准（pre_close），否则跳过（不计入 correct，但仍计入误差与分母）
    pre_close = p.get("pre_close")
    if pre_close is not None and pre_close > 0:
        pred_dir = (p["predicted_price"] - pre_close) > 0
        actual_dir = (p["actual_price"] - pre_close) > 0
        if pred_dir == actual_dir:
            correct_direction += 1
```

- 分母 `len(predictions)` 不变；旧记录（无 `pre_close`）跳过方向判断，不影响误差统计。
- 准确率语义：**有基准记录的方向正确率**，不会虚高。

---

### 修复 E — 历史资金流金额双重换算（删除 /10000）

**文件**：`vnpy_china_analysis/ui/widget.py`
**位置**：`MoneyFlowWidget.update_historical_table()`（第 519-553 行）与 `update_historical_summary()`（第 555-568 行）

**改动**：删除所有 `/ 10000`，单位本就是「元」，直接进 `format_amount`（与实时路径一致）。

`update_historical_table`（6 处）：
```python
main_inflow = data.get("main_net_amount", 0)                    # 删 / 10000
super_large = data.get("super_large_net_amount", 0)             # 删 / 10000
large = data.get("large_net_amount", 0)                         # 删 / 10000
medium = data.get("medium_net_amount", 0)                       # 删 / 10000
small = data.get("small_net_amount", 0)                         # 删 / 10000
net_inflow = data.get("total_net_amount", 0)                    # 删 / 10000
```

`update_historical_summary`（2 处）：
```python
total_main_inflow = sum(d.get("main_net_amount", 0) for d in data_list)     # 删 / 10000
total_net_inflow = sum(d.get("total_net_amount", 0) for d in data_list)     # 删 / 10000
```

---

## 3. 测试计划（TDD，修复时配套补测试）

扩展 `tests/test_analysis.py`，并顺带修 #9 硬编码路径：

| 修复 | 测试用例 | 断言 |
|------|---------|------|
| A | `get_support_level` 空 history + 有数据，调 UI 填充 | 不抛 TypeError；空数据显默认 |
| B | 连续 `update()` 两条 tick | `analyze` 收到 ≥2 条（聚合生效） |
| C | `tick_adapter` ask1 成交→buy；bid1 成交→sell；盘口间上涨→buy | 方向推断正确 |
| C | QMT 场景 `last_volume=0`，连续两 tick `volume` 递增 | 差分得到正确 `trade_vol` |
| C | 发 tick Event | `MoneyFlowAnalyzer.on_tick` 被调用，`tick_history` 非空 |
| D | predicted>pre_close 且 actual>pre_close | `accuracy` 计入正确方向 |
| D | 旧记录无 `pre_close` | 跳过方向判断，不虚高准确率 |
| E | `main_net_amount=1e8` 经历史路径 | 显示「亿」量级，与实时路径一致 |

**#9 路径修复**：`tests/test_analysis.py:4` 硬编码 `/Users/berton/Github/vnpy`，改为 `conftest.py` 注入或相对路径。

---

## 4. 修复顺序

```
A（止血崩溃）
  └─→ B（恢复聚合，为 C 提供缓冲基础）
        └─→ D（独立、低风险）
              └─→ E（独立、删行，低风险）
                    └─→ C（依赖 tick_adapter 新建，最后做）
                          └─→ 补测试（TDD 回归）
```

---

## 5. 决策记录

| 决策点 | 选择 | 依据 |
|--------|------|------|
| #6 方向来源 | **Level1 方向推断** | 实盘为 Level1，无主动方向 |
| #6 成交量 | **last_volume 优先 + volume 差分 fallback** | Review 确认 QMT 不填 `last_volume`，必须双路径 |
| #1/#4 update 改法 | **新增 tick 缓冲区** | 职责分离，对外契约不变 |
| #2 旧数据兼容 | **None 检查跳过** | `pre_close=0` 会虚高准确率 |
| #5 金额单位 | **删 /10000** | Review 确认 `main_net_amount` 单位为「元」 |
| #7 clear 逻辑 | **不修（误报）** | 当前逻辑正确 |
| #9 硬编码路径 | **顺带修复** | 否则 Windows 下测试无法运行 |

---

## 6. 风险与回滚

- **B 风险**：`update()` 行为变化（聚合从「单条」变「窗口」），数值更准确但与旧行为不同。对外返回结构不变。
- **C 风险**：方向推断 + 成交量差分均为近似。**缓解**：`on_tick` 跳过 0 成交；差分对 `volume` 回退（累计量减小）取 0。
- **D 风险**：旧记录无 `pre_close` 被跳过，准确率样本变小但更真实。
- **E 风险**：无；纯删行，与实时路径对齐。
- **回滚**：改动按文件隔离，git 可按文件粒度回滚。A/B/D/E/C 互相独立（C 依赖 B 的缓冲字段）。

---

*v2 已纳入 review 反馈（C.3 差分、D.2 None、#5 删除、C.1 通过）。按「修复顺序」逐项实施，每项完成后补测试并回归。*
