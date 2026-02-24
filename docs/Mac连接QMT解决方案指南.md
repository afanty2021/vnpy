# Mac + VeighNa + QMT 完整解决方案

> 更新时间：2026-02-24
> 适用场景：Mac用户需要使用QMT进行A股量化交易

---

## 🎯 方案概述

### 核心思路

**分布式架构**：利用VeighNa原生支持的RPC服务，实现Mac和Windows的分离部署

```
Mac (开发/策略)  <--RPC-->  Windows (执行/QMT)
```

### 优势分析

| 方面 | 优势 |
|------|------|
| ✅ **开发体验** | Mac本地进行策略开发、回测、调试 |
| ✅ **系统稳定** | Mac享受Unix系统稳定性，Windows专注交易 |
| ✅ **资源隔离** | 交易服务独立运行，不影响日常开发 |
| ✅ **远程访问** | 可随时随地在Mac上管理交易 |
| ✅ **原生支持** | VeighNa内置RPC功能，无需第三方工具 |
| ✅ **成本可控** | 可使用已有Windows机器或低成本云主机 |

---

## 📐 架构设计

### 网络拓扑图

```
┌─────────────────────────────────────────────────────────────┐
│                      场景1：局域网部署（推荐）                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [MacBook Pro]                        [Windows PC]          │
│   ┌─────────────────┐               ┌─────────────────┐     │
│   │ VeighNa GUI     │               │ QMT + RPC Server│     │
│   │ 策略开发         │  <--局域网-->  │ 交易执行         │     │
│   │ 回测分析         │   ZeroMQ      │ 行情接收         │     │
│   └─────────────────┘               └─────────────────┘     │
│   IP: 192.168.1.50                   IP: 192.168.1.100       │
│   Port: 动态                         Port: 2014/4102        │
│                                                              │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                      场景2：互联网部署                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [MacBook Pro - 任意位置]                                   │
│   ┌─────────────────┐                                       │
│   │ VeighNa GUI     │                                       │
│   │ 策略开发         │  <--互联网-->                         │
│   │ 远程监控         │   VPN/SSH     ┌─────────────────┐   │
│   └─────────────────┘               │ [云Windows]     │   │
│   位置: 家/办公室/外出               │ QMT + RPC Server│   │
│                                      │ 24/7运行        │   │
│                                      └─────────────────┘   │
│                                      IP: 云服务器公网IP      │
│                                                              │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                    场景3：Parallels虚拟机                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [MacBook Pro - 本地]                                       │
│   ┌────────────────────────────────────────────────────┐    │
│   │  macOS                                              │    │
│   │  ┌──────────────────────────────────────────────┐  │    │
│   │  │ VeighNa GUI (策略开发)                        │  │    │
│   │  └──────────────────────────────────────────────┘  │    │
│   │           │ 本地RPC                               │    │
│   │           └──────────────────┐                    │    │
│   │                              ↓                    │    │
│   │  ┌──────────────────────────────────────────────┐  │    │
│   │  │  Parallels/VMWare Windows虚拟机               │  │    │
│   │  │  ┌────────────────────────────────────────┐  │  │    │
│   │  │  │ QMT + RPC Server                      │  │  │    │
│   │  │  └────────────────────────────────────────┘  │  │    │
│   │  └──────────────────────────────────────────────┘  │    │
│   └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 方案一：RPC分布式（最推荐）

### 1.1 Windows端配置

#### 硬件要求

| 配置 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 双核2.0GHz | 四核3.0GHz+ |
| 内存 | 4GB | 8GB+ |
| 硬盘 | 50GB | 100GB+ SSD |
| 网络 | 有线网络 | 有线网络（稳定） |

#### 软件安装

```powershell
# 1. 安装Python 3.11
# 下载：https://www.python.org/downloads/

# 2. 创建VeighNa环境
python -m venv vnpy_rpc
vnpy_rpc\Scripts\activate

# 3. 安装依赖
pip install vnpy
pip install vnpy_qmt
pip install vnpy_rpcservice
pip install vnpy_ctastrategy

