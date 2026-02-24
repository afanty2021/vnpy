# REQ-003 A股数据服务模块 - 详细实现方案

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-003
> 模块名称：vnpy_china_data
> 预计工时：6人天
>
> **变更记录**:
> - v1.1: 添加Tushare完整API调用实现和QMT实时行情订阅详细设计
> - v1.0: 初始版本

---

## 1. 模块概述

### 1.1 核心职责

vnpy_china_data是A股交易系统的**唯一数据源**，负责：

1. 整合QMT实时数据和Tushare离线数据
2. 实现标准数据接口（IDataProvider系列）
3. 提供高性能缓存机制
4. 支持增量数据更新

### 1.2 模块定位

```
vnpy_china_data
├── 职责：数据获取、存储、缓存
├── 依赖：QMT网关、Tushare API、MySQL、Redis
├── 被依赖：所有其他A股模块
└── 实现：IDataProvider, IDragonTigerProvider, INorthboundProvider等接口
```

---

## 2. 目录结构

```
vnpy_china_data/
├── __init__.py                 # 模块初始化，导出主要类
├── service.py                  # 数据服务主类（核心）
├── cache.py                    # Redis缓存管理
├── database.py                 # MySQL数据库操作层
├── limiter.py                  # API限流器（新增）
├── validator.py                # 数据验证器
├── adapter/                    # 数据适配器
│   ├── __init__.py
│   ├── base.py                # 适配器基类
│   ├── tushare_adapter.py     # Tushare数据适配器
│   ├── qmt_adapter.py         # QMT数据适配器
│   └── composite_adapter.py   # 组合适配器
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── stock_info.py          # 股票信息模型
│   ├── financial_data.py      # 财务数据模型
│   ├── dragon_tiger.py        # 龙虎榜数据模型
│   ├── northbound.py          # 北向资金数据模型
│   └── sector.py              # 板块数据模型
├── updater/                    # 数据更新器
│   ├── __init__.py
│   ├── base_updater.py        # 更新器基类
│   ├── daily_updater.py       # 日线数据更新
│   ├── info_updater.py        # 信息数据更新
│   └── scheduler.py           # 定时调度
└── config.py                   # 配置项
```

---

## 3. 核心类实现

### 3.1 数据服务主类（ChinaDataService）

```python
"""
vnpy_china_data/service.py
"""
数据服务主类 - 实现 IDataProvider 及相关接口
"""
from typing import List, Optional, Dict
from datetime import datetime, date
import threading
from pathlib import Path

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import BaseDatabase

from vnpy_china_interface import (
    IDataProvider,
    IDragonTigerProvider,
    INorthboundProvider,
    ISectorProvider,
    DragonTigerData,
    NorthboundFlowData,
    SectorData
)
from vnpy_china_config import ConfigManager, DataModuleConfig
from .cache import DataQueryCache
from .database import MySQLDatabaseLayer
from .adapter import TushareDataAdapter, QMTDataAdapter


class ChinaDataService(IDataProvider, IDragonTigerProvider,
                        INorthboundProvider, ISectorProvider):
    """
    A股数据服务主类

    实现多个数据接口：
    - IDataProvider: 基础行情数据
    - IDragonTigerProvider: 龙虎榜数据
    - INorthboundProvider: 北向资金数据
    - ISectorProvider: 板块数据
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 获取配置
        config_manager = ConfigManager()
        self.config: DataModuleConfig = config_manager.get_config("data")

        # 初始化组件
        self.cache = DataQueryCache(
            host=self.config.database.redis_host,
            port=self.config.database.redis_port
        )
        self.database = MySQLDatabaseLayer(
            host=self.config.database.mysql_host,
            port=self.config.database.mysql_port,
            user=self.config.database.mysql_user,
            password=self.config.database.mysql_password,
            database=self.config.database.mysql_database
        )
        self.tushare_adapter = TushareDataAdapter(
            token=self.config.tushare_token,
            rate_limit=self.config.tushare_rate_limit
        )
        self.qmt_adapter = QMTDataAdapter(
            path=self.config.qmt_path,
            account_id=self.config.qmt_account_id
        )

        # 运行状态
        self.connected = False

    def connect(self) -> bool:
        """连接数据源"""
        try:
            # 连接MySQL
            self.database.connect()

            # 连接Redis
            self.cache.connect()

            # 连接QMT
            self.qmt_adapter.connect()

            self.connected = True
            return True
        except Exception as e:
            print(f"数据服务连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self.database.close()
        self.cache.close()
        self.qmt_adapter.disconnect()
        self.connected = False

    # ========== IDataProvider 接口实现 ==========

    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """
        获取K线数据

        查询优先级：缓存 → 数据库 → API
        """
        # 1. 尝试从缓存获取
        cache_key = f"bar_{symbol}_{exchange}_{interval}_{start}_{end}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # 2. 尝试从数据库获取
        db_data = self.database.load_bar_data(symbol, exchange, interval, start, end)
        if db_data:
            self.cache.set(cache_key, db_data, ttl=self.config.cache_bar_ttl)
            return db_data

        # 3. 从API获取并存储
        api_data = self._fetch_bars_from_api(symbol, exchange, interval, start, end)
        if api_data:
            self.database.save_bar_data(api_data)
            self.cache.set(cache_key, api_data, ttl=self.config.cache_bar_ttl)
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

        if interval in [Interval.MINUTE_1, Interval.MINUTE_5, Interval.MINUTE_15, Interval.MINUTE_30]:
            # 分钟线：优先使用QMT
            if self.qmt_adapter.connected:
                return self.qmt_adapter.get_minute_bars(ts_code, start, end, interval)
            else:
                return self.tushare_adapter.get_minute_bars(ts_code, start, end, interval)
        else:
            # 日线及以上：使用Tushare
            return self.tushare_adapter.get_daily_bars(ts_code, start, end)

    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """获取Tick数据"""
        # Tick数据只从QMT获取
        return self.qmt_adapter.get_tick_data(symbol, start, end)

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
            self.cache.set(cache_key, info, ttl=self.config.cache_info_ttl)
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
        data = self.tushare_adapter.get_financial_data(symbol, report_date)
        if data:
            self.cache.set(cache_key, data, ttl=self.config.cache_info_ttl)
        return data

    def subscribe_quote(self, symbols: List[str]) -> bool:
        """订阅实时行情"""
        return self.qmt_adapter.subscribe(symbols)

    # ========== IDragonTigerProvider 接口实现 ==========

    def get_dragon_tiger_data(
        self,
        trade_date: date
    ) -> List[DragonTigerData]:
        """获取指定日期的龙虎榜数据"""
        # 尝试从缓存获取
        cache_key = f"dragon_tiger_{trade_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 从Tushare获取
        data = self.tushare_adapter.get_dragon_tiger_data(trade_date)
        if data:
            # 缓存7天
            self.cache.set(cache_key, data, ttl=7*86400)
        return data

    def get_institution_rank(
        self,
        trade_date: date,
        top_n: int = 10
    ) -> List[DragonTigerData]:
        """获取机构排名"""
        data = self.get_dragon_tiger_data(trade_date)
        # 按机构净买入排序
        return sorted(data, key=lambda x: x.institution_net_buy, reverse=True)[:top_n]

    # ========== INorthboundProvider 接口实现 ==========

    def get_northbound_flow(
        self,
        trade_date: date
    ) -> Optional[NorthboundFlowData]:
        """获取北向资金流向"""
        # 尝试从缓存获取
        cache_key = f"northbound_{trade_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 从Tushare获取
        data = self.tushare_adapter.get_northbound_flow(trade_date)
        if data:
            # 缓存1天
            self.cache.set(cache_key, data, ttl=86400)
        return data

    def get_stock_holding_change(
        self,
        symbol: str,
        days: int = 5
    ) -> Dict[str, float]:
        """获取个股持股变化"""
        return self.tushare_adapter.get_holding_change(symbol, days)

    # ========== ISectorProvider 接口实现 ==========

    def get_sector_list(self) -> List[SectorData]:
        """获取板块列表"""
        # 尝试从缓存获取
        cache_key = "sector_list"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 从Tushare获取
        data = self.tushare_adapter.get_sector_list()
        if data:
            # 缓存1天
            self.cache.set(cache_key, data, ttl=86400)
        return data

    def get_sector_stocks(self, sector_code: str) -> List[str]:
        """获取板块成分股"""
        return self.tushare_adapter.get_sector_stocks(sector_code)

    def get_sector_index(
        self,
        sector_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取板块指数数据"""
        return self.tushare_adapter.get_sector_index(
            sector_code, start_date, end_date
        )

    # ========== 工具方法 ==========

    def _convert_to_ts_code(self, symbol: str, exchange: Exchange) -> str:
        """转换symbol为tushare格式"""
        suffix_map = {
            Exchange.SSE: "SH",
            Exchange.SZSE: "SZ",
            Exchange.BSE: "BJ"
        }
        suffix = suffix_map.get(exchange, "")
        return f"{symbol}.{suffix}"

    def _convert_from_ts_code(self, ts_code: str) -> tuple:
        """从tushare格式转换为(symbol, exchange)"""
        symbol, suffix = ts_code.split(".")

        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE
        }
        exchange = exchange_map.get(suffix, Exchange.SZSE)

        return symbol, exchange
```

