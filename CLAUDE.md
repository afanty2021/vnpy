# VeighNa量化交易框架

> 更新时间：2026-02-28
> 版本：4.3.0
> AI驱动的一站数量化交易平台

## 本地环境配置

### Conda 环境
- **环境名称**: Quant-3.11
- **Python 版本**: 3.11
- **安装路径**: D:\scoop\apps\miniconda\current\envs\Quant-3.11(windows);
- /opt/homebrew/caskroom/miniconda/base(mac os)

### 已安装的包
- vnpy (核心框架)
- vnpy_tushare (Tushare数据接口)
- vnpy_qmt (QMT证券交易接口) - **已应用补丁** (见 patches/ 目录)

### QMT 配置
- **QMT 账号**: ******
- **MiniQMT 路径**: D:/国金证券QMT交易端/userdata_mini/  (**注意：不是主目录，是userdata_mini子目录**)
- **xtquant 模块**: 已复制到 conda 环境 site-packages

### 启动命令
```bash
# 启动 QMT 交易客户端
conda run -n Quant-3.11 python examples/veighna_trader/run_qmt.py

# 启动演示应用
conda run -n Quant-3.11 python demo_app.py
```

> ⚠️ **重要：MiniQMT 路径必须是 userdata_mini 子目录！**
>
> 错误路径：`D:/国金证券QMT交易端/` ❌
> 正确路径：`D:/国金证券QMT交易端/userdata_mini/` ✅
>
> 注意：运行 QMT 接口时需要保持 MiniQMT 客户端登录状态

## 项目愿景

VeighNa（原VN.Py）是一套基于Python的开源量化交易系统开发框架，自2015年发布以来已经发展成为功能全面的多功能量化交易平台。4.0版本重磅推出AI驱动的vnpy.alpha模块，为专业量化交易员提供一站式多因子机器学习策略开发、投研和实盘交易解决方案。

## 架构总览

### 核心架构特点
- **事件驱动架构**：基于EventEngine的松耦合设计，支持高性能事件处理
- **模块化设计**：采用插件式架构，各功能模块独立开发和部署
- **跨平台支持**：支持Windows、Linux、macOS三大操作系统
- **丰富的交易接口**：支持国内外主流期货、证券、期权等交易品种

### 技术栈
- **核心语言**：Python 3.10+
- **GUI框架**：PySide6
- **数据处理**：Pandas, Polars, NumPy
- **机器学习**：PyTorch, LightGBM, scikit-learn
- **技术分析**：TA-Lib
- **可视化**：Plotly, PyQtGraph
- **通信框架**：ZeroMQ (RPC服务)

## ✨ 模块结构图

```mermaid
graph TD
    A["(根) VeighNa量化交易框架"] --> B["vnpy"];
    A --> H["examples<br/>示例应用"];

    B --> C["trader<br/>交易核心"];
    B --> D["alpha<br/>AI量化研究"];
    B --> E["event<br/>事件引擎"];
    B --> F["chart<br/>图表组件"];
    B --> G["rpc<br/>RPC通信"];

    C --> C1["engine<br/>主引擎"];
    C --> C2["object<br/>数据对象"];
    C --> C3["gateway<br/>交易接口"];
    C --> C4["app<br/>应用基类"];
    C --> C5["ui<br/>界面组件"];
    C5 --> C51["mainwindow<br/>主窗口"];
    C5 --> C52["widget<br/>通用组件"];

    D --> D1["dataset<br/>特征工程"];
    D --> D2["model<br/>模型训练"];
    D --> D3["strategy<br/>策略开发"];
    D --> D4["lab<br/>投研管理"];

    D1 --> D11["Alpha 158因子集"];
    D1 --> D12["表达式引擎"];
    D1 --> D13["时序/截面函数"];

    D2 --> D21["Lasso回归"];
    D2 --> D22["LightGBM"];
    D2 --> D23["MLP神经网络"];

    H --> H1["veighna_trader<br/>GUI交易应用"];
    H --> H2["no_ui<br/>无界面守护进程"];
    H --> H3["client_server<br/>分布式部署"];
    H --> H4["candle_chart<br/>K线图表示例"];

    click C "./vnpy/trader/CLAUDE.md" "查看 trader 模块文档"
    click D "./vnpy/alpha/CLAUDE.md" "查看 alpha 模块文档"
    click E "./vnpy/event/CLAUDE.md" "查看 event 模块文档"
    click F "./vnpy/chart/CLAUDE.md" "查看 chart 模块文档"
    click G "./vnpy/rpc/CLAUDE.md" "查看 rpc 模块文档"
    click H "./examples/CLAUDE.md" "查看 examples 模块文档"
```

