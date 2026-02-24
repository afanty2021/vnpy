# A股交易风险管理系统设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-002
> 优先级：P0

---

## 1. 设计目标

基于 `vnpy_riskmanager` 框架，扩展A股特色风控规则，实现：
- 仓位风控：单股/总仓位/行业/数量限制
- 止损止盈：单笔/移动/组合止损
- 资金风控：日亏损/单笔风险/资金使用
- 交易风控：频率/撤单/价格偏离/连续亏损

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     A股风险管理系统架构                           │
├─────────────────────────────────────────────────────────────────┤
│  【vnpy_riskmanager 基础层】                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ RiskManagerApp │  │ RiskEngine   │  │RuleTemplate  │         │
│  │   (应用层)    │  │   (引擎)     │  │   (模板)     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│  【vnpy_china_rules 规则层】                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ ChinaStock   │  │   Rules      │  │  RiskFilter  │         │
│  │ RulesEngine  │  │  (T+1/涨跌停) │  │ (交易规则)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│  【A股特色风控规则】                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Position  │ │StopProfit│ │Capital   │ │Trading   │          │
│  │Control   │ │LossRule  │ │RiskRule  │ │LimitRule │          │
│  │Rule      │ │          │ │          │ │          │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  【VeighNa 核心层】                                            │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │  MainEngine  │  │ EventEngine  │                           │
│  └──────────────┘  └──────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_rules/
├── __init__.py
├── datasource.py              # 已完成
├── engine.py                  # 已完成
├── filter.py                  # 已完成
├── strategy.py                # 已完成
├── risk/
│   ├── __init__.py           # 模块入口
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── position_control_rule.py    # 仓位风控规则
│   │   ├── stop_profit_loss_rule.py    # 止损止盈规则
│   │   ├── capital_risk_rule.py        # 资金风控规则
│   │   ├── trading_limit_rule.py       # 交易风控规则
│   │   └── __init__.py
│   └── manager.py             # 风控管理器
└── tests/
```

---

## 3. 核心类设计

### 3.1 仓位控制规则 (PositionControlRule)

```python
from vnpy.trader.object import OrderRequest, TradeData, PositionData
from vnpy.trader.constant import Direction
from vnpy_riskmanager.template import RuleTemplate


