# VMware Fusion + VeighNa + QMT 完整方案

> 更新时间：2026-02-24
> 适用场景：Mac用户通过VMware Fusion虚拟机运行QMT
> 方案类型：本地RPC通信

---

## 🎯 方案概述

### 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MacBook Pro (物理机)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  macOS (主机)                                         │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ VeighNa GUI (策略开发)                         │  │   │
│  │  │ • 策略编写                                      │  │   │
│  │  │ • 回测分析                                      │  │   │
│  │  │ • 监控界面                                      │  │   │
│  │  │ • RPC Client                                   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                        │                             │   │
│  │                        │ 虚拟网络                    │   │
│  │                        ↓                             │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  VMware Fusion 虚拟机                           │  │   │
│  │  │  ┌──────────────────────────────────────────┐  │  │   │
│  │  │  │  Windows 11 (虚拟机)                      │  │  │   │
│  │  │  │  ┌────────────────────────────────────┐   │  │  │   │
│  │  │  │  │ QMT + MiniQMT                      │   │  │  │   │
│  │  │  │  │ • 交易接口                          │   │  │  │   │
│  │  │  │  │ • 行情接收                          │   │  │  │   │
│  │  │  │  │ • 交易执行                          │   │  │  │   │
│  │  │  │  └────────────────────────────────────┘   │  │  │   │
│  │  │  │  ┌────────────────────────────────────┐   │  │  │   │
│  │  │  │  │ RPC Server                         │   │  │  │   │
│  │  │  │  │ • 接收Mac端请求                     │   │  │  │   │
│  │  │  │  │ • 执行QMT操作                       │   │  │  │   │
│  │  │  │  │ • 返回结果                          │   │  │  │   │
│  │  │  │  └────────────────────────────────────┘   │  │  │   │
│  │  │  └──────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  硬件资源分配：                                                │
│  • CPU: 4核 (虚拟机)                                          │
│  • 内存: 8GB (虚拟机)                                         │
│  • 磁盘: 100GB SSD                                           │
└─────────────────────────────────────────────────────────────┘
```

### 方案优势

| 优势 | 说明 |
|------|------|
| ✅ **零网络延迟** | 虚拟网络通信，延迟<1ms |
| ✅ **数据安全** | 所有数据在本地，不上传 |
| ✅ **方便调试** | 可同时查看Mac和Windows界面 |
| ✅ **成本可控** | VMware Fusion有免费版 |
| ✅ **资源隔离** | Windows崩溃不影响Mac日常使用 |
| ✅ **可移植性** | 虚拟机可备份、迁移 |
| ✅ **灵活性高** | 可暂停、恢复、快照 |

---

## 📦 第一步：安装VMware Fusion

### 1.1 下载VMware Fusion

```bash
# VMware Fusion有两个版本：
# 1. Fusion Pro (付费，功能完整)
# 2. Fusion Player (免费，个人使用足够)

# 下载地址：
# https://www.vmware.com/go/getfusionplayer
# 或
# https://customerconnect.vmware.com/en/downloads/info/slug/desktop_end_user_computing/vmware_fusion/13_0

# 注册免费账号即可下载Fusion Player
```

### 1.2 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| Mac型号 | 2011年及以后 | 2015年及以后 |
| 处理器 | Intel Core 2 Duo | Intel i5/i7/i9 或 Apple Silicon |
| 内存 | 8GB | 16GB+ |
| 硬盘 | 80GB可用空间 | 200GB+ SSD |
| 系统 | macOS 10.15+ | macOS 12+ |

### 1.3 安装步骤

```
1. 下载VMware Fusion.dmg
2. 双击安装包，拖动到应用程序文件夹
3. 首次启动需要注册（免费版需要VM账号）
4. 完成安装
```

---

## 🪟 第二步：创建Windows虚拟机

### 2.1 准备Windows镜像

```bash
# Windows 11 官方镜像下载
# 方法1：Microsoft官网（推荐）
https://www.microsoft.com/zh-cn/software-download/windows11

