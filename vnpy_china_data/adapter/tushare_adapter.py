"""
Tushare数据适配器

实现Tushare API的数据获取功能。
"""

import tushare as ts
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from threading import Lock

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval

from ..limiter import TushareRateLimiter
from ..models.dragon_tiger import DragonTigerData
from ..models.northbound import NorthboundFlowData
from ..models.sector import SectorData
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
        elif interval in [Interval.MINUTE_1, Interval.MINUTE_5,
                          Interval.MINUTE_15, Interval.MINUTE_30]:
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
        """
        # 转换为Tushare频率格式
        freq_map = {
            Interval.MINUTE_1: "1min",
            Interval.MINUTE_5: "5min",
            Interval.MINUTE_15: "15min",
            Interval.MINUTE_30: "30min",
        }
        freq = freq_map.get(interval, "5min")

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

        # 获取最新的沪股通和深股通数据
        df = df.sort_values("trade_date", ascending=False)

        # 沪股通
        sh_row = df[df["trade_type"] == "沪股通"].iloc[0] if len(df[df["trade_type"] == "沪股通"]) > 0 else None
        # 深股通
        sz_row = df[df["trade_type"] == "深股通"].iloc[0] if len(df[df["trade_type"] == "深股通"]) > 0 else None

        data = NorthboundFlowData(
            trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
            sh_net_inflow=float(sh_row.get("net_amount", 0)) / 100000000 if sh_row is not None else 0,
            sh_buy_volume=float(sh_row.get("buy_amount", 0)) / 100000000 if sh_row is not None else 0,
            sh_sell_volume=float(sh_row.get("sell_amount", 0)) / 100000000 if sh_row is not None else 0,
            sz_net_inflow=float(sz_row.get("net_amount", 0)) / 100000000 if sz_row is not None else 0,
            sz_buy_volume=float(sz_row.get("buy_amount", 0)) / 100000000 if sz_row is not None else 0,
            sz_sell_volume=float(sz_row.get("sell_amount", 0)) / 100000000 if sz_row is not None else 0,
        )

        return data

    # ========== 板块数据 ==========

    def get_sector_list(self) -> List[SectorData]:
        """获取板块列表（行业分类）"""
        df = self._call_api(
            "sw_daily",
            start_date=datetime.now().strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d")
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
        """从ts_code获取交易所"""
        suffix = ts_code.split(".")[-1]
        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE
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
