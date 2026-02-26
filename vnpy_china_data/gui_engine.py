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
            symbols: 股票代码列表（如 ["000001.SZ", "600000.SH"]）
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

                    # 下载数据
                    bars = self.data_service.download_bar_data(
                        symbol=symbol,
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

    def _parse_exchange(self, symbol: str) -> Exchange:
        """从股票代码解析交易所

        Args:
            symbol: 股票代码（如 "000001.SZ" 或 "000001.SZSE"）

        Returns:
            交易所枚举
        """
        if symbol.endswith(".SH") or ".SH" in symbol:
            return Exchange.SSE
        elif symbol.endswith(".SZ") or ".SZ" in symbol:
            return Exchange.SZSE
        else:
            # 默认判断
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
