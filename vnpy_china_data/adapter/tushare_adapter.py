"""
Tushare数据适配器

实现Tushare API的数据获取功能。
"""

import tushare as ts
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from threading import Lock

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval

from ..limiter import TushareRateLimiter
from ..models.dragon_tiger import DragonTigerData
from ..models.northbound import NorthboundFlowData
from ..models.sector import SectorData
from ..models.money_flow import MoneyFlowData
from .base import BaseDataAdapter


class TushareDataAdapter(BaseDataAdapter):
    """Tushare数据适配器

    封装Tushare Pro API，提供股票数据获取功能。
    支持限流和自动重试。
    """

    def __init__(
        self,
        token: str = "",
        rate_limit: int = 200,
        timeout: int = 30
    ):
        """初始化Tushare适配器

        Args:
            token: Tushare Token
            rate_limit: 每分钟调用次数限制
            timeout: 超时时间（秒）
        """
        super().__init__()
        self.token = token
        self.timeout = timeout

        # 初始化Tushare Pro API
        if token:
            self.pro = ts.pro_api(token)
        else:
            self.pro = None

        # 限流器
        self.rate_limiter = TushareRateLimiter(
            max_calls=rate_limit,
            period=60
        )

        self._lock = Lock()

    def connect(self) -> bool:
        """连接Tushare API"""
        if not self.token:
            return False

        try:
            # 测试API连接
            self.pro = ts.pro_api(self.token)
            # 获取token信息
            self.pro.token
            self._connected = True
            return True
        except Exception as e:
            print(f"Tushare连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._connected = False

    def _call_api(self, api_name: str, **kwargs) -> pd.DataFrame:
        """带限流的API调用

        Args:
            api_name: API方法名
            **kwargs: API参数

        Returns:
            DataFrame结果
        """
        if not self._connected or not self.pro:
            return pd.DataFrame()

        # 等待限流器
        while not self.rate_limiter.acquire():
            import time
            time.sleep(0.1)

        try:
            api_method = getattr(self.pro, api_name)
            df = api_method(**kwargs)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            print(f"Tushare API调用失败: {api_name}, {e}")
            return pd.DataFrame()

    # ========== 行情数据实现 ==========

    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取K线数据"""
        ts_code = self.symbol_to_ts_code(symbol, exchange)

        if interval == Interval.DAILY:
            return self._get_daily_bars(ts_code, start, end)
        elif interval == Interval.MINUTE:
            return self._get_minute_bars(ts_code, start, end, interval)
        else:
            return []

    def _get_daily_bars(
        self,
        ts_code: str,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取日线数据"""
        start_date = start.strftime("%Y%m%d")
        end_date = end.strftime("%Y%m%d")

        df = self._call_api(
            "daily",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        bars = []
        for _, row in df.iterrows():
            try:
                bar = BarData(
                    symbol=ts_code.split(".")[0],
                    exchange=self._get_exchange(ts_code),
                    interval=Interval.DAILY,
                    datetime=pd.to_datetime(row["trade_date"]),
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    volume=float(row["vol"]) if "vol" in row else 0,
                    turnover=float(row.get("amount", 0))
                )
                bars.append(bar)
            except Exception:
                continue

        return bars

    def _get_minute_bars(
        self,
        ts_code: str,
        start: datetime,
        end: datetime,
        interval: Interval
    ) -> List[BarData]:
        """获取分钟线数据

        Note: Tushare分钟线需要高级权限
        VeighNa 使用 Interval.MINUTE 表示分钟线，默认使用1分钟
        """
        # VeighNa Interval.MINUTE 表示分钟线，默认使用1分钟
        freq = "1min"

        start_time = start.strftime("%Y%m%d%H%M%S")
        end_time = end.strftime("%Y%m%d%H%M%S")

        try:
            df = self._call_api(
                "stk_mins",
                ts_code=ts_code,
                start_time=start_time,
                end_time=end_time,
                freq=freq
            )

            if df.empty:
                return []

            bars = []
            for _, row in df.iterrows():
                try:
                    bar = BarData(
                        symbol=ts_code.split(".")[0],
                        exchange=self._get_exchange(ts_code),
                        interval=interval,
                        datetime=pd.to_datetime(row["trade_time"]),
                        open_price=float(row["open"]),
                        high_price=float(row["high"]),
                        low_price=float(row["low"]),
                        close_price=float(row["close"]),
                        volume=float(row["vol"]) if "vol" in row else 0,
                        turnover=0
                    )
                    bars.append(bar)
                except Exception:
                    continue

            return bars

        except AttributeError:
            print("Tushare分钟线需要高级权限")
            return []

    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List:
        """获取Tick数据

        Note: Tushare不提供实时Tick数据，此功能需要使用QMT
        """
        return []

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息"""
        # 转换symbol格式
        if symbol.startswith("6"):
            ts_code = f"{symbol}.SH"
        else:
            ts_code = f"{symbol}.SZ"

        df = self._call_api(
            "stock_basic",
            ts_code=ts_code,
            fields="ts_code,symbol,name,area,industry,market,list_date"
        )

        if df.empty:
            return None

        row = df.iloc[0]
        return {
            "symbol": row["symbol"],
            "name": row["name"],
            "exchange": self._get_exchange(row["ts_code"]).value,
            "industry": row.get("industry", ""),
            "area": row.get("area", ""),
            "market": row.get("market", ""),
            "list_date": row.get("list_date", ""),
            "is_st": "ST" in row.get("name", "")
        }

    # ========== 龙虎榜数据 ==========

    def get_dragon_tiger_data(
        self,
        trade_date: str
    ) -> List[DragonTigerData]:
        """获取龙虎榜数据"""
        df = self._call_api("top_list", trade_date=trade_date)

        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            try:
                dt = DragonTigerData(
                    symbol=row["ts_code"].split(".")[0],
                    name=row.get("name", ""),
                    trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
                    close_price=float(row.get("close", 0)),
                    change_pct=float(row.get("pct_chg", 0)),
                    turnover_rate=float(row.get("turnover_rate", 0)),
                    institution_net_buy=float(row.get("amount_buy", 0)) / 10000,
                    institution_buy=float(row.get("amount_buy", 0)) / 10000,
                    institution_sell=float(row.get("amount_sell", 0)) / 10000,
                    broker_net_buy=0,
                    reason=row.get("pchange_reason", ""),
                )
                results.append(dt)
            except Exception:
                continue

        return results

    # ========== 北向资金数据 ==========

    def get_northbound_flow(
        self,
        trade_date: str
    ) -> Optional[NorthboundFlowData]:
        """获取北向资金流向"""
        df = self._call_api("moneyflow_hsgt", trade_date=trade_date)

        if df.empty:
            return None

        # 获取最新数据（已按日期排序）
        row = df.iloc[0]

        # 新的Tushare API返回格式：
        # ggt_ss: 港股通（上海）
        # ggt_sz: 港股通（深圳）
        # hgt: 沪港通
        # sgt: 深港通
        # north_money: 北向净流入
        # south_money: 南向净流入
        # 单位：万元

        # 沪股通 = 沪港通(hgt) - 需要分开计算
        # 使用北向资金总量数据
        sh_net = float(row.get("hgt", 0) or 0)  # 沪港通
        sz_net = float(row.get("sgt", 0) or 0)  # 深港通

        # 北向净流入 = 沪股通 + 深股通
        north_money = float(row.get("north_money", 0) or 0)

        data = NorthboundFlowData(
            trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
            sh_net_inflow=sh_net / 10000,  # 万元转亿元
            sh_buy_volume=0,  # API不返回详细买卖数据
            sh_sell_volume=0,
            sz_net_inflow=sz_net / 10000,  # 万元转亿元
            sz_buy_volume=0,
            sz_sell_volume=0,
        )

        return data

    # ========== 个股资金流向数据 ==========

    def get_moneyflow(
        self,
        ts_code: str = "",
        trade_date: str = "",
        start_date: str = "",
        end_date: str = ""
    ) -> List[MoneyFlowData]:
        """获取个股资金流向数据

        Args:
            ts_code: 股票代码（格式：000001.SZ）
            trade_date: 交易日期（格式：20240201）
            start_date: 开始日期（格式：20240101）
            end_date: 结束日期（格式：20240131）

        Returns:
            资金流向数据列表

        Note:
            如果不指定ts_code，返回所有股票的资金流向数据
            如果不指定日期，默认返回最近一个交易日的数据
        """
        # 构建API参数
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        df = self._call_api("moneyflow", **params)

        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            try:
                # 解析交易日期
                trade_dt = datetime.strptime(str(row["trade_date"]), "%Y%m%d").date()

                # 解析股票代码和名称
                symbol_code = row.get("ts_code", "")
                symbol = symbol_code.split(".")[0] if symbol_code else ""
                name = row.get("name", "")

                moneyflow = MoneyFlowData(
                    symbol=symbol,
                    name=name,
                    trade_date=trade_dt,
                    close_price=float(row.get("close", 0)) if "close" in row else 0.0,
                    change_pct=float(row.get("pct_chg", 0)) if "pct_chg" in row else 0.0,
                    # 超大单（手）- 使用 elg (extra large)
                    super_large_buy=int(row.get("buy_elg_vol", 0)),
                    super_large_sell=int(row.get("sell_elg_vol", 0)),
                    # 大单（手）- 使用 lg (large)
                    large_buy=int(row.get("buy_lg_vol", 0)),
                    large_sell=int(row.get("sell_lg_vol", 0)),
                    # 中单（手）- 使用 md (medium)
                    medium_buy=int(row.get("buy_md_vol", 0)),
                    medium_sell=int(row.get("sell_md_vol", 0)),
                    # 小单（手）- 使用 sm (small)
                    small_buy=int(row.get("buy_sm_vol", 0)),
                    small_sell=int(row.get("sell_sm_vol", 0)),
                    # 超大单金额（元）
                    super_large_buy_amount=float(row.get("buy_elg_amount", 0)),
                    super_large_sell_amount=float(row.get("sell_elg_amount", 0)),
                    # 大单金额（元）
                    large_buy_amount=float(row.get("buy_lg_amount", 0)),
                    large_sell_amount=float(row.get("sell_lg_amount", 0)),
                    # 中单金额（元）
                    medium_buy_amount=float(row.get("buy_md_amount", 0)),
                    medium_sell_amount=float(row.get("sell_md_amount", 0)),
                    # 小单金额（元）
                    small_buy_amount=float(row.get("buy_sm_amount", 0)),
                    small_sell_amount=float(row.get("sell_sm_amount", 0)),
                )
                results.append(moneyflow)
            except Exception as e:
                print(f"解析资金流向数据失败: {e}")
                continue

        return results

    # ========== 板块数据 ==========

    def get_sector_list(self) -> List[SectorData]:
        """获取板块列表（行业分类）"""
        # 获取最近交易日
        try:
            cal_df = self._call_api(
                "trade_cal",
                exchange="SSE",
                start_date=(datetime.now() - timedelta(days=10)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                is_open="1"
            )
            if cal_df.empty:
                return []
            trade_date = cal_df.iloc[-1]["cal_date"]
        except Exception:
            # 使用固定日期作为fallback
            trade_date = "20260213"

        df = self._call_api(
            "sw_daily",
            trade_date=trade_date
        )

        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            try:
                sector = SectorData(
                    sector_code=row.get("ts_code", ""),
                    sector_name=row.get("name", ""),
                    trade_date=datetime.now().date(),
                    change_pct=float(row.get("pct_chg", 0)),
                )
                results.append(sector)
            except Exception:
                continue

        return results

    # ========== 订阅接口 ==========

    def subscribe(self, symbols: List[str]) -> bool:
        """订阅实时行情

        Note: Tushare不支持实时订阅，需要使用QMT
        """
        return False

    def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅"""
        return False

    # ========== 工具方法 ==========

    def _get_exchange(self, ts_code: str) -> Exchange:
        """从ts_code获取交易所

        支持港股通交易所映射。Tushare 对所有港股（沪港通/深港通/香港本地）
        都使用 .HK 后缀，因此默认映射为 SEHK（香港交易所）。
        """
        suffix = ts_code.split(".")[-1]
        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE,
            "HK": Exchange.SEHK  # Tushare 港股统一使用 .HK
        }
        return exchange_map.get(suffix, Exchange.SZSE)

    def _is_st(self, name: str) -> bool:
        """判断是否ST股票"""
        return "ST" in name or "st" in name

    # ========== 扩展API ==========

    def get_stock_list(self, list_status: str = "L") -> List[Dict]:
        """获取股票列表"""
        df = self._call_api(
            "stock_basic",
            exchange="",
            list_status=list_status,
            fields="ts_code,symbol,name,area,industry,market,list_date"
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_hk_sh_symbols(self, date: str = None) -> List[str]:
        """获取沪港通标的列表

        使用 Tushare 获取沪港通可交易的港股列表。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SHHK", "2318.SHHK"]）

        Note:
            Tushare 的 hk_basic 接口返回港股基本信息，需要筛选沪港通标的
        """
        try:
            # 获取港股基本信息
            df = self._call_api(
                "hk_basic",
                is_sch="S"  # 沪港通
            )

            if df.empty:
                return []

            # 转换为 VeighNa 格式
            result = []
            for _, row in df.iterrows():
                try:
                    ts_code = row.get("ts_code", "")
                    # Tushare 港股格式: 00700.HK
                    # 转换为 VeighNa 格式: 0700.SHHK
                    if ts_code and ts_code.endswith(".HK"):
                        symbol = ts_code.split(".")[0]
                        vnpy_symbol = f"{symbol}.SHHK"
                        result.append(vnpy_symbol)
                except Exception:
                    continue

            return result

        except Exception as e:
            print(f"Tushare 获取沪港通标的列表失败: {e}")
            return []

    def get_hk_sz_symbols(self, date: str = None) -> List[str]:
        """获取深港通标的列表

        使用 Tushare 获取深港通可交易的港股列表。

        Args:
            date: 交易日期（格式：YYYYMMDD），None 表示获取最新列表

        Returns:
            VeighNa 格式的股票代码列表（如 ["0700.SZHK", "2318.SZHK"]）

        Note:
            Tushare 的 hk_basic 接口返回港股基本信息，需要筛选深港通标的
        """
        try:
            # 获取港股基本信息
            df = self._call_api(
                "hk_basic",
                is_sch="D"  # 深港通
            )

            if df.empty:
                return []

            # 转换为 VeighNa 格式
            result = []
            for _, row in df.iterrows():
                try:
                    ts_code = row.get("ts_code", "")
                    # Tushare 港股格式: 00700.HK
                    # 转换为 VeighNa 格式: 0700.SZHK
                    if ts_code and ts_code.endswith(".HK"):
                        symbol = ts_code.split(".")[0]
                        vnpy_symbol = f"{symbol}.SZHK"
                        result.append(vnpy_symbol)
                except Exception:
                    continue

            return result

        except Exception as e:
            print(f"Tushare 获取深港通标的列表失败: {e}")
            return []

    def get_pro_bar(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        adj: str = "qfq"
    ) -> pd.DataFrame:
        """获取日线数据（pro_bar接口，支持复权）"""
        try:
            return self._call_api(
                "pro_bar",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                adj=adj,
                freq="D"
            )
        except Exception as e:
            print(f"获取pro_bar失败: {e}")
            return pd.DataFrame()

    def get_income_statement(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """获取利润表"""
        df = self._call_api(
            "income",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_balance_sheet(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """获取资产负债表"""
        df = self._call_api(
            "balancesheet",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_cash_flow(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """获取现金流量表"""
        df = self._call_api(
            "cashflow",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    # ========== 交易日历 ==========
    def get_trade_calendar(
        self,
        exchange: str = "SSE",
        start_date: str = None,
        end_date: str = None
    ) -> List[str]:
        """获取交易日历

        Args:
            exchange: 交易所 ("SSE"上交所, "SZSE"深交所, "HKEX"港交所)
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）

        Returns:
            交易日期列表（格式：YYYYMMDD）
        """
        # 默认获取最近一年的交易日历
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            # Tushare的trade_cal接口支持以下exchange参数：
            # SSE - 上交所
            # SZSE - 深交所（使用相同日历）
            # 对于香港市场，需要使用不同的方法
            df = self._call_api(
                "trade_cal",
                exchange=exchange,
                start_date=start_date,
                end_date=end_date,
                is_open="1"  # 只返回开市的日期
            )

            if df.empty:
                return []

            return df["cal_date"].tolist()

        except Exception as e:
            print(f"获取交易日历失败: {e}")
            return []

    def get_hk_trade_calendar(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> List[str]:
        """获取香港交易日历

        Args:
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）

        Returns:
            交易日期列表（格式：YYYYMMDD）
        """
        # 默认获取最近一年的交易日历
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            # Tushare的hk_trade_cal接口用于获取港股交易日历
            df = self._call_api(
                "hk_trade_cal",
                start_date=start_date,
                end_date=end_date,
                is_open="1"  # 只返回开市的日期
            )

            if df.empty:
                return []

            return df["cal_date"].tolist()

        except Exception as e:
            print(f"获取香港交易日历失败: {e}")
            return []