class PositionControlRule(RuleTemplate):
    """仓位控制风控规则"""

    name: str = "A股仓位控制"

    parameters: dict[str, str] = {
        "max_single_position_ratio": "单股最大仓位比例",
        "max_total_position_ratio": "总仓位最大比例",
        "max_industry_ratio": "单一行业最大比例",
        "max_holdings": "最大持仓股票数",
        "enable_industry_check": "启用行业检查",
    }

    variables: dict[str, str] = {
        "current_total_ratio": "当前总仓位比例",
        "current_positions": "当前持仓数",
    }

    def on_init(self) -> None:
        """初始化参数"""
        # 默认配置
        self.max_single_position_ratio: float = 0.20      # 单股最大20%
        self.max_total_position_ratio: float = 0.80       # 总仓位最大80%
        self.max_industry_ratio: float = 0.40             # 单一行业最大40%
        self.max_holdings: int = 10                       # 最多持仓10只
        self.enable_industry_check: bool = False          # 默认不启用行业检查

        # 运行时状态
        self.current_total_ratio: float = 0.0
        self.current_positions: int = 0
        self.position_data: dict[str, PositionData] = {}

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """检查是否允许委托"""
        # 1. 检查持仓数量限制
        if self._check_holdings_limit(req):
            return False

        # 2. 检查单股仓位限制
        if self._check_single_position_limit(req):
            return False

        # 3. 检查总仓位限制
        if self._check_total_position_limit(req):
            return False

        # 4. 检查行业仓位限制
        if self.enable_industry_check:
            if self._check_industry_limit(req):
                return False

        return True

    def on_trade(self, trade: TradeData) -> None:
        """成交推送 - 更新持仓"""
        # 更新持仓数据
        self._update_position(trade)
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        """委托推送"""
        self.put_event()

    def _check_holdings_limit(self, req: OrderRequest) -> bool:
        """检查持仓数量限制"""
        # 获取当前持仓股票数
        current_count = len([p for p in self.position_data.values()
                           if p.volume > 0])

        # 如果是新买入，检查是否超过持仓数量
        if req.direction == Direction.LONG and current_count >= self.max_holdings:
            # 检查是否在已有持仓中
            if req.vt_symbol not in self.position_data:
                self.write_log(
                    f"持仓数量{current_count}达到上限{self.max_holdings}，禁止新开仓"
                )
                return True
        return False

    def _check_single_position_limit(self, req: OrderRequest) -> bool:
        """检查单股仓位限制"""
        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 计算当前持仓价值
        current_volume = 0
        if req.vt_symbol in self.position_data:
            pos = self.position_data[req.vt_symbol]
            current_volume = pos.volume

        # 计算委托后持仓
        if req.direction == Direction.LONG:
            new_volume = current_volume + req.volume
        else:
            new_volume = max(0, current_volume - req.volume)

        # 计算持仓比例
        position_value = new_volume * req.price * contract.size
        # 需要获取账户总资金
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        position_ratio = position_value / account.balance

        if position_ratio > self.max_single_position_ratio:
            self.write_log(
                f"单股仓位比例{position_ratio:.2%}超过上限{self.max_single_position_ratio:.2%}"
            )
            return True
        return False

    def _check_total_position_limit(self, req: OrderRequest) -> bool:
        """检查总仓位限制"""
        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 计算当前总持仓价值
        total_value = 0
        for pos in self.position_data.values():
            if pos.volume > 0:
                total_value += pos.volume * pos.price * contract.size

        # 计算委托后总持仓
        order_value = req.volume * req.price * contract.size
        if req.direction == Direction.LONG:
            total_value += order_value

        # 获取账户总资金
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        total_ratio = total_value / account.balance

        if total_ratio > self.max_total_position_ratio:
            self.write_log(
                f"总仓位比例{total_ratio:.2%}超过上限{self.max_total_position_ratio:.2%}"
            )
            return True
        return False

    def _check_industry_limit(self, req: OrderRequest) -> bool:
        """检查行业仓位限制"""
        # 获取股票行业信息
        industry = self._get_industry(req.vt_symbol)
        if not industry:
            return False

        # 计算当前行业持仓
        industry_value = 0
        for vt_symbol, pos in self.position_data.items():
            if pos.volume > 0 and self._get_industry(vt_symbol) == industry:
                industry_value += pos.volume * pos.price

        # 计算委托后行业持仓
        contract = self.get_contract(req.vt_symbol)
        if contract:
            order_value = req.volume * req.price * contract.size
            if req.direction == Direction.LONG:
                industry_value += order_value

        # 获取账户总资金
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        industry_ratio = industry_value / account.balance

        if industry_ratio > self.max_industry_ratio:
            self.write_log(
                f"行业[{industry}]仓位比例{industry_ratio:.2%}超过上限{self.max_industry_ratio:.2%}"
            )
            return True
        return False

    def _get_industry(self, vt_symbol: str) -> str:
        """获取股票行业"""
        # 从数据源获取
        return "科技"  # TODO: 实现从数据源获取

    def _update_position(self, trade: TradeData) -> None:
        """更新持仓数据"""
        if trade.vt_symbol not in self.position_data:
            self.position_data[trade.vt_symbol] = PositionData(
                symbol=trade.symbol,
                exchange=trade.exchange,
                direction=trade.direction,
                volume=0,
                frozen=0,
                price=0,
                cost=0,
                PNL=0,
            )

        pos = self.position_data[trade.vt_symbol]

        if trade.direction == Direction.LONG:
            pos.volume += trade.volume
            pos.cost = (pos.cost * (pos.volume - trade.volume) +
                       trade.price * trade.volume) / pos.volume
        else:
            pos.volume -= trade.volume
            if pos.volume == 0:
                pos.cost = 0

        # 更新最新价格
        pos.price = trade.price
```

### 3.2 止损止盈规则 (StopProfitLossRule)

```python
from vnpy.trader.object import OrderRequest, TradeData, OrderData
from vnpy.trader.constant import Direction, Status
from vnpy_riskmanager.template import RuleTemplate
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class StopLossRecord:
    """止损止盈记录"""
    vt_symbol: str
    direction: Direction
    entry_price: float           # 入场价格
    volume: int                 # 持仓数量
    stop_loss_price: float      # 止损价
    stop_profit_price: float    # 止盈价
    trailing_stop_price: float  # 移动止损价
    entry_time: datetime         # 入场时间
    highest_price: float = 0    # 最高价（用于移动止损）
    lowest_price: float = 0     # 最低价（用于移动止损）


