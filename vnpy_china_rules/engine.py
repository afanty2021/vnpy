"""
规则引擎

提供A股交易规则检查功能，包括：
- T+1交易规则
- 涨跌停板规则
- 交易时间规则
- 交易单位规则
- 新股申购规则
"""

from dataclasses import dataclass, field
from datetime import datetime, time, date
from typing import List, Optional, Dict, Any
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from loguru import logger

from vnpy.trader.object import OrderData, TradeData
from vnpy.trader.constant import Direction, Exchange

from .datasource import DataSourceManager, StockInfo


@dataclass
class RuleResult:
    """
    规则检查结果

    Attributes
    ----------
    passed : bool
        是否通过规则检查
    rule_name : str
        规则名称
    message : str
        详细消息
    """
    passed: bool
    rule_name: str
    message: str


@dataclass
class PositionRecord:
    """
    持仓记录（用于T+1规则）

    Attributes
    ----------
    symbol : str
        股票代码
    volume : int
        买入数量
    buy_datetime : datetime
        买入时间
    available : int
        可用数量（卖出后减少）
    """
    symbol: str
    volume: int
    buy_datetime: datetime
    available: int


class T1RulesEngine:
    """
    T+1规则引擎

    实现A股T+1交易规则：当日买入的股票，下一交易日才能卖出。

    实现原理：
    1. 维护持仓流水记录，记录每次买入的时间、数量
    2. 计算可卖数量：遍历持仓，计算当日之前买入的股数
    3. 卖出时扣减：卖出成交后，减少对应买入记录的可用数量
    """

    def __init__(self, rules_engine: "ChinaStockRulesEngine") -> None:
        """
        初始化T+1规则引擎

        Parameters
        ----------
        rules_engine : ChinaStockRulesEngine
            规则引擎主实例
        """
        self.rules_engine: "ChinaStockRulesEngine" = rules_engine
        # 持仓流水记录 {symbol: [PositionRecord, ...]}
        self.positions: Dict[str, List[PositionRecord]] = defaultdict(list)

        logger.info("T+1规则引擎初始化成功")

    def record_buy(self, symbol: str, volume: int, datetime: datetime) -> None:
        """
        记录买入成交

        Parameters
        ----------
        symbol : str
            股票代码
        volume : int
            买入数量
        datetime : datetime
            买入时间
        """
        # 参数验证
        if volume <= 0:
            logger.warning(f"买入数量必须大于0: {volume}")
            return

        # 创建持仓记录
        record = PositionRecord(
            symbol=symbol,
            volume=volume,
            buy_datetime=datetime,
            available=volume
        )

        # 添加到持仓流水
        self.positions[symbol].append(record)

        logger.debug(f"记录买入: {symbol} {volume}股 时间:{datetime}")

    def record_sell(self, symbol: str, volume: int, datetime: datetime) -> None:
        """
        记录卖出成交

        使用FIFO（先进先出）原则扣减持仓记录的可用数量。

        Parameters
        ----------
        symbol : str
            股票代码
        volume : int
            卖出数量
        datetime : datetime
            卖出时间
        """
        # 参数验证
        if volume <= 0:
            logger.warning(f"卖出数量必须大于0: {volume}")
            return

        # 获取持仓记录
        if symbol not in self.positions:
            logger.warning(f"股票{symbol}没有持仓记录")
            return

        remaining = volume

        # 按时间顺序扣减（FIFO）
        for record in self.positions[symbol]:
            if remaining <= 0:
                break

            if record.available > 0:
                deduct = min(record.available, remaining)
                record.available -= deduct
                remaining -= deduct
                logger.debug(
                    f"扣减持仓: {symbol} {deduct}股 "
                    f"买入时间:{record.buy_datetime} "
                    f"剩余可用:{record.available}"
                )

        if remaining > 0:
            logger.warning(
                f"卖出数量超过可卖数量: {symbol} 超出{remaining}股"
            )

    def get_sellable_volume(self, symbol: str, current_datetime: datetime) -> int:
        """
        获取可卖出数量

        计算规则：只有当前日期之前买入的股票才可以卖出。

        Parameters
        ----------
        symbol : str
            股票代码
        current_datetime : datetime
            当前时间

        Returns
        -------
        int
            可卖出数量
        """
        if symbol not in self.positions:
            return 0

        current_date = current_datetime.date()
        sellable = 0

        # 遍历持仓记录，计算可卖数量
        for record in self.positions[symbol]:
            # 只有当前日期之前买入的才可以卖出
            if record.buy_datetime.date() < current_date:
                sellable += record.available

        logger.debug(f"可卖数量: {symbol} {sellable}股")
        return sellable

    def check(self, order: OrderData) -> RuleResult:
        """
        检查卖出订单的T+1规则

        Parameters
        ----------
        order : OrderData
            委托订单

        Returns
        -------
        RuleResult
            规则检查结果
        """
        # 买入订单不受T+1限制
        if order.direction == Direction.LONG:
            return RuleResult(
                passed=True,
                rule_name="T+1规则",
                message="买入订单不受T+1限制"
            )

        # 卖出订单需要检查T+1规则
        if order.direction == Direction.SHORT:
            # 获取可卖数量
            sellable = self.get_sellable_volume(
                order.symbol,
                order.datetime or datetime.now()
            )

            # 检查可卖数量是否足够
            if sellable < int(order.volume):
                return RuleResult(
                    passed=False,
                    rule_name="T+1规则",
                    message=f"可卖数量不足：需要{int(order.volume)}股，可卖{sellable}股"
                )

            return RuleResult(
                passed=True,
                rule_name="T+1规则",
                message=f"T+1检查通过，可卖{sellable}股"
            )

        # 其他类型订单通过
        return RuleResult(
            passed=True,
            rule_name="T+1规则",
            message="非买卖订单，不检查T+1规则"
        )


