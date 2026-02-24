# A股数据服务设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-003
> 优先级：P0

---

## 1. 设计目标

为VeighNa框架构建完整的A股数据服务层，实现：

1. **统一数据接口**：整合QMT实时数据和Tushare离线数据
2. **多层次数据覆盖**：基础行情、股票信息、财务数据
3. **高性能存储**：MySQL + Redis缓存
4. **增量更新**：避免全量拉取

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       A股数据服务架构                              │
├─────────────────────────────────────────────────────────────────┤
│  【数据源层】                                                    │
│  ┌────────────── ┌──────────────┐  ┌──────────────┐ ┐        │
│  │ QMT实时行情   │  │Tushare API  │  │  本地缓存    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【服务层】                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ DataService   │  │  QueryCache  │  │ DataSource   │        │
│  │   (主服务)    │  │   (缓存)     │  │  Adapter     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【存储层】                                                      │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │   MySQL      │  │   Redis      │                          │
│  │  (持久存储)   │  │  (热点缓存)  │                          │
│  └──────────────┘  └──────────────┘                          │
├─────────────────────────────────────────────────────────────────┤
│  【接口层】                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  行情数据API  │  │ 股票信息API  │  │  财务数据API │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_data/
├── __init__.py
├── service.py                 # 数据服务主类
├── cache.py                  # 缓存管理
├── database.py               # MySQL数据库层
├── adapter/
│   ├── __init__.py
│   ├── tushare_adapter.py    # Tushare数据适配器
│   └── qmt_adapter.py       # QMT数据适配器
├── models/
│   ├── __init__.py
│   ├── stock_info.py         # 股票信息模型
│   └── financial_data.py     # 财务数据模型
└── config.py                 # 配置项
```

---

## 3. 核心类设计

### 3.1 数据服务主类

```python
from vnpy.trader.object import BarData, TickData, HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime
from typing import Optional


class ChinaDataService:
    """A股数据服务"""

    def __init__(self):
        self.cache = DataQueryCache()
        self.database = DatabaseLayer()
        self.tushare_adapter = TushareDataAdapter()
        self.qmt_adapter = QMTDataAdapter()

    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> list[BarData]:
        """获取K线数据"""
        # 1. 尝试从缓存获取
        cache_key = f"bar_{symbol}_{exchange}_{interval}_{start}_{end}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # 2. 尝试从数据库获取
        db_data = self.database.load_bar_data(symbol, exchange, interval, start, end)
        if db_data:
            self.cache.set(cache_key, db_data)
            return db_data

        # 3. 从API获取并存储
        api_data = self._fetch_from_api(symbol, exchange, interval, start, end)
        if api_data:
            self.database.save_bar_data(api_data)
            self.cache.set(cache_key, api_data)
        return api_data

    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> list[TickData]:
        """获取Tick数据"""

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本信息"""

    def get_financial_data(self, symbol: str, report_date: str) -> Optional[FinancialData]:
        """获取财务数据"""

    def get_daily_bars(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> list[BarData]:
        """获取日线数据（简化接口）"""
        return self.get_bar_data(symbol, exchange, Interval.DAILY, start, end)

    def get_minute_bars(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> list[BarData]:
        """获取分钟线数据"""
        return self.get_bar_data(symbol, exchange, interval, start, end)
```

### 3.2 缓存管理

```python
import redis
from typing import Any, Optional
import json
from datetime import timedelta


class DataQueryCache:
    """数据查询缓存"""

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True
        )

        # 缓存配置
        self.default_ttl = timedelta(hours=1)
        self.bar_ttl = timedelta(minutes=5)
        self.tick_ttl = timedelta(seconds=30)
        self.info_ttl = timedelta(hours=24)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """设置缓存"""
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, int(ttl.total_seconds()), serialized)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配的所有缓存"""
        keys = self.redis_client.keys(pattern)
        if keys:
            return self.redis_client.delete(*keys)
        return 0
```

### 3.3 MySQL数据库层

```python
from vnpy.trader.database import BaseDatabase
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime
from typing import Optional


class MySQLDatabaseLayer(BaseDatabase):
    """MySQL数据库层"""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        import pymysql
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )

    def save_bar_data(self, bars: list[BarData]) -> bool:
        """保存K线数据"""
        # 批量插入或更新
        pass

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> list[BarData]:
        """加载K线数据"""
        pass

    def save_stock_info(self, info: StockInfo) -> bool:
        """保存股票信息"""

    def load_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """加载股票信息"""

    def save_financial_data(self, data: FinancialData) -> bool:
        """保存财务数据"""

    def load_financial_data(self, symbol: str, report_date: str) -> Optional[FinancialData]:
        """加载财务数据"""
```

### 3.4 Tushare数据适配器

```python
import tushare as ts
from typing import Optional
import pandas as pd


