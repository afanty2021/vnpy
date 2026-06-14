# vnpy_china_backtest 代码审查修复方案

> 创建日期：2026-06-14（v2）
> 来源：模块代码审查报告（13 项）经逐行核实 + 两轮 review 后的修复计划
> 状态：**已 review 通过，执行中**（v2 纳入 review 反馈 + 新增 F11）

---

## 0. 背景与范围

本文档针对 `vnpy_china_backtest` 模块的代码审查报告，记录核实结论与逐项修复方案。
**先核实、再修复**——审查报告绝大多数成立，#7 的修复方向与 #12 的性质经核实已纠正。

### 修复范围（11 项）

| 编号 | 问题 | 文件 | 核实结论 |
|------|------|------|---------|
| F1（#1） | 部分平仓 PnL 算错，连累胜率/盈亏比 | `report/metrics.py` | ✅ 属实 |
| F2（#2） | 连续盈亏按 symbol 序非时间序，且数值复用 F1 错算法 | `report/metrics.py` | ✅ 属实 |
| F3（#3） | `load_data` 未清理 pre_closes | `engine.py` | ✅ 属实 |
| F4（#4） | sortino_ratio 从不计算 | `report/metrics.py` | ✅ 属实 |
| F5（#5） | `get_realized_pnl` 存桩恒返回 0 | `rules/t1_simulator.py` | ✅ 属实 |
| F6（#6） | ImpactCost 滑点公式永不执行（market_volume 恒 0） | `engine.py` + `slippage.py` | ✅ 属实 |
| F7（#7） | 过户费 `max(transfer_fee, 0.1)` 强制了不存在的最低值 | `cost.py` | ✅ 属实 |
| F8（#8） | annual_days 未贯通 engine→calculator | `engine.py` | ✅ 属实 |
| F9（#9） | `_calculate_monthly_returns` 存桩返回 `{}` | `report/metrics.py` | ✅ 属实 |
| F10（#11） | test_backtest.py 硬编码 macOS 路径 | `tests/test_backtest.py` | ✅ 属实 |
| F11（#10） | stop_backtest 不实际停止（回测同步阻塞 GUI 线程） | `ui/widget.py` | ✅ 属实（review 决定本期处理） |

### 暂不修（2 项，需评估/设计）

| 编号 | 报告判定 | 决定 | 理由 |
|------|---------|------|------|
| #12 | 策略冗余 pre_closes 赋值 | **暂不修** | 非简单冗余：`process_bar`（engine.py:177）把 pre_closes 设成「当前 bar 收盘」本身名实不符（应为「前一交易日收盘」）。删除策略侧赋值会让 buy 用上一根值反而更接近真「昨收」。**涉及 pre_closes 整体语义设计，需统一重设计而非删一行** |
| #13 | 单标的 current_prices 更新不全 | **暂不修（当前不触发）** | `current_prices` 是累积更新的「最新已知价」字典；持仓标的必被 bar 处理过，不会 None。多标的时其他标的保持各自最后一根 bar 的 close（正确语义）。仅理论风险 |

---

## 1. 核实结论（基于代码逐行确认）

> 全部问题文件均位于 `vnpy_china_backtest/` 模块下（v1 文档曾误写 `vnpy_china_analysis`，已纠正）。

### F1. 部分平仓 PnL 算错（#1）— 属实，最严重

`report/metrics.py:298-314` `_calculate_stock_pnl` 用 `sell_value - buy_value` 未匹配买卖，部分平仓必错（买200×10卖100×15 → 返回-500，实际+500）。喂给 `win_rate`（190）+ `profit_loss_ratio`（201），胜率/盈亏比连带失真。

### F2. 连续盈亏无序（#2）— 属实，双重错

`report/metrics.py:248-277`：`stock_pnls` 按 `symbol` 聚合后遍历 `values()`（symbol 插入序，非时间序），且每个 symbol 的 pnl 仍用 F1 错算法。

### F3. pre_closes 未清理（#3）— 属实

`engine.py:149-162` `load_data` 清了 history_bars/current_prices/equity_curve，独不清 pre_closes。`if bar.vt_symbol not in self.pre_closes`（161）只写入新 symbol，老 symbol 残留。

