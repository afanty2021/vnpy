# 数据分析报表设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-009
> 优先级：P1
> 预计工时：4人天

---

## 1. 设计目标

构建A股数据分析报表模块：

1. **交易报表**：每日、月度、年度交易报告
2. **持仓分析**：分布、行业、盈亏分析
3. **策略分析**：收益、归因、对比分析

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       报表系统架构                                 │
├─────────────────────────────────────────────────────────────────┤
│  【报表生成】                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │DailyReport   │  │MonthlyReport │  │YearlyReport │        │
│  │(日报)        │  │(月报)        │  │(年报)        │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【分析模块】                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │PositionAnalysis│  │IndustryAnalysis│ │RiskAnalysis │        │
│  │(持仓分析)    │  │(行业分析)   │  │(风险分析)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【导出模块】                                                   │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │ExcelExporter │  │ PDFExporter  │                          │
│  │(Excel导出)   │  │(PDF导出)     │                          │
│  └──────────────┘  └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_reporting/
├── __init__.py
├── report/
│   ├── __init__.py
│   ├── base.py             # 报表基类
│   ├── daily.py            # 日报
│   ├── monthly.py          # 月报
│   └── yearly.py           # 年报
├── analysis/
│   ├── __init__.py
│   ├── position.py        # 持仓分析
│   ├── industry.py        # 行业分析
│   └── risk.py           # 风险分析
├── export/
│   ├── __init__.py
│   ├── excel.py          # Excel导出
│   └── pdf.py            # PDF导出
└── templates/
    └── report_template.html  # HTML模板
```

---

## 3. 核心类设计

### 3.1 报表数据模型

```python
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict


@dataclass
class TradeRecord:
    """交易记录"""
    datetime: datetime
    symbol: str
    name: str
    direction: str
    price: float
    volume: int
    amount: float
    commission: float


@dataclass
class PositionRecord:
    """持仓记录"""
    symbol: str
    name: str
    volume: int
    cost: float
    current_price: float
    market_value: float
    pnl: float
    pnl_ratio: float
    weight: float  # 仓位权重


@dataclass
class DailyReport:
    """每日交易报告"""
    date: date

    # 资金情况
    start_balance: float
    end_balance: float
    daily_pnl: float
    daily_return: float

    # 交易情况
    total_trades: int
    buy_trades: int
    sell_trades: int
    total_amount: float
    total_commission: float

    # 持仓情况
    positions: List[PositionRecord] = field(default_factory=list)
    total_market_value: float = 0.0

    # 风险指标
    position_ratio: float = 0.0
    daily_drawdown: float = 0.0
```

### 3.2 日报生成器

```python
class DailyReportGenerator:
    """日报生成器"""

    def __init__(self, main_engine):
        self.main_engine = main_engine

    def generate(self, report_date: date) -> DailyReport:
        """生成日报"""

        # 获取当日交易记录
        trades = self.get_trades(report_date)

        # 获取账户资金
        account = self.main_engine.get_account()

        # 获取持仓
        positions = self.get_positions()

        # 计算指标
        daily_pnl = account.balance - account.pre_balance
        daily_return = daily_pnl / account.pre_balance if account.pre_balance > 0 else 0

        return DailyReport(
            date=report_date,
            start_balance=account.pre_balance,
            end_balance=account.balance,
            daily_pnl=daily_pnl,
            daily_return=daily_return,
            total_trades=len(trades),
            buy_trades=len([t for t in trades if t.direction == "buy"]),
            sell_trades=len([t for t in trades if t.direction == "sell"]),
            total_amount=sum(t.amount for t in trades),
            total_commission=sum(t.commission for t in trades),
            positions=positions,
            total_market_value=sum(p.market_value for p in positions),
            position_ratio=sum(p.market_value for p in positions) / account.balance
        )

    def get_trades(self, report_date: date) -> List[TradeRecord]:
        """获取指定日期的交易记录"""
        # 从数据库或事件中获取
        pass

    def get_positions(self) -> List[PositionRecord]:
        """获取当前持仓"""
        pass
