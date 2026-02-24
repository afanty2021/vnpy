"""
月报生成器

生成月度交易报表，包含整月交易记录、月度统计和分析。
"""

from datetime import date
from calendar import monthrange
from typing import List, Dict, Optional, Any

from .base import BaseReportGenerator
from .daily import DailyReportGenerator
from ..core.models import ReportData
from ..core.enums import ReportType


class MonthlyReportGenerator(BaseReportGenerator):
    """
    月报生成器

    生成月度交易报表，包含整月交易记录、月度统计和分析。
    """

    def __init__(self, main_engine: Optional[Any] = None) -> None:
        """
        初始化月报生成器

        Args:
            main_engine: 主引擎实例
        """
        super().__init__(main_engine)
        self.report_type = ReportType.MONTHLY
        self.daily_generator = DailyReportGenerator(main_engine)

    def generate_monthly(self, year: int, month: int) -> ReportData:
        """
        生成月报数据

        Args:
            year: 年份
            month: 月份

        Returns:
            月报数据
        """
        # 计算月度日期范围
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        # 获取本月交易
        trades = self.get_trades(start_date, end_date)

        # 获取持仓
        positions = self.get_positions()

        # 获取账户数据
        account = self.get_account()

        # 计算月度盈亏
        monthly_pnl = self.calculate_daily_pnl(trades)
        monthly_pnl_ratio = 0.0
        if account.total_equity > 0:
            monthly_pnl_ratio = monthly_pnl / account.total_equity

        return ReportData(
            report_type=self.report_type,
            start_date=start_date,
            end_date=end_date,
            account=account,
            positions=positions,
            trades=trades,
            daily_pnl=monthly_pnl,
            daily_pnl_ratio=monthly_pnl_ratio
        )

    def generate_by_date(self, report_date: date) -> ReportData:
        """
        根据日期生成月报

        Args:
            report_date: 报表日期（取月份）

        Returns:
            月报数据
        """
        return self.generate_monthly(report_date.year, report_date.month)

    def generate_daily(self, report_date: date) -> ReportData:
        """
        实现基类的日报生成接口

        Args:
            report_date: 报表日期

        Returns:
            日报数据（实际返回当日报表，但使用月报生成器的数据源）
        """
        return self.daily_generator.generate_daily(report_date)

    def get_trading_days(self, year: int, month: int) -> List[date]:
        """
        获取指定月份的交易日列表

        Args:
            year: 年份
            month: 月份

        Returns:
            交易日列表
        """
        days_in_month = monthrange(year, month)[1]
        trading_days = []

        for day in range(1, days_in_month + 1):
            dt = date(year, month, day)
            # 排除周末 (0-4 是周一到周五)
            if dt.weekday() < 5:
                trading_days.append(dt)

        return trading_days

    def get_monthly_summary(self, report: ReportData) -> Dict:
        """
        获取月报摘要

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
            "报表月份": f"{report.start_date.year}年{report.start_date.month:02d}月" if report.start_date else "",
            "期初余额": f"{report.account.total_equity - report.daily_pnl:.2f}",
            "期末余额": f"{report.account.total_equity:.2f}",
            "月度盈亏": f"{report.daily_pnl:.2f}",
            "月度收益率": f"{report.daily_pnl_ratio:.2%}",
            "交易次数": total_trades,
            "买入次数": buy_trades,
            "卖出次数": sell_trades,
            "成交金额": f"{total_amount:.2f}",
            "手续费": f"{report.account.commission:.2f}",
            "持仓市值": f"{report.account.market_value:.2f}",
            "持仓数量": len(report.positions)
        }

    def get_monthly_stats(self, year: int, month: int) -> Dict:
        """
        获取月度统计信息

        Args:
            year: 年份
            month: 月份

        Returns:
            月度统计字典
        """
        trading_days = self.get_trading_days(year, month)

        daily_pnls = []
        for day in trading_days:
            trades = self.get_trades(day, day)
            pnl = self.calculate_daily_pnl(trades)
            daily_pnls.append(pnl)

        return {
            "trading_days": len(trading_days),
            "total_pnl": sum(daily_pnls),
            "avg_daily_pnl": sum(daily_pnls) / len(daily_pnls) if daily_pnls else 0,
            "best_day_pnl": max(daily_pnls) if daily_pnls else 0,
            "worst_day_pnl": min(daily_pnls) if daily_pnls else 0,
            "positive_days": len([p for p in daily_pnls if p > 0]),
            "negative_days": len([p for p in daily_pnls if p < 0])
        }