# 方法2：使用Media Creation Tool
# 下载后选择"创建Windows 11安装媒体"

# 方法3：开发人员虚拟机（已激活）
https://developer.microsoft.com/zh-cn/windows/downloads/virtual-machines/
# 选择"HyperV"版本，VMware也支持

# 推荐配置：
# - Windows 11 专业版
# - 64位
```

### 2.2 创建虚拟机

```
1. 启动VMware Fusion
2. 文件 -> 新建
3. 拖拽Windows ISO文件到窗口
4. 选择"Windows 11或更高版本"
5. 配置虚拟机设置：

   【基本设置】
   - 虚拟机名称：Windows-QMT
   - 位置：~/Documents/Virtual Machines/Windows-QMT

   【处理器和内存】
   - 处理器：4个核心（或更多）
   - 内存：8GB（或更多，建议占Mac内存的50%以内）

   【磁盘】
   - 磁盘大小：100GB
   - 单个文件或拆分均可

   【网络适配器】
   - 重要！选择"网络适配器：NAT"
   - 或选择"自定义：仅主机模式"
```

### 2.3 网络模式选择（关键！）

```
VMware Fusion提供三种网络模式：

┌─────────────────────────────────────────────────────────────┐
│  1. NAT模式（推荐用于RPC）                                    │
│  ├─ 优点：                                                   │
│  │  • 虚拟机可访问外网（更新、下载）                          │
│  │  • Mac和虚拟机隔离，安全性高                              │
│  │  • 虚拟机IP自动分配（DHCP）                              │
│  │  • 支持端口转发                                           │
│  └─ 配置：                                                   │
│    - 虚拟机IP: 192.168.xxx.xxx                               │
│    - Mac访问虚拟机: 通过端口转发                             │
│    - IP地址固定: 需配置                                       │
├─────────────────────────────────────────────────────────────┤
│  2. 仅主机模式（推荐用于RPC）                                  │
│  ├─ 优点：                                                   │
│  │  • Mac和虚拟机私有网络通信                                │
│  │  • 完全隔离，安全性最高                                   │
│  │  • IP地址固定                                             │
│  │  • 延迟最低                                               │
│  └─ 配置：                                                   │
│    - 虚拟机IP: 192.168.xxx.xxx                               │
│    - Mac直接访问虚拟机IP                                     │
│    - 最适合RPC通信                                           │
├─────────────────────────────────────────────────────────────┤
│  3. 桥接模式                                                  │
│  ├─ 优点：                                                   │
│  │  • 虚拟机和Mac在同一局域网                                │
│  │  • 其他设备可访问虚拟机                                   │
│  └─ 缺点：                                                   │
│    • 安全性较低（暴露在局域网）                              │
│    • IP可能变化（DHCP）                                      │
│    • 一般不需要使用此模式                                    │
└─────────────────────────────────────────────────────────────┘

推荐使用：NAT模式 或 仅主机模式
```

### 2.4 完成Windows安装

```
1. 启动虚拟机
2. 按Windows安装向导完成安装
3. 安装VMware Tools（重要！提升性能）
   - 虚拟机菜单 -> 虚拟机 -> 安装VMware Tools
   - 自动安装，完成后重启

4. Windows系统优化：
   - 关闭Windows自动更新（或设置为手动）
   - 关闭休眠：powercfg -h off
   - 关闭屏幕保护
   - 设置电源计划：从不休眠
```

---

## 🔧 第三步：配置网络连接

### 3.1 查看虚拟机IP地址

```powershell
# 在Windows虚拟机中打开PowerShell

# 查看IP配置
ipconfig

# 输出示例（NAT模式）：
# Windows IP 配置
#
# 以太网适配器 VMware Network Adapter VMnet8:
#
#    连接特定的 DNS 后缀 . . . . . . . :
#    本地链接 IPv6 地址. . . . . . . . : fe80::xxx
#    IPv4 地址 . . . . . . . . . . . . : 192.168.223.128  ← 记录这个IP
#    子网掩码  . . . . . . . . . . . . : 255.255.255.0
#    默认网关. . . . . . . . . . . . . : 192.168.223.2

