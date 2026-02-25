# QMT RPC 客户端配置指南

> 更新时间：2026-02-25

## 配置方式

### 方式1：配置文件（推荐）

在项目根目录创建配置文件 `.vntrader_china/config/data_development.yaml`：

```yaml
# QMT RPC配置
qmt_use_rpc: true
qmt_rpc_req_address: "tcp://192.168.2.168:2014"
qmt_rpc_sub_address: "tcp://192.168.2.168:4102"
```

**说明**：
- 将 `192.168.2.168` 替换为您的 Windows 机器 IP 地址
- 端口 `2014` 是 RPC 请求端口
- 端口 `4102` 是 RPC 订阅端口

### 方式2：环境变量

设置环境变量来覆盖配置文件中的值：

```bash
# macOS/Linux
export QMT_RPC_REQ_ADDRESS="tcp://192.168.2.168:2014"
export QMT_RPC_SUB_ADDRESS="tcp://192.168.2.168:4102"

# Windows PowerShell
$env:QMT_RPC_REQ_ADDRESS="tcp://192.168.2.168:2014"
$env:QMT_RPC_SUB_ADDRESS="tcp://192.168.2.168:4102"
```

### 方式3：虚拟机（Parallels/VMware）

如果在 Mac 上使用 Parallels/VMware 虚拟机运行 Windows：

```yaml
# 虚拟机通常使用桥接网络，IP可能不同
# 可以使用 localhost（如果端口转发配置正确）
qmt_rpc_req_address: "tcp://127.0.0.1:2014"
qmt_rpc_sub_address: "tcp://127.0.0.1:4102"
```

**Parallels 端口转发配置**：
1. 打开 Parallels Desktop
2. 选择虚拟机 → 配置 → 硬件 → 网络
3. 源端口：2014、4102
4. 协议：TCP
5. 转发到：localhost

## 网络配置示例

### 局域网环境

```
┌─────────────────────────────────────────────────────────────┐
│  Mac 客户端                   Windows 服务器（QMT服务端）          │
│  IP: 192.168.2.50             IP: 192.168.2.168                │
│  运行 run_qmt_client.py        运行 run_qmt_server.py          │
├─────────────────────────────────────────────────────────────┤
│  配置:                                                        │
│  qmt_rpc_req_address: "tcp://192.168.2.168:2014"            │
│  qmt_rpc_sub_address: "tcp://192.168.2.168:4102"            │
└─────────────────────────────────────────────────────────────┘
```

### Parallels 虚拟机环境

```
┌─────────────────────────────────────────────────────────────┐
│  Mac 主机                                                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  macOS                                                    │ │
│  │  运行 run_qmt_client.py                                 │ │
│  │  配置: localhost                                       │ │
│  │         │                                               │ │
│  │         ↓ 端口转发                                      │ │
│  │  ┌───────────────────────────────────────────────────┐  │ │
│  │  │  Parallels Windows 虚拟机                          │  │ │
│  │  │  运行 run_qmt_server.py                            │  │ │
│  │  │  监听: 0.0.0.0:2014, 0.0.0.0:4102              │  │ │
│  │  └───────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 云服务器环境

```
┌─────────────────────────────────────────────────────────────┐
│  Mac 客户端（任意位置）                                      │
│  运行 run_qmt_client.py                                     │
│                                                              │
│  配置:                                                        │
│  qmt_rpc_req_address: "tcp://YOUR_SERVER_IP:2014"            │
│  qmt_rpc_sub_address: "tcp://YOUR_SERVER_IP:4102"            │
│                         │                                       │
│                         ↓ 互联网（VPN/公网IP）                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  云服务器（Windows Server）                              ││
│  │  公网IP: YOUR_SERVER_IP                                ││
│  │  安全组开放: 2014, 4102                                ││
│  │  运行 run_qmt_server.py                                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 启动步骤

### Windows 服务端

