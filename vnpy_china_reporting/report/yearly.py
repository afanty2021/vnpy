"""
年报生成器

生成年度交易报表，包含全年交易记录、年度统计和分析。
盈亏采用权益变化法：年度盈亏 = 期末权益 - 期初权益。
"""

from datetime import date
from typing import Dict, Optional, Any
import logging

from .base import BaseReportGenerator
from .monthly import MonthlyReportGenerator
from ..core.models import ReportData
from ..core.enums import ReportType

logger = logging.getLogger(__name__)


class YearlyReportGenerator(BaseReportGenerator):
    """
    年报生成器

    生成年度交易报表，包含全年交易记录、年度统计和分析。
    """

    def __init__(
        self,
        main_engine: Optional[Any] = None,
        equity_source: Optional[Any] = None,
        industry_source: Optional[Any] = None,
    ) -> None:
        """
        初始化年报生成器

        Args:
            main_engine: 主引擎实例
            equity_source: 期初权益源（见 BaseReportGenerator）
            industry_source: 行业映射源（见 BaseReportGenerator）
        """
        super().__init__(main_engine, equity_source, industry_source)
        self.report_type = ReportType.YEARLY
        self.monthly_generator = MonthlyReportGenerator(main_engine, equity_source, industry_source)

    def generate_yearly(
        self,
        year: int,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """
        生成年报数据

        Args:
            year: 年份
            start_equity: 年初权益（权益变化法所需，vnpy 不提供历史权益，
                需调用方传入；为 None 时年度盈亏记为 None）

        Returns:
            年报数据
        """
        # 计算年度日期范围
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # 获取本年交易、持仓、账户
        trades = self.get_trades(start_date, end_date)
        positions = self.get_positions()
        account = self.get_account()

        # 权益变化法计算年度盈亏
        start_equity = self._resolve_start_equity(start_date, start_equity)
        end_equity = account.total_equity if account else None
        yearly_pnl = self.calculate_pnl(start_equity, end_equity)
        yearly_pnl_ratio = self.calculate_pnl_ratio(yearly_pnl, start_equity)

        return ReportData(
            report_type=self.report_type,
            start_date=start_date,
            end_date=end_date,
            account=account,
            positions=positions,
            trades=trades,
            daily_pnl=yearly_pnl,
            daily_pnl_ratio=yearly_pnl_ratio
        )

    def generate_by_date(
        self,
        report_date: date,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """
        根据日期生成年报

        Args:
            report_date: 报表日期（取年份）
            start_equity: 年初权益

        Returns:
            年报数据
        """
        return self.generate_yearly(report_date.year, start_equity)

    def generate_daily(
        self,
        report_date: date,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """实现基类的日报生成接口（委托内部日报生成器）"""
        return self.monthly_generator.daily_generator.generate_daily(report_date, start_equity)

    def get_yearly_summary(self, report: ReportData) -> Dict:
        """
        获取年报摘要

        Args:
            report: 报表数据对象

        Returns:
            摘要字典
        """
        total_trades = len(report.trades)
        total_amount = sum(t.amount for t in report.trades)

        buy_trades = len([t for t in report.trades if t.direction == "buy"])
        sell_trades = len([t for t in report.trades if t.direction == "sell"])

        acc = report.account
        start_balance: Optional[float] = None
        if acc is not None and report.daily_pnl is not None:
            start_balance = acc.total_equity - report.daily_pnl

        return {
            "报表年份": f"{report.start_date.year}年" if report.start_date else "",
            "期初余额": self._fmt(start_balance),
            "期末余额": self._fmt(acc.total_equity if acc else None),
            "年度盈亏": self._fmt(report.daily_pnl),
            "年度收益率": self._fmt_pct(report.daily_pnl_ratio),
            "交易次数": total_trades,
            "买入次数": buy_trades,
            "卖出次数": sell_trades,
            "成交金额": f"{total_amount:.2f}",
            "手续费": self._fmt(acc.commission if acc else None),
            "持仓市值": self._fmt(acc.market_value if acc else None),
            "持仓数量": len(report.positions)
        }

    def get_yearly_stats(
        self,
        year: int,
        monthly_equities: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        获取年度统计信息

        Args:
            year: 年份
            monthly_equities: 月末权益快照 {month(1-12): 权益}，相邻月差分得月度盈亏。
                vnpy 不提供历史权益，需调用方传入；未提供时盈亏统计为 None。

        Returns:
            年度统计字典
        """
        monthly_pnls: list = []
        if monthly_equities:
            months = sorted(monthly_equities.keys())
            for i in range(1, len(months)):
                monthly_pnls.append(monthly_equities[months[i]] - monthly_equities[months[i - 1]])
        else:
            logger.warning("未提供月末权益(monthly_equities)，年度盈亏统计不可用")

        positive_months = len([p for p in monthly_pnls if p > 0])
        total_pnl = sum(monthly_pnls) if monthly_pnls else None

        return {
            "year": year,
            "total_pnl": total_pnl,
            "avg_monthly_pnl": (total_pnl / len(monthly_pnls)) if monthly_pnls else None,
            "positive_months": positive_months,
            "negative_months": (len(monthly_pnls) - positive_months) if monthly_pnls else 0,
            "monthly_pnls": monthly_pnls,
        }

    def get_monthly_breakdown(
        self,
        year: int,
        monthly_start_equities: Optional[Dict[int, float]] = None
    ) -> Dict[str, Dict]:
        """
        获取月度分解数据

        Args:
            year: 年份
            monthly_start_equities: 各月月初权益 {month: 月初权益}，用于各月盈亏计算。
                未提供时各月盈亏为 None。

        Returns:
            月度分解字典
        """
        monthly_breakdown = {}

        for month in range(1, 13):
            start_eq = monthly_start_equities.get(month) if monthly_start_equities else None
            month_report = self.monthly_generator.generate_monthly(year, month, start_eq)
            month_key = f"{year}年{month:02d}月"

            acc = month_report.account
            monthly_breakdown[month_key] = {
                "start_date": month_report.start_date,
                "end_date": month_report.end_date,
                "daily_pnl": month_report.daily_pnl,
                "daily_pnl_ratio": month_report.daily_pnl_ratio,
                "total_trades": len(month_report.trades),
                "total_amount": sum(t.amount for t in month_report.trades),
                "commission": acc.commission if acc else None,
            }

        return monthly_breakdown
