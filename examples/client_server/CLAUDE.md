[根目录](../../CLAUDE.md) > **examples** > [client_server](.)

# Client_Server - 分布式部署示例

> 更新时间：2026-02-25
> 版本：1.0

## 模块概述

Client_Server 目录提供了 VeighNa 框架的分布式部署示例，展示如何将交易系统和界面分离部署，基于 RPC 服务实现分布式通信。支持 GUI 和终端两种运行模式。

## 核心架构

### 分布式架构

```
┌──────────────────────────────────────────────────────────────┐
│                    分布式部署架构                              │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   [Mac/Linux 客户端]                  [Windows 服务端]         │
│   ┌─────────────────────┐            ┌─────────────────────┐   │
│   │ RPC Client          │            │ RPC Server          │   │
│   │ - GUI 界面          │  <--RPC-->  │ - QMT Gateway        │   │
│   │ - 策略执行          │   ZeroMQ   │ - 交易执行          │   │
│   │ - 数据分析          │            │ - 行情接收          │   │
│   └─────────────────────┘            └─────────────────────┘   │
│                                                                │
│   支持多客户端同时连接同一交易实例                              │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

## 文件说明

### 服务端文件

**`run_qmt_server.py`** - Windows QMT RPC 服务端

- **运行环境**：Windows + QMT + VeighNa
- **功能**：启动 RPC 服务，连接 QMT 接口，处理交易请求
- **监听地址**：
  - 请求端口：`0.0.0.0:2014`
  - 订阅端口：`0.0.0.0:4102`

**启动方式**：
```bash
# Windows 命令行
cd G:\Berton\VNPY\examples\client_server
python run_qmt_server.py
```

### 客户端文件

**`run_qmt_client.py`** - Mac/Linux RPC 客户端

- **运行环境**：Mac/Linux + VeighNa
- **功能**：通过 RPC 连接到 Windows 服务端，显示 GUI 界面
- **集成模块**：7 个 A 股增强模块（策略、分析、规则、数据、回测、资金、机器学习）

**启动方式**：
```bash
# Mac/Linux 终端
cd /Users/berton/Github/vnpy/examples/client_server
python run_qmt_client.py
```

### 配置文件

**`data_config.yaml.example`** - 配置文件示例

包含所有可配置项：
- Tushare 配置
- QMT RPC 配置
- 缓存配置
- 增量更新配置

## RPC 配置指南

### 配置方式

#### 方式1：配置文件（推荐）

在项目根目录创建配置文件 `.vntrader_china/config/data_development.yaml`：

```yaml
# QMT RPC配置
qmt_use_rpc: true
qmt_rpc_req_address: "tcp://192.168.2.168:2014"
qmt_rpc_sub_address: "tcp://192.168.2.168:4102"
```

#### 方式2：环境变量

```bash
# 设置环境变量覆盖配置
export QMT_RPC_REQ_ADDRESS="tcp://192.168.2.168:2014"
export QMT_RPC_SUB_ADDRESS="tcp://192.168.2.168:4102"
```

详细配置说明请参考：[README_RPC_CONFIG.md](./README_RPC_CONFIG.md)

### 网络配置场景

#### 局域网环境

```
Mac 客户端 (192.168.2.50)  <--->  Windows 服务端 (192.168.2.168)
```

配置：
```yaml
qmt_rpc_req_address: "tcp://192.168.2.168:2014"
qmt_rpc_sub_address: "tcp://192.168.2.168:4102"
```

#### Parallels 虚拟机

```
Mac 主机  <--端口转发-->  Parallels Windows 虚拟机
```

配置：
```yaml
qmt_rpc_req_address: "tcp://127.0.0.1:2014"
qmt_rpc_sub_address: "tcp://127.0.0.1:4102"
```

#### 云服务器

```
Mac 客户端  <--互联网(VPN)-->  云 Windows 服务器
```

配置：
```yaml
qmt_rpc_req_address: "tcp://YOUR_SERVER_IP:2014"
qmt_rpc_sub_address: "tcp://YOUR_SERVER_IP:4102"
```

## 使用流程

### 1. Windows 服务端启动

```bash
# 1. 确保 QMT 已安装并登录
# 2. 启动 RPC 服务端
python run_qmt_server.py