```bash
# 1. 进入项目目录
cd G:\Berton\VNPY\examples\client_server

# 2. 启动 QMT RPC 服务端
python run_qmt_server.py
```

输出示例：
```
==============================================================
VeighNa RPC服务端 - QMT版本
==============================================================
RPC服务已启动：
  请求地址: tcp://0.0.0.0:2014
  订阅地址: tcp://0.0.0.0:4102

网络配置提示：
  1. 本地测试：使用 127.0.0.1 即可
  2. 局域网：使用实际IP地址，如 192.168.1.100
  3. 外网访问：需要端口映射和防火墙配置
```

### Mac/Linux 客户端

```bash
# 1. 配置 RPC 地址（选择一种方式）

# 方式1：编辑配置文件
# 创建 .vntrader_china/config/data_development.yaml
# 设置 qmt_rpc_req_address 和 qmt_rpc_sub_address

# 方式2：设置环境变量
export QMT_RPC_REQ_ADDRESS="tcp://192.168.2.168:2014"
export QMT_RPC_SUB_ADDRESS="tcp://192.168.2.168:4102"

# 2. 启动客户端
cd /Users/berton/Github/vnpy/examples/client_server
python run_qmt_client.py
```

## 常见问题

### Q1: 连接超时

**问题**：客户端无法连接到服务端

**排查步骤**：
1. 检查 Windows 服务端是否运行 `run_qmt_server.py`
2. 检查 Windows 防火墙是否开放 2014、4102 端口
3. 使用 `ping` 命令测试网络连通性
4. 检查配置文件中的 IP 地址是否正确

**Windows 防火墙配置**：
```powershell
# 添加入站规则
netsh advfirewall firewall add rule `
    name="VeighNa RPC" `
    dir=in action=allow protocol=TCP localport=2014,4102
```

### Q2: 虚拟机网络不通

**问题**：Parallels/VMware 虚拟机无法连接

**解决方案**：
1. 检查虚拟机网络模式（建议使用桥接模式）
2. 在 Windows 虚拟机中查看 IP 地址：
   ```powershell
   ipconfig
   ```
3. 在 Mac 中测试连通性：
   ```bash
   ping <Windows虚拟机IP>
   ```

### Q3: 配置文件不生效

**问题**：修改配置文件后仍然使用旧配置

**解决方案**：
1. 确认配置文件路径：`.vntrader_china/config/data_development.yaml`
2. 配置文件会自动创建，使用默认值
3. 环境变量优先级高于配置文件
4. 重启客户端以加载新配置

## 安全建议

### 局域网使用

✅ **推荐**：在局域网内使用 RPC 连接
- 保持 Windows 和 Mac 在同一网络
- 使用防火墙限制访问
- 定期更换端口号

### 互联网使用

⚠️ **谨慎**：如需互联网访问
1. **使用 VPN**：建立加密通道
2. **配置 SSL/TLS**：加密 RPC 通信
3. **IP 白名单**：限制客户端 IP 访问
4. **定期更换端口**：避免使用默认端口

### 端口配置建议

```yaml
# 生产环境建议使用自定义端口
qmt_rpc_req_address: "tcp://YOUR_SERVER_IP:PORT_1"
qmt_rpc_sub_address: "tcp://YOUR_SERVER_IP:PORT_2"

# 避免使用默认端口 2014、4102
# 定期更换端口号提高安全性
```

## 测试连接

### 测试 RPC 连通性

```bash
# 测试端口是否开放（Mac上执行）
nc -zv 192.168.2.168 2014
nc -zv 192.168.2.168 4102

# 预期输出：
# Connection to 192.168.2.168 port 2014 [tcp/*] succeeded!
# Connection to 192.168.2.168 port 4102 [tcp/*] succeeded!
```

### 使用测试脚本

```bash
# 运行 RPC 连接测试
python -m vnpy_china_data.examples.test_rpc_qmt
```

---

**文档版本**：v1.0
**最后更新**：2026-02-25
**维护者**：AI Assistant