# 4. 配置QMT
# - 确保MiniQMT已安装
# - 路径：D:/国金证券QMT交易端/userdata_mini/
# - 账号已登录
```

#### 启动RPC服务

```bash
# Windows命令行
cd G:\Berton\VNPY\examples\client_server
python run_qmt_server.py
```

#### 网络配置

```python
# 本地测试（Mac和Windows在同一台机器的虚拟机）
RPC_SETTING = {
    "req_address": "tcp://127.0.0.1:2014",
    "sub_address": "tcp://127.0.0.1:4102",
}

# 局域网访问（Mac和Windows在同一局域网）
RPC_SETTING = {
    "req_address": "tcp://0.0.0.0:2014",  # 0.0.0.0允许外网访问
    "sub_address": "tcp://0.0.0.0:4102",
}
# Mac端配置Windows的实际IP，如 192.168.1.100

# 互联网访问（需要配置端口映射）
# 1. 路由器端口映射：2014、4102
# 2. 使用动态DNS（如花生壳）
# 3. 配置防火墙规则
RPC_SETTING = {
    "req_address": "tcp://0.0.0.0:2014",
    "sub_address": "tcp://0.0.0.0:4102",
}
# Mac端配置公网IP或域名
```

#### 防火墙配置

```powershell
# Windows防火墙 - 添加入站规则
netsh advfirewall firewall add rule `
    name="VeighNa RPC Request" `
    dir=in action=allow protocol=TCP localport=2014

netsh advfirewall firewall add rule `
    name="VeighNa RPC Subscribe" `
    dir=in action=allow protocol=TCP localport=4102

# 或通过图形界面：
# 控制面板 -> Windows Defender 防火墙 -> 高级设置
# 入站规则 -> 新建规则 -> 端口 -> TCP特定本地端口 -> 2014,4102
```

### 1.2 Mac端配置

#### 安装VeighNa

```bash
# 1. 安装Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Python 3.11
brew install python@3.11

# 3. 克隆VeighNa项目
git clone https://github.com/vnpy/vnpy.git
cd vnpy

# 4. 创建虚拟环境
python3.11 -m venv vnpy_mac
source vnpy_mac/bin/activate

# 5. 安装VeighNa
pip install -e .

# 6. 安装依赖
pip install vnpy_ctastrategy
pip install vnpy_ctabacktester
pip install vnpy_datamanager
# 注意：Mac上不需要安装vnpy_qmt
```

#### 测试RPC连接

```bash
# 方式1：命令行测试
cd examples/client_server
python run_qmt_client.py --mode test

# 方式2：启动GUI
python run_qmt_client.py --mode gui
```

#### 配置文件

```python
# config/rpc_config.py
"""Mac端RPC配置"""

# Windows服务器配置
RPC_SERVER = {
    "name": "windows_qmt_server",
    "host": "192.168.1.100",  # Windows机器IP
    "req_port": 2014,
    "sub_port": 4102,

    # 或使用公网IP/域名
    # "host": "your-server.ddns.net",
}

# 本地策略配置
STRATEGY = {
    "template_path": "./strategies",
    "data_path": "./data",
    "log_path": "./logs",
}
```

### 1.3 安全配置

#### SSL/TLS加密（推荐生产环境）

```python
# 使用TLS加密RPC通信
import ssl

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.load_verify_locations("server.crt")  # 服务器证书

# 客户端连接时使用TLS
rpc_client.connect(
    req_address="tls://192.168.1.100:2014",
    sub_address="tls://192.168.1.100:4102",
    ssl=context
)
```

#### 访问控制

```python
# Windows服务端 - IP白名单
ALLOWED_IPS = [
    "192.168.1.50",   # Mac的IP
    "192.168.1.0/24",  # 整个局域网（可选）
]

