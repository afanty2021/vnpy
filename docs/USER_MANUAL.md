# VeighNa A股交易系统 - 用户手册

> 文档版本：v1.0
> 创建日期：2026-02-25
> 适用版本：VeighNa 4.3.0

---

## 📚 目录

1. [快速开始](#快速开始)
2. [核心模块使用](#核心模块使用)
3. [API 参考](#api-参考)
4. [策略开发指南](#策略开发指南)
5. [常见问题](#常见问题)
6. [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 环境准备

```bash
# 1. 激活 Conda 环境
conda activate Quant-3.11

# 2. 进入项目目录
cd G:/Berton/vnpy

# 3. 验证安装
python -c "import vnpy; print('VeighNa OK')"
```

### 启动交易系统

```python
# 最简启动示例
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_qmt import QmtGateway

def main():
    """启动交易系统"""
    # 创建事件引擎和主引擎
    qapp = create_qapp()
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加 QMT 交易接口
    main_engine.add_gateway(QmtGateway)

    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.show()

    # 运行
    qapp.exec()

if __name__ == "__main__":
    main()
```

---

## 🧩 核心模块使用

### 1. A股交易规则 (vnpy_china_rules)

#### T+1 交易规则控制

```python
from vnpy_china_rules import TradingRulesEngine

# 创建规则引擎
rules_engine = TradingRulesEngine()

# 检查股票是否可卖（T+1规则）
symbol = "000001.SZ"
volume = 100  # 卖出100股

if rules_engine.check_t1_sellable(symbol, volume):
    print("✓ 可以卖出")
else:
    print("✗ T+1规则限制，当日买入不可卖出")

# 获取可卖出数量
sellable_volume = rules_engine.get_sellable_volume(symbol)
print(f"可卖出数量: {sellable_volume}")
```

#### 涨跌停板检测

```python
from vnpy_china_rules import TradingRulesEngine
from datetime import datetime

rules_engine = TradingRulesEngine()

# 计算涨跌停价格
symbol = "000001.SZ"
prev_close = 10.0  # 昨日收盘价

limit = rules_engine.calculate_price_limit(symbol, prev_close)
print(f"涨停价: {limit.upper_limit}")
print(f"跌停价: {limit.lower_limit}")

# 判断价格是否有效
price = 10.5
if rules_engine.is_price_valid(symbol, price):
    print("✓ 价格有效")
else:
    print("✗ 价格超过涨跌停限制")

# 判断是否触及涨跌停
if rules_engine.is_price_limit_reached(symbol, price):
    print("⚠️ 价格触及涨跌停")
```

#### 交易时间验证

```python
from vnpy_china_rules import TradingRulesEngine
from datetime import datetime

rules_engine = TradingRulesEngine()

# 判断是否在交易时间
if rules_engine.is_trading_time():
    print("✓ 当前在交易时间")
    phase = rules_engine.get_trading_phase()
    print(f"交易时段: {phase}")
else:
    print("✗ 当前不在交易时间")

# 交易时段: pre_open（集合竞价）, trading（交易中）, close（收盘）
```

#### 交易单位控制

```python
from vnpy_china_rules import TradingRulesEngine

rules_engine = TradingRulesEngine()

# 将数量取整到交易单位（100股）
rounded_volume = rules_engine.round_lot_volume(1055)
print(f"取整后数量: {rounded_volume}")  # 输出: 1000

# 验证委托数量是否符合规则
if rules_engine.validate_order_volume("000001.SZ", 100, "buy"):
    print("✓ 委托数量符合规则")
else:
    print("✗ 委托数量不符合规则")
```

### 2. 风险管理系统 (vnpy_china_rules/risk)

```python
from vnpy_china_rules.risk import RiskManager, PositionLimit, TradingLimit

# 创建风控管理器
risk_manager = RiskManager()

# 设置仓位限制
position_limit = PositionLimit(
    max_single_position=0.2,    # 单只股票最大20%
    max_total_position=0.8,     # 总仓位最大80%
    max_industry_ratio=0.4,      # 单一行业最大40%
    max_holdings=10              # 最多持仓10只
)

# 检查仓位限制
if risk_manager.check_position_limit("000001.SZ", 100, 10.0):
    print("✓ 仓位检查通过")
else:
    print("✗ 超过仓位限制")

# 设置交易限制
trading_limit = TradingLimit(
    max_orders_per_minute=10,
    max_orders_per_day=100,
    max_cancel_ratio=0.5,
    max_price_deviation=0.02,
    max_consecutive_losses=5
)

# 检查交易限制
if risk_manager.check_trading_limit(order_data):
    print("✓ 交易限制检查通过")
else:
    print("✗ 超过交易限制")
```

### 3. A股数据服务 (vnpy_china_data)

```python
from vnpy_china_data import DataService, DatabaseManager

# 创建数据服务
data_service = DataService()

# 获取股票列表
from vnpy_china_data.objects import StockInfo
all_stocks = data_service.get_all_stocks()
print(f"股票数量: {len(all_stocks)}")

# 获取股票基本信息
stock_info = data_service.get_stock_info("000001.SZ")
print(f"股票名称: {stock_info.name}")
print(f"所属行业: {stock_info.industry}")

# 获取日线数据
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

bars = data_service.get_bar_data(
    symbol="000001.SZ",
    start_date=start_date,
    end_date=end_date,
    interval="1d"
)
print(f"K线数据数量: {len(bars)}")

# 获取财务数据
financial = data_service.get_financial_data("000001.SZ")
print(f"PE: {financial.pe_ratio}")
print(f"PB: {financial.pb_ratio}")
```

### 4. 监控告警系统 (vnpy_china_monitor)

```python
from vnpy_china_monitor import MonitorManager, AlertChannel

# 创建监控管理器
monitor_manager = MonitorManager()

# 配置系统监控
monitor_manager.configure_system_monitor(
    cpu_threshold=80.0,
    memory_threshold=80.0,
    disk_threshold=90.0,
    check_interval=60
)

# 配置交易监控
monitor_manager.configure_trade_monitor(
    enable_trade_monitor=True,
    check_interval=10
)

# 发送告警
monitor_manager.send_alert(
    message="系统异常警告",
    level="WARNING",
    channels=[AlertChannel.EMAIL, AlertChannel.WECHAT]
)

# 添加告警规则
from vnpy_china_monitor.alert import AlertRule

rule = AlertRule(
    name="仓位预警",
    condition=lambda: risk_manager.get_total_position_ratio() > 0.8,
    message_template="总仓位超过80%：{ratio:.1%}",
    level="WARNING",
    channels=[AlertChannel.EMAIL],
    cooldown=300
)
monitor_manager.add_alert_rule(rule)
```

### 5. A股特色策略库 (vnpy_china_strategy)

#### 龙虎榜策略

```python
from vnpy_china_strategy.dragon_tiger import DragonTigerStrategy

class MyDragonTigerStrategy(DragonTigerStrategy):
    """龙虎榜策略示例"""

    def __init__(self, strategy_engine, strategy_name, vt_symbol, setting):
        super().__init__(strategy_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.follow_institution = setting.get("follow_institution", True)
        self.min_buy_amount = setting.get("min_buy_amount", 1000000)  # 100万
        self.max_position_count = setting.get("max_position_count", 5)
```

#### 北向资金策略

```python
from vnpy_china_strategy.northbound import NorthBoundStrategy

class MyNorthBoundStrategy(NorthBoundStrategy):
    """北向资金策略示例"""

    def __init__(self, strategy_engine, strategy_name, vt_symbol, setting):
        super().__init__(strategy_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.follow_threshold = setting.get("follow_threshold", 500000000)  # 5亿
        self.holding_days = setting.get("holding_days", 5)
```

#### 板块轮动策略

```python
from vnpy_china_strategy.sector_rotation import SectorRotationStrategy

class MySectorStrategy(SectorRotationStrategy):
    """板块轮动策略示例"""

    def __init__(self, strategy_engine, strategy_name, vt_symbol, setting):
        super().__init__(strategy_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.lookback_days = setting.get("lookback_days", 20)
        self.top_sector_count = setting.get("top_sector_count", 3)
```

### 6. 增强回测系统 (vnpy_china_backtest)

```python
from vnpy_china_backtest import (
    ChinaBacktestEngine,
    TradingCost,
    SlippageMode,
    T1RuleChecker
)

# 创建回测引擎
engine = ChinaBacktestEngine()

# 设置 A股交易成本
trading_cost = TradingCost(
    commission_rate=0.0003,    # 万3佣金
    min_commission=5.0,         # 最低5元
    stamp_duty=0.001,           # 印花税0.1%（仅卖出）
    transfer_fee=0.00001,       # 过户费0.001%
)
engine.set_trading_cost(trading_cost)

# 设置滑点模式
engine.set_slippage_mode(
    mode=SlippageMode.PERCENTAGE,  # 百分比滑点
    value=0.001                   # 0.1%
)

# 启用 T+1 规则检查
t1_checker = T1RuleChecker()
engine.set_rule_checker(t1_checker)

# 加载历史数据
from datetime import datetime
engine.set_data_start_date(datetime(2020, 1, 1))
engine.set_data_end_date(datetime(2024, 12, 31))
engine.load_data()

# 运行回测
engine.run_backtest()

# 获取回测报告
report = engine.get_report()
print(f"总收益率: {report.total_return:.2%}")
print(f"年化收益率: {report.annual_return:.2%}")
print(f"最大回撤: {report.max_drawdown:.2%}")
print(f"夏普比率: {report.sharpe_ratio:.2f}")
```

### 7. 资金管理 (vnpy_china_capital)

```python
from vnpy_china_capital import (
    PositionSizer,
    EqualWeightSizer,
    RiskParitySizer,
    SplitOrderExecutor
)

# 创建仓位管理器
position_sizer = PositionSizer()

# 等权重配置
symbols = ["000001.SZ", "000002.SZ", "600000.SH"]
total_capital = 100000  # 10万

allocations = position_sizer.equal_weight(
    symbols=symbols,
    total_capital=total_capital
)
print(f"等权重配置: {allocations}")

# 风险平价配置
volatilities = {
    "000001.SZ": 0.2,
    "000002.SZ": 0.25,
    "600000.SH": 0.18
}
allocations = position_sizer.risk_parity(
    symbols=symbols,
    total_capital=total_capital,
    volatilities=volatilities
)
print(f"风险平价配置: {allocations}")

# 分批交易执行器
executor = SplitOrderExecutor()
executor.set_split_method("equal", batch_count=5)
executor.execute_order(
    symbol="000001.SZ",
    direction="long",
    total_volume=1000
)
```

### 8. 行情数据分析 (vnpy_china_analysis)

```python
from vnpy_china_analysis import (
    MoneyFlowAnalyzer,
    MainForceAnalyzer,
    OrderQueueAnalyzer,
    AuctionAnalyzer
)

# 资金流向分析
money_flow_analyzer = MoneyFlowAnalyzer()

# 分析资金流向
money_flow = money_flow_analyzer.analyze(
    symbol="000001.SZ",
    start_time=datetime.now() - timedelta(hours=1)
)
print(f"超大单净流入: {money_flow.super_large_inflow}")
print(f"大单净流入: {money_flow.large_inflow}")
print(f"主力净流入: {money_flow.main_net_inflow}")

# 主力动向分析
main_force_analyzer = MainForceAnalyzer()
main_force = main_force_analyzer.analyze(
    symbol="000001.SZ",
    window=60  # 60分钟窗口
)
print(f"主力买入: {main_force.buy_volume}")
print(f"主力卖出: {main_force.sell_volume}")
print(f"主力强度: {main_force.strength:.2f}")
```

### 9. 数据分析报表 (vnpy_china_reporting)

```python
from vnpy_china_reporting import (
    TradingReportGenerator,
    ReportExporter
)

# 生成每日交易报告
report_generator = TradingReportGenerator()

# 设置报告日期
report_date = datetime.now().date()
daily_report = report_generator.generate_daily_report(report_date)

# 导出为 Excel
exporter = ReportExporter()
exporter.export_to_excel(daily_report, "reports/daily_report_20250225.xlsx")

# 导出为 PDF
exporter.export_to_pdf(daily_report, "reports/daily_report_20250225.pdf")

# 生成策略分析报告
strategy_report = report_generator.generate_strategy_report(
    strategy_name="my_strategy",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

### 10. 策略参数优化 (vnpy_china_optimize)

```python
from vnpy_china_optimize import (
    OptimizationManager,
    GridSearchOptimizer,
    GeneticOptimizer,
    BayesianOptimizer
)

# 创建优化管理器
opt_manager = OptimizationManager()

# 网格搜索优化
grid_optimizer = GridSearchOptimizer()
grid_optimizer.set_parameter_space({
    "fast_window": [5, 10, 15, 20],
    "slow_window": [30, 60, 90],
    "threshold": [0.02, 0.03, 0.05]
})

best_result = grid_optimizer.optimize(
    strategy_class=MyStrategy,
    vt_symbol="000001.SZ",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)
print(f"最优参数: {best_result.best_params}")
print(f"最优收益: {best_result.best_return:.2%}")

# 贝叶斯优化
bayesian_optimizer = BayesianOptimizer()
bayesian_optimizer.set_parameter_space({
    "entry_threshold": (0.01, 0.1),      # 连续参数
    "exit_threshold": (0.01, 0.1),
    "position_ratio": [0.1, 0.2, 0.3]     # 离散参数
})

best_result = bayesian_optimizer.optimize(
    strategy_class=MyStrategy,
    vt_symbol="000001.SZ",
    n_calls=50
)
```

### 11. 机器学习策略 (vnpy_china_ml)

```python
from vnpy_china_ml import (
    ChinaAlphaDataset,
    MLStrategyManager,
    LightGBMModel,
    ModelEvaluator
)

# 创建 A股特征数据集
dataset = ChinaAlphaDataset()

# 加载特征数据
dataset.load_data(
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2024, 12, 31),
    feature_types=["technical", "fundamental", "market"]
)

# 划分训练集和测试集
train_data, test_data = dataset.split(test_ratio=0.2)

# 创建 LightGBM 模型
model = LightGBMModel(
    params={
        "objective": "regression",
        "metric": "rmse",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9
    }
)

# 训练模型
model.fit(train_data)

# 模型评估
evaluator = ModelEvaluator()
metrics = evaluator.evaluate(model, test_data)

print(f"IC: {metrics['ic']:.4f}")
print(f"IR: {metrics['ir']:.4f}")
print(f"Rank IC: {metrics['rank_ic']:.4f}")

# 使用模型预测
predictions = model.predict(test_data)
```

### 12. 统一配置管理 (vnpy_china_config)

```python
from vnpy_china_config import (
    ConfigManager,
    Environment,
    GlobalConfig,
    DataModuleConfig
)

# 获取配置管理器单例
config_manager = ConfigManager()

# 设置运行环境
config_manager.set_environment(Environment.PRODUCTION)

# 设置配置文件路径
from pathlib import Path
config_manager.set_config_path(Path(".vntrader_china/config"))

# 加载全局配置
global_config = config_manager.load_global_config()
print(f"MySQL Host: {global_config.database.mysql_host}")
print(f"Log Level: {global_config.logging.level}")

# 加载模块配置
data_config = config_manager.load_module_config(
    "data",
    DataModuleConfig
)
print(f"Tushare Token: {data_config.tushare_token}")

# 更新配置
config_manager.update_config(
    "global",
    logging_level="DEBUG"
)

# 保存配置
config_manager.save_config("global")

# 热更新配置
config_manager.reload_config("global")
```

---

## 📖 API 参考

### 核心接口

#### TradingRulesEngine

```python
class TradingRulesEngine:
    """A股交易规则引擎"""

    def check_t1_sellable(self, symbol: str, volume: int) -> bool:
        """检查股票是否可卖（T+1规则）"""

    def get_sellable_volume(self, symbol: str) -> int:
        """获取可卖出数量"""

    def calculate_price_limit(self, symbol: str, prev_close: float) -> PriceLimit:
        """计算涨跌停价格"""

    def is_price_valid(self, symbol: str, price: float) -> bool:
        """判断价格是否有效"""

    def is_trading_time(self, dt: datetime = None) -> bool:
        """判断是否在交易时间"""

    def get_trading_phase(self, dt: datetime = None) -> str:
        """获取交易时段"""

    def round_lot_volume(self, volume: int) -> int:
        """将数量取整到交易单位"""
```

#### RiskManager

```python
class RiskManager:
    """风险管理器"""

    def check_position_limit(
        self,
        symbol: str,
        volume: int,
        price: float
    ) -> bool:
        """检查是否超过仓位限制"""

    def check_stop_loss(self, position: Position) -> bool:
        """检查止损条件"""

    def check_daily_loss(self) -> float:
        """获取单日亏损比例"""

    def stop_all_trading(self):
        """停止所有交易"""
```

#### DataService

```python
class DataService:
    """A股数据服务"""

    def get_all_stocks(self) -> List[StockInfo]:
        """获取所有A股列表"""

    def get_stock_info(self, symbol: str) -> StockInfo:
        """获取股票基本信息"""

    def get_bar_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[BarData]:
        """获取K线数据"""

    def get_tick_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[TickData]:
        """获取Tick数据"""

    def get_financial_data(self, symbol: str) -> FinancialData:
        """获取财务数据"""
```

---

## 🎯 策略开发指南

### 创建自定义策略

```python
from vnpy_china_strategy.base import ChinaStockStrategy
from vnpy.trader.object import TickData, BarData, OrderData, TradeData
from vnpy.trader.constant import Direction, OrderType, Status

class MyStrategy(ChinaStockStrategy):
    """自定义A股策略示例"""

    def __init__(self, strategy_engine, strategy_name, vt_symbol, setting):
        """初始化"""
        super().__init__(strategy_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.fast_window = setting.get("fast_window", 10)
        self.slow_window = setting.get("slow_window", 30)
        self.threshold = setting.get("threshold", 0.02)

        # 策略变量
        self.fast_ma = []
        self.slow_ma = []

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")

        # 加载历史数据
        bars = self.load_bar(100)
        for bar in bars:
            self.on_bar(bar)

    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        # Tick 处理逻辑
        pass

    def on_bar(self, bar: BarData):
        """K线数据回调"""
        # 计算移动平均线
        if len(self.fast_ma) < self.fast_window:
            self.fast_ma.append(bar.close_price)
            return

        self.fast_ma.append(bar.close_price)
        if len(self.fast_ma) > self.fast_window:
            self.fast_ma.pop(0)

        if len(self.slow_ma) < self.slow_window:
            self.slow_ma.append(bar.close_price)
            return

        self.slow_ma.append(bar.close_price)
        if len(self.slow_ma) > self.slow_window:
            self.slow_ma.pop(0)

        # 计算指标
        fast_avg = sum(self.fast_ma) / len(self.fast_ma)
        slow_avg = sum(self.slow_ma) / len(self.slow_ma)

        # 交易逻辑
        if fast_avg > slow_avg * (1 + self.threshold):
            # 金叉买入
            if self.pos == 0:
                self.buy(bar.close_price, 100)

        elif fast_avg < slow_avg * (1 - self.threshold):
            # 死叉卖出
            if self.pos > 0:
                self.sell(bar.close_price, self.pos)

    def buy(self, price: float, volume: int):
        """买入"""
        # 检查交易规则
        if not self.check_trading_rules(self.vt_symbol, volume, "buy"):
            return

        # 创建委托
        order = OrderData(
            symbol=self.vt_symbol,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=volume,
            price=price,
            reference=self.vt_symbol
        )

        # 发送委托
        self.send_order(order)

    def sell(self, price: float, volume: int):
        """卖出"""
        # 检查交易规则
        if not self.check_trading_rules(self.vt_symbol, volume, "sell"):
            return

        # 创建委托
        order = OrderData(
            symbol=self.vt_symbol,
            direction=Direction.SHORT,
            type=OrderType.LIMIT,
            volume=volume,
            price=price,
            reference=self.vt_symbol
        )

        # 发送委托
        self.send_order(order)
```

### 策略配置示例

```python
# 策略配置
strategy_setting = {
    "fast_window": 10,
    "slow_window": 30,
    "threshold": 0.02
}

# 添加策略
engine.add_strategy(
    strategy_name="my_strategy",
    vt_symbol="000001.SZ",
    strategy_class=MyStrategy,
    setting=strategy_setting
)
```

---

## ❓ 常见问题

### Q1: 如何处理 T+1 规则？

A: 使用 `TradingRulesEngine` 自动处理：

```python
from vnpy_china_rules import TradingRulesEngine

rules_engine = TradingRulesEngine()
# 自动检查 T+1 规则
if rules_engine.check_t1_sellable(symbol, volume):
    # 执行卖出
    pass
```

### Q2: 如何设置止损止盈？

A: 使用风控模块：

```python
from vnpy_china_rules.risk import StopOrder

# 设置止损止盈
stop_order = StopOrder(
    symbol="000001.SZ",
    long_stop_loss=9.5,      # 多头止损价
    long_take_profit=11.0,    # 多头止盈价
    trailing_stop=0.5         # 移动止损幅度
)

risk_manager.set_stop_order(stop_order)
```

### Q3: 如何获取历史数据？

A: 使用数据服务：

```python
from vnpy_china_data import DataService
from datetime import datetime, timedelta

data_service = DataService()
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

bars = data_service.get_bar_data(
    symbol="000001.SZ",
    start_date=start_date,
    end_date=end_date,
    interval="1d"
)
```

### Q4: 如何生成回测报告？

A: 使用回测引擎：

```python
from vnpy_china_backtest import ChinaBacktestEngine

engine = ChinaBacktestEngine()
engine.set_data_start_date(datetime(2023, 1, 1))
engine.set_data_end_date(datetime(2024, 12, 31))
engine.load_data()
engine.run_backtest()

report = engine.get_report()
report.to_excel("backtest_report.xlsx")
```

---

## 🏆 最佳实践

### 1. 风控优先

```python
# 1. 设置仓位限制
risk_manager.set_position_limit(PositionLimit(...))

# 2. 设置止损止盈
risk_manager.set_stop_order(...)

# 3. 设置交易限制
risk_manager.set_trading_limit(...)

# 4. 实时监控
risk_manager.start_monitoring()
```

### 2. 数据验证

```python
# 验证数据完整性
def validate_data(bars):
    if len(bars) == 0:
        raise ValueError("数据为空")

    # 检查缺失值
    for bar in bars:
        if bar.open_price <= 0 or bar.close_price <= 0:
            raise ValueError(f"价格异常: {bar}")
```

### 3. 异常处理

```python
try:
    # 交易逻辑
    order = self.send_order(...)
except Exception as e:
    self.write_log(f"交易异常: {e}")
    # 发送告警
    monitor_manager.send_alert(f"交易异常: {e}", level="ERROR")
```

### 4. 日志记录

```python
# 记录关键操作
self.write_log(f"买入信号: {self.vt_symbol} @ {price}")
self.write_log(f"持仓变化: {self.pos} → {self.pos + volume}")
self.write_log(f"委托状态: {order.status}")
```

---

**文档版本**：v1.0
**创建日期**：2026-02-25
**维护者**：AI Assistant