---

## 4. 缓存管理实现

```python
"""
vnpy_china_data/cache.py
"""
Redis缓存管理
"""
import redis
import json
from typing import Any, Optional
from datetime import timedelta, datetime


class DataQueryCache:
    """数据查询缓存"""

    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: str = ""):
        """
        初始化Redis缓存

        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库编号
            password: 密码
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )

        # 默认TTL配置
        self.default_ttl = timedelta(hours=1)

    def connect(self) -> bool:
        """连接Redis"""
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    def close(self):
        """关闭连接"""
        self.redis_client.close()

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，不存在返回None
        """
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示使用默认值

        Returns:
            是否设置成功
        """
        try:
            ttl = ttl or int(self.default_ttl.total_seconds())
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            return self.redis_client.setex(key, ttl, serialized) == "OK"
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return self.redis_client.delete(key) > 0
        except Exception:
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配的所有缓存

        Args:
            pattern: 键模式（如：bar_*）

        Returns:
            删除的键数量
        """
        try:
            keys = self.redis_client.keys(f"{pattern}*")
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception:
            return 0

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            return self.redis_client.exists(key) > 0
        except Exception:
            return False
```

---

## 5. 数据库操作层实现

```python
"""
vnpy_china_data/database.py
"""
MySQL数据库操作层
"""
import pymysql
from typing import List, Optional
from datetime import datetime
from contextlib import contextmanager

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval


class MySQLDatabaseLayer:
    """MySQL数据库层"""

    def __init__(self, host: str, port: int, user: str,
                 password: str, database: str):
        """
        初始化数据库连接

        Args:
            host: 数据库主机
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
        """
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4"
        }
        self.connection = None

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()

    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(**self.config)
            return True
        except Exception:
            return False

    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()

    def save_bar_data(self, bars: List[BarData]) -> bool:
        """
        批量保存K线数据

        Args:
            bars: K线数据列表

        Returns:
            是否保存成功
        """
        if not bars:
            return True

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 批量插入SQL
                sql = """
                INSERT INTO db_bar_data
                (symbol, exchange, interval, datetime, open_price, high_price,
                 low_price, close_price, volume, turnover)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    turnover = VALUES(turnover)
                """

                # 准备数据
                values = []
                for bar in bars:
                    values.append((
                        bar.symbol,
                        bar.exchange.value,
                        bar.interval.value,
                        bar.datetime,
                        bar.open_price,
                        bar.high_price,
                        bar.low_price,
                        bar.close_price,
                        bar.volume,
                        bar.turnover
                    ))

                cursor.executemany(sql, values)
                conn.commit()
                return True

        except Exception as e:
            print(f"保存K线数据失败: {e}")
            return False

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """
        加载K线数据

        Returns:
            K线数据列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = """
                SELECT symbol, exchange, interval, datetime,
                       open_price, high_price, low_price, close_price,
                       volume, turnover
                FROM db_bar_data
                WHERE symbol = %s
                  AND exchange = %s
                  AND interval = %s
                  AND datetime >= %s
                  AND datetime <= %s
                ORDER BY datetime ASC
                """

                cursor.execute(sql, (
                    symbol, exchange.value, interval.value,
                    start, end
                ))

                results = cursor.fetchall()

                # 转换为BarData对象
                bars = []
                for row in results:
                    bars.append(BarData(
                        symbol=row[0],
                        exchange=Exchange(row[1]),
                        interval=Interval(row[2]),
                        datetime=row[3],
                        open_price=row[4],
                        high_price=row[5],
                        low_price=row[6],
                        close_price=row[7],
                        volume=row[8],
                        turnover=row[9]
                    ))

                return bars

        except Exception as e:
            print(f"加载K线数据失败: {e}")
            return []

    def get_latest_date(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> Optional[datetime]:
        """获取指定合约的最新数据日期"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = """
                SELECT MAX(datetime) as latest_date
                FROM db_bar_data
                WHERE symbol = %s
                  AND exchange = %s
                  AND interval = %s
                """

                cursor.execute(sql, (symbol, exchange.value, interval.value))
                result = cursor.fetchone()

                if result and result[0]:
                    return result[0]
                return None

        except Exception:
            return None
```

---

## 6. Tushare适配器实现