# 或（仅主机模式）：
# 以太网适配器 VMware Network Adapter VMnet1:
#
#    IPv4 地址 . . . . . . . . . . . . : 192.168.44.128  ← 记录这个IP
#    子网掩码  . . . . . . . . . . . . : 255.255.255.0
```

### 3.2 设置固定IP（推荐）

```powershell
# 方法1：通过Windows设置
# 1. 设置 -> 网络和Internet -> 以太网
# 2. 编辑 -> 手动分配IP
# 3. 设置：
#    - IP地址：192.168.223.128（或你想要的IP）
#    - 子网掩码：255.255.255.0
#    - 默认网关：192.168.223.2
#    - DNS：自动或使用8.8.8.8

# 方法2：通过PowerShell（推荐）
# 设置固定IP（NAT模式示例）
New-NetIPAddress `
    -InterfaceAlias "Ethernet" `
    -IPAddress "192.168.223.128" `
    -PrefixLength 24 `
    -DefaultGateway "192.168.223.2"

# 设置DNS
Set-DnsClientServerAddress `
    -InterfaceAlias "Ethernet" `
    -ServerAddresses ("8.8.8.8","8.8.4.4")
```

### 3.3 测试网络连通

```bash
# 在Mac终端测试

# 1. 测试虚拟机IP是否可达
ping 192.168.223.128

# 2. 测试RPC端口
nc -zv 192.168.223.128 2014
nc -zv 192.168.223.128 4102

# 如果端口未开放，需要在Windows防火墙添加规则
```

### 3.4 配置端口转发（NAT模式需要）

```bash
# 如果使用NAT模式，需要配置端口转发
# 在Mac终端执行：

# 找到VMware的网络配置文件
# 通常在：/Library/Preferences/VMware Fusion/networking

# 或通过VMware Fusion设置：
# 1. VMware Fusion -> 偏好设置 -> 网络
# 2. 选择NAT网络，点击"端口转发"
# 3. 添加规则：
#    - 主机端口：2014 -> 虚拟机IP:2014
#    - 主机端口：4102 -> 虚拟机IP:4102

# 或者更简单的方法：
# Mac端直接连接虚拟机的私有IP
# RPC配置中使用 192.168.223.128（虚拟机IP）
```

---

## 📥 第四步：在虚拟机中安装QMT和VeighNa

### 4.1 安装QMT

```powershell
# 1. 下载QMT安装包
# 从券商官网下载QMT交易终端

# 2. 安装到虚拟机
# 注意：确保虚拟机有足够的磁盘空间（至少20GB）

# 3. 配置MiniQMT路径
# 记录MiniQMT的路径，例如：
# C:\Program Files\QMT\userdata_mini\

# 4. 登录QMT
# 使用账号密码登录
# 确保可以正常查看行情和交易
```

### 4.2 在虚拟机中安装VeighNa

```powershell
# 1. 安装Python 3.11
# 下载：https://www.python.org/downloads/

# 2. 创建VeighNa环境
python -m venv vnpy_rpc
vnpy_rpc\Scripts\activate

# 3. 安装VeighNa
pip install vnpy
pip install vnpy_qmt
pip install vnpy_rpcservice

# 4. 复制VeighNa项目到虚拟机
# 或直接在虚拟机中git clone
```

### 4.3 配置RPC服务端

```python
# 在Windows虚拟机中创建：run_qmt_server.py

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.rpcservice import RpcServiceApp
from vnpy_qmt import QmtGateway

# RPC配置 - 绑定到所有接口
RPC_SETTING = {
    "req_address": "tcp://0.0.0.0:2014",  # 允许外网访问
    "sub_address": "tcp://0.0.0.0:4102",
}

