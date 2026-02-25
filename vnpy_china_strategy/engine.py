"""
A股策略引擎
管理A股特色策略的运行
"""

from typing import Dict, Any, Optional
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine
from vnpy.trader.object import TickData, BarData, OrderData, TradeData, ContractData, PositionData, AccountData


class ChinaStrategyEngine(BaseEngine):
    """A股策略引擎

    负责管理A股特色策略的运行生命周期，包括：
    - 策略初始化和启动
    - 数据事件处理
    - 交易订单管理
    """

    engine_name: str = "ChinaStrategyApp"

    def __init__(self, main_engine: Any, event_engine: EventEngine) -> None:
        """初始化引擎"""
        super().__init__(main_engine, event_engine, self.engine_name)

        # 策略字典
        self.strategies: Dict[str, Any] = {}

        # 注册事件监听
        self.register_event()

    def init(self) -> None:
        """引擎初始化"""
        self.write_log("A股策略引擎初始化完成")

    def register_event(self) -> None:
        """注册事件监听"""
        # 订阅行情数据事件
        self.event_engine.register("tick", self.process_tick_event)
        self.event_engine.register("bar", self.process_bar_event)

        # 订阅交易事件
        self.event_engine.register("order", self.process_order_event)
        self.event_engine.register("trade", self.process_trade_event)

    def process_tick_event(self, event: Event) -> None:
        """处理Tick行情事件"""
        tick: TickData = event.data
        # 分发给所有订阅该合约的策略
        for strategy in self.strategies.values():
            if hasattr(strategy, "on_tick"):
                strategy.on_tick(tick)

    def process_bar_event(self, event: Event) -> None:
        """处理K线行情事件"""
        bar: BarData = event.data
        # 分发给所有订阅该合约的策略
        for strategy in self.strategies.values():
            if hasattr(strategy, "on_bar"):
                strategy.on_bar(bar)

    def process_order_event(self, event: Event) -> None:
        """处理委托事件"""
        order: OrderData = event.data
        # 分发给相关策略
        for strategy in self.strategies.values():
            if hasattr(strategy, "on_order"):
                strategy.on_order(order)

    def process_trade_event(self, event: Event) -> None:
        """处理成交事件"""
        trade: TradeData = event.data
        # 分发给相关策略
        for strategy in self.strategies.values():
            if hasattr(strategy, "on_trade"):
                strategy.on_trade(trade)

    def add_strategy(self, strategy_name: str, strategy: Any) -> None:
        """添加策略"""
        self.strategies[strategy_name] = strategy
        self.write_log(f"策略 {strategy_name} 已添加")

    def remove_strategy(self, strategy_name: str) -> None:
        """移除策略"""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            self.write_log(f"策略 {strategy_name} 已移除")

    def get_strategy(self, strategy_name: str) -> Optional[Any]:
        """获取策略"""
        return self.strategies.get(strategy_name)

    def get_all_strategies(self) -> Dict[str, Any]:
        """获取所有策略"""
        return self.strategies.copy()

    def start_strategy(self, strategy_name: str) -> bool:
        """启动策略"""
        strategy = self.get_strategy(strategy_name)
        if strategy:
            if hasattr(strategy, "start"):
                strategy.start()
                self.write_log(f"策略 {strategy_name} 已启动")
                return True
        return False

    def stop_strategy(self, strategy_name: str) -> bool:
        """停止策略"""
        strategy = self.get_strategy(strategy_name)
        if strategy:
            if hasattr(strategy, "stop"):
                strategy.stop()
                self.write_log(f"策略 {strategy_name} 已停止")
                return True
        return False

    def get_all_strategy_names(self) -> list[str]:
        """获取所有策略名称"""
        return list(self.strategies.keys())


__all__ = ["ChinaStrategyEngine"]