```python
"""
vnpy_china_data/adapter/tushare_adapter.py
"""
Tushare数据适配器 - 支持限流和重试
"""
import tushare as ts
import pandas as pd
import time
from typing import List, Optional, Dict
from datetime import datetime, date

from .limiter import TushareRateLimiter
from ..models.dragon_tiger import DragonTigerData
from ..models.northbound import NorthboundFlowData


class TushareDataAdapter:
    """Tushare数据适配器"""

    def __init__(self, token: str, rate_limit: int = 200):
        """
        初始化Tushare适配器

        Args:
            token: Tushare Token
            rate_limit: 每分钟调用次数限制
        """
        self.pro = ts.pro_api(token)
        self.rate_limiter = TushareRateLimiter(
            max_calls=rate_limit,
            period=60  # 60秒
        )

    def _call_with_limit(self, api_name: str, **kwargs):
        """
        带限流的API调用

        Args:
            api_name: API方法名
            **kwargs: API参数

        Returns:
            API返回结果
        """
        # 等待限流器
        while not self.rate_limiter.acquire():
            time.sleep(0.1)

        # 调用API
        api_method = getattr(self.pro, api_name)
        return api_method(**kwargs)

    def get_daily_bars(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取日线数据"""
        df = self._call_with_limit(
            "daily",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        # 转换为BarData列表
        bars = []
        for _, row in df.iterrows():
            bars.append(BarData(
                symbol=row["ts_code"].split(".")[0],
                exchange=self._get_exchange(row["ts_code"]),
                interval=Interval.DAILY,
                datetime=pd.to_datetime(row["trade_date"]),
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"],
                volume=row["vol"],
                turnover=row.get("amount", 0)
            ))

        return bars

    def get_minute_bars(
        self,
        ts_code: str,
        start_time: str,
        end_time: str,
        freq: str = "5min"
    ) -> List[BarData]:
        """获取分钟线数据"""
        # Tushare分钟线需要高级权限
        try:
            df = self._call_with_limit(
                "stk_mins",
                ts_code=ts_code,
                start_time=start_time,
                end_time=end_time,
                freq=freq
            )

            if df.empty:
                return []

            # 转换...
            return self._convert_df_to_bars(df, freq)

        except AttributeError:
            print("Tushare分钟线需要高级权限")
            return []

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """获取股票基本信息"""
        df = self._call_with_limit(
            "stock_basic",
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,list_date'
        )

        if df.empty:
            return None

        # 查找对应股票
        ts_code = self._symbol_to_ts_code(symbol)
        row = df[df["ts_code"] == ts_code]

        if row.empty:
            return None

        row = row.iloc[0]
        return {
            "symbol": row["symbol"],
            "name": row["name"],
            "exchange": self._get_exchange(row["ts_code"]),
            "industry": row.get("industry", ""),
            "area": row.get("area", ""),
            "list_date": row.get("list_date", ""),
            "is_st": self._is_st(row["name"])
        }

    def get_financial_data(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict]:
        """获取财务数据"""
        ts_code = self._symbol_to_ts_code(symbol)

        df = self._call_with_limit(
            "fina_indicator",
            ts_code=ts_code,
            period=report_date,
            report_type="1"
        )

        if df.empty:
            return None

        row = df.iloc[0]
        return {
            "symbol": symbol,
            "report_date": row["end_date"],
            "pe_ratio": row.get("pe", 0),
            "pb_ratio": row.get("pb", 0),
            "roe": row.get("roe", 0),
            "roa": row.get("roa", 0),
            "gross_margin": row.get("grossprofit_margin", 0),
            "net_margin": row.get("netprofit_margin", 0),
            "revenue": row.get("revenue", 0),
            "net_profit": row.get("net_profit", 0)
        }

    def get_dragon_tiger_data(
        self,
        trade_date: str
    ) -> List[DragonTigerData]:
        """获取龙虎榜数据"""
        df = self._call_with_limit(
            "top_list",
            date=trade_date
        )

        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            results.append(DragonTigerData(
                symbol=row["ts_code"].split(".")[0],
                trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
                close_price=row.get("close", 0),
                change_pct=row.get("pct_chg", 0),
                institution_net_buy=row.get("amount_buy", 0) - row.get("amount_sell", 0),
                broker_net_buy=0,  # 需要额外计算
                buy_ratio=row.get("buy_ratio", 0) / 10000,
                sell_ratio=row.get("sell_ratio", 0) / 10000,
                buy_brokers=[],
                sell_brokers=[]
            ))

        return results

    def get_northbound_flow(
        self,
        trade_date: str
    ) -> Optional[NorthboundFlowData]:
        """获取北向资金流向"""
        df = self._call_with_limit(
            "moneyflow_hsgt",
            trade_date=trade_date
        )

        if df.empty:
            return None

        df = df.sort_values("trade_date", ascending=False)
        row = df.iloc[0]

        return NorthboundFlowData(
            trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
            net_inflow=row.get("ggt_ss", 0) / 100000000,  # 转为亿元
            buy_volume=row.get("ggt_buy", 0) / 100000000,
            sell_volume=row.get("ggt_sell", 0) / 100000000,
            holding_changes={}
        )

    def _get_exchange(self, ts_code: str) -> Exchange:
        """从ts_code获取交易所"""
        suffix = ts_code.split(".")[-1]
        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE
        }
        return exchange_map.get(suffix, Exchange.SZSE)

    def _symbol_to_ts_code(self, symbol: str) -> str:
        """symbol转ts_code格式"""
        # 简化实现，实际需要维护映射表
        if symbol.startswith("6"):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"

    def _is_st(self, name: str) -> bool:
        """判断是否ST股票"""
        return "ST" in name or "st" in name

    # ==================== 完整Tushare API调用实现 ====================

    def get_stock_list(self, list_status: str = "L") -> List[Dict]:
        """
        获取股票列表

        Args:
            list_status: 上市状态 L上市 D退市 P暂停上市
        """
        df = self._call_with_limit(
            "stock_basic",
            exchange='',
            list_status=list_status,
            fields='ts_code,symbol,name,area,industry,market,list_date'
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_daily_bars_pro(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        adj: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取日线数据（pro_bar接口，支持复权）

        Args:
            ts_code: 股票代码（如 000001.SZ）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            adj: 复权类型 None不复权 qfq前复权 hfq后复权

        Returns:
            DataFrame with columns: ts_code, trade_date, open, high, low, close, vol, amount
        """
        try:
            df = self._call_with_limit(
                "pro_bar",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                adj=adj,
                freq="D"
            )
            return df
        except Exception as e:
            print(f"获取日线数据失败: {e}")
            return pd.DataFrame()

    def get_adj_factor(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取复权因子

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            复权因子数据
        """
        try:
            df = self._call_with_limit(
                "adj_factor",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception:
            return pd.DataFrame()

    def get_income_statement(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        report_type: str = "1"
    ) -> List[Dict]:
        """
        获取利润表数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            report_type: 报告类型 1合并报表 2单季合并 3调整单季表 4调整合并表 5调整前合并表
        """
        df = self._call_with_limit(
            "income",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_balance_sheet(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        report_type: str = "1"
    ) -> List[Dict]:
        """
        获取资产负债表数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            report_type: 报告类型
        """
        df = self._call_with_limit(
            "balancesheet",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_cash_flow(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        report_type: str = "1"
    ) -> List[Dict]:
        """
        获取现金流量表数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            report_type: 报告类型
        """
        df = self._call_with_limit(
            "cashflow",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_financial_indicator(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        获取财务指标数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        """
        df = self._call_with_limit(
            "fina_indicator",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_dragon_tiger_list(
        self,
        trade_date: str
    ) -> List[DragonTigerData]:
        """
        获取龙虎榜每日数据

        Args:
            trade_date: 交易日期 YYYYMMDD
        """
        df = self._call_with_limit(
            "top_list",
            date=trade_date
        )

        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            results.append(DragonTigerData(
                symbol=row["ts_code"].split(".")[0],
                trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
                close_price=row.get("close", 0),
                change_pct=row.get("pct_chg", 0),
                institution_net_buy=row.get("amount_buy", 0) - row.get("amount_sell", 0),
                broker_net_buy=0,
                buy_ratio=row.get("buy_ratio", 0) / 10000,
                sell_ratio=row.get("sell_ratio", 0) / 10000,
                buy_brokers=[],
                sell_brokers=[]
            ))

        return results

    def get_dragon_tiger_detail(
        self,
        ts_code: str,
        trade_date: str
    ) -> Dict:
        """
        获取龙虎榜明细数据

        Args:
            ts_code: 股票代码
            trade_date: 交易日期
        """
        df = self._call_with_limit(
            "top_inst",
            date=trade_date,
            ts_code=ts_code
        )

        if df.empty:
            return {}

        # 分类统计
        buy_brokers = []
        sell_brokers = []
        institution_net_buy = 0

        for _, row in df.iterrows():
            exalter = row.get("exalter", "")
            amount = row.get("amount_buy", 0) - row.get("amount_sell", 0)

            if "机构" in exalter:
                institution_net_buy += amount

            if amount > 0:
                buy_brokers.append(exalter)
            else:
                sell_brokers.append(exalter)

        return {
            "buy_brokers": buy_brokers,
            "sell_brokers": sell_brokers,
            "institution_net_buy": institution_net_buy
        }

    def get_northbound_flow_detail(
        self,
        trade_date: str
    ) -> Optional[NorthboundFlowData]:
        """
        获取北向资金流向详情

        Args:
            trade_date: 交易日期 YYYYMMDD

        Returns:
            北向资金流向数据
        """
        df = self._call_with_limit(
            "moneyflow_hsgt",
            trade_date=trade_date
        )

        if df.empty:
            return None

        df = df.sort_values("trade_date", ascending=False)
        row = df.iloc[0]

        return NorthboundFlowData(
            trade_date=datetime.strptime(trade_date, "%Y%m%d").date(),
            net_inflow=row.get("ggt_ss", 0) / 100000000,  # 转为亿元
            buy_volume=row.get("ggt_buy", 0) / 100000000,
            sell_volume=row.get("ggt_sell", 0) / 100000000,
            holding_changes={}
        )

    def get_northbound_holding(
        self,
        trade_date: str,
        ts_code: Optional[str] = None
    ) -> List[Dict]:
        """
        获取北向持股数据

        Args:
            trade_date: 交易日期
            ts_code: 股票代码（可选，不指定则返回所有）

        Returns:
            持股数据列表
        """
        params = {"trade_date": trade_date}
        if ts_code:
            params["ts_code"] = ts_code

        df = self._call_with_limit("hk_hold", **params)

        if df.empty:
            return []

        return df.to_dict('records')

    def get_index_classify(
        self,
        level: str = "L1",
        src: str = "SW"
    ) -> List[Dict]:
        """
        获取行业分类

        Args:
            level: 行业级别 L1一级行业 L2二级行业 L3三级行业
            src: 分类来源 SW申万 ZZZS中证

        Returns:
            行业分类列表
        """
        df = self._call_with_limit(
            "index_classify",
            level=level,
            src=src
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_index_member(
        self,
        index_code: str
    ) -> List[Dict]:
        """
        获取指数成分股

        Args:
            index_code: 指数代码（如 801010.SI）

        Returns:
            成分股列表
        """
        df = self._call_with_limit(
            "index_member",
            index_code=index_code
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_concept_stocks(
        self,
        concept_id: Optional[str] = None
    ) -> List[Dict]:
        """
        获取概念板块成分股

        Args:
            concept_id: 概念ID（可选）

        Returns:
            概念股列表
        """
        params = {}
        if concept_id:
            params["id"] = concept_id

        df = self._call_with_limit("concept_detail", **params)

        if df.empty:
            return []

        return df.to_dict('records')

    def get_limit_stocks(
        self,
        trade_date: str,
        limit_type: str = "U"
    ) -> List[Dict]:
        """
        获取涨跌停股票

        Args:
            trade_date: 交易日期
            limit_type: 类型 U涨停 D跌停

        Returns:
            涨跌停股票列表
        """
        df = self._call_with_limit(
            "limit_list",
            trade_date=trade_date,
            limit_type=limit_type
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_new_stocks(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        获取新股数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            新股列表
        """
        df = self._call_with_limit(
            "new_share",
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_margin_trade_stocks(
        self,
        trade_date: str
    ) -> List[Dict]:
        """
        获取融资融券标的

        Args:
            trade_date: 交易日期

        Returns:
            融资融券股票列表
        """
        df = self._call_with_limit(
            "margin",
            trade_date=trade_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_margin_trade_detail(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        获取融资融券明细

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            融资融券明细
        """
        df = self._call_with_limit(
            "margin_detail",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_stock_name_change(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        获取股票更名数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        """
        df = self._call_with_limit(
            "namechange",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')

    def get_stock_company(
        self,
        ts_code: str
    ) -> Optional[Dict]:
        """
        获取上市公司基本信息

        Args:
            ts_code: 股票代码
        """
        df = self._call_with_limit(
            "stock_company",
            ts_code=ts_code,
            fields='ts_code,chairman,manager,secretary,reg_capital,setup_date,province,city,introduction,website,email,office,employees,main_business,business_scope'
        )

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    def get_daily_quota(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        获取每日资金额度

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        df = self._call_with_limit(
            "hk_quota",
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        return df.to_dict('records')
```

