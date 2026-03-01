# Alpha158 特征工程训练脚本使用指南

## 概述

`train_alpha158_model.py` 是一个用于训练 Alpha158 因子模型的命令行脚本。该脚本从 MySQL 数据库加载历史行情数据，计算 158 个技术因子，并训练 LightGBM 模型用于预测股票收益率。

## 功能特性

- 使用 Alpha158 因子集（157 个特征 + 1 个标签）
- 从 MySQL 数据库加载 QMT 历史数据
- 支持命令行参数配置
- 自动划分训练集、验证集、测试集
- 生成特征重要性图表

## 安装依赖

```bash
pip install vnpy polars numpy lightgbm matplotlib pymysql pyarrow
```

## 使用方法

### 基本用法

```bash
python examples/train_alpha158_model.py \
    --symbols "000001,000002" \
    --start-date "2021-01-01" \
    --end-date "2024-12-31"
```

### 命令行参数

| 参数 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `--symbols` | 是 | 股票代码列表，逗号分隔 | `"000001,000002"` |
| `--start-date` | 是 | 开始日期（YYYY-MM-DD） | `"2021-01-01"` |
| `--end-date` | 是 | 结束日期（YYYY-MM-DD） | `"2024-12-31"` |
| `--num-boost-round` | 否 | 训练轮数，默认 1000 | `2000` |

### 高级用法

```bash
# 使用更多训练轮数
python examples/train_alpha158_model.py \
    --symbols "000001,000002,600000" \
    --start-date "2021-01-01" \
    --end-date "2024-12-31" \
    --num-boost-round 2000
```

## 输出文件

训练完成后，脚本会生成以下文件：

1. **模型文件**: `~/vnpy_lab/model/alpha158_lgb.txt`
   - 训练好的 LightGBM 模型
   - 可用于后续预测

2. **特征重要性图表**: `~/vnpy_lab/feature_importance.png`
   - 展示前 30 个最重要的特征
   - 帮助理解模型预测依据

## Alpha158 因子说明

Alpha158 是源自微软 Qlib 项目的经典因子集，包含以下类型的因子：

### 蜡烛图形态因子（9个）
- kmid, klen, kmid_2, kup, kup_2, klow, klow_2, ksft, ksft_2

### 价格变化因子（3个）
- open_0, high_0, low_0

### 时间序列因子（146个）
- 收益率因子：roc_5, roc_10, roc_20, roc_30, roc_60
- 均线因子：ma_5, ma_10, ma_20, ma_30, ma_60
- 标准差因子：std_5, std_10, std_20, std_30, std_60
- Beta因子：beta_5, beta_10, beta_20, beta_30, beta_60
- R平方因子：rsqr_5, rsqr_10, rsqr_20, rsqr_30, rsqr_60
- 残差因子：resi_5, resi_10, resi_20, resi_30, resi_60
- 最大值因子：max_5, max_10, max_20, max_30, max_60
- 最小值因子：min_5, min_10, min_20, min_30, min_60
- 分位数因子：qtlu_5/10/20/30/60, qtld_5/10/20/30/60
- 排序因子：rank_5/10/20/30/60
- RSV因子：rsv_5/10/20/30/60
- 极值位置因子：imax_5/10/20/30/60, imin_5/10/20/30/60, imxd_5/10/20/30/60
- 相关性因子：corr_5/10/20/30/60, cord_5/10/20/30/60
- 上涨下跌因子：cntp_5/10/20/30/60, cntn_5/10/20/30/60, cntd_5/10/20/30/60
- 上涨下跌和因子：sump_5/10/20/30/60, sumn_5/10/20/30/60, sumd_5/10/20/30/60
- 成交量因子：vma_5/10/20/30/60, vstd_5/10/20/30/60, wvma_5/10/20/30/60
- 成交量变化因子：vsump_5/10/20/30/60, vsumn_5/10/20/30/60, vsumd_5/10/20/30/60

### 标签（1个）
- 5 日远期收益率：`ts_delay(close, 5) / close - 1`

## 数据集划分

脚本自动将数据划分为三个部分：

- **训练集（70%）**: 用于训练模型
- **验证集（15%）**: 用于调整超参数和早停
- **测试集（15%）**: 用于评估最终模型性能

## 模型评估指标

训练完成后，脚本会输出以下评估指标：

- **MAE (Mean Absolute Error)**: 平均绝对误差
- **RMSE (Root Mean Square Error)**: 均方根误差
- **IC (Information Coefficient)**: 信息系数（预测值与真实值的相关系数）

## 常见问题

### Q: 如何选择股票代码？
A: 建议选择流动性好、历史数据完整的股票。可以先用少量股票测试，再逐步增加。

### Q: 训练需要多长时间？
A: 取决于数据量和训练轮数。通常 2-3 只股票、3 年数据、1000 轮训练需要 5-10 分钟。

### Q: 如何调整模型参数？
A: 可以修改 `train_alpha158_model.py` 中的 `LgbModel` 初始化参数：
- `learning_rate`: 学习率（默认 0.1）
- `num_leaves`: 叶子节点数（默认 31）
- `early_stopping_rounds`: 早停轮数（默认 50）

### Q: 模型预测效果不好怎么办？
A: 可以尝试：
1. 增加训练数据量（更多股票或更长历史）
2. 调整数据集划分比例
3. 优化模型超参数
4. 检查数据质量

## 示例输出

```
======================================================================
 Alpha158 特征工程训练
======================================================================

正在从 MySQL 加载数据...
  股票代码: 000001, 000002
  日期范围: 2021-01-01 ~ 2024-12-31
  ✓ 加载了 1956 条记录
  ✓ 日期范围: 2021-01-01 ~ 2024-12-31
  ✓ 股票数量: 2

正在准备 Alpha158 数据集...
  训练集: 2021-01-01 ~ 2023-05-20
  验证集: 2023-05-21 ~ 2024-01-24
  测试集: 2024-01-25 ~ 2024-12-31

正在计算 Alpha158 因子...
[100%]████████████ 158/158
  ✓ 因子计算完成

正在创建 LightGBM 模型...

正在训练模型（最多 1000 轮）...
[100] train's l2: 0.001234 valid's l2: 0.004567

正在评估模型...
  测试集评估:
    MAE:  0.012345
    RMSE: 0.045678
    IC:   0.123456

正在保存模型...
模型已保存到：/Users/username/vnpy_lab/model/alpha158_lgb.txt
  ✓ 模型已保存到: /Users/username/vnpy_lab/model/alpha158_lgb.txt

正在生成特征重要性图表...
  ✓ 图表已保存到: /Users/username/vnpy_lab/feature_importance.png

======================================================================
 训练完成！
======================================================================

输出文件:
  - 模型: /Users/username/vnpy_lab/model/alpha158_lgb.txt
  - 特征重要性: /Users/username/vnpy_lab/feature_importance.png
```

## 参考资料

- [VeighNa Alpha 模块文档](../vnpy/alpha/CLAUDE.md)
- [Alpha158 因子源码](../vnpy/alpha/dataset/datasets/alpha_158.py)
- [LightGBM 官方文档](https://lightgbm.readthedocs.io/)
