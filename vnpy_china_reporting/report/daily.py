"""
日报生成器

生成每日交易报表，包含当日交易记录、持仓状况和盈亏情况。
"""

from datetime import date, timedelta
from typing import List, Dict, Optional, Any

from .base import BaseReportGenerator
from ..core.models import ReportData, TradeRecord, AccountData
from ..core.enums import ReportType


class DailyReportGenerator(BaseReportGenerator):
    """
    日报生成器

    生成每日交易报表，包含当日交易记录、持仓状况和盈亏情况。
    """

    def __init__(self, main_engine: Optional[Any] = None) -> None:
        """
        初始化日报生成器

        Args:
            main_engine: 主引擎实例
        """
        super().__init__(main_engine)
        self.report_type = ReportType.DAILY

    def generate_daily(self, report_date: date) -> ReportData:
        """
        生成日报数据

        Args:
            report_date: 报表日期

        Returns:
            日报数据
        """
        # 获取当日交易
        trades = self.get_trades(report_date, report_date)

        # 获取持仓
        positions = self.get_positions()

        # 获取账户数据
        account = self.get_account()

        # 计算当日盈亏
        daily_pnl = self.calculate_daily_pnl(trades)
        daily_pnl_ratio = 0.0
        if account.total_equity > 0:
            daily_pnl_ratio = daily_pnl / account.total_equity

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

    def get_trades(self, start_date: date, end_date: date) -> List[TradeRecord]:
        """
        获取指定日期的交易记录

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易记录列表
        """
        # 实际实现应从主引擎获取数据
        # 这里返回模拟数据用于测试
        return super().get_trades(start_date, end_date)

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

        return {
            "报表日期": report.start_date.strftime("%Y-%m-%d") if report.start_date else "",
            "期初余额": f"{report.account.total_equity - report.daily_pnl:.2f}",
            "期末余额": f"{report.account.total_equity:.2f}",
            "当日盈亏": f"{report.daily_pnl:.2f}",
            "收益率": f"{report.daily_pnl_ratio:.2%}",
            "交易次数": len(report.trades),
            "买入次数": buy_trades,
            "卖出次数": sell_trades,
            "成交金额": f"{total_amount:.2f}",
            "手续费": f"{report.account.commission:.2f}",
            "持仓市值": f"{report.account.market_value:.2f}",
            "持仓数量": len(report.positions)
        }
