# VeighNa A股量化交易系统 — 部署指南

> 从零开始在 Windows 上部署完整的 A 股量化交易系统，包含数据下载、策略回测、实盘交易功能。

## 前置条件

| 项目 | 要求 | 说明 |
|------|------|------|
| 操作系统 | Windows 10/11 64位 | MiniQMT 仅支持 Windows |
| Python | 3.10 - 3.13 | 推荐 3.11 |
| Conda | Miniconda 或 Anaconda | 推荐 Miniconda |
| MiniQMT | 国金证券 QMT 交易端 | 必须安装并登录 |
| MySQL | 5.7+ 或 8.0+ | 推荐 8.0+ |
| Redis | 5.0+ | 数据缓存 |
| Git | 任意版本 | 拉取代码 |

---

## 步骤一：获取代码

```bash
git clone <仓库地址> vnpy
cd vnpy
```

---

## 步骤二：创建 Conda 环境

```bash
# 创建环境
conda create -n quant-3.11 python=3.11 -y

# 激活环境
conda activate quant-3.11
```

---

## 步骤三：安装依赖

### 3.1 安装 VeighNa 核心

```bash
# 编辑模式安装（推荐，便于开发调试）
pip install -e .
```

### 3.2 安装 QMT 相关包

```bash
# QMT 交易接口
pip install vnpy_qmt

# xtquant（QMT Python API，从 MiniQMT 安装目录安装）
# 方式一：如果 pip 能找到
pip install xtquant

# 方式二：从 MiniQMT 安装目录安装
pip install "D:/国金证券QMT交易端/userdata_mini/XtQuant-Python/packages/xtquant-xxx.whl"
```

### 3.3 安装其他依赖

```bash
# RPC 服务（服务端必需）
pip install vnpy_rpcservice

# SQLite 存储（回测必需）
pip install vnpy_sqlite

# 数据库驱动
pip install pymysql dbutils

# Redis 客户端
pip install redis

# GUI 依赖
pip install qdarkstyle

# Alpha 量化研究模块（可选）
pip install polars scikit-learn lightgbm
```

### 3.4 验证安装

```bash
python test_qmt_installation.py
```

所有检查项应显示 `[OK]`。

---

## 步骤四：应用补丁

> **关键步骤！** pip 安装的 `vnpy_qmt` 缺少 `query_history` 方法，必须应用补丁。

### 方式一：自动部署（推荐）

```bash
python patches/deploy_vnpy_qmt_fix.py
```

### 方式二：手动部署

如果自动脚本找不到 conda 环境，手动复制 4 个文件：

```bash
# 查找 site-packages 路径
python -c "import vnpy_qmt; print(vnpy_qmt.__file__)"
# 输出类似：D:\Scoop\apps\miniconda3\current\envs\quant-3.11\Lib\site-packages\vnpy_qmt\__init__.py

# 设置目标目录
set TARGET=D:\Scoop\apps\miniconda3\current\envs\quant-3.11\Lib\site-packages\vnpy_qmt

# 复制补丁文件
copy patches\md.py          %TARGET%\md.py
copy patches\td.py          %TARGET%\td.py
copy patches\utils.py       %TARGET%\utils.py
copy patches\qmt_gateway.py %TARGET%\qmt_gateway.py
```

### 补丁文件说明

| 文件 | 作用 |
|------|------|
| `md.py` | 添加 `query_history` 方法，支持通过 xtquant 下载历史 K 线数据 |
| `qmt_gateway.py` | 添加 `query_history` 委托方法，添加港股通交易所支持 |
| `utils.py` | 添加港股通交易所映射（SHHK/SZHK/SEHK） |
| `td.py` | 修复账户 `balance` 字段使用 `asset.cash`（可用现金） |

> ⚠️ **重要**：每次 `pip install --upgrade vnpy_qmt` 后，必须重新应用补丁！

---

## 步骤五：配置外部服务

### 5.1 MySQL

#### 安装 MySQL