class PriceLimitRulesEngine:
    """
    涨跌停规则引擎

    实现A股涨跌停板价格检查：
    - 主板：10%
    - 创业板：20%
    - 科创板：20%
    - 北交所：30%
    - ST股票：5%
    """

    def __init__(self, rules_engine: "ChinaStockRulesEngine") -> None:
        """
        初始化涨跌停规则引擎

        Parameters
        ----------
        rules_engine : ChinaStockRulesEngine
            规则引擎主实例
        """
        self.rules_engine: "ChinaStockRulesEngine" = rules_engine

        logger.info("涨跌停规则引擎初始化成功")

    def calculate_limit_price(
        self,
        symbol: str,
        prev_close: float,
        limit_ratio: Optional[float] = None
    ) -> tuple[float, float]:
        """
        计算涨跌停价格

        Parameters
        ----------
        symbol : str
            股票代码
        prev_close : float
            昨日收盘价
        limit_ratio : Optional[float]
            涨跌停比例（如果为None，则从股票信息获取）

        Returns
        -------
        tuple[float, float]
            (涨停价, 跌停价)
        """
        # 如果没有指定涨跌停比例，尝试从数据源获取
        if limit_ratio is None:
            stock_info = self.rules_engine.dm.get_stock_info(symbol)
            if stock_info:
                limit_ratio = stock_info.limit_ratio
            else:
                # 默认主板10%
                limit_ratio = self.rules_engine.LIMIT_RATIO_MAIN
                logger.warning(
                    f"无法获取股票{symbol}的涨跌停比例，使用默认值10%"
                )

        # 计算涨跌停价格
        # 使用Decimal确保精度
        prev_close_decimal = Decimal(str(prev_close))
        limit_ratio_decimal = Decimal(str(limit_ratio))

        limit_up = float(
            (prev_close_decimal * (Decimal("1") + limit_ratio_decimal))
            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        limit_down = float(
            (prev_close_decimal * (Decimal("1") - limit_ratio_decimal))
            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        logger.debug(
            f"涨跌停价格: {symbol} 昨收:{prev_close} "
            f"涨停:{limit_up} 跌停:{limit_down} 比例:{limit_ratio*100}%"
        )

        return limit_up, limit_down

    def check(
        self,
        order: OrderData,
        prev_close: Optional[float] = None
    ) -> RuleResult:
        """
        检查委托价格的涨跌停规则

        Parameters
        ----------
        order : OrderData
            委托订单
        prev_close : Optional[float]
            昨日收盘价（如果为None，则从数据源获取）

        Returns
        -------
        RuleResult
            规则检查结果
        """
        # 获取股票信息
        stock_info = self.rules_engine.dm.get_stock_info(order.symbol)

        if stock_info is None:
            logger.warning(f"无法获取股票{order.symbol}的信息，跳过涨跌停检查")
            return RuleResult(
                passed=True,
                rule_name="涨跌停规则",
                message="股票信息不可用，跳过涨跌停检查"
            )

        # 获取昨日收盘价
        if prev_close is None:
            # 尝试从行情数据获取
            market_data = self.rules_engine.dm.get_market_data(order.symbol)
            if market_data:
                if hasattr(market_data, "pre_close"):
                    prev_close = market_data.pre_close
                else:
                    logger.warning(f"行情数据没有pre_close字段")
                    return RuleResult(
                        passed=True,
                        rule_name="涨跌停规则",
                        message="昨日收盘价不可用，跳过涨跌停检查"
                    )
            else:
                logger.warning(f"无法获取股票{order.symbol}的行情数据")
                return RuleResult(
                    passed=True,
                    rule_name="涨跌停规则",
                    message="行情数据不可用，跳过涨跌停检查"
                )

        if prev_close is None or prev_close <= 0:
            logger.warning(f"昨日收盘价无效: {prev_close}")
            return RuleResult(
                passed=True,
                rule_name="涨跌停规则",
                message="昨日收盘价无效，跳过涨跌停检查"
            )

        # 计算涨跌停价格
        limit_up, limit_down = self.calculate_limit_price(
            order.symbol,
            prev_close,
            stock_info.limit_ratio
        )

        # 检查买入价格
        if order.direction == Direction.LONG:
            if order.price > limit_up:
                return RuleResult(
                    passed=False,
                    rule_name="涨跌停规则",
                    message=f"买入价{order.price:.2f}超过涨停价{limit_up:.2f}"
                )

        # 检查卖出价格
        elif order.direction == Direction.SHORT:
            if order.price < limit_down:
                return RuleResult(
                    passed=False,
                    rule_name="涨跌停规则",
                    message=f"卖出价{order.price:.2f}低于跌停价{limit_down:.2f}"
                )

        return RuleResult(
            passed=True,
            rule_name="涨跌停规则",
            message=f"价格检查通过：涨停{limit_up:.2f} 跌停{limit_down:.2f}"
        )


class TimeRulesEngine:
    """
    交易时间规则引擎

    实现A股交易时间检查：
    - 集合竞价：9:15-9:25
    - 上午交易：9:30-11:30
    - 下午交易：13:00-15:00
    """

    def __init__(self, rules_engine: "ChinaStockRulesEngine") -> None:
        """
        初始化交易时间规则引擎

        Parameters
        ----------
        rules_engine : ChinaStockRulesEngine
            规则引擎主实例
        """
        self.rules_engine: "ChinaStockRulesEngine" = rules_engine

        logger.info("交易时间规则引擎初始化成功")

    def is_trading_time(self, dt: datetime) -> bool:
        """
        判断是否在交易时间

        Parameters
        ----------
        dt : datetime
            待判断的时间

        Returns
        -------
        bool
            是否在交易时间
        """
        current_time = dt.time()

        # 集合竞价时间：9:15-9:25
        if time(9, 15) <= current_time <= time(9, 25):
            return True

        # 上午交易时间：9:30-11:30
        if time(9, 30) <= current_time <= time(11, 30):
            return True

        # 下午交易时间：13:00-15:00
        if time(13, 0) <= current_time <= time(15, 0):
            return True

        return False

    def can_submit_order(self, dt: datetime) -> bool:
        """
        判断是否可委托

        可委托时间：
        - 集合竞价时间：9:15-9:25
        - 正常交易时间：9:30-11:30, 13:00-15:00

        Parameters
        ----------
        dt : datetime
            待判断的时间

        Returns
        -------
        bool
            是否可委托
        """
        return self.is_trading_time(dt)

    def check(self, order: OrderData) -> RuleResult:
        """
        检查委托时间的交易时间规则

        Parameters
        ----------
        order : OrderData
            委托订单

        Returns
        -------
        RuleResult
            规则检查结果
        """
        # 获取订单时间
        order_time = order.datetime or datetime.now()

        # 检查是否在交易时间
        if not self.is_trading_time(order_time):
            return RuleResult(
                passed=False,
                rule_name="交易时间规则",
                message=f"非交易时间：{order_time.strftime('%H:%M:%S')}"
            )

        return RuleResult(
            passed=True,
            rule_name="交易时间规则",
            message=f"交易时间检查通过：{order_time.strftime('%H:%M:%S')}"
        )


class UnitRulesEngine:
    """
    交易单位规则引擎

    实现A股交易单位检查：
    - 最小交易单位：100股（1手）
    - 必须是100股的整数倍
    """

    def __init__(self, rules_engine: "ChinaStockRulesEngine") -> None:
        """
        初始化交易单位规则引擎

        Parameters
        ----------
        rules_engine : ChinaStockRulesEngine
            规则引擎主实例
        """
        self.rules_engine: "ChinaStockRulesEngine" = rules_engine
        self.MIN_UNIT = 100  # 最小交易单位

        logger.info("交易单位规则引擎初始化成功")

    def check(self, order: OrderData) -> RuleResult:
        """
        检查委托数量的交易单位规则

        Parameters
        ----------
        order : OrderData
            委托订单

        Returns
        -------
        RuleResult
            规则检查结果
        """
        volume = int(order.volume)

        # 检查是否小于最小单位
        if volume < self.MIN_UNIT:
            return RuleResult(
                passed=False,
                rule_name="交易单位规则",
                message=f"委托数量{volume}股小于最小单位{self.MIN_UNIT}股"
            )

        # 检查是否为100的整数倍
        if volume % self.MIN_UNIT != 0:
            return RuleResult(
                passed=False,
                rule_name="交易单位规则",
                message=f"委托数量{volume}股必须是{self.MIN_UNIT}股的整数倍"
            )

        return RuleResult(
            passed=True,
            rule_name="交易单位规则",
            message=f"交易单位检查通过：{volume}股"
        )


class IpoRulesEngine:
    """
    新股申购规则引擎

    实现A股新股申购规则：
    - 申购额度计算：市值每1万元可申购1000股
    - T-2日前20个交易日的日均市值
    """

    def __init__(self, rules_engine: "ChinaStockRulesEngine") -> None:
        """
        初始化新股申购规则引擎

        Parameters
        ----------
        rules_engine : ChinaStockRulesEngine
            规则引擎主实例
        """
        self.rules_engine: "ChinaStockRulesEngine" = rules_engine

        logger.info("新股申购规则引擎初始化成功")

    def calculate_subs_quota(self, account_data: Dict[str, Any]) -> int:
        """
        计算申购额度

        申购额度 = 市值 / 10000 * 1000

        Parameters
        ----------
        account_data : Dict[str, Any]
            账户数据，包含：
            - market_value: 市值（元）
            - cash: 现金（元）

        Returns
        -------
        int
            申购额度（股）
        """
        market_value = account_data.get("market_value", 0)

        # 计算申购额度（向下取整到1000股的倍数）
        quota = int(market_value / 10000) * 1000

        logger.debug(f"申购额度计算: 市值{market_value}元 -> 额度{quota}股")

        return quota

    def check(self, order: OrderData) -> RuleResult:
        """
        检查新股申购订单

        Parameters
        ----------
        order : OrderData
            委托订单

        Returns
        -------
        RuleResult
            规则检查结果
        """
        # 新股申购检查逻辑
        # 这里需要根据实际的申购规则实现
        # 暂时返回通过

        return RuleResult(
            passed=True,
            rule_name="新股申购规则",
            message="新股申购检查通过"
        )


class ChinaStockRulesEngine:
    """
    A股交易规则引擎

    提供完整的A股交易规则检查功能，包括T+1、涨跌停、交易时间、交易单位、新股申购等规则。

    Attributes
    ----------
    dm : DataSourceManager
        数据源管理器
    t1_rules : T1RulesEngine
        T+1规则引擎
    price_limit_rules : PriceLimitRulesEngine
        涨跌停规则引擎
    time_rules : TimeRulesEngine
        交易时间规则引擎
    unit_rules : UnitRulesEngine
        交易单位规则引擎
    ipo_rules : IpoRulesEngine
        新股申购规则引擎

    常量
    ----------
    TRADING_MORNING_START : time
        上午交易开始时间：9:15
    TRADING_MORNING_END : time
        上午交易结束时间：11:30
    TRADING_AFTERNOON_START : time
        下午交易开始时间：13:00
    TRADING_AFTERNOON_END : time
        下午交易结束时间：15:00
    LIMIT_RATIO_MAIN : float
        主板涨跌停比例：10%
    LIMIT_RATIO_SME : float
        创业板涨跌停比例：20%
    LIMIT_RATIO_SCI : float
        科创板涨跌停比例：20%
    LIMIT_RATIO_BSE : float
        北交所涨跌停比例：30%
    LIMIT_RATIO_ST : float
        ST股票涨跌停比例：5%
    """

    # 交易时间常量
    TRADING_MORNING_START: time = time(9, 15)
    TRADING_MORNING_END: time = time(11, 30)
    TRADING_AFTERNOON_START: time = time(13, 0)
    TRADING_AFTERNOON_END: time = time(15, 0)

    # 涨跌停比例常量
    LIMIT_RATIO_MAIN: float = 0.10  # 主板10%
    LIMIT_RATIO_SME: float = 0.20  # 创业板20%
    LIMIT_RATIO_SCI: float = 0.20  # 科创板20%
    LIMIT_RATIO_BSE: float = 0.30  # 北交所30%
    LIMIT_RATIO_ST: float = 0.05   # ST股票5%

    def __init__(self, datasource_manager: DataSourceManager, db: Optional[Any] = None) -> None:
        """
        初始化A股交易规则引擎

        Parameters
        ----------
        datasource_manager : DataSourceManager
            数据源管理器
        db : Optional[Any]
            可选持久化连接（需实现 execute(sql,args)->int、query(sql,args)->List[dict]，
            如 vnpy_china_reporting.data_source.db.DataSourceDB）。为 None 时纯内存模式。
        """
        self.dm = datasource_manager

        # 初始化子规则引擎
        self.t1_rules = T1RulesEngine(self)
        self.price_limit_rules = PriceLimitRulesEngine(self)
        self.time_rules = TimeRulesEngine(self)
        self.unit_rules = UnitRulesEngine(self)
        self.ipo_rules = IpoRulesEngine(self)

        # T+1 持久化（可选）：db 注入时建表并重放，失败降级纯内存。
        # 降级时已建好的 t1_trade_flow 表会保留（CREATE TABLE IF NOT EXISTS 幂等，
        # 下次启动复用），不影响纯内存模式的正确性。
        self.store = None
        if db is not None:
            try:
                from vnpy_china_rules.t1_store import T1PositionStore
                self.store = T1PositionStore(db)
                self.store.init_schema()
                self._replay()
            except Exception as e:
                self.store = None
                logger.exception(f"T+1持久化初始化失败，降级纯内存模式: {e}")

        logger.info("A股交易规则引擎初始化成功")

    def _replay(self) -> None:
        """从流水重放重建T+1内存持仓

        读取 t1_trade_flow 全表（已按 trade_time, id 排序），逐条喂给
        record_buy/record_sell，与正常成交路径复用同一逻辑。
        单条脏数据（类型异常等）只告警跳过、不中断整体重放，避免持久
        脏数据导致每次启动都降级。
        """
        if self.store is None:
            return
        processed = 0
        skipped = 0
        for row in self.store.load_all():
            try:
                symbol = row["symbol"]
                volume = int(row["volume"])
                dt = row["trade_time"]
                if row["direction"] == Direction.LONG.value:      # "多"
                    self.t1_rules.record_buy(symbol, volume, dt)
                    processed += 1
                elif row["direction"] == Direction.SHORT.value:   # "空"
                    self.t1_rules.record_sell(symbol, volume, dt)
                    processed += 1
                else:
                    # NET 或异常值：跳过（不应出现在成交流水）
                    skipped += 1
            except Exception as e:
                skipped += 1
                logger.warning(f"T+1重放跳过异常流水行: {row}, 原因: {e}")
        logger.info(f"T+1持仓重放完成，重放 {processed} 条，跳过 {skipped} 条")

    def check_order(self, order: OrderData) -> List[RuleResult]:
        """
        全面检查订单合规性

        依次检查所有规则，返回所有规则的检查结果。

        Parameters
        ----------
        order : OrderData
            委托订单

        Returns
        -------
        List[RuleResult]
            所有规则的检查结果列表
        """
        results = []

        # 1. 交易时间规则
        results.append(self.time_rules.check(order))

        # 2. 交易单位规则
        results.append(self.unit_rules.check(order))

        # 3. 涨跌停规则
        results.append(self.price_limit_rules.check(order))

        # 4. T+1规则
        results.append(self.t1_rules.check(order))

        # 5. 新股申购规则（如果适用）
        # results.append(self.ipo_rules.check(order))

        return results

    def can_submit_order(self, order: OrderData) -> tuple[bool, str]:
        """
        判断订单是否可提交

        综合所有规则检查结果，返回订单是否可以提交。

        Parameters
        ----------
        order : OrderData
            委托订单

        Returns
        -------
        tuple[bool, str]
            (是否可提交, 原因说明)
        """
        # 检查所有规则
        results = self.check_order(order)

        # 检查是否有未通过的规则
        for result in results:
            if not result.passed:
                return False, f"{result.rule_name}：{result.message}"

        return True, "订单检查通过"

    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调

        先落 T+1 流水（崩溃恢复权威），再更新内存持仓（T+1 检查权威）。
        DB 与内存共用单次计算的 trade_time，保证原始执行与重放一致。
        重复 vt_tradeid 时 DB 层 INSERT IGNORE 返回 0，内存同步跳过以保持幂等。

        Parameters
        ----------
        trade : TradeData
            成交数据
        """
        # 单次计算时间戳，DB 与内存共用（避免 now() 不幂等导致重放漂移）
        trade_time = trade.datetime or datetime.now()

        # 先落库；失败降级纯内存，不阻断成交回调
        update_memory = True
        if self.store is not None:
            try:
                rows = self.store.append_trade(
                    trade.vt_tradeid, trade.symbol,
                    trade.direction.value, int(trade.volume), trade_time,
                )
                if rows == 0:
                    # 重复 trade_id：DB 已忽略，内存同步跳过以保持一致（幂等）
                    update_memory = False
                    logger.info(f"重复成交已忽略，不重复记录T+1持仓: {trade.vt_tradeid}")
            except Exception as e:
                logger.warning(f"T+1流水写入失败，降级纯内存: {e}")

        # 再更新内存（T+1 检查权威；重复成交或 store=None 时仍按需更新）
        if update_memory:
            if trade.direction == Direction.LONG:
                self.t1_rules.record_buy(
                    symbol=trade.symbol,
                    volume=int(trade.volume),
                    datetime=trade_time,
                )
            elif trade.direction == Direction.SHORT:
                self.t1_rules.record_sell(
                    symbol=trade.symbol,
                    volume=int(trade.volume),
                    datetime=trade_time,
                )

        logger.debug(f"成交回调处理完成: {trade.symbol} {trade.direction.value} {trade.volume}股")
