"""
A股资金管理数据库操作

提供资金流水的持久化存储和查询功能。
"""

from typing import List, Optional, Any
from datetime import date, datetime

from vnpy.trader.object import TradeData, AccountData
from vnpy.trader.logger import logger

from .objects.capital_flow import CapitalFlowData


class CapitalFlowDatabase:
    """资金流水数据库操作

    高级封装，提供便捷的资金流水管理接口。
    """

    def __init__(self, database_layer: Any):
        """初始化数据库操作层

        Args:
            database_layer: vnpy_china_data 的数据库层实例
        """
        self.db = database_layer

    def init_tables(self) -> bool:
        """初始化数据库表

        Returns:
            是否初始化成功
        """
        return self.db.create_capital_flow_table()

    def save_capital_flow(self, flow: CapitalFlowData) -> bool:
        """保存资金流水记录

        Args:
            flow: 资金流水数据

        Returns:
            是否保存成功
        """
        return self.db.save_capital_flow(flow)

    def save_capital_flow_from_trade(
        self,
        trade: TradeData,
        account: AccountData,
        flow_type: str = "trade",
        description: str = ""
    ) -> Optional[CapitalFlowData]:
        """从成交数据创建资金流水记录

        Args:
            trade: 成交数据
            account: 账户数据
            flow_type: 流水类型
            description: 说明

        Returns:
            资金流水记录，保存失败返回None
        """
        flow = CapitalFlowData.from_trade_data(
            trade_data=trade,
            account_data=account,
            flow_type=flow_type,
            description=description,
        )
        if self.save_capital_flow(flow):
            return flow
        return None

    def query_capital_flow(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None,
        flow_type: Optional[str] = None,
    ) -> List[CapitalFlowData]:
        """查询资金流水记录

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol: 股票代码
            flow_type: 流水类型

        Returns:
            资金流水列表
        """
        results = self.db.query_capital_flow(
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            symbol=symbol,
            flow_type=flow_type,
        )

        flows = []
        for row in results:
            try:
                flow = CapitalFlowData.from_db_dict(row)
                if flow_type is None or flow.flow_type == flow_type:
                    flows.append(flow)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"解析资金流水记录失败: {e}, row: {row}")
                continue
        return flows

    def query_capital_flow_by_symbol(
        self,
        symbol: str,
        days: int = 30,
    ) -> List[CapitalFlowData]:
        """查询指定股票最近N天的资金流水

        Args:
            symbol: 股票代码
            days: 天数

        Returns:
            资金流水列表
        """
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days)
        return self.query_capital_flow(start_date=start_date, end_date=end_date, symbol=symbol)

    def get_latest_capital_flow(
        self,
        symbol: Optional[str] = None,
    ) -> Optional[CapitalFlowData]:
        """获取最新的资金流水记录

        Args:
            symbol: 股票代码（可选）

        Returns:
            最新的资金流水记录
        """
        flows = self.query_capital_flow(symbol=symbol)
        return flows[0] if flows else None

    def import_historical_flows(self, flows: List[CapitalFlowData]) -> int:
        """批量导入历史流水记录

        使用executemany批量插入提升性能。

        Args:
            flows: 历史流水列表

        Returns:
            导入成功数量
        """
        if not flows:
            return 0

        try:
            from vnpy.trader.constant import Direction, Offset

            # 构建批量插入数据
            sql = """
            INSERT INTO db_capital_flow
            (flow_id, gateway_name, trade_id, symbol, exchange, direction, offset,
             price, volume, amount, balance, available, trade_time, created_at,
             flow_type, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                amount = VALUES(amount),
                balance = VALUES(balance),
                available = VALUES(available)
            """

            values = [
                (
                    flow.flow_id,
                    flow.gateway_name,
                    flow.trade_id,
                    flow.symbol,
                    flow.exchange,
                    flow.direction.value if isinstance(flow.direction, Direction) else flow.direction,
                    flow.offset.value if isinstance(flow.offset, Offset) else flow.offset,
                    float(flow.price) if flow.price is not None else None,
                    float(flow.volume) if flow.volume is not None else None,
                    float(flow.amount) if flow.amount is not None else None,
                    float(flow.balance) if flow.balance is not None else None,
                    float(flow.available) if flow.available is not None else None,
                    flow.trade_time,
                    flow.created_at,
                    flow.flow_type,
                    flow.description
                )
                for flow in flows
            ]

            result = self.db._execute_sql(sql, values, fetch_all=False, many=True)
            return result if isinstance(result, int) and result > 0 else len(flows)

        except Exception as e:
            logger.error(f"批量导入资金流水失败: {e}", exc_info=True)
            # 降级到逐条保存
            count = 0
            for flow in flows:
                if self.save_capital_flow(flow):
                    count += 1
            return count

    def delete_duplicate_flows(self) -> int:
        """删除重复的流水记录

        保留flow_id最小的记录，删除重复的记录。

        Returns:
            删除的记录数
        """
        sql = """
        DELETE t1 FROM db_capital_flow t1
        INNER JOIN db_capital_flow t2
        WHERE t1.id > t2.id
        AND t1.flow_id = t2.flow_id
        """
        result = self.db._execute_sql(sql, fetch_all=False)
        return result if isinstance(result, int) else 0

    def get_flow_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """获取资金流水统计信息

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计信息字典
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("trade_time >= %s")
            params.append(start_date.isoformat())

        if end_date:
            conditions.append("trade_time <= %s")
            params.append(end_date.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
        SELECT
            flow_type,
            COUNT(*) as count,
            SUM(amount) as total_amount,
            COUNT(DISTINCT symbol) as symbol_count
        FROM db_capital_flow
        WHERE {where_clause}
        GROUP BY flow_type
        """

        results = self.db._execute_sql(sql, tuple(params) if params else None, fetch_all=True)

        statistics = {}
        if results:
            for row in results:
                statistics[row["flow_type"]] = {
                    "count": row["count"],
                    "total_amount": float(row["total_amount"]) if row["total_amount"] else 0.0,
                    "symbol_count": row["symbol_count"],
                }

        return statistics

    def get_daily_flow_summary(
        self,
        target_date: Optional[date] = None,
    ) -> List[dict]:
        """获取指定日期的资金流水汇总

        Args:
            target_date: 目标日期，默认为今天

        Returns:
            每日汇总列表
        """
        if target_date is None:
            target_date = date.today()

        sql = """
        SELECT
            symbol,
            exchange,
            flow_type,
            COUNT(*) as count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            MIN(trade_time) as first_time,
            MAX(trade_time) as last_time
        FROM db_capital_flow
        WHERE DATE(trade_time) = %s
        GROUP BY symbol, exchange, flow_type
        ORDER BY total_amount DESC
        """

        results = self.db._execute_sql(sql, (target_date.isoformat(),), fetch_all=True)
        return results if results else []
