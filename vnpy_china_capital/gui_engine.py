"""A股资金管理GUI引擎"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine
from vnpy.trader.object import TradeData, AccountData
from vnpy.trader.logger import logger

from .database import CapitalFlowDatabase


class ChinaCapitalGuiEngine(BaseEngine):
    """A股资金管理GUI引擎

    提供资金流水的实时记录和查询功能：
    - 监听成交事件，自动记录资金流水
    - 集成vnpy_china_data的数据库进行持久化
    - 提供内存缓存作为fallback
    - 支持历史数据导入和查询
    """

    engine_name: str = "ChinaCapitalApp"

    def __init__(self, main_engine, event_engine: EventEngine):
        """初始化GUI引擎

        Args:
            main_engine: 主引擎实例
            event_engine: 事件引擎实例
        """
        super().__init__(main_engine, event_engine, self.engine_name)

        # 数据库操作实例
        self.capital_db: Optional[Any] = None
        self.capital_flow_db: Optional[CapitalFlowDatabase] = None

        # 资金流水缓存（数据库不可用时使用）
        self.flows_cache: List[Dict[str, Any]] = []

        # 初始化数据库连接
        self._init_database()

    def init(self) -> None:
        """引擎初始化入口"""
        self.main_engine.write_log("A股资金管理引擎初始化完成", self.engine_name)

    def _init_database(self) -> None:
        """初始化数据库连接"""
        try:
            # 尝试使用vnpy_china_data的数据库
            from vnpy_china_data.database import MySQLDatabaseLayer
            from vnpy_china_data.service import get_data_service

            ds = get_data_service()
            if hasattr(ds, 'database') and ds.database:
                self.capital_db = ds.database

                # 创建资金流水表
                if hasattr(self.capital_db, 'create_capital_flow_table'):
                    self.capital_db.create_capital_flow_table()

                # 初始化资金流水数据库操作层
                self.capital_flow_db = CapitalFlowDatabase(self.capital_db)

                self.main_engine.write_log("资金流水数据库初始化成功", self.engine_name)
            else:
                self.main_engine.write_log("警告：数据库未连接，使用内存缓存", self.engine_name)
        except Exception as e:
            logger.warning(f"数据库初始化失败: {e}")
            self.main_engine.write_log("使用内存模式记录资金流水", self.engine_name)

    def register_event(self) -> None:
        """注册事件监听"""
        # 订阅成交事件
        self.event_engine.register("trade", self.process_trade_event)
        # 订阅账户事件
        self.event_engine.register("account", self.process_account_event)

    def process_trade_event(self, event: Event) -> None:
        """处理成交事件，记录资金流水

        Args:
            event: 成交事件
        """
        trade: TradeData = event.data

        try:
            # 获取账户信息
            accounts = self.main_engine.get_all_accounts()
            if not accounts:
                logger.warning("无法获取账户信息，跳过资金流水记录")
                return

            # 按 trade.gateway_name 匹配账户（多 gateway 场景）；无匹配回退 accounts[0]
            # 注：TradeData 不携带 accountid，gateway_name 是可匹配的最高精度
            account = None
            for acc in accounts:
                if acc.gateway_name == trade.gateway_name:
                    account = acc
                    break
            if account is None:
                account = accounts[0]

            # 保存流水
            if self.capital_flow_db:
                flow = self.capital_flow_db.save_capital_flow_from_trade(
                    trade,
                    account,
                    "trade",
                    f"{trade.direction.value}{trade.offset.value} {trade.symbol}"
                )
                if flow:
                    self.main_engine.write_log(
                        f"记录资金流水: {trade.symbol} {trade.direction.value} {trade.price}x{trade.volume}",
                        self.engine_name
                    )
            else:
                # 内存缓存模式
                flow_dict = {
                    "gateway_name": trade.gateway_name,
                    "trade_id": trade.tradeid,
                    "symbol": trade.symbol,
                    "exchange": trade.exchange.value,
                    "direction": trade.direction.value if trade.direction else "",
                    "offset": trade.offset.value if trade.offset else "",
                    "price": float(trade.price) if trade.price is not None else 0.0,
                    "volume": float(trade.volume) if trade.volume is not None else 0.0,
                    "amount": float(trade.price * trade.volume) if trade.price and trade.volume else 0.0,
                    "balance": float(account.balance) if account.balance is not None else 0.0,
                    "available": float(account.balance - account.frozen) if account.balance is not None else 0.0,
                    "trade_time": trade.datetime or datetime.now(),
                    "created_at": datetime.now(),
                    "flow_type": "trade",
                    "description": f"{trade.direction.value}{trade.offset.value} {trade.symbol}"
                }
                self.flows_cache.append(flow_dict)

                self.main_engine.write_log(
                    f"记录资金流水(缓存): {trade.symbol} {trade.direction.value} {trade.price}x{trade.volume}",
                    self.engine_name
                )

        except Exception as e:
            logger.error(f"处理成交事件失败: {e}", exc_info=True)

    def process_account_event(self, event: Event) -> None:
        """处理账户事件（记录出入金等操作）

        Args:
            event: 账户事件
        """
        # 可以扩展记录出入金、手续费等操作
        pass

    @staticmethod
    def _flow_to_dict(flow: "CapitalFlowData") -> Dict[str, Any]:
        """CapitalFlowData → 字典（统一映射，消除 get_capital_flows/import_historical_data 重复）"""
        return {
            "flow_id": flow.flow_id,
            "gateway_name": flow.gateway_name,
            "trade_id": flow.trade_id,
            "symbol": flow.symbol,
            "exchange": flow.exchange,
            "direction": flow.direction.value if flow.direction else "",
            "offset": flow.offset.value if flow.offset else "",
            "price": float(flow.price) if flow.price is not None else 0.0,
            "volume": float(flow.volume) if flow.volume is not None else 0.0,
            "amount": float(flow.amount) if flow.amount is not None else 0.0,
            "balance": float(flow.balance) if flow.balance is not None else 0.0,
            "available": float(flow.available) if flow.available is not None else 0.0,
            "trade_time": flow.trade_time,
            "created_at": flow.created_at,
            "flow_type": flow.flow_type,
            "description": flow.description,
        }

    def get_capital_flows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取资金流水记录

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol: 股票代码（可选）

        Returns:
            资金流水字典列表
        """
        if self.capital_flow_db:
            try:
                flows = self.capital_flow_db.query_capital_flow(
                    start_date=start_date,
                    end_date=end_date,
                    symbol=symbol
                )

                # 转换为字典列表
                return [self._flow_to_dict(f) for f in flows]
            except Exception as e:
                logger.error(f"查询资金流水失败: {e}", exc_info=True)

        # 返回缓存数据（最近100条）
        return self.flows_cache[-100:]

    def import_historical_data(self, flows: List[Any]) -> Dict[str, Any]:
        """导入历史资金流水数据

        Args:
            flows: 历史流水列表（CapitalFlowData对象或字典）

        Returns:
            导入结果统计
        """
        success_count = 0
        error_count = 0
        errors = []

        for flow in flows:
            try:
                if self.capital_flow_db:
                    # 如果是字典，先转换为CapitalFlowData
                    from .objects.capital_flow import CapitalFlowData

                    if isinstance(flow, dict):
                        flow = CapitalFlowData.from_db_dict(flow)

                    self.capital_flow_db.save_capital_flow(flow)
                    success_count += 1
                else:
                    # 内存缓存
                    if isinstance(flow, dict):
                        self.flows_cache.append(flow)
                    else:
                        # 假设是CapitalFlowData对象
                        self.flows_cache.append(self._flow_to_dict(flow))
                    success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }

    def get_database_status(self) -> Dict[str, Any]:
        """获取数据库状态

        Returns:
            状态信息字典
        """
        return {
            "connected": self.capital_db is not None,
            "cache_count": len(self.flows_cache),
            "database_type": type(self.capital_db).__name__ if self.capital_db else "memory"
        }

    def get_flow_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """获取资金流水统计信息

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计信息字典
        """
        if self.capital_flow_db:
            return self.capital_flow_db.get_flow_statistics(start_date, end_date)

        # 返回缓存统计
        return {
            "trade": {
                "count": len(self.flows_cache),
                "total_amount": sum(f.get("amount", 0) for f in self.flows_cache),
                "symbol_count": len(set(f.get("symbol") for f in self.flows_cache))
            }
        }

    def get_daily_flow_summary(
        self,
        target_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """获取指定日期的资金流水汇总

        Args:
            target_date: 目标日期，默认为今天

        Returns:
            每日汇总列表
        """
        if self.capital_flow_db:
            return self.capital_flow_db.get_daily_flow_summary(target_date)

        # 返回缓存汇总（简化版本）
        if not target_date:
            target_date = date.today()

        summary = {}
        for flow in self.flows_cache:
            if flow.get("trade_time") and flow["trade_time"].date() == target_date:
                key = (flow.get("symbol"), flow.get("exchange"), flow.get("flow_type"))
                if key not in summary:
                    summary[key] = {
                        "symbol": flow.get("symbol"),
                        "exchange": flow.get("exchange"),
                        "flow_type": flow.get("flow_type"),
                        "count": 0,
                        "total_amount": 0.0,
                        "avg_amount": 0.0
                    }
                summary[key]["count"] += 1
                summary[key]["total_amount"] += flow.get("amount", 0.0)

        # 计算平均金额
        for item in summary.values():
            if item["count"] > 0:
                item["avg_amount"] = item["total_amount"] / item["count"]

        return sorted(summary.values(), key=lambda x: x["total_amount"], reverse=True)


__all__ = ["ChinaCapitalGuiEngine"]
