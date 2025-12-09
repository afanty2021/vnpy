[根目录](../../CLAUDE.md) > **examples**

# Examples - 示例应用集合

> 更新时间：2025-12-09 11:44:15

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

### 6. data_recorder - 数据记录示例
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
- `simple_rpc/test_server.py` - RPC测试服务端
- `simple_rpc/test_client.py` - RPC测试客户端
- `data_recorder/data_recorder.py` - 数据记录程序

## 变更记录 (Changelog)

### 2025-12-09 11:44:15
- ✨ 创建examples模块文档
- 📊 整理所有示例应用的说明
- 🔧 添加使用指南和最佳实践
- 📝 提供常见问题解答

---

*提示：建议按照文档顺序学习示例，从简单的GUI应用到复杂的多进程架构。*