# QMT配置
QMT_SETTING = {
    "交易账号": "40218291",
    "mini路径": "C:/Program Files/QMT/userdata_mini/",
}

# 启动服务
event_engine = EventEngine()
main_engine = MainEngine(event_engine)
main_engine.add_gateway(QmtGateway)
main_engine.add_app(RpcServiceApp)

# 启动RPC服务器
rpc_service = main_engine.get_app(RpcServiceApp)
rpc_service.start_server(
    req_address=RPC_SETTING["req_address"],
    sub_address=RPC_SETTING["sub_address"]
)

print(f"RPC服务已启动")
print(f"虚拟机IP: 192.168.223.128")
print(f"请求端口: 2014")
print(f"订阅端口: 4102")

# 保持运行
import time
while True:
    time.sleep(1)
```

### 4.4 Windows防火墙配置

```powershell
# 方法1：PowerShell命令（推荐）
# 添加入站规则
New-NetFirewallRule `
    -DisplayName "VeighNa RPC Request" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 2014 `
    -Action Allow

New-NetFirewallRule `
    -DisplayName "VeighNa RPC Subscribe" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 4102 `
    -Action Allow

# 方法2：图形界面
# 1. Windows Defender 防火墙 -> 高级设置
# 2. 入站规则 -> 新建规则
# 3. 端口 -> TCP -> 特定本地端口 -> 2014,4102
# 4. 允许连接
# 5. 完成

# 验证规则
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*VeighNa*"}
```

---

## 🍎 第五步：在Mac上配置VeighNa客户端

### 5.1 安装VeighNa

```bash
# 1. 安装Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Python 3.11
brew install python@3.11

# 3. 克隆VeighNa项目
cd ~
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
# 注意：不需要安装vnpy_qmt
```

### 5.2 创建RPC客户端

```python
# 在Mac上创建：run_qmt_client.py

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.rpc import RpcClient
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp
from vnpy_datamanager import DataManagerApp

# RPC配置 - 连接到Windows虚拟机
RPC_SETTING = {
    "req_address": "tcp://192.168.223.128:2014",  # Windows虚拟机IP
    "sub_address": "tcp://192.168.223.128:4102",
}

def main():
    """主函数"""
    # 创建Qt应用
    qapp = create_qapp()

    # 创建事件引擎
    event_engine = EventEngine()

    # 创建主引擎
    main_engine = MainEngine(event_engine)

    # 添加应用模块
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)
    main_engine.add_app(DataManagerApp)

    # 连接RPC到Windows虚拟机
    print("=" * 60)
    print("正在连接到Windows虚拟机RPC服务...")
    print(f"虚拟机IP: 192.168.223.128")
    print("=" * 60)

    rpc_client = RpcClient()
    try:
        rpc_client.connect(
            req_address=RPC_SETTING["req_address"],
            sub_address=RPC_SETTING["sub_address"]
        )
        print("✓ RPC连接成功！")
    except Exception as e:
        print(f"✗ RPC连接失败: {e}")
        print("\n请检查：")
        print("  1. Windows虚拟机是否已启动")
        print("  2. RPC服务是否已启动")
        print("  3. IP地址是否正确")
        print("  4. 防火墙是否已配置")

    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    # 启动Qt事件循环
    qapp.exec()

if __name__ == "__main__":
    main()
```

### 5.3 测试RPC连接

```bash
# 在Mac终端测试

# 1. 测试网络连通
ping -c 4 192.168.223.128

# 2. 测试端口开放
nc -zv 192.168.223.128 2014
nc -zv 192.168.223.128 4102

# 3. 启动VeighNa GUI
cd ~/vnpy/examples/client_server
python run_qmt_client.py
```

---

## ⚙️ 第六步：优化配置

### 6.1 虚拟机性能优化

```powershell
# 在VMware Fusion中设置：

