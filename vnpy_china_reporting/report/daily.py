"""
日报生成器

生成每日交易报表，包含当日交易记录、持仓状况和盈亏情况。
盈亏采用权益变化法：当日盈亏 = 期末权益 - 期初权益。
"""

from datetime import date
from typing import List, Dict, Optional, Any

from .base import BaseReportGenerator
from ..core.models import ReportData
from ..core.enums import ReportType


class DailyReportGenerator(BaseReportGenerator):
    """
    日报生成器

    生成每日交易报表，包含当日交易记录、持仓状况和盈亏情况。
    """

    def __init__(
        self,
        main_engine: Optional[Any] = None,
        equity_source: Optional[Any] = None,
        industry_source: Optional[Any] = None,
    ) -> None:
        """
        初始化日报生成器

        Args:
            main_engine: 主引擎实例
            equity_source: 期初权益源（见 BaseReportGenerator）
            industry_source: 行业映射源（见 BaseReportGenerator）
        """
        super().__init__(main_engine, equity_source, industry_source)
        self.report_type = ReportType.DAILY

    def generate_daily(
        self,
        report_date: date,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """
        生成日报数据

        Args:
            report_date: 报表日期
            start_equity: 期初权益（权益变化法所需，vnpy 不提供历史权益，
                需调用方传入；为 None 时当日盈亏记为 None）

        Returns:
            日报数据
        """
        # 获取当日交易、持仓、账户
        trades = self.get_trades(report_date, report_date)
        positions = self.get_positions()
        account = self.get_account()

        # 权益变化法计算当日盈亏
        start_equity = self._resolve_start_equity(report_date, start_equity)
        end_equity = account.total_equity if account else None
        daily_pnl = self.calculate_pnl(start_equity, end_equity)
        daily_pnl_ratio = self.calculate_pnl_ratio(daily_pnl, start_equity)

        return ReportData(
            report_type=self.report_type,
            start_date=report_date,
            end_date=report_date,
            account=account,
            positions=positions,
            trades=trades,
            daily_pnl=daily_pnl,
            daily_pnl_ratio=daily_pnl_ratio
        )

    def get_trades_detail(self, report_date: date) -> List[Dict]:
        """
        获取交易明细

        Args:
            report_date: 报表日期

        Returns:
            交易明细列表
        """
        trades = self.get_trades(report_date, report_date)

        return [
            {
                "时间": t.timestamp.strftime("%H:%M:%S") if t.timestamp else "",
                "代码": t.symbol,
                "方向": "买入" if t.direction == "buy" else "卖出",
                "价格": f"{t.price:.2f}",
                "数量": t.volume,
                "金额": f"{t.amount:.2f}",
                "手续费": f"{t.commission:.2f}"
            }
            for t in trades
        ]

    def get_summary(self, report: ReportData) -> Dict:
        """
        获取日报摘要

        Args:
            report: 报表数据对象

        Returns:
            摘要字典
        """
        buy_trades = len([t for t in report.trades if t.direction == "buy"])
        sell_trades = len([t for t in report.trades if t.direction == "sell"])
        total_amount = sum(t.amount for t in report.trades)

        acc = report.account
        # 期初余额 = 期末权益 - 当日盈亏（盈亏可得时反推）
        start_balance: Optional[float] = None
        if acc is not None and report.daily_pnl is not None:
            start_balance = acc.total_equity - report.daily_pnl

        return {
            "报表日期": report.start_date.strftime("%Y-%m-%d") if report.start_date else "",
            "期初余额": self._fmt(start_balance),
            "期末余额": self._fmt(acc.total_equity if acc else None),
            "当日盈亏": self._fmt(report.daily_pnl),
            "收益率": self._fmt_pct(report.daily_pnl_ratio),
            "交易次数": len(report.trades),
            "买入次数": buy_trades,
            "卖出次数": sell_trades,
            "成交金额": f"{total_amount:.2f}",
            "手续费": self._fmt(acc.commission if acc else None),
            "持仓市值": self._fmt(acc.market_value if acc else None),
            "持仓数量": len(report.positions)
        }
