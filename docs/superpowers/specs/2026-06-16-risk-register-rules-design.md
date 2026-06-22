# 补完 `_register_custom_rules` 规则注册 设计

> 日期：2026-06-16 | 状态：待 review（v2，已修正 review 反馈）| 模块：`vnpy_china_rules/risk`

## 背景

`vnpy_china_rules/risk/manager.py` 的 `AStockRiskManager._register_custom_rules`（约 105-124 行）当前用 `importlib` 动态加载 `rules/*_rule.py`，但**加载后不取类、不注册到 `risk_engine`**——"成功加载"日志是假象，4 个自定义 A股风控规则（`CapitalRiskRule`/`PositionControlRule`/`StopProfitLossRule`/`TradingLimitRule`）实际未注册，即使安装了 vnpy_riskmanager 也不生效。

## 目标

补完注册逻辑，让 4 个 A股规则在 vnpy_riskmanager 已安装时**完整生效**（按规则设计分工）：

1. **下单拦截**：`CapitalRiskRule`/`PositionControlRule`/`TradingLimitRule` 的 `check_allowed` 在 `send_order` 拦截违规委托
2. **状态更新**：规则的 `on_trade`/`on_tick`/`on_timer`/`on_order` 回调更新内部状态（`StopProfitLossRule` 的 `check_allowed` 恒为 True，其作用是 `on_tick` 监控行情触发止损止盈日志，不拦截委托）
3. **告警联动**：`CapitalRiskRule`/`PositionControlRule` 触发告警（`_trigger_alert`）联动到 `AStockRiskManager` 告警系统（通过 `set_risk_manager`）

## 接口约束（源码确认）

### `RiskEngine.add_rule(rule_class)`（vnpy_riskmanager engine.py）

```python
def add_rule(self, rule_class: type[RuleTemplate]) -> None:
    rule_setting: dict = self.setting.get(rule_class.name, {})
    rule: RuleTemplate = rule_class(self, rule_setting)   # 实例化
    self.rules[rule.name] = rule
    self.field_name_map.update(rule.parameters)
    self.field_name_map.update(rule.variables)
```

接收**规则类**，内部 `rule_class(risk_engine, setting)` 实例化，存入 `rules[rule.name]`。

### `RuleTemplate.__init__(risk_engine, setting)`（template.py）

绑定 `self.risk_engine`、`self.active=True`、合并 `parameters`（加 `"active"`）、调 `on_init()`、`update_setting(setting)`。

### `RiskEngine.__init__` 流程

`load_rules()`（加载内置规则并 `add_rule`）→ `register_events()`（按 `needs_callback` 检测重写的 `on_tick/on_order/on_trade/on_timer`，append 到 `tick_rules` 等并注册）→ `patch_functions()`。

### `needs_callback(rule, method_name)`

```python
rule_method = getattr(rule, method_name)
base_method = getattr(RuleTemplate, method_name)
return rule_method.__func__ is not base_method
```

比较**实例**方法与基类方法（重写才 True）。在 `add_rule`（实例化）后调用时，规则方法已绑定子类重写版本，比较有效。

### `EventEngine.register`（vnpy/event/engine.py:111-118）

```python
def register(self, type: str, handler: HandlerType) -> None:
    """Every function can only be registered once for each event type."""
    handler_list: list = self._handlers[type]
    if handler not in handler_list:
        handler_list.append(handler)
```

幂等（去重）。**但本设计不依赖此内部实现**，每事件类型显式 register 一次（见 §2）。

### 关键约束

`register_events` 在 `RiskEngine.__init__` 时跑完。`_init_risk_manager` 在 `add_app`（触发 `__init__`）之后才调 `_register_custom_rules`，故后 `add_rule` 的规则**事件回调不会自动注册**，必须手动补。

## 设计

### 1. 注册主流程（重写 `_register_custom_rules`）

**前置条件**：此方法仅在 `_init_risk_manager` 成功后调用。`_init_risk_manager` 首行 `from vnpy_riskmanager import RiskManagerApp` 已保证 vnpy_riskmanager 可用，故 `vnpy_china_rules.risk.rules` 可直接导入、4 个规则类必非 None。**无需 None 检查**（v1 的 `if rule_class is None` 是死代码，已删除——它只在 `risk/__init__.py` 降级路径有意义，但运行时到不了这里）。

