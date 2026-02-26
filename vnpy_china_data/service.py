"""
A股数据服务主类

实现IDataProvider及相关的龙虎榜、北向资金、板块数据接口。
整合QMT实时数据和Tushare离线数据。
"""

from typing import List, Optional, Dict
from datetime import datetime, date
from threading import Lock
from pathlib import Path

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

from vnpy_china_interface import (
    IDataProvider,
    IDragonTigerProvider,
    INorthboundProvider,
    ISectorProvider,
    DragonTigerData as InterfaceDragonTigerData,
    NorthboundFlowData as InterfaceNorthboundFlowData,
    SectorData as InterfaceSectorData,
)
from vnpy_china_config import ConfigManager, DataModuleConfig

from .cache import DataQueryCache
from .database import MySQLDatabaseLayer
from .adapter import TushareDataAdapter, QMTDataAdapter, RpcQmtDataAdapter
from .models.dragon_tiger import DragonTigerData
from .models.northbound import NorthboundFlowData
from .models.sector import SectorData
from .models.money_flow import MoneyFlowData
from .config import data_config


class ChinaDataService(
    IDataProvider,
    IDragonTigerProvider,
    INorthboundProvider,
    ISectorProvider
):
    """A股数据服务主类

    实现多个数据接口：
    - IDataProvider: 基础行情数据
    - IDragonTigerProvider: 龙虎榜数据
    - INorthboundProvider: 北向资金数据
    - ISectorProvider: 板块数据

    数据查询优先级：缓存 -> 数据库 -> API
    """

    _instance: Optional["ChinaDataService"] = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        # 获取配置
        config_manager = ConfigManager()
        self.config: DataModuleConfig = config_manager.load_module_config("data", DataModuleConfig)
        self.global_config = config_manager.load_global_config()

        # 初始化组件
        self.cache = DataQueryCache(
            host=self.global_config.database.redis_host,
            port=self.global_config.database.redis_port,
            password=self.global_config.database.redis_password,
            default_ttl=data_config.DEFAULT_CACHE_TTL
        )

        self.database = MySQLDatabaseLayer(
            host=self.global_config.database.mysql_host,
            port=self.global_config.database.mysql_port,
            user=self.global_config.database.mysql_user,
            password=self.global_config.database.mysql_password,
            database=self.global_config.database.mysql_database
        )

        self.tushare_adapter = TushareDataAdapter(
            token=self.config.tushare_token,
            rate_limit=self.config.tushare_rate_limit
        )

        # 根据配置选择QMT适配器类型
        if self.config.qmt_use_rpc:
            # 使用RPC模式（Mac/Linux客户端）
            self.qmt_adapter = RpcQmtDataAdapter(
                req_address=self.config.qmt_rpc_req_address,
                sub_address=self.config.qmt_rpc_sub_address
            )
        else:
            # 使用直接模式（Windows本地）
            self.qmt_adapter = QMTDataAdapter(
                qmt_path=str(self.config.qmt_path),
                account_id=self.config.qmt_account_id
            )

        # 运行状态
        self._connected = False
        self._initialized = True

    def connect(self) -> bool:
        """连接数据源"""
        import logging
        logger = logging.getLogger("vnpy_china_data")

        try:
            # 连接MySQL
            if not self.database.connect():
                logger.warning("MySQL连接失败")

            # 连接Redis
            if not self.cache.connect():
                logger.warning("Redis连接失败")

            # 连接Tushare
            self.tushare_adapter.connect()

            # 连接QMT（可选）
            self.qmt_adapter.connect()

            self._connected = True
            return True

        except Exception as e:
            print(f"数据服务连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self.database.close()
        self.cache.close()
        self.qmt_adapter.disconnect()
        self.tushare_adapter.disconnect()
        self._connected = False

    @property
    def connected(self) -> bool:
        """连接状态"""
        return self._connected

    # ========== IDataProvider 接口实现 ==========

    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取K线数据

        查询优先级：缓存 -> 数据库 -> API
        """
        # 1. 尝试从缓存获取
        cache_key = f"bar_{symbol}_{exchange.value}_{interval.value}_{start.isoformat()}_{end.isoformat()}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return self._deserialize_bars(cached_data)

        # 2. 尝试从数据库获取
        db_data = self.database.load_bar_data(symbol, exchange, interval, start, end)
        if db_data:
            self.cache.set(cache_key, self._serialize_bars(db_data), ttl=data_config.BAR_CACHE_TTL)
            return db_data

        # 3. 从API获取并存储
        api_data = self._fetch_bars_from_api(symbol, exchange, interval, start, end)
        if api_data:
            self.database.save_bar_data(api_data)
            self.cache.set(cache_key, self._serialize_bars(api_data), ttl=data_config.BAR_CACHE_TTL)
        return api_data

    def download_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: date,
        end: date
    ) -> List[BarData]:
        """下载并存储历史K线数据

        这个方法会强制从API获取数据并存储到数据库，跳过缓存。
        专门用于历史数据批量下载功能。

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期
            start: 开始日期
            end: 结束日期

        Returns:
            下载的K线数据列表
        """
        # 转换为datetime
        start_datetime = datetime.combine(start, datetime.min.time())
        end_datetime = datetime.combine(end, datetime.max.time())

        # 直接从API获取
        api_data = self._fetch_bars_from_api(
            symbol, exchange, interval, start_datetime, end_datetime
        )

        # 存储到数据库
        if api_data:
            self.database.save_bar_data(api_data)

        return api_data

    def _fetch_bars_from_api(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """从API获取K线数据"""
        # 转换symbol为tushare格式
        ts_code = self._convert_to_ts_code(symbol, exchange)

        if interval in [Interval.MINUTE_1, Interval.MINUTE_5,
                       Interval.MINUTE_15, Interval.MINUTE_30]:
            # 分钟线：优先使用QMT
            if self.qmt_adapter.connected:
                return self.qmt_adapter.get_bar_data(symbol, exchange, interval, start, end)
            else:
                return self.tushare_adapter.get_bar_data(symbol, exchange, interval, start, end)
        else:
            # 日线及以上：使用Tushare
            return self.tushare_adapter.get_bar_data(symbol, exchange, interval, start, end)

    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """获取Tick数据

        Note: Tick数据只从QMT获取
        """
        if self.qmt_adapter.connected:
            return self.qmt_adapter.get_tick_data(symbol, exchange, start, end)
        return []

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """获取股票基本信息"""
        # 尝试从缓存获取
        cache_key = f"stock_info_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 从Tushare获取
        info = self.tushare_adapter.get_stock_info(symbol)
        if info:
            self.cache.set(cache_key, info, ttl=data_config.INFO_CACHE_TTL)
        return info

    def get_financial_data(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict]:
        """获取财务数据"""
        # 尝试从缓存获取
        cache_key = f"financial_{symbol}_{report_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 从Tushare获取
        ts_code = self._convert_to_ts_code(symbol, Exchange.SZSE)
        data = self.tushare_adapter.get_pro_bar(ts_code, report_date, report_date)
        if not data.empty:
            result = data.iloc[0].to_dict()
            self.cache.set(cache_key, result, ttl=data_config.INFO_CACHE_TTL)
            return result
        return None

    def subscribe_quote(self, symbols: List[str]) -> bool:
        """订阅实时行情"""
        return self.qmt_adapter.subscribe(symbols)

    # ========== IDragonTigerProvider 接口实现 ==========

    def get_dragon_tiger_data(
        self,
        trade_date: date
    ) -> List[InterfaceDragonTigerData]:
        """获取指定日期的龙虎榜数据"""
        # 尝试从缓存获取
        cache_key = f"dragon_tiger_{trade_date.isoformat()}"
        cached = self.cache.get(cache_key)
        if cached:
            return [DragonTigerData.from_dict(d) for d in cached]

        # 从Tushare获取
        trade_date_str = trade_date.strftime("%Y%m%d")
        data = self.tushare_adapter.get_dragon_tiger_data(trade_date_str)

        if data:
            # 缓存7天
            serialized = [d.to_dict() for d in data]
            self.cache.set(cache_key, serialized, ttl=7 * 86400)
            return data
        return []

    def get_institution_rank(
        self,
        trade_date: date,
        top_n: int = 10
    ) -> List[InterfaceDragonTigerData]:
        """获取机构排名"""
        data = self.get_dragon_tiger_data(trade_date)
        # 按机构净买入排序
        return sorted(data, key=lambda x: x.institution_net_buy, reverse=True)[:top_n]

    # ========== INorthboundProvider 接口实现 ==========

    def get_northbound_flow(
        self,
        trade_date: date
    ) -> Optional[InterfaceNorthboundFlowData]:
        """获取北向资金流向"""
        # 尝试从缓存获取
        cache_key = f"northbound_{trade_date.isoformat()}"
        cached = self.cache.get(cache_key)
        if cached:
            return NorthboundFlowData.from_dict(cached)

        # 从Tushare获取
        trade_date_str = trade_date.strftime("%Y%m%d")
        data = self.tushare_adapter.get_northbound_flow(trade_date_str)

        if data:
            # 缓存1天
            self.cache.set(cache_key, data.to_dict(), ttl=86400)
            return data
        return None

    def get_stock_holding_change(
        self,
        symbol: str,
        days: int = 5
    ) -> Dict[str, float]:
        """获取个股持股变化"""
        # 这里简化实现，实际需要调用专门的API
        return {}

    # ========== ISectorProvider 接口实现 ==========

    def get_sector_list(self) -> List[InterfaceSectorData]:
        """获取板块列表"""
        # 尝试从缓存获取
        cache_key = "sector_list"
        cached = self.cache.get(cache_key)
        if cached:
            return [SectorData.from_dict(d) for d in cached]

        # 从Tushare获取
        data = self.tushare_adapter.get_sector_list()

        if data:
            # 缓存1天
            serialized = [d.to_dict() for d in data]
            self.cache.set(cache_key, serialized, ttl=86400)
            return data
        return []

    def get_sector_stocks(self, sector_code: str) -> List[str]:
        """获取板块成分股"""
        # 简化实现
        return []

    def get_sector_index(
        self,
        sector_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取板块指数数据"""
        # 简化实现
        return []

    # ========== 资金流向数据 ==========

    def get_moneyflow(
        self,
        symbol: str = "",
        exchange: Exchange = Exchange.SZSE,
        trade_date: date = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[MoneyFlowData]:
        """获取个股资金流向数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            trade_date: 交易日期
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            资金流向数据列表
        """
        # 转换为Tushare格式
        ts_code = self._convert_to_ts_code(symbol, exchange) if symbol else ""

        # 格式化日期参数
        trade_date_str = trade_date.strftime("%Y%m%d") if trade_date else ""
        start_date_str = start_date.strftime("%Y%m%d") if start_date else ""
        end_date_str = end_date.strftime("%Y%m%d") if end_date else ""

        # 尝试从缓存获取
        cache_key = f"moneyflow_{ts_code}_{trade_date_str}_{start_date_str}_{end_date_str}"
        cached = self.cache.get(cache_key)
        if cached:
            return [MoneyFlowData(**d) for d in cached]

        # 从Tushare获取
        data = self.tushare_adapter.get_moneyflow(
            ts_code=ts_code,
            trade_date=trade_date_str,
            start_date=start_date_str,
            end_date=end_date_str
        )

        if data:
            # 缓存1天
            serialized = [
                {
                    "symbol": d.symbol,
                    "name": d.name,
                    "trade_date": d.trade_date.isoformat(),
                    "close_price": d.close_price,
                    "change_pct": d.change_pct,
                    "super_large_buy": d.super_large_buy,
                    "super_large_sell": d.super_large_sell,
                    "large_buy": d.large_buy,
                    "large_sell": d.large_sell,
                    "medium_buy": d.medium_buy,
                    "medium_sell": d.medium_sell,
                    "small_buy": d.small_buy,
                    "small_sell": d.small_sell,
                    "super_large_buy_amount": d.super_large_buy_amount,
                    "super_large_sell_amount": d.super_large_sell_amount,
                    "large_buy_amount": d.large_buy_amount,
                    "large_sell_amount": d.large_sell_amount,
                    "medium_buy_amount": d.medium_buy_amount,
                    "medium_sell_amount": d.medium_sell_amount,
                    "small_buy_amount": d.small_buy_amount,
                    "small_sell_amount": d.small_sell_amount,
                }
                for d in data
            ]
            self.cache.set(cache_key, serialized, ttl=86400)
        return data

    # ========== 工具方法 ==========

    def _convert_to_ts_code(self, symbol: str, exchange: Exchange) -> str:
        """转换symbol为tushare格式"""
        suffix_map = {
            Exchange.SSE: "SH",
            Exchange.SZSE: "SZ",
            Exchange.BSE: "BJ"
        }
        suffix = suffix_map.get(exchange, "SZ")
        return f"{symbol}.{suffix}"

    def _convert_from_ts_code(self, ts_code: str) -> tuple:
        """从tushare格式转换为(symbol, exchange)"""
        if '.' not in ts_code:
            return ts_code, Exchange.SZSE

        symbol, suffix = ts_code.split(".")

        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE
        }
        exchange = exchange_map.get(suffix, Exchange.SZSE)

        return symbol, exchange

    def _serialize_bars(self, bars: List[BarData]) -> List[Dict]:
        """序列化K线数据"""
        return [
            {
                "symbol": bar.symbol,
                "exchange": bar.exchange.value,
                "interval": bar.interval.value,
                "datetime": bar.datetime.isoformat(),
                "open_price": bar.open_price,
                "high_price": bar.high_price,
                "low_price": bar.low_price,
                "close_price": bar.close_price,
                "volume": bar.volume,
                "turnover": getattr(bar, 'turnover', 0),
            }
            for bar in bars
        ]

    def _deserialize_bars(self, data: List[Dict]) -> List[BarData]:
        """反序列化K线数据"""
        bars = []
        for item in data:
            try:
                bar = BarData(
                    symbol=item["symbol"],
                    exchange=Exchange(item["exchange"]),
                    interval=Interval(item["interval"]),
                    datetime=datetime.fromisoformat(item["datetime"]),
                    open_price=item["open_price"],
                    high_price=item["high_price"],
                    low_price=item["low_price"],
                    close_price=item["close_price"],
                    volume=item["volume"],
                    turnover=item.get("turnover", 0)
                )
                bars.append(bar)
            except Exception:
                continue
        return bars


# 全局单例
_service_instance: Optional[ChinaDataService] = None


def get_data_service() -> ChinaDataService:
    """获取数据服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ChinaDataService()
    return _service_instance
