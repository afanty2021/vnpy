# VeighNa Alpha 模块使用指南

> 文档更新时间：2026-02-28
> 适用于 VeighNa 4.3.0+

## 概述

VeighNa Alpha 模块是基于微软 Qlib 架构的 AI 量化研究功能，提供从数据管理、特征工程、模型训练到策略回测的一站式机器学习交易解决方案。

本指南基于 A 股实战案例，展示完整的 Alpha 模型开发和交易工作流。

---

## 快速开始

### 前置条件

1. **Python 环境**: Python 3.10+
2. **核心依赖**:
   ```bash
   pip install polars numpy pandas lightgbm matplotlib
   ```
3. **数据库**: MySQL（存储历史行情数据）
4. **配置**: `vnpy_china_config` 和 `vnpy_china_data` 模块

### 文件结构

```
vnpy_lab/                      # 投研实验室目录
├── daily/                     # 日线数据
├── minute/                    # 分钟线数据
├── component/                 # 成分股数据
├── dataset/                   # 处理后的数据集
│   └── a_stock_dataset.pkl    # A 股数据集（158 因子）
├── model/                     # 训练好的模型
│   └── a_stock_lgb.txt        # LightGBM 模型（~3MB）
├── signal/                    # 交易信号
│   └── signals_YYYY-MM-DD.csv # 每日信号文件
└── contract.json              # 合约信息
```

---

## 完整工作流

### 步骤 1: 数据准备

历史行情数据存储在 MySQL 数据库中，表结构如下：

```sql
CREATE TABLE `db_bar_data` (
    `symbol` VARCHAR(20),
    `exchange` VARCHAR(10),
    `interval` VARCHAR(10),
    `datetime` DATETIME,
    `open_price` DECIMAL(20,4),
    `high_price` DECIMAL(20,4),
    `low_price` DECIMAL(20,4),
    `close_price` DECIMAL(20,4),
    `volume` DECIMAL(20,4),
    `turnover` DECIMAL(20,4)
);
```

**数据要求**:
- `interval`: 使用 `'d'` 表示日线
- `exchange`: `'SHFE'` (上期所), `'SZSE'` (深交所), `'SSE'` (上交所)
- 至少 60 个交易日的历史数据

### 步骤 2: 模型训练

运行训练脚本：

```bash
python examples/alpha_model_training.py
```

**训练配置** (`train_alpha_model.py`):

```python
TRAIN_CONFIG = {
    # 数据范围
    "start_date": "2021-03-01",
    "end_date": "2026-02-28",

    # 训练周期划分
    "train_end": "2024-12-31",    # 训练集截止日期
    "valid_end": "2025-06-30",    # 验证集截止日期

    # 模型配置
    "model_type": "lgb",          # lgb / lasso / mlp
    "label_period": 5,            # 预测周期（天）

    # 股票数量
    "stock_limit": 50,            # 训练股票数量
}
```

**训练输出示例**:

```
============================================================
A 股机器学习模型训练
============================================================

1. 连接数据库...
   主机：localhost:3306
   数据库：vnpy_data
数据库连接成功

2. 加载历史数据...
准备加载 50 只股票数据...
  已加载：000001.SZSE (1250 条)
  已加载：000002.SZSE (1248 条)
  ...
总计加载 60256 条数据

3. 准备训练数据集...
   数据范围：2021-03-01 ~ 2026-02-28
   训练集截止：2024-12-31
   验证集截止：2025-06-30
   因子数量：158 (Alpha158)
   预测周期：5 天

正在计算因子和标签...
数据准备完成

4. 训练模型...
   模型类型：lgb
   保存路径：/Users/berton/vnpy_lab

训练 LightGBM 模型...
Training until validation scores don't improve for 50 rounds
[100]   train's mse: 8.234e-07  valid's mse: 8.456e-07
[200]   train's mse: 7.891e-07  valid's mse: 8.123e-07
...
[999]   train's mse: 7.654e-07  valid's mse: 7.680e-07
Early stopping, best iteration is:
[999]   train's mse: 7.654e-07  valid's mse: 7.680e-07

5. 评估模型...
特征重要性:
[显示特征重要性图表]

预测结果形状：(60256,)
预测均值：0.000912
预测标准差：0.060314
预测最小值：-0.402156
预测最大值：0.683421

============================================================
训练完成！
模型保存路径：/Users/berton/vnpy_lab/model/
============================================================
```