class StopProfitLossRule(RuleTemplate):
    """止损止盈风控规则"""

    name: str = "A股止损止盈"

    parameters: dict[str, str] = {
        "enable_stop_loss": "启用止损",
        "stop_loss_ratio": "止损比例",
        "enable_stop_profit": "启用止盈",
        "stop_profit_ratio": "止盈比例",
        "enable_trailing_stop": "启用移动止损",
        "trailing_stop_ratio": "移动止损比例",
        "enable_combo_stop": "启用组合止损",
        "combo_stop_ratio": "组合止损比例",
    }

    variables: dict[str, str] = {
        "total_pnl": "总盈亏",
        "daily_pnl": "当日盈亏",
        "stop_loss_count": "止损次数",
        "stop_profit_count": "止盈次数",
    }

    def on_init(self) -> None:
        """初始化"""
        # 参数
        self.enable_stop_loss: bool = True
        self.stop_loss_ratio: float = 0.05          # 止损5%

        self.enable_stop_profit: bool = True
        self.stop_profit_ratio: float = 0.10        # 止盈10%

        self.enable_trailing_stop: bool = False
        self.trailing_stop_ratio: float = 0.03      # 移动止损3%

        self.enable_combo_stop: bool = False
        self.combo_stop_ratio: float = 0.08         # 组合止损8%

        # 运行时状态
        self.positions: dict[str, StopLossRecord] = {}
        self.total_pnl: float = 0.0
        self.daily_pnl: float = 0.0
        self.stop_loss_count: int = 0
        self.stop_profit_count: int = 0
        self.consecutive_losses: int = 0            # 连续亏损次数
        self.last_trade_pnl: float = 0.0            # 上笔交易盈亏

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """开仓前检查"""
        # 开仓不涉及止损止盈检查
        return True

    def on_trade(self, trade: TradeData) -> None:
        """成交推送 - 记录入场"""
        key = f"{trade.vt_symbol}_{trade.direction}"

        if trade.direction == Direction.LONG:
            # 买入开仓 - 记录入场信息
            self.positions[key] = StopLossRecord(
                vt_symbol=trade.vt_symbol,
                direction=trade.direction,
                entry_price=trade.price,
                volume=trade.volume,
                stop_loss_price=trade.price * (1 - self.stop_loss_ratio),
                stop_profit_price=trade.price * (1 + self.stop_profit_ratio),
                trailing_stop_price=0,
                entry_time=trade.datetime,
                highest_price=trade.price,
                lowest_price=trade.price,
            )
        else:
            # 卖出平仓 - 清除入场记录
            if key in self.positions:
                # 计算盈亏
                record = self.positions[key]
                pnl = (trade.price - record.entry_price) * trade.volume
                self.total_pnl += pnl
                self.daily_pnl += pnl
                self.last_trade_pnl = pnl

                # 更新连续亏损计数
                if pnl < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0

                # 更新止损止盈统计
                if pnl < 0:
                    self.stop_loss_count += 1
                else:
                    self.stop_profit_count += 1

                del self.positions[key]

        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        """行情推送 - 检查止损止盈"""
        # 遍历所有持仓，检查是否触发止损止盈
        keys_to_close = []

        for key, record in self.positions.items():
            if record.direction != Direction.LONG:
                continue

            # 更新最高/最低价
            if tick.last_price > record.highest_price:
                record.highest_price = tick.last_price

                # 更新移动止损价
                if self.enable_trailing_stop:
                    record.trailing_stop_price = record.highest_price * (
                        1 - self.trailing_stop_ratio
                    )

            # 检查止损
            if self.enable_stop_loss:
                if tick.last_price <= record.stop_loss_price:
                    keys_to_close.append((key, "止损"))

            # 检查止盈
            if self.enable_stop_profit:
                if tick.last_price >= record.stop_profit_price:
                    keys_to_close.append((key, "止盈"))

            # 检查移动止损
            if self.enable_trailing_stop and record.trailing_stop_price > 0:
                if tick.last_price <= record.trailing_stop_price:
                    keys_to_close.append((key, "移动止损"))

        # 执行平仓（这里只是记录日志，实际平仓由策略执行）
        for key, reason in keys_to_close:
            record = self.positions[key]
            self.write_log(
                f"触发{reason}：{record.vt_symbol}，当前价{tick.last_price}，"
                f"止损价{record.stop_loss_price}，止盈价{record.stop_profit_price}"
            )

    def on_timer(self) -> None:
        """定时检查组合止损"""
        if self.enable_combo_stop:
            account = self.risk_engine.main_engine.get_account()
            if account:
                # 计算当前资金比例
                current_ratio = (account.balance - account.frozen) / account.balance

                if current_ratio < (1 - self.combo_stop_ratio):
                    self.write_log(
                        f"触发组合止损：资金比例{current_ratio:.2%}，"
                        f"低于止损比例{self.combo_stop_ratio:.2%}"
                    )
