"""
QMT数据适配器

实现QMT证券客户端的数据获取和实时行情订阅功能。
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, date
from threading import Thread, Event, Lock
from collections import defaultdict

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.event import EventEngine

from .base import BaseDataAdapter


class QMTDataAdapter(BaseDataAdapter):
    """QMT数据适配器

    封装QMT证券客户端API，提供：
    - 实时行情订阅
    - Tick数据获取
    - 实时K线生成
    - 申万行业板块数据
    - 板块成分股查询
    """

    def __init__(
        self,
        qmt_path: str = "",
        account_id: str = "",
        event_engine: Optional[EventEngine] = None,
    ):
        """初始化QMT适配器

        Args:
            qmt_path: QMT Mini路径
            account_id: 账户ID
            event_engine: 事件引擎（用于发布行情事件）
        """
        super().__init__()
        self.qmt_path = qmt_path
        self.account_id = account_id
        self.event_engine = event_engine

        # QMT API对象（动态导入）
        self._qmt_api = None
        self._session_id: Optional[int] = None

        # 订阅管理
        self._subscribed_symbols: set = set()
        self._symbol_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # Tick数据缓存
        self._tick_cache: Dict[str, TickData] = {}

        # 实时K线生成器
        self._bar_generators: Dict[str, "RealtimeBarGenerator"] = {}

        # 运行控制
        self._stop_event = Event()
        self._reconnect_thread: Optional[Thread] = None
        self._reconnect_interval = 30

        # 统计信息
        self._tick_count = 0
        self._last_tick_time: Optional[datetime] = None
        self._lock = Lock()

    def connect(self) -> bool:
        """连接QMT"""
        try:
            # 尝试导入xtquant
            try:
                from xtquant import xtquant
                from xtquant.xttype import Stock
                self._qmt_api = xtquant
            except ImportError:
                print("警告: 未安装xtquant库，QMT适配器无法使用")
                return False

            # 尝试连接
            if self.qmt_path and self._qmt_api:
                # 创建session
                self._session_id = 1
                # 注意：实际连接需要QMT客户端运行
                self._connected = True
                return True

            return False

        except Exception as e:
            print(f"QMT连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开QMT连接"""
        self._stop_event.set()

        # 停止重连线程
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=5)

        # 取消所有订阅
        if self._subscribed_symbols:
            self.unsubscribe(list(self._subscribed_symbols))

        # 清理状态
        self._subscribed_symbols.clear()
        self._tick_cache.clear()
        self._bar_generators.clear()
        self._connected = False

    def _start_reconnect_thread(self) -> None:
        """启动重连线程"""
        self._stop_event = Event()
        self._reconnect_thread = Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        """重连循环"""
        while not self._stop_event.is_set():
            if not self._connected:
                self.connect()
            self._stop_event.wait(self._reconnect_interval)

    # ========== 行情数据实现 ==========

    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取K线数据

        使用 miniQMT 的两步下载流程：
        1. 调用 download_history_data2 异步下载数据到本地
        2. 等待下载完成
        3. 使用 get_local_data 读取本地数据

        Note: 建议在盘后时段使用，避免干扰实时数据
        """
        import time
        import logging

        logger = logging.getLogger("vnpy_china_data")

        if not self._connected:
            logger.debug("QMT未连接，无法获取历史数据")
            return []

        try:
            from xtquant import xtdata

            # 转换为QMT格式代码
            qmt_code = self._convert_to_qmt_code(symbol, exchange)
            if not qmt_code:
                logger.warning(f"无法转换股票代码: {symbol}.{exchange.value}")
                return []

            # 转换周期
            period = self._interval_to_period(interval)
            if not period:
                logger.warning(f"不支持的K线周期: {interval.value}")
                return []

            # 格式化时间
            start_time = start.strftime("%Y%m%d")
            end_time = end.strftime("%Y%m%d")

            logger.debug(f"QMT正在下载数据: {qmt_code}, period={period}, start={start_time}, end={end_time}")

            # 第1步：异步下载数据到本地
            if hasattr(xtdata, 'download_history_data2'):
                xtdata.download_history_data2(
                    stock_list=[qmt_code],
                    period=period,
                    start_time=start_time,
                    end_time=end_time
                )
                # 等待异步下载完成（建议2-5秒）
                time.sleep(3)
            else:
                logger.warning("xtdata不支持download_history_data2方法")
                return []

            # 第2步：读取本地数据
            if hasattr(xtdata, 'get_local_data'):
                data_list = xtdata.get_local_data(
                    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[qmt_code],
                    period=period,
                    start_time=start_time,
                    end_time=end_time
                )
            else:
                logger.warning("xtdata不支持get_local_data方法")
                return []

            # 第3步：转换为BarData列表
            bars: List[BarData] = []

            if data_list is None or len(data_list) == 0:
                logger.debug(f"QMT未获取到数据: {qmt_code}")
                return []

            # 处理DataFrame数据
            if hasattr(data_list, 'iterrows'):
                for _, row in data_list.iterrows():
                    bar = BarData(
                        gateway_name="QMT",
                        symbol=symbol,
                        exchange=exchange,
                        interval=interval,
                        datetime=self._parse_qmt_time(row.get('time')),
                        open_price=float(row.get('open', 0)),
                        high_price=float(row.get('high', 0)),
                        low_price=float(row.get('low', 0)),
                        close_price=float(row.get('close', 0)),
                        volume=float(row.get('volume', 0)),
                        turnover=float(row.get('amount', 0)),
                    )
                    bars.append(bar)

            logger.debug(f"QMT获取历史数据: {qmt_code}, 共{len(bars)}条")
            return bars

        except ImportError:
            logger.warning("xtdata模块未安装，无法获取QMT历史数据")
            return []
        except Exception as e:
            logger.warning(f"QMT获取历史数据失败: {e}")
            return []

    def _convert_to_qmt_code(self, symbol: str, exchange: Exchange) -> Optional[str]:
        """将VeighNa格式代码转换为QMT格式

        重要：港股通股票（SHHK/SZHK）统一转换为香港本地交易所（HK），
        因为港股通股票本身就是在香港联合交易所上市的。

        Args:
            symbol: 股票代码（不含交易所后缀）
            exchange: 交易所枚举

        Returns:
            QMT格式代码（如 "000001.SZ", "00700.HK"）

        Examples:
            >>> adapter._convert_to_qmt_code("000001", Exchange.SZSE)
            "000001.SZ"
            >>> adapter._convert_to_qmt_code("00700", Exchange.SHHK)
            "00700.HK"
            >>> adapter._convert_to_qmt_code("00700", Exchange.SEHK)
            "00700.HK"
        """
        # A股交易所映射
        exchange_suffix = {
            Exchange.SSE: "SH",
            Exchange.SZSE: "SZ",
        }

        # 港股（包括港股通）统一使用香港本地交易所
        if exchange in (Exchange.SEHK, Exchange.SHHK, Exchange.SZHK):
            return f"{symbol}.HK"

        # A股
        suffix = exchange_suffix.get(exchange)
        if suffix:
            return f"{symbol}.{suffix}"

        return None

    def _interval_to_period(self, interval: Interval) -> Optional[str]:
        """将VeighNa周期转换为QMT周期

        Args:
            interval: K线周期枚举

        Returns:
            QMT周期字符串（如 "1d", "1h", "1m"）

        Examples:
            >>> adapter._interval_to_period(Interval.DAILY)
            "1d"
            >>> adapter._interval_to_period(Interval.HOUR)
            "1h"
        """
        period_map = {
            Interval.MINUTE: "1m",
            Interval.HOUR: "1h",
            Interval.DAILY: "1d",
            Interval.WEEKLY: "1w",
        }
        return period_map.get(interval)

    def _parse_qmt_time(self, time_value) -> datetime:
        """解析QMT返回的时间值

        Args:
            time_value: 时间值（可能是字符串、时间戳等）

        Returns:
            datetime对象
        """
        if isinstance(time_value, datetime):
            return time_value
        elif isinstance(time_value, str):
            # 尝试多种格式
            formats = [
                "%Y%m%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y%m%d",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(time_value, fmt)
                except ValueError:
                    continue
            # 如果都失败，返回当前时间
            return datetime.now()
        else:
            return datetime.now()

    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """获取Tick数据"""
        # 返回缓存的Tick数据
        vt_symbol = f"{symbol}.{exchange.value}"
        tick = self._tick_cache.get(vt_symbol)

        if tick:
            return [tick]
        return []

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息

        Note: QMT不提供此功能，需要使用Tushare
        """
        return None

    # ========== 实时行情订阅 ==========

    def subscribe(self, symbols: List[str]) -> bool:
        """订阅实时行情

        支持沪港通和深港通实时行情订阅。

        Args:
            symbols: 股票代码列表（VeighNa格式，如 ["0700.SHHK", "2318.SZHK"]）

        Returns:
            订阅是否成功

        Examples:
            >>> adapter.subscribe(["0700.SHHK", "2318.SZHK"])  # 订阅港股通
            >>> adapter.subscribe(["000001.SZSE"])  # 订阅A股（暂不支持）
        """
        if not self._connected:
            return False

        try:
            # 分离港股通和A股代码
            hk_sh_symbols = []
            hk_sz_symbols = []

            for symbol in symbols:
                if symbol not in self._subscribed_symbols:
                    # 解析交易所
                    parts = symbol.rsplit(".", 1)
                    if len(parts) == 2:
                        code, exchange = parts
                        if exchange == "SHHK":
                            hk_sh_symbols.append(code)
                        elif exchange == "SZHK":
                            hk_sz_symbols.append(code)
                        else:
                            print(f"不支持的交易所: {exchange} (代码: {symbol})")
                            continue

                        # 添加到订阅集合
                        self._subscribed_symbols.add(symbol)

                        # 创建实时K线生成器
                        for interval in [Interval.MINUTE, Interval.MINUTE]:
                            key = f"{symbol}.{interval.value}"
                            if key not in self._bar_generators:
                                self._bar_generators[key] = RealtimeBarGenerator(
                                    symbol, interval, self._on_bar_generated
                                )

            # 调用港股通订阅方法
            if hk_sh_symbols:
                self.subscribe_hk_sh_quotes(hk_sh_symbols)

            if hk_sz_symbols:
                self.subscribe_hk_sz_quotes(hk_sz_symbols)

            return True

        except Exception as e:
            print(f"QMT订阅失败: {e}")
            return False

    def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅"""
        try:
            for symbol in symbols:
                if symbol in self._subscribed_symbols:
                    # 实际取消订阅逻辑
                    # self._qmt_api.unsubscribe_stock(symbol)
                    self._subscribed_symbols.discard(symbol)

            return True

        except Exception as e:
            print(f"QMT取消订阅失败: {e}")
            return False

    def subscribe_hk_sh_quotes(self, symbols: List[str]) -> bool:
        """订阅沪港通实时行情

        使用 QMT xtdata.subscribe_quote() API 订阅沪港通 Tick 行情。

        Args:
            symbols: 股票代码列表（不含交易所后缀，如 ["0700", "2318"]）

        Returns:
            订阅是否成功

        Examples:
            >>> adapter.subscribe_hk_sh_quotes(["0700", "2318", "09988"])
        """
        if not self._connected:
            print("QMT 未连接，无法订阅沪港通行情")
            return False

        if not symbols:
            return True

        try:
            from xtquant import xtdata

            # 转换为 QMT 格式（添加市场后缀）
            qmt_symbols = []
            for symbol in symbols:
                qmt_symbol = f"{symbol}.HK_SHTC"
                qmt_symbols.append(qmt_symbol)

            # 调用 QMT 订阅 API
            result = xtdata.subscribe_quote(
                stock_list=qmt_symbols,
                period="tick"  # 订阅 tick 级别数据
            )

            if result != 0:
                print(f"QMT 沪港通订阅失败，错误码: {result}")
                return False

            print(f"成功订阅 {len(symbols)} 只沪港通股票的实时行情")
            return True

        except ImportError:
            print("警告: xtdata 模块未安装，无法订阅沪港通行情")
            return False
        except Exception as e:
            print(f"QMT 沪港通订阅失败: {e}")
            return False

    def subscribe_hk_sz_quotes(self, symbols: List[str]) -> bool:
        """订阅深港通实时行情

        使用 QMT xtdata.subscribe_quote() API 订阅深港通 Tick 行情。

        Args:
            symbols: 股票代码列表（不含交易所后缀，如 ["0700", "2318"]）

        Returns:
            订阅是否成功

        Examples:
            >>> adapter.subscribe_hk_sz_quotes(["0700", "2318", "09988"])
        """
        if not self._connected:
            print("QMT 未连接，无法订阅深港通行情")
            return False

        if not symbols:
            return True

        try:
            from xtquant import xtdata

            # 转换为 QMT 格式（添加市场后缀）
            qmt_symbols = []
            for symbol in symbols:
                qmt_symbol = f"{symbol}.HK_SZTC"
                qmt_symbols.append(qmt_symbol)

            # 调用 QMT 订阅 API
            result = xtdata.subscribe_quote(
                stock_list=qmt_symbols,
                period="tick"  # 订阅 tick 级别数据
            )

            if result != 0:
                print(f"QMT 深港通订阅失败，错误码: {result}")
                return False

            print(f"成功订阅 {len(symbols)} 只深港通股票的实时行情")
            return True

        except ImportError:
            print("警告: xtdata 模块未安装，无法订阅深港通行情")
            return False
        except Exception as e:
            print(f"QMT 深港通订阅失败: {e}")
            return False

    def unsubscribe_hk_sh_quotes(self, symbols: List[str]) -> bool:
        """取消沪港通实时行情订阅

        Args:
            symbols: 股票代码列表（不含交易所后缀，如 ["0700", "2318"]）

        Returns:
            取消订阅是否成功

        Examples:
            >>> adapter.unsubscribe_hk_sh_quotes(["0700", "2318"])
        """
        if not self._connected:
            print("QMT 未连接，无法取消沪港通订阅")
            return False

        if not symbols:
            return True

        try:
            from xtquant import xtdata

            # 转换为 QMT 格式
            qmt_symbols = []
            for symbol in symbols:
                qmt_symbol = f"{symbol}.HK_SHTC"
                qmt_symbols.append(qmt_symbol)

            # 调用 QMT 取消订阅 API
            result = xtdata.unsubscribe_quote(qmt_symbols)

            if result != 0:
                print(f"QMT 沪港通取消订阅失败，错误码: {result}")
                return False

            print(f"成功取消 {len(symbols)} 只沪港通股票的订阅")
            return True

        except ImportError:
            print("警告: xtdata 模块未安装，无法取消沪港通订阅")
            return False
        except Exception as e:
            print(f"QMT 沪港通取消订阅失败: {e}")
            return False

    def unsubscribe_hk_sz_quotes(self, symbols: List[str]) -> bool:
        """取消深港通实时行情订阅

        Args:
            symbols: 股票代码列表（不含交易所后缀，如 ["0700", "2318"]）

        Returns:
            取消订阅是否成功

        Examples:
            >>> adapter.unsubscribe_hk_sz_quotes(["0700", "2318"])
        """
        if not self._connected:
            print("QMT 未连接，无法取消深港通订阅")
            return False

        if not symbols:
            return True

        try:
            from xtquant import xtdata

            # 转换为 QMT 格式
            qmt_symbols = []
            for symbol in symbols:
                qmt_symbol = f"{symbol}.HK_SZTC"
                qmt_symbols.append(qmt_symbol)

            # 调用 QMT 取消订阅 API
            result = xtdata.unsubscribe_quote(qmt_symbols)

            if result != 0:
                print(f"QMT 深港通取消订阅失败，错误码: {result}")
                return False

            print(f"成功取消 {len(symbols)} 只深港通股票的订阅")
            return True

        except ImportError:
            print("警告: xtdata 模块未安装，无法取消深港通订阅")
            return False
        except Exception as e:
            print(f"QMT 深港通取消订阅失败: {e}")
            return False

    def register_callback(
        self,
        symbol: str,
        callback: Callable[[TickData], None]
    ) -> None:
        """注册Tick回调"""
        self._symbol_callbacks[symbol].append(callback)

    def _on_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        with self._lock:
            # 更新缓存
            self._tick_cache[tick.vt_symbol] = tick
            self._tick_count += 1
            self._last_tick_time = datetime.now()

            # 更新K线生成器
            for generator in self._bar_generators.values():
                if tick.symbol in generator.symbol:
                    generator.update_tick(tick)

            # 执行回调
            callbacks = self._symbol_callbacks.get(tick.symbol, [])
            for callback in callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    print(f"回调执行失败: {e}")

            # 发布事件
            if self.event_engine:
                self.event_engine.put(tick)

    def _on_bar_generated(self, bar: BarData) -> None:
        """K线生成回调"""
        if self.event_engine:
            self.event_engine.put(bar)

    def _exchange_to_market(self, exchange: Exchange) -> Optional[str]:
        """将交易所转换为市场标识符

        Args:
            exchange: 交易所枚举

        Returns:
            市场标识符字符串
        """
        # 香港交易所映射
        if exchange == Exchange.SHHK:
            return "HK_SHTC"  # 沪港通
        elif exchange == Exchange.SZHK:
            return "HK_SZTC"  # 深港通
        elif exchange == Exchange.SEHK:
            return "HK"  # 香港本地

        # 其他交易所暂不支持
        return None

    def _qmt_symbol_to_vnpy(self, qmt_symbol: str) -> Optional[str]:
        """将 QMT 格式的股票代码转换为 VeighNa 格式

        Args:
            qmt_symbol: QMT 格式代码（如 "0700.HK_SHTC"）

        Returns:
            VeighNa 格式代码（如 "0700.SHHK"），转换失败返回 None

        Examples:
            >>> adapter._qmt_symbol_to_vnpy("0700.HK_SHTC")
            "0700.SHHK"
            >>> adapter._qmt_symbol_to_vnpy("2318.HK_SZTC")
            "2318.SZHK"
        """
        try:
            # QMT 格式: "0700.HK_SHTC" 或 "2318.HK_SZTC"
            # 处理多个点号的情况（只取第一个点号后的市场部分）
            if "." not in qmt_symbol:
                return None

            # 只按第一个点号分割
            parts = qmt_symbol.split(".", 1)
            if len(parts) != 2:
                return None

            code, market = parts[0], parts[1]

            # 再次按点号分割市场部分（处理类似 "HK_SHTC.EXTRA" 的情况）
            market = market.split(".")[0]

            # 映射 QMT 市场到 VeighNa 交易所
            market_to_exchange = {
                "HK_SHTC": "SHHK",  # 沪港通
                "HK_SZTC": "SZHK",  # 深港通
                "HK": "SEHK",       # 香港本地
            }

            exchange = market_to_exchange.get(market)
            if not exchange:
                return None

            return f"{code}.{exchange}"

        except Exception as e:
            print(f"QMT股票代码转换失败 {qmt_symbol}: {e}")
            return None

    # ========== 港股通数据 ==========

    def get_hk_sh_symbols(self, date: str = None) -> List[str]:
        """获取沪港通标的列表

        使用 QMT API 获取沪港通可交易的港股列表。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SHHK", "2318.SHHK"]）

        Examples:
            >>> adapter = QMTDataAdapter()
            >>> adapter.connect()
            >>> symbols = adapter.get_hk_sh_symbols()
            >>> print(symbols[:5])  # ['0700.SHHK', '09988.SHHK', ...]
        """
        if not self._connected:
            print("QMT 未连接，无法获取沪港通标的列表")
            return []

        try:
            # 尝试使用 xtdata 模块
            from xtquant import xtdata

            # QMT API: 获取沪港通标的列表
            sector_code = "HK_SHTC_STOCKS"
            stock_list = xtdata.get_stock_list_in_sector(sector_code)

            if not stock_list:
                print(f"QMT 未返回沪港通标的列表: {sector_code}")
                return []

            # 转换为 VeighNa 格式
            result = []
            for qmt_symbol in stock_list:
                vnpy_symbol = self._qmt_symbol_to_vnpy(qmt_symbol)
                if vnpy_symbol:
                    result.append(vnpy_symbol)

            print(f"获取到 {len(result)} 只沪港通标的")
            return result

        except ImportError:
            print("警告: xtdata 模块未安装，无法获取沪港通标的")
            return []
        except Exception as e:
            print(f"QMT 获取沪港通标的列表失败: {e}")
            return []

    def get_hk_sz_symbols(self, date: str = None) -> List[str]:
        """获取深港通标的列表

        使用 QMT API 获取深港通可交易的港股列表。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SZHK", "2318.SZHK"]）

        Examples:
            >>> adapter = QMTDataAdapter()
            >>> adapter.connect()
            >>> symbols = adapter.get_hk_sz_symbols()
            >>> print(symbols[:5])  # ['0700.SZHK', '09988.SZHK', ...]
        """
        if not self._connected:
            print("QMT 未连接，无法获取深港通标的列表")
            return []

        try:
            # 尝试使用 xtdata 模块
            from xtquant import xtdata

            # QMT API: 获取深港通标的列表
            sector_code = "HK_SZTC_STOCKS"
            stock_list = xtdata.get_stock_list_in_sector(sector_code)

            if not stock_list:
                print(f"QMT 未返回深港通标的列表: {sector_code}")
                return []

            # 转换为 VeighNa 格式
            result = []
            for qmt_symbol in stock_list:
                vnpy_symbol = self._qmt_symbol_to_vnpy(qmt_symbol)
                if vnpy_symbol:
                    result.append(vnpy_symbol)

            print(f"获取到 {len(result)} 只深港通标的")
            return result

        except ImportError:
            print("警告: xtdata 模块未安装，无法获取深港通标的")
            return []
        except Exception as e:
            print(f"QMT 获取深港通标的列表失败: {e}")
            return []

    def _get_stock_list_in_sector_mock(self, sector_code: str) -> List[str]:
        """获取板块成分股的 Mock 方法，用于测试

        Args:
            sector_code: 板块代码

        Returns:
            成分股代码列表
        """
        # 这个方法可以在子类中重写或用于 Mock
        return []

    def get_hk_sh_symbols_mockable(self, date: str = None) -> List[str]:
        """获取沪港通标的列表（可 Mock 版本）

        这个方法使用 _get_stock_list_in_sector_mock 方法，
        方便在测试中 Mock。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表
        """
        if not self._connected:
            print("QMT 未连接，无法获取沪港通标的列表")
            return []

        try:
            # QMT API: 获取沪港通标的列表
            sector_code = "HK_SHTC_STOCKS"
            stock_list = self._get_stock_list_in_sector_mock(sector_code)

            if not stock_list:
                print(f"QMT 未返回沪港通标的列表: {sector_code}")
                return []

            # 转换为 VeighNa 格式
            result = []
            for qmt_symbol in stock_list:
                vnpy_symbol = self._qmt_symbol_to_vnpy(qmt_symbol)
                if vnpy_symbol:
                    result.append(vnpy_symbol)

            print(f"获取到 {len(result)} 只沪港通标的")
            return result

        except Exception as e:
            print(f"QMT 获取沪港通标的列表失败: {e}")
            return []

    def get_hk_sz_symbols_mockable(self, date: str = None) -> List[str]:
        """获取深港通标的列表（可 Mock 版本）

        这个方法使用 _get_stock_list_in_sector_mock 方法，
        方便在测试中 Mock。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表
        """
        if not self._connected:
            print("QMT 未连接，无法获取深港通标的列表")
            return []

        try:
            # QMT API: 获取深港通标的列表
            sector_code = "HK_SZTC_STOCKS"
            stock_list = self._get_stock_list_in_sector_mock(sector_code)

            if not stock_list:
                print(f"QMT 未返回深港通标的列表: {sector_code}")
                return []

            # 转换为 VeighNa 格式
            result = []
            for qmt_symbol in stock_list:
                vnpy_symbol = self._qmt_symbol_to_vnpy(qmt_symbol)
                if vnpy_symbol:
                    result.append(vnpy_symbol)

            print(f"获取到 {len(result)} 只深港通标的")
            return result

        except Exception as e:
            print(f"QMT 获取深港通标的列表失败: {e}")
            return []

    # ========== 订单簿功能 ==========

    def get_order_book(self, symbol: str) -> Optional[Dict]:
        """获取订单簿"""
        tick = self._tick_cache.get(symbol)
        if not tick:
            return None

        return {
            "bid_price_1": tick.bid_price_1,
            "bid_volume_1": tick.bid_volume_1,
            "bid_price_2": tick.bid_price_2,
            "bid_volume_2": tick.bid_volume_2,
            "bid_price_3": tick.bid_price_3,
            "bid_volume_3": tick.bid_volume_3,
            "bid_price_4": tick.bid_price_4,
            "bid_volume_4": tick.bid_volume_4,
            "bid_price_5": tick.bid_price_5,
            "bid_volume_5": tick.bid_volume_5,
            "ask_price_1": tick.ask_price_1,
            "ask_volume_1": tick.ask_volume_1,
            "ask_price_2": tick.ask_price_2,
            "ask_volume_2": tick.ask_volume_2,
            "ask_price_3": tick.ask_price_3,
            "ask_volume_3": tick.ask_volume_3,
            "ask_price_4": tick.ask_price_4,
            "ask_volume_4": tick.ask_volume_4,
            "ask_price_5": tick.ask_price_5,
            "ask_volume_5": tick.ask_volume_5,
        }

    def get_bid_ask_spread(self, symbol: str) -> Optional[float]:
        """获取买卖价差"""
        order_book = self.get_order_book(symbol)
        if order_book:
            return order_book.get("ask_price_1", 0) - order_book.get("bid_price_1", 0)
        return None

    # ========== 统计信息 ==========

    @property
    def tick_count(self) -> int:
        """Tick总数"""
        return self._tick_count

    @property
    def last_tick_time(self) -> Optional[datetime]:
        """最后Tick时间"""
        return self._last_tick_time

    @property
    def subscribed_count(self) -> int:
        """订阅数量"""
        return len(self._subscribed_symbols)

    # ========== 板块数据 ==========

    def get_sector_list(self) -> List:
        """获取板块列表

        使用 QMT API 获取申万行业板块分类。

        Returns:
            板块列表
        """
        try:
            from ..models.sector import SectorData

            sector_list = []

            # 常见申万一级行业（硬编码，无需连接即可使用）
            sw_sectors = {
                "801010": "农林牧渔",
                "801020": "采掘",
                "801030": "化工",
                "801040": "钢铁",
                "801050": "有色金属",
                "801080": "电子",
                "801110": "家用电器",
                "801120": "食品饮料",
                "801130": "纺织服装",
                "801140": "轻工制造",
                "801150": "医药生物",
                "801160": "公用事业",
                "801170": "交通运输",
                "801180": "房地产",
                "801200": "商业贸易",
                "801210": "休闲服务",
                "801230": "综合",
                "801710": "建筑材料",
                "801720": "建筑装饰",
                "801730": "电气设备",
                "801740": "国防军工",
                "801750": "计算机",
                "801760": "传媒",
                "801770": "通信",
                "801780": "银行",
                "801790": "非银金融",
                "801880": "汽车",
                "801890": "机械设备",
            }

            for code, name in sw_sectors.items():
                sector = SectorData(
                    sector_code=code,
                    sector_name=name,
                    trade_date=datetime.now().date(),
                    change_pct=0.0,
                )
                sector_list.append(sector)

            return sector_list

        except Exception as e:
            print(f"QMT获取板块列表失败: {e}")
            return []

    def get_sector_stocks(self, sector_code: str) -> List[str]:
        """获取板块成分股

        Args:
            sector_code: 板块代码

        Returns:
            成分股代码列表
        """
        if not self._connected or not self._qmt_api:
            return []

        try:
            # QMT API: 获取板块成分股
            if hasattr(self._qmt_api, 'get_stock_list_in_sector'):
                stock_list = self._qmt_api.get_stock_list_in_sector(sector_code)
                return stock_list if stock_list else []
            return []
        except Exception as e:
            print(f"QMT获取板块成分股失败: {e}")
            return []

    def get_sector_index(
        self,
        sector_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取板块指数数据

        使用 miniQMT 两步下载流程（与 get_bar_data 一致）：
        1. download_history_data2 异步下载到本地
        2. get_local_data 读取本地数据

        Args:
            sector_code: 板块代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            K线数据列表
        """
        import time
        import logging

        logger = logging.getLogger("vnpy_china_data")

        if not self._connected:
            logger.debug("QMT未连接，无法获取板块指数数据")
            return []

        try:
            from xtquant import xtdata

            logger.debug(
                f"QMT正在下载板块指数: {sector_code}, "
                f"start={start_date}, end={end_date}"
            )

            # 第1步：异步下载数据到本地
            if hasattr(xtdata, 'download_history_data2'):
                xtdata.download_history_data2(
                    stock_list=[sector_code],
                    period="1d",
                    start_time=start_date,
                    end_time=end_date
                )
                time.sleep(3)
            else:
                logger.warning("xtdata不支持download_history_data2方法")
                return []

            # 第2步：读取本地数据
            if hasattr(xtdata, 'get_local_data'):
                data = xtdata.get_local_data(
                    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[sector_code],
                    period="1d",
                    start_time=start_date,
                    end_time=end_date
                )
            else:
                logger.warning("xtdata不支持get_local_data方法")
                return []

            # xtdata.get_local_data 返回 dict[str, DataFrame]（key=stock_code, value=K线DataFrame）
            if not data:
                logger.debug(f"QMT未获取到板块指数数据: {sector_code}")
                return []

            # 第3步：转换为 BarData 列表
            result: List[BarData] = []
            for df in data.values():
                if df is None or not hasattr(df, "iterrows"):
                    continue
                for _, row in df.iterrows():
                    # xtdata 的 time 列是毫秒时间戳（int），转 datetime
                    time_value = row.get("time")
                    if isinstance(time_value, (int, float)):
                        bar_dt = datetime.fromtimestamp(time_value / 1000)
                    else:
                        bar_dt = self._parse_qmt_time(time_value)
                    bar = BarData(
                        gateway_name="QMT",
                        symbol=sector_code,
                        exchange=Exchange.SSE if sector_code.startswith("80") else Exchange.SZSE,
                        datetime=bar_dt,
                        interval=Interval.DAILY,
                        open_price=float(row.get("open", 0)),
                        high_price=float(row.get("high", 0)),
                        low_price=float(row.get("low", 0)),
                        close_price=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        turnover=float(row.get("amount", 0)),
                    )
                    result.append(bar)

            logger.debug(f"QMT获取板块指数: {sector_code}, 共{len(result)}条")
            return result

        except ImportError:
            logger.warning("xtdata模块未安装，无法获取板块指数数据")
            return []
        except Exception as e:
            logger.warning(f"QMT获取板块指数失败: {e}")
            return []

    # ========== 龙虎榜数据 ==========

    def get_dragon_tiger_data(self, trade_date: str) -> List:
        """获取龙虎榜数据

        QMT 暂不支持直接获取龙虎榜数据，返回空列表。
        龙虎榜数据需要通过其他方式获取（如东方财富、同花顺等）。

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            龙虎榜数据列表
        """
        # QMT 目前不提供龙虎榜数据接口
        # 实际项目中可以通过以下方式获取：
        # 1. 东方财富 API
        # 2. 同花顺 API
        # 3. Tushare (需要高级权限)
        return []