### F4. sortino 不算（#4）— 属实

`report/metrics.py:25` 声明 `sortino_ratio`，`_calculate_basic_metrics`（115-166）只算 Sharpe。

### F5. realized_pnl 存桩（#5）— 属实

`rules/t1_simulator.py:180-197` 循环体 `pass` 恒返回 0。`_process_sell`（199）已按 FIFO 更新 sold_volume，但未累加盈亏。

### F6. ImpactCost 退化（#6）— 属实

`engine.py:303` 永传 `market_volume=0` → `slippage.py:128` 走 `price*0.0005` 固定分支，冲击公式（134）永不执行。

### F7. 过户费 max(0.1)（#7）— 属实，报告修复方向错误

`cost.py:112`。2022/4 起 A 股过户费沪深统一双边万 0.1、**无最低值**。报告「沪市1元」是过时规则。**正确修复：删除 max**。

### F8. annual_days 未贯通（#8）— 属实

`engine.py:49` `MetricsCalculator()` 用默认 240，engine 的 `self.annual_days`（63）从未传入。

### F9. monthly_returns 存桩（#9）— 属实

`report/metrics.py:316-323` `return {}`。

### F10. 测试硬编码路径（#11）— 属实

`tests/test_backtest.py:4` macOS 绝对路径，Windows 下无效。

### F11. stop_backtest 不停止（#10）— 属实

- `ui/widget.py:328` `start_backtest` 同步调 `_run_backtest`（372-435），回测阻塞 GUI 线程
- `_run_backtest:398-399` `on_progress` 直接 `self.progress_bar.setValue`（跨线程隐患）
- `stop_backtest:553-556` 仅 `show_status` + 进度归零，**无中断机制**

---

## 2. 逐项修复方案

### 修复 F1+F2 — PnL 与连续盈亏（FIFO 匹配，共享实现）

**文件**：`vnpy_china_backtest/report/metrics.py`

抽一个共享 FIFO 匹配方法，F1（胜负/盈亏比）与 F2（连续盈亏）共用，消除 #2 复用 #1 错算法的根因（DRY）。

#### 共享方法：按时间序产出「已实现盈亏事件」

```python
def _compute_realized_events(
    self,
    trades: List[TradeData]
) -> List[float]:
    """FIFO 匹配买卖，按时间序返回每笔卖出的已实现盈亏

    未平仓部分不计入（符合「已实现盈亏」语义）。
    跨标的统一按 datetime 排序，供连续盈亏统计。

    Returns:
        按时间序的已实现盈亏列表（每元素对应一次卖出平仓）
    """
    if not trades:
        return []

    sorted_trades = sorted(trades, key=lambda t: t.datetime or datetime.min)

    # 每个 symbol 的 FIFO 买入队列：[[price, remaining_volume], ...]
    queues: Dict[str, List[List]] = {}
    events: List[float] = []

    for t in sorted_trades:
        q = queues.setdefault(t.symbol, [])
        if t.direction == Direction.LONG:
            q.append([t.price, t.volume])
        else:  # SHORT：FIFO 匹配买入
            remaining = t.volume
            realized = 0.0
            while remaining > 0 and q:
                buy_price, buy_vol = q[0]
                matched = min(remaining, buy_vol)
                realized += matched * (t.price - buy_price)
                remaining -= matched
                if matched >= buy_vol:
                    q.pop(0)
                else:
                    q[0][1] = buy_vol - matched
            events.append(realized)

    return events
```

#### F1 改 `_calculate_stock_pnl`

```python
def _calculate_stock_pnl(self, trades: List[TradeData]) -> float:
    """计算单只股票已实现盈亏（FIFO 匹配，仅已平仓部分）"""
    return sum(self._compute_realized_events(trades))
```
`win_rate` / `profit_loss_ratio` 调用点（189-210）不变，现拿到正确的已实现盈亏。

#### F2 改 `_calculate_trade_stats` 连续盈亏段（247-277）