```

### 3.3 资金风控规则 (CapitalRiskRule)

```python
from vnpy.trader.object import OrderRequest, TradeData
from vnpy.trader.constant import Direction
from vnpy_riskmanager.template import RuleTemplate
from datetime import datetime, time


class CapitalRiskRule(RuleTemplate):
    """资金风控规则"""

    name: str = "A股资金风控"

    parameters: dict[str, str] = {
        "max_daily_loss_ratio": "单日最大亏损比例",
        "max_single_trade_loss": "单笔最大亏损金额",
        "max_capital_usage_ratio": "最大资金使用比例",
        "enable_margin_check": "启用保证金检查",
    }

    variables: dict[str, str] = {
        "daily_pnl": "当日盈亏",
        "capital_usage_ratio": "资金使用比例",
        "frozen_capital": "冻结资金",
    }

    def on_init(self) -> None:
        """初始化"""
        self.max_daily_loss_ratio: float = 0.05      # 单日最大亏损5%
        self.max_single_trade_loss: float = 10000     # 单笔最大亏损1万
        self.max_capital_usage_ratio: float = 0.90    # 最大资金使用90%
        self.enable_margin_check: bool = False        # 默认不启用融资融券

        # 运行时状态
        self.daily_pnl: float = 0.0
        self.daily_initial_balance: float = 0.0
        self.capital_usage_ratio: float = 0.0
        self.frozen_capital: float = 0.0

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """检查是否允许委托"""
        # 1. 检查资金使用比例
        if self._check_capital_usage(req):
            return False

        # 2. 检查单笔最大亏损
        if self._check_single_trade_loss(req):
            return False

        return True

    def on_trade(self, trade: TradeData) -> None:
        """成交推送 - 更新资金"""
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return

        # 更新当日盈亏
        self.daily_pnl = account.balance - self.daily_initial_balance

        # 检查是否触发日止损
        if self._check_daily_loss_limit():
            self.write_log(
                f"触发单日止损：当日的损{self.daily_pnl:.2f}，"
                f"达到上限{self.max_daily_loss_ratio:.2%}"
            )

        # 更新资金使用比例
        self.capital_usage_ratio = (
            (account.balance - account.available) / account.balance
        )

        self.put_event()

    def on_timer(self) -> None:
        """定时检查"""
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return

        # 记录每日开盘资金
        if self.daily_initial_balance == 0:
            self.daily_initial_balance = account.balance

        # 检查日亏损
        self.daily_pnl = account.balance - self.daily_initial_balance
        self._check_daily_loss_limit()

        # 更新资金使用
        self.capital_usage_ratio = (
            (account.balance - account.available) / account.balance
        )

        # 检查资金使用比例
        if self.capital_usage_ratio > self.max_capital_usage_ratio:
            self.write_log(
                f"资金使用比例{self.capital_usage_ratio:.2%}，"
                f"超过上限{self.max_capital_usage_ratio:.2%}"
            )

        self.put_event()

    def _check_capital_usage(self, req: OrderRequest) -> bool:
        """检查资金使用比例"""
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 计算委托所需资金
        required_capital = req.volume * req.price * contract.size

        if req.direction == Direction.LONG:
            # 买入需要资金
            new_used = (account.balance - account.available) + required_capital
            new_ratio = new_used / account.balance

            if new_ratio > self.max_capital_usage_ratio:
                self.write_log(
                    f"资金使用比例{new_ratio:.2%}，"
                    f"委托后超过上限{self.max_capital_usage_ratio:.2%}"
                )
                return True

        return False

    def _check_single_trade_loss(self, req: OrderRequest) -> bool:
        """检查单笔最大亏损"""
        # 这个检查需要在开仓前估算最大可能亏损
        # 这里简单处理，不做限制
        return False

    def _check_daily_loss_limit(self) -> bool:
        """检查单日亏损限制"""
        if self.daily_initial_balance == 0:
            return False

        loss_ratio = abs(self.daily_pnl) / self.daily_initial_balance

        if self.daily_pnl < 0 and loss_ratio > self.max_daily_loss_ratio:
            return True

        return False