---

## 7. QMT适配器实现（实时行情订阅）

```python
"""
vnpy_china_data/adapter/qmt_adapter.py
"""
QMT数据适配器 - 实时行情订阅与Tick数据获取
"""
from typing import List, Dict, Callable, Optional, Set
from datetime import datetime, time
from threading import Thread, Event
import time as time_module
from collections import defaultdict

from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.event import EVENT_TICK, EVENT_CONTRACT
from vnpy.event import EventEngine

from vnpy_qmt.qmt_gateway import QmtGateway, QmtMdApi


class QMTDataAdapter:
    """QMT数据适配器 - 支持实时行情订阅"""

    def __init__(
        self,
        qmt_path: str,
        event_engine: Optional[EventEngine] = None
    ):
        """
        初始化QMT适配器

        Args:
            qmt_path: QMT Mini路径（如 D:/国金证券QMT交易端/userdata_mini）
            event_engine: VeighNa事件引擎（可选）
        """
        self.qmt_path = qmt_path
        self.event_engine = event_engine or EventEngine()

        # QMT网关
        self.gateway: Optional[QmtGateway] = None

        # 订阅管理
        self.subscribed_symbols: Set[str] = set()
        self.symbol_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # Tick数据缓存
        self.tick_cache: Dict[str, TickData] = {}

        # 连接状态
        self.connected: bool = False
        self._stop_event = Event()
        self._reconnect_thread: Optional[Thread] = None

        # 统计信息
        self.tick_count = 0
        self.last_tick_time: Optional[datetime] = None

    def connect(self) -> bool:
        """
        连接QMT网关

        Returns:
            是否连接成功
        """
        try:
            # 创建QMT网关
            self.gateway = QmtGateway()

            # 设置回调
            if hasattr(self.gateway, 'on_tick'):
                self.gateway.on_tick = self._on_qmt_tick

            # 连接
            self.gateway.connect(
                qmt_path=self.qmt_path,
                session_id=1
            )

            # 启动重连线程
            self._start_reconnect_thread()

            self.connected = True
            return True

        except Exception as e:
            print(f"QMT连接失败: {e}")
            return False

    def disconnect(self):
        """断开QMT连接"""
        self._stop_event.set()

        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=5)

        if self.gateway:
            self.gateway.close()

        self.connected = False
        self.subscribed_symbols.clear()

    def subscribe(
        self,
        symbol: str,
        exchange: Exchange,
        callback: Optional[Callable[[TickData], None]] = None
    ):
        """
        订阅实时行情

        Args:
            symbol: 股票代码
            exchange: 交易所
            callback: 回调函数（可选）
        """
        vt_symbol = f"{symbol}.{exchange.value}"

        # 添加到订阅列表
        self.subscribed_symbols.add(vt_symbol)

        # 注册回调
        if callback:
            self.symbol_callbacks[vt_symbol].append(callback)

        # 调用QMT订阅
        if self.gateway and self.connected:
            req = {
                "symbol": symbol,
                "exchange": exchange
            }
            self.gateway.subscribe(req)

    def unsubscribe(
        self,
        symbol: str,
        exchange: Exchange
    ):
        """
        取消订阅

        Args:
            symbol: 股票代码
            exchange: 交易所
        """
        vt_symbol = f"{symbol}.{exchange.value}"

        if vt_symbol in self.subscribed_symbols:
            self.subscribed_symbols.remove(vt_symbol)
            self.symbol_callbacks.pop(vt_symbol, None)

        # 调用QMT取消订阅
        if self.gateway and self.connected:
            # QMT可能不支持取消订阅
            pass

    def get_realtime_tick(
        self,
        symbol: str,
        exchange: Exchange
    ) -> Optional[TickData]:
        """
        获取最新Tick数据

        Args:
            symbol: 股票代码
            exchange: 交易所

        Returns:
            最新的Tick数据
        """
        vt_symbol = f"{symbol}.{exchange.value}"

        if vt_symbol in self.tick_cache:
            # 检查数据时效性（5秒内）
            tick = self.tick_cache[vt_symbol]
            if (datetime.now() - tick.datetime).total_seconds() < 5:
                return tick

        # 如果没有缓存或过期，从QMT获取
        if self.gateway and self.connected:
            return self._fetch_tick_from_qmt(symbol, exchange)

        return None

    def get_realtime_bars(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        count: int = 100
    ) -> List[BarData]:
        """
        获取实时K线数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期
            count: 数量

        Returns:
            K线数据列表
        """
        if self.gateway and self.connected:
            req = {
                "symbol": symbol,
                "exchange": exchange,
                "interval": interval,
                "start": None,
                "end": None
            }

            # 调用QMT网关查询历史数据
            bars = self.gateway.query_history(req, count)
            return bars

        return []

    def subscribe_market_data(
        self,
        symbols: List[tuple],
        callback: Optional[Callable[[TickData], None]] = None
    ):
        """
        批量订阅行情

        Args:
            symbols: [(symbol, exchange), ...] 列表
            callback: 统一回调函数（可选）
        """
        for symbol, exchange in symbols:
            self.subscribe(symbol, exchange, callback)

    def get_subscribed_symbols(self) -> List[str]:
        """获取已订阅的股票列表"""
        return list(self.subscribed_symbols)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "connected": self.connected,
            "subscribed_count": len(self.subscribed_symbols),
            "tick_count": self.tick_count,
            "last_tick_time": self.last_tick_time
        }

    # ==================== 内部方法 ====================

    def _on_qmt_tick(self, tick: TickData):
        """
        QMT Tick数据回调

        Args:
            tick: Tick数据
        """
        # 更新缓存
        vt_symbol = tick.vt_symbol
        self.tick_cache[vt_symbol] = tick

        # 更新统计
        self.tick_count += 1
        self.last_tick_time = datetime.now()

        # 触发VeighNa事件
        if self.event_engine:
            from vnpy.event import Event
            event = Event(EVENT_TICK, tick)
            self.event_engine.put(event)

        # 调用注册的回调
        if vt_symbol in self.symbol_callbacks:
            for callback in self.symbol_callbacks[vt_symbol]:
                try:
                    callback(tick)
                except Exception as e:
                    print(f"Tick回调错误: {e}")

    def _fetch_tick_from_qmt(
        self,
        symbol: str,
        exchange: Exchange
    ) -> Optional[TickData]:
        """从QMT获取Tick数据"""
        # 这里需要根据QMT API实现
        # 通常是调用QMT MdApi的查询接口
        pass

    def _start_reconnect_thread(self):
        """启动重连线程"""
        self._reconnect_thread = Thread(
            target=self._reconnect_loop,
            daemon=True
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self):
        """重连循环"""
        while not self._stop_event.is_set():
            time_module.sleep(30)  # 每30秒检查一次

            if not self.connected:
                print("QMT未连接，尝试重连...")
                self.connect()

            # 检查订阅状态
            if self.connected and self.gateway:
                for vt_symbol in list(self.subscribed_symbols):
                    symbol, exchange_str = vt_symbol.split('.')
                    # 重新订阅
                    try:
                        self.gateway.subscribe({
                            "symbol": symbol,
                            "exchange": Exchange(exchange_str)
                        })
                    except Exception as e:
                        print(f"重新订阅失败 {vt_symbol}: {e}")


class QMTRealtimeBarGenerator:
    """QMT实时K线生成器"""

    def __init__(self, interval: Interval = Interval.MINUTE):
        """
        初始化

        Args:
            interval: K线周期
        """
        self.interval = interval
        self.bar_buffer: Dict[str, dict] = defaultdict(self._create_bar_buffer)

    def _create_bar_buffer(self) -> dict:
        """创建K线缓冲区"""
        return {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": 0,
            "turnover": 0,
            "datetime": None
        }

    def on_tick(self, tick: TickData) -> Optional[BarData]:
        """
        处理Tick数据，生成K线

        Args:
            tick: Tick数据

        Returns:
            如果K线完成则返回K线数据
        """
        vt_symbol = tick.vt_symbol
        buffer = self.bar_buffer[vt_symbol]

        # 判断是否切换到新的K线周期
        bar_datetime = self._get_bar_datetime(tick.datetime)

        if buffer["datetime"] is None:
            buffer["datetime"] = bar_datetime
        elif buffer["datetime"] != bar_datetime:
            # 新周期，返回完成的K线
            bar = self._create_bar(vt_symbol, buffer)
            # 重置缓冲区
            self.bar_buffer[vt_symbol] = self._create_bar_buffer()
            buffer = self.bar_buffer[vt_symbol]
            buffer["datetime"] = bar_datetime

        # 更新K线数据
        if buffer["open"] is None:
            buffer["open"] = tick.last_price
            buffer["high"] = tick.last_price
            buffer["low"] = tick.last_price
        else:
            buffer["high"] = max(buffer["high"], tick.last_price)
            buffer["low"] = min(buffer["low"], tick.last_price)

        buffer["close"] = tick.last_price
        buffer["volume"] += tick.volume
        buffer["turnover"] += tick.turnover

        return None

    def _get_bar_datetime(self, tick_time: datetime) -> datetime:
        """根据周期获取K线时间"""
        if self.interval == Interval.MINUTE:
            return tick_time.replace(second=0, microsecond=0)
        elif self.interval == Interval.HOUR:
            return tick_time.replace(minute=0, second=0, microsecond=0)
        elif self.interval == Interval.DAILY:
            return tick_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return tick_time

    def _create_bar(self, vt_symbol: str, buffer: dict) -> BarData:
        """创建K线对象"""
        symbol, exchange_str = vt_symbol.split('.')

        return BarData(
            symbol=symbol,
            exchange=Exchange(exchange_str),
            interval=self.interval,
            datetime=buffer["datetime"],
            open_price=buffer["open"],
            high_price=buffer["high"],
            low_price=buffer["low"],
            close_price=buffer["close"],
            volume=buffer["volume"],
            turnover=buffer["turnover"]
        )


class QMTOrderBookMonitor:
    """QMT订单簿监控"""

    def __init__(self, qmt_adapter: QMTDataAdapter):
        """
        初始化

        Args:
            qmt_adapter: QMT适配器
        """
        self.qmt_adapter = qmt_adapter
        self.order_books: Dict[str, dict] = {}

    def on_tick(self, tick: TickData):
        """更新订单簿"""
        vt_symbol = tick.vt_symbol

        self.order_books[vt_symbol] = {
            "datetime": tick.datetime,
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

    def get_order_book(self, symbol: str, exchange: Exchange) -> Optional[dict]:
        """获取订单簿"""
        vt_symbol = f"{symbol}.{exchange.value}"
        return self.order_books.get(vt_symbol)

    def get_bid_ask_spread(self, symbol: str, exchange: Exchange) -> Optional[float]:
        """获取买卖价差"""
        order_book = self.get_order_book(symbol, exchange)
        if order_book:
            return order_book["ask_price_1"] - order_book["bid_price_1"]
        return None
```