```python
# 按时间序的已实现盈亏事件（跨标的统一），替代原先按 symbol 聚合的无序遍历
events = self._compute_realized_events(trades)

max_consecutive_wins = 0
max_consecutive_losses = 0
current_wins = 0
current_losses = 0

for pnl in events:
    if pnl > 0:
        current_wins += 1
        current_losses = 0
        max_consecutive_wins = max(max_consecutive_wins, current_wins)
    elif pnl < 0:
        current_losses += 1
        current_wins = 0
        max_consecutive_losses = max(max_consecutive_losses, current_losses)
    else:
        current_wins = 0
        current_losses = 0

metrics.max_consecutive_wins = max_consecutive_wins
metrics.max_consecutive_losses = max_consecutive_losses
```

**设计要点**：FIFO 模式参照 `t1_simulator._process_sell`（199-217）已验证实现；`_compute_realized_events` 跨标的按时间排序，F1/F2 语义自洽；未平仓不计入。

---

### 修复 F3 — pre_closes 清理

**文件**：`vnpy_china_backtest/engine.py`，`load_data`（149-154）

```python
def load_data(self, bars: List[BarData]) -> None:
    """加载历史数据"""
    self.history_bars.clear()
    self.pre_closes.clear()          # 新增：与 history_bars 等同步清理

    self.current_datetime = None
    self.current_prices.clear()
    self.equity_curve = [self.cash]
    ...
```

---

### 修复 F4 — sortino_ratio

**文件**：`vnpy_china_backtest/report/metrics.py`，`_calculate_basic_metrics` Sharpe 后（162 之后）

```python
# 索提诺比率（仅用负收益计算下行标准差）
if returns:
    downside_returns = [r for r in returns if r < 0]
    if downside_returns:
        downside_std = (
            sum(r ** 2 for r in downside_returns) / len(downside_returns)
        ) ** 0.5
        if downside_std > 0:
            avg_return = sum(returns) / len(returns)
            metrics.sortino_ratio = (
                (avg_return * self.annual_days)
                / (downside_std * math.sqrt(self.annual_days))
            )
```

---

### 修复 F5 — get_realized_pnl（在 _process_sell 内累加，一次 FIFO）

> **v2 改进**（采纳 review）：消除原方案 `_sell_records` 的二次 FIFO 重复。改为在 `_process_sell` 匹配成交时直接累加到 `_realized_pnl`，`get_realized_pnl` 仅取值。

**文件**：`vnpy_china_backtest/rules/t1_simulator.py`

#### 5.1 构造函数追加累计盈亏字段

```python
def __init__(self):
    self._buy_records: Dict[str, List[BuyRecord]] = {}
    self._positions: Dict[str, PositionRecord] = {}
    # 已实现盈亏累计 {symbol: pnl}，由 _process_sell 在 FIFO 匹配时累加
    self._realized_pnl: Dict[str, float] = {}
```

#### 5.2 _process_sell 加 sell_price 参数并累加（199-217）

```python
def _process_sell(self, symbol: str, volume: int, trade_date: date, sell_price: float) -> None:
    """处理卖出（FIFO原则），同时累加已实现盈亏"""
    if symbol not in self._buy_records:
        return

    self._realized_pnl.setdefault(symbol, 0.0)
    remaining = volume
    for record in self._buy_records[symbol]:
        if remaining <= 0:
            break
        if record.buy_date >= trade_date:
            continue
        available = record.volume - record.sold_volume
        if available > 0:
            sold = min(remaining, available)
            record.sold_volume += sold
            # 在同一次 FIFO 匹配中累加已实现盈亏（避免二次匹配）
            self._realized_pnl[symbol] += sold * (sell_price - record.price)
            remaining -= sold
```

#### 5.3 record_sell 传入 sell_price（101-102）

```python
# 记录卖出（使用FIFO原则）—— 传入卖出价供盈亏累加
self._process_sell(symbol, volume, trade_date, sell_price=price)
```

#### 5.4 get_realized_pnl 简化为取值（180-197 重写）

```python
def get_realized_pnl(self, symbol: str) -> float:
    """获取已实现盈亏（由 _process_sell 在 FIFO 匹配时累加）"""
    return self._realized_pnl.get(symbol, 0.0)
```

#### 5.5 reset 同步清理

