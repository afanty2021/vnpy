# VeighNa A股交易系统 - 快速参考卡 (Cheat Sheet)

> 版本：v1.0 | 更新日期：2026-02-25

---

## 🚀 快速启动

```bash
# 启动交易系统
conda activate Quant-3.11
cd G:/Berton/vnpy
python examples/veighna_trader/run_qmt.py

# 启动 Web 监控
cd vnpy_china_monitor
python run_web.py

# 运行测试
pytest tests/ -v --tb=short
```

---

## 📦 模块导入速查

```python
# 核心模块
from vnpy_china_rules import TradingRulesEngine          # 交易规则
from vnpy_china_rules.risk import RiskManager          # 风险管理
from vnpy_china_data import DataService               # 数据服务
from vnpy_china_monitor import MonitorManager         # 监控告警
from vnpy_china_strategy import *                     # 策略库
from vnpy_china_backtest import ChinaBacktestEngine   # 回测引擎
from vnpy_china_capital import PositionSizer          # 资金管理
from vnpy_china_analysis import *                     # 行情分析
from vnpy_china_reporting import *                    # 报表系统
from vnpy_china_optimize import *                     # 参数优化
from vnpy_china_ml import *                           # 机器学习
from vnpy_china_config import ConfigManager, Environment  # 配置管理
```

---

## 🔧 常用代码片段

### T+1 规则检查

```python
from vnpy_china_rules import TradingRulesEngine

rules = TradingRulesEngine()
if rules.check_t1_sellable("000001.SZ", 100):
    print("可卖")
```

### 涨跌停检查

```python
limit = rules.calculate_price_limit("000001.SZ", 10.0)
print(f"涨停价: {limit.upper_limit}, 跌停价: {limit.lower_limit}")
```

### 获取股票列表

```python
from vnpy_china_data import DataService

data = DataService()
stocks = data.get_all_stocks()
```

### 发送告警

```python
from vnpy_china_monitor import MonitorManager, AlertChannel

monitor = MonitorManager()
monitor.send_alert("系统警告", "WARNING", [AlertChannel.EMAIL])
```

### 回测运行

```python
from vnpy_china_backtest import ChinaBacktestEngine

engine = ChinaBacktestEngine()
engine.set_data_start_date(datetime(2023, 1, 1))
engine.set_data_end_date(datetime(2024, 12, 31))
engine.load_data()
engine.run_backtest()
```

---

## ⚙️ 配置文件位置

```
.vntrader_china/
├── config/
│   ├── global_{env}.yaml      # 全局配置
│   ├── data_{env}.yaml         # 数据配置
│   ├── monitor_{env}.yaml     # 监控配置
│   └── strategy_{env}.yaml    # 策略配置
├── logs/                       # 日志文件
└── data/                       # 数据文件
```

环境：`development` | `testing` | `production`

---

## 🎯 策略模板

```python
from vnpy_china_strategy.base import ChinaStockStrategy

class MyStrategy(ChinaStockStrategy):
    def on_bar(self, bar):
        # 交易逻辑
        if self.should_buy(bar):
            self.buy(bar.close_price, 100)
        elif self.should_sell(bar):
            self.sell(bar.close_price, self.pos)
```

---

## 📊 数据获取

| 数据类型 | 方法 | 示例 |
|---------|------|------|
| 股票列表 | `get_all_stocks()` | `data.get_all_stocks()` |
| K线数据 | `get_bar_data()` | `data.get_bar_data(symbol, start, end, "1d")` |
| Tick数据 | `get_tick_data()` | `data.get_tick_data(symbol, start, end)` |
| 财务数据 | `get_financial_data()` | `data.get_financial_data(symbol)` |
| 资金流向 | `MoneyFlowAnalyzer.analyze()` | `analyzer.analyze(symbol)` |

---

## 🛡️ 风控配置

```python
from vnpy_china_rules.risk import PositionLimit, TradingLimit

# 仓位限制
PositionLimit(
    max_single_position=0.2,    # 单只股票20%
    max_total_position=0.8,     # 总仓位80%
    max_holdings=10              # 最多10只
)

# 交易限制
TradingLimit(
    max_orders_per_minute=10,   # 每分钟10单
    max_consecutive_losses=5,    # 最多连亏5次
    max_price_deviation=0.02     # 价格偏离2%
)
```

---

## 📈 报表生成

```python
from vnpy_china_reporting import TradingReportGenerator, ReportExporter

# 生成报告
generator = TradingReportGenerator()
report = generator.generate_daily_report(datetime.now())

# 导出
exporter = ReportExporter()
exporter.export_to_excel(report, "daily.xlsx")
exporter.export_to_pdf(report, "daily.pdf")
```

---

## 🧪 测试命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/analysis/ -v
pytest tests/capital/ -v
pytest tests/reporting/ -v

# 运行特定测试文件
pytest tests/test_config.py -v

# 显示覆盖率
pytest tests/ --cov=vnpy_china --cov-report=html
```

---

## 🔍 故障排查

| 问题 | 检查项 | 解决方案 |
|------|--------|----------|
| 无法连接 QMT | QMT 客户端状态 | 登录 QMT 客户端 |
| 数据获取失败 | Tushare Token | 检查 token 是否有效 |
| 数据库错误 | MySQL 服务 | 检查 MySQL 运行状态 |
| 内存不足 | 缓存配置 | 减少 cache_bar_ttl |
| 策略不交易 | 交易时间 | 检查是否在交易时间 |

---

## 📞 常用命令

```bash
# 查看日志
tail -f .vntrader_china/logs/vnpy_china.log

# 查看错误
grep ERROR .vntrader_china/logs/vnpy_china.log

# 检查进程
ps aux | grep vnpy

# 重启服务
python examples/no_ui/restart_system.py

# 备份数据
mysqldump -u vnpy_prod -p vnpy_china_prod > backup.sql
```

---

## 🎓 学习资源

- 完整文档: `docs/USER_MANUAL.md`
- 部署指南: `docs/PRODUCTION_DEPLOYMENT.md`
- 需求文档: `docs/A股交易系统增强需求文档.md`
- 示例代码: `examples/`
- 测试用例: `tests/`

---

**更新日期**: 2026-02-25
