# VeighNa 4.2.0 开发版启动指南

> 更新时间：2025-12-09
> 适用于：已通过pip install -e .安装的开发版

## 🎉 恭喜！VeighNa开发版已成功安装

本指南将帮助您快速开始使用VeighNa量化交易框架。

## 🚀 快速开始

### 1. 验证安装（推荐首先执行）

```bash
# 运行快速测试，验证所有功能正常
python test_quick.py
```

### 2. 运行示例应用

#### 无需交易接口的示例：

```bash
# K线图表展示
cd examples/candle_chart
python run.py

# Alpha量化研究（需要Jupyter）
cd examples/alpha_research
jupyter notebook
```

### 3. 启动完整交易应用

如果您需要连接交易接口：

```bash
# 安装CTP接口（国内期货）
pip install vnpy_ctp

# 运行完整GUI应用
cd examples/veighna_trader
python run.py
```

## 📋 功能模块说明

### 核心功能（已安装）
- ✅ **事件引擎** - 高性能事件驱动架构
- ✅ **主引擎** - 统一的交易、行情、风控管理
- ✅ **GUI框架** - 基于PySide6的现代化界面
- ✅ **数据管理** - 支持多种数据库
- ✅ **图表组件** - 高性能K线图表

### Alpha量化研究（已安装）
- ✅ **特征工程** - Alpha 158因子集
- ✅ **模型训练** - LightGBM/MLP/Lasso
- ✅ **策略回测** - 完整的回测引擎
- ✅ **投研管理** - AlphaLab工作流

### 交易接口（可选安装）
- ⭕ **国内期货** - CTP、CTP Mini、CTP Sopt
- ⭕ **国内证券** - XTP、TORA、华盛通
- ⭕ **海外市场** - Interactive Brokers
- ⭕ **数据服务** - RQData、迅投研、TuShare

## 🔧 配置选项

### 选项1：纯测试模式（推荐新手）
```bash
# 1. 运行基础测试
python test_quick.py

# 2. 查看图表示例
cd examples/candle_chart
python run.py
```

### 选项2：模拟交易模式
```bash
# 1. 注册SimNow账号（免费）
#    网址：https://www.simnow.com.cn/

# 2. 安装CTP接口
pip install vnpy_ctp

# 3. 运行应用并配置SimNow账号
cd examples/veighna_trader
python run.py
```

### 选项3：实盘交易模式
```bash
# 1. 申请期货/证券账户
# 2. 安装对应交易接口
pip install vnpy_ctp  # 期货
pip install vnpy_xtp  # 证券

# 3. 配置实盘账号信息
# 4. 运行应用
cd examples/veighna_trader
python run.py
```

## 📚 学习路径

### 初学者
1. 先运行`test_quick.py`熟悉环境
2. 查看`examples/candle_chart`学习图表使用
3. 阅读[官方文档](https://www.vnpy.com/docs)

### 量化开发者
1. 学习`examples/alpha_research`中的 notebooks
2. 了解Alpha模块的使用方法
3. 开始策略开发

### 交易者
1. 注册SimNow模拟账号
2. 安装CTP接口
3. 运行`veighna_trader`开始模拟交易

## 🛠️ 常用命令

```bash
# 查看已安装的包
pip list | grep vnpy

# 安装额外功能
pip install vnpy_ctastrategy  # CTA策略模块
pip install vnpy_portfoliostrategy  # 组合策略模块
pip install vnpy_algotrading  # 算法交易模块

# 运行代码检查
ruff check .
mypy vnpy
```

## 📖 资源链接

- **官方文档**: https://www.vnpy.com/docs
- **社区论坛**: https://www.vnpy.com/forum
- **GitHub仓库**: https://github.com/vnpy/vnpy
- **SimNow模拟**: https://www.simnow.com.cn/

## ❓ 常见问题

### Q: 如何开始策略开发？
A: 查看`examples/alpha_research`中的示例，学习Alpha模块的使用方法。

### Q: 支持哪些交易品种？
A: 支持期货、期权、股票、ETF、外汇等，具体取决于安装的交易接口。

### Q: 如何获取历史数据？
A: 可以通过RQData、TuShare等数据服务获取，或者使用交易接口下载。

### Q: 如何进行回测？
A: 使用vnpy_ctastrategy或vnpy_alpha模块中的回测功能。

### Q: 遇到问题怎么办？
A: 查看官方文档、搜索论坛，或在GitHub提交Issue。

## ✅ 检查清单

- [ ] 运行`python test_quick.py`验证安装
- [ ] 查看`examples/`目录中的示例
- [ ] 根据需要安装交易接口
- [ ] 配置数据源（如需要）
- [ ] 开始策略开发或模拟交易

## 🎯 下一步

现在您已经：
1. ✅ 成功安装了VeighNa 4.2.0开发版
2. ✅ 验证了所有核心功能正常
3. ✅ 了解了配置选项

**开始您的量化交易之旅吧！** 🚀