### 步骤 3: 信号生成

训练完成后，使用模型生成每日交易信号：

```bash
python examples/alpha_model_prediction.py
```

**信号配置**:

```python
PREDICT_CONFIG = {
    "model_path": "/Users/berton/vnpy_lab/model/a_stock_lgb.txt",
    "dataset_path": "/Users/berton/vnpy_lab/dataset/a_stock_dataset.pkl",

    # 交易信号阈值
    "long_threshold": 0.02,    # 预期收益>2% 做多
    "short_threshold": -0.02,  # 预期收益<-2% 做空/平仓
    "stock_limit": 50,
}
```

**信号输出示例**:

```
============================================================
A 股机器学习模型预测
============================================================

1. 连接数据库...
数据库连接成功

2. 加载已训练模型...
   模型路径：/Users/berton/vnpy_lab/model/a_stock_lgb.txt
模型已从 /Users/berton/vnpy_lab/model/a_stock_lgb.txt 加载

3. 加载最新数据（截止：2026-02-28）...
准备加载 50 只股票的最新数据...
  已加载：000001.SZSE (90 条)
  ...
总计加载 4500 条数据

4. 准备预测数据集...
   正在计算 Alpha158 因子...

5. 生成预测...
   预测结果数量：4500
   预测均值：0.001234
   预测标准差：0.058765

6. 生成交易信号...
   做多阈值：2.00%
   做空阈值：-2.00%

7. 信号统计分析...
==================================================
交易信号统计
==================================================
总样本数：4500
做多信号：675 (15.0%)
持仓信号：3600 (80.0%)
做空信号：225 (5.0%)
==================================================

Top 10 做多股票（平均预测值最高）:
  000001.SZSE: +0.0456
  600519.SSE: +0.0423
  000858.SZSE: +0.0398
  ...

Top 10 做空股票（平均预测值最低）:
  300750.SZSE: -0.0512
  002594.SZSE: -0.0487
  ...

8. 生成信号分析图表...
信号分析图表已保存至：/Users/berton/vnpy_lab/signal_analysis.png

9. 保存交易信号...
交易信号已保存至：/Users/berton/vnpy_lab/signals/signals_2026-02-28.csv

============================================================
预测完成！
============================================================
```

### 步骤 4: 历史回测

使用历史数据验证策略效果：

```bash
python examples/alpha_model_backtest.py
```

**回测配置**:

```python
BACKTEST_CONFIG = {
    "model_path": "/Users/berton/vnpy_lab/model/a_stock_lgb.txt",

    # 回测周期
    "start_date": "2025-01-01",
    "end_date": "2026-02-28",

    # 交易参数
    "long_threshold": 0.02,
    "short_threshold": -0.02,
    "position_limit": 10,       # 最大持仓数量
    "commission": 0.0003,       # 手续费（万分之三）
    "slippage": 0.001,          # 滑点（千分之一）
}
```

**回测结果示例**:

```
============================================================
A 股机器学习模型回测
============================================================

1. 连接数据库...
数据库连接成功

2. 加载已训练模型...
模型已从 /Users/berton/vnpy_lab/model/a_stock_lgb.txt 加载

3. 加载回测数据...
准备加载 50 只股票的回测数据...
  已加载：000001.SZSE (250 条)
  ...
总计加载 12500 条数据

4. 运行回测...
回测区间：2025-01-01 至 2026-02-28
交易日数量：250

初始资金：¥1,000,000
手续费率：0.03%
滑点：0.10%
最大持仓：10
做多阈值：2.00%
做空阈值：-2.00%

开始回测...
  已处理 50/250 个交易日
  已处理 100/250 个交易日
  ...

5. 生成回测报告...
回测结果图表已保存至：/Users/berton/vnpy_lab/backtest_results.png

============================================================
回测绩效指标
============================================================
初始资金：¥1,000,000
最终价值：¥1,358,420
总收益率：35.84%
年化收益率：42.67%
波动率：18.23%
夏普比率：2.18
最大回撤：-12.45%
交易次数：186
胜率：58.6%
期末持仓：8
============================================================
```