```

### 3.4 交易限制规则 (TradingLimitRule)

```python
from vnpy.trader.object import OrderRequest, OrderData, TradeData
from vnpy.trader.constant import Status
from vnpy_riskmanager.template import RuleTemplate
from collections import defaultdict
from datetime import datetime, timedelta


class TradingLimitRule(RuleTemplate):
    """交易限制风控规则"""

    name: str = "A股交易限制"

    parameters: dict[str, str] = {
        "max_orders_per_minute": "每分钟最大委托数",
        "max_orders_per_day": "每日最大委托数",
        "max_cancel_ratio": "最大撤单比例",
        "max_price_deviation": "最大价格偏离比例",
        "max_consecutive_losses": "最大连续亏损次数",
    }

    variables: dict[str, str] = {
        "minute_order_count": "分钟委托数",
        "daily_order_count": "日委托数",
        "cancel_ratio": "撤单比例",
        "consecutive_losses": "连续亏损次数",
    }

    def on_init(self) -> None:
        """初始化"""
        self.max_orders_per_minute: int = 10
        self.max_orders_per_day: int = 100
        self.max_cancel_ratio: float = 0.5
        self.max_price_deviation: float = 0.02
        self.max_consecutive_losses: int = 5

        # 运行时状态
        self.minute_orders: list[datetime] = []
        self.daily_orders: list[datetime] = []
        self.cancel_count: int = 0
        self.order_count: int = 0
        self.consecutive_losses: int = 0

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """检查是否允许委托"""
        # 1. 检查分钟频率限制
        if self._check_minute_limit():
            return False

        # 2. 检查日频率限制
        if self._check_daily_limit():
            return False

        # 3. 检查价格偏离
        if self._check_price_deviation(req):
            return False

        # 4. 检查连续亏损
        if self._check_consecutive_losses():
            return False

        return True

    def on_order(self, order: OrderData) -> None:
        """委托推送"""
        self.order_count += 1
        self.daily_orders.append(order.datetime)

        # 记录撤单
        if order.status == Status.CANCELLED:
            self.cancel_count += 1

        self.put_event()

    def on_trade(self, trade: TradeData) -> None:
        """成交推送"""
        # 检查连续亏损
        # 这里需要结合持仓和盈亏计算
        self.put_event()

    def on_timer(self) -> None:
        """定时清理"""
        now = datetime.now()

        # 清理一分钟前的委托记录
        cutoff = now - timedelta(minutes=1)
        self.minute_orders = [t for t in self.minute_orders if t > cutoff]

        # 清理昨天的委托记录
        if now.date() > self.last_date:
            self.daily_orders.clear()
            self.order_count = 0
            self.cancel_count = 0
            self.last_date = now.date()

        self.put_event()

    def _check_minute_limit(self) -> bool:
        """检查分钟频率"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        recent_orders = [t for t in self.minute_orders if t > cutoff]

        if len(recent_orders) >= self.max_orders_per_minute:
            self.write_log(
                f"分钟委托数{len(recent_orders)}达到上限{self.max_orders_per_minute}"
            )
            return True
        return False

    def _check_daily_limit(self) -> bool:
        """检查日频率"""
        if self.order_count >= self.max_orders_per_day:
            self.write_log(
                f"日委托数{self.order_count}达到上限{self.max_orders_per_day}"
            )
            return True
        return False

    def _check_price_deviation(self, req: OrderRequest) -> bool:
        """检查价格偏离"""
        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 获取最新行情
        tick = self.risk_engine.main_engine.get_tick(req.vt_symbol)
        if not tick:
            return False

        # 计算偏离比例
        if req.direction == Direction.LONG:
            # 买入，检查卖价
            deviation = abs(req.price - tick.ask_price_1) / tick.ask_price_1
        else:
            # 卖出，检查买价
            deviation = abs(req.price - tick.bid_price_1) / tick.bid_price_1

        if deviation > self.max_price_deviation:
            self.write_log(
                f"价格偏离比例{deviation:.2%}超过上限{self.max_price_deviation:.2%}"
            )
            return True
        return False

    def _check_consecutive_losses(self) -> bool:
        """检查连续亏损"""
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.write_log(
                f"连续亏损{self.consecutive_losses}次达到上限{self.max_consecutive_losses}，"
                f"禁止开仓"
            )
            return True
        return False
```

---

## 4. 风控管理器

### 4.1 RiskManager 扩展

```python
# risk/manager.py

from vnpy_riskmanager.engine import RiskEngine
from vnpy_china_rules.engine import ChinaStockRulesEngine
from vnpy_china_rules.datasource import DataSourceManager


class AStockRiskManager:
    """A股风险管理器"""

    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 初始化 vnpy_riskmanager
        self.risk_engine: RiskEngine = None

        # 初始化 A股规则引擎
        self.china_rules_engine: ChinaStockRulesEngine = None

    def initialize(self, qmt_gateway=None, tushare_token=None):
        """初始化风控系统"""
        # 1. 初始化数据源
        datasource_manager = DataSourceManager()

        if qmt_gateway:
            from vnpy_china_rules.datasource import QMTDataSource
            qmt_source = QMTDataSource(qmt_gateway)
            datasource_manager.register_source("qmt", qmt_source, primary=True)

        if tushare_token:
            from vnpy_china_rules.datasource import TushareDataSource
            tushare_source = TushareDataSource(tushare_token)
            datasource_manager.register_source("tushare", tushare_source)

        # 2. 初始化A股规则引擎
        self.china_rules_engine = ChinaStockRulesEngine(datasource_manager)

        # 3. 初始化vnpy_riskmanager
        self._init_risk_manager()

    def _init_risk_manager(self):
        """初始化风控引擎"""
        from vnpy_riskmanager import RiskManagerApp

        # 添加风控应用
        self.main_engine.add_app(RiskManagerApp)
        self.risk_engine = self.main_engine.get_engine(RiskEngine)

        # 注册自定义规则
        self._register_custom_rules()

    def _register_custom_rules(self):
        """注册自定义规则"""
        # 动态加载 rules/ 目录下的规则
        from pathlib import Path
        import importlib.util

        rules_path = Path(__file__).parent / "rules"
        for file in rules_path.glob("*_rule.py"):
            if file.name.startswith("_"):
                continue

            # 动态导入模块
            module_name = f"vnpy_china_rules.risk.rules.{file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

    def get_risk_engine(self) -> RiskEngine:
        """获取风控引擎"""
        return self.risk_engine

    def get_china_rules_engine(self) -> ChinaStockRulesEngine:
        """获取A股规则引擎"""
        return self.china_rules_engine
```

---

## 5. 集成方式

### 5.1 在 VeighNa 中使用

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_riskmanager import RiskManagerApp
from vnpy_china_rules.risk.manager import AStockRiskManager


def main():
    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加QMT网关
    # main_engine.add_gateway(QmtGateway)

    # 初始化A股风控系统
    risk_manager = AStockRiskManager(main_engine, event_engine)
    risk_manager.initialize(
        qmt_gateway=main_engine.get_gateway("QMT"),
        tushare_token="your_token"
    )

    # 之后可以添加策略等
    # main_engine.add_app(CtaStrategyApp)

    # 运行
    main_engine.write_log("A股风控系统初始化完成")


if __name__ == "__main__":
    main()
```

---

## 6. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建risk目录结构和基础文件 | 0.5人天 |
| 2 | 实现PositionControlRule仓位控制规则 | 1.5人天 |
| 3 | 实现StopProfitLossRule止损止盈规则 | 2人天 |
| 4 | 实现CapitalRiskRule资金风控规则 | 1.5人天 |
| 5 | 实现TradingLimitRule交易限制规则 | 1.5人天 |
| 6 | 实现RiskManager管理器 | 1人天 |
| 合计 | | **8人天** |

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