---

## 8. API限流器实现

```python
"""
vnpy_china_data/limiter.py
"""
API限流器 - 支持令牌桶算法
"""
import time
from collections import deque
from threading import Lock


class TushareRateLimiter:
    """Tushare API限流器"""

    def __init__(self, max_calls: int = 200, period: int = 60):
        """
        初始化限流器

        Args:
            max_calls: 时间周期内最大调用次数
            period: 时间周期（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = Lock()

    def acquire(self) -> bool:
        """
        尝试获取调用许可

        Returns:
            是否可以调用
        """
        with self.lock:
            now = time.time()

            # 清理过期的调用记录
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()

            # 检查是否可以调用
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True

            return False

    def wait_acquire(self, timeout: Optional[float] = None) -> bool:
        """
        等待并获取调用许可

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功获取许可
        """
        start_time = time.time()

        while True:
            if self.acquire():
                return True

            if timeout and (time.time() - start_time) > timeout:
                return False

            time.sleep(0.1)

    def get_available_calls(self) -> int:
        """获取当前可用调用次数"""
        with self.lock:
            now = time.time()
            # 清理过期的调用记录
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()

            return self.max_calls - len(self.calls)

    def get_reset_time(self) -> float:
        """获取限流重置时间（秒）"""
        if not self.calls:
            return 0.0

        with self.lock:
            oldest_call = self.calls[0]
            reset_time = oldest_call + self.period - time.time()
            return max(0.0, reset_time)
```