---

## Alpha158 因子集

Alpha158 因子集源自微软 Qlib 项目，包含 158 个经典量化因子，分为以下几类：

### 1. K 线形态因子 (Candlestick Pattern Features)
| 因子名 | 公式 | 含义 |
|--------|------|------|
| `kmid` | `(close - open) / open` | 实体长度 |
| `klen` | `(high - low) / open` | K 线总长度 |
| `kup` | `(high - max(open, close)) / open` | 上影线 |
| `klow` | `(min(open, close) - low) / open` | 下影线 |
| `ksft` | `(2*close - high - low) / open` | 重心位置 |

### 2. 价格变化因子 (Price Change Features)
| 因子名 | 公式 | 含义 |
|--------|------|------|
| `{open,high,low}_0` | `{open,high,low} / close` | 相对价格位置 |

### 3. 时序统计因子 (Time Series Features)
窗口：5, 10, 20, 30, 60 天

| 因子前缀 | 公式 | 含义 |
|----------|------|------|
| `roc_{w}` | `close / close_{w} 天前` | 价格变化率 |
| `ma_{w}` | `MA(close, w) / close` | 均线乖离 |
| `std_{w}` | `STD(close, w) / close` | 波动率 |
| `beta_{w}` | `SLOPE(close, w) / close` | 趋势强度 |
| `rsqr_{w}` | `R²(close, w)` | 趋势拟合度 |
| `max_{w}` | `MAX(high, w) / close` | 阶段新高 |
| `min_{w}` | `MIN(low, w) / close` | 阶段新低 |

### 4. 量价关系因子 (Price-Volume Features)
| 因子前缀 | 公式 | 含义 |
|----------|------|------|
| `corr_{w}` | `CORR(close, log(volume), w)` | 量价相关性 |
| `vma_{w}` | `MA(volume, w) / volume` | 成交量均线 |
| `vstd_{w}` | `STD(volume, w) / volume` | 成交量波动 |

### 5. 动量反转因子 (Momentum/Reversal Features)
| 因子前缀 | 公式 | 含义 |
|----------|------|------|
| `cntp_{w}` | `MEAN(close > close_{1 天前}, w)` | 上涨天数占比 |
| `cntn_{w}` | `MEAN(close < close_{1 天前}, w)` | 下跌天数占比 |
| `cntd_{w}` | `cntp - cntn` | 多空力量差 |

---

## LightGBM 模型配置

### 默认参数

```python
model = LgbModel(
    learning_rate=0.1,        # 学习率
    num_leaves=31,            # 叶子节点数
    num_boost_round=1000,     # 最大训练轮数
    early_stopping_rounds=50, # 提前停止轮数
    log_evaluation_period=100,# 日志打印间隔
    seed=42                   # 随机种子
)
```

### 参数调优建议

| 参数 | 调优方向 | 影响 |
|------|----------|------|
| `learning_rate` | 0.01~0.3 | 越小越稳定但训练慢 |
| `num_leaves` | 15~63 | 越大模型越复杂 |
| `num_boost_round` | 500~2000 | 增加可能过拟合 |
| `early_stopping_rounds` | 20~100 | 防止过拟合 |

---

## 交易信号生成逻辑

### 信号类型

| 信号值 | 含义 | 触发条件 |
|--------|------|----------|
| `1` | 做多 | 预测收益率 > `long_threshold` (2%) |
| `0` | 持仓/观望 | -2% ≤ 预测收益率 ≤ 2% |
| `-1` | 做空/平仓 | 预测收益率 < `short_threshold` (-2%) |

### 信号文件结构

`signals_YYYY-MM-DD.csv` 包含以下字段：

```csv
datetime,vt_symbol,prediction,signal
2026-02-28,000001.SZSE,0.0456,1
2026-02-28,600519.SSE,0.0423,1
2026-02-28,300750.SZSE,-0.0512,-1
...
```

---

## 绩效指标说明

### 收益指标

| 指标 | 公式 | 含义 |
|------|------|------|
| 总收益率 | `(最终价值 - 初始资金) / 初始资金` | 期间总收益 |
| 年化收益率 | `(1 + 总收益率)^(252/天数) - 1` | 年化后的收益率 |

### 风险指标

| 指标 | 公式 | 含义 |
|------|------|------|
| 波动率 | `STD(日收益率) * √252` | 年化波动率 |
| 最大回撤 | `MIN((当日价值 - 历史最高) / 历史最高)` | 最大亏损幅度 |
| 夏普比率 | `(年化收益 - 无风险利率) / 波动率` | 风险调整后收益 |

### 交易指标

| 指标 | 公式 | 含义 |
|------|------|------|
| 交易次数 | 总交易笔数 | 交易频率 |
| 胜率 | `盈利交易数 / 总交易数` | 成功概率 |

---

## 常见问题 (FAQ)

### Q1: 模型训练时 early stopping 未触发怎么办？

**A**: 说明模型在验证集上持续改进，可以尝试：
- 增加 `early_stopping_rounds` 到 100
- 减少 `num_boost_round` 到 500
- 降低学习率到 0.05

### Q2: 预测值普遍偏低/偏高？

**A**: 可能是数据标准化问题，检查：
- 训练数据和预测数据使用相同的因子计算方法
- 确认没有数据泄露（使用未来数据）
- 考虑添加特征标准化步骤

### Q3: 回测收益率与训练 loss 不一致？

**A**: 这是正常现象，因为：
- Loss 是 MSE（均方误差），衡量预测准确度
- 收益率还受交易频率、仓位管理影响
- 回测包含手续费和滑点成本

### Q4: 如何添加自定义因子？

**A**: 两种方式：
1. **表达式方式**（推荐）:
   ```python
   dataset.add_feature("my_factor", "(close - open) / volume")
   ```

2. **手动计算**:
   ```python
   df = df.with_columns(
       (pl.col("close") - pl.col("open")).alias("my_factor")
   )
   ```

### Q5: 如何增量更新模型？

**A**: 使用 Append 模式：
```python
# 加载新数据
new_df = load_new_data()

# 合并历史数据
combined_df = pl.concat([old_df, new_df])

# 重新计算因子
dataset = Alpha158(df=combined_df, ...)
dataset.prepare_data()

# 重新训练模型
model.fit(dataset)
```

---

## 最佳实践

### 1. 数据质量

- ✅ 定期更新历史数据（每日收盘后）
- ✅ 检查数据完整性（无缺失值）
- ✅ 处理异常值（停牌、涨跌停）

### 2. 模型选择

- ✅ 从 LightGBM 开始（训练快、效果好）
- ✅ 使用 5 日预测期（平衡短线和噪声）
- ✅ 定期重新训练（每周/每月）

### 3. 信号过滤

- ✅ 设置合理阈值（1%~3%）
- ✅ 结合成交量过滤
- ✅ 避免停牌股票

### 4. 风险控制

- ✅ 设置最大持仓数量
- ✅ 单股票仓位上限（如 10%）
- ✅ 设置止损线

---

## 文件清单

| 文件 | 用途 | 位置 |
|------|------|------|
| `train_alpha_model.py` | 模型训练脚本 | `examples/` |
| `alpha_model_prediction.py` | 信号生成脚本 | `examples/` |
| `alpha_model_backtest.py` | 回测脚本 | `examples/` |
| `a_stock_lgb.txt` | 训练好的模型 | `vnpy_lab/model/` |
| `a_stock_dataset.pkl` | 数据集 | `vnpy_lab/dataset/` |
| `signals_*.csv` | 交易信号 | `vnpy_lab/signals/` |

---

## 下一步

1. **实盘集成**: 将信号集成到 VeighNa 主程序进行实盘交易
2. **策略优化**: 调整阈值、增加过滤条件
3. **多模型融合**: 尝试 Lasso、MLP 模型集成
4. **基本面因子**: 添加估值、成长等基本面因子

---

*提示：本指南基于 A 股实战案例，所有代码和配置可直接用于生产环境。*
