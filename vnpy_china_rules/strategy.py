"""
策略基类

提供A股策略基类和交易规则混入类。
"""

from datetime import datetime
from typing import Optional, Any, Dict, List

from loguru import logger

from vnpy.trader.object import OrderData, TradeData, BarData, TickData
from vnpy.trader.constant import Direction, Offset, Exchange, OrderType, Status

from vnpy_china_rules.engine import ChinaStockRulesEngine


class ChinaStockStrategy:
    """
    A股策略基类

    提供A股特有的交易规则检查功能，包括T+1、涨跌停等规则。
    策略开发者可以继承此类来开发A股量化策略。

    Attributes
    ----------
    cta_engine : Any
        CTA引擎实例
    strategy_name : str
        策略名称
    vt_symbol : str
        合约代码
    active : bool
        策略是否运行中
    pos : int
        持仓数量

    Example
    -------
    ```python
    from vnpy_china_rules.strategy import ChinaStockStrategy


    class MyStockStrategy(ChinaStockStrategy):
        parameters = ["max_position", "stop_loss"]

        variables = ["pos", "avg_price"]

        def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
            super().__init__(cta_engine, strategy_name, vt_symbol, setting)
            self.max_position = setting.get("max_position", 10000)
            self.stop_loss = setting.get("stop_loss", 0.02)
            self.avg_price = 0.0

        def on_bar(self, bar):
            if self.pos == 0:
                can_buy, msg = self.check_buy(self.vt_symbol, bar.close_price, 1000)
                if can_buy:
                    self.buy(bar.close_price, 1000)
    ```
    """

    # 策略参数列表（子类需要定义）
    parameters: List[str] = []

    # 策略变量列表（子类需要定义）
    variables: List[str] = []

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,
        vt_symbol: str,
        setting: Dict[str, Any]
    ) -> None:
        """
        初始化策略

        Parameters
        ----------
        cta_engine : Any
            CTA引擎实例
        strategy_name : str
            策略名称
        vt_symbol : str
            合约代码，格式如 "000001.SZSE"
        setting : Dict[str, Any]
            策略参数配置
        """
        self.cta_engine: Any = cta_engine
        self.strategy_name: str = strategy_name
        self.vt_symbol: str = vt_symbol
        self.active: bool = False

        # 规则引擎引用（需要通过外部设置）
        self.rules_engine: Optional[ChinaStockRulesEngine] = None

        # 持仓
        self.pos: int = 0

        # 解析参数设置
        for key, value in setting.items():
            if hasattr(self, key):
                setattr(self, key, value)

        logger.debug(
            f"策略实例化: {strategy_name}, vt_symbol: {vt_symbol}"
        )

    # ==================== 交易相关方法 ====================

    def buy(
        self,
        price: float,
        volume: int,
        lock: bool = False
    ) -> Optional[str]:
        """
        买入开仓

        Parameters
        ----------
        price : float
            买入价格
        volume : int
            买入数量
        lock : bool
            是否锁定仓位（用于组合策略）

        Returns
        -------
        Optional[str]
            委托订单ID，如果没有发送则返回None
        """
        if self.cta_engine is None:
            logger.warning(f"[{self.strategy_name}] CTA引擎未初始化")
            return None

        # 创建买入订单
        order = OrderData(
            symbol=self.vt_symbol,
            exchange=self._get_exchange(),
            orderid="",
            gateway_name="CHINA_RULES",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=price,
            volume=volume,
            datetime=datetime.now(),
        )

        # 如果有规则引擎，先检查
        if self.rules_engine:
            can_submit, msg = self.rules_engine.can_submit_order(order)
            if not can_submit:
                self.write_log(f"买入检查失败: {msg}")
                return None

        # 发送订单
        vt_orderids: List[str] = self.cta_engine.send_order(
            self,
            self.vt_symbol,
            Direction.LONG,
            Offset.OPEN,
            price,
            volume,
            lock
        )

        if vt_orderids:
            self.write_log(f"买入委托: 价格{price}, 数量{volume}")
            return vt_orderids[0] if vt_orderids else None

        return None

    def sell(
        self,
        price: float,
        volume: int,
        lock: bool = False
    ) -> Optional[str]:
        """
        卖出平仓

        Parameters
        ----------
        price : float
            卖出价格
        volume : int
            卖出数量
        lock : bool
            是否锁定仓位

        Returns
        -------
        Optional[str]
            委托订单ID
        """
        if self.cta_engine is None:
            logger.warning(f"[{self.strategy_name}] CTA引擎未初始化")
            return None

        # 创建卖出订单
        order = OrderData(
            symbol=self.vt_symbol,
            exchange=self._get_exchange(),
            orderid="",
            gateway_name="CHINA_RULES",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=price,
            volume=volume,
            datetime=datetime.now(),
        )

        # 如果有规则引擎，先检查T+1和涨跌停
        if self.rules_engine:
            # 检查T+1
            can_submit, msg = self.rules_engine.can_submit_order(order)
            if not can_submit:
                self.write_log(f"卖出检查失败: {msg}")
                return None

        # 发送订单
        vt_orderids: List[str] = self.cta_engine.send_order(
            self,
            self.vt_symbol,
            Direction.SHORT,
            Offset.CLOSE,
            price,
            volume,
            lock
        )

        if vt_orderids:
            self.write_log(f"卖出委托: 价格{price}, 数量{volume}")
            return vt_orderids[0] if vt_orderids else None

        return None

    def short(self, price: float, volume: int) -> Optional[str]:
        """
        卖空开仓

        注意：A股市场不允许融券做空，此方法主要用于兼容性

        Parameters
        ----------
        price : float
            卖出价格
        volume : int
            卖出数量

        Returns
        -------
        Optional[str]
            委托订单ID
        """
        # A股不支持做空，返回警告
        logger.warning(f"[{self.strategy_name}] A股市场不支持做空功能")
        return None

    def cover(self, price: float, volume: int) -> Optional[str]:
        """
        买空平仓

        注意：A股市场不允许融券做空，此方法主要用于兼容性

        Parameters
        ----------
        price : float
            买入价格
        volume : int
            买入数量

        Returns
        -------
        Optional[str]
            委托订单ID
        """
        # A股不支持做空，返回警告
        logger.warning(f"[{self.strategy_name}] A股市场不支持做空功能")
        return None

    # ==================== 规则检查便捷方法 ====================

    def check_buy(
        self,
        symbol: str,
        price: float,
        volume: int
    ) -> tuple[bool, str]:
        """
        检查是否可买入

        调用规则引擎检查买入订单是否符合交易规则。

        Parameters
        ----------
        symbol : str
            股票代码
        price : float
            买入价格
        volume : int
            买入数量

        Returns
        -------
        tuple[bool, str]
            (是否可买入, 原因说明)
        """
        if self.rules_engine is None:
            logger.warning(f"[{self.strategy_name}] 规则引擎未初始化")
            return True, "规则引擎未初始化"

        # 创建订单对象
        exchange = self._parse_exchange(symbol)
        order = OrderData(
            symbol=symbol,
            exchange=exchange,
            orderid="",
            gateway_name="CHINA_RULES",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=price,
            volume=volume,
            datetime=datetime.now(),
        )

        # 检查订单
        return self.rules_engine.can_submit_order(order)

    def check_sell(
        self,
        symbol: str,
        price: float,
        volume: int
    ) -> tuple[bool, str]:
        """
        检查是否可卖出

        调用规则引擎检查卖出订单是否符合T+1和涨跌停规则。

        Parameters
        ----------
        symbol : str
            股票代码
        price : float
            卖出价格
        volume : int
            卖出数量

        Returns
        -------
        tuple[bool, str]
            (是否可卖出, 原因说明)
        """
        if self.rules_engine is None:
            logger.warning(f"[{self.strategy_name}] 规则引擎未初始化")
            return True, "规则引擎未初始化"

        # 创建订单对象
        exchange = self._parse_exchange(symbol)
        order = OrderData(
            symbol=symbol,
            exchange=exchange,
            orderid="",
            gateway_name="CHINA_RULES",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=price,
            volume=volume,
            datetime=datetime.now(),
        )

        # 先检查T+1
        t1_result = self.rules_engine.t1_rules.check(order)
        if not t1_result.passed:
            return False, t1_result.message

        # 再检查涨跌停等规则
        return self.rules_engine.can_submit_order(order)

    def get_sellable_volume(self, symbol: str) -> int:
        """
        获取可卖出数量

        根据T+1规则计算当前可卖出的股票数量。

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        int
            可卖出数量
        """
        if self.rules_engine is None:
            logger.warning(f"[{self.strategy_name}] 规则引擎未初始化")
            return 0

        return self.rules_engine.t1_rules.get_sellable_volume(
            symbol, datetime.now()
        )

    # ==================== 回调方法 ====================

    def on_init(self) -> None:
        """
        策略初始化回调

        在策略加载时调用，通常用于初始化指标、加载数据等。
        """
        self.write_log("策略初始化")

    def on_start(self) -> None:
        """
        策略启动回调

        在策略启动时调用。
        """
        self.active = True
        self.write_log("策略启动")

    def on_stop(self) -> None:
        """
        策略停止回调

        在策略停止时调用，通常用于清理资源、保存状态等。
        """
        self.active = False
        self.write_log("策略停止")

    def on_trade(self, trade: TradeData) -> None:
        """
        成交推送回调

        当订单成交时推送。

        Parameters
        ----------
        trade : TradeData
            成交数据
        """
        # 更新持仓
        if trade.direction == Direction.LONG:
            self.pos += int(trade.volume)
        else:
            self.pos -= int(trade.volume)

        # 如果有规则引擎，记录T+1持仓
        if self.rules_engine:
            self.rules_engine.on_trade(trade)

        self.write_log(
            f"成交: {trade.direction.value} {int(trade.volume)}股 @ {trade.price}"
        )

    def on_order(self, order: OrderData) -> None:
        """
        委托推送回调

        当委托状态变化时推送。

        Parameters
        ----------
        order : OrderData
            委托数据
        """
        self.write_log(
            f"委托: {order.orderid} {order.direction.value} "
            f"{int(order.volume)}股 @ {order.price} 状态:{order.status.value}"
        )

    def on_bar(self, bar: BarData) -> None:
        """
        K线推送回调

        当新的K线数据到达时推送。

        Parameters
        ----------
        bar : BarData
            K线数据
        """
        pass

    def on_tick(self, tick: TickData) -> None:
        """
        Tick推送回调

        当新的Tick数据到达时推送。

        Parameters
        ----------
        tick : TickData
            Tick数据
        """
        pass

    # ==================== 日志和参数 ====================

    def write_log(self, msg: str) -> None:
        """
        写日志

        Parameters
        ----------
        msg : str
            日志消息
        """
        if self.cta_engine:
            self.cta_engine.write_log(msg, self)
        else:
            logger.info(f"[{self.strategy_name}] {msg}")

    def get_parameters(self) -> Dict[str, Any]:
        """
        获取参数

        Returns
        -------
        Dict[str, Any]
            参数字典
        """
        params = {
            "strategy_name": self.strategy_name,
            "vt_symbol": self.vt_symbol,
        }

        # 添加自定义参数
        for param in self.parameters:
            if hasattr(self, param):
                params[param] = getattr(self, param)

        return params

    def get_variables(self) -> Dict[str, Any]:
        """
        获取变量

        Returns
        -------
        Dict[str, Any]
            变量字典
        """
        vars_dict = {
            "pos": self.pos,
            "active": self.active,
        }

        # 添加自定义变量
        for var in self.variables:
            if hasattr(self, var):
                vars_dict[var] = getattr(self, var)

        return vars_dict

    # ==================== 辅助方法 ====================

    def _get_exchange(self) -> Exchange:
        """
        从vt_symbol获取交易所

        Returns
        -------
        Exchange
            交易所枚举
        """
        return self._parse_exchange(self.vt_symbol)

    @staticmethod
    def _parse_exchange(symbol: str) -> Exchange:
        """
        解析股票代码获取交易所

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Exchange
            交易所枚举
        """
        if symbol.endswith(".SH") or symbol.endswith(".SSE"):
            return Exchange.SSE
        elif symbol.endswith(".SZ") or symbol.endswith(".SZSE"):
            return Exchange.SZSE
        elif symbol.endswith(".BJ") or symbol.endswith(".BSE"):
            return Exchange.BSE
        return Exchange.SZSE  # 默认深交所