---

## 8. 数据模型实现

```python
"""
vnpy_china_data/models/dragon_tiger.py
"""
龙虎榜数据模型
"""
from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class DragonTigerData:
    """龙虎榜数据"""

    symbol: str              # 股票代码
    trade_date: date        # 交易日期
    close_price: float      # 收盘价
    change_pct: float       # 涨跌幅（%）

    # 买卖信息
    institution_net_buy: float  # 机构净买入额（元）
    broker_net_buy: float       # 营业部净买入额（元）

    # 买卖占比
    buy_ratio: float           # 买入占比（0-1）
    sell_ratio: float          # 卖出占比（0-1）

    # 席位信息
    buy_brokers: List[str]     # 买入营业部列表
    sell_brokers: List[str]    # 卖出营业部列表

    def is_strong_buy(self) -> bool:
        """是否强势买入（机构净买入）"""
        return self.institution_net_buy > 0 and self.buy_ratio > 0.5

    def is_limit_up(self) -> bool:
        """是否涨停"""
        return self.change_pct >= 9.9 and self.buy_ratio > 0.8
```

---

## 9. 增量更新实现

```python
"""
vnpy_china_data/updater/daily_updater.py
"""
日线数据增量更新器
"""
from datetime import datetime, timedelta
from typing import List
from vnpy.trader.constant import Exchange, Interval

from ..service import ChinaDataService
from ..adapter import TushareDataAdapter


class DailyBarUpdater:
    """日线数据增量更新器"""

    def __init__(self, data_service: ChinaDataService):
        """
        初始化

        Args:
            data_service: 数据服务实例
        """
        self.data_service = data_service
        self.tushare_adapter = TushareDataAdapter(
            token=data_service.config.tushare_token
        )

    def update_all_stocks(self, symbols: List[str]) -> dict:
        """
        更新所有股票的日线数据

        Args:
            symbols: 股票列表

        Returns:
            更新统计
        """
        stats = {
            "total": len(symbols),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        for symbol in symbols:
            try:
                exchange = self._get_exchange(symbol)
                updated = self.update_stock(symbol, exchange)

                if updated > 0:
                    stats["success"] += 1
                    stats["details"].append({
                        "symbol": symbol,
                        "status": "success",
                        "count": updated
                    })
                else:
                    stats["skipped"] += 1
                    stats["details"].append({
                        "symbol": symbol,
                        "status": "skipped",
                        "count": 0
                    })

            except Exception as e:
                stats["failed"] += 1
                stats["details"].append({
                    "symbol": symbol,
                    "status": "failed",
                    "error": str(e)
                })

        return stats

    def update_stock(self, symbol: str, exchange: Exchange) -> int:
        """
        更新单个股票的日线数据

        Args:
            symbol: 股票代码
            exchange: 交易所

        Returns:
            更新的数据条数
        """
        # 获取最新日期
        latest_date = self.data_service.database.get_latest_date(
            symbol, exchange, Interval.DAILY
        )

        # 确定更新范围
        if latest_date:
            start_date = latest_date + timedelta(days=1)
        else:
            start_date = datetime(2015, 1, 1)  # 默认从2015年开始

        end_date = datetime.now()

        # 如果最新数据已是今天，跳过
        if start_date >= end_date:
            return 0

        # 转换日期格式
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        # 从Tushare获取数据
        ts_code = self._symbol_to_ts_code(symbol, exchange)
        df = self.tushare_adapter._call_with_limit(
            "daily",
            ts_code=ts_code,
            start_date=start_str,
            end_date=end_str
        )

        if df.empty:
            return 0

        # 保存到数据库
        bars = self._convert_df_to_bars(df)
        self.data_service.database.save_bar_data(bars)

        return len(bars)

    def update_scheduled(self) -> dict:
        """
        定时更新（在收盘后执行）

        Returns:
            更新统计
        """
        # 获取所有股票列表
        stocks = self.tushare_adapter.get_stock_list()

        # 更新所有股票
        return self.update_all_stocks(stocks)
```