# 或使用VPN（推荐）
# Mac通过VPN连接到Windows网络
```

---

## 🌐 方案二：云Windows服务器

### 2.1 云服务选择

| 提供商 | 配置 | 价格（月） | 优势 |
|--------|------|-----------|------|
| **阿里云** | 2核4GB | ¥100-200 | 国内速度快 |
| **腾讯云** | 2核4GB | ¥100-200 | 稳定性好 |
| **华为云** | 2核4GB | ¥100-200 | 企业级 |
| **AWS** | t3.medium | $30-50 | 全球覆盖 |
| **Azure** | B2s | $30-50 | 企业级 |

### 2.2 部署步骤

```bash
# 1. 购买云服务器
# - 系统：Windows Server 2019/2022
# - 带宽：按量付费或固定带宽
# - 安全组：开放2014、4102端口

# 2. 远程连接（Windows远程桌面）
# Mac：使用Microsoft Remote Desktop
# 下载：https://apps.apple.com/cn/app/microsoft-remote-desktop/

# 3. 在云服务器上安装QMT和VeighNa
# （参照方案一的Windows端配置）

# 4. 配置安全组规则
# 入站规则：
# - TCP 2014 (RPC请求)
# - TCP 4102 (RPC订阅)
# - TCP 3389 (远程桌面，可选)

# 5. Mac连接测试
python run_qmt_client.py --mode test
```

### 2.3 成本优化

```python
# 成本优化建议

# 1. 使用按量付费
# 交易时间（9:30-15:00）自动开机
# 非交易时间自动关机

# 2. 使用抢占式实例
# 成本降低50-80%
# 注意：可能被自动回收

# 3. 选择合适的配置
# - 开发/测试：1核2GB即可
# - 实盘交易：2核4GB推荐
# - 多策略运行：4核8GB

# 4. 带宽优化
# - 使用流量计费
# - RPC数据量很小（<1MB/分钟）
```

---

## 💻 方案三：Parallels虚拟机

### 3.1 安装Parallels Desktop

```bash
# 1. 购买Parallels Desktop
# 价格：¥500-800/年
# 下载：https://www.parallelsglobal.com/

# 2. 安装Windows虚拟机
# - Windows 10/11 均可
# - 分配内存：4GB+
# - 磁盘：60GB+

# 3. 安装QMT和VeighNa
# （在虚拟机中安装，参照方案一）

# 4. 网络配置
# Parallels默认使用桥接网络
# 虚拟机和Mac在同一网段，可直接通信
```

### 3.2 优势与局限

| 优势 | 局限 |
|------|------|
| ✅ 本地运行，延迟最低 | ❌ Mac负担重 |
| ✅ 无需网络配置 | ❌ 需要购买软件 |
| ✅ 数据安全可控 | ❌ 虚拟机性能损耗 |
| ✅ 方便调试 | ❌ 占用Mac资源 |

---

## 🔄 方案四：远程桌面

### 4.1 方案对比

| 方案 | 成本 | 延迟 | 体验 |
|------|------|------|------|
| Windows远程桌面 | 低 | 中 | 好 |
| TeamViewer | 中 | 中 | 好 |
| 向日葵 | 低 | 中 | 好 |
| ToDesk | 低 | 中 | 好 |
| VNC | 低 | 高 | 一般 |

### 4.2 使用场景

```python
# 适用场景：
# 1. 策略调试：需要频繁查看Windows端状态
# 2. QMT配置：需要在Windows上操作QMT界面
# 3. 故障排查：需要直接访问Windows系统

# 使用方式：
# 1. Mac安装远程桌面客户端
# 2. 连接到Windows机器
# 3. 在Windows上操作VeighNa和QMT
# 4. 适合临时使用，不适合日常开发
```

---

## 📊 方案对比总结

### 综合评分

```
┌───────────────────────────────────────────────────────────────┐
│                    方案综合对比表                              │
├──────────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┤
│ 方案         │ 成本 │ 延迟 │ 稳定 │ 便携 │ 安全 │ 维护 │ 推荐 │
├──────────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ RPC局域网    │ ⭐   │ ⭐⭐ │ ⭐⭐⭐│ ⭐   │ ⭐⭐⭐│ ⭐⭐ │⭐⭐⭐⭐│
│ RPC云服务器  │ ⭐⭐ │ ⭐⭐ │ ⭐⭐⭐⭐⭐│ ⭐⭐⭐⭐⭐│ ⭐⭐ │ ⭐⭐⭐│⭐⭐⭐⭐│
│ Parallels    │ ⭐   │ ⭐⭐⭐⭐⭐│ ⭐⭐⭐│ ⭐⭐⭐│ ⭐⭐⭐⭐│ ⭐⭐ │⭐⭐⭐│
│ 远程桌面     │ ⭐⭐ │ ⭐⭐ │ ⭐⭐ │ ⭐⭐⭐⭐│ ⭐⭐ │ ⭐  │⭐⭐│
└──────────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

