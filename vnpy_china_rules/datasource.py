"""
数据源管理层

提供统一的数据源接口，支持QMT、Tushare等多数据源，
实现数据源管理和降级机制。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Union
from functools import lru_cache

from loguru import logger

from vnpy.trader.object import TickData, BarData, ContractData
from vnpy.trader.constant import Exchange
from vnpy.trader.engine import MainEngine


try:
    import tushare as ts
except ImportError:
    ts = None  # type: ignore


@dataclass
class StockInfo:
    """
    股票信息数据类

    Attributes
    ----------
    symbol : str
        股票代码
    exchange : Exchange
        交易所
    name : str
        股票名称
    market_type : str
        市场类型：主板/创业板/科创板/北交所
    is_st : bool
        是否ST股票
    list_date : str
        上市日期 (YYYYMMDD格式)
    limit_ratio : float
        涨跌停比例
    """
    symbol: str
    exchange: Exchange
    name: str
    market_type: str
    is_st: bool
    list_date: str
    limit_ratio: float


class DataSource(ABC):
    """
    数据源抽象基类

    所有数据源必须实现此类的方法。
    """

    @abstractmethod
    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        获取股票基本信息

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[StockInfo]
            股票信息对象，如果获取失败返回None
        """
        pass

    @abstractmethod
    def get_market_data(self, symbol: str) -> Union[TickData, BarData, None]:
        """
        获取行情数据

        不同数据源可能返回不同类型的行情数据：
        - QMTDataSource返回实时TickData
        - TushareDataSource返回历史BarData（日线）

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Union[TickData, BarData, None]
            行情数据对象，如果获取失败返回None
        """
        pass