```python
def _register_custom_rules(self):
    """注册 A股自定义风控规则到 vnpy_riskmanager 引擎

    前置：仅 _init_risk_manager 成功后调用（vnpy_riskmanager 已安装）。
    """
    from vnpy_china_rules.risk.rules import (
        CapitalRiskRule, PositionControlRule,
        StopProfitLossRule, TradingLimitRule,
    )

    rule_classes = [
        CapitalRiskRule, PositionControlRule,
        StopProfitLossRule, TradingLimitRule,
    ]

    registered_rules = []
    for rule_class in rule_classes:
        try:
            self.risk_engine.add_rule(rule_class)
            rule = self.risk_engine.rules.get(rule_class.name)
            if rule is not None:
                registered_rules.append(rule)
            else:
                self.write_log(f"注册风控规则未找到实例: {rule_class.name}")
        except Exception as e:
            self.write_log(f"注册风控规则失败 {rule_class.__name__}: {e}")

    self._register_rule_events(registered_rules)

    # 告警联动：仅 CapitalRiskRule/PositionControlRule 有 set_risk_manager
    for rule in registered_rules:
        if hasattr(rule, "set_risk_manager"):
            rule.set_risk_manager(self)
        self.write_log(f"成功注册风控规则: {rule.name}")
```

### 2. 事件回调补注册（新增 `_register_rule_events`）

每事件类型只 register 一次（显式去重，不依赖 `EventEngine.register` 内部幂等性）：

```python
def _register_rule_events(self, rules):
    """为新注册的规则补注册事件回调

    register_events 已在 RiskEngine.__init__ 跑完，后 add_rule 的规则需手动补。
    needs_callback 在 add_rule（实例化）后调用，规则方法已绑定子类重写版本。
    """
    from vnpy.trader.event import (
        EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_TIMER,
    )

    re = self.risk_engine
    buckets = [
        ("on_tick", re.tick_rules, EVENT_TICK, re.process_tick_event),
        ("on_order", re.order_rules, EVENT_ORDER, re.process_order_event),
        ("on_trade", re.trade_rules, EVENT_TRADE, re.process_trade_event),
        ("on_timer", re.timer_rules, EVENT_TIMER, re.process_timer_event),
    ]

    # 规则加入对应 bucket；记录哪些事件类型需要注册
    events_to_register = []
    for method_name, bucket, event_type, handler in buckets:
        added = False
        for rule in rules:
            if re.needs_callback(rule, method_name) and rule not in bucket:
                bucket.append(rule)
                added = True
        if added:
            events_to_register.append((event_type, handler))

    # 每事件类型只 register 一次（显式去重，不依赖 EventEngine.register 幂等性）
    for event_type, handler in events_to_register:
        re.event_engine.register(event_type, handler)
```

依赖 RiskEngine 的 public/半 public 接口：`add_rule`、`needs_callback`、`process_tick_event`/`process_order_event`/`process_trade_event`/`process_timer_event`、`tick_rules`/`order_rules`/`trade_rules`/`timer_rules`、`event_engine`、`rules`。

### 3. 告警联动

`add_rule` 后对有 `set_risk_manager` 的规则（`CapitalRiskRule`、`PositionControlRule`）调 `rule.set_risk_manager(self)`，使 `_trigger_alert` → `_risk_manager._trigger_alert` 联动到 `AStockRiskManager` 告警系统（`_active_alerts` + 订阅回调）。

**`hasattr` 鸭子类型说明**：当前仅 `CapitalRiskRule`/`PositionControlRule` 定义了 `set_risk_manager`（`StopProfitLossRule`/`TradingLimitRule` 无）。用 `hasattr` 区分是有意的鸭子类型。理论风险：若 `RuleTemplate` 基类未来新增同名方法（不同语义），`hasattr` 静默通过。更稳健方案是定义 `AlertableRule` Mixin 让规则显式继承，但需改规则类继承（超出"不改规则类"范围），列为未来改进。当前 `RuleTemplate`（vnpy_riskmanager template.py）无 `set_risk_manager`，`hasattr` 行为正确。

### 4. 降级处理

- **vnpy_riskmanager 缺失**：`_init_risk_manager` 的 `from vnpy_riskmanager import ...` 抛 ImportError → `_register_custom_rules` 根本不被调用（与现有降级行为一致）
- **单规则 add_rule 异常**：`write_log` 降级，继续注册其他规则

