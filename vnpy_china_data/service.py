"""
A股数据服务主类

实现IDataProvider及相关的龙虎榜、北向资金、板块数据接口。
整合QMT实时数据和Tushare离线数据。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
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

        # 调试：打印配置加载信息
        import logging
        logger = logging.getLogger("vnpy_china_data")
        logger.info(f"ConfigManager配置路径: {config_manager.config_path.absolute()}")
        logger.info(f"MySQL用户: {self.global_config.database.mysql_user}")
        logger.info(f"MySQL密码长度: {len(self.global_config.database.mysql_password)}")

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

        # 根据配置选择QMT适配器类型（从全局配置读取）
        qmt_config = self.global_config.qmt
        if qmt_config.use_rpc:
            # 使用RPC模式（Mac/Linux客户端）
            self.qmt_adapter = RpcQmtDataAdapter(
                req_address=self.global_config.rpc.rep_address,
                sub_address=self.global_config.rpc.pub_address
            )
        else:
            # 使用直接模式（Windows本地）
            self.qmt_adapter = QMTDataAdapter(
                qmt_path=str(qmt_config.mini_path),
                account_id=qmt_config.account_id
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

            # 检查港股通名单是否需要更新
            if data_config.HK_CONNECT_AUTO_UPDATE:
                self._check_and_update_hk_connect_stocks()

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
        """从API获取K线数据

        优先使用 QMT（券商提供，数据更全），其次使用 Tushare。
        """
        # 转换symbol为tushare格式
        ts_code = self._convert_to_ts_code(symbol, exchange)

        if interval == Interval.MINUTE:
            # 分钟线：优先使用QMT
            if self.qmt_adapter and self.qmt_adapter.connected:
                try:
                    bars = self.qmt_adapter.get_bar_data(symbol, exchange, interval, start, end)
                    if bars:
                        return bars
                except Exception as e:
                    import logging
                    logger = logging.getLogger("vnpy_china_data")
                    logger.warning(f"QMT获取分钟线失败: {e}，尝试Tushare")

            # Fallback: Tushare (需要高级权限)
            bars = self.tushare_adapter.get_bar_data(symbol, exchange, interval, start, end)
            if bars:
                return bars

            import logging
            logger = logging.getLogger("vnpy_china_data")
            logger.warning(
                f"无法获取{ts_code}分钟线数据。"
                f"QMT未连接或Tushare需要高级权限。"
            )
            return []
        else:
            # 日线及以上：优先使用QMT，其次使用Tushare
            if self.qmt_adapter and self.qmt_adapter.connected:
                try:
                    bars = self.qmt_adapter.get_bar_data(symbol, exchange, interval, start, end)
                    if bars:
                        return bars
                except Exception as e:
                    import logging
                    logger = logging.getLogger("vnpy_china_data")
                    logger.warning(f"QMT获取日线失败: {e}，尝试Tushare")

            # Fallback: Tushare
            bars = self.tushare_adapter.get_bar_data(symbol, exchange, interval, start, end)
            if bars:
                return bars

            import logging
            logger = logging.getLogger("vnpy_china_data")
            logger.warning(
                f"无法获取{ts_code}数据。"
                f"QMT未连接或Tushare无数据。"
            )
            return []

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
        """获取指定日期的龙虎榜数据

        Note: 龙虎榜数据获取有限制：
        - Tushare 需要高级权限
        - QMT 暂不支持龙虎榜数据接口

        建议使用东方财富、同花顺等第三方数据源。
        """
        # 尝试从缓存获取
        cache_key = f"dragon_tiger_{trade_date.isoformat()}"
        cached = self.cache.get(cache_key)
        if cached:
            return [DragonTigerData.from_dict(d) for d in cached]

        # 从Tushare获取（需要高级权限）
        trade_date_str = trade_date.strftime("%Y%m%d")
        data = self.tushare_adapter.get_dragon_tiger_data(trade_date_str)

        if data:
            # 缓存7天
            serialized = [d.to_dict() for d in data]
            self.cache.set(cache_key, serialized, ttl=7 * 86400)
            return data

        # 如果没有数据，输出提示
        import logging
        logger = logging.getLogger("vnpy_china_data")
        logger.warning(
            f"未获取到 {trade_date_str} 的龙虎榜数据。"
            f"Tushare 需要高级权限访问龙虎榜数据，"
            f"建议使用东方财富、同花顺等第三方数据源。"
        )

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

        # 优先使用 QMT 适配器（无需特殊权限）
        if self.qmt_adapter:
            data = self.qmt_adapter.get_sector_list()
            if data:
                # 缓存1天
                serialized = [d.to_dict() for d in data]
                self.cache.set(cache_key, serialized, ttl=86400)
                return data

        # Fallback: 从Tushare获取
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
        """获取板块指数数据

        Args:
            sector_code: 板块代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            K线数据列表
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 优先使用 QMT 适配器
        if self.qmt_adapter and self.qmt_adapter.connected:
            try:
                data = self.qmt_adapter.get_sector_index(sector_code, start_date, end_date)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"QMT适配器获取板块指数失败: {e}，尝试其他方式...")

        # 如果QMT不可用，尝试从本地数据库获取
        try:
            data = self._get_sector_index_from_db(sector_code, start_date, end_date)
            if data:
                return data
        except Exception as e:
            logger.debug(f"数据库获取板块指数失败: {e}")

        logger.warning(
            f"无法获取板块指数数据: {sector_code}。"
            "RPC模式下需要Windows服务端支持get_sector_index函数，"
            "或提前通过本地QMT下载板块指数数据。"
        )
        return []

    def _get_sector_index_from_db(self, sector_code: str, start_date: str, end_date: str) -> List[BarData]:
        """从本地数据库获取板块指数数据"""
        # 简化实现 - 可以扩展为从MySQL获取历史数据
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

    # ========== 股票列表 ==========

    def get_stock_list(self, list_status: str = "L") -> List[Dict[str, Any]]:
        """获取股票列表

        Args:
            list_status: 上市状态 (L上市 D退市 P暂停上市)

        Returns:
            股票列表，每个股票包含 ts_code, symbol, name 等信息
        """
        # 尝试从缓存获取
        cache_key = f"stock_list_{list_status}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 从Tushare获取
        data = self.tushare_adapter.get_stock_list(list_status=list_status)

        if data:
            # 缓存1天
            self.cache.set(cache_key, data, ttl=86400)

        return data

    def update_hk_connect_stocks(self) -> Dict[str, Any]:
        """更新港股通股票名单

        从上交所和深交所网站爬取最新的港股通股票名单，
        并存储到数据库中。

        Returns:
            更新结果字典，包含 success, count, sh_count, sz_count 等

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> result = service.update_hk_connect_stocks()
            >>> print(f"更新成功：沪港通 {result['sh_count']} 只，深港通 {result['sz_count']} 只")
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        result = {
            "success": False,
            "count": 0,
            "sh_count": 0,
            "sz_count": 0,
            "error": None
        }

        try:
            # 确保港股通名单表存在
            if not self.database.create_hk_connect_table():
                result["error"] = "创建港股通名单表失败"
                return result

            # 爬取港股通股票名单
            from ..crawler import crawl_hk_connect_stocks
            stocks = crawl_hk_connect_stocks()

            if not stocks:
                result["error"] = "未爬取到港股通股票名单"
                return result

            # 保存到数据库
            if self.database.save_hk_connect_stocks(stocks):
                result["success"] = True
                result["count"] = len(stocks)
                result["sh_count"] = len([s for s in stocks if s.channel == "SHHK"])
                result["sz_count"] = len([s for s in stocks if s.channel == "SZHK"])

                logger.info(
                    f"港股通名单更新成功：总计 {result['count']} 只，"
                    f"沪港通 {result['sh_count']} 只，深港通 {result['sz_count']} 只"
                )
            else:
                result["error"] = "保存港股通名单到数据库失败"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"更新港股通名单失败: {e}")

        return result

    def _check_and_update_hk_connect_stocks(self) -> None:
        """检查并自动更新港股通名单

        在连接数据源后自动调用，检查港股通名单是否需要更新。
        如果数据过期或不存在，则自动更新。
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        try:
            # 获取更新信息
            update_info = self.database.get_hk_connect_update_info()

            if not update_info:
                logger.debug("无法获取港股通名单更新信息")
                return

            # 检查是否需要更新
            needs_update = (
                not update_info["exists"] or  # 数据不存在
                update_info["days_since_update"] >= data_config.HK_CONNECT_UPDATE_DAYS  # 数据过期
            )

            if needs_update:
                if data_config.HK_CONNECT_UPDATE_ON_START:
                    logger.info("港股通名单数据过期，正在自动更新...")
                    result = self.update_hk_connect_stocks()
                    if result["success"]:
                        logger.info(f"港股通名单自动更新成功：{result['count']} 只")
                    else:
                        logger.warning(f"港股通名单自动更新失败: {result.get('error')}")
                else:
                    logger.warning(
                        f"港股通名单已过期（{update_info['days_since_update']} 天），"
                        f"请手动更新：调用 update_hk_connect_stocks() 方法"
                    )
            else:
                logger.debug(
                    f"港股通名单数据正常（{update_info['days_since_update']} 天前更新），"
                    f"共 {update_info['total_count']} 只股票"
                )

        except Exception as e:
            logger.debug(f"检查港股通名单更新状态失败: {e}")

    def get_hk_connect_update_info(self) -> Optional[Dict[str, Any]]:
        """获取港股通名单更新信息

        提供给外部调用，用于显示更新状态或判断是否需要更新。

        Returns:
            更新信息字典，包含 last_updated, days_since_update, total_count 等

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> info = service.get_hk_connect_update_info()
            >>> if info['days_since_update'] > 7:
            ...     service.update_hk_connect_stocks()
        """
        return self.database.get_hk_connect_update_info()

    def get_hk_sh_symbols(self, date: str = None) -> List[str]:
        """获取沪港通标的股票列表

        优先从 QMT 获取，失败则从缓存读取，支持缓存机制（1天有效期）。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SHHK", "2318.SHHK"]）

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> symbols = service.get_hk_sh_symbols()
            >>> print(f"沪港通标的数量: {len(symbols)}")
            >>> print(symbols[:5])  # ['0700.SHHK', '09988.SHHK', ...]
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 格式化日期参数
        date_param = date
        if date is None:
            # 使用当前日期作为默认
            date_param = datetime.now().strftime("%Y%m%d")
        elif isinstance(date, datetime):
            # 如果传入的是 datetime 对象，转换为字符串
            date_param = date.strftime("%Y%m%d")
        elif hasattr(date, 'strftime'):
            # 如果传入的是 date 对象，转换为字符串
            date_param = date.strftime("%Y%m%d")

        # 尝试从缓存获取
        cache_key = f"hk_sh_symbols_{date_param}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"从缓存获取沪港通标的列表: {len(cached)} 只")
            return cached

        # 优先使用 QMT 适配器
        if self.qmt_adapter and self.qmt_adapter.connected:
            try:
                data = self.qmt_adapter.get_hk_sh_symbols(date=date_param)
                if data:
                    # 缓存1天
                    self.cache.set(cache_key, data, ttl=86400)
                    logger.info(f"从 QMT 获取沪港通标的列表: {len(data)} 只")
                    return data
            except Exception as e:
                logger.warning(f"QMT 获取沪港通标的列表失败: {e}")

        # Fallback: 从Tushare获取（如果有的话）
        try:
            data = self.tushare_adapter.get_hk_sh_symbols(date=date_param)
            if data:
                # 缓存1天
                self.cache.set(cache_key, data, ttl=86400)
                logger.info(f"从 Tushare 获取沪港通标的列表: {len(data)} 只")
                return data
        except Exception as e:
            logger.warning(f"Tushare 获取沪港通标的列表失败: {e}")

        logger.warning("无法获取沪港通标的列表")
        return []

    def get_hk_sz_symbols(self, date: str = None) -> List[str]:
        """获取深港通标的股票列表

        优先从 QMT 获取，失败则从缓存读取，支持缓存机制（1天有效期）。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SZHK", "2318.SZHK"]）

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> symbols = service.get_hk_sz_symbols()
            >>> print(f"深港通标的数量: {len(symbols)}")
            >>> print(symbols[:5])  # ['0700.SZHK', '09988.SZHK', ...]
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 格式化日期参数
        date_param = date
        if date is None:
            # 使用当前日期作为默认
            date_param = datetime.now().strftime("%Y%m%d")
        elif isinstance(date, datetime):
            # 如果传入的是 datetime 对象，转换为字符串
            date_param = date.strftime("%Y%m%d")
        elif hasattr(date, 'strftime'):
            # 如果传入的是 date 对象，转换为字符串
            date_param = date.strftime("%Y%m%d")

        # 尝试从缓存获取
        cache_key = f"hk_sz_symbols_{date_param}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"从缓存获取深港通标的列表: {len(cached)} 只")
            return cached

        # 优先使用 QMT 适配器
        if self.qmt_adapter and self.qmt_adapter.connected:
            try:
                data = self.qmt_adapter.get_hk_sz_symbols(date=date_param)
                if data:
                    # 缓存1天
                    self.cache.set(cache_key, data, ttl=86400)
                    logger.info(f"从 QMT 获取深港通标的列表: {len(data)} 只")
                    return data
            except Exception as e:
                logger.warning(f"QMT 获取深港通标的列表失败: {e}")

        # Fallback: 从Tushare获取（如果有的话）
        try:
            data = self.tushare_adapter.get_hk_sz_symbols(date=date_param)
            if data:
                # 缓存1天
                self.cache.set(cache_key, data, ttl=86400)
                logger.info(f"从 Tushare 获取深港通标的列表: {len(data)} 只")
                return data
        except Exception as e:
            logger.warning(f"Tushare 获取深港通标的列表失败: {e}")

        logger.warning("无法获取深港通标的列表")
        return []

    def get_hk_all_symbols(self, date: str = None) -> List[str]:
        """合并获取所有港股通标的

        合并沪港通和深港通的标的列表，去重后返回。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SHHK", "2318.SZHK", ...]）

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> symbols = service.get_hk_all_symbols()
            >>> print(f"港股通标的总数: {len(symbols)}")
            >>> # 统计沪港通和深港通数量
            >>> sh_count = sum(1 for s in symbols if s.endswith('.SHHK'))
            >>> sz_count = sum(1 for s in symbols if s.endswith('.SZHK'))
            >>> print(f"沪港通: {sh_count}, 深港通: {sz_count}")
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 获取沪港通和深港通标的
        sh_symbols = self.get_hk_sh_symbols(date)
        sz_symbols = self.get_hk_sz_symbols(date)

        # 合并去重
        all_symbols = list(set(sh_symbols + sz_symbols))

        logger.info(f"港股通标的总数: {len(all_symbols)} (沪港通: {len(sh_symbols)}, 深港通: {len(sz_symbols)})")

        return all_symbols

    def get_hk_stock_list(self, hk_type: str, date: str = None) -> List[dict]:
        """获取港股通标的股票列表（桥接方法）

        根据港股通类型返回对应标的列表，返回格式兼容 GUI 引擎。

        Args:
            hk_type: 港股通类型 ("HK_SH"/"HK_SZ"/"HK_ALL")
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            字典列表，每个字典包含 ts_code 字段：[{"ts_code": "0700.HK"}, ...]

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> # 沪港通
            >>> sh_list = service.get_hk_stock_list("HK_SH")
            >>> # 深港通
            >>> sz_list = service.get_hk_stock_list("HK_SZ")
            >>> # 全部港股通
            >>> all_list = service.get_hk_stock_list("HK_ALL")
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 根据 hk_type 调用对应方法
        if hk_type == "HK_SH":
            symbols = self.get_hk_sh_symbols(date)
        elif hk_type == "HK_SZ":
            symbols = self.get_hk_sz_symbols(date)
        elif hk_type == "HK_ALL":
            symbols = self.get_hk_all_symbols(date)
        else:
            logger.warning(f"不支持的港股通类型: {hk_type}")
            return []

        # 转换为字典列表格式（兼容 GUI 引擎）
        # 保留原始后缀 (.SHHK/.SZHK)，以便 GUI 引擎正确解析交易所
        result = [{"ts_code": symbol} for symbol in symbols]

        logger.info(f"获取 {hk_type} 港股通标的: {len(result)} 只")
        return result

    # ========== 港股通交易日历 ==========
    def _get_hk_sh_trading_calendar(self, start_date: str = None, end_date: str = None) -> set:
        """获取沪港通交易日历（内地交易日 ∩ 香港交易日）

        Args:
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）

        Returns:
            沪港通交易日期集合（格式：YYYYMMDD）
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 默认获取最近一年的交易日历
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        # 尝试从缓存获取
        cache_key = f"hk_sh_calendar_{start_date}_{end_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return set(cached)

        try:
            # 获取内地交易日历
            cn_calendar = self.tushare_adapter.get_trade_calendar(
                exchange="SSE",
                start_date=start_date,
                end_date=end_date
            )
            cn_dates = set(cn_calendar)

            # 获取香港交易日历
            hk_calendar = self.tushare_adapter.get_hk_trade_calendar(
                start_date=start_date,
                end_date=end_date
            )
            hk_dates = set(hk_calendar)

            # 计算交集（两地都开市的日期）
            sh_calendar = cn_dates & hk_dates

            # 缓存30天
            self.cache.set(cache_key, list(sh_calendar), ttl=30 * 86400)
            logger.info(f"获取沪港通交易日历: {len(sh_calendar)} 个交易日")

            return sh_calendar

        except Exception as e:
            logger.warning(f"获取沪港通交易日历失败: {e}")
            return set()

    def _get_hk_sz_trading_calendar(self, start_date: str = None, end_date: str = None) -> set:
        """获取深港通交易日历（内地交易日 ∩ 香港交易日）

        Args:
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）

        Returns:
            深港通交易日期集合（格式：YYYYMMDD）
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 默认获取最近一年的交易日历
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        # 尝试从缓存获取
        cache_key = f"hk_sz_calendar_{start_date}_{end_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return set(cached)

        try:
            # 获取内地交易日历
            cn_calendar = self.tushare_adapter.get_trade_calendar(
                exchange="SZSE",
                start_date=start_date,
                end_date=end_date
            )
            cn_dates = set(cn_calendar)

            # 获取香港交易日历
            hk_calendar = self.tushare_adapter.get_hk_trade_calendar(
                start_date=start_date,
                end_date=end_date
            )
            hk_dates = set(hk_calendar)

            # 计算交集（两地都开市的日期）
            sz_calendar = cn_dates & hk_dates

            # 缓存30天
            self.cache.set(cache_key, list(sz_calendar), ttl=30 * 86400)
            logger.info(f"获取深港通交易日历: {len(sz_calendar)} 个交易日")

            return sz_calendar

        except Exception as e:
            logger.warning(f"获取深港通交易日历失败: {e}")
            return set()

    def is_hk_sh_trading_day(self, date_str: str) -> bool:
        """判断是否为沪港通交易日

        沪港通交易日 = A股交易日 ∩ 香港交易日

        Args:
            date_str: 日期字符串，格式可以是：
                      - "20260220" (YYYYMMDD)
                      - "2026-02-20" (YYYY-MM-DD)
                      - datetime.date 对象
                      - datetime.datetime 对象

        Returns:
            True: 是沪港通交易日
            False: 不是沪港通交易日

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> service.is_hk_sh_trading_day("20260220")
            True
            >>> service.is_hk_sh_trading_day(date(2026, 2, 20))
            True
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 格式化日期参数
        date_param = date_str
        if isinstance(date_str, datetime):
            date_param = date_str.strftime("%Y%m%d")
        elif isinstance(date_str, date):
            date_param = date_str.strftime("%Y%m%d")
        elif "-" in date_str:
            # 将 "2026-02-20" 转换为 "20260220"
            date_param = date_str.replace("-", "")

        # 获取沪港通交易日历（包含过去和未来3个月的日期）
        target_date = datetime.strptime(date_param, "%Y%m%d")
        start_date = (target_date - timedelta(days=90)).strftime("%Y%m%d")
        end_date = (target_date + timedelta(days=90)).strftime("%Y%m%d")

        calendar = self._get_hk_sh_trading_calendar(start_date, end_date)

        result = date_param in calendar
        logger.debug(f"日期 {date_param} 是否为沪港通交易日: {result}")
        return result

    def is_hk_sz_trading_day(self, date_str: str) -> bool:
        """判断是否为深港通交易日

        深港通交易日 = A股交易日 ∩ 香港交易日

        Args:
            date_str: 日期字符串，格式可以是：
                      - "20260220" (YYYYMMDD)
                      - "2026-02-20" (YYYY-MM-DD)
                      - datetime.date 对象
                      - datetime.datetime 对象

        Returns:
            True: 是深港通交易日
            False: 不是深港通交易日

        Examples:
            >>> service = ChinaDataService()
            >>> service.connect()
            >>> service.is_hk_sz_trading_day("20260220")
            True
            >>> service.is_hk_sz_trading_day(date(2026, 2, 20))
            True
        """
        import logging
        logger = logging.getLogger("vnpy_china_data")

        # 格式化日期参数
        date_param = date_str
        if isinstance(date_str, datetime):
            date_param = date_str.strftime("%Y%m%d")
        elif isinstance(date_str, date):
            date_param = date_str.strftime("%Y%m%d")
        elif "-" in date_str:
            # 将 "2026-02-20" 转换为 "20260220"
            date_param = date_str.replace("-", "")

        # 获取深港通交易日历（包含过去和未来3个月的日期）
        target_date = datetime.strptime(date_param, "%Y%m%d")
        start_date = (target_date - timedelta(days=90)).strftime("%Y%m%d")
        end_date = (target_date + timedelta(days=90)).strftime("%Y%m%d")

        calendar = self._get_hk_sz_trading_calendar(start_date, end_date)

        result = date_param in calendar
        logger.debug(f"日期 {date_param} 是否为深港通交易日: {result}")
        return result

    # ========== 工具方法 ==========

    def _convert_to_ts_code(self, symbol: str, exchange: Exchange) -> str:
        """转换symbol为tushare格式

        Args:
            symbol: 股票代码，可能包含或不包含交易所后缀（如 "000001" 或 "000001.SZ"）
            exchange: 交易所枚举

        Returns:
            tushare格式的股票代码（如 "000001.SZ"）

        Note:
            如果symbol已包含交易所后缀，会先去除后再添加正确的后缀
            港股通交易所 (SHHK/SZHK/SEHK) 都映射为 "HK"
        """
        suffix_map = {
            Exchange.SSE: "SH",
            Exchange.SZSE: "SZ",
            Exchange.BSE: "BJ",
            # 港股通交易所映射
            Exchange.SHHK: "HK",
            Exchange.SZHK: "HK",
            Exchange.SEHK: "HK",
        }
        suffix = suffix_map.get(exchange, "SZ")

        # 如果symbol已包含交易所后缀，先去除
        if '.' in symbol:
            symbol = symbol.split('.')[0]

        return f"{symbol}.{suffix}"

    def _convert_from_ts_code(self, ts_code: str) -> tuple:
        """从tushare格式转换为(symbol, exchange)

        Note:
            对于 "HK" 后缀，默认映射到 Exchange.SEHK
            (港股通的实际交易所需要根据业务逻辑判断)
        """
        if '.' not in ts_code:
            return ts_code, Exchange.SZSE

        symbol, suffix = ts_code.split(".")

        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE,
            # HK后缀默认映射到SEHK (港股通)
            "HK": Exchange.SEHK
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