## 模块索引

| 模块名称 | 路径 | 类型 | 主要功能 | 核心组件 | 文档覆盖率 |
|---------|------|------|---------|---------|------------|
| **trader** | `vnpy/trader` | 核心 | 交易核心框架 | MainEngine, BaseGateway, BaseApp | 100% |
| **alpha** | `vnpy/alpha` | 功能 | AI量化研究模块 | AlphaDataset, AlphaModel, AlphaLab | 100% |
| **event** | `vnpy/event` | 核心 | 事件驱动引擎 | EventEngine, Event | 100% |
| **chart** | `vnpy/chart` | 功能 | 图表组件 | ChartWidget, CandleItem | 100% |
| **rpc** | `vnpy/rpc` | 功能 | RPC通信服务 | RpcClient, RpcServer | 100% |
| **examples** | `examples` | 示例 | 示例应用集合 | veighna_trader, no_ui, simple_chart, demo_app | 100% |

## 运行与开发

### 📖 启动前必读
项目根目录提供了 `STARTUP_GUIDE.md` 启动指南，包含：
- 环境验证命令 (`python test_quick.py`)
- 三种配置模式（纯测试/模拟交易/实盘交易）
- 学习路径推荐
- 常用命令和资源链接

### 快速启动
```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

def main():
    """启动VeighNa主界面"""
    qapp = create_qapp()

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加交易接口
    # main_engine.add_gateway(CtpGateway)

    # 添加应用模块
    # main_engine.add_app(CtaStrategyApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.show()

    qapp.exec()
```

### 🎯 演示应用（推荐新手）
项目根目录提供了 `demo_app.py` 功能演示应用：
- **零依赖**：无需交易接口或历史数据
- **完整演示**：展示事件引擎、主引擎、图表组件、Alpha模块
- **实时更新**：模拟实时K线数据更新

运行方式：
```bash
python demo_app.py
```

### 无界面模式
```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine

def main():
    """无界面运行模式"""
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加必要的网关和应用
    # main_engine.add_gateway(CtpGateway)

    # 运行策略
    # ...
```

### 分布式部署
```python
# 服务端
from vnpy.rpcservice import RpcServiceApp

main_engine.add_app(RpcServiceApp)
rpc_engine.start("tcp://0.0.0.0:2014", "tcp://0.0.0.0:4102")

# 客户端
from vnpy.rpc import RpcClient

rpc_client = RpcClient()
rpc_client.connect("tcp://127.0.0.1:2014", "tcp://127.0.0.1:4102")
```

## 测试策略

### 测试目录结构
- **根目录测试文件**：
  - `test_quick.py` - 快速验证所有核心功能
  - `test_basic.py` - 基础功能测试
  - `test_simple.py` - 简单功能演示
- **示例应用**：`examples/` - 示例代码和演示程序
- **回测引擎**：`vnpy/alpha/strategy/backtesting.py` - Alpha策略回测引擎
- 测试覆盖：主要通过示例应用验证功能

### 质量工具
- **代码检查**：Ruff (PEP8, flake8-bugbear, pyupgrade)
- **类型检查**：MyPy (严格模式)
- **国际化**：Babel (支持中英文)

## 编码规范

### 代码风格
- 遵循PEP 8编码规范
- 使用dataclass定义数据结构
- 采用类型注解(Type Hints)
- 严格的MyPy类型检查配置

### 模块开发规范
- 所有应用模块继承自`BaseApp`
- 交易接口继承自`BaseGateway`
- 使用事件驱动模式进行模块间通信
- 遵循统一的日志和错误处理机制