# 输出示例
==============================================================
VeighNa RPC服务端 - QMT版本
==============================================================
RPC服务已启动：
  请求地址: tcp://0.0.0.0:2014
  订阅地址: tcp://0.0.0.0:4102
==============================================================
```

### 2. Mac/Linux 客户端连接

```bash
# 1. 配置 RPC 地址（配置文件或环境变量）
# 2. 启动客户端
python run_qmt_client.py

# 输出示例
==============================================================
VeighNa Trader - RPC连接模式
==============================================================
  请求地址: tcp://192.168.2.168:2014
  订阅地址: tcp://192.168.2.168:4102
  显示精度: 2位小数
  功能模块: A股策略、分析、规则、数据、回测、资金、机器学习
==============================================================
正在连接RPC...
✓ 已连接到Windows QMT服务端

正在加载A股增强模块...
  ✓ A股策略模块
  ✓ A股分析模块
  ✓ A股规则模块
  ✓ A股数据模块
  ✓ A股回测模块
  ✓ A股资金模块
  ✓ A股机器学习模块
✓ A股增强模块加载完成
```

## 集成模块

客户端集成了 7 个 A 股增强模块：

| 模块 | 文件 | 功能描述 |
|------|------|----------|
| **策略模块** | `vnpy_china_strategy` | A股策略模板、信号生成 |
| **分析模块** | `vnpy_china_analysis` | Level-2、资金流向、技术指标 |
| **规则模块** | `vnpy_china_rules` | T+1、涨跌停、交易时间检查 |
| **数据模块** | `vnpy_china_data` | Tushare 数据、龙虎榜、北向资金 |
| **回测模块** | `vnpy_china_backtest` | A股回测引擎、滑点模型 |
| **资金模块** | `vnpy_china_capital` | 资金流水、持仓分析、风险监控 |
| **机器学习模块** | `vnpy_china_ml` | ML 策略、特征工程、模型训练 |

## 测试文件

- **`test_rpc_connect.py`** - RPC 连接测试
- **`test_rpc_full.py`** - 完整 RPC 功能测试
- **`test_qt_window.py`** - Qt 窗口测试

## 常见问题

### Q1: RPC 连接超时

**检查步骤**：
1. Windows 服务端是否运行 `run_qmt_server.py`
2. Windows 防火墙是否开放 2014、4102 端口
3. 网络连通性：`ping 192.168.2.168`
4. 配置文件 IP 地址是否正确

**解决方案**：
```powershell
# Windows 防火墙 - 添加入站规则
netsh advfirewall firewall add rule `
    name="VeighNa RPC" `
    dir=in action=allow protocol=TCP localport=2014,4102
```

### Q2: 配置文件不生效

**检查步骤**：
1. 配置文件路径：`.vntrader_china/config/data_development.yaml`
2. 环境变量优先级高于配置文件
3. 重启客户端加载新配置

### Q3: 虚拟机网络不通

**Parallels 配置**：
1. 虚拟机 → 配置 → 硬件 → 网络
2. 选择"桥接网络"模式
3. 查看 Windows IP：`ipconfig`
4. 测试连通性：`ping <Windows_IP>`

## 安全建议

1. **使用局域网**：避免将 RPC 服务暴露到公网
2. **配置防火墙**：只允许特定 IP 访问
3. **使用 VPN**：如需公网访问，建立加密通道
4. **定期更换端口**：不使用默认端口号

## 相关文档

- [Mac连接QMT解决方案指南](../../docs/Mac连接QMT解决方案指南.md)
- [VMware Fusion QMT方案指南](../../docs/VMware_Fusion_QMT方案指南.md)
- [README_RPC_CONFIG.md](./README_RPC_CONFIG.md)

## 变更记录

### 2026-02-25
- ✨ **RPC 配置文件化**：移除硬编码配置，支持配置文件和环境变量
- 📝 **添加配置示例**：`data_config.yaml.example`
- 📚 **添加配置文档**：`README_RPC_CONFIG.md`
- 🔧 **更新客户端代码**：使用 `ConfigManager` 加载配置

### 2026-02-24
- ✨ **集成 7 个 A股增强模块**
- 🔧 **自定义显示精度**：保留 2 位小数
- 📝 **添加模块说明文档**

---

*提示：首次使用请先阅读 [README_RPC_CONFIG.md](./README_RPC_CONFIG.md) 了解详细的配置方法。*