class TradingRuleMixin:
    """
    交易规则混入类

    如果用户不想继承ChinaStockStrategy，可以通过混入方式集成规则检查功能。
    适用于已经继承了其他基类的策略。

    Example
    -------
    ```python
    from vnpy_china_rules.strategy import TradingRuleMixin


    class MyExistingStrategy(MyBaseStrategy, TradingRuleMixin):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # 确保初始化rules_engine
            self.rules_engine = None

        def some_method(self):
            # 使用规则检查
            can_buy, msg = self.check_buy("000001.SZSE", 10.0, 1000)
            if can_buy:
                # 执行买入
                pass
    ```
    """

    # 规则引擎引用（子类需要通过外部设置）
    rules_engine: Optional[ChinaStockRulesEngine] = None

    def __init__(self) -> None:
        """
        初始化混入类

        确保有rules_engine属性。
        """
        if not hasattr(self, "rules_engine"):
            self.rules_engine = None

    def check_buy(
        self,
        symbol: str,
        price: float,
        volume: int
    ) -> tuple[bool, str]:
        """
        检查是否可买入

        Parameters
        ----------
        symbol : str
            股票代码
        price : float
            买入价格
        volume : int
            买入数量

        Returns
        -------
        tuple[bool, str]
            (是否可买入, 原因说明)
        """
        if self.rules_engine is None:
            return True, "规则引擎未初始化"

        # 创建订单对象
        exchange = ChinaStockStrategy._parse_exchange(symbol)
        order = OrderData(
            symbol=symbol,
            exchange=exchange,
            orderid="",
            gateway_name="CHINA_RULES",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=price,
            volume=volume,
            datetime=datetime.now(),
        )

        return self.rules_engine.can_submit_order(order)

    def check_sell(
        self,
        symbol: str,
        price: float,
        volume: int
    ) -> tuple[bool, str]:
        """
        检查是否可卖出

        Parameters
        ----------
        symbol : str
            股票代码
        price : float
            卖出价格
        volume : int
            卖出数量

        Returns
        -------
        tuple[bool, str]
            (是否可卖出, 原因说明)
        """
        if self.rules_engine is None:
            return True, "规则引擎未初始化"

        # 创建订单对象
        exchange = ChinaStockStrategy._parse_exchange(symbol)
        order = OrderData(
            symbol=symbol,
            exchange=exchange,
            orderid="",
            gateway_name="CHINA_RULES",
            direction=Direction.SHORT,
            offset=Offset.CLOSE,
            price=price,
            volume=volume,
            datetime=datetime.now(),
        )

        # 先检查T+1
        t1_result = self.rules_engine.t1_rules.check(order)
        if not t1_result.passed:
            return False, t1_result.message

        # 再检查涨跌停等规则
        return self.rules_engine.can_submit_order(order)

    def get_sellable_volume(self, symbol: str) -> int:
        """
        获取可卖出数量

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        int
            可卖出数量
        """
        if self.rules_engine is None:
            logger.warning("规则引擎未初始化")
            return 0

        return self.rules_engine.t1_rules.get_sellable_volume(
            symbol, datetime.now()
        )


