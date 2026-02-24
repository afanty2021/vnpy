"""
财务数据模型

定义财务数据相关的数据结构。
"""

from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class FinancialData:
    """财务数据"""

    symbol: str
    report_date: str  # 报告期 YYYYMM
    report_type: str = "1"  # 报告类型 1合并报表 2单季合并

    # 基本指标
    pe_ratio: float = 0.0  # 市盈率
    pb_ratio: float = 0.0  # 市净率
    ps_ratio: float = 0.0  # 市销率

    # 盈利能力
    roe: float = 0.0  # 净资产收益率
    roa: float = 0.0  # 总资产收益率
    gross_margin: float = 0.0  # 毛利率
    net_margin: float = 0.0  # 净利率

    # 规模指标
    revenue: float = 0.0  # 营业收入
    net_profit: float = 0.0  # 净利润
    total_assets: float = 0.0  # 总资产
    total_equity: float = 0.0  # 股东权益

    # 增长指标
    revenue_growth: float = 0.0  # 营收增长
    profit_growth: float = 0.0  # 净利润增长

    # 运营指标
    inventory_turnover: float = 0.0  # 存货周转率
    asset_turnover: float = 0.0  # 资产周转率

    # 估值
    market_cap: float = 0.0  # 市值
    float_market_cap: float = 0.0  # 流通市值

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "report_date": self.report_date,
            "report_type": self.report_type,
            "pe_ratio": self.pe_ratio,
            "pb_ratio": self.pb_ratio,
            "ps_ratio": self.ps_ratio,
            "roe": self.roe,
            "roa": self.roa,
            "gross_margin": self.gross_margin,
            "net_margin": self.net_margin,
            "revenue": self.revenue,
            "net_profit": self.net_profit,
            "total_assets": self.total_assets,
            "total_equity": self.total_equity,
            "revenue_growth": self.revenue_growth,
            "profit_growth": self.profit_growth,
            "inventory_turnover": self.inventory_turnover,
            "asset_turnover": self.asset_turnover,
            "market_cap": self.market_cap,
            "float_market_cap": self.float_market_cap,
        }


@dataclass
class IncomeStatement:
    """利润表数据"""

    symbol: str
    report_date: str
    report_type: str = "1"

    # 收入
    total_revenue: float = 0.0  # 营业收入
    operating_revenue: float = 0.0  # 主营业务收入

    # 成本
    total_cost: float = 0.0  # 营业成本
    operating_cost: float = 0.0  # 主营业务成本

    # 费用
    sales_expense: float = 0.0  # 销售费用
    management_expense: float = 0.0  # 管理费用
    financial_expense: float = 0.0  # 财务费用

    # 利润
    operating_profit: float = 0.0  # 营业利润
    total_profit: float = 0.0  # 利润总额
    net_profit: float = 0.0  # 净利润

    # 每股收益
    eps: float = 0.0  # 每股收益

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "report_date": self.report_date,
            "report_type": self.report_type,
            "total_revenue": self.total_revenue,
            "operating_revenue": self.operating_revenue,
            "total_cost": self.total_cost,
            "operating_cost": self.operating_cost,
            "sales_expense": self.sales_expense,
            "management_expense": self.management_expense,
            "financial_expense": self.financial_expense,
            "operating_profit": self.operating_profit,
            "total_profit": self.total_profit,
            "net_profit": self.net_profit,
            "eps": self.eps,
        }


@dataclass
class BalanceSheet:
    """资产负债表数据"""

    symbol: str
    report_date: str
    report_type: str = "1"

    # 资产
    total_assets: float = 0.0  # 资产总计
    current_assets: float = 0.0  # 流动资产
    non_current_assets: float = 0.0  # 非流动资产

    # 流动资产
    cash_equivalents: float = 0.0  # 货币资金
    accounts_receivable: float = 0.0  # 应收账款
    inventory: float = 0.0  # 存货

    # 负债
    total_liabilities: float = 0.0  # 负债合计
    current_liabilities: float = 0.0  # 流动负债
    non_current_liabilities: float = 0.0  # 非流动负债

    # 权益
    total_equity: float = 0.0  # 股东权益
    paid_in_capital: float = 0.0  # 实收资本
    retained_earnings: float = 0.0  # 未分配利润

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "report_date": self.report_date,
            "report_type": self.report_type,
            "total_assets": self.total_assets,
            "current_assets": self.current_assets,
            "non_current_assets": self.non_current_assets,
            "cash_equivalents": self.cash_equivalents,
            "accounts_receivable": self.accounts_receivable,
            "inventory": self.inventory,
            "total_liabilities": self.total_liabilities,
            "current_liabilities": self.current_liabilities,
            "non_current_liabilities": self.non_current_liabilities,
            "total_equity": self.total_equity,
            "paid_in_capital": self.paid_in_capital,
            "retained_earnings": self.retained_earnings,
        }


@dataclass
class CashFlow:
    """现金流量表数据"""

    symbol: str
    report_date: str
    report_type: str = "1"

    # 经营活动
    operating_cash_flow: float = 0.0  # 经营活动产生的现金流量净额

    # 投资活动
    investing_cash_flow: float = 0.0  # 投资活动产生的现金流量净额

    # 筹资活动
    financing_cash_flow: float = 0.0  # 筹资活动产生的现金流量净额

    # 现金变动
    net_cash_flow: float = 0.0  # 现金及现金等价物净增加额

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "report_date": self.report_date,
            "report_type": self.report_type,
            "operating_cash_flow": self.operating_cash_flow,
            "investing_cash_flow": self.investing_cash_flow,
            "financing_cash_flow": self.financing_cash_flow,
            "net_cash_flow": self.net_cash_flow,
        }
