# Alpha158因子集与RPC实时信号生成 - 实现计划

## 项目概述

为VeighNa量化交易框架添加两个增强功能：
1. **Alpha158因子集特征工程**：使用微软Qlib的158个经典因子进行模型训练
2. **RPC实时信号生成**：结合RPC-QMT连接实现实时交易信号生成

## 背景信息

### 当前环境
- **项目路径**：/Users/berton/Github/vnpy
- **Conda环境**：Quant-3.11 (Python 3.11)
- **MySQL数据库**：localhost:3306，包含5,906,017条QMT历史数据
- **RPC服务器**：Windows QMT服务器 (192.168.2.168:2014/4102)

### 已有资源
- **Alpha158因子集**：vnpy/alpha/dataset/datasets/alpha_158.py（已实现）
- **RPC客户端**：vnpy/rpc/client.py（已可用）
- **训练脚本示例**：train_qmt_real_data.py（使用简单特征）

### 技术栈
- **数据处理**：polars, numpy
- **机器学习**：lightgbm
- **RPC通信**：ZeroMQ (vnpy.rpc)
- **数据库**：PyMySQL

---

## 任务列表

### 任务 1：创建Alpha158特征工程脚本

**描述**：创建一个训练脚本，使用Alpha158因子集从QMT历史数据计算158个技术因子，并训练LightGBM模型。

**要求**：
- 使用vnpy.alpha.dataset.datasets.Alpha158类
- 从MySQL数据库加载QMT历史数据（db_bar_data表）
- 支持自定义日期范围和股票列表
- 计算157个Alpha158因子（排除vwap）
- 使用5日远期收益率作为标签
- 训练LightGBM模型
- 保存模型和特征重要性报告
- 输出：训练好的模型 + 特征重要性图表

**上下文**：
- Alpha158类在vnpy/alpha/dataset/datasets/alpha_158.py
- 需要将MySQL数据转换为AlphaDataset格式
- 参考脚本：train_qmt_real_data.py（已实现简单版本）

**验收标准**：
- 脚本可运行且无错误
- 成功从MySQL加载至少50只股票的数据
- 计算157个Alpha158因子
- 模型训练完成（验证集Loss < 0.01）
- 生成特征重要性图表
- 保存模型到文件

---

### 任务 2：创建RPC实时信号生成脚本

**描述**：创建一个实时信号生成脚本，通过RPC连接Windows QMT服务器，获取实时行情并使用训练好的模型生成交易信号。

**要求**：
- 连接RPC服务器（tcp://192.168.2.168:2014, tcp://192.168.2.168:4102）
- 订阅实时行情（tick数据）
- 使用Alpha158因子集计算实时特征
- 使用训练好的模型进行预测
- 根据预测收益率生成交易信号：
  - 预测 > 阈值 → 做多信号
  - 预测 < -阈值 → 做空信号
  - 否则 → 持仓/观望
- 实时显示信号列表
- 支持自定义信号阈值
- 输出：实时信号监控界面

**上下文**：
- RPC客户端使用vnpy.rpc.RpcClient
- QMT RPC服务器已在Windows运行
- Alpha158因子计算需要历史数据窗口（至少20日）
- 模型文件路径：~/vnpy_lab/model/a_stock_lgb.txt

**验收标准**：
- 成功连接RPC服务器
- 实时接收行情数据
- 实时计算Alpha158因子
- 生成交易信号并显示
- 支持信号阈值调整
- 显示Top做多/做空股票列表

---

## 实施顺序

1. **任务 1**：Alpha158特征工程脚本（离线训练）
2. **任务 2**：RPC实时信号生成脚本（在线推理）

---

## 注意事项

### 依赖关系
- 任务2依赖任务1的模型输出
- 两个任务共享相同的Alpha158因子定义

### 代码风格
- 遵循PEP 8编码规范
- 使用类型注解(Type Hints)
- 添加中文注释和文档字符串
- 错误处理要完善

### 测试要求
- 每个脚本都要进行实际测试
- 验证与MySQL数据库的连接
- 验证RPC连接和实时数据接收

---

## 输出位置

- **任务1脚本**：examples/train_alpha158_model.py
- **任务2脚本**：examples/rpc_realtime_signals.py
- **模型文件**：~/vnpy_lab/model/alpha158_lgb.txt
- **特征重要性图表**：~/vnpy_lab/feature_importance.png