【处理器和内存】
- 处理器：4核心或更多
- 内存：8GB或更多（建议不超过Mac总内存的50%）
- 勾选"启用hypervisor应用程序"

【高级选项】
- 勾选"禁用侧通道缓解"（性能提升20-30%）
- 勾选"启用虚拟机基于主机的电源管理"

【磁盘】
- 使用SSD存储
- 勾选"启用加速3D图形"（如需要GUI）

【电源管理】
- 虚拟机永不休眠
- Mac休眠时虚拟机可选择继续运行或暂停
```

### 6.2 自动启动配置

```powershell
# 在Windows虚拟机中配置RPC服务自动启动

# 方法1：创建启动脚本
# 1. 创建启动脚本：start_rpc.bat
@echo off
cd C:\vnpy\examples\client_server
python run_qmt_server.py

# 2. 将快捷方式放到启动文件夹
# Win+R -> shell:startup -> 粘贴快捷方式

# 方法2：使用Windows服务（高级）
# 使用nssm将Python脚本注册为Windows服务
```

### 6.3 虚拟机快照和备份

```bash
# 创建快照（在重要操作前）
VMware Fusion菜单 -> 虚拟机 -> 快照 -> 创建快照
命名：QMT就绪状态

# 恢复快照（出问题时）
VMware Fusion菜单 -> 虚拟机 -> 快照 -> 恢复到...

# 定期备份虚拟机
# 虚拟机文件位置：
# ~/Documents/Virtual Machines.localized/Windows-QMT.vmwarevm/
```

---

## 🧪 第七步：完整测试流程

### 7.1 连接测试清单

```markdown
□ Windows虚拟机启动
□ QMT已登录
□ RPC服务已启动
□ 防火墙规则已配置
□ 虚拟机IP地址已记录
□ Mac可以ping通虚拟机
□ Mac可以连接RPC端口
□ VeighNa GUI已启动
□ 策略可以加载
□ 委托可以发送（模拟环境）
```

### 7.2 功能测试

```python
# 测试脚本：test_rpc_connection.py

from vnpy.rpc import RpcClient

def test_connection():
    """测试RPC连接"""
    # 连接
    client = RpcClient()
    client.connect(
        req_address="tcp://192.168.223.128:2014",
        sub_address="tcp://192.168.223.128:4102"
    )

    print("测试RPC功能...")

    # 测试1：查询账户
    try:
        account = client.get_account()
        print(f"✓ 账户查询成功: {account.accountid}")
    except Exception as e:
        print(f"✗ 账户查询失败: {e}")

    # 测试2：查询持仓
    try:
        positions = client.get_positions()
        print(f"✓ 持仓查询成功: {len(positions)}只股票")
    except Exception as e:
        print(f"✗ 持仓查询失败: {e}")

    # 测试3：查询委托
    try:
        orders = client.get_orders()
        print(f"✓ 委托查询成功: {len(orders)}条委托")
    except Exception as e:
        print(f"✗ 委托查询失败: {e}")

    print("\n✓ 所有测试通过！")

if __name__ == "__main__":
    test_connection()
```

---

## 🔧 常见问题与解决方案

### Q1: 虚拟机IP地址变化

```markdown
问题：虚拟机重启后IP地址变了

解决方案：
1. 设置固定IP（推荐）
   - Windows网络设置 -> 手动配置IP
   - 使用上面第三步的方法

2. 使用主机名
   - 在Mac的/etc/hosts文件添加：
     192.168.223.128 windows-qmt
   - RPC配置使用主机名：
     "req_address": "tcp://windows-qmt:2014"

3. 使用DNS
   - 在虚拟机中安装Bonjour服务
   - 使用.local域名访问
```

### Q2: RPC连接超时

```markdown
问题：Mac无法连接到虚拟机RPC

排查步骤：
□ 1. 检查虚拟机是否运行
□ 2. 检查RPC服务是否启动
□ 3. 检查IP地址是否正确
□ 4. 检查Windows防火墙
□ 5. 测试端口：nc -zv 192.168.223.128 2014
□ 6. 检查VMware网络设置
□ 7. 重启虚拟机网络适配器
```

### Q3: 性能问题

```markdown
问题：虚拟机运行慢，RPC延迟高