```python
def reset(self) -> None:
    self._buy_records.clear()
    self._positions.clear()
    self._realized_pnl.clear()        # 新增
```

**要点**：一次 FIFO（在 _process_sell），盈亏计算与 T+1 卖出记录同源，无重复逻辑（DRY）。

---

### 修复 F6 — ImpactCost 市场成交量

**文件**：`vnpy_china_backtest/engine.py` + `slippage.py`

#### 6.1 engine 记录当前 bar 成交量

`__init__` 追加：
```python
self.current_bar_volume: float = 0.0    # 当前 bar 成交量（供 ImpactCost 滑点）
```
`process_bar`（164-180）追加：
```python
self.current_bar_volume = bar.volume
```
`load_data` / `reset` 清理处追加 `self.current_bar_volume = 0.0`。

#### 6.2 _execute_order 传入真实市场量（298-304）

```python
if self.enable_slippage and self.slippage_model:
    price = self.slippage_model.apply(
        price,
        volume,
        direction,
        market_volume=self.current_bar_volume   # 改：传真实 bar 成交量
    )
```

**⚠️ 近似**：策略在 `process_bar` 之前下单（strategies.py:101 buy 在 121 process_bar 之前），首根 bar buy 用 0，走 `slippage.py:128` 兜底分支。可接受（ImpactCost 主要影响大单，边界场景影响小）。

---

### 修复 F7 — 过户费移除 max

**文件**：`vnpy_china_backtest/cost.py`，line 109-112

```python
# 3. 过户费（双向收取，万0.1，2022年4月起沪深统一，无最低值）
transfer_fee = turnover * self.config.transfer_fee_rate
# 删除：transfer_fee = max(transfer_fee, 0.1)  ← 无依据的最低收费
```

---

### 修复 F8 — annual_days 贯通（属性赋值，不重建实例）

> **v2 改进**（采纳 review）：不重建 `MetricsCalculator`，直接赋 `annual_days` 属性——避免未来 calculator 增加状态时被重置。

**文件**：`vnpy_china_backtest/engine.py`

`__init__`（49）：
```python
self.annual_days: int = 240
self.metrics_calculator = MetricsCalculator(annual_days=self.annual_days)
```
`set_parameters`（124）：
```python
self.annual_days = annual_days
self.metrics_calculator.annual_days = annual_days   # 属性赋值，贯通（不重建实例）
```

---

### 修复 F9 — monthly_returns（含长度断言防御）

> **v2 改进**（采纳 review）：加入 `bar_datetimes` 与 `equity_curve` 长度断言，多标的对齐问题提前暴露。

**文件**：`vnpy_china_backtest/report/metrics.py` + `engine.py`

`equity_curve` 是 `List[float]` 无日期，`calculate` 增加可选 `bar_datetimes` 参数；equity_curve[0] 为初始资金，其后每点对应一根 bar。

#### 9.1 MetricsCalculator.calculate 增参

```python
def calculate(
    self,
    trades, equity_curve, trading_days, initial_capital, final_capital,
    total_cost: float = 0.0,
    bar_datetimes: Optional[List[datetime]] = None   # 新增
) -> EnhancedMetrics:
    ...
    metrics.monthly_returns = self._calculate_monthly_returns(
        equity_curve, trading_days, bar_datetimes
    )
```

#### 9.2 实现 _calculate_monthly_returns

```python
def _calculate_monthly_returns(
    self,
    equity_curve: List[float],
    trading_days: int,
    bar_datetimes: Optional[List[datetime]] = None
) -> Dict[str, float]:
    """计算月度收益率

    equity_curve[0] 为初始资金；其后每点对应一根 bar（bar_datetimes 提供日期）。
    无日期信息时返回空字典（向后兼容）。
    """
    if not bar_datetimes or len(equity_curve) < 2:
        return {}

    # 防御：bar_datetimes 必须与 equity_curve 逐点对应（首点为初始资金）
    if len(bar_datetimes) != len(equity_curve) - 1:
        # 长度不一致时无法对齐，返回空避免静默错误
        return {}

    month_start: Dict[str, float] = {}
    month_end: Dict[str, float] = {}

    for i, dt in enumerate(bar_datetimes):
        idx = i + 1
        if idx >= len(equity_curve):
            break
        key = f"{dt.year}-{dt.month:02d}"
        if key not in month_start:
            month_start[key] = equity_curve[idx - 1]
        month_end[key] = equity_curve[idx]

    return {
        k: (month_end[k] - month_start[k]) / month_start[k]
        for k in month_end
        if month_start[k] > 0
    }
```