---

## 10. 配置集成

```python
"""
vnpy_china_data/config.py
"""
数据服务配置
"""
from vnpy_china_config import DataModuleConfig


# 导出配置类
__all__ = ["DataModuleConfig", "get_config"]


def get_config() -> DataModuleConfig:
    """获取数据服务配置"""
    from vnpy_china_config import ConfigManager

    config_manager = ConfigManager()
    return config_manager.get_config("data")
```

---

## 11. 测试策略

```python
"""
tests/test_data_service.py
"""
数据服务模块测试
"""
import pytest
from datetime import datetime
from vnpy.trader.constant import Exchange, Interval

from vnpy_china_data.service import ChinaDataService
from vnpy_china_data.models.dragon_tiger import DragonTigerData


class TestChinaDataService:
    """数据服务测试类"""

    @pytest.fixture
    def data_service(self):
        """创建数据服务实例（使用Mock）"""
        # 使用测试配置
        service = ChinaDataService()
        # ... Mock初始化
        return service

    def test_get_bar_data_from_cache(self, data_service):
        """测试从缓存获取K线数据"""
        # 先设置缓存
        # ...

        # 测试缓存命中
        bars = data_service.get_bar_data(
            "000001", Exchange.SZSE, Interval.DAILY,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        )

        assert len(bars) > 0

    def test_get_dragon_tiger_data(self, data_service):
        """测试获取龙虎榜数据"""
        data = data_service.get_dragon_tiger_data(
            datetime(2024, 2, 20).date()
        )

        assert isinstance(data, list)
        # ...

    def test_rate_limiter(self):
        """测试限流器"""
        from vnpy_china_data.limiter import TushareRateLimiter

        limiter = TushareRateLimiter(max_calls=10, period=60)

        # 快速调用10次
        for _ in range(10):
            assert limiter.acquire() == True

        # 第11次应该失败
        assert limiter.acquire() == False
```

---

## 12. 实施步骤

### 第1步：创建基础结构（0.5人天）

```bash
# 创建目录结构
mkdir -p vnpy_china_data/{adapter,models,updater}
touch vnpy_china_data/__init__.py
touch vnpy_china_data/{cache,database,service,limiter,validator,config}.py
touch vnpy_china_data/adapter/__init__.py
touch vnpy_china_data/models/__init__.py
touch vnpy_china_data/updater/__init__.py
```

### 第2步：实现缓存管理（1人天）

- 实现 `DataQueryCache` 类
- 添加Redis连接管理
- 实现get/set/delete方法
- 添加单元测试

### 第3步：实现数据库层（1人天）

- 实现 `MySQLDatabaseLayer` 类
- 创建数据库表结构SQL
- 实现CRUD操作
- 添加批量操作支持

### 第4步：实现Tushare适配器（1.5人天）

- 实现 `TushareDataAdapter` 类
- 实现限流器
- 实现重试机制
- 添加数据转换方法

### 第5步：实现QMT适配器（1人天）

- 实现 `QMTDataAdapter` 类
- 实现实时行情订阅
- 实现Tick数据获取
- 添加连接状态管理

### 第6步：实现数据服务主类（1人天）

- 实现 `ChinaDataService` 类
- 实现所有接口
- 集成缓存和数据库
- 添加连接管理

### 第7步：集成测试（1人天）

- 编写集成测试
- 性能测试
- 与vnpy_china_config集成测试
- 与vnpy_china_interface集成测试

---

## 13. 数据库表结构

```sql
-- K线数据表
CREATE TABLE db_bar_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    datetime DATETIME NOT NULL,
    open_price DECIMAL(10, 2) NOT NULL,
    high_price DECIMAL(10, 2) NOT NULL,
    low_price DECIMAL(10, 2) NOT NULL,
    close_price DECIMAL(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    turnover DECIMAL(20, 2),
    INDEX idx_symbol_exchange (symbol, exchange),
    INDEX idx_datetime (datetime),
    UNIQUE KEY uk_bar (symbol, exchange, interval, datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 股票信息表
CREATE TABLE db_stock_info (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    industry VARCHAR(50),
    area VARCHAR(50),
    list_date DATE,
    is_st TINYINT(1),
    INDEX idx_exchange (exchange),
    INDEX idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 财务数据表
CREATE TABLE db_financial_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    report_date VARCHAR(10) NOT NULL,
    report_type VARCHAR(10) NOT NULL,
    pe_ratio DECIMAL(10, 2),
    pb_ratio DECIMAL(10, 2),
    roe DECIMAL(10, 4),
    roa DECIMAL(10, 4),
    gross_margin DECIMAL(10, 4),
    net_margin DECIMAL(10, 4),
    revenue DECIMAL(20, 2),
    net_profit DECIMAL(20, 2),
    INDEX idx_symbol_date (symbol, report_date),
    UNIQUE KEY uk_financial (symbol, report_date, report_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 14. 关键技术点

### 14.1 数据一致性保证

**问题**: Redis缓存与MySQL数据库可能不一致

**解决方案**:
1. 设置合理的缓存TTL
2. 重要数据更新时主动清除缓存
3. 定期对账缓存和数据库

```python
def save_bar_data_with_cache_invalidate(self, bars):
    """保存K线数据并失效缓存"""
    # 保存到数据库
    self.database.save_bar_data(bars)

    # 清除相关缓存
    for bar in bars:
        cache_key = f"bar_{bar.symbol}_{bar.exchange}_{bar.interval}"
        self.cache.clear_pattern(cache_key)