class RealtimeBarGenerator:
    """实时K线生成器

    从Tick数据实时生成K线数据。
    """

    def __init__(
        self,
        symbol: str,
        interval: Interval,
        callback: Optional[Callable[[BarData], None]] = None
    ):
        self.symbol = symbol
        self.interval = interval
        self.callback = callback

        # 当前K线数据
        self._current_bar: Optional[BarData] = None
        self._last_tick: Optional[TickData] = None

        # 周期转换
        self._interval_seconds = self._get_interval_seconds(interval)

    def update_tick(self, tick: TickData) -> Optional[BarData]:
        """更新Tick数据，生成K线"""
        # 初始化或创建新K线
        if not self._current_bar:
            self._create_new_bar(tick)
            return None

        # 检查是否需要创建新K线
        current_time = tick.datetime
        bar_time = self._current_bar.datetime

        # 计算时间差
        if self._is_new_bar(current_time, bar_time):
            # 返回完成的K线，创建新K线
            finished_bar = self._current_bar
            self._create_new_bar(tick)
            return finished_bar

        # 更新当前K线
        self._update_bar(tick)
        return None

    def _create_new_bar(self, tick: TickData) -> None:
        """创建新K线"""
        self._current_bar = BarData(
            symbol=tick.symbol,
            exchange=tick.exchange,
            interval=self.interval,
            datetime=self._get_bar_time(tick.datetime),
            open_price=tick.last_price,
            high_price=tick.last_price,
            low_price=tick.last_price,
            close_price=tick.last_price,
            volume=tick.volume,
            turnover=tick.turnover
        )

    def _update_bar(self, tick: TickData) -> None:
        """更新当前K线"""
        if not self._current_bar:
            return

        # 更新收盘价
        self._current_bar.close_price = tick.last_price

        # 更新最高价
        if tick.last_price > self._current_bar.high_price:
            self._current_bar.high_price = tick.last_price

        # 更新最低价
        if tick.last_price < self._current_bar.low_price:
            self._current_bar.low_price = tick.last_price

        # 累加成交量
        if tick.volume and self._last_tick:
            self._current_bar.volume += (tick.volume - self._last_tick.volume)

        # 累加成交额
        if tick.turnover and self._last_tick:
            self._current_bar.turnover += (tick.turnover - self._last_tick.turnover)

        self._last_tick = tick

    def _is_new_bar(self, current_time: datetime, bar_time: datetime) -> bool:
        """判断是否新K线

        注意：vnpy的Interval枚举只包含基础值（MINUTE, HOUR, DAILY等），
        不包含MINUTE_5、MINUTE_15等细分周期。如需支持多周期，
        请通过字符串方式传递周期信息。
        """
        if self.interval == Interval.MINUTE:
            return current_time.minute != bar_time.minute
        elif self.interval == Interval.HOUR:
            return current_time.hour != bar_time.hour
        elif self.interval == Interval.DAILY:
            return current_time.date() != bar_time.date()

        return False

    def _get_bar_time(self, tick_time: datetime) -> datetime:
        """获取K线时间

        注意：vnpy的Interval枚举只包含基础值。
        """
        if self.interval == Interval.MINUTE:
            return tick_time.replace(second=0, microsecond=0)
        elif self.interval == Interval.HOUR:
            return tick_time.replace(minute=0, second=0, microsecond=0)
        elif self.interval == Interval.DAILY:
            return tick_time.replace(hour=0, minute=0, second=0, microsecond=0)

        return tick_time

    @staticmethod
    def _get_interval_seconds(interval: Interval) -> int:
        """获取周期秒数

        注意：vnpy的Interval枚举只包含基础值。
        """
        mapping = {
            Interval.MINUTE: 60,
            Interval.HOUR: 3600,
            Interval.DAILY: 86400,
            Interval.WEEKLY: 604800,
        }
        return mapping.get(interval, 60)