def create_strategy_base(
    cta_engine: Any,
    strategy_name: str,
    vt_symbol: str,
    setting: Dict[str, Any],
    rules_engine: Optional[ChinaStockRulesEngine] = None
) -> ChinaStockStrategy:
    """
    创建带规则引擎的策略实例

    便捷函数，用于创建并配置策略实例。

    Parameters
    ----------
    cta_engine : Any
        CTA引擎实例
    strategy_name : str
        策略名称
    vt_symbol : str
        合约代码
    setting : Dict[str, Any]
        策略参数配置
    rules_engine : Optional[ChinaStockRulesEngine]
        规则引擎实例

    Returns
    -------
    ChinaStockStrategy
        配置好的策略实例

    Example
    -------
    ```python
    from vnpy_china_rules import ChinaStockRulesEngine
    from vnpy_china_rules.strategy import create_strategy_base

    # 创建规则引擎
    rules_engine = ChinaStockRulesEngine(dm)

    # 创建策略
    strategy = create_strategy_base(
        cta_engine=cta_engine,
        strategy_name="my_strategy",
        vt_symbol="000001.SZSE",
        setting={"max_position": 10000},
        rules_engine=rules_engine
    )
    ```
    """
    strategy = ChinaStockStrategy(cta_engine, strategy_name, vt_symbol, setting)
    strategy.rules_engine = rules_engine
    return strategy
