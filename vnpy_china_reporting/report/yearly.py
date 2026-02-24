"""
年报生成器

生成年度交易报表，包含全年交易记录、年度统计和分析。
"""

from datetime import date
from typing import List, Dict

from .base import BaseReportGenerator
from .monthly import MonthlyReportGenerator
from ..core.models import ReportData
from ..core.enums import ReportType


class YearlyReportGenerator(BaseReportGenerator):
    """
    年报生成器

    生成年度交易报表，包含全年交易记录、年度统计和分析。
    """

    def __init__(self, main_engine=None):
        """
        初始化年报生成器

        Args:
            main_engine: 主引擎实例
        """
        super().__init__(main_engine)
        self.report_type = ReportType.YEARLY
        self.monthly_generator = MonthlyReportGenerator(main_engine)

    def generate(self, year: int) -> ReportData:
        """
        生成年报数据

        Args:
            year: 年份

        Returns:
            年报数据
        """
        # 计算年度日期范围
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # 获取本年交易
        trades = self.get_trades(start_date, end_date)

        # 获取持仓
        positions = self.get_positions()

        # 获取账户数据
        account = self.get_account()

        # 计算年度盈亏
        yearly_pnl = self.calculate_daily_pnl(trades)
        yearly_pnl_ratio = 0.0
        if account.total_equity > 0:
            yearly_pnl_ratio = yearly_pnl / account.total_equity

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

    def generate_by_date(self, report_date: date) -> ReportData:
        """
        根据日期生成年报

        Args:
            report_date: 报表日期（取年份）

        Returns:
            年报数据
        """
        return self.generate(report_date.year)

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

        # 计算交易方向统计
        buy_trades = len([t for t in report.trades if t.direction == "buy"])
        sell_trades = len([t for t in report.trades if t.direction == "sell"])

        return {
            "报表年份": f"{report.start_date.year}年" if report.start_date else "",
            "期初余额": f"{report.account.total_equity - report.daily_pnl:.2f}",
            "期末余额": f"{report.account.total_equity:.2f}",
            "年度盈亏": f"{report.daily_pnl:.2f}",
            "年度收益率": f"{report.daily_pnl_ratio:.2%}",
            "交易次数": total_trades,
            "买入次数": buy_trades,
            "卖出次数": sell_trades,
            "成交金额": f"{total_amount:.2f}",
            "手续费": f"{report.account.commission:.2f}",
            "持仓市值": f"{report.account.market_value:.2f}",
            "持仓数量": len(report.positions)
        }

    def get_yearly_stats(self, year: int) -> Dict:
        """
        获取年度统计信息

        Args:
            year: 年份

        Returns:
            年度统计字典
        """
        monthly_stats = []
        for month in range(1, 13):
            stats = self.monthly_generator.get_monthly_stats(year, month)
            monthly_stats.append(stats)

        # 汇总月度数据
        total_pnl = sum(s["total_pnl"] for s in monthly_stats)
        total_trading_days = sum(s["trading_days"] for s in monthly_stats)
        positive_months = len([s for s in monthly_stats if s["total_pnl"] > 0])

        return {
            "year": year,
            "total_trading_days": total_trading_days,
            "total_pnl": total_pnl,
            "avg_monthly_pnl": total_pnl / 12,
            "positive_months": positive_months,
            "negative_months": 12 - positive_months,
            "monthly_stats": monthly_stats
        }

    def get_monthly_breakdown(self, year: int) -> Dict[str, Dict]:
        """
        获取月度分解数据

        Args:
            year: 年份

        Returns:
            月度分解字典
        """
        monthly_breakdown = {}

        for month in range(1, 13):
            month_report = self.monthly_generator.generate(year, month)
            month_key = f"{year}年{month:02d}月"

            monthly_breakdown[month_key] = {
                "start_date": month_report.start_date,
                "end_date": month_report.end_date,
                "daily_pnl": month_report.daily_pnl,
                "daily_pnl_ratio": month_report.daily_pnl_ratio,
                "total_trades": len(month_report.trades),
                "total_amount": sum(t.amount for t in month_report.trades),
                "commission": month_report.account.commission
            }

        return monthly_breakdown
