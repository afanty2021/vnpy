# RPC实时信号生成系统 - 数据加载指南

## 概述

`rpc_realtime_signals.py` 是一个通过RPC连接到QMT服务器，使用Alpha158因子和LightGBM模型生成实时交易信号的脚本。

## 问题说明

### 当前状态

`load_initial_data()` 方法当前为空实现，这意味着：

1. **系统启动后需要等待60天**才能积累足够的数据窗口（window_size=60）
2. 在此期间无法生成任何交易信号
3. 不适合快速测试和开发

## 解决方案

### 方案1：从本地CSV文件加载（推荐用于开发测试）

创建数据目录并准备CSV文件：

```bash
mkdir -p data/
```

CSV文件格式示例（`data/000001.SZSE.csv`）：

```csv
datetime,open,high,low,close,volume,turnover
2024-01-01 09:30:00,10.50,10.60,10.45,10.55,1000000,10550000
2024-01-01 09:31:00,10.55,10.65,10.50,10.60,1200000,12720000
...
```

在 `load_initial_data()` 方法中添加：

```python
def load_initial_data(self, symbols: List[Tuple[str, str]]) -> None:
    """从本地CSV文件加载历史数据"""
    data_dir = Path("data")

    for symbol, exchange_str in symbols:
        vt_symbol = f"{symbol}.{exchange_str}"
        csv_path = data_dir / f"{vt_symbol}.csv"

        if csv_path.exists():
            df = pl.read_csv(csv_path, try_parse_dates=True)
            for row in df.iter_rows(named=True):
                self.data_windows[vt_symbol].append({
                    "datetime": row["datetime"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                    "turnover": row.get("turnover", 0),
                })
            logger.info(f"已加载 {vt_symbol} 的历史数据，共 {len(df)} 条")
```

### 方案2：从数据库加载（推荐用于生产环境）

如果使用MySQL数据库存储历史数据：

```python
import sqlalchemy

def load_initial_data(self, symbols: List[Tuple[str, str]]) -> None:
    """从MySQL数据库加载历史数据"""
    engine = sqlalchemy.create_engine("mysql+pymysql://user:password@localhost/vnpy")

    for symbol, exchange_str in symbols:
        vt_symbol = f"{symbol}.{exchange_str}"

        query = f"""
        SELECT datetime, open, high, low, close, volume, turnover
        FROM {symbol.replace('.', '_')}_data
        ORDER BY datetime DESC
        LIMIT {self.window_size}
        """

        df = pl.read_database(query, engine)
        for row in df.iter_rows(named=True):
            self.data_windows[vt_symbol].append({
                "datetime": row["datetime"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "turnover": row.get("turnover", 0),
            })
        logger.info(f"已从数据库加载 {vt_symbol} 的历史数据，共 {len(df)} 条")
```

### 方案3：通过RPC查询（需要RPC服务器支持）

如果RPC服务器提供历史数据查询接口：

```python
def load_initial_data(self, symbols: List[Tuple[str, str]]) -> None:
    """通过RPC查询历史数据"""
    for symbol, exchange_str in symbols:
        vt_symbol = f"{symbol}.{exchange_str}"

        # 假设RPC服务器提供 query_history 方法
        history = self.rpc_client.query_history(
            symbol=symbol,
            exchange=exchange_str,
            interval="1m",
            start_date=datetime.now() - timedelta(days=self.window_size),
            end_date=datetime.now()
        )

        for bar in history:
            self.data_windows[vt_symbol].append({
                "datetime": bar["datetime"],
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
                "turnover": bar.get("turnover", 0),
            })
        logger.info(f"已通过RPC加载 {vt_symbol} 的历史数据，共 {len(history)} 条")
```

## 推荐实施步骤

1. **开发阶段**：使用方案1（本地CSV文件）
   - 从Tushare或其他数据源下载历史数据
   - 保存为CSV格式
   - 快速验证系统功能

2. **测试阶段**：使用方案2（数据库）
   - 建立数据库连接
   - 导入历史数据到数据库
   - 验证数据查询性能

3. **生产阶段**：使用方案3（RPC查询）
   - 确保RPC服务器支持历史数据查询
   - 实现自动化的数据同步机制
   - 添加数据完整性检查

## 数据质量要求

### 必需字段

- `datetime`: 时间戳（datetime类型）
- `open`: 开盘价（float类型）
- `high`: 最高价（float类型）
- `low`: 最低价（float类型）
- `close`: 收盘价（float类型）
- `volume`: 成交量（float/int类型）

### 可选字段

- `turnover`: 成交额（float类型，默认0）

### 数据要求

- 时间顺序：从旧到新
- 数据量：至少 `window_size` 条记录（默认60条）
- 时间间隔：1分钟K线数据
- 无缺失值：所有必需字段必须有效

## 常见问题

### Q1: 为什么需要60天的历史数据？

A: Alpha158因子计算需要足够的历史数据才能准确计算技术指标（如MA、MACD等）。窗口大小可通过 `window_size` 参数调整。

### Q2: 可以减少窗口大小吗？

A: 可以，但会降低因子计算的准确性。建议窗口大小至少30天。

### Q3: 如何验证数据加载是否成功？

A: 检查日志输出，每只股票会显示 "已加载 XXX 的历史数据，共 N 条"。

### Q4: 数据加载失败怎么办？

A: 检查文件路径、数据格式、数据库连接等，参考日志中的错误信息进行排查。

## 相关文件

- `rpc_realtime_signals.py` - 主脚本
- `alpha_model_training.py` - 模型训练脚本
- `alpha_model_prediction.py` - 信号预测脚本