优化方案：
1. 增加虚拟机资源（CPU/内存）
2. 使用SSD存储虚拟机
3. 启用虚拟机性能优化选项
4. 关闭Windows不必要的服务
5. 使用仅主机模式（最低延迟）
```

### Q4: Mac休眠后连接断开

```markdown
问题：Mac休眠后RPC连接断开

解决方案：
1. 配置自动重连
2. Mac设置不休眠（仅在使用外部显示器时）
3. 虚拟机保持运行
```

---

## 📊 方案对比总结

### VMware Fusion vs Parallels Desktop

| 对比项 | VMware Fusion | Parallels Desktop |
|--------|---------------|-------------------|
| **价格** | 免费版可用 | 付费（¥500+/年） |
| **性能** | 良好 | 优秀 |
| **易用性** | 中等 | 优秀 |
| **网络配置** | 灵活 | 简单 |
| **资源占用** | 较低 | 较高 |
| **稳定性** | 优秀 | 优秀 |
| **推荐场景** | 专业用户 | 普通用户 |

### 推荐选择

```
┌─────────────────────────────────────────────────────────────┐
│  VMware Fusion 更适合您，如果：                              │
│  • 预算有限（免费版足够）                                    │
│  • 需要灵活的网络配置                                        │
│  • 有一定的技术能力                                          │
│  • 需要运行多个虚拟机                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Parallels Desktop 更适合您，如果：                          │
│  • 预算充足                                                  │
│  • 追求最佳易用性                                            │
│  • 需要最高性能                                              │
│  • 不想折腾配置                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 快速开始检查清单

### 安装阶段

- [ ] 下载安装VMware Fusion
- [ ] 下载Windows 11镜像
- [ ] 创建虚拟机（4核8GB配置）
- [ ] 完成Windows安装
- [ ] 安装VMware Tools
- [ ] 配置网络（NAT或仅主机模式）
- [ ] 设置固定IP地址

### 配置阶段

- [ ] 在虚拟机安装QMT
- [ ] 在虚拟机安装VeighNa和RPC服务
- [ ] 配置Windows防火墙
- [ ] 在Mac安装VeighNa
- [ ] 配置RPC客户端连接
- [ ] 测试网络连通性

### 测试阶段

- [ ] 启动Windows虚拟机
- [ ] 登录QMT
- [ ] 启动RPC服务
- [ ] Mac连接RPC
- [ ] 测试账户查询
- [ ] 测试委托功能（模拟环境）
- [ ] 运行策略测试

### 运行阶段

- [ ] 配置虚拟机自动启动
- [ ] 配置RPC服务自动启动
- [ ] 创建虚拟机快照
- [ ] 配置定期备份
- [ ] 监控系统运行状态

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| VMware Fusion | https://www.vmware.com/go/getfusionplayer |
| VeighNa文档 | https://www.vnpy.com/docs |
| QMT接口文档 | https://zhuanlan.zhihu.com/p/595358960 |
| Windows 11下载 | https://www.microsoft.com/zh-cn/software-download/windows11 |

---

**文档版本**：v1.0
**最后更新**：2026-02-24
**维护者**：AI Assistant

---

## 🎉 总结

**VMware Fusion + RPC 方案的优势：**

✅ **本地运行，零延迟** - 虚拟网络通信，延迟<1ms
✅ **完全免费** - VMware Fusion Player个人使用免费
✅ **安全可靠** - 数据在本地，完全可控
✅ **灵活配置** - 网络模式可灵活选择
✅ **方便调试** - 可同时查看Mac和Windows界面
✅ **资源隔离** - Windows问题不影响Mac日常使用

这是Mac用户使用VeighNa + QMT的**最佳方案之一**，强烈推荐！
