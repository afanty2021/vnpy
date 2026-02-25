"""
A股数据服务GUI引擎
管理A股数据服务的GUI功能
"""

from typing import Dict, Any, Optional, List
from datetime import date, datetime
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine


class ChinaDataGuiEngine(BaseEngine):
    """A股数据服务GUI引擎

    提供A股数据服务的GUI管理功能：
    - 龙虎榜数据查询
    - 北向资金数据查询
    - 板块数据查询
    - 数据服务状态监控
    """

    engine_name: str = "ChinaDataApp"

    def __init__(self, main_engine: Any, event_engine: EventEngine) -> None:
        """初始化引擎"""
        super().__init__(main_engine, event_engine, self.engine_name)

        # 数据服务引用
        self.data_service: Optional[Any] = None

        # 直接在__init__中初始化数据服务
        self._init_data_service()

    def _init_data_service(self) -> None:
        """初始化数据服务"""
        try:
            from .service import ChinaDataService, get_data_service
            # 获取或创建数据服务单例
            self.data_service = get_data_service()
            # 尝试连接数据服务
            if self.data_service.connect():
                self.main_engine.write_log("A股数据服务连接成功", "ChinaDataApp")
            else:
                self.main_engine.write_log("警告：数据服务连接失败，部分功能可能不可用", "ChinaDataApp")
        except ImportError:
            self.main_engine.write_log("警告：无法导入数据服务", "ChinaDataApp")
        except Exception as e:
            self.main_engine.write_log(f"数据服务初始化异常：{e}", "ChinaDataApp")

    def init(self) -> None:
        """引擎初始化（由VeighNa框架调用）"""
        # 数据服务已在__init__中初始化
        pass

    def query_dragon_tiger(self, trade_date: Optional[date] = None) -> List[Any]:
        """查询龙虎榜数据

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            龙虎榜数据列表
        """
        if not self.data_service:
            # 返回mock数据用于演示
            return self._get_mock_dragon_tiger_data(trade_date or date.today())

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询龙虎榜数据：{trade_date}", "ChinaDataApp")
            data = self.data_service.get_dragon_tiger_data(trade_date)
            self.main_engine.write_log(f"查询完成，共{len(data)}条记录", "ChinaDataApp")
            return data if data else self._get_mock_dragon_tiger_data(trade_date)
        except Exception as e:
            self.main_engine.write_log(f"查询龙虎榜数据失败：{e}，使用mock数据", "ChinaDataApp")
            return self._get_mock_dragon_tiger_data(trade_date)

    def query_northbound_flow(self, trade_date: Optional[date] = None) -> Optional[Any]:
        """查询北向资金流向

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            北向资金流向数据
        """
        if not self.data_service:
            # 返回mock数据用于演示
            return self._get_mock_northbound_flow(trade_date or date.today())

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询北向资金流向：{trade_date}", "ChinaDataApp")
            data = self.data_service.get_northbound_flow(trade_date)
            if data:
                self.main_engine.write_log(f"查询完成，净流入：{data.total_net_inflow:.2f}亿元", "ChinaDataApp")
            else:
                self.main_engine.write_log("未查询到北向资金数据，使用mock数据", "ChinaDataApp")
                return self._get_mock_northbound_flow(trade_date)
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询北向资金流向失败：{e}，使用mock数据", "ChinaDataApp")
            return self._get_mock_northbound_flow(trade_date)

    def get_data_service_status(self) -> Dict[str, Any]:
        """获取数据服务状态

        Returns:
            服务状态信息
        """
        status = {
            "service_loaded": self.data_service is not None,
            "connected": False,
            "service_type": "unknown"
        }

        if self.data_service:
            status["connected"] = self.data_service.connected
            status["service_type"] = type(self.data_service).__name__

        return status

    def _get_mock_dragon_tiger_data(self, trade_date: date) -> List[Any]:
        """获取mock龙虎榜数据用于演示"""
        # 创建简单的数据对象
        class DragonTigerRecord:
            def __init__(self, symbol, name, trade_date, close_price, change_pct,
                        institution_net_buy, institution_count, broker_net_buy,
                        total_buy, turnover_rate, reason):
                self.symbol = symbol
                self.name = name
                self.trade_date = trade_date
                self.close_price = close_price
                self.change_pct = change_pct
                self.institution_net_buy = institution_net_buy
                self.institution_count = institution_count
                self.broker_net_buy = broker_net_buy
                self.total_buy = total_buy
                self.turnover_rate = turnover_rate
                self.reason = reason

        return [
            DragonTigerRecord("000001", "平安银行", trade_date, 15.50, 5.23,
                             15000000, 3, 8000000, 30000000, 8.5, "涨幅偏离值达7%"),
            DragonTigerRecord("600519", "贵州茅台", trade_date, 1850.00, 2.15,
                             50000000, 5, 20000000, 80000000, 1.2, "当日涨幅偏离值达7%"),
            DragonTigerRecord("300750", "宁德时代", trade_date, 220.50, -3.12,
                             -20000000, 2, -15000000, 50000000, 6.8, "当日跌幅偏离值达7%"),
        ]

    def _get_mock_northbound_flow(self, trade_date: date) -> Any:
        """获取mock北向资金数据用于演示"""
        class NorthboundFlow:
            def __init__(self, trade_date, total_net_inflow, buy_volume, sell_volume):
                self.trade_date = trade_date
                self.total_net_inflow = total_net_inflow
                self.buy_volume = buy_volume
                self.sell_volume = sell_volume
                self.hk_exchg_net_buy = total_net_inflow * 0.5
                self.sh_exchg_net_buy = total_net_inflow * 0.3
                self.sz_exchg_net_buy = total_net_inflow * 0.2

        return NorthboundFlow(trade_date, 15.0, 500.0, 485.0)


__all__ = ["ChinaDataGuiEngine"]
