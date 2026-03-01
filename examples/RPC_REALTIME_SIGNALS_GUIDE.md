# RPC实时信号生成系统 - 使用指南

## 功能概述

RPC实时信号生成脚本通过RPC连接到Windows QMT服务器，订阅实时行情数据，使用Alpha158因子和LightGBM模型生成实时交易信号。

### 主要功能

1. **RPC连接管理**
   - 自动连接到QMT RPC服务器
   - 支持自动重连机制
   - 订阅实时行情数据推送

2. **历史数据窗口管理**
   - 维护每只股票的历史数据窗口（默认60天）
   - 滚动更新数据，保持窗口大小固定
   - Tick数据自动聚合为K线数据

3. **Alpha158因子实时计算**
   - 基于vnpy.alpha模块的Alpha158因子集
   - 实时计算157个技术指标特征
   - 支持滚动计算，确保因子时效性

4. **LightGBM模型预测**
   - 加载预训练的LightGBM模型
   - 对每只股票进行实时预测
   - 输出5日预期收益率

5. **交易信号生成**
   - 根据预测收益率生成交易信号
   - 做多阈值：默认2%
   - 做空阈值：默认-2%
   - 持仓信号：介于阈值之间

6. **Rich终端UI实时显示**
   - 显示当前时间和系统状态
   - Top 10做多信号列表
   - Top 10做空信号列表
   - Top 20持仓股票列表
   - 实时更新显示

## 安装依赖

```bash
# 安装Rich库（用于终端UI）
pip install rich

# 其他依赖已在VeighNa环境中安装
```

## 配置说明

编辑脚本中的配置参数：

### RPC配置
```python
RPC_CONFIG = {
    "req_address": "tcp://192.168.2.168:2014",  # RPC请求地址
    "sub_address": "tcp://192.168.2.168:4102",  # RPC订阅地址
    "reconnect_interval": 5,                     # 重连间隔（秒）
}
```

### 模型配置
```python
MODEL_CONFIG = {
    "model_path": str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),
}
```

### 信号配置
```python
SIGNAL_CONFIG = {
    "long_threshold": 0.02,    # 做多阈值（2%）
    "short_threshold": -0.02,  # 做空阈值（-2%）
    "window_size": 60,         # 历史数据窗口（天数）
    "min_data_points": 30,     # 最小数据点数
}
```

### 股票池配置
```python
STOCK_POOL = [
    # 配置要监控的股票列表
    # 示例: ("000001", "SZSE"), ("600000", "SSE")
    # 为空时将从RPC获取合约列表
]
```

## 使用方法

### 1. 确保Windows QMT RPC服务器运行

在Windows机器上运行QMT RPC服务器：
```bash
python run_qmt_server.py
```

### 2. 启动实时信号系统

在macOS客户端上运行：
```bash
python examples/rpc_realtime_signals.py
```

### 3. 观察实时信号输出

系统将显示Rich终端UI，包括：
- 当前时间和系统状态
- Top 10做多信号
- Top 10做空信号
- 持仓股票列表

### 4. 退出系统

按 `Ctrl+C` 退出系统

## 测试验证

运行单元测试验证功能：
```bash
python test_rpc_realtime_signals.py
```

测试包括：
1. 模型加载测试
2. 数据窗口管理测试
3. Tick转K线测试
4. 信号生成接口测试
5. 统计功能测试

## 输出说明

### 信号类型
- **做多信号（1）**：预测收益率 > 2%
- **做空信号（-1）**：预测收益率 < -2%
- **持仓信号（0）**：-2% ≤ 预测收益率 ≤ 2%

### 信号数据结构
```python
{
    "vt_symbol": "000001.SZSE",      # 股票代码
    "prediction": 0.025,              # 预测收益率
    "signal": 1,                      # 信号类型
    "timestamp": datetime,            # 信号时间
}
```

### 统计信息
- **total_predictions**：总预测次数
- **long_signals**：做多信号次数
- **short_signals**：做空信号次数
- **hold_signals**：持仓信号次数

## 注意事项

1. **网络连接**：确保macOS客户端能访问Windows QMT服务器
2. **防火墙**：Windows防火墙需要开放2014和4102端口
3. **模型文件**：确保模型文件存在于指定路径
4. **数据延迟**：实时信号基于接收到的行情数据，可能有网络延迟
5. **计算资源**：Alpha158因子计算需要一定CPU资源

## 扩展开发

### 添加自定义因子
继承AlphaDataset类并添加自定义特征：
```python
class CustomAlpha(AlphaDataset):
    def __init__(self, df, ...):
        super().__init__(df, ...)
        self.add_feature("custom_factor", "close / ts_mean(close, 20)")
```

### 调整信号阈值
在配置中修改阈值：
```python
SIGNAL_CONFIG = {
    "long_threshold": 0.03,    # 调整为3%
    "short_threshold": -0.03,  # 调整为-3%
}
```

### 集成到交易策略
获取实时信号并执行交易：
```python
manager = RealtimeSignalManager(...)
# ... 连接并接收数据 ...

long_signals, short_signals = manager.get_top_signals(10)

for signal in long_signals:
    vt_symbol = signal["vt_symbol"]
    # 执行做多操作
    # ...
```

## 故障排查

### RPC连接失败
- 检查Windows服务器是否运行
- 检查网络连通性（ping命令）
- 检查防火墙设置
- 确认RPC地址配置正确

### 模型加载失败
- 确认模型文件存在
- 检查模型文件路径
- 验证模型文件格式

### 信号生成异常
- 确认历史数据窗口已满（60天）
- 检查Alpha158因子计算
- 验证模型输入特征数量（157个）

## 相关文件

- **主脚本**：`examples/rpc_realtime_signals.py`
- **测试脚本**：`test_rpc_realtime_signals.py`
- **模型文件**：`~/vnpy_lab/model/a_stock_lgb.txt`
- **RPC客户端**：`vnpy/rpc/client.py`
- **Alpha158类**：`vnpy/alpha/dataset/datasets/alpha_158.py`
- **LightGBM模型**：`vnpy/alpha/model/models/lgb_model.py`

## 更新日志

### 2026-03-01
- 创建RPC实时信号生成脚本
- 实现RPC连接管理
- 实现历史数据窗口管理
- 实现Alpha158因子实时计算
- 实现LightGBM模型预测
- 实现交易信号生成
- 实现Rich终端UI显示
- 创建单元测试脚本
