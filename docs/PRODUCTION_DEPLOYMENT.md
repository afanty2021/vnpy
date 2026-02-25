# VeighNa A股交易系统 - 生产环境部署指南

> 文档版本：v1.0
> 创建日期：2026-02-25
> 适用版本：VeighNa 4.3.0

---

## 📋 部署前检查清单

### 1. 系统环境检查

- [ ] Python 3.11+ 已安装
- [ ] Conda 环境 Quant-3.11 已配置
- [ ] MySQL 8.0+ 已安装并运行
- [ ] Redis 6.0+ 已安装并运行
- [ ] QMT 交易客户端已安装并配置

### 2. 依赖包检查

```bash
# 进入项目目录
cd G:/Berton/vnpy

# 激活 Conda 环境
conda activate Quant-3.11

# 安装所有依赖
pip install -r requirements.txt

# 验证关键依赖
python -c "import vnpy; print('VeighNa OK')"
python -c "import vnpy_qmt; print('QMT Gateway OK')"
python -c "import pydantic; print('Pydantic OK')"
python -c "import polars; print('Polars OK')"
```

### 3. 数据库配置检查

```bash
# 验证 MySQL 连接
mysql -u root -p -e "SELECT VERSION();"

# 验证 Redis 连接
redis-cli ping
```

---

## 🔧 生产环境配置

### 1. 配置文件结构

```
.vntrader_china/
├── config/
│   ├── global_production.yaml    # 全局配置（生产环境）
│   ├── data_production.yaml       # 数据服务配置
│   ├── monitor_production.yaml    # 监控告警配置
│   ├── strategy_production.yaml   # 策略配置
│   ├── capital_production.yaml    # 资金管理配置
│   ├── analysis_production.yaml   # 行情分析配置
│   └── ml_production.yaml         # 机器学习配置
├── logs/                          # 日志目录
└── data/                          # 数据目录
```

### 2. 环境变量配置

创建 `.env.production` 文件：

```bash
# VeighNa A股交易系统 - 生产环境配置

# 运行环境
VNPY_ENV=production

# MySQL 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=vnpy_prod
MYSQL_PASSWORD=your_secure_password_here
MYSQL_DATABASE=vnpy_china_prod

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here
REDIS_DB=0

# Tushare API 配置
TUSHARE_TOKEN=your_tushare_token_here
TUSHARE_RATE_LIMIT=200

# QMT 交易接口配置
QMT_PATH=D:/国金证券QMT交易端/userdata_mini
QMT_ACCOUNT_ID=your_account_id

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/vnpy_china.log

# RPC 配置
RPC_REP_ADDRESS=tcp://127.0.0.1:2014
RPC_PUB_ADDRESS=tcp://127.0.0.1:4102

# 风控配置
RISK_MAX_POSITION_RATIO=0.8
RISK_MAX_SINGLE_POSITION_RATIO=0.2
RISK_MAX_DAILY_LOSS_RATIO=0.05
RISK_MAX_CONSECUTIVE_LOSSES=5

# 告警配置（邮件）
ALERT_EMAIL_ENABLED=true
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
EMAIL_USERNAME=your_email@qq.com
EMAIL_PASSWORD=your_email_password

# 告警配置（企业微信）
ALERT_WECHAT_ENABLED=true
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
```

### 3. 全局配置模板

创建 `config/global_production.yaml`：

```yaml
# VeighNa A股交易系统 - 全局配置（生产环境）

environment: production

# 数据库配置
database:
  mysql_host: localhost
  mysql_port: 3306
  mysql_user: vnpy_prod
  mysql_password: ${MYSQL_PASSWORD}
  mysql_database: vnpy_china_prod
  redis_host: localhost
  redis_port: 6379
  redis_password: ${REDIS_PASSWORD}
  redis_db: 0
  pool_size: 10
  max_overflow: 20

# 日志配置
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_enabled: true
  file_path: logs/vnpy_china.log
  max_bytes: 104857600  # 100MB
  backup_count: 10
  console_enabled: false

# RPC 配置
rpc:
  rep_address: tcp://127.0.0.1:2014
  pub_address: tcp://127.0.0.1:4102
  timeout: 5000

# 风控全局参数
risk:
  max_position_ratio: 0.8
  max_single_position_ratio: 0.2
  max_daily_loss_ratio: 0.05
  max_consecutive_losses: 5

# 目录配置
work_dir: .vntrader_china
data_dir: data
```

---

## 🚀 启动流程

### 1. 数据库初始化

```bash
# 创建生产数据库
mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS vnpy_china_prod
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'vnpy_prod'@'localhost'
IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON vnpy_china_prod.*
TO 'vnpy_prod'@'localhost';

FLUSH PRIVILEGES;
"

# 初始化数据表
cd G:/Berton/vnpy
python -c "
from vnpy_china_data import DatabaseManager
db = DatabaseManager()
db.create_tables()
print('数据库初始化完成')
"
```

### 2. 启动监控和告警系统

```bash
# 启动 Web 监控系统（可选）
cd G:/Berton/vnpy/vnpy_china_monitor
python run_web.py

# 或启动后台监控守护进程
python -m vnpy_china_monitor daemon
```

### 3. 启动交易系统

```bash
# 方式1：使用启动脚本
cd G:/Berton/vnpy
python examples/veighna_trader/run_qmt.py

# 方式2：使用无界面守护进程
python examples/no_ui/run_qmt_daemon.py
```

### 4. 验证系统状态