## AI使用指引

### AI量化开发流程
1. **数据准备**：使用`AlphaDataset`加载和处理历史数据
2. **特征工程**：利用内置的Alpha 158因子集或自定义表达式
3. **模型训练**：选择合适的算法（Lasso/LightGBM/MLP）
4. **策略回测**：通过`BacktestingEngine`验证策略效果
5. **实盘部署**：集成到主引擎进行实盘交易

### 最佳实践
- 使用`AlphaLab`管理完整的投研工作流
- 充分利用Polars进行高性能数据处理
- 通过`AlphaDataset`的append模式优化增量学习
- 使用Notebook进行交互式策略研发

## 集成应用

### 官方应用模块
- **CTA策略**：`vnpy_ctastrategy` - 经典CTA策略框架
- **算法交易**：`vnpy_algotrading` - 大单拆分算法
- **期权管理**：`vnpy_optionmaster` - 期权交易和管理
- **组合策略**：`vnpy_portfoliostrategy` - 多品种组合策略
- **数据管理**：`vnpy_datamanager` - 本地数据管理工具
- **RPC服务**：`vnpy_rpcservice` - 分布式部署支持
- **图表向导**：`vnpy_chartwizard` - 可视化图表工具

### 交易接口支持
- **国内期货**：CTP、CTP Mini、CTP Sopt、CTP UFT、Femas
- **国内证券**：XTP、TORA、华盛通、富途
- **国际市场**：Interactive Brokers (IB)、TAP

## 变更记录 (Changelog)

### 2026-03-01
- ✨ **Alpha158 因子集训练**：使用 Microsoft Qlib 的 157 个技术因子进行模型训练
  - `examples/train_alpha158_model.py` - 从 MySQL 数据库加载 QMT 数据，计算 Alpha158 因子，训练 LightGBM 模型
  - 环境变量配置支持（MySQL 凭据）
  - 模型持久化保存到 `~/vnpy_lab/model/alpha158_lgb.txt`
  - `examples/TRAIN_ALPHA158_GUIDE.md` - 详细使用指南
- 🚀 **RPC 实时信号生成**：结合 RPC-QMT 连接实现实时交易信号生成
  - `examples/rpc_realtime_signals.py` - 通过 RPC 连接获取实时行情，使用 Alpha158 因子集计算特征，生成交易信号
  - 因子缓存优化（性能提升 50-70%）
  - RPC 自动重连机制（最多重试 3 次）
  - 丰富的终端 UI 实时显示信号
  - `examples/RPC_REALTIME_SIGNALS_GUIDE.md` - 详细使用指南
  - `examples/rpc_realtime_signals_README.md` - 历史数据加载指南
- 🔧 **子代理驱动开发**：使用 superpowers:subagent-driven-development 技能完成实现
  - 严格的规范审查 → 代码质量审查流程
  - 两轮审查修复（安全、性能、错误处理）
  - 最终评分：train_alpha158_model.py 通过，rpc_realtime_signals.py 9.5/10

### 2026-02-28
- 📈 **Alpha 模型实战案例**：添加 A 股机器学习模型训练完整工作流
  - ✅ **数据加载**：从 MySQL 数据库加载 50 只股票的 5 年历史数据（60,256 条样本）
  - ✅ **特征工程**：使用 Alpha158 因子集（157 个特征）
  - ✅ **模型训练**：LightGBM 回归模型（999 棵树，验证集 Loss: 7.68e-07）
  - ✅ **信号生成**：根据预测收益率生成做多/做空/持仓信号
  - ✅ **历史回测**：包含手续费、滑点、仓位管理的完整回测引擎
- 📁 **新增示例脚本**：
  - `examples/alpha_model_training.py` - 模型训练脚本
  - `examples/alpha_model_prediction.py` - 信号生成脚本
  - `examples/alpha_model_backtest.py` - 历史回测脚本
  - `examples/ALPHA_MODEL_GUIDE.md` - 详细使用指南
  - `examples/README_ALPHA.md` - 快速入门指南
