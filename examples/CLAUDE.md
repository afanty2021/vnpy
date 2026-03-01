[根目录](../../CLAUDE.md) > **examples**

# Examples - 示例应用集合

> 更新时间：2026-02-28

## 模块职责

Examples目录提供了VeighNa框架的各种使用示例，帮助开发者快速理解框架功能并上手开发。包括完整的交易应用、无界面运行模式、分布式部署示例等多种场景。

## 示例列表

### 1. veighna_trader - 完整的GUI交易应用
**路径**: `veighna_trader/run.py`

**功能描述**:
- 完整的图形界面交易应用
- 集成了多个交易接口（CTP、Mini、Femas等）
- 包含常用功能模块（CTA策略、回测、数据管理等）
- 适合日常交易和策略开发

**关键特性**:
- 支持多网关同时连接
- 模块化架构，可按需启用功能
- 完整的GUI界面，包含所有监控窗口

**使用方法**:
```bash
cd examples/veighna_trader
python run.py
```

### 2. no_ui - 无界面交易守护进程
**路径**: `no_ui/run.py`

**功能描述**:
- 无界面的后台交易程序
- 支持父子进程架构，自动管理生命周期
- 根据交易时间自动启停
- 适合服务器部署和量化实盘

**关键特性**:
- 双进程架构：父进程监控、子进程交易
- 自动识别交易时段
- 进程异常自动重启
- 完整的日志记录

**架构设计**:
- 父进程：监控交易时段，管理子进程生命周期
- 子进程：实际运行交易策略
- 自动在非交易时段退出，节省资源

### 3. client_server - 分布式部署示例
**路径**: `client_server/`

**功能描述**:
- 展示如何将交易系统和界面分离部署
- 基于RPC服务实现分布式通信
- 支持GUI和终端两种运行模式

**关键组件**:
- `run_server.py`: 交易服务端
- `run_client.py`: 客户端连接示例

**使用场景**:
- 交易程序部署在服务器
- 监控界面运行在本地
- 多个客户端同时监控同一交易实例

### 4. candle_chart - K线图表示例
**路径**: `candle_chart/run.py`

**功能描述**:
- 展示如何使用Chart组件创建K线图表
- 包含实时数据更新和交互功能
- 适合学习图表组件的使用方法

### 5. simple_rpc - RPC基础示例
**路径**: `simple_rpc/`

**功能描述**:
- 最简单的RPC服务示例
- 展示基础的客户端-服务端通信
- 适合理解RPC服务的基本原理

### 6. notebook_trading - Jupyter笔记本交易示例
**路径**: `notebook_trading/demo_notebook.ipynb`

**功能描述**:
- 展示如何在Jupyter Notebook中进行交互式交易开发
- 集成了事件引擎、数据订阅、策略执行等完整流程
- 适合量化研究和策略原型开发
- 支持实时数据展示和交互式调试

**关键特性**:
- 交互式单元格执行，方便调试
- 实时K线数据可视化
- 策略信号回测展示
- 完整的交易生命周期演示

**运行环境**:
- Python 3.13.9 (通过ipykernel)
- Jupyter Notebook/Lab
- 推荐使用conda或venv虚拟环境

**使用方法**:
```bash
cd examples/notebook_trading
jupyter notebook demo_notebook.ipynb
```

### 7. alpha_research - Alpha 量化研究示例
**路径**: `alpha_research/`

**功能描述**:
- Alpha 因子研究和探索
- 包含多个研究脚本和策略示例
- 适合学习 Alpha 因子开发流程

### 8. alpha_model_training - Alpha 模型训练示例
**路径**: `alpha_model_training.py`

**功能描述**:
- 从 MySQL 数据库加载历史行情数据
- 使用 vnpy.alpha 模块训练 LightGBM 模型
- 基于 Alpha158 因子集（158 个技术指标）
- 适合量化研究和机器学习策略开发

**关键特性**:
- 支持多股票批量数据加载
- 自动计算 158 个 Alpha 因子
- 训练集/验证集/测试集自动划分
- 模型自动保存和特征重要性展示

**使用方法**:
```bash
python examples/alpha_model_training.py
```

**输出文件**:
- `~/vnpy_lab/model/a_stock_lgb.txt` - 训练好的 LightGBM 模型
- `~/vnpy_lab/dataset/a_stock_dataset.pkl` - 处理后的数据集

### 9. alpha_model_prediction - Alpha 模型预测示例
**路径**: `alpha_model_prediction.py`

**功能描述**:
- 使用已训练的模型生成当日交易信号
- 根据预测收益率生成做多/做空/持仓信号
- 提供信号统计分析和可视化

**关键特性**:
- 支持自定义交易信号阈值
- 自动生成信号分析图表
- 按股票和日期分组统计
- Top 做多/做空股票排名

**使用方法**:
```bash
python examples/alpha_model_prediction.py
```

**输出文件**:
- `~/vnpy_lab/signals/signals_YYYY-MM-DD.csv` - 每日交易信号
- `~/vnpy_lab/signal_analysis.png` - 信号分析图表