class QMTDataSource(DataSource):
    """
    QMT数据源

    从QMT网关获取实时行情数据。

    涨跌停比例常量：
    - LIMIT_RATIO_MAIN: 主板 10%
    - LIMIT_RATIO_SME: 创业板 20%
    - LIMIT_RATIO_SCI: 科创板 20%
    - LIMIT_RATIO_BSE: 北交所 30%
    - LIMIT_RATIO_ST: ST股票 5%
    """

    # 涨跌停比例常量
    LIMIT_RATIO_MAIN = 0.10      # 主板10%
    LIMIT_RATIO_SME = 0.20       # 创业板20%
    LIMIT_RATIO_SCI = 0.20       # 科创板20%
    LIMIT_RATIO_BSE = 0.30       # 北交所30%
    LIMIT_RATIO_ST = 0.05        # ST股票5%

    def __init__(self, main_engine: MainEngine) -> None:
        """
        初始化QMT数据源

        Parameters
        ----------
        main_engine : MainEngine
            VeighNa主引擎实例

        Raises
        ------
        TypeError
            如果传入的不是MainEngine实例
        """
        if not isinstance(main_engine, MainEngine):
            raise TypeError(
                f"QMTDataSource需要MainEngine实例，"
                f"收到: {type(main_engine).__name__}"
            )

        self.main_engine = main_engine
        # 获取第一个网关名称作为数据源标识
        if main_engine.gateways:
            self.gateway_name: str = list(main_engine.gateways.keys())[0]
        else:
            self.gateway_name = "QMT"

        logger.info(f"QMT数据源初始化成功，使用网关: {self.gateway_name}")

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        从QMT网关获取股票信息

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[StockInfo]
            股票信息对象，如果获取失败返回None
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"无效的股票代码: {symbol}")
            return None

        try:
            # 从主引擎获取合约信息
            contract: Optional[ContractData] = self.main_engine.get_contract(symbol)

            if contract is None:
                logger.info(f"QMT数据源未找到股票{symbol}的合约信息")
                return None

            # 解析市场类型和涨跌停比例
            exchange: Exchange = contract.exchange
            market_type, limit_ratio = self._parse_market_info(exchange, contract.symbol)

            # 判断是否为ST股票
            name: str = contract.name
            is_st: bool = self._is_st_stock(name)

            # ST股票涨跌停比例为5%
            if is_st:
                limit_ratio = self.LIMIT_RATIO_ST

            stock_info = StockInfo(
                symbol=contract.symbol,
                exchange=exchange,
                name=name,
                market_type=market_type,
                is_st=is_st,
                list_date="",  # QMT网关可能不提供此信息
                limit_ratio=limit_ratio
            )

            logger.debug(f"QMT数据源获取股票{symbol}信息成功")
            return stock_info

        except Exception as e:
            logger.error(f"QMT数据源获取股票{symbol}信息失败: {e}")
            return None

    def get_market_data(self, symbol: str) -> Optional[TickData]:
        """
        从QMT网关获取实时行情

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[TickData]
            行情数据对象，如果获取失败返回None
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"无效的股票代码: {symbol}")
            return None

        try:
            # 从主引擎获取最新tick数据
            tick = self.main_engine.get_tick(symbol)

            if tick is None:
                logger.info(f"QMT数据源未找到股票{symbol}的行情数据")
                return None

            logger.debug(f"QMT数据源获取股票{symbol}行情成功")
            return tick

        except Exception as e:
            logger.error(f"QMT数据源获取股票{symbol}行情失败: {e}")
            return None

    def _parse_market_info(self, exchange: Exchange, symbol: str) -> tuple[str, float]:
        """
        根据交易所和股票代码解析市场类型和涨跌停比例

        Parameters
        ----------
        exchange : Exchange
            交易所枚举
        symbol : str
            股票代码

        Returns
        -------
        tuple[str, float]
            (市场类型, 涨跌停比例)
        """
        if exchange == Exchange.SSE:
            # 上海证券交易所
            # 688xxx为科创板，其他为主板
            if symbol.startswith('688'):
                return "科创板", self.LIMIT_RATIO_SCI
            return "主板", self.LIMIT_RATIO_MAIN
        elif exchange == Exchange.SZSE:
            # 深圳证券交易所
            # 300xxx为创业板，其他为主板
            if symbol.startswith('300'):
                return "创业板", self.LIMIT_RATIO_SME
            return "主板", self.LIMIT_RATIO_MAIN
        elif exchange == Exchange.BSE:
            # 北京证券交易所
            return "北交所", self.LIMIT_RATIO_BSE
        else:
            # 默认主板
            return "主板", self.LIMIT_RATIO_MAIN

    def _is_st_stock(self, name: str) -> bool:
        """
        判断是否为ST股票

        Parameters
        ----------
        name : str
            股票名称

        Returns
        -------
        bool
            是否为ST股票
        """
        # ST股票名称包含"ST"、"*ST"等标记
        st_prefixes = ["ST", "*ST", "S*ST", "SST"]
        name_upper = name.upper()

        for prefix in st_prefixes:
            if name_upper.startswith(prefix):
                return True

        return False


class TushareDataSource(DataSource):
    """
    Tushare数据源

    使用Tushare API获取离线补充数据。

    涨跌停比例常量：
    - LIMIT_RATIO_MAIN: 主板 10%
    - LIMIT_RATIO_SME: 创业板 20%
    - LIMIT_RATIO_SCI: 科创板 20%
    - LIMIT_RATIO_BSE: 北交所 30%
    """

    # 涨跌停比例常量
    LIMIT_RATIO_MAIN = 0.10      # 主板10%
    LIMIT_RATIO_SME = 0.20       # 创业板20%
    LIMIT_RATIO_SCI = 0.20       # 科创板20%
    LIMIT_RATIO_BSE = 0.30       # 北交所30%

    def __init__(self, token: str) -> None:
        """
        初始化Tushare数据源

        Parameters
        ----------
        token : str
            Tushare API token

        Raises
        ------
        ImportError
            如果未安装tushare库
        """
        if ts is None:
            raise ImportError(
                "未安装tushare库，请先安装: pip install tushare"
            )

        self.pro = ts.pro_api(token)
        self.token = token
        self.gateway_name: str = "TUSHARE"

        logger.info("Tushare数据源初始化成功")

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        从Tushare获取股票基本信息

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[StockInfo]
            股票信息对象，如果获取失败返回None
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"无效的股票代码: {symbol}")
            return None

        try:
            # 将股票代码转换为Tushare格式 (000001 -> 000001.SZ)
            ts_symbol = self._convert_to_tushare_symbol(symbol)

            # 调用Tushare API
            df = self.pro.stock_basic(
                ts_code=ts_symbol,
                fields='ts_code,symbol,name,market,list_date'
            )

            if df is None or df.empty:
                logger.info(f"Tushare数据源未找到股票{symbol}的基本信息")
                return None

            # 解析数据
            row = df.iloc[0]

            # 根据ts_code判断交易所
            ts_code: str = row['ts_code']
            exchange = self._parse_exchange_from_tscode(ts_code)

            # 解析市场类型和涨跌停比例
            market: str = row['market']
            market_type, limit_ratio = self._parse_market_type(market)

            stock_info = StockInfo(
                symbol=row['symbol'],
                exchange=exchange,
                name=row['name'],
                market_type=market_type,
                is_st=False,  # stock_basic接口不提供ST信息
                list_date=row['list_date'],
                limit_ratio=limit_ratio
            )

            logger.debug(f"Tushare数据源获取股票{symbol}信息成功")
            return stock_info

        except Exception as e:
            logger.error(f"Tushare数据源获取股票{symbol}信息失败: {e}")
            return None

    def get_market_data(self, symbol: str) -> Optional[BarData]:
        """
        从Tushare获取历史行情（返回最新的日线数据）

        注意：此方法返回BarData（K线数据）而非TickData，
        这与QMTDataSource的返回类型不同。

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[BarData]
            K线数据对象，如果获取失败返回None
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"无效的股票代码: {symbol}")
            return None

        try:
            # 将股票代码转换为Tushare格式
            ts_symbol = self._convert_to_tushare_symbol(symbol)

            # 调用Tushare API获取最新日线数据
            df = self.pro.daily(
                ts_code=ts_symbol,
                limit="1"
            )

            if df is None or df.empty:
                logger.info(f"Tushare数据源未找到股票{symbol}的历史数据")
                return None

            # 解析数据
            row = df.iloc[0]

            # 解析交易所
            exchange = self._parse_exchange_from_tscode(row['ts_code'])

            # 创建BarData对象
            bar = BarData(
                gateway_name="TUSHARE",
                symbol=row['ts_code'].split('.')[0],
                exchange=exchange,
                datetime=datetime.strptime(str(row['trade_date']), "%Y%m%d"),
                interval=None,
                volume=float(row['vol']),
                turnover=float(row['amount']),
                open_price=float(row['open']),
                high_price=float(row['high']),
                low_price=float(row['low']),
                close_price=float(row['close'])
            )

            logger.debug(f"Tushare数据源获取股票{symbol}行情成功")
            return bar

        except Exception as e:
            logger.error(f"Tushare数据源获取股票{symbol}行情失败: {e}")
            return None

    def _convert_to_tushare_symbol(self, symbol: str) -> str:
        """
        将股票代码转换为Tushare格式

        Parameters
        ----------
        symbol : str
            股票代码 (如: 000001)

        Returns
        -------
        str
            Tushare格式的股票代码 (如: 000001.SZ)
        """
        # 简单判断：6位数字
        if len(symbol) == 6 and symbol.isdigit():
            # 上海证券交易所：600xxx, 601xxx, 603xxx, 605xxx, 688xxx(科创板)
            if symbol.startswith('6'):
                return f"{symbol}.SH"
            # 深圳证券交易所：000xxx(主板), 001xxx, 002xxx(创业板), 300xxx(创业板)
            elif symbol.startswith('0') or symbol.startswith('3'):
                return f"{symbol}.SZ"
            # 北京证券交易所：43xxxx, 83xxxx, 87xxxx
            elif symbol.startswith(('4', '8')):
                return f"{symbol}.BJ"

        # 如果已经是Tushare格式，直接返回
        if '.' in symbol:
            return symbol

        # 默认假设为深圳
        return f"{symbol}.SZ"

    def _parse_exchange_from_tscode(self, ts_code: str) -> Exchange:
        """
        从Tushare代码解析交易所

        Parameters
        ----------
        ts_code : str
            Tushare格式的股票代码

        Returns
        -------
        Exchange
            交易所枚举
        """
        suffix = ts_code.split('.')[-1].upper()

        if suffix == 'SH':
            return Exchange.SSE
        elif suffix == 'SZ':
            return Exchange.SZSE
        elif suffix == 'BJ':
            return Exchange.BSE
        else:
            return Exchange.SZSE  # 默认深圳

    def _parse_market_type(self, market: str) -> tuple[str, float]:
        """
        解析市场类型和涨跌停比例

        Parameters
        ----------
        market : str
            Tushare市场标识

        Returns
        -------
        tuple[str, float]
            (市场类型, 涨跌停比例)
        """
        # Tushare市场标识：
        # 主板：主板
        # 创业板：创业板
        # 科创板：科创板
        # 北交所：北交所

        market_upper = market.upper()

        if '科创' in market:
            return "科创板", self.LIMIT_RATIO_SCI
        elif '创业' in market:
            return "创业板", self.LIMIT_RATIO_SME
        elif '北交' in market:
            return "北交所", self.LIMIT_RATIO_BSE
        else:
            return "主板", self.LIMIT_RATIO_MAIN


