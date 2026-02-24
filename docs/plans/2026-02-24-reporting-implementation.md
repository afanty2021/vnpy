# 数据分析报表系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-009
> 优先级：P1
> 预计工时：4人天
> 实施周期：1周

---

## 1. 方案概述

### 1.1 项目背景

量化交易系统需要完善的报表功能来展示交易结果、分析持仓状况、评估策略表现。本方案旨在为VeighNa A股交易系统构建专业的数据分析报表能力，支持Excel和PDF格式的报告导出。

### 1.2 实施目标

| 目标类别 | 具体目标 | 成功标准 |
|---------|---------|---------|
| 报表生成 | 支持日报、月报、年报 | 自动生成，数据准确 |
| 分析功能 | 持仓分析、行业分析、风险分析 | 分析维度全面 |
| 导出功能 | Excel、PDF格式导出 | 格式美观、数据完整 |
| 可视化 | 图表展示 | 图表清晰 |

### 1.3 交付物清单

| 序号 | 交付物 | 类型 | 说明 |
|------|--------|------|------|
| 1 | vnpy_china_reporting模块 | 代码 | 报表核心模块 |
| 2 | 单元测试 | 代码 | pytest测试套件 |
| 3 | 报表模板 | 文件 | Excel/PDF模板 |
| 4 | 使用示例 | 代码 | 示例脚本 |
| 5 | API文档 | 文档 | 接口说明文档 |
| 6 | 实施报告 | 文档 | 开发过程总结 |

---

## 2. 技术架构设计

### 2.1 模块结构

```
vnpy_china_reporting/
├── __init__.py                     # 模块入口
├── core/                           # 核心数据模型
│   ├── __init__.py
│   ├── models.py                   # 数据类定义
│   └── enums.py                    # 枚举类型
├── report/                         # 报表生成
│   ├── __init__.py
│   ├── base.py                     # 报表基类
│   ├── daily.py                    # 日报生成器
│   ├── monthly.py                  # 月报生成器
│   └── yearly.py                   # 年报生成器
├── analysis/                       # 分析模块
│   ├── __init__.py
│   ├── position.py                 # 持仓分析
│   ├── industry.py                 # 行业分析
│   ├── risk.py                     # 风险分析
│   └── strategy.py                 # 策略分析
├── export/                         # 导出模块
│   ├── __init__.py
│   ├── excel.py                    # Excel导出
│   ├── pdf.py                      # PDF导出
│   └── charts.py                   # 图表生成
├── templates/                      # 模板文件
│   ├── excel/
│   │   ├── daily_template.xlsx     # 日报模板
│   │   └── monthly_template.xlsx   # 月报模板
│   └── pdf/
│       └── report_style.css        # PDF样式
└── utils/                          # 工具函数
    ├── __init__.py
    ├── calculator.py               # 计算工具
    └── formatter.py                # 格式化工具
```

### 2.2 类图设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      BaseReportGenerator                        │
│                        (报表基类)                               │
├─────────────────────────────────────────────────────────────────┤
│ -main_engine: MainEngine                                       │
│ -data_cache: Dict                                              │
├─────────────────────────────────────────────────────────────────┤
│ +generate(date) -> ReportData                                  │
│ +get_trades(date) -> List[TradeRecord]                         │
│ +get_positions() -> List[PositionRecord]                       │
│ +get_account() -> AccountData                                   │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────────────┐   ┌──────────────────┐   ┌─────────────────┐
│DailyReport    │   │MonthlyReport     │   │YearlyReport     │
│Generator      │   │Generator         │   │Generator        │
├───────────────┤   ├──────────────────┤   ├─────────────────┤
│+generate()    │   │+generate()       │   │+generate()       │
└───────────────┘   └──────────────────┘   └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     PositionAnalyzer                            │
│                    (持仓分析器)                                 │
├─────────────────────────────────────────────────────────────────┤
│ +analyze_distribution(positions) -> Dict                       │
│ +analyze_industry(positions) -> Dict                           │
│ +analyze_pnl(positions) -> Dict                                │
│ +get_concentration(positions) -> Dict                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      RiskAnalyzer                               │
│                     (风险分析器)                                │
├─────────────────────────────────────────────────────────────────┤
│ +calculate_var(returns, confidence) -> float                   │
│ +calculate_volatility(returns) -> float                        │
│ +calculate_sharpe(returns, rf) -> float                        │
│ +calculate_max_drawdown(equity_curve) -> float                 │
│ +analyze_risk(positions, returns) -> Dict                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ExcelExporter                               │
│                    (Excel导出器)                                │
├─────────────────────────────────────────────────────────────────┤
│ +export_daily_report(report, filepath) -> None                 │
│ +export_monthly_report(report, filepath) -> None               │
│ +export_position_analysis(analysis, filepath) -> None          │
│ +apply_styles(worksheet) -> None                               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 数据流设计

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  数据源层     │ ──>  │  报表生成层   │ ──>  │  分析计算层   │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ • MainEngine │      │ • 日报生成    │      │ • 持仓分析    │
│ • Database   │      │ • 月报生成    │      │ • 风险分析    │
│ • Cache      │      │ • 年报生成    │      │ • 策略分析    │
└──────────────┘      └──────────────┘      └──────────────┘
                                                     │
                                                     v
                                              ┌──────────────┐
                                              │  导出层      │
                                              ├──────────────┤
                                              │ • Excel导出  │
                                              │ • PDF导出    │
                                              │ • 图表生成   │
                                              └──────────────┘
```

---

## 3. 详细实施计划

### 3.1 第一阶段：基础框架搭建（1人天）

#### 任务1.1：创建目录结构

```bash
# 创建模块根目录
mkdir -p vnpy_china_reporting

# 创建子目录
mkdir -p vnpy_china_reporting/core
mkdir -p vnpy_china_reporting/report
mkdir -p vnpy_china_reporting/analysis
mkdir -p vnpy_china_reporting/export
mkdir -p vnpy_china_reporting/templates/excel
mkdir -p vnpy_china_reporting/templates/pdf
mkdir -p vnpy_china_reporting/utils

# 创建测试目录
mkdir -p tests/reporting

# 创建输出目录
mkdir -p reports/daily
mkdir -p reports/monthly
mkdir -p reports/yearly
```

**验收标准**：
- [ ] 所有目录创建完成
- [ ] 每个目录包含`__init__.py`文件

#### 任务1.2：定义核心数据模型

**文件位置**：`vnpy_china_reporting/core/models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional
from enum import Enum


class Direction(Enum):
    """交易方向"""
    BUY = "buy"
    SELL = "sell"


class ReportType(Enum):
    """报表类型"""
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class TradeRecord:
    """交易记录"""
    datetime: datetime
    symbol: str
    name: str
    direction: Direction
    price: float
    volume: int
    amount: float
    commission: float
    pnl: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.direction, str):
            self.direction = Direction(self.direction)


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
    weight: float = 0.0
    industry: str = ""
    sector: str = ""