```

### 14.2 异常处理

```python
def safe_api_call(api_func, *args, **kwargs):
    """安全的API调用（带重试）"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避
    return None
```

### 14.3 性能优化

1. **批量操作**: 批量插入/查询减少数据库访问
2. **异步更新**: 使用独立线程进行数据更新
3. **连接池**: 使用连接池管理数据库连接

---

## 15. 使用示例

### 15.1 基本使用

```python
from vnpy_china_data import ChinaDataService
from vnpy_china_config import ConfigManager, Environment, DataModuleConfig
from datetime import datetime

# 初始化配置
config_manager = ConfigManager()
config_manager.set_environment(Environment.PRODUCTION)

# 加载配置（自动创建默认配置文件）
data_config = config_manager.load_module_config(
    "data",
    DataModuleConfig
)

# 设置Tushare Token
data_config.tushare_token = "your_token_here"
config_manager.save_config("data")

# 创建并连接数据服务
data_service = ChinaDataService()
data_service.connect()

# 获取K线数据
bars = data_service.get_bar_data(
    symbol="000001",
    exchange=Exchange.SZSE,
    interval=Interval.DAILY,
    start=datetime(2024, 1, 1),
    end=datetime.now()
)

print(f"获取到 {len(bars)} 条K线数据")
```

### 15.2 获取特色数据

```python
# 获取龙虎榜数据
dragon_tiger_data = data_service.get_dragon_tiger_data(
    datetime(2024, 2, 20).date()
)

for data in dragon_tiger_data:
    print(f"{data.symbol}: 机构净买入 {data.institution_net_buy:.2f} 元")

# 获取北向资金
northbound = data_service.get_northbound_flow(
    datetime(2024, 2, 20).date()
)

print(f"北向资金净流入: {northbound.net_inflow:.2f} 亿元")
```

---

`★ Insight ─────────────────────────────────────`
**REQ-003实现的关键设计决策：**
1. **单例模式**：确保整个应用只有一个数据服务实例，避免重复连接
2. **接口分层**：实现多个接口，每个接口对应一类数据需求
3. **限流保护**：Tushare API有严格限流，必须实现令牌桶算法
4. **缓存优先**：三级缓存（内存→Redis→MySQL）保证性能
5. **Tushare完整API覆盖**：实现了25+个Tushare Pro API接口，覆盖股票、财务、龙虎榜、北向资金、板块等全部数据类型
6. **QMT实时订阅机制**：通过订阅回调+VeighNa事件引擎实现实时行情分发，支持自动重连和订单簿监控
`─────────────────────────────────────────────────`

---

## 16. Tushare适配器API调用清单

### 16.1 基础数据API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `stock_basic` | 股票列表 | 200次/分 | 基础信息 |
| `stock_company` | 公司信息 | 200次/分 | 公司详情 |
| `namechange` | 更名数据 | 200次/分 | 历史名称 |

### 16.2 行情数据API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `daily` | 日线数据 | 200次/分 | OHLCV |
| `pro_bar` | 专业行情(复权) | 200次/分 | 支持复权 |
| `stk_mins` | 分钟线 | 需高级权限 | 分钟数据 |
| `adj_factor` | 复权因子 | 200次/分 | 复权系数 |

### 16.3 财务数据API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `income` | 利润表 | 200次/分 | 收入利润 |
| `balancesheet` | 资产负债表 | 200次/分 | 资产负债 |
| `cashflow` | 现金流量表 | 200次/分 | 现金流 |
| `fina_indicator` | 财务指标 | 200次/分 | PE/PB/ROE等 |

### 16.4 龙虎榜API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `top_list` | 每日龙虎榜 | 200次/分 | 榜单汇总 |
| `top_inst` | 龙虎榜明细 | 200次/分 | 席位明细 |

### 16.5 北向资金API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `moneyflow_hsgt` | 资金流向 | 200次/分 | 每日流向 |
| `hk_hold` | 持股数据 | 200次/分 | 个股持股 |
| `hk_quota` | 资金额度 | 200次/分 | 额度使用 |

### 16.6 板块分类API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `index_classify` | 行业分类 | 200次/分 | 行业列表 |
| `index_member` | 成分股 | 200次/分 | 成分股列表 |
| `concept_detail` | 概念股 | 200次/分 | 概念成分股 |

### 16.7 其他特色API

| API方法 | 功能 | 限流要求 | 返回数据 |
|--------|------|----------|----------|
| `limit_list` | 涨跌停 | 200次/分 | 涨跌停列表 |
| `new_share` | 新股 | 200次/分 | 新股发行 |
| `margin` | 融资融券 | 200次/分 | 标的股票 |
| `margin_detail` | 融资融券明细 | 200次/分 | 每日余额 |

---

## 17. QMT适配器实时行情订阅详解

### 17.1 订阅流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    QMT实时行情订阅流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 初始化阶段                                                   │
│     ┌──────────────┐                                           │
│     │ 创建QMT网关  │ → 设置回调函数 → 连接QMT                  │
│     └──────────────┘                                           │
│                                                                 │
│  2. 订阅阶段                                                     │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│     │ 添加订阅列表  │→│ 注册回调函数  │→│ 调用QMT订阅  │       │
│     └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                                 │
│  3. 数据接收阶段                                                 │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│     │ QMT推送Tick  │→│ 更新缓存     │→│ 触发事件     │       │
│     └──────────────┘  └──────────────┘  └──────────────┘      │
│                           ↓                                     │
│                     ┌──────────────┐                           │
│                     │ 执行回调函数  │                            │
│                     └──────────────┘                           │
│                                                                 │
│  4. 容错处理                                                     │
│     ┌──────────────┐  ┌──────────────┐                         │
│     │ 检测连接状态  │→│ 自动重连     │→│ 重新订阅     │       │
│     └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 17.2 数据流转

```
QMT行情源
    ↓
QMTDataAdapter._on_qmt_tick()
    ↓
┌──────────────────────┬──────────────────────┬──────────────────────┐
│  更新tick_cache       │  VeighNa事件引擎      │  执行用户回调        │
│  (内存缓存)           │  (EventEngine)       │  (symbol_callbacks)  │
└──────────────────────┴──────────────────────┴──────────────────────┘
    ↓                      ↓                      ↓
快速查询最新Tick      事件驱动架构         策略接收实时行情
```

### 17.3 实时K线生成

```
Tick数据流
    ↓
QMTRealtimeBarGenerator.on_tick()
    ↓
┌─────────────────────────────────────────────────────────────────┐
│  判断是否切换周期                                               │
│    ┌──────────┐  ┌──────────┐                                  │
│    │ 同一周期  │→│ 更新K线   │                                  │
│    └──────────┘  └──────────┘                                  │
│    ┌──────────┐                                                │
│    │ 新周期    │→ 返回完成的K线 → 重置缓冲区                    │
│    └──────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### 17.4 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Tick延迟 | <100ms | 从QMT接收到策略接收 |
| 订阅容量 | 500只 | 同时订阅股票数量 |
| 重连时间 | <30秒 | 连接断开后恢复时间 |
| 内存占用 | <100MB | 订阅500只股票时 |

---

**需要我继续详细说明某个具体子模块的实现吗？**比如：
- Tushare适配器的详细实现
- 数据库表设计的完整SQL
- 缓存策略的详细方案
- 单元测试的完整示例