### 推荐选择

```
┌─────────────────────────────────────────────────────────────┐
│  首选：RPC局域网方案                                         │
│  - 适用：有Windows电脑                                       │
│  - 成本：最低（0额外成本）                                   │
│  - 性能：最佳                                               │
│  - 操作：配置简单                                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  次选：RPC云服务器方案                                       │
│  - 适用：无Windows电脑或需要24/7运行                         │
│  - 成本：中等（¥100-200/月）                                │
│  - 性能：良好                                               │
│  - 操作：配置稍复杂                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  备选：Parallels虚拟机方案                                   │
│  - 适用：预算充足、追求极致体验                              │
│  - 成本：高（软件费用）                                     │
│  - 性能：优秀                                               │
│  - 操作：简单                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 实施检查清单

### RPC局域网方案

- [ ] Windows机器准备
- [ ] QMT安装并登录
- [ ] VeighNa环境配置
- [ ] RPC服务端启动
- [ ] 防火墙配置
- [ ] Mac端VeighNa安装
- [ ] RPC连接测试
- [ ] 策略开发测试
- [ ] 模拟盘验证
- [ ] 实盘运行

### RPC云服务器方案

- [ ] 云服务器购买
- [ ] Windows系统配置
- [ ] QMT安装（可能需要券商支持）
- [ ] 安全组规则配置
- [ ] VPN配置（推荐）
- [ ] SSL证书配置（推荐）
- [ ] 自动启动配置
- [ ] 监控告警配置
- [ ] 备份策略配置

---

## 🔧 常见问题

### Q1: RPC连接超时

```
问题：Mac无法连接到Windows RPC服务

排查步骤：
1. 检查Windows防火墙（端口2014、4102）
2. 检查网络连通性：ping 192.168.1.100
3. 检查RPC服务是否启动
4. 检查IP地址是否正确
5. 检查Mac和Windows是否在同一网络

解决方案：
# 临时关闭防火墙测试
# Windows PowerShell
netsh advfirewall set allprofiles state off

# 确认后重新开启并添加规则
netsh advfirewall set allprofiles state on
```

### Q2: 数据同步延迟

```
问题：Mac端数据更新慢

原因：网络延迟、数据量大

解决方案：
1. 使用有线网络
2. 减少订阅品种
3. 降低数据推送频率
4. 使用更快的网络（千兆）
```

### Q3: Windows机器休眠

```
问题：Windows休眠后RPC断开

解决方案：
# Windows设置
1. 电源选项 -> 从不休眠
2. 关闭硬盘：从不
3. 关机设置 -> 关闭"启用快速启动"

# 或使用服务器版本Windows Server
```

### Q4: QMT登录过期

```
问题：QMT自动退出或登录过期

解决方案：
1. 启用QMT自动登录
2. 配置心跳检测
3. 异常自动重连
4. 使用服务器版Windows（更稳定）
```

---

## 📞 技术支持

### 参考资源

| 资源 | 链接 |
|------|------|
| VeighNa官方文档 | https://www.vnpy.com/docs |
| vnpy_rpcservice | https://github.com/vnpy/vnpy_rpcservice |
| QMT接口文档 | https://zhuanlan.zhihu.com/p/595358960 |
| Parallels Desktop | https://www.parallels.com/ |

### 社区支持

- VeighNa官方QQ群：262656087
- VeighNa官方论坛：https://www.vnpy.com/forum

---

**文档版本**：v1.0
**最后更新**：2026-02-24
**维护者**：AI Assistant
