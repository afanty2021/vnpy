"""
风控过滤器

提供A股交易规则风控过滤器，可集成到VeighNa框架的风控系统中。
"""

from loguru import logger

from vnpy.trader.object import OrderData, TradeData
from vnpy.trader.constant import Direction

from vnpy_china_rules.engine import ChinaStockRulesEngine


class ChinaStockRiskFilter:
    """
    A股交易风控过滤器

    作为VeighNa框架的风控过滤器，在订单提交前进行规则检查，
    在成交后更新T+1持仓记录。

    集成方式：
    ```python
    from vnpy_china_rules import ChinaStockRiskFilter

    # 创建风控过滤器
    risk_filter = ChinaStockRiskFilter(rules_engine)

    # 注册到主引擎（需要VeighNa框架支持）
    main_engine.add_risk_filter(risk_filter)
    ```

    注意事项：
    - 该过滤器需要在策略执行后、订单提交前被调用
    - 成交后必须调用on_trade更新T+1持仓记录
    - 可以通过enabled属性启用/禁用过滤器

    Attributes
    ----------
    rules_engine : ChinaStockRulesEngine
        A股交易规则引擎
    enabled : bool
        是否启用过滤器，默认为True

    Example
    -------
    ```python
    # 初始化
    risk_filter = ChinaStockRiskFilter(rules_engine)

    # 订单检查（返回是否通过和原因）
    passed, message = risk_filter.check_order(order)

    # 成交回调（更新T+1记录）
    risk_filter.on_trade(trade)

    # 禁用过滤器
    risk_filter.enabled = False
    ```
    """

    def __init__(self, rules_engine: ChinaStockRulesEngine) -> None:
        """
        初始化风控过滤器

        Parameters
        ----------
        rules_engine : ChinaStockRulesEngine
            A股交易规则引擎实例
        """
        self.rules_engine: ChinaStockRulesEngine = rules_engine
        self.enabled: bool = True

        logger.info("A股交易风控过滤器初始化成功")

    def check_order(self, order: OrderData) -> tuple[bool, str]:
        """
        订单检查回调

        被VeighNa风控系统调用，用于检查订单是否符合A股交易规则。

        检查规则包括：
        - 交易时间规则：是否在可交易时间内
        - 交易单位规则：数量是否为100股的整数倍
        - 涨跌停规则：买入价是否超过涨停价，卖出价是否低于跌停价
        - T+1规则：当日买入的股票是否可卖出

        Parameters
        ----------
        order : OrderData
            委托订单数据

        Returns
        -------
        tuple[bool, str]
            (是否通过检查, 原因消息)
            - 如果通过，返回 (True, "")
            - 如果不通过，返回 (False, "规则名称：具体原因")

        Example
        -------
        ```python
        passed, message = risk_filter.check_order(order)
        if not passed:
            print(f"订单被风控拦截: {message}")
        ```
        """
        # 如果过滤器被禁用，直接通过
        if not self.enabled:
            logger.debug("风控过滤器已禁用，跳过检查")
            return True, ""

        try:
            # 使用规则引擎进行全面检查
            results = self.rules_engine.check_order(order)

            # 检查所有规则结果
            failed_rules = [r for r in results if not r.passed]

            if failed_rules:
                # 返回第一个失败的规则消息
                rule = failed_rules[0]
                logger.warning(
                    f"订单检查未通过: {order.symbol} "
                    f"{order.direction.value} {order.volume}股 "
                    f"规则:{rule.rule_name} 原因:{rule.message}"
                )
                return False, f"{rule.rule_name}：{rule.message}"

            logger.debug(
                f"订单检查通过: {order.symbol} "
                f"{order.direction.value} {order.volume}股"
            )
            return True, "所有规则检查通过"

        except Exception as e:
            # 发生异常时记录日志并返回失败
            logger.error(f"订单检查发生异常: {e}")
            return False, f"订单检查异常：{str(e)}"

    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调

        当订单成交后被调用，用于更新T+1持仓记录。
        买入成交后记录持仓，卖出成交后扣减可用数量。

        Parameters
        ----------
        trade : TradeData
            成交数据

        Example
        -------
        ```python
        # 在策略的on_trade回调中调用
        def on_trade(self, trade):
            risk_filter.on_trade(trade)
        ```
        """
        try:
            # 买入成交：记录持仓
            if trade.direction == Direction.LONG:
                self.rules_engine.t1_rules.record_buy(
                    symbol=trade.symbol,
                    volume=int(trade.volume),
                    datetime=trade.datetime,
                )
                logger.info(
                    f"买入成交记录: {trade.symbol} "
                    f"{trade.volume}股 时间:{trade.datetime}"
                )

            # 卖出成交：扣减持仓
            elif trade.direction == Direction.SHORT:
                self.rules_engine.t1_rules.record_sell(
                    symbol=trade.symbol,
                    volume=int(trade.volume),
                    datetime=trade.datetime,
                )
                logger.info(
                    f"卖出成交记录: {trade.symbol} "
                    f"{trade.volume}股 时间:{trade.datetime}"
                )

        except Exception as e:
            logger.error(f"成交回调处理失败: {e}")

    def on_order(self, order: OrderData) -> None:
        """
        订单状态回调（可选实现）

        当订单状态变化时被调用，可用于记录订单日志。

        Parameters
        ----------
        order : OrderData
            订单数据
        """
        logger.debug(
            f"订单状态变化: {order.symbol} "
            f"{order.orderid} 状态:{order.status.value}"
        )

    def on_cancel(self, order: OrderData) -> None:
        """
        订单撤销回调（可选实现）

        当订单被撤销时被调用。

        Parameters
        ----------
        order : OrderData
            订单数据
        """
        logger.info(
            f"订单撤销: {order.symbol} "
            f"{order.orderid}"
        )


def create_risk_filter(rules_engine: ChinaStockRulesEngine) -> ChinaStockRiskFilter:
    """
    创建风控过滤器的便捷函数

    Parameters
    ----------
    rules_engine : ChinaStockRulesEngine
        A股交易规则引擎实例

    Returns
    -------
    ChinaStockRiskFilter
        风控过滤器实例

    Example
    -------
    ```python
    from vnpy_china_rules import create_risk_filter, create_rules_engine

    # 创建规则引擎
    rules_engine = create_rules_engine(qmt_gateway=gateway)

    # 创建风控过滤器
    risk_filter = create_risk_filter(rules_engine)

    # 注册到主引擎
    main_engine.add_risk_filter(risk_filter)
    ```
    """
    return ChinaStockRiskFilter(rules_engine)