如果尚未安装 MySQL，参考 [mysql_init_guide.md](mysql_init_guide.md)。

#### 创建数据库和用户

```sql
-- 以 root 登录
mysql -u root -p

-- 创建数据库
CREATE DATABASE vnpy_china CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'vnpy_dev'@'localhost' IDENTIFIED BY 'VnpyDev2024!';
GRANT ALL PRIVILEGES ON vnpy_china.* TO 'vnpy_dev'@'localhost';

FLUSH PRIVILEGES;
```

也可以使用自动化脚本：

```bash
python init_mysql_database.py
```

#### 设置环境变量

```bash
# 设置 MySQL 密码环境变量（永久生效）
setx MYSQL_PASSWORD "VnpyDev2024!"
```

#### 初始化数据库表

```bash
python init_database.py
```

该脚本会创建以下表：
- `db_bar_data` — K 线数据
- `db_stock_info` — 股票信息
- `db_hk_connect_stocks` — 港股通股票
- `db_capital_flow` — 资金流向

### 5.2 Redis

#### Windows 安装

```bash
# 方式一：Scoop（推荐）
scoop install redis

# 方式二：Chocolatey
choco install redis-64

# 方式三：手动下载
# https://github.com/tporadowski/redis/releases
```

#### 启动 Redis

```bash
# 前台运行（调试用）
redis-server

# 后台运行（带内存限制）
redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

# 注册为 Windows 服务（开机自启）
redis-server --service-install redis.windows.conf
redis-server --service-start
```

#### 验证

```bash
redis-cli ping
# 应返回：PONG
```

---

## 步骤六：配置文件

### 6.1 创建配置目录

```bash
mkdir -p .vntrader_china\config
```

### 6.2 全局配置

项目已收敛为单环境配置（client/server 共用），直接编辑 `.vntrader_china/config/config.yaml`：

```bash
# 直接使用项目中已有的配置文件 .vntrader_china/config/config.yaml
# 只需修改以下内容：
```

需要修改的关键配置项（`.vntrader_china/config/config.yaml`）：

```yaml
# QMT 配置 — 必须修改
qmt:
  account_id: "你的QMT账号"        # ← 改成你的
  mini_path: "D:/国金证券QMT交易端/userdata_mini/"  # ← 改成你的安装路径

# 数据库配置 — 如果密码不同需修改
database:
  mysql_user: vnpy_dev
  mysql_password: 'VnpyDev2024!'
  mysql_database: vnpy_china
```

### 6.3 QMT 网关配置

编辑 `.vntrader_china/config/qmt_gateway.yaml`：

```yaml
qmt:
  account_id: '你的QMT账号'
  mini_path: 'D:/国金证券QMT交易端/userdata_mini/'
```

### 6.4 环境变量（可选）

```bash
setx MYSQL_PASSWORD "VnpyDev2024!"
setx REDIS_PASSWORD ""
setx TUSHARE_TOKEN "你的Tushare令牌"
setx QMT_ACCOUNT_ID "你的QMT账号"
```

---

## 步骤七：启动系统

### 7.0 启动 MiniQMT

> 必须先启动 QMT 交易端并登录账号！

1. 打开「国金证券 QMT 交易端」
2. 登录你的交易账号
3. 确认 MiniQMT 运行（任务栏右下角应有图标）

### 7.1 启动 Redis

```bash
redis-server --maxmemory 512mb
```

### 7.2 启动 QMT RPC 服务端

```bash
# 新开一个终端
conda activate quant-3.11
python examples/client_server/run_qmt_server_full.py
```

等待看到以下输出：

```
============================================================
服务运行中，按Ctrl+C停止
============================================================
[QMT] [ td ] 连接成功
[QMT] [ td ] 登录账户成功
```

### 7.3 启动 QMT 客户端（GUI 界面）

```bash
# 再开一个终端
conda activate quant-3.11
python examples/client_server/run_qmt_client.py
```

VeighNa 主窗口应弹出，可以正常操作。

---

## 步骤八：验证

### 8.1 安装验证

```bash
python test_qmt_installation.py
```

### 8.2 一键验证

```bash
python scripts/deploy.py --verify
```

### 8.3 手动验证清单

| 检查项 | 验证方法 | 期望结果 |
|--------|----------|----------|
| Python 版本 | `python --version` | 3.10+ |
| xtquant | `python -c "from xtquant import xtdata"` | 无报错 |
| vnpy_qmt 补丁 | `python -c "from vnpy_qmt.md import MD; print('query_history' in dir(MD))"` | `True` |
| MySQL 连接 | `python -c "import pymysql; c=pymysql.connect(host='localhost',user='vnpy_dev',password='VnpyDev2024!',database='vnpy_china'); print('OK')"` | `OK` |
| Redis 连接 | `redis-cli ping` | `PONG` |
| RPC 服务端 | `netstat -an \| findstr "2014.*LISTENING"` | 有输出 |
| 数据下载 | 界面中选择 600660.SSE，下载最近 30 天日线 | 返回非 0 条数据 |

---

## 常见问题

### Q1: `ModuleNotFoundError: No module named 'xxx'`

在 quant-3.11 环境中安装缺失的包：

```bash
conda activate quant-3.11
pip install xxx
```

### Q2: 界面下载显示"成功: 0 条数据"

最常见原因：**补丁未应用**。运行 `python patches/deploy_vnpy_qmt_fix.py` 并重启服务端。

其他可能：
- MiniQMT 未登录
- RPC 服务端未启动
- 当前在交易时段（9:30-11:30, 13:00-15:00），RPC QMT 会跳过查询

### Q3: RPC 服务端报错 `_pickle.UnpicklingError`

不要向 RPC 端口发送 JSON 数据。VeighNa RPC 使用 pickle 序列化协议。
测试 RPC 时必须使用 `RpcClient` 子类，不要直接用 zmq 的 `send_json()`。

### Q4: MySQL `Table 'xxx' doesn't exist`

运行数据库初始化：

```bash
python init_database.py
```

### Q5: Redis 连接失败

```bash
# 检查 Redis 是否运行
redis-cli ping

# 如果未运行，启动它
redis-server
```

### Q6: pip install -e . 报错 ta-lib 安装失败

ta-lib 需要编译。Windows 上建议使用预编译包：

```bash
# 从 https://github.com/cgohlke/talib-build/releases 下载 whl 文件
pip install TA_Lib-0.6.4-cp311-cp311-win_amd64.whl
```

或者使用 conda 安装：

```bash
conda install -c conda-forge ta-lib
```

---

## 快速部署脚本

一键完成步骤三到步骤五：

```bash
conda activate quant-3.11
python scripts/deploy.py
```

---

## 目录结构参考

```
vnpy/
├── .vntrader_china/          # 运行时配置和数据
│   └── config/
│       ├── config.yaml                # 全局配置（单环境，client/server 共用）
│       ├── qmt_gateway.yaml           # QMT 网关配置
│       └── data.yaml                  # 数据服务配置
├── patches/                  # 补丁文件
│   ├── md.py                 # 历史数据查询补丁
│   ├── qmt_gateway.py        # 网关补丁（含 query_history 委托）
│   ├── utils.py              # 港股通交易所映射补丁
│   ├── td.py                 # 交易账户字段补丁
│   └── deploy_vnpy_qmt_fix.py  # 自动部署脚本
├── config_templates/         # 配置文件模板
├── scripts/
│   ├── deploy.py             # 一键部署脚本
│   └── init_database.py      # 数据库初始化
├── init_database.py          # 数据库建表
├── init_mysql_database.py    # MySQL 初始化
├── test_qmt_installation.py  # 安装验证
└── examples/
    └── client_server/
        ├── run_qmt_server_full.py  # RPC 服务端
        └── run_qmt_client.py       # GUI 客户端
```

---

*最后更新：2026-07-01*
