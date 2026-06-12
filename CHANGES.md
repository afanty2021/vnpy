# VeighNa 变更记录 (Changelog)

> 本文档记录 VeighNa 量化交易框架的所有重要变更

## 2026-03-01

### ✨ Alpha158 因子集训练
使用 Microsoft Qlib 的 157 个技术因子进行模型训练

**实现内容：**
- `examples/train_alpha158_model.py` - 从 MySQL 数据库加载 QMT 数据，计算 Alpha158 因子，训练 LightGBM 模型
- 环境变量配置支持（MySQL 凭据）
- 模型持久化保存到 `~/vnpy_lab/model/alpha158_lgb.txt`
- `examples/TRAIN_ALPHA158_GUIDE.md` - 详细使用指南

### 🚀 RPC 实时信号生成
结合 RPC-QMT 连接实现实时交易信号生成

**实现内容：**
- `examples/rpc_realtime_signals.py` - 通过 RPC 连接获取实时行情，使用 Alpha158 因子集计算特征，生成交易信号
- 因子缓存优化（性能提升 50-70%）
- RPC 自动重连机制（最多重试 3 次）
- 丰富的终端 UI 实时显示信号
- `examples/RPC_REALTIME_SIGNALS_GUIDE.md` - 详细使用指南
- `examples/rpc_realtime_signals_README.md` - 历史数据加载指南

### 🔧 子代理驱动开发
使用 superpowers:subagent-driven-development 技能完成实现

- 严格的规范审查 → 代码质量审查流程
- 两轮审查修复（安全、性能、错误处理）
- 最终评分：train_alpha158_model.py 通过，rpc_realtime_signals.py 9.5/10

## 2026-02-28

### 📈 Alpha 模型实战案例
添加 A 股机器学习模型训练完整工作流

**实现内容：**
- ✅ **数据加载**：从 MySQL 数据库加载 50 只股票的 5 年历史数据（60,256 条样本）
- ✅ **特征工程**：使用 Alpha158 因子集（157 个特征）
- ✅ **模型训练**：LightGBM 回归模型（999 棵树，验证集 Loss: 7.68e-07）
- ✅ **信号生成**：根据预测收益率生成做多/做空/持仓信号
- ✅ **历史回测**：包含手续费、滑点、仓位管理的完整回测引擎

**新增示例脚本：**
- `examples/alpha_model_training.py` - 模型训练脚本
- `examples/alpha_model_prediction.py` - 信号生成脚本
- `examples/alpha_model_backtest.py` - 历史回测脚本
- `examples/ALPHA_MODEL_GUIDE.md` - 详细使用指南
- `examples/README_ALPHA.md` - 快速入门指南

**模型保存位置：**
- 模型文件：`~/vnpy_lab/model/a_stock_lgb.txt` (~3MB)
- 数据集：`~/vnpy_lab/dataset/a_stock_dataset.pkl` (~152MB)

## 2026-02-27

### 🔧 vnpy_qmt 补丁（外部包修复）

- 创建 `patches/` 目录跟踪外部依赖包修复
- 添加 vnpy_qmt 历史数据下载修复补丁
- 修复 Interval 枚举引用错误（MINUTE_5/15/30 不存在）
- 添加两步数据下载流程（download_history_data2 → get_local_data）
- 创建自动部署脚本 `patches/deploy_vnpy_qmt_fix.py`

### 📝 miniQMT 调研报告（提交b623fb40）

- 添加 `docs/reports/miniQMT历史数据下载问题调研报告.md`
- 记录问题根本原因、修复方案和测试结果
- 确认 A 股和香港本地股票历史数据可用
- 港股通（SHHK/SZHK）暂不支持

### ✅ QMT 测试脚本（提交6680c06f）

- 添加 `test_qmt_simple.py` - A股基础测试
- 添加 `test_qmt_history.py` - QMT 接口测试
- 添加 `test_hk_stock_connect.py` - 港股通综合测试
- 添加 `test_xtdata_direct.py` - API 直接测试

## 2026-01-18

### 🐛 Bug修复（提交fe2697a8, PR#3721）

- 修复LogEngine中loguru日志记录时的KeyError问题
- 将logger.log()的gateway_name参数改为使用logger.bind()方法
- 正确绑定到loguru的extra上下文中（Issue #3715）

### 🔧 示例应用优化（提交bc499df8）

- demo_notebook配置更新：Python内核3.7.4->3.13.9
- 清理单元格元数据，更新nbformat版本

### 📚 文档完善

- examples模块新增notebook_trading示例说明
- 同步examples模块文档至2026-01-18

### 🔄 上游同步（提交c1bc4c3d）

- 合并upstream/master最新代码

## 2026-01-11

### 📈 版本升级到4.3.0
同步上游最新版本

### 📚 文档资源完善

- 新增 `STARTUP_GUIDE.md` 启动指南
- 新增 `demo_app.py` 功能演示应用
- 新增 `examples/candle_chart/simple_chart.py` 简化图表示例
- 新增 `test_quick.py`、`test_basic.py`、`test_simple.py` 测试文件

### 🔧 核心代码改进（提交b08f9422, cb29c5cb, 5881a61b）

- 重构 `ts_slope` / `ts_rsquare` / `ts_resi` 算子函数
- DataProxy的所有比较运算，直接返回pl.Int32（而不是Bool）

### 📊 更新模块索引
examples模块新增简化图表示例

## 2025-12-23

- 📈 **文档覆盖率100%**：所有7个模块CLAUDE.md文档完成
- 📊 更新时间戳至2025-12-23
- 🔄 同步最新代码库状态

## 2025-12-09 16:23:49

- 📝 添加VeighNa中文知识库完整文档（提交：e554ecf9）
- 📚 完善核心模块文档体系

## 2025-12-09 11:44:15

- ✨ 更新覆盖率至95%（61个文件，扫描58个）
- 📊 深入分析GUI系统（MainWindow和各种Monitor组件）
- 🔧 完善Chart组件文档（基于PyQtGraph的高性能图表）
- 📝 添加Examples模块文档（6个示例应用说明）
- 🚀 新增分布式部署和RPC服务说明
- 💡 补充Alpha 158因子集和模型实现细节

## 2025-12-09 11:33:34

- ✨ 创建VeighNa量化交易框架文档体系
- 📊 完成核心模块架构梳理（trader/alpha/event/chart/rpc）
- 🔧 整理AI量化研究功能（vnpy.alpha模块）
- 📝 建立模块间依赖关系图
- 🚀 提供快速启动指南和开发规范
