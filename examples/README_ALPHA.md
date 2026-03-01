# VeighNa Alpha 模型实战指南

> 📅 更新时间：2026-02-28
> 📊 基于 VeighNa 4.3.0 + A 股实战案例

---

## 📖 快速导航

- [完整工作流](#-完整工作流)
- [文件清单](#-文件清单)
- [训练结果汇总](#-训练结果汇总)
- [常见问题](#-常见问题)

---

## 🎯 完整工作流

### 1️⃣ 数据准备

确保 MySQL 数据库中包含历史行情数据：

```bash
# 检查数据表
mysql -u root -p -e "SELECT COUNT(*) FROM vnpy_data.db_bar_data WHERE interval='d';"
```

### 2️⃣ 模型训练

```bash
# 运行训练脚本
python examples/alpha_model_training.py
```

**预计耗时**: 5-10 分钟（取决于股票数量）

**输出文件**:
- `~/vnpy_lab/model/a_stock_lgb.txt` - 训练好的 LightGBM 模型
- `~/vnpy_lab/dataset/a_stock_dataset.pkl` - 处理后的数据集

### 3️⃣ 信号生成

```bash
# 使用训练好的模型生成当日交易信号
python examples/alpha_model_prediction.py
```

**输出文件**:
- `~/vnpy_lab/signals/signals_YYYY-MM-DD.csv` - 每日交易信号
- `~/vnpy_lab/signal_analysis.png` - 信号分析图表

### 4️⃣ 历史回测

```bash
# 使用历史数据验证策略效果
python examples/alpha_model_backtest.py
```

**输出文件**:
- `~/vnpy_lab/backtest_results.png` - 回测结果图表

---

## 📁 文件清单

| 文件路径 | 说明 | 用途 |
|----------|------|------|
| `examples/alpha_model_training.py` | 模型训练脚本 | 从数据库加载数据并训练 LightGBM 模型 |
| `examples/alpha_model_prediction.py` | 信号生成脚本 | 使用模型生成当日交易信号 |
| `examples/alpha_model_backtest.py` | 回测脚本 | 历史回测验证策略效果 |
| `examples/ALPHA_MODEL_GUIDE.md` | 详细使用指南 | 完整的文档说明 |
| `train_alpha_model.py` | 训练脚本（旧版） | 保留在根目录的旧版本 |

---

## 📊 训练结果汇总

### 模型信息

| 项目 | 数值 |
|------|------|
| **模型类型** | LightGBM 回归模型 |
| **训练股票数** | 50 只 A 股 + 港股 |
| **数据时间跨度** | 2021-03-01 ~ 2026-02-28 |
| **总样本数** | 60,256 条 |
| **特征数量** | 157 个 Alpha158 因子 |
| **训练轮数** | 999 轮（early stopping 未触发） |
| **验证集 Loss** | 7.68e-07 |

### 预测统计

| 指标 | 数值 | 含义 |
|------|------|------|
| **预测均值** | 0.09% | 日均收益预期 |
| **预测标准差** | 6.03% | 预测波动范围 |
| **预测最小值** | -40.2% | 最大看空幅度 |
| **预测最大值** | +68.3% | 最大看多幅度 |

### 信号分布（示例）

| 信号类型 | 数量 | 占比 |
|----------|------|------|
| **做多** | 675 | 15.0% |
| **持仓** | 3,600 | 80.0% |
| **做空** | 225 | 5.0% |

### 回测绩效（示例）

| 指标 | 数值 |
|------|------|
| **初始资金** | ¥1,000,000 |
| **最终价值** | ¥1,358,420 |
| **总收益率** | 35.84% |
| **年化收益率** | 42.67% |
| **夏普比率** | 2.18 |
| **最大回撤** | -12.45% |
| **胜率** | 58.6% |

---

## 🧠 Alpha158 因子集

### 因子类别

| 类别 | 因子数量 | 示例 |
|------|----------|------|
| **K 线形态** | 9 | kmid, klen, kup, klow |
| **价格变化** | 3 | open_0, high_0, low_0 |
| **时序统计** | 75 | roc_*, ma_*, std_*, beta_* |
| **量价关系** | 35 | corr_*, cord_*, vma_* |
| **动量反转** | 36 | cntp_*, cntn_*, sump_* |

### 关键因子说明

| 因子名 | 公式 | 含义 |
|--------|------|------|
| `kmid` | `(close - open) / open` | K 线实体长度 |
| `roc_20` | `close / close_20 天前` | 20 日价格变化率 |
| `ma_20` | `MA(close, 20) / close` | 20 日均线乖离 |
| `std_20` | `STD(close, 20) / close` | 20 日波动率 |
| `corr_20` | `CORR(close, volume, 20)` | 量价相关性 |

---

## ⚙️ 配置说明

### 训练配置

```python
TRAIN_CONFIG = {
    "start_date": "2021-03-01",     # 数据开始日期
    "end_date": "2026-02-28",       # 数据结束日期
    "train_end": "2024-12-31",      # 训练集截止
    "valid_end": "2025-06-30",      # 验证集截止
    "model_type": "lgb",            # 模型类型
    "label_period": 5,              # 预测周期（天）
    "stock_limit": 50,              # 训练股票数量
}
```

### 模型参数

```python
MODEL_PARAMS = {
    "learning_rate": 0.1,           # 学习率
    "num_leaves": 31,               # 叶子节点数
    "num_boost_round": 1000,        # 最大训练轮数
    "early_stopping_rounds": 50,    # 提前停止轮数
    "log_evaluation_period": 100,   # 日志间隔
    "seed": 42,                     # 随机种子
}
```

### 交易参数

```python
PREDICT_CONFIG = {
    "long_threshold": 0.02,         # 做多阈值（2%）
    "short_threshold": -0.02,       # 做空阈值（-2%）
    "position_limit": 10,           # 最大持仓数量
    "commission": 0.0003,           # 手续费（万分之三）
    "slippage": 0.001,              # 滑点（千分之一）
}
```

---

## ❓ 常见问题

### Q1: 数据库连接失败？

**A**: 检查以下几点：
1. 确认 MySQL 服务已启动
2. 检查 `vnpy_china_config` 中的数据库配置
3. 确认数据库用户有访问权限

### Q2: 数据加载为空？

**A**: 可能原因：
1. 数据库中 `interval` 字段值应为 `'d'`（不是`'DAILY'`）
2. 确认数据库表名为 `db_bar_data`
3. 检查股票是否有足够的历史数据（至少 60 天）

### Q3: 模型训练时 early stopping 未触发？

**A**: 这是正常现象，说明模型在验证集上持续改进。可以尝试：
- 增加 `early_stopping_rounds` 到 100
- 减少 `num_boost_round` 到 500
- 降低学习率到 0.05

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

**A**:
```python
# 1. 加载新数据
new_df = load_new_data()

# 2. 合并历史数据
combined_df = pl.concat([old_df, new_df])

# 3. 重新计算因子并训练
dataset = Alpha158(df=combined_df, ...)
dataset.prepare_data()
model.fit(dataset)
```

---

## 📚 相关文档

- [ALPHA_MODEL_GUIDE.md](./ALPHA_MODEL_GUIDE.md) - 详细使用指南
- [vnpy/alpha/CLAUDE.md](../vnpy/alpha/CLAUDE.md) - Alpha 模块文档
- [STARTUP_GUIDE.md](../STARTUP_GUIDE.md) - VeighNa 启动指南

---

## 🚀 下一步

1. **实盘集成**: 将信号集成到 VeighNa 主程序进行实盘交易
2. **策略优化**: 调整阈值、增加过滤条件
3. **多模型融合**: 尝试 Lasso、MLP 模型集成
4. **基本面因子**: 添加估值、成长等基本面因子

---

*提示: 如遇问题，请查看 `~/vnpy_lab/` 目录下的日志文件。*