class DataSourceManager:
    """
    数据源管理器

    管理多个数据源，实现数据源优先级和降级机制。
    """

    def __init__(self) -> None:
        """初始化数据源管理器"""
        self.sources: Dict[str, DataSource] = {}
        self.primary_source: Optional[str] = None

        logger.info("数据源管理器初始化成功")

    def register_source(
        self,
        name: str,
        source: DataSource,
        primary: bool = False
    ) -> None:
        """
        注册数据源

        Parameters
        ----------
        name : str
            数据源名称
        source : DataSource
            数据源对象
        primary : bool, default False
            是否为主数据源
        """
        self.sources[name] = source

        if primary:
            self.primary_source = name
            logger.info(f"注册主数据源: {name}")
        else:
            logger.info(f"注册数据源: {name}")

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        获取股票信息

        优先从主数据源获取，失败则降级到其他数据源。

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[StockInfo]
            股票信息对象，如果所有数据源都失败返回None
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"无效的股票代码: {symbol}")
            return None

        # 如果没有注册任何数据源，直接返回None
        if not self.sources:
            logger.warning("未注册任何数据源")
            return None

        # 获取数据源优先级列表
        source_order = self._get_source_order()

        # 按优先级尝试获取数据
        for source_name in source_order:
            source = self.sources[source_name]

            try:
                result = source.get_stock_info(symbol)
                if result is not None:
                    logger.debug(
                        f"从数据源{source_name}获取股票{symbol}信息成功"
                    )
                    return result
            except Exception as e:
                logger.error(
                    f"从数据源{source_name}获取股票{symbol}信息异常: {e}"
                )
                continue

        logger.warning(f"所有数据源都未能获取股票{symbol}的信息")
        return None

    def get_market_data(self, symbol: str) -> Union[TickData, BarData, None]:
        """
        获取行情数据

        优先从主数据源获取，失败则降级到其他数据源。
        注意：不同数据源可能返回不同类型的数据。

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Union[TickData, BarData, None]
            行情数据对象，如果所有数据源都失败返回None
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"无效的股票代码: {symbol}")
            return None

        # 如果没有注册任何数据源，直接返回None
        if not self.sources:
            logger.warning("未注册任何数据源")
            return None

        # 获取数据源优先级列表
        source_order = self._get_source_order()

        # 按优先级尝试获取数据
        for source_name in source_order:
            source = self.sources[source_name]

            try:
                result = source.get_market_data(symbol)
                if result is not None:
                    logger.debug(
                        f"从数据源{source_name}获取股票{symbol}行情成功"
                    )
                    return result
            except Exception as e:
                logger.error(
                    f"从数据源{source_name}获取股票{symbol}行情异常: {e}"
                )
                continue

        logger.warning(f"所有数据源都未能获取股票{symbol}的行情")
        return None

    def _get_source_order(self) -> list[str]:
        """
        获取数据源优先级列表

        Returns
        -------
        list[str]
            数据源名称列表，主数据源排在最前
        """
        if self.primary_source and self.primary_source in self.sources:
            # 主数据源优先，然后是其他数据源
            order = [self.primary_source]
            order.extend([
                name for name in self.sources.keys()
                if name != self.primary_source
            ])
            return order
        else:
            # 没有设置主数据源，按注册顺序
            return list(self.sources.keys())

    @lru_cache(maxsize=128)
    def get_cached_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        获取缓存的股票信息

        使用LRU缓存，减少重复查询。

        Parameters
        ----------
        symbol : str
            股票代码

        Returns
        -------
        Optional[StockInfo]
            股票信息对象
        """
        return self.get_stock_info(symbol)

    def clear_cache(self) -> None:
        """清除股票信息缓存"""
        self.get_cached_stock_info.cache_clear()
        logger.info("已清除股票信息缓存")
