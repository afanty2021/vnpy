"""
月报生成器

生成月度交易报表，包含整月交易记录、月度统计和分析。
盈亏采用权益变化法：月度盈亏 = 期末权益 - 期初权益。
"""

from datetime import date
from calendar import monthrange
from typing import List, Dict, Optional, Any
import logging

from .base import BaseReportGenerator
from .daily import DailyReportGenerator
from ..core.models import ReportData
from ..core.enums import ReportType

logger = logging.getLogger(__name__)


class MonthlyReportGenerator(BaseReportGenerator):
    """
    月报生成器

    生成月度交易报表，包含整月交易记录、月度统计和分析。
    """

    def __init__(
        self,
        main_engine: Optional[Any] = None,
        equity_source: Optional[Any] = None,
        industry_source: Optional[Any] = None,
    ) -> None:
        """
        初始化月报生成器

        Args:
            main_engine: 主引擎实例
            equity_source: 期初权益源（见 BaseReportGenerator）
            industry_source: 行业映射源（见 BaseReportGenerator）
        """
        super().__init__(main_engine, equity_source, industry_source)
        self.report_type = ReportType.MONTHLY
        self.daily_generator = DailyReportGenerator(main_engine, equity_source, industry_source)

    def generate_monthly(
        self,
        year: int,
        month: int,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """
        生成月报数据

        Args:
            year: 年份
            month: 月份
            start_equity: 月初权益（权益变化法所需，vnpy 不提供历史权益，
                需调用方传入；为 None 时月度盈亏记为 None）

        Returns:
            月报数据
        """
        # 计算月度日期范围
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        # 获取本月交易、持仓、账户
        trades = self.get_trades(start_date, end_date)
        positions = self.get_positions()
        account = self.get_account()

        # 权益变化法计算月度盈亏
        start_equity = self._resolve_start_equity(start_date, start_equity)
        end_equity = account.total_equity if account else None
        monthly_pnl = self.calculate_pnl(start_equity, end_equity)
        monthly_pnl_ratio = self.calculate_pnl_ratio(monthly_pnl, start_equity)

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

    def generate_by_date(
        self,
        report_date: date,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """
        根据日期生成月报

        Args:
            report_date: 报表日期（取月份）
            start_equity: 月初权益

        Returns:
            月报数据
        """
        return self.generate_monthly(report_date.year, report_date.month, start_equity)

    def generate_daily(
        self,
        report_date: date,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """实现基类的日报生成接口（委托内部日报生成器）"""
        return self.daily_generator.generate_daily(report_date, start_equity)

    def get_trading_days(self, year: int, month: int) -> List[date]:
        """
        获取指定月份的交易日列表（仅排除周末，未排除法定假日）

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

    def get_monthly_stats(
        self,
        year: int,
        month: int,
        daily_equities: Optional[Dict[date, float]] = None
    ) -> Dict:
        """
        获取月度统计信息

        Args:
            year: 年份
            month: 月份
            daily_equities: 每日权益快照 {date: 权益}，相邻交易日差分得每日盈亏。
                vnpy 不提供历史权益，需调用方传入；未提供时盈亏统计为 None。

        Returns:
            月度统计字典
        """
        trading_days = self.get_trading_days(year, month)

        daily_pnls: List[float] = []
        if daily_equities:
            month_days = sorted(
                d for d in daily_equities if d.year == year and d.month == month
            )
            for i in range(1, len(month_days)):
                daily_pnls.append(
                    daily_equities[month_days[i]] - daily_equities[month_days[i - 1]]
                )
        else:
            logger.warning("未提供每日权益(daily_equities)，月度盈亏统计不可用")

        return {
            "trading_days": len(trading_days),
            "total_pnl": sum(daily_pnls) if daily_pnls else None,
            "avg_daily_pnl": (sum(daily_pnls) / len(daily_pnls)) if daily_pnls else None,
            "best_day_pnl": max(daily_pnls) if daily_pnls else None,
            "worst_day_pnl": min(daily_pnls) if daily_pnls else None,
            "positive_days": len([p for p in daily_pnls if p > 0]),
            "negative_days": len([p for p in daily_pnls if p < 0]),
        }

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

        buy_trades = len([t for t in report.trades if t.direction == "buy"])
        sell_trades = len([t for t in report.trades if t.direction == "sell"])

        acc = report.account
        start_balance: Optional[float] = None
        if acc is not None and report.daily_pnl is not None:
            start_balance = acc.total_equity - report.daily_pnl

        return {
            "报表月份": f"{report.start_date.year}年{report.start_date.month:02d}月" if report.start_date else "",
            "期初余额": self._fmt(start_balance),
            "期末余额": self._fmt(acc.total_equity if acc else None),
            "月度盈亏": self._fmt(report.daily_pnl),
            "月度收益率": self._fmt_pct(report.daily_pnl_ratio),
            "交易次数": total_trades,
            "买入次数": buy_trades,
            "卖出次数": sell_trades,
            "成交金额": f"{total_amount:.2f}",
            "手续费": self._fmt(acc.commission if acc else None),
            "持仓市值": self._fmt(acc.market_value if acc else None),
            "持仓数量": len(report.positions)
        }
