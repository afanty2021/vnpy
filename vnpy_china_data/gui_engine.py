"""
A股数据服务GUI引擎
管理A股数据服务的GUI功能
"""

from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine
from vnpy.trader.constant import Exchange, Interval


class ChinaDataGuiEngine(BaseEngine):
    """A股数据服务GUI引擎

    提供A股数据服务的GUI管理功能：
    - 历史数据下载
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

        # 下载状态
        self._downloading: bool = False

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

    # ==================== 港股通名单管理 ====================

    def update_hk_connect_stocks(self) -> Dict[str, Any]:
        """手动更新港股通股票名单

        从上交所和深交所网站爬取最新的港股通股票名单，
        并存储到数据库中。

        Returns:
            更新结果字典，包含 success, count, sh_count, sz_count 等

        Examples:
            >>> result = engine.update_hk_connect_stocks()
            >>> if result['success']:
            ...     print(f"更新成功：沪港通 {result['sh_count']} 只，深港通 {result['sz_count']} 只")
        """
        if not self.data_service:
            return {
                "success": False,
                "error": "数据服务未初始化"
            }

        self.main_engine.write_log("正在更新港股通股票名单...", "ChinaDataApp")

        result = self.data_service.update_hk_connect_stocks()

        if result["success"]:
            self.main_engine.write_log(
                f"港股通名单更新成功：总计 {result['count']} 只，"
                f"沪港通 {result['sh_count']} 只，深港通 {result['sz_count']} 只",
                "ChinaDataApp"
            )
        else:
            self.main_engine.write_log(
                f"港股通名单更新失败: {result.get('error', '未知错误')}",
                "ChinaDataApp"
            )

        return result

    def get_hk_connect_update_info(self) -> Optional[Dict[str, Any]]:
        """获取港股通名单更新信息

        Returns:
            更新信息字典，包含 last_updated, days_since_update, total_count 等
        """
        if not self.data_service:
            return None

        return self.data_service.get_hk_connect_update_info()

    # ==================== 历史数据下载 ====================

    def download_history_data(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: Interval = Interval.DAILY
    ) -> Dict[str, Any]:
        """下载历史数据

        Args:
            symbols: 股票代码列表（如 ["000001.SZ", "600000.SH", "00700.SEHK"]）
            start_date: 开始日期
            end_date: 结束日期
            interval: K线周期

        Returns:
            下载结果字典，包含 success, downloaded_count, failed_symbols 等
        """
        if not self.data_service:
            return {
                "success": False,
                "error": "数据服务未初始化，请配置Tushare token或QMT RPC连接"
            }

        if self._downloading:
            return {
                "success": False,
                "error": "已有下载任务正在进行"
            }

        self._downloading = True
        result = {
            "success": True,
            "downloaded_count": 0,
            "failed_symbols": [],
            "total_symbols": len(symbols)
        }

        try:
            self.main_engine.write_log(
                f"开始下载历史数据：{len(symbols)}只股票，{start_date} 至 {end_date}",
                "ChinaDataApp"
            )

            for i, symbol in enumerate(symbols):
                try:
                    # 解析股票代码和交易所
                    exchange = self._parse_exchange(symbol)

                    # 提取纯代码（去除交易所后缀）
                    # 例如："00700.SEHK" -> "00700"
                    if "." in symbol:
                        code = symbol.split(".")[0]
                    else:
                        code = symbol

                    # 下载数据（使用纯代码和交易所枚举）
                    bars = self.data_service.download_bar_data(
                        symbol=code,  # 使用纯代码，不含交易所后缀
                        exchange=exchange,
                        interval=interval,
                        start=start_date,
                        end=end_date
                    )

                    if bars:
                        result["downloaded_count"] += len(bars)

                    self.main_engine.write_log(
                        f"[{i+1}/{len(symbols)}] {symbol}: 已下载 {len(bars) if bars else 0} 条数据",
                        "ChinaDataApp"
                    )

                except Exception as e:
                    result["failed_symbols"].append(symbol)
                    self.main_engine.write_log(f"下载 {symbol} 失败: {e}", "ChinaDataApp")

            self.main_engine.write_log(
                f"下载完成：成功 {result['downloaded_count']} 条，失败 {len(result['failed_symbols'])} 只",
                "ChinaDataApp"
            )

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            self.main_engine.write_log(f"下载历史数据失败: {e}", "ChinaDataApp")

        finally:
            self._downloading = False

        return result

    def get_default_symbols(self) -> List[str]:
        """获取默认股票代码列表

        Returns:
            常用A股代码列表
        """
        return [
            # 上证指数
            "000001.SH",
            # 深证成指
            "399001.SZ",
            # 蓝筹股
            "600000.SH",  # 浦发银行
            "600036.SH",  # 招商银行
            "600519.SH",  # 贵州茅台
            "600887.SH",  # 伊利股份
            "601318.SH",  # 中国平安
            "601398.SH",  # 工商银行
            "601857.SH",  # 中国石油
            "601988.SH",  # 中国银行
            "000001.SZ",  # 平安银行
            "000002.SZ",  # 万科A
            "000063.SZ",  # 中兴通讯
            "000066.SZ",  # 长城电脑
            "000333.SZ",  # 美的集团
            "000858.SZ",  # 五粮液
        ]

    def get_exchange_symbols(self, exchange: str) -> List[str]:
        """获取交易所所有股票代码

        Args:
            exchange: 交易所代码 (SSE/SZSE/BSE/HK_SH/HK_SZ/HK_ALL)

        Returns:
            股票代码列表
        """
        try:
            # 从数据服务获取股票列表
            stock_list = self.data_service.get_stock_list()

            # 根据交易所筛选
            exchange_suffix_map = {
                "SSE": ".SH",
                "SZSE": ".SZ",
                "BSE": ".BJ",
            }

            suffix = exchange_suffix_map.get(exchange)
            if not suffix:
                return []

            # 筛选股票代码
            symbols = []
            for stock in stock_list:
                ts_code = stock.get("ts_code", "")
                if ts_code.endswith(suffix):
                    symbols.append(ts_code)

            self.main_engine.write_log(
                f"获取{exchange}交易所股票：共 {len(symbols)} 只",
                "ChinaDataApp"
            )

            return symbols[:500]  # 限制数量，避免过多

        except Exception as e:
            self.main_engine.write_log(f"获取交易所股票失败: {e}", "ChinaDataApp")
            return []

    def get_hk_symbols(self, hk_type: str) -> List[str]:
        """获取港股通股票代码

        重要：港股通股票本身在香港联合交易所上市，
        历史数据下载时需要使用 Exchange.SEHK（香港本地）后缀。

        Args:
            hk_type: 港股通类型 (HK_SH/HK_SZ/HK_ALL)

        Returns:
            港股代码列表（使用 SEHK 后缀用于下载）

        Examples:
            >>> symbols = engine.get_hk_symbols("HK_ALL")
            >>> print(symbols[:5])  # ['00700.SEHK', '01810.SEHK', ...]
        """
        try:
            # 从数据库获取港股通股票列表
            channel_map = {
                "HK_SH": "SHHK",   # 沪港通
                "HK_SZ": "SZHK",   # 深港通
                "HK_ALL": None,    # 全部
            }

            channel = channel_map.get(hk_type)
            symbols = self.data_service.database.get_hk_connect_symbols(
                channel=channel,
                status="active"
            )

            if not symbols:
                self.main_engine.write_log(f"未获取到{hk_type}港股通股票", "ChinaDataApp")
                return []

            # symbols 已经是 "00700.HK" 格式
            # 需要转换为 "00700.SEHK" 格式用于显示
            display_symbols = [s.replace(".HK", ".SEHK") for s in symbols]

            self.main_engine.write_log(
                f"获取{hk_type}港股通股票：共 {len(display_symbols)} 只",
                "ChinaDataApp"
            )

            return display_symbols

        except AttributeError:
            # 数据库方法不存在
            self.main_engine.write_log(
                f"警告：港股通数据库表尚未创建，请先运行数据更新",
                "ChinaDataApp"
            )
            return []
        except Exception as e:
            self.main_engine.write_log(f"获取港股通股票失败: {e}", "ChinaDataApp")
            return []

    def get_hk_sh_symbols(self) -> List[str]:
        """获取沪港通股票代码

        Returns:
            沪港通股票代码列表
        """
        return self.get_hk_symbols("HK_SH")

    def get_hk_sz_symbols(self) -> List[str]:
        """获取深港通股票代码

        Returns:
            深港通股票代码列表
        """
        return self.get_hk_symbols("HK_SZ")

    def get_index_symbols(self, index: str) -> List[str]:
        """获取指数成分股

        Args:
            index: 指数代码 (HS300/ZZ500/ZZ1000)

        Returns:
            成分股代码列表
        """
        try:
            # 指数代码映射
            index_map = {
                "HS300": "000300.SH",  # 沪深300
                "ZZ500": "000905.SH",  # 中证500
                "ZZ1000": "000852.SH",  # 中证1000
            }

            index_code = index_map.get(index)
            if not index_code:
                return []

            # 从数据服务获取指数成分股
            # 暂时使用硬编码的成分股列表
            # 实际项目中应该从 Tushare index_classify 或 index_member API 获取

            # 沪深300成分股（前50只示例）
            if index == "HS300":
                symbols = [
                    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
                    "601318.SH", "601398.SH", "601857.SH", "601988.SH",
                    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
                    "000333.SZ", "000333.SZ", "000858.SZ", "002594.SZ",
                ]
            # 中证500成分股（前50只示例）
            elif index == "ZZ500":
                symbols = [
                    "600000.SH", "600004.SH", "600009.SH", "600010.SH",
                    "600016.SH", "600030.SH", "600104.SH", "600196.SH",
                    "000001.SZ", "000002.SZ", "000006.SZ", "000009.SZ",
                    "000012.SZ", "000025.SZ", "000027.SZ", "000030.SZ",
                ]
            # 中证1000成分股（前50只示例）
            elif index == "ZZ1000":
                symbols = [
                    "600000.SH", "600036.SH", "600519.SH", "600887.SH",
                    "601318.SH", "601398.SH", "601857.SH", "601988.SH",
                    "000001.SZ", "000002.SZ", "000063.SZ", "000066.SZ",
                    "000333.SZ", "000858.SZ", "002594.SZ", "300750.SZ",
                ]
            else:
                symbols = []

            self.main_engine.write_log(
                f"获取{index}成分股：共 {len(symbols)} 只（示例）",
                "ChinaDataApp"
            )

            return symbols

        except Exception as e:
            self.main_engine.write_log(f"获取指数成分股失败: {e}", "ChinaDataApp")
            return []

    def _parse_exchange(self, symbol: str) -> Exchange:
        """从股票代码解析交易所

        重要：港股通股票（.SHHK/.SZHK）在历史数据下载时
        需要转换为香港本地交易所（.SEHK），因为港股通股票
        本身就是在香港联合交易所上市的。

        Args:
            symbol: 股票代码（如 "000001.SZ", "0700.SHHK", "0700.SEHK"）

        Returns:
            交易所枚举（港股通统一返回 SEHK）
        """
        # 港股通：沪港通/深港通/香港本地 → 统一 SEHK
        if symbol.endswith((".SHHK", ".SZHK", ".SEHK", ".HK")):
            return Exchange.SEHK
        # A股：上海/深圳
        elif symbol.endswith(".SH"):
            return Exchange.SSE
        elif symbol.endswith(".SZ"):
            return Exchange.SZSE
        else:
            # 默认按首位字符判断（A 股）
            if symbol.startswith("6"):
                return Exchange.SSE
            else:
                return Exchange.SZSE

    def is_downloading(self) -> bool:
        """是否正在下载数据"""
        return self._downloading

    # ==================== 龙虎榜数据查询 ====================

    def query_dragon_tiger(self, trade_date: Optional[date] = None) -> List[Any]:
        """查询龙虎榜数据

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            龙虎榜数据列表
        """
        if not self.data_service:
            # 数据服务未初始化，返回空列表并提示用户
            self.main_engine.write_log(
                "错误：A股数据服务未初始化，请配置Tushare token或QMT RPC连接\n"
                "配置方式：1)设置环境变量 TUSHARE_TOKEN 或 2)启动QMT客户端",
                "ChinaDataApp"
            )
            return []

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询龙虎榜数据：{trade_date}", "ChinaDataApp")
            data = self.data_service.get_dragon_tiger_data(trade_date)

            if not data:
                self.main_engine.write_log(
                    f"未查询到 {trade_date} 的龙虎榜数据\n"
                    f"可能原因：1)非交易日 2)Tushare token未配置 3)网络问题",
                    "ChinaDataApp"
                )
                return []

            self.main_engine.write_log(f"查询完成，共{len(data)}条记录", "ChinaDataApp")
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询龙虎榜数据失败：{e}", "ChinaDataApp")
            return []

    def query_northbound_flow(self, trade_date: Optional[date] = None) -> Optional[Any]:
        """查询北向资金流向

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            北向资金流向数据
        """
        if not self.data_service:
            # 数据服务未初始化，返回空并提示用户
            self.main_engine.write_log(
                "错误：A股数据服务未初始化，请配置Tushare token或QMT RPC连接\n"
                "配置方式：1)设置环境变量 TUSHARE_TOKEN 或 2)启动QMT客户端",
                "ChinaDataApp"
            )
            return None

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询北向资金流向：{trade_date}", "ChinaDataApp")
            data = self.data_service.get_northbound_flow(trade_date)
            if data:
                self.main_engine.write_log(f"查询完成，净流入：{data.total_net_inflow:.2f}亿元", "ChinaDataApp")
            else:
                self.main_engine.write_log(
                    f"未查询到 {trade_date} 的北向资金数据\n"
                    f"可能原因：1)非交易日 2)Tushare token未配置 3)网络问题",
                    "ChinaDataApp"
                )
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询北向资金流向失败：{e}", "ChinaDataApp")
            return None

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


__all__ = ["ChinaDataGuiEngine"]