## 测试策略

### 单测（新建 `vnpy_china_rules/tests/test_risk_manager.py`，不需 vnpy_riskmanager）

- `unittest.mock.patch` 替换 `vnpy_china_rules.risk.rules` 的 4 个类为 fake（带 `name` 类属性；其中两个带 `set_risk_manager`）
- `MagicMock` 模拟 risk_engine：`add_rule`（把类加入 `rules` dict）、`needs_callback`（按 fake 规则重写情况 stub True/False）、`tick_rules`/`order_rules`/`trade_rules`/`timer_rules`（真实 list）、`event_engine.register`、`process_xxx_event`
- 验证：
  - 4 个规则各调 `add_rule` 一次
  - `needs_callback=True` 的回调 append 到对应 bucket
  - **规则只重写部分回调时**（模拟），未重写的 bucket 不含该规则
  - **规则已在 bucket 时**不重复 append（幂等）
  - **每事件类型 `event_engine.register` 只调用一次**（不重复注册）
  - 有 `set_risk_manager` 的规则调用它（注入 `self`），无的不调用
  - `add_rule` 抛异常时降级日志、继续其他规则

### 集成测试（新建 `vnpy_china_rules/tests/test_risk_integration.py`，默认 `@skipUnless RUN_INTEGRATION`）

真实 vnpy_riskmanager + RiskEngine + 4 规则，验证：
- 注册后 `risk_engine.rules` 含 4 个规则
- `CapitalRiskRule`/`PositionControlRule`/`TradingLimitRule` 的 `check_allowed` 对违规委托返回 False；`StopProfitLossRule.check_allowed` 恒 True
- `on_trade` 推送后规则状态更新
- `CapitalRiskRule` 触发告警时 `AStockRiskManager._active_alerts` 增加
- **重复调用 `_register_rule_events` 不会导致回调多次触发**（每事件 handler 只注册一次）

## 验收标准

- [ ] vnpy_riskmanager 已安装时，4 个规则注册到 `risk_engine.rules`
- [ ] `CapitalRiskRule`/`PositionControlRule`/`TradingLimitRule` 的 `check_allowed` 生效（`send_order` 拦截违规委托）
- [ ] `StopProfitLossRule.check_allowed` 恒为 True（仅 `on_tick` 监控行情，设计如此，不拦截）
- [ ] `on_trade`/`on_tick`/`on_timer` 回调触发，且**每事件 handler 只注册一次**（重复注册不导致回调多次执行）
- [ ] `CapitalRiskRule`/`PositionControlRule` 的 `set_risk_manager` 被调用（告警联动）
- [ ] vnpy_riskmanager 缺失时不阻断（`_init_risk_manager` 降级）
- [ ] 单规则异常不阻断其他规则注册
- [ ] 单测全绿（不需 vnpy_riskmanager）；集成测试默认跳过

## 范围外（YAGNI）

- 不改 4 个规则类逻辑。**已知不完整项**（均不在本次范围）：`CapitalRiskRule._check_single_trade_loss` 恒返回 False、`TradingLimitRule.on_trade` 无实质逻辑、`StopProfitLossRule.on_tick` 平仓仅记录日志
- 不改 RiskEngine 源码（vnpy_riskmanager 第三方）
- 不实现规则参数持久化（`risk_manager_setting.json` 由 vnpy_riskmanager 管理）
- 不实现 GUI 集成
- `AlertableRule` Mixin（`hasattr` 鸭子类型的稳健替代）列为未来改进，需改规则类继承

## 变更记录

- **v2**（本次）：修正 review 反馈——(1) 事件 register 改为每事件类型一次，不依赖 `EventEngine.register` 幂等性（已源码确认幂等，但显式去重更稳健）；(2) 删除 `None` 检查死代码，注明 `_register_custom_rules` 前置条件；(3) `hasattr` 鸭子类型加说明 + Mixin 列为未来改进；(4) `needs_callback` 时序注释；(5) 补测试边界（部分回调重写、幂等、每事件一次）；(6) 验收标准区分 `StopProfitLossRule`（不拦截）；(7) 集成测试覆盖重复注册；(8) 范围外注明已知不完整项
- **v1**：初版设计