- 💾 **模型保存位置**：
  - 模型文件：`~/vnpy_lab/model/a_stock_lgb.txt` (~3MB)
  - 数据集：`~/vnpy_lab/dataset/a_stock_dataset.pkl` (~152MB)

### 2026-02-27
- 🔧 **vnpy_qmt 补丁**（外部包修复）：
  - 创建 `patches/` 目录跟踪外部依赖包修复
  - 添加 vnpy_qmt 历史数据下载修复补丁
  - 修复 Interval 枚举引用错误（MINUTE_5/15/30 不存在）
  - 添加两步数据下载流程（download_history_data2 → get_local_data）
  - 创建自动部署脚本 `patches/deploy_vnpy_qmt_fix.py`
- 📝 **miniQMT 调研报告**（提交b623fb40）：
  - 添加 `docs/reports/miniQMT历史数据下载问题调研报告.md`
  - 记录问题根本原因、修复方案和测试结果
  - 确认 A 股和香港本地股票历史数据可用
  - 港股通（SHHK/SZHK）暂不支持
- ✅ **QMT 测试脚本**（提交6680c06f）：
  - 添加 `test_qmt_simple.py` - A股基础测试
  - 添加 `test_qmt_history.py` - QMT 接口测试
  - 添加 `test_hk_stock_connect.py` - 港股通综合测试
  - 添加 `test_xtdata_direct.py` - API 直接测试

### 2026-01-18
- 🐛 **Bug修复**（提交fe2697a8, PR#3721）：
  - 修复LogEngine中loguru日志记录时的KeyError问题
  - 将logger.log()的gateway_name参数改为使用logger.bind()方法
  - 正确绑定到loguru的extra上下文中（Issue #3715）
- 🔧 **示例应用优化**（提交bc499df8）：
  - demo_notebook配置更新：Python内核3.7.4->3.13.9
  - 清理单元格元数据，更新nbformat版本
- 📚 **文档完善**：
  - examples模块新增notebook_trading示例说明
  - 同步examples模块文档至2026-01-18
- 🔄 **上游同步**（提交c1bc4c3d）：
  - 合并upstream/master最新代码

### 2026-01-11
- 📈 **版本升级到4.3.0**：同步上游最新版本
- 📚 **文档资源完善**：
  - 新增 `STARTUP_GUIDE.md` 启动指南
  - 新增 `demo_app.py` 功能演示应用
  - 新增 `examples/candle_chart/simple_chart.py` 简化图表示例
  - 新增 `test_quick.py`、`test_basic.py`、`test_simple.py` 测试文件
- 🔧 **核心代码改进**（提交b08f9422, cb29c5cb, 5881a61b）：
  - 重构 `ts_slope` / `ts_rsquare` / `ts_resi` 算子函数
  - DataProxy的所有比较运算，直接返回pl.Int32（而不是Bool）
- 📊 **更新模块索引**：examples模块新增简化图表示例

### 2025-12-23
- 📈 **文档覆盖率100%**：所有7个模块CLAUDE.md文档完成
- 📊 更新时间戳至2025-12-23
- 🔄 同步最新代码库状态

### 2025-12-09 16:23:49
- 📝 添加VeighNa中文知识库完整文档（提交：e554ecf9）
- 📚 完善核心模块文档体系

### 2025-12-09 11:44:15
- ✨ 更新覆盖率至95%（61个文件，扫描58个）
- 📊 深入分析GUI系统（MainWindow和各种Monitor组件）
- 🔧 完善Chart组件文档（基于PyQtGraph的高性能图表）
- 📝 添加Examples模块文档（6个示例应用说明）
- 🚀 新增分布式部署和RPC服务说明
- 💡 补充Alpha 158因子集和模型实现细节

### 2025-12-09 11:33:34
- ✨ 创建VeighNa量化交易框架文档体系
- 📊 完成核心模块架构梳理（trader/alpha/event/chart/rpc）
- 🔧 整理AI量化研究功能（vnpy.alpha模块）
- 📝 建立模块间依赖关系图
- 🚀 提供快速启动指南和开发规范

---

*提示：点击上方模块名称或图表中的节点可快速跳转到对应模块的详细文档。*