#### 9.3 engine.calculate_metrics 传入日期 + 断言（435-442）

```python
bar_datetimes = [bar.datetime for bar in self.history_bars.values()]
# 断言：history_bars 插入序应与 equity_curve 逐点对应（首点为初始资金）
assert len(bar_datetimes) == len(equity_curve) - 1, (
    f"bar_datetimes({len(bar_datetimes)}) 与 equity_curve({len(equity_curve)}) 长度不匹配"
)

return self.metrics_calculator.calculate(
    trades=list(self.trades.values()),
    equity_curve=equity_curve,
    trading_days=trading_days,
    initial_capital=initial_capital,
    final_capital=final_capital,
    total_cost=self.total_cost,
    bar_datetimes=bar_datetimes,
)
```

**⚠️ 注意**：`history_bars` key 为 `(datetime, vt_symbol)`，`dict.values()` 在 Python 3.7+ 保插入序。多标的时需确认插入序与 process_bar 调用序一致——断言会在不一致时提前暴露。

---

### 修复 F10 — 测试硬编码路径

**文件**：`vnpy_china_backtest/tests/test_backtest.py`，line 4

```python
import os
import sys
# 项目根目录（本文件上溯三级：tests -> vnpy_china_backtest -> 项目根）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
```

---

### 修复 F11 — UI 线程化（QThread + 取消标志）

> review 决定本期处理 #10。回测移入 worker 线程，stop 真正中断，进度/结果通过 signal 跨线程回传。

**文件**：`vnpy_china_backtest/ui/widget.py`

#### 11.1 新增 BacktestWorker(QThread) + 取消异常

放 widget.py 顶部（ChinaBacktestWidget 之前）。Signal 从项目的 qt 封装导入（实施时确认 `from vnpy.trader.ui.qt import QtCore`，用 `QtCore.Signal`）。

```python
class BacktestCancelled(Exception):
    """回测取消异常（on_progress 检测到取消时抛出，中断 strategy 循环）"""
    pass


class BacktestWorker(QtCore.QThread):
    """回测工作线程

    在子线程执行回测，通过信号回传进度与结果。
    cancel() 设置取消标志；strategy 循环内经 on_progress 检查并中断。
    engine 在本线程内创建与使用，不跨线程共享，线程安全。
    """
    progress = Signal(int)                                   # 0-100 相对进度
    finished_ok = Signal(dict, list, list, list)             # results, trades, equity_curve, daily_logs

    def __init__(self, vt_symbol, bars, capital, strategy_key, config):
        super().__init__()
        self._vt_symbol = vt_symbol
        self._bars = bars
        self._capital = capital
        self._strategy_key = strategy_key
        self._config = config     # {enable_cost/slippage/price_limit/t1}
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        from vnpy_china_backtest.engine import EnhancedBacktestEngine
        from vnpy_china_backtest.strategies import get_strategy

        engine = EnhancedBacktestEngine()
        engine.capital = self._capital
        engine.cash = self._capital
        engine.enable_cost = self._config["enable_cost"]
        engine.enable_slippage = self._config["enable_slippage"]
        engine.enable_price_limit = self._config["enable_price_limit"]
        engine.enable_t1 = self._config["enable_t1"]
        engine.load_data(self._bars)

        # on_progress：检查取消 → 抛异常中断；否则 emit 进度（跨线程安全）
        def on_progress(percent: int) -> None:
            if self._cancelled:
                raise BacktestCancelled()
            self.progress.emit(percent)

        strategy = get_strategy(self._strategy_key)
        try:
            daily_logs = strategy.run(
                engine, self._bars, self._vt_symbol, on_progress=on_progress
            )
        except BacktestCancelled:
            return    # 取消：不发 finished_ok

        metrics = engine.calculate_metrics()
        results = {
            "total_return": metrics.total_return,
            "annual_return": metrics.annual_return,
            "max_drawdown": metrics.max_drawdown,
            "sharpe_ratio": metrics.sharpe_ratio,
            "win_rate": metrics.win_rate,
            "profit_loss_ratio": metrics.profit_loss_ratio,
            "avg_holding_days": metrics.avg_holding_days,
            "total_cost": engine.total_cost,
            "total_trades": metrics.total_trades,
            "blocked_orders": engine.blocked_orders,
            "final_equity": engine.get_equity(),
            "bar_count": len(self._bars),
        }
        self.finished_ok.emit(
            results,
            list(engine.trades.values()),
            list(engine.equity_curve),
            daily_logs,
        )
```

#### 11.2 widget 改造

`__init__` 追加：
```python
self._worker: Optional["BacktestWorker"] = None
```

`start_backtest`（283-333）末尾替换同步调用为线程启动：
```python
        # 执行回测（移入 worker 线程，避免阻塞 GUI）
        self._start_btn.setEnabled(False)          # 防重复触发
        self.progress_bar.setValue(20)

        config = {
            "enable_cost": self.enable_cost_checkbox.isChecked(),
            "enable_slippage": self.enable_slippage_checkbox.isChecked(),
            "enable_price_limit": self.enable_price_limit_checkbox.isChecked(),
            "enable_t1": self.enable_t1_checkbox.isChecked(),
        }
        self._worker = BacktestWorker(
            vt_symbol=f"{symbol}.{exchange.value}",
            bars=bars, capital=capital,
            strategy_key=strategy_key, config=config,
        )
        self._worker.progress.connect(self._on_backtest_progress)
        self._worker.finished_ok.connect(self._on_backtest_finished)
        self._worker.finished.connect(self._on_backtest_thread_finished)  # QThread.finished：清理
        self._worker.start()
```

新增槽（跨线程 signal 自动排队到主线程）：
```python
def _on_backtest_progress(self, percent: int) -> None:
    """worker 进度回调（主线程执行）"""
    self.progress_bar.setValue(20 + int(percent * 0.7))

def _on_backtest_finished(self, results, trades, equity_curve, daily_logs) -> None:
    """worker 完成回调（主线程执行）"""
    self.backtest_results = results
    self.trades = trades
    self.equity_curve = equity_curve
    self.daily_logs = daily_logs
    self.update_results()
    self.progress_bar.setValue(100)
    self.show_status(
        _("回测完成：{} 条数据，{} 笔交易").format(
            results.get("bar_count", 0), len(trades)
        )
    )

def _on_backtest_thread_finished(self) -> None:
    """线程结束清理（无论正常/取消/异常）"""
    self._start_btn.setEnabled(True)
    self._worker = None
```

`stop_backtest`（553-556）重写为真正取消：
```python
def stop_backtest(self) -> None:
    """停止回测（设置取消标志，worker 在下一个 on_progress 检查点中断）"""
    if self._worker and self._worker.isRunning():
        self._worker.cancel()
        self.show_status(_("正在停止回测..."))
    else:
        self.progress_bar.setValue(0)
        self.show_status(_("就绪"))
```

#### 11.3 strategy 代码无需改动

`on_progress` 已在每个 bar 调用（strategies.py:85/122/161），cancel 后 `raise BacktestCancelled` 自然传播中断循环。利用现有钩子，不改 strategy 签名（OCP）。

**要点**：
- engine 在 worker 线程内创建使用，纯逻辑无 GUI 依赖，线程安全
- 进度/结果用 Signal 回传（Qt 自动跨线程队列），**不在 worker 线程直接操作 UI 控件**（修复原 `_run_backtest:399` 的跨线程隐患）
- 取消标志在 on_progress 检查点生效（粒度=每根 bar）

**风险**：取消后 engine 状态半途，但 worker 即将销毁，无影响；worker 异常时 `_on_backtest_thread_finished` 仍恢复按钮（finished 信号无条件触发）。

---

## 3. 测试计划（TDD，修复时配套补测试）