@dataclass
class AccountData:
    """账户数据"""
    account_id: str
    balance: float
    pre_balance: float
    available: float
    frozen: float = 0.0
    position_value: float = 0.0
    leverage: float = 1.0


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
    position_ratio: float = 0.0

    # 风险指标
    daily_drawdown: float = 0.0
    max_drawdown: float = 0.0

    # 时间戳
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MonthlyReport:
    """月度交易报告"""
    year: int
    month: int

    # 收益情况
    start_balance: float
    end_balance: float
    monthly_pnl: float
    monthly_return: float

    # 交易统计
    total_trades: int
    total_commission: float

    # 日收益序列
    daily_returns: List[float] = field(default_factory=list)

    # 风险指标
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0

    # 持仓统计
    avg_positions: float = 0.0
    max_positions: int = 0


@dataclass
class YearlyReport:
    """年度交易报告"""
    year: int

    # 收益情况
    start_balance: float
    end_balance: float
    yearly_pnl: float
    yearly_return: float

    # 月度收益
    monthly_returns: Dict[str, float] = field(default_factory=dict)

    # 统计指标
    total_trades: int
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_loss_ratio: float = 0.0

    # 风险指标
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0


@dataclass
class PositionAnalysis:
    """持仓分析结果"""
    # 分布分析
    total_positions: int
    total_market_value: float
    large_position_ratio: float  # 大市值持仓占比
    medium_position_ratio: float
    small_position_ratio: float

    # 行业分布
    industry_distribution: Dict[str, Dict]

    # 盈亏分布
    profitable_count: int
    loss_count: int
    total_pnl: float
    best_pnl: float
    worst_pnl: float

    # 集中度
    concentration_ratio: float  # 前十大持仓占比
    herfindahl_index: float     # 赫芬达尔指数


@dataclass
class RiskAnalysis:
    """风险分析结果"""
    # 组合风险
    portfolio_volatility: float
    portfolio_var_95: float
    portfolio_var_99: float
    max_drawdown: float
    current_drawdown: float

    # 收益指标
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # 个股风险
    position_risks: List[Dict]
```

**验收标准**：
- [ ] 所有数据类定义完整
- [ ] 通过MyPy类型检查
- [ ] 包含完整的文档字符串

#### 任务1.3：创建报表基类

**文件位置**：`vnpy_china_reporting/report/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import date, datetime
from ..core.models import (
    TradeRecord,
    PositionRecord,
    AccountData,
    DailyReport
)


class BaseReportGenerator(ABC):
    """
    报表生成器基类

    所有报表生成器应继承此类，实现统一的接口。
    """

    def __init__(self, main_engine=None) -> None:
        """
        构造函数

        Args:
            main_engine: VeighNa主引擎实例
        """
        self.main_engine = main_engine
        self.data_cache: Dict[str, List] = {}

    @abstractmethod
    def generate(self, report_date: date) -> Dict:
        """
        生成报表

        Args:
            report_date: 报表日期

        Returns:
            报表数据字典
        """
        pass

    def get_account(self) -> Optional[AccountData]:
        """
        获取账户数据

        Returns:
            AccountData对象
        """
        if not self.main_engine:
            return None

        try:
            account = self.main_engine.get_account()
            return AccountData(
                account_id=account.accountid,
                balance=account.balance,
                pre_balance=account.pre_balance,
                available=account.available,
                frozen=getattr(account, 'frozen', 0.0),
                position_value=getattr(account, 'position_value', 0.0)
            )
        except Exception as e:
            print(f"获取账户数据失败: {e}")
            return None

    def get_trades(self, report_date: date) -> List[TradeRecord]:
        """
        获取指定日期的交易记录

        Args:
            report_date: 报表日期

        Returns:
            TradeRecord列表
        """
        if not self.main_engine:
            return []

        try:
            trades = self.main_engine.get_trades()
            trade_records = []

            for trade in trades:
                # 筛选指定日期的交易
                if trade.datetime.date() == report_date:
                    trade_records.append(TradeRecord(
                        datetime=trade.datetime,
                        symbol=trade.symbol,
                        name=getattr(trade, 'name', ''),
                        direction=trade.direction.value,
                        price=trade.price,
                        volume=trade.volume,
                        amount=trade.volume * trade.price,
                        commission=getattr(trade, 'commission', 0.0)
                    ))

            return trade_records
        except Exception as e:
            print(f"获取交易记录失败: {e}")
            return []

    def get_positions(self) -> List[PositionRecord]:
        """
        获取当前持仓

        Returns:
            PositionRecord列表
        """
        if not self.main_engine:
            return []

        try:
            positions = self.main_engine.get_positions()
            position_records = []

            for pos in positions:
                if pos.volume == 0:
                    continue

                market_value = pos.volume * pos.price
                pnl = (pos.price - pos.avg_price) * pos.volume
                pnl_ratio = (pnl / (pos.avg_price * pos.volume)
                            if pos.avg_price > 0 else 0.0)

                position_records.append(PositionRecord(
                    symbol=pos.symbol,
                    name=getattr(pos, 'name', ''),
                    volume=pos.volume,
                    cost=pos.avg_price,
                    current_price=pos.price,
                    market_value=market_value,
                    pnl=pnl,
                    pnl_ratio=pnl_ratio
                ))

            return position_records
        except Exception as e:
            print(f"获取持仓失败: {e}")
            return []

    def calculate_position_weights(
        self,
        positions: List[PositionRecord],
        total_value: float
    ) -> None:
        """
        计算持仓权重

        Args:
            positions: 持仓列表
            total_value: 总市值
        """
        if total_value == 0:
            return

        for pos in positions:
            pos.weight = pos.market_value / total_value
```

**验收标准**：
- [ ] 基类接口完整
- [ ] 数据获取方法可用
- [ ] 工具方法实现正确

---

### 3.2 第二阶段：报表生成器实现（1人天）

#### 任务2.1：日报生成器

**文件位置**：`vnpy_china_reporting/report/daily.py`

```python
from typing import List
from datetime import date, datetime
from .base import BaseReportGenerator
from ..core.models import DailyReport, AccountData


class DailyReportGenerator(BaseReportGenerator):
    """
    日报生成器

    生成每日交易报告，包含资金情况、交易统计、持仓明细等。
    """

    def generate(self, report_date: date) -> DailyReport:
        """
        生成日报

        Args:
            report_date: 报表日期

        Returns:
            DailyReport对象
        """
        # 获取账户数据
        account = self.get_account()

        if account is None:
            # 返回空报表
            return DailyReport(
                date=report_date,
                start_balance=0.0,
                end_balance=0.0,
                daily_pnl=0.0,
                daily_return=0.0,
                total_trades=0,
                buy_trades=0,
                sell_trades=0,
                total_amount=0.0,
                total_commission=0.0
            )

        # 获取交易记录
        trades = self.get_trades(report_date)

        # 获取持仓
        positions = self.get_positions()

        # 计算资金情况
        start_balance = account.pre_balance
        end_balance = account.balance
        daily_pnl = end_balance - start_balance
        daily_return = daily_pnl / start_balance if start_balance > 0 else 0.0

        # 统计交易情况
        buy_trades = len([t for t in trades if t.direction.value == "buy"])
        sell_trades = len([t for t in trades if t.direction.value == "sell"])
        total_amount = sum(t.amount for t in trades)
        total_commission = sum(t.commission for t in trades)

        # 计算持仓市值和仓位比例
        total_market_value = sum(p.market_value for p in positions)
        position_ratio = total_market_value / end_balance if end_balance > 0 else 0.0

        # 计算持仓权重
        self.calculate_position_weights(positions, total_market_value)

        return DailyReport(
            date=report_date,
            start_balance=start_balance,
            end_balance=end_balance,
            daily_pnl=daily_pnl,
            daily_return=daily_return,
            total_trades=len(trades),
            buy_trades=buy_trades,
            sell_trades=sell_trades,
            total_amount=total_amount,
            total_commission=total_commission,
            positions=positions,
            total_market_value=total_market_value,
            position_ratio=position_ratio
        )

    def get_trades_detail(
        self,
        report_date: date
    ) -> List[dict]:
        """
        获取交易明细

        Returns:
            交易明细列表
        """
        trades = self.get_trades(report_date)

        return [
            {
                "时间": t.datetime.strftime("%H:%M:%S"),
                "代码": t.symbol,
                "名称": t.name,
                "方向": "买入" if t.direction.value == "buy" else "卖出",
                "价格": f"{t.price:.2f}",
                "数量": t.volume,
                "金额": f"{t.amount:.2f}",
                "手续费": f"{t.commission:.2f}"
            }
            for t in trades
        ]

    def get_summary(self, report: DailyReport) -> dict:
        """
        获取日报摘要

        Args:
            report: 日报对象

        Returns:
            摘要字典
        """
        return {
            "报表日期": report.date.strftime("%Y-%m-%d"),
            "期初余额": f"{report.start_balance:.2f}",
            "期末余额": f"{report.end_balance:.2f}",
            "当日盈亏": f"{report.daily_pnl:.2f}",
            "收益率": f"{report.daily_return:.2%}",
            "交易次数": report.total_trades,
            "买入次数": report.buy_trades,
            "卖出次数": report.sell_trades,
            "成交金额": f"{report.total_amount:.2f}",
            "手续费": f"{report.total_commission:.2f}",
            "持仓市值": f"{report.total_market_value:.2f}",
            "仓位比例": f"{report.position_ratio:.2%}",
            "持仓数量": len(report.positions)
        }
```

**测试用例**：
```python
import pytest
from datetime import date
from vnpy_china_reporting.report.daily import DailyReportGenerator


def test_daily_report_generation():
    """测试日报生成"""
    generator = DailyReportGenerator()

    report = generator.generate(date.today())

    assert report.date == date.today()
    assert report.total_trades >= 0
    assert len(report.positions) >= 0
    assert report.position_ratio >= 0
    assert report.position_ratio <= 1


def test_daily_report_summary():
    """测试日报摘要"""
    generator = DailyReportGenerator()
    report = generator.generate(date.today())

    summary = generator.get_summary(report)

    assert "报表日期" in summary
    assert "期初余额" in summary
    assert "当日盈亏" in summary
```

#### 任务2.2：月报生成器

**文件位置**：`vnpy_china_reporting/report/monthly.py`

```python
from typing import List, Dict
from datetime import date, datetime, timedelta
from calendar import monthrange
from .base import BaseReportGenerator
from .daily import DailyReportGenerator
from ..core.models import MonthlyReport
from ..utils.calculator import calculate_returns, calculate_max_drawdown


class MonthlyReportGenerator(BaseReportGenerator):
    """
    月报生成器

    汇总每日数据，生成月度交易报告。
    """

    def __init__(self, main_engine=None) -> None:
        super().__init__(main_engine)
        self.daily_generator = DailyReportGenerator(main_engine)

    def generate(self, report_date: date) -> MonthlyReport:
        """
        生成月报

        Args:
            report_date: 报表日期（取月份）

        Returns:
            MonthlyReport对象
        """
        year = report_date.year
        month = report_date.month

        # 获取月份的所有交易日
        trading_days = self._get_trading_days(year, month)

        if not trading_days:
            return self._empty_report(year, month)

        # 生成所有日报
        daily_reports = []
        for day in trading_days:
            report = self.daily_generator.generate(day)
            daily_reports.append(report)

        # 汇总数据
        first_report = daily_reports[0]
        last_report = daily_reports[-1]

        start_balance = first_report.start_balance
        end_balance = last_report.end_balance
        monthly_pnl = end_balance - start_balance
        monthly_return = monthly_pnl / start_balance if start_balance > 0 else 0.0

        # 统计交易
        total_trades = sum(r.total_trades for r in daily_reports)
        total_commission = sum(r.total_commission for r in daily_reports)

        # 日收益序列
        daily_returns = [r.daily_return for r in daily_reports]

        # 风险指标
        max_drawdown = calculate_max_drawdown(daily_returns)
        volatility = self._calculate_volatility(daily_returns)
        sharpe_ratio = self._calculate_sharpe(daily_returns)

        # 持仓统计
        position_counts = [len(r.positions) for r in daily_reports]
        avg_positions = sum(position_counts) / len(position_counts) if position_counts else 0
        max_positions = max(position_counts) if position_counts else 0

        return MonthlyReport(
            year=year,
            month=month,
            start_balance=start_balance,
            end_balance=end_balance,
            monthly_pnl=monthly_pnl,
            monthly_return=monthly_return,
            total_trades=total_trades,
            total_commission=total_commission,
            daily_returns=daily_returns,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            avg_positions=avg_positions,
            max_positions=max_positions
        )

    def _get_trading_days(self, year: int, month: int) -> List[date]:
        """获取月份的交易日"""
        # TODO: 从数据库或配置获取交易日历
        # 这里简单返回所有工作日
        days_in_month = monthrange(year, month)[1]
        trading_days = []

        for day in range(1, days_in_month + 1):
            dt = date(year, month, day)
            # 排除周末
            if dt.weekday() < 5:  # 0-4是周一到周五
                trading_days.append(dt)

        return trading_days

    def _calculate_volatility(self, returns: List[float]) -> float:
        """计算波动率"""
        if not returns:
            return 0.0

        import numpy as np
        return float(np.std(returns) * (252 ** 0.5))  # 年化

    def _calculate_sharpe(
        self,
        returns: List[float],
        risk_free_rate: float = 0.03
    ) -> float:
        """计算夏普比率"""
        if not returns:
            return 0.0

        avg_return = sum(returns) / len(returns)
        volatility = self._calculate_volatility(returns)

        if volatility == 0:
            return 0.0

        # 年化
        annual_return = avg_return * 252
        sharpe = (annual_return - risk_free_rate) / volatility
        return sharpe

    def _empty_report(self, year: int, month: int) -> MonthlyReport:
        """返回空报表"""
        return MonthlyReport(
            year=year,
            month=month,
            start_balance=0.0,
            end_balance=0.0,
            monthly_pnl=0.0,
            monthly_return=0.0,
            total_trades=0,
            total_commission=0.0
        )

    def get_monthly_summary(self, report: MonthlyReport) -> Dict:
        """获取月报摘要"""
        return {
            "报表月份": f"{report.year}年{report.month:02d}月",
            "期初余额": f"{report.start_balance:.2f}",
            "期末余额": f"{report.end_balance:.2f}",
            "月度盈亏": f"{report.monthly_pnl:.2f}",
            "月度收益率": f"{report.monthly_return:.2%}",
            "交易次数": report.total_trades,
            "手续费": f"{report.total_commission:.2f}",
            "最大回撤": f"{report.max_drawdown:.2%}",
            "波动率": f"{report.volatility:.2%}",
            "夏普比率": f"{report.sharpe_ratio:.2f}",
            "平均持仓数": f"{report.avg_positions:.1f}",
            "最大持仓数": report.max_positions
        }
```

#### 任务2.3：年报生成器

**文件位置**：`vnpy_china_reporting/report/yearly.py`

```python
from typing import List, Dict
from datetime import date
from .base import BaseReportGenerator
from .monthly import MonthlyReportGenerator
from ..core.models import YearlyReport


class YearlyReportGenerator(BaseReportGenerator):
    """
    年报生成器

    汇总12个月度数据，生成年度交易报告。
    """

    def __init__(self, main_engine=None) -> None:
        super().__init__(main_engine)
        self.monthly_generator = MonthlyReportGenerator(main_engine)

    def generate(self, report_date: date) -> YearlyReport:
        """
        生成年报

        Args:
            report_date: 报表日期（取年份）

        Returns:
            YearlyReport对象
        """
        year = report_date.year

        # 生成12个月报
        monthly_reports = []
        for month in range(1, 13):
            month_date = date(year, month, 1)
            report = self.monthly_generator.generate(month_date)
            monthly_reports.append(report)

        # 汇总数据
        first_month = monthly_reports[0]
        last_month = monthly_reports[-1]

        start_balance = first_month.start_balance
        end_balance = last_month.end_balance
        yearly_pnl = end_balance - start_balance
        yearly_return = yearly_pnl / start_balance if start_balance > 0 else 0.0

        # 月度收益
        monthly_returns = {}
        for i, report in enumerate(monthly_reports, 1):
            month_name = f"{report.year}年{report.month:02d}月"
            monthly_returns[month_name] = report.monthly_return

        # 统计指标
        total_trades = sum(r.total_trades for r in monthly_reports)

        # 计算胜率等指标（基于月度收益）
        positive_months = [r for r in monthly_reports if r.monthly_return > 0]
        win_rate = len(positive_months) / len(monthly_reports) if monthly_reports else 0

        avg_win = (
            sum(r.monthly_return for r in positive_months) / len(positive_months)
            if positive_months else 0
        )

        negative_months = [r for r in monthly_reports if r.monthly_return < 0]
        avg_loss = (
            sum(r.monthly_return for r in negative_months) / len(negative_months)
            if negative_months else 0
        )

        profit_loss_ratio = (
            abs(avg_win / avg_loss) if avg_loss != 0 else 0
        )

        # 风险指标
        max_drawdown = max(r.max_drawdown for r in monthly_reports)
        sharpe_ratio = sum(r.sharpe_ratio for r in monthly_reports) / len(monthly_reports)
        calmar_ratio = yearly_return / max_drawdown if max_drawdown != 0 else 0

        return YearlyReport(
            year=year,
            start_balance=start_balance,
            end_balance=end_balance,
            yearly_pnl=yearly_pnl,
            yearly_return=yearly_return,
            monthly_returns=monthly_returns,
            total_trades=total_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_loss_ratio=profit_loss_ratio,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio
        )

    def get_yearly_summary(self, report: YearlyReport) -> Dict:
        """获取年报摘要"""
        return {
            "报表年份": f"{report.year}年",
            "期初余额": f"{report.start_balance:.2f}",
            "期末余额": f"{report.end_balance:.2f}",
            "年度盈亏": f"{report.yearly_pnl:.2f}",
            "年度收益率": f"{report.yearly_return:.2%}",
            "交易次数": report.total_trades,
            "月度胜率": f"{report.win_rate:.2%}",
            "平均盈利": f"{report.avg_win:.2%}",
            "平均亏损": f"{report.avg_loss:.2%}",
            "盈亏比": f"{report.profit_loss_ratio:.2f}",
            "最大回撤": f"{report.max_drawdown:.2%}",
            "夏普比率": f"{report.sharpe_ratio:.2f}",
            "卡玛比率": f"{report.calmar_ratio:.2f}"
        }
```

**验收标准**：
- [ ] 日报生成器正常工作
- [ ] 月报生成器正确汇总
- [ ] 年报生成器数据完整
- [ ] 测试用例通过

---

### 3.3 第三阶段：分析模块实现（1人天）

#### 任务3.1：持仓分析器

**文件位置**：`vnpy_china_reporting/analysis/position.py`

```python
from typing import List, Dict
from collections import defaultdict
from ..core.models import PositionRecord, PositionAnalysis


class PositionAnalyzer:
    """
    持仓分析器

    分析持仓分布、行业分布、盈亏分布等。
    """

    def analyze(
        self,
        positions: List[PositionRecord]
    ) -> PositionAnalysis:
        """
        综合持仓分析

        Args:
            positions: 持仓列表

        Returns:
            PositionAnalysis对象
        """
        # 分布分析
        distribution = self.analyze_distribution(positions)

        # 行业分析
        industry_dist = self.analyze_industry(positions)

        # 盈亏分析
        pnl_analysis = self.analyze_pnl(positions)

        # 集中度分析
        concentration = self.analyze_concentration(positions)

        return PositionAnalysis(
            total_positions=distribution["total_positions"],
            total_market_value=distribution["total_market_value"],
            large_position_ratio=distribution["large_position_ratio"],
            medium_position_ratio=distribution["medium_position_ratio"],
            small_position_ratio=distribution["small_position_ratio"],
            industry_distribution=industry_dist,
            profitable_count=pnl_analysis["profitable_count"],
            loss_count=pnl_analysis["loss_count"],
            total_pnl=pnl_analysis["total_pnl"],
            best_pnl=pnl_analysis["best_pnl"],
            worst_pnl=pnl_analysis["worst_pnl"],
            concentration_ratio=concentration["ratio"],
            herfindahl_index=concentration["hhi"]
        )

    def analyze_distribution(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析持仓市值分布

        Args:
            positions: 持仓列表

        Returns:
            分布统计字典
        """
        if not positions:
            return {
                "total_positions": 0,
                "total_market_value": 0.0,
                "large_position_ratio": 0.0,
                "medium_position_ratio": 0.0,
                "small_position_ratio": 0.0
            }

        total_value = sum(p.market_value for p in positions)

        # 分类
        large = sum(p.market_value for p in positions if p.market_value > 100000)
        medium = sum(p.market_value for p in positions
                    if 30000 <= p.market_value <= 100000)
        small = sum(p.market_value for p in positions if p.market_value < 30000)

        return {
            "total_positions": len(positions),
            "total_market_value": total_value,
            "large_position_ratio": large / total_value if total_value > 0 else 0.0,
            "medium_position_ratio": medium / total_value if total_value > 0 else 0.0,
            "small_position_ratio": small / total_value if total_value > 0 else 0.0
        }

    def analyze_industry(
        self,
        positions: List[PositionRecord]
    ) -> Dict[str, Dict]:
        """
        分析行业分布

        Args:
            positions: 持仓列表

        Returns:
            {行业: {value, ratio, count, avg_pnl}}
        """
        if not positions:
            return {}

        # 按行业分组
        industry_groups = defaultdict(list)
        for pos in positions:
            industry = pos.industry or "未知"
            industry_groups[industry].append(pos)

        # 计算各行业统计
        total_value = sum(p.market_value for p in positions)
        industry_data = {}

        for industry, pos_list in industry_groups.items():
            value = sum(p.market_value for p in pos_list)
            industry_data[industry] = {
                "value": value,
                "ratio": value / total_value if total_value > 0 else 0.0,
                "count": len(pos_list),
                "avg_pnl": sum(p.pnl for p in pos_list) / len(pos_list) if pos_list else 0.0,
                "pnl_ratio": sum(p.pnl_ratio for p in pos_list) / len(pos_list) if pos_list else 0.0
            }

        return industry_data

    def analyze_pnl(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析盈亏分布

        Args:
            positions: 持仓列表

        Returns:
            盈亏统计字典
        """
        if not positions:
            return {
                "profitable_count": 0,
                "loss_count": 0,
                "total_pnl": 0.0,
                "best_pnl": 0.0,
                "worst_pnl": 0.0
            }

        profitable = [p for p in positions if p.pnl > 0]
        loss = [p for p in positions if p.pnl < 0]

        pnls = [p.pnl for p in positions]

        return {
            "profitable_count": len(profitable),
            "loss_count": len(loss),
            "total_pnl": sum(pnls),
            "avg_pnl": sum(pnls) / len(pnls) if pnls else 0.0,
            "best_pnl": max(pnls) if pnls else 0.0,
            "worst_pnl": min(pnls) if pnls else 0.0
        }

    def analyze_concentration(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析持仓集中度

        Args:
            positions: 持仓列表

        Returns:
            {ratio: 前十大持仓占比, hhi: 赫芬达尔指数}
        """
        if not positions:
            return {"ratio": 0.0, "hhi": 0.0}

        # 按市值排序
        sorted_positions = sorted(
            positions,
            key=lambda p: p.market_value,
            reverse=True
        )

        total_value = sum(p.market_value for p in positions)

        # 前十大持仓占比
        top10_value = sum(
            p.market_value for p in sorted_positions[:10]
        )
        concentration_ratio = top10_value / total_value if total_value > 0 else 0.0

        # 赫芬达尔指数（HHI）
        # HHI = sum(权重^2)，范围[1/n, 1]，越接近1越集中
        hhi = sum((p.weight ** 2) for p in positions)

        return {
            "ratio": concentration_ratio,
            "hhi": hhi
        }

    def get_top_positions(
        self,
        positions: List[PositionRecord],
        top_n: int = 10
    ) -> List[Dict]:
        """
        获取前N大持仓

        Args:
            positions: 持仓列表
            top_n: 前N名

        Returns:
            前N持仓列表
        """
        sorted_positions = sorted(
            positions,
            key=lambda p: p.market_value,
            reverse=True
        )

        return [
            {
                "代码": p.symbol,
                "名称": p.name,
                "市值": f"{p.market_value:.2f}",
                "占比": f"{p.weight:.2%}",
                "盈亏": f"{p.pnl:.2f}",
                "盈亏比例": f"{p.pnl_ratio:.2%}"
            }
            for p in sorted_positions[:top_n]
        ]
```

#### 任务3.2：风险分析器

**文件位置**：`vnpy_china_reporting/analysis/risk.py`

```python
from typing import List, Dict
import numpy as np
from ..core.models import PositionRecord, RiskAnalysis


class RiskAnalyzer:
    """
    风险分析器

    计算各种风险指标，包括VaR、波动率、夏普比率等。
    """

    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """
        计算VaR（Value at Risk）

        VaR表示在给定置信水平下，可能的最大损失。

        Args:
            returns: 收益率序列
            confidence: 置信水平（默认95%）

        Returns:
            VaR值
        """
        if not returns:
            return 0.0

        return float(np.percentile(returns, (1 - confidence) * 100))

    def calculate_cvar(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """
        计算条件VaR（Expected Shortfall）

        CVaR是超过VaR的平均损失。

        Args:
            returns: 收益率序列
            confidence: 置信水平

        Returns:
            CVaR值
        """
        if not returns:
            return 0.0

        var = self.calculate_var(returns, confidence)
        tail_losses = [r for r in returns if r <= var]

        if not tail_losses:
            return var

        return float(np.mean(tail_losses))

    def calculate_volatility(
        self,
        returns: List[float],
        annualize: bool = True
    ) -> float:
        """
        计算波动率

        Args:
            returns: 收益率序列
            annualize: 是否年化

        Returns:
            波动率
        """
        if not returns:
            return 0.0

        std = np.std(returns)

        if annualize:
            # 假设252个交易日
            return float(std * np.sqrt(252))

        return float(std)

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.03
    ) -> float:
        """
        计算夏普比率

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率（年化）

        Returns:
            夏普比率
        """
        if not returns:
            return 0.0

        avg_return = np.mean(returns)
        volatility = self.calculate_volatility(returns)

        if volatility == 0:
            return 0.0

        # 年化
        annual_return = avg_return * 252
        sharpe = (annual_return - risk_free_rate) / volatility

        return float(sharpe)

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.03
    ) -> float:
        """
        计算索提诺比率

        与夏普比率类似，但只考虑下行波动。

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率

        Returns:
            索提诺比率
        """
        if not returns:
            return 0.0

        avg_return = np.mean(returns)

        # 下行波动率
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return 0.0

        downside_std = np.std(negative_returns) * np.sqrt(252)

        if downside_std == 0:
            return 0.0

        annual_return = avg_return * 252
        sortino = (annual_return - risk_free_rate) / downside_std

        return float(sortino)

    def calculate_max_drawdown(
        self,
        equity_curve: List[float]
    ) -> float:
        """
        计算最大回撤

        Args:
            equity_curve: 资金曲线

        Returns:
            最大回撤比例
        """
        if not equity_curve:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value

            drawdown = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)

        return float(max_dd)

    def analyze(
        self,
        positions: List[PositionRecord],
        history_returns: List[float]
    ) -> RiskAnalysis:
        """
        综合风险分析

        Args:
            positions: 当前持仓
            history_returns: 历史收益率序列

        Returns:
            RiskAnalysis对象
        """
        # 组合风险指标
        portfolio_vol = self.calculate_volatility(history_returns)
        portfolio_var_95 = self.calculate_var(history_returns, 0.95)
        portfolio_var_99 = self.calculate_var(history_returns, 0.99)
        max_dd = self.calculate_max_drawdown(history_returns)

        # 当前回撤
        current_dd = 0.0
        if history_returns:
            peak = max(history_returns)
            current = history_returns[-1]
            current_dd = (peak - current) / peak if peak > 0 else 0

        # 收益指标
        sharpe = self.calculate_sharpe_ratio(history_returns)
        sortino = self.calculate_sortino_ratio(history_returns)
        calmar = (
            (sum(history_returns) * 252) / max_dd if max_dd != 0 else 0
        )

        # 个股风险
        position_risks = []
        for pos in positions:
            # TODO: 需要获取个股历史收益率
            position_risks.append({
                "symbol": pos.symbol,
                "weight": pos.weight,
                "pnl_ratio": pos.pnl_ratio
            })

        return RiskAnalysis(
            portfolio_volatility=portfolio_vol,
            portfolio_var_95=portfolio_var_95,
            portfolio_var_99=portfolio_var_99,
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            position_risks=position_risks
        )
```

#### 任务3.3：策略分析器

**文件位置**：`vnpy_china_reporting/analysis/strategy.py`

```python
from typing import List, Dict
from datetime import date
from ..core.models import TradeRecord


class StrategyAnalyzer:
    """
    策略分析器

    分析策略收益、归因、对比等。
    """

    def analyze_performance(
        self,
        trades: List[TradeRecord]
    ) -> Dict:
        """
        分析策略表现

        Args:
            trades: 交易记录列表

        Returns:
            策略表现字典
        """
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_return": 0.0
            }

        # 计算每笔交易的收益率
        # 需要配对买入和卖出
        paired_returns = self._pair_trades(trades)

        if not paired_returns:
            return {
                "total_trades": len(trades),
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_return": 0.0
            }

        # 胜率
        winning_trades = [r for r in paired_returns if r > 0]
        win_rate = len(winning_trades) / len(paired_returns)

        # 平均收益率
        avg_return = sum(paired_returns) / len(paired_returns)

        # 总收益率
        total_return = sum(paired_returns)

        return {
            "total_trades": len(trades),
            "paired_trades": len(paired_returns),
            "win_rate": win_rate,
            "avg_return": avg_return,
            "total_return": total_return,
            "best_return": max(paired_returns),
            "worst_return": min(paired_returns)
        }

    def _pair_trades(
        self,
        trades: List[TradeRecord]
    ) -> List[float]:
        """
        配对买卖交易，计算收益率

        Args:
            trades: 交易记录

        Returns:
            收益率列表
        """
        # 按股票分组
        symbol_trades: Dict[str, List[TradeRecord]] = {}
        for trade in trades:
            if trade.symbol not in symbol_trades:
                symbol_trades[trade.symbol] = []
            symbol_trades[trade.symbol].append(trade)

        returns = []

        # 配对买卖
        for symbol, symbol_trade_list in symbol_trades.items():
            # 按时间排序
            symbol_trade_list.sort(key=lambda t: t.datetime)

            buy_queue = []

            for trade in symbol_trade_list:
                if trade.direction.value == "buy":
                    buy_queue.append(trade)
                else:  # sell
                    if buy_queue:
                        buy_trade = buy_queue.pop(0)
                        # 计算收益率
                        cost = buy_trade.price * buy_trade.volume
                        revenue = trade.price * trade.volume
                        ret = (revenue - cost) / cost if cost > 0 else 0
                        returns.append(ret)

        return returns

    def analyze_by_month(
        self,
        trades: List[TradeRecord]
    ) -> Dict[str, Dict]:
        """
        按月分析策略表现

        Args:
            trades: 交易记录

        Returns:
            {月份: {统计数据}}
        """
        monthly_trades: Dict[str, List[TradeRecord]] = {}

        for trade in trades:
            month_key = trade.datetime.strftime("%Y-%m")
            if month_key not in monthly_trades:
                monthly_trades[month_key] = []
            monthly_trades[month_key].append(trade)

        monthly_stats = {}
        for month, month_trades in monthly_trades.items():
            monthly_stats[month] = self.analyze_performance(month_trades)

        return monthly_stats

    def compare_strategies(
        self,
        strategies: Dict[str, List[TradeRecord]]
    ) -> Dict:
        """
        对比多个策略

        Args:
            strategies: {策略名: 交易记录}

        Returns:
            策略对比结果
        """
        comparison = {}

        for name, trades in strategies.items():
            comparison[name] = self.analyze_performance(trades)

        return comparison
```

**验收标准**：
- [ ] 持仓分析全面
- [ ] 风险指标计算正确
- [ ] 策略分析有效
- [ ] 测试通过

---

### 3.4 第四阶段：导出模块实现（1人天）

#### 任务4.1：Excel导出器

**文件位置**：`vnpy_china_reporting/export/excel.py`

```python
from typing import List, Dict
from datetime import date
import openpyxl
from openpyxl.styles import (
    Font, Alignment, PatternFill, Border, Side
)
from openpyxl.utils import get_column_letter
from ..core.models import DailyReport, MonthlyReport


class ExcelExporter:
    """
    Excel导出器

    将报表数据导出为Excel文件。
    """

    def __init__(self):
        """初始化样式"""
        self.title_font = Font(size=14, bold=True, color="FFFFFF")
        self.header_font = Font(size=11, bold=True, color="333333")
        self.normal_font = Font(size=10)

        self.title_fill = PatternFill(
            start_color="4472C4", end_color="4472C4", fill_type="solid"
        )
        self.header_fill = PatternFill(
            start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
        )

        self.center_align = Alignment(
            horizontal="center", vertical="center"
        )
        self.left_align = Alignment(
            horizontal="left", vertical="center"
        )
        self.right_align = Alignment(
            horizontal="right", vertical="center"
        )

        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        self.border = thin_border

    def export_daily_report(
        self,
        report: DailyReport,
        filepath: str
    ) -> None:
        """
        导出日报到Excel

        Args:
            report: 日报对象
            filepath: 输出文件路径
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "日报"

        row = 1

        # 标题
        self._write_title(ws, row, f"每日交易报告 - {report.date}")
        row += 2

        # 资金情况
        row = self._write_section(ws, row, "资金情况", [
            ["期初余额", f"{report.start_balance:.2f}"],
            ["期末余额", f"{report.end_balance:.2f}"],
            ["当日盈亏", f"{report.daily_pnl:.2f}"],
            ["收益率", f"{report.daily_return:.2%}"],
            ["持仓市值", f"{report.total_market_value:.2f}"],
            ["仓位比例", f"{report.position_ratio:.2%}"]
        ])

        # 交易情况
        row = self._write_section(ws, row, "交易情况", [
            ["总交易次数", report.total_trades],
            ["买入次数", report.buy_trades],
            ["卖出次数", report.sell_trades],
            ["成交金额", f"{report.total_amount:.2f}"],
            ["手续费", f"{report.total_commission:.2f}"]
        ])

        # 持仓明细
        if report.positions:
            row = self._write_position_table(ws, row, report.positions)

        wb.save(filepath)

    def export_monthly_report(
        self,
        report: MonthlyReport,
        filepath: str
    ) -> None:
        """
        导出月报到Excel

        Args:
            report: 月报对象
            filepath: 输出文件路径
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "月报"

        row = 1

        # 标题
        self._write_title(
            ws, row,
            f"月度交易报告 - {report.year}年{report.month:02d}月"
        )
        row += 2

        # 收益情况
        row = self._write_section(ws, row, "收益情况", [
            ["期初余额", f"{report.start_balance:.2f}"],
            ["期末余额", f"{report.end_balance:.2f}"],
            ["月度盈亏", f"{report.monthly_pnl:.2f}"],
            ["月度收益率", f"{report.monthly_return:.2%}"]
        ])

        # 风险指标
        row = self._write_section(ws, row, "风险指标", [
            ["最大回撤", f"{report.max_drawdown:.2%}"],
            ["波动率", f"{report.volatility:.2%}"],
            ["夏普比率", f"{report.sharpe_ratio:.2f}"]
        ])

        # 持仓统计
        row = self._write_section(ws, row, "持仓统计", [
            ["平均持仓数", f"{report.avg_positions:.1f}"],
            ["最大持仓数", report.max_positions]
        ])

        # 日收益明细
        if report.daily_returns:
            row = self._write_daily_returns_table(ws, row, report.daily_returns)

        wb.save(filepath)

    def _write_title(self, ws, row: int, text: str) -> int:
        """写入标题"""
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = self.title_font
        cell.fill = self.title_fill
        cell.alignment = self.center_align
        ws.row_dimensions[row].height = 25
        return row + 1

    def _write_section(
        self,
        ws,
        row: int,
        title: str,
        data: List[List]
    ) -> int:
        """写入一个数据区块"""
        # 区块标题
        ws.cell(row=row, column=1, value=title).font = self.header_font
        row += 1

        # 数据行
        for label, value in data:
            ws.cell(row=row, column=1, value=label).alignment = self.left_align
            ws.cell(row=row, column=2, value=value).alignment = self.right_align
            row += 1

        return row + 1

    def _write_position_table(
        self,
        ws,
        row: int,
        positions: List
    ) -> int:
        """写入持仓明细表"""
        # 表头
        ws.cell(row=row, column=1, value="持仓明细").font = self.header_font
        row += 1

        headers = ["代码", "名称", "数量", "成本", "现价", "市值", "盈亏", "盈亏比"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = self.center_align
            cell.border = self.border
        row += 1

        # 数据行
        for pos in positions:
            data = [
                pos.symbol,
                pos.name,
                pos.volume,
                f"{pos.cost:.2f}",
                f"{pos.current_price:.2f}",
                f"{pos.market_value:.2f}",
                f"{pos.pnl:.2f}",
                f"{pos.pnl_ratio:.2%}"
            ]
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.alignment = self.right_align if col > 2 else self.left_align
                cell.border = self.border
            row += 1

        return row + 1

    def _write_daily_returns_table(
        self,
        ws,
        row: int,
        returns: List[float]
    ) -> int:
        """写入日收益表"""
        ws.cell(row=row, column=1, value="日收益明细").font = self.header_font
        row += 1

        # 表头
        headers = ["日期", "收益率"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = self.center_align
        row += 1

        # 数据
        for i, ret in enumerate(returns, 1):
            ws.cell(row=row, column=1, value=f"第{i}天")
            cell = ws.cell(row=row, column=2, value=f"{ret:.2%}")
            # 根据正负设置颜色
            if ret > 0:
                cell.font = Font(color="00AA00")  # 绿色
            elif ret < 0:
                cell.font = Font(color="FF0000")  # 红色
            row += 1

        return row + 1
```

#### 任务4.2：PDF导出器

**文件位置**：`vnpy_china_reporting/export/pdf.py`

```python
from typing import List
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from ..core.models import DailyReport


class PDFExporter:
    """
    PDF导出器

    将报表数据导出为PDF文件。
    """

    def __init__(self):
        """初始化"""
        self.styles = getSampleStyleSheet()
        self._setup_fonts()

    def _setup_fonts(self):
        """设置中文字体"""
        # 注册中文字体
        try:
            pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttc'))
            pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.ttf'))
        except:
            # 使用默认字体
            pass

    def export_daily_report(
        self,
        report: DailyReport,
        filepath: str
    ) -> None:
        """
        导出日报到PDF

        Args:
            report: 日报对象
            filepath: 输出文件路径
        """
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        elements = []

        # 标题
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#4472C4'),
            alignment=1  # 居中
        )
        elements.append(Paragraph(
            f"每日交易报告 - {report.date}",
            title_style
        ))
        elements.append(Spacer(1, 1*cm))

        # 资金情况
        elements.append(self._create_section("资金情况", [
            ["期初余额", f"{report.start_balance:.2f}"],
            ["期末余额", f"{report.end_balance:.2f}"],
            ["当日盈亏", f"{report.daily_pnl:.2f}"],
            ["收益率", f"{report.daily_return:.2%}"]
        ]))

        # 交易情况
        elements.append(self._create_section("交易情况", [
            ["总交易次数", str(report.total_trades)],
            ["买入次数", str(report.buy_trades)],
            ["卖出次数", str(report.sell_trades)],
            ["成交金额", f"{report.total_amount:.2f}"]
        ]))

        # 持仓明细
        if report.positions:
            elements.append(self._create_position_table(report.positions))

        doc.build(elements)

    def _create_section(
        self,
        title: str,
        data: List[List]
    ):
        """创建一个数据区块"""
        elements = []

        # 标题
        title_style = ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333')
        )
        elements.append(Paragraph(title, title_style))

        # 数据表
        table_data = [[label, value] for label, value in data]
        table = Table(table_data, colWidths=[6*cm, 6*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#D9E1F2')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'SimSun'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        return elements

    def _create_position_table(self, positions):
        """创建持仓表格"""
        elements = []

        title_style = ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333')
        )
        elements.append(Paragraph("持仓明细", title_style))

        # 表头
        headers = ["代码", "名称", "数量", "成本", "现价", "市值", "盈亏"]
        table_data = [headers]

        # 数据
        for pos in positions:
            row = [
                pos.symbol,
                pos.name,
                str(pos.volume),
                f"{pos.cost:.2f}",
                f"{pos.current_price:.2f}",
                f"{pos.market_value:.2f}",
                f"{pos.pnl:.2f}"
            ]
            table_data.append(row)

        table = Table(table_data, colWidths=[2*cm, 3*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'SimHei'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        return elements
```

#### 任务4.3：图表生成器

**文件位置**：`vnpy_china_reporting/export/charts.py`

```python
from typing import List
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date
from ..core.models import DailyReport


class ChartGenerator:
    """
    图表生成器

    生成报表相关的图表。
    """

    def __init__(self):
        """初始化"""
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

    def generate_equity_curve(
        self,
        reports: List[DailyReport],
        filepath: str
    ) -> None:
        """
        生成资金曲线图

        Args:
            reports: 日报列表
            filepath: 输出文件路径
        """
        dates = [r.date for r in reports]
        balances = [r.end_balance for r in reports]

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(dates, balances, linewidth=2, color='#4472C4')
        ax.fill_between(dates, balances, alpha=0.3, color='#4472C4')

        ax.set_title('资金曲线', fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('资金', fontsize=12)
        ax.grid(True, alpha=0.3)

        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

    def generate_daily_return_bar(
        self,
        reports: List[DailyReport],
        filepath: str
    ) -> None:
        """
        生成日收益柱状图

        Args:
            reports: 日报列表
            filepath: 输出文件路径
        """
        dates = [r.date for r in reports]
        returns = [r.daily_return for r in reports]

        colors = ['#00AA00' if r >= 0 else '#FF0000' for r in returns]

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.bar(dates, [r * 100 for r in returns], color=colors, alpha=0.7)

        ax.set_title('日收益率', fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('收益率(%)', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

    def generate_position_pie(
        self,
        report: DailyReport,
        filepath: str
    ) -> None:
        """
        生成持仓分布饼图

        Args:
            report: 日报对象
            filepath: 输出文件路径
        """
        if not report.positions:
            return

        labels = [f"{p.symbol}\n{p.name}" for p in report.positions]
        sizes = [p.market_value for p in report.positions]

        fig, ax = plt.subplots(figsize=(10, 10))

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.Set3(range(len(labels)))
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        ax.set_title('持仓分布', fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
```

**验收标准**：
- [ ] Excel导出正常
- [ ] PDF导出正常
- [ ] 图表生成美观
- [ ] 格式正确

---

## 4. 测试计划

### 4.1 单元测试矩阵

| 模块 | 测试文件 | 用例数 | 覆盖目标 |
|------|---------|--------|---------|
| core/models | test_models.py | 6 | 100% |
| report/daily | test_daily.py | 5 | 90% |
| report/monthly | test_monthly.py | 4 | 85% |
| report/yearly | test_yearly.py | 4 | 85% |
| analysis/position | test_position.py | 5 | 90% |
| analysis/risk | test_risk.py | 6 | 90% |
| analysis/strategy | test_strategy.py | 4 | 85% |
| export/excel | test_excel.py | 4 | 80% |
| export/pdf | test_pdf.py | 3 | 75% |
| export/charts | test_charts.py | 3 | 75% |
| **合计** | | **44** | **87%** |

### 4.2 集成测试

```python
# tests/reporting/test_integration.py
import pytest
from datetime import date, timedelta
from vnpy_china_reporting.report import DailyReportGenerator
from vnpy_china_reporting.analysis import PositionAnalyzer, RiskAnalyzer
from vnpy_china_reporting.export import ExcelExporter


def test_full_reporting_workflow():
    """测试完整报表流程"""
    # 1. 生成日报
    generator = DailyReportGenerator()
    report = generator.generate(date.today())

    assert report.date == date.today()
    assert len(report.positions) >= 0

    # 2. 持仓分析
    analyzer = PositionAnalyzer()
    analysis = analyzer.analyze(report.positions)

    assert analysis.total_positions == len(report.positions)

    # 3. 导出Excel
    exporter = ExcelExporter()
    filepath = "reports/test_daily.xlsx"
    exporter.export_daily_report(report, filepath)

    import os
    assert os.path.exists(filepath)
    os.remove(filepath)


def test_monthly_to_excel_export():
    """测试月报导出"""
    from vnpy_china_reporting.report import MonthlyReportGenerator

    generator = MonthlyReportGenerator()
    report = generator.generate(date.today())

    exporter = ExcelExporter()
    filepath = "reports/test_monthly.xlsx"
    exporter.export_monthly_report(report, filepath)

    import os
    assert os.path.exists(filepath)
    os.remove(filepath)
```

---

## 5. 时间安排

### 5.1 日程计划

| 日期 | 任务 | 工时 |
|------|------|------|
| Day 1 | 基础框架+数据模型 | 8h |
| Day 2 | 日报+月报+年报生成器 | 8h |
| Day 3 | 持仓+风险+策略分析 | 8h |
| Day 4 | Excel+PDF+图表导出 | 8h |
| **合计** | | **32h (4人天)** |

### 5.2 里程碑

| 里程碑 | 时间 | 交付内容 |
|--------|------|---------|
| M1 | Day 1结束 | 基础框架完成 |
| M2 | Day 2结束 | 报表生成器完成 |
| M3 | Day 3结束 | 分析模块完成 |
| M4 | Day 4结束 | 导出模块完成 |

---

## 6. 风险管理

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| PDF中文乱码 | 中 | 中 | 使用正确的中文字体 |
| Excel样式问题 | 低 | 低 | 充分测试各种格式 |
| 图表依赖缺失 | 低 | 中 | 提供安装说明 |

### 6.2 数据风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 数据不完整 | 中 | 中 | 使用默认值 |
| 数据格式错误 | 低 | 低 | 容错处理 |

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 日报生成正确
- [ ] 月报汇总准确
- [ ] 年报数据完整
- [ ] 持仓分析全面
- [ ] 风险指标正确
- [ ] Excel导出正常
- [ ] PDF导出正常
- [ ] 图表生成美观

### 7.2 质量验收

- [ ] 单元测试覆盖率≥85%
- [ ] 所有测试通过
- [ ] 代码通过类型检查
- [ ] 文档完整

---

## 8. 后续计划

### 8.1 功能扩展

- [ ] 支持HTML格式导出
- [ ] 支持邮件自动发送
- [ ] 支持自定义报表模板
- [ ] 支持多账户合并报表

### 8.2 优化方向

- [ ] 使用缓存加速报表生成
- [ ] 支持异步导出
- [ ] 支持增量更新
- [ ] 添加更多图表类型

---

**文档版本**：v1.0
**创建日期**：2026-02-24
**维护者**：AI Assistant
**下次更新**：实施完成后更新
