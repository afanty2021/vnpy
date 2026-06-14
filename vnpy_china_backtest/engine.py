"""
增强回测引擎

整合交易成本、滑点、涨跌停、T+1规则
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from copy import copy

from vnpy.trader.constant import Direction, Offset, Interval, Status, Exchange
from vnpy.trader.object import OrderData, TradeData, BarData
from vnpy.trader.utility import round_to, extract_vt_symbol

from vnpy_china_backtest.cost import CostCalculator, CostConfig
from vnpy_china_backtest.slippage import SlippageModel, SlippageModelFactory, PercentSlippage
from vnpy_china_backtest.rules.price_limit import PriceLimitHandler
from vnpy_china_backtest.rules.t1_simulator import T1Simulator
from vnpy_china_backtest.report.metrics import MetricsCalculator, EnhancedMetrics


class EnhancedBacktestEngine:
    """增强回测引擎

    在VeighNa现有回测系统基础上增加A股特色交易模拟功能：
    1. 交易成本模拟：佣金、印花税、过户费、经手费
    2. 滑点模拟：固定、百分比、冲击成本
    3. 涨跌停处理：涨停无法买入、跌停无法卖出
    4. T+1规则模拟：当日买入次日才能卖出
    """

    gateway_name: str = "CHINA_BACKTEST"

    def __init__(self):
        """初始化"""
        # 交易成本计算器
        self.cost_calculator = CostCalculator()

        # 滑点模型
        self.slippage_model: Optional[SlippageModel] = PercentSlippage(0.001)

        # 涨跌停处理器
        self.price_limit_handler = PriceLimitHandler()

        # T+1模拟器
        self.t1_simulator = T1Simulator()

        # 指标计算器
        self.metrics_calculator = MetricsCalculator()

        # 配置开关
        self.enable_cost: bool = True           # 启用交易成本
        self.enable_slippage: bool = True       # 启用滑点
        self.enable_price_limit: bool = True    # 启用涨跌停
        self.enable_t1: bool = True             # 启用T+1

        # 回测参数
        self.vt_symbols: List[str] = []
        self.interval: Interval = Interval.DAILY
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.capital: float = 1_000_000
        self.annual_days: int = 240

        # 持仓数据
        self.positions: Dict[str, int] = {}       # {symbol: volume}
        self.avg_prices: Dict[str, float] = {}    # {symbol: avg_price}

        # 订单和成交数据
        self.limit_order_count: int = 0
        self.limit_orders: Dict[str, OrderData] = {}
        self.active_limit_orders: Dict[str, OrderData] = {}

        self.trade_count: int = 0
        self.trades: Dict[str, TradeData] = {}

        # 账户数据
        self.cash: float = 0.0
        self.frozen: float = 0.0

        # 统计
        self.total_cost: float = 0.0
        self.blocked_orders: int = 0
        self.logs: List[str] = []

        # 历史数据
        self.history_bars: Dict[Tuple[datetime, str], BarData] = {}
        self.pre_closes: Dict[str, float] = {}  # 昨日收盘价

        # 回测时钟与市价快照（由 process_bar 随 bar 推进）
        # current_datetime 取自 bar.datetime，替代此前的 datetime.now()
        self.current_datetime: Optional[datetime] = None
        # 当前市价映射，用于按市价计算持仓市值
        self.current_prices: Dict[str, float] = {}

        # 当前 bar 成交量（供 ImpactCost 滑点模型，由 process_bar 推进）
        self.current_bar_volume: float = 0.0

        # 权益曲线（首点为初始资金，其后为每根 bar 收盘权益）
        self.equity_curve: List[float] = []

    def set_parameters(
        self,
        vt_symbols: List[str],
        interval: Interval,
        start: datetime,
        end: datetime,
        capital: int = 1_000_000,
        annual_days: int = 240
    ) -> None:
        """设置回测参数

        Args:
            vt_symbols: 股票代码列表
            interval: 周期
            start: 开始日期
            end: 结束日期
            capital: 初始资金
            annual_days: 年交易日天数
        """
        self.vt_symbols = vt_symbols
        self.interval = interval
        self.start_date = start
        self.end_date = end
        self.capital = capital
        self.cash = capital
        self.annual_days = annual_days
        # F8: 贯通——engine 的 annual_days 同步到 metrics 计算器（属性赋值，不重建实例）
        self.metrics_calculator.annual_days = annual_days

    def set_cost_config(self, config: CostConfig) -> None:
        """设置成本配置

        Args:
            config: 成本配置
        """
        self.cost_calculator = CostCalculator(config)

    def set_slippage(self, model_type: str = "percent", **kwargs) -> None:
        """设置滑点模型

        Args:
            model_type: 滑点模型类型
            **kwargs: 模型参数
        """
        self.slippage_model = SlippageModelFactory.create(model_type, **kwargs)

    def load_data(self, bars: List[BarData]) -> None:
        """加载历史数据

        Args:
            bars: K线数据列表
        """
        self.history_bars.clear()
        self.pre_closes.clear()          # F3: 与 history_bars 等同步清理，避免连续回测残留

        # 重置回测时钟、市价与权益曲线（首点为初始资金）
        self.current_datetime = None
        self.current_prices.clear()
        self.current_bar_volume = 0.0
        self.equity_curve = [self.cash]

        for bar in bars:
            key = (bar.datetime, bar.vt_symbol)
            self.history_bars[key] = bar

            # 计算昨日收盘价
            if bar.vt_symbol not in self.pre_closes:
                self.pre_closes[bar.vt_symbol] = bar.close_price

    def process_bar(self, bar: BarData) -> None:
        """处理K线数据

        Args:
            bar: K线数据
        """
        symbol = bar.vt_symbol

        # 推进回测时钟：用 bar 的历史日期替代此前的 datetime.now()
        self.current_datetime = bar.datetime

        # 更新市价快照与昨日收盘价
        self.current_prices[symbol] = bar.close_price
        self.pre_closes[symbol] = bar.close_price
        # 记录当前 bar 成交量（供 ImpactCost 滑点）
        self.current_bar_volume = bar.volume

        # 记录当日收盘权益，构建真实的权益曲线
        self.equity_curve.append(self.get_equity())

    def buy(
        self,
        vt_symbol: str,
        price: float,
        volume: int,
        lock: bool = False,
        frozen: bool = False
    ) -> Tuple[bool, str]:
        """买入开多

        Args:
            vt_symbol: 股票代码
            price: 价格
            volume: 数量
            lock: 是否锁仓
            frozen: 是否冻结

        Returns:
            Tuple[bool, str]: (是否成功, 原因)
        """
        return self._execute_order(
            vt_symbol=vt_symbol,
            direction=Direction.LONG,
            price=price,
            volume=volume,
            offset=Offset.OPEN
        )

    def sell(
        self,
        vt_symbol: str,
        price: float,
        volume: int,
        lock: bool = False
    ) -> Tuple[bool, str]:
        """卖出平多

        Args:
            vt_symbol: 股票代码
            price: 价格
            volume: 数量
            lock: 是否锁仓

        Returns:
            Tuple[bool, str]: (是否成功, 原因)
        """
        return self._execute_order(
            vt_symbol=vt_symbol,
            direction=Direction.SHORT,
            price=price,
            volume=volume,
            offset=Offset.CLOSE
        )

    def _execute_order(
        self,
        vt_symbol: str,
        direction: Direction,
        price: float,
        volume: int,
        offset: Offset
    ) -> Tuple[bool, str]:
        """执行订单

        Returns:
            Tuple[bool, str]: (是否成交, 原因)
        """
        # 提取交易所信息
        symbol, exchange = extract_vt_symbol(vt_symbol)

        # 交易日期取回测时钟（由 process_bar 推进）；
        # 无回放上下文（如直接调用 buy/sell）时回退系统日期以保持向后兼容
        trade_date = (
            self.current_datetime.date()
            if self.current_datetime
            else datetime.now().date()
        )

        # 获取昨日收盘价
        prev_close = self.pre_closes.get(vt_symbol, price)

        # 获取当前价格（简化：使用委托价格）
        current_price = price

        # 涨跌停检查
        if self.enable_price_limit:
            success, reason, exec_price, exec_volume = self.price_limit_handler.process_order(
                symbol=vt_symbol,
                direction=direction,
                price=price,
                volume=volume,
                trade_date=trade_date,
                prev_close=prev_close,
                current_price=current_price,
                allow_limit_up=False,
                allow_limit_down=False
            )

            if not success:
                self.blocked_orders += 1
                self.write_log(f"订单被阻止: {reason}")
                return False, reason

            price = exec_price
            volume = exec_volume

        # T+1检查（卖出时）
        if self.enable_t1 and direction == Direction.SHORT:
            sellable = self.t1_simulator.get_sellable_volume(vt_symbol, trade_date)
            if volume > sellable:
                self.blocked_orders += 1
                reason = f"T+1限制：卖出数量{volume}超过可卖出{sellable}"
                self.write_log(reason)
                return False, reason

        # 应用滑点
        if self.enable_slippage and self.slippage_model:
            price = self.slippage_model.apply(
                price,
                volume,
                direction,
                market_volume=self.current_bar_volume
            )

        # 扣除交易成本（买入时）
        cost = 0.0
        if self.enable_cost:
            cost_obj = self.cost_calculator.calculate(price, volume, direction, exchange)
            cost = cost_obj.total
            self.total_cost += cost

        # 计算成交金额
        turnover = price * volume

        # 检查资金是否足够（买入时）
        if direction == Direction.LONG:
            total_needed = turnover + cost
            if self.cash < total_needed:
                self.write_log(f"资金不足：需要{total_needed}，可用{self.cash}")
                return False, "资金不足"

            self.cash -= total_needed
        else:
            # 卖出时释放资金
            self.cash += turnover - cost

        # 更新持仓
        if direction == Direction.LONG:
            self._update_position(vt_symbol, volume, price, is_buy=True)

            # 记录T+1买入
            if self.enable_t1:
                self.t1_simulator.record_buy(vt_symbol, volume, price, trade_date)
        else:
            self._update_position(vt_symbol, volume, price, is_buy=False)

            # 记录T+1卖出
            if self.enable_t1:
                self.t1_simulator.record_sell(vt_symbol, volume, price, trade_date)

        # 生成成交记录
        self._create_trade(vt_symbol, direction, offset, price, volume)

        return True, "成交"

    def _update_position(
        self,
        vt_symbol: str,
        volume: int,
        price: float,
        is_buy: bool
    ) -> None:
        """更新持仓"""
        if is_buy:
            old_volume = self.positions.get(vt_symbol, 0)
            old_cost = old_volume * self.avg_prices.get(vt_symbol, 0)
            new_cost = old_cost + volume * price
            new_volume = old_volume + volume

            self.positions[vt_symbol] = new_volume
            self.avg_prices[vt_symbol] = new_cost / new_volume if new_volume > 0 else 0.0
        else:
            old_volume = self.positions.get(vt_symbol, 0)
            new_volume = old_volume - volume

            self.positions[vt_symbol] = new_volume
            if new_volume == 0:
                self.avg_prices.pop(vt_symbol, None)
                self.positions.pop(vt_symbol, None)

    def _create_trade(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: int
    ) -> None:
        """创建成交记录"""
        self.trade_count += 1
        trade_id = f"TRADE_{self.trade_count}"
        order_id = f"ORDER_{self.trade_count}"

        # 提取symbol和exchange
        symbol, exchange = extract_vt_symbol(vt_symbol)

        trade = TradeData(
            symbol=symbol,
            exchange=exchange,
            orderid=order_id,
            tradeid=trade_id,
            direction=direction,
            offset=offset,
            price=price,
            volume=volume,
            datetime=self.current_datetime or datetime.now(),
            gateway_name=self.gateway_name
        )

        self.trades[trade_id] = trade

    def get_position(self, vt_symbol: str) -> int:
        """获取持仓"""
        return self.positions.get(vt_symbol, 0)

    def get_equity(self) -> float:
        """获取当前权益（现金 + 持仓按市价计算）"""
        # 持仓市值：优先用回测当前市价，无市价快照时回退持仓均价
        position_value = 0.0
        for vt_symbol, volume in self.positions.items():
            price = self.current_prices.get(vt_symbol)
            if price is None:
                price = self.avg_prices.get(vt_symbol, 0)
            position_value += volume * price

        return self.cash + position_value

    def calculate_metrics(self) -> EnhancedMetrics:
        """计算回测指标

        Returns:
            EnhancedMetrics: 回测指标
        """
        # 使用真实权益曲线与回测天数，而非此前的两点曲线 + 硬编码 240
        equity_curve = (
            self.equity_curve
            if len(self.equity_curve) >= 2
            else [self.capital, self.get_equity()]
        )
        initial_capital = self.capital
        final_capital = equity_curve[-1]
        trading_days = max(1, len(equity_curve) - 1)

        # F9: 收集各 bar 的 datetime（history_bars 保插入序），供月度收益对齐
        bar_datetimes = [bar.datetime for bar in self.history_bars.values()]
        if len(bar_datetimes) != len(equity_curve) - 1:
            # 长度不匹配：history_bars 非空则是对齐异常（断言暴露）；空则为兜底场景（月度返回 {}）
            assert not bar_datetimes, (
                f"bar_datetimes({len(bar_datetimes)}) 与 equity_curve({len(equity_curve)}) 长度不匹配"
            )
            bar_datetimes = None

        return self.metrics_calculator.calculate(
            trades=list(self.trades.values()),
            equity_curve=equity_curve,
            trading_days=trading_days,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_cost=self.total_cost,
            bar_datetimes=bar_datetimes,
        )

    def write_log(self, msg: str) -> None:
        """写日志"""
        log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}"
        self.logs.append(log)

    def get_logs(self) -> List[str]:
        """获取日志"""
        return self.logs.copy()

    def reset(self) -> None:
        """重置引擎"""
        self.positions.clear()
        self.avg_prices.clear()
        self.cash = self.capital
        self.frozen = 0.0

        self.limit_orders.clear()
        self.active_limit_orders.clear()
        self.trades.clear()
        self.trade_count = 0
        self.limit_order_count = 0

        self.total_cost = 0.0
        self.blocked_orders = 0
        self.logs.clear()

        # 重置回测时钟、市价与权益曲线
        self.current_datetime = None
        self.current_prices.clear()
        self.current_bar_volume = 0.0
        self.equity_curve = []

        self.t1_simulator.reset()


# 便捷函数
def create_engine(
    capital: float = 1_000_000,
    enable_cost: bool = True,
    enable_slippage: bool = True,
    enable_price_limit: bool = True,
    enable_t1: bool = True,
    slippage_type: str = "percent",
    slippage_value: float = 0.001
) -> EnhancedBacktestEngine:
    """创建增强回测引擎的便捷函数

    Args:
        capital: 初始资金
        enable_cost: 启用交易成本
        enable_slippage: 启用滑点
        enable_price_limit: 启用涨跌停
        enable_t1: 启用T+1
        slippage_type: 滑点类型
        slippage_value: 滑点值

    Returns:
        EnhancedBacktestEngine: 增强回测引擎
    """
    engine = EnhancedBacktestEngine()
    engine.capital = capital
    engine.cash = capital

    engine.enable_cost = enable_cost
    engine.enable_slippage = enable_slippage
    engine.enable_price_limit = enable_price_limit
    engine.enable_t1 = enable_t1

    engine.set_slippage(slippage_type, percent=slippage_value)

    return engine
