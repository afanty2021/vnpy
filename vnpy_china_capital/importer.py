"""QMT历史数据导入器"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from vnpy.trader.object import TradeData
from vnpy.trader.logger import logger


class QMTHistoryImporter:
    """QMT历史数据导入器

    用于从QMT获取历史成交数据并转换为资金流水格式
    """

    def __init__(self, main_engine: Any) -> None:
        """初始化导入器

        Args:
            main_engine: 主引擎实例
        """
        self.main_engine = main_engine
        self.rpc_client = None

    def connect_rpc(self, rpc_address: str = "tcp://127.0.0.1:2014") -> bool:
        """连接RPC服务获取历史数据

        Args:
            rpc_address: RPC服务地址

        Returns:
            是否连接成功
        """
        try:
            from vnpy.rpc import RpcClient
            self.rpc_client = RpcClient()
            self.rpc_client.connect(rpc_address, "")
            logger.info("QMT导入器RPC连接成功")
            return True
        except Exception as e:
            logger.warning(f"QMT导入器RPC连接失败: {e}")
            return False

    def fetch_history_trades(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[TradeData]:
        """从QMT获取历史成交数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史成交数据列表
        """
        if not self.rpc_client:
            logger.warning("RPC客户端未连接，无法获取历史成交")
            return []

        try:
            # 调用RPC服务获取历史成交
            # 注意：这需要QMT接口提供历史成交查询功能
            # 这里是一个示例实现，实际需要根据QMT接口调整
            trades = self.rpc_client.query_history_trades(
                symbol=symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            return trades if trades else []
        except Exception as e:
            logger.error(f"获取QMT历史成交失败: {e}", exc_info=True)
            return []

    def convert_to_capital_flows(
        self,
        trades: List[TradeData],
        account_data: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """将成交数据转换为资金流水格式

        Args:
            trades: 成交数据列表
            account_data: 账户数据 {symbol: balance, available}

        Returns:
            资金流水字典列表
        """
        flows = []

        for trade in trades:
            balance = account_data.get(trade.symbol, 0)
            available = account_data.get(f"{trade.symbol}_available", balance)

            flow = {
                "flow_id": f"QMT_{trade.vt_tradeid}",
                "gateway_name": trade.gateway_name,
                "trade_id": trade.vt_tradeid,
                "symbol": trade.symbol,
                "exchange": trade.exchange.value,
                "direction": trade.direction.value if trade.direction else "",
                "offset": trade.offset.value if trade.offset else "",
                "price": trade.price,
                "volume": trade.volume,
                "amount": trade.price * trade.volume if trade.price and trade.volume else 0.0,
                "balance": balance,
                "available": available,
                "trade_time": trade.datetime or datetime.now(),
                "created_at": datetime.now(),
                "flow_type": "trade",
                "description": f"历史成交导入-{trade.direction.value if trade.direction else ''}{trade.offset.value if trade.offset else ''}"
            }
            flows.append(flow)

        return flows

    def import_from_qmt(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        gui_engine: Any
    ) -> Dict[str, Any]:
        """从QMT导入历史数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            gui_engine: GUI引擎用于保存数据

        Returns:
            导入结果统计
        """
        total_count = 0
        success_count = 0
        errors = []

        for symbol in symbols:
            try:
                trades = self.fetch_history_trades(symbol, start_date, end_date)
                if trades:
                    flows = self.convert_to_capital_flows(trades, {})
                    result = gui_engine.import_historical_data(flows)

                    total_count += len(flows)
                    success_count += result["success_count"]
                    errors.extend(result.get("errors", []))

                    logger.info(f"导入{symbol}历史数据: {len(flows)}条，成功{result['success_count']}条")
            except Exception as e:
                error_msg = f"{symbol}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        result = {
            "total_count": total_count,
            "success_count": success_count,
            "error_count": total_count - success_count,
            "errors": errors
        }

        logger.info(f"QMT历史数据导入完成: 总计{total_count}条，成功{success_count}条，失败{result['error_count']}条")

        return result

    def import_from_qmt_file(
        self,
        file_path: str,
        gui_engine: Any
    ) -> Dict[str, Any]:
        """从QMT导出的CSV文件导入历史数据

        Args:
            file_path: CSV文件路径
            gui_engine: GUI引擎用于保存数据

        Returns:
            导入结果统计
        """
        try:
            import csv

            flows = []
            with open(file_path, 'r', encoding='gbk') as f:  # QMT导出文件通常是GBK编码
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        from vnpy.trader.constant import Direction, Offset

                        # 解析QMT导出的成交记录格式
                        # 字段映射：证券代码|证券名称|买卖方向|成交价格|成交数量|成交金额|成交时间|合同编号
                        flow = {
                            "flow_id": f"QMT_{row.get('合同编号', row.get('合同序号', ''))}",
                            "gateway_name": "QMT",
                            "trade_id": row.get("合同编号", row.get("合同序号", "")),
                            "symbol": row.get("证券代码", ""),
                            "exchange": "SSE" if row.get("证券代码", "").startswith("6") else "SZSE",
                            "direction": Direction.LONG.value if row.get("买卖方向") == "买入" else Direction.SHORT.value,
                            "offset": Offset.OPEN.value,  # QMT成交默认为开仓
                            "price": float(row.get("成交价格", 0)),
                            "volume": float(row.get("成交数量", 0)),
                            "amount": float(row.get("成交金额", 0)),
                            "balance": 0.0,  # 文件中没有余额信息，需要后续更新
                            "available": 0.0,
                            "trade_time": datetime.strptime(row.get("成交时间", ""), "%Y-%m-%d %H:%M:%S"),
                            "created_at": datetime.now(),
                            "flow_type": "买入" if row.get("买卖方向") == "买入" else "卖出",
                            "description": f"QMT历史导入-{row.get('证券名称', '')}"
                        }
                        flows.append(flow)
                    except Exception as e:
                        logger.warning(f"解析QMT CSV行失败: {e}, row: {row}")
                        continue

            # 批量导入
            result = gui_engine.import_historical_data(flows)
            result["total_count"] = len(flows)

            logger.info(f"QMT文件导入完成: 总计{len(flows)}条，成功{result['success_count']}条")

            return result

        except Exception as e:
            logger.error(f"导入QMT文件失败: {e}", exc_info=True)
            return {
                "total_count": 0,
                "success_count": 0,
                "error_count": 0,
                "errors": [str(e)]
            }


__all__ = ["QMTHistoryImporter"]