```

### 3.3 持仓分析

```python
class PositionAnalyzer:
    """持仓分析器"""

    def analyze_distribution(self, positions: List[PositionRecord]) -> Dict:
        """分析持仓分布"""

        # 按市值分布
        total_value = sum(p.market_value for p in positions)
        large = sum(p.market_value for p in positions if p.market_value > 100000)
        medium = sum(p.market_value for p in positions if 30000 <= p.market_value <= 100000)
        small = sum(p.market_value for p in positions if p.market_value < 30000)

        return {
            "total_positions": len(positions),
            "total_market_value": total_value,
            "large_position_ratio": large / total_value if total_value > 0 else 0,
            "medium_position_ratio": medium / total_value if total_value > 0 else 0,
            "small_position_ratio": small / total_value if total_value > 0 else 0,
        }

    def analyze_industry(self, positions: List[PositionRecord]) -> Dict:
        """分析行业分布"""

        # 按行业分组
        industry_data = {}
        for pos in positions:
            industry = self.get_stock_industry(pos.symbol)
            if industry not in industry_data:
                industry_data[industry] = []
            industry_data[industry].append(pos)

        # 计算各行业占比
        total_value = sum(p.market_value for p in positions)
        industry_ratio = {}
        for industry, pos_list in industry_data.items():
            value = sum(p.market_value for p in pos_list)
            industry_ratio[industry] = {
                "value": value,
                "ratio": value / total_value if total_value > 0 else 0,
                "count": len(pos_list),
                "avg_pnl": sum(p.pnl for p in pos_list) / len(pos_list) if pos_list else 0
            }

        return industry_ratio

    def analyze_pnl(self, positions: List[PositionRecord]) -> Dict:
        """分析盈亏分布"""

        profitable = [p for p in positions if p.pnl > 0]
        loss = [p for p in positions if p.pnl < 0]

        return {
            "profitable_count": len(profitable),
            "loss_count": len(loss),
            "total_pnl": sum(p.pnl for p in positions),
            "avg_pnl": sum(p.pnl for p in positions) / len(positions) if positions else 0,
            "best_pnl": max((p.pnl for p in positions), default=0),
            "worst_pnl": min((p.pnl for p in positions), default=0),
        }
```

### 3.4 风险分析

```python
class RiskAnalyzer:
    """风险分析器"""

    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """计算VaR（Value at Risk）"""
        import numpy as np
        if not returns:
            return 0
        return np.percentile(returns, (1 - confidence) * 100)

    def calculate_volatility(self, returns: List[float]) -> float:
        """计算波动率"""
        import numpy as np
        if not returns:
            return 0
        return np.std(returns) * np.sqrt(252)  # 年化波动率

    def analyze_risk(self, positions: List[PositionRecord], history_returns: List[float]) -> Dict:
        """综合风险分析"""

        # 计算各持仓的波动率
        position_risks = []
        for pos in positions:
            vol = self.calculate_volatility(self.get_stock_returns(pos.symbol))
            position_risks.append({
                "symbol": pos.symbol,
                "volatility": vol,
                "var_95": self.calculate_var(self.get_stock_returns(pos.symbol)),
            })

        # 组合风险
        portfolio_vol = self.calculate_volatility(history_returns)
        portfolio_var = self.calculate_var(history_returns)

        return {
            "portfolio_volatility": portfolio_vol,
            "portfolio_var_95": portfolio_var,
            "position_risks": position_risks,
        }
```

### 3.5 Excel导出

```python
class ExcelExporter:
    """Excel导出器"""

    def export_daily_report(self, report: DailyReport, filepath: str):
        """导出日报到Excel"""
        import openpyxl
        from openpyxl.styles import Font, Alignment

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "日报"

        # 标题
        ws['A1'] = f"每日交易报告 - {report.date}"
        ws['A1'].font = Font(size=14, bold=True)

        # 资金情况
        ws['A3'] = "资金情况"
        ws['A4'] = "期初余额"
        ws['B4'] = report.start_balance
        ws['A5'] = "期末余额"
        ws['B5'] = report.end_balance
        ws['A6'] = "当日盈亏"
        ws['B6'] = report.daily_pnl

        # 交易情况
        ws['A8'] = "交易情况"
        ws['A9'] = "总交易次数"
        ws['B9'] = report.total_trades

        # 持仓情况
        ws['A11'] = "持仓明细"
        headers = ["代码", "名称", "数量", "成本", "现价", "市值", "盈亏", "盈亏比"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=11, column=col, value=header)

        for row, pos in enumerate(report.positions, 12):
            ws.cell(row=row, column=1, value=pos.symbol)
            ws.cell(row=row, column=2, value=pos.name)
            ws.cell(row=row, column=3, value=pos.volume)
            ws.cell(row=row, column=4, value=pos.cost)
            ws.cell(row=row, column=5, value=pos.current_price)
            ws.cell(row=row, column=6, value=pos.market_value)
            ws.cell(row=row, column=7, value=pos.pnl)
            ws.cell(row=row, column=8, value=pos.pnl_ratio)

        wb.save(filepath)

    def export_monthly_report(self, reports: List[DailyReport], filepath: str):
        """导出月报"""
        pass
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构 | 0.5人天 |
| 2 | 实现报表数据模型 | 0.5人天 |
| 3 | 实现日报生成器 | 1人天 |
| 4 | 实现持仓和风险分析 | 1人天 |
| 5 | 实现Excel/PDF导出 | 1人天 |
| 合计 | | **4人天** |

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