class TushareDataAdapter:
    """Tushare数据适配器"""

    def __init__(self, token: str):
        self.pro = ts.pro_api(token)

    def fetch_daily_bars(
        self,
        ts_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取日线数据"""
        df = self.pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        return df

    def fetch_minute_bars(
        self,
        ts_code: str,
        start_time: str,
        end_time: str,
        freq: str = "5min"
    ) -> pd.DataFrame:
        """获取分钟线数据"""
        df = self.pro.minute(
            ts_code=ts_code,
            start_time=start_time,
            end_time=end_time,
            freq=freq
        )
        return df

    def fetch_stock_basic(self) -> pd.DataFrame:
        """获取股票基本信息"""
        df = self.pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,list_date'
        )
        return df

    def fetch_financial_data(
        self,
        ts_code: str,
        report_type: str = "1"
    ) -> pd.DataFrame:
        """获取财务数据"""
        df = self.pro.fina_indicator(
            ts_code=ts_code,
            report_type=report_type
        )
        return df

    def fetch_dividend_data(self, ts_code: str) -> pd.DataFrame:
        """获取分红送股数据"""
        df = self.pro.dividend(ts_code=ts_code)
        return df
```

---

## 4. 数据模型

### 4.1 股票信息

```python
from dataclasses import dataclass
from datetime import date


@dataclass
class StockInfo:
    """股票基本信息"""
    symbol: str                    # 股票代码（000001.SZSE）
    name: str                     # 股票名称
    exchange: str                 # 交易所（SSE/SZSE/BSE）
    market: str                  # 市场类型（主板/创业板/科创板/北交所）
    list_date: date              # 上市日期
    is_st: bool                  # 是否ST
    industry: str                # 所属行业
    area: str                   # 所属地区
    limit_ratio: float          # 涨跌停比例
```

### 4.2 财务数据

```python
from dataclasses import dataclass
from datetime import date


@dataclass
class FinancialData:
    """财务数据"""
    symbol: str                  # 股票代码
    report_date: date           # 报告期
    report_type: str           # 报告类型（季报/半年报/年报）

    # 估值指标
    pe_ratio: float             # 市盈率
    pb_ratio: float             # 市净率
    ps_ratio: float             # 市销率

    # 盈利能力
    roe: float                 # 净资产收益率
    roa: float                 # 总资产收益率
    gross_margin: float        # 毛利率
    net_margin: float          # 净利率

    # 财务数据
    revenue: float             # 营业收入
    net_profit: float          # 净利润
    total_assets: float        # 总资产
    total_liabilities: float   # 总负债
    equity: float              # 股东权益
```

---

## 5. 增量更新机制

### 5.1 数据更新流程

```python
class IncrementalUpdater:
    """增量更新器"""

    def __init__(self, data_service: ChinaDataService):
        self.data_service = data_service

    def update_daily_bars(self, symbol: str, exchange: Exchange) -> int:
        """更新日线数据"""
        # 1. 获取数据库中最新日期
        latest_date = self.database.get_latest_date(symbol, exchange, Interval.DAILY)

        # 2. 如果没有数据，从2015年开始
        if not latest_date:
            start_date = "20150101"
        else:
            start_date = latest_date.strftime("%Y%m%d")

        # 3. 从Tushare获取增量数据
        end_date = datetime.now().strftime("%Y%m%d")
        new_bars = self.tushare_adapter.fetch_daily_bars(symbol, start_date, end_date)

        # 4. 保存到数据库
        if new_bars:
            self.database.save_bar_data(new_bars)

        return len(new_bars)

    def update_stock_info(self) -> int:
        """更新股票基本信息"""
        # 每周更新一次股票列表
        pass

    def update_financial_data(self, symbol: str) -> int:
        """更新财务数据"""
        # 每季度财报公布后更新
        pass
```

---

## 6. 配置设计

### 6.1 配置文件

```python
# vnpy_china_data/config.py

from dataclasses import dataclass


@dataclass
class DataServiceConfig:
    """数据服务配置"""

    # Redis缓存配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # MySQL数据库配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "vnpy"
    mysql_password: str = ""
    mysql_database: str = "vnpy_data"

    # Tushare配置
    tushare_token: str = ""

    # 缓存策略
    bar_cache_ttl: int = 300        # 5分钟
    tick_cache_ttl: int = 30        # 30秒
    info_cache_ttl: int = 86400    # 24小时

    # 更新策略
    auto_update_enabled: bool = True
    update_interval: int = 60       # 更新间隔（秒）


# 从环境变量或配置文件加载
CONFIG = DataServiceConfig(
    redis_host=os.getenv("REDIS_HOST", "localhost"),
    tushare_token=os.getenv("TUSHARE_TOKEN", ""),
    # ...
)
```

---

## 7. 集成方式

### 7.1 在VeighNa中使用

```python
from vnpy_china_data import ChinaDataService


def main():
    # 初始化数据服务
    data_service = ChinaDataService()

    # 获取日线数据
    bars = data_service.get_daily_bars(
        symbol="000001",
        exchange=Exchange.SZSE,
        start=datetime(2024, 1, 1),
        end=datetime.now()
    )

    # 获取股票信息
    info = data_service.get_stock_info("000001.SZSE")

    # 获取财务数据
    financial = data_service.get_financial_data(
        "000001.SZSE",
        "2024-03-31"
    )
```

---

## 8. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基础配置 | 0.5人天 |
| 2 | 实现MySQL数据库层 | 1人天 |
| 3 | 实现Redis缓存管理 | 1人天 |
| 4 | 实现Tushare数据适配器 | 1.5人天 |
| 5 | 实现数据服务主类 | 1人天 |
| 6 | 实现增量更新机制 | 1人天 |
| 合计 | | **6人天** |

---

## 9. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