报告指出 `test_backtest.py` 是空壳。每项修复补针对性测试：

| 修复 | 测试用例 | 断言 |
|------|---------|------|
| F1 | 买200×10、卖100×15、再卖100×12 | `_calculate_stock_pnl` = 100×5+100×2 = 700 |
| F2 | 两标的交替盈亏事件 | 连续盈亏按时间序，非 symbol 序 |
| F3 | 连续两次 load_data 不同标的 | pre_closes 不残留老标的 |
| F4 | 权益曲线有负收益 | sortino_ratio > 0 |
| F5 | 买100×10、卖100×12 | get_realized_pnl = 200 |
| F6 | engine 设 ImpactCostSlippage + bar volume | apply 走冲击公式分支 |
| F7 | turnover 极小（过户费 < 0.1） | transfer_fee = turnover×rate |
| F8 | engine.set_parameters(annual_days=365) | metrics.annual_return 用 365 |
| F9 | 传 bar_datetimes 跨两月 | monthly_returns 含两个月份键 |
| F9 | bar_datetimes 长度不匹配 | 返回 {} 不崩溃 |
| F11 | worker cancel 后 | finished_ok 不发，线程正常结束 |

---

## 4. 修复顺序（v2：F4 并入第一组）

```
第一组（独立小改，metrics+engine+cost+test，减少文件切换）：
  F3 / F7 / F8 / F10 / F4
      └─→ F1 + F2（核心算法重写，metrics 共享 FIFO，不可拆）
            └─→ F9（monthly，贯通 bar_datetimes，较复杂）
                  └─→ F5（t1_simulator，_process_sell 累加）
                        └─→ F6（engine + slippage 调用链）
                              └─→ F11（UI 线程化，较大，最后）
                                    └─→ 补测试（TDD 回归）
```

---

## 5. 决策记录

| 决策点 | 选择 | 依据 |
|--------|------|------|
| #7 过户费 | **移除 max** | 2022/4 起沪深统一双边万 0.1、无最低（用户已确认） |
| #1/#2 算法 | **FIFO + 时间序** | 参照 `t1_simulator._process_sell` |
| #1/#2 实现 | **共享 `_compute_realized_events`** | 消除 #2 复用 #1 错算法根因（DRY） |
| #5 实现 | **_process_sell 内累加 `_realized_pnl`** | review 改进：消除二次 FIFO，盈亏与 T+1 卖出同源（DRY） |
| #8 实现 | **属性赋值 `metrics_calculator.annual_days`** | review 改进：不重建实例，避免未来状态丢失 |
| #9 防御 | **长度断言 + 不匹配返回 {}** | review 改进：多标的对齐问题提前暴露 |
| #10 UI 线程化 | **本期处理（F11）** | review 决定：QThread + 取消标志 |
| #12 策略冗余 | **暂不修** | 涉及 pre_closes 语义重设计 |
| #13 current_prices | **暂不修** | 当前设计下不触发 |

---

## 6. 风险与回滚

- **F1/F2**：PnL 语义从「净额」变「已实现（FIFO）」，win_rate/profit_loss_ratio/连续盈亏数值变化（更准确），预期内修正。
- **F5**：盈亏在 `_process_sell` 累加，若卖出未走 `record_sell` 则不准。**缓解**：engine.py:340 已确认走 record_sell。
- **F6**：`current_bar_volume` 依赖 bar.volume；首根 bar 边界用 0 兜底。
- **F9**：`history_bars.values()` 插入序需与 equity_curve 对齐，断言会暴露。
- **F11**：UI 线程化是行为级改动（同步→异步）；`_run_backtest` 方法可保留为 worker.run 的参考实现或删除。回测异常需确保 `_on_backtest_thread_finished` 恢复按钮（QThread.finished 无条件触发）。
- **回滚**：改动按文件隔离。F1+F2 强耦合（共享方法）需一起回滚；F11 独立于其他项。

---

*v2 已纳入两轮 review 反馈（路径纠正、F5 消除二次 FIFO、F8 属性赋值、F9 断言、F4 归组、新增 F11）。按「修复顺序」逐项实施，每项完成后补测试并回归。*