### 10. alpha_model_backtest - Alpha 模型回测示例
**路径**: `alpha_model_backtest.py`

**功能描述**:
- 使用历史数据验证模型交易效果
- 包含完整的回测引擎（手续费、滑点、仓位管理）
- 提供详细的绩效指标和可视化

**关键特性**:
- 支持自定义回测周期
- 包含手续费和滑点成本
- 最大持仓数量控制
- 年化收益率、夏普比率、最大回撤等指标

**使用方法**:
```bash
python examples/alpha_model_backtest.py
```

**输出文件**:
- `~/vnpy_lab/backtest_results.png` - 回测结果图表

### 11. data_recorder - 数据记录示例
**路径**: `data_recorder/data_recorder.py`

**功能描述**:
- 展示如何记录和保存市场数据
- 支持多种数据格式和存储方式
- 适合搭建自己的数据服务器

## 使用指南

### 选择合适的示例

1. **初学者**: 从`veighna_trader`开始，了解完整的GUI应用
2. **量化开发**: 参考`no_ui`学习服务器部署
3. **分布式需求**: 查看`client_server`了解架构设计
4. **图表开发**: 研究`candle_chart`学习Chart组件
5. **数据管理**: 使用`data_recorder`搭建数据服务

### 配置说明

大部分示例需要配置以下内容：
1. **交易接口配置**: 用户名、密码、服务器地址等
2. **数据库配置**: SQLite/MySQL等数据库连接
3. **策略参数**: 根据实际策略调整参数

### 最佳实践

1. **开发环境**: 先在`veighna_trader`中开发和测试
2. **实盘部署**: 使用`no_ui`模式部署到服务器
3. **监控管理**: 通过`client_server`实现远程监控
4. **数据备份**: 使用`data_recorder`记录重要数据

## 常见问题 (FAQ)

### Q: 如何选择合适的示例？
A: 根据你的需求选择：需要GUI选veighna_trader，服务器部署选no_ui，分布式架构选client_server。

### Q: 示例中的接口配置如何获取？
A: 需要从相应的期货公司或券商申请，SimNow提供免费的模拟环境。

### Q: no_ui模式如何更新策略？
A: 需要重启子进程，或通过RPC接口实现热更新。

### Q: client_server支持多客户端吗？
A: 是的，支持多个客户端同时连接同一个服务端。

## 相关文件清单

- `veighna_trader/run.py` - 主GUI应用
- `veighna_trader/demo_script.py` - 演示脚本
- `no_ui/run.py` - 无界面交易程序
- `client_server/run_server.py` - 服务端程序
- `client_server/run_client.py` - 客户端程序
- `candle_chart/run.py` - K线图表示例
- `candle_chart/simple_chart.py` - 简化K线图表示例
- `simple_rpc/test_server.py` - RPC测试服务端
- `simple_rpc/test_client.py` - RPC测试客户端
- `notebook_trading/demo_notebook.ipynb` - Jupyter笔记本交易示例
- `data_recorder/data_recorder.py` - 数据记录程序
- `alpha_research/` - Alpha 因子研究示例目录
- `alpha_model_training.py` - Alpha 模型训练脚本
- `alpha_model_prediction.py` - Alpha 模型预测脚本
- `alpha_model_backtest.py` - Alpha 模型回测脚本
- `ALPHA_MODEL_GUIDE.md` - Alpha 模型详细使用指南
- `README_ALPHA.md` - Alpha 模型快速入门指南

## 变更记录 (Changelog)

### 2026-02-28
- 📈 **新增 Alpha 模型系列示例**：添加机器学习模型训练、预测和回测脚本
  - `alpha_model_training.py` - 模型训练脚本
  - `alpha_model_prediction.py` - 信号生成脚本
  - `alpha_model_backtest.py` - 历史回测脚本
  - `ALPHA_MODEL_GUIDE.md` - 详细使用指南
  - `README_ALPHA.md` - 快速入门指南
- 🔧 **Alpha 模型实战案例**：
  - 基于 Alpha158 因子集（157 个特征）
  - LightGBM 模型（999 棵树，验证集 Loss: 7.68e-07）
  - 50 只 A 股，60,256 条样本数据
  - 模型保存至 `~/vnpy_lab/model/a_stock_lgb.txt`

### 2026-01-18
- 📈 **新增notebook_trading示例**：添加Jupyter笔记本交易示例说明
- 🔧 **demo_notebook配置更新**（提交bc499df8）：
  - 清理单元格元数据（移除scrolled字段）
  - 更新Python内核版本：3.7.4 -> 3.13.9
  - 更新nbformat版本：2 -> 4
- 📝 文档时间戳同步更新

### 2025-12-09 11:44:15
- ✨ 创建examples模块文档
- 📊 整理所有示例应用的说明
- 🔧 添加使用指南和最佳实践
- 📝 提供常见问题解答

---

*提示：建议按照文档顺序学习示例，从简单的GUI应用到复杂的多进程架构。*

<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Feb 25, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #6681 | 12:22 AM | 🟣 | REQ-008 market analysis system implementation completed and committed | ~353 |
</claude-mem-context>