```python
# 验证脚本
from vnpy_china_config import ConfigManager, Environment

manager = ConfigManager()
manager.set_environment(Environment.PRODUCTION)

# 加载配置
global_config = manager.load_global_config()
data_config = manager.load_module_config("data", DataModuleConfig)

# 验证配置
print(f"环境: {global_config.environment}")
print(f"MySQL: {global_config.database.mysql_host}")
print(f"Redis: {global_config.database.redis_host}")
print(f"Tushare: {'***' + data_config.tushare_token[-4:]}")

# 验证数据库连接
from vnpy_china_data import DatabaseManager
db = DatabaseManager()
if db.test_connection():
    print("✓ 数据库连接正常")
else:
    print("✗ 数据库连接失败")

# 验证 Redis 连接
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
try:
    r.ping()
    print("✓ Redis 连接正常")
except:
    print("✗ Redis 连接失败")
```

---

## 📊 监控和维护

### 1. 日志监控

```bash
# 实时查看日志
tail -f .vntrader_china/logs/vnpy_china.log

# 查看错误日志
grep ERROR .vntrader_china/logs/vnpy_china.log

# 查看交易日志
grep "成交通知" .vntrader_china/logs/vnpy_china.log
```

### 2. 性能监控

```python
# 系统状态检查脚本
import psutil
import time
from vnpy_china_monitor import SystemMonitor

monitor = SystemMonitor()

# 检查 CPU 使用率
cpu_percent = psutil.cpu_percent(interval=1)
print(f"CPU 使用率: {cpu_percent}%")
if cpu_percent > 80:
    print("⚠️ CPU 使用率过高！")

# 检查内存使用
memory = psutil.virtual_memory()
print(f"内存使用: {memory.percent}%")
if memory.percent > 80:
    print("⚠️ 内存使用率过高！")

# 检查磁盘空间
disk = psutil.disk_usage('.')
print(f"磁盘使用: {disk.percent}%")
if disk.percent > 90:
    print("⚠️ 磁盘空间不足！")
```

### 3. 数据备份

```bash
# 每日备份脚本
#!/bin/bash
BACKUP_DIR="/backup/vnpy_china/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 备份数据库
mysqldump -u vnpy_prod -p vnpy_china_prod > "$BACKUP_DIR/database.sql"

# 备份配置文件
cp -r .vntrader_china/config "$BACKUP_DIR/"

# 备份日志（最近7天）
find .vntrader_china/logs -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \;

# 压缩备份
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

# 删除30天前的备份
find /backup/vnpy_china -mtime +30 -delete
```

---

## ⚠️ 故障处理

### 1. QMT 连接断开

```python
# 自动重连脚本
from vnpy_qmt import QmtGateway
import time

gateway = QmtGateway()

while True:
    try:
        if not gateway.isConnected():
            print("尝试重新连接 QMT...")
            gateway.connect()
            time.sleep(5)
            if gateway.isConnected():
                print("✓ QMT 重连成功")
        time.sleep(60)  # 每分钟检查一次
    except Exception as e:
        print(f"重连异常: {e}")
        time.sleep(30)
```

### 2. 数据库连接失败

```bash
# 检查 MySQL 状态
systemctl status mysql
# 或 Windows
net start MySQL80

# 重启 MySQL
systemctl restart mysql
# 或 Windows
net stop MySQL80 && net start MySQL80
```

### 3. 内存溢出

```bash
# 查找内存泄漏
python -m memory_profiler examples/veighna_trader/run_qmt.py

# 清理缓存
redis-cli FLUSHDB

# 重启系统
python examples/no_ui/restart_system.py
```

---

## 📞 应急响应

### 紧急停止交易

```python
# 紧急停止脚本
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine

event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 停止所有策略
all_strategies = main_engine.get_all_strategies()
for strategy in all_strategies:
    main_engine.stop_strategy(strategy)

# 取消所有委托
all_orders = main_engine.get_all_orders()
for order in all_orders:
    if order.status == 'ACTIVE':
        main_engine.cancel_order(order)

print("✓ 所有策略已停止，所有委托已撤销")
```

### 风险触发处理

```python
# 风险监控脚本
from vnpy_china_rules.risk import RiskManager

risk_manager = RiskManager()

# 检查单日亏损
daily_loss = risk_manager.get_daily_loss_ratio()
if daily_loss > 0.05:  # 超过5%
    print("⚠️ 触发单日最大亏损限制！")
    risk_manager.stop_all_trading()
    risk_manager.send_alert("触发单日最大亏损限制，已停止所有交易")

# 检查连续亏损
consecutive_losses = risk_manager.get_consecutive_losses()
if consecutive_losses >= 5:
    print("⚠️ 触发连续亏损限制！")
    risk_manager.stop_all_trading()
    risk_manager.send_alert("触发连续亏损限制，已停止所有交易")
```

---

## 📝 维护计划

### 日常维护任务

| 任务 | 频率 | 负责人 |
|------|------|--------|
| 检查系统日志 | 每日 | 运维 |
| 数据备份 | 每日 | 自动化 |
| 性能监控 | 每日 | 自动化 |
| 策略绩效回顾 | 每周 | 交易员 |
| 系统更新 | 每月 | 开发 |
| 全面安全审计 | 每季度 | 安全 |

### 月度检查清单

- [ ] 检查数据库磁盘空间
- [ ] 清理过期日志文件
- [ ] 验证备份完整性
- [ ] 检查系统性能指标
- [ ] 更新交易规则数据
- [ ] 检查依赖包更新
- [ ] 审查告警规则配置

---

## 📧 联系方式

如有部署问题，请联系：
- 技术支持：[待填写]
- 紧急联系：[待填写]

---

**文档版本**：v1.0
**创建日期**：2026-02-25
**维护者**：AI Assistant
