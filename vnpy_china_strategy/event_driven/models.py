"""
事件驱动数据模型
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class EarningsForecast:
    """业绩预告

    记录上市公司发布的业绩预告信息。
    """

    symbol: str  # 股票代码
    name: str  # 公司名称
    forecast_date: date  # 预告日期
    report_date: date  # 报告期
    earnings_type: str  # 业绩类型 (预增/预减/扭亏/...)
    earnings_range_low: Optional[Decimal] = None  # 业绩下限
    earnings_range_high: Optional[Decimal] = None  # 业绩上限
    yoy_change: Optional[float] = None  # 同比变化

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "forecast_date": self.forecast_date.isoformat() if self.forecast_date else None,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "earnings_type": self.earnings_type,
            "earnings_range_low": float(self.earnings_range_low) if self.earnings_range_low else None,
            "earnings_range_high": float(self.earnings_range_high) if self.earnings_range_high else None,
            "yoy_change": self.yoy_change,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EarningsForecast":
        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            forecast_date=date.fromisoformat(data["forecast_date"]) if data.get("forecast_date") else date.today(),
            report_date=date.fromisoformat(data["report_date"]) if data.get("report_date") else date.today(),
            earnings_type=data.get("earnings_type", ""),
            earnings_range_low=Decimal(str(data["earnings_range_low"])) if data.get("earnings_range_low") else None,
            earnings_range_high=Decimal(str(data["earnings_range_high"])) if data.get("earnings_range_high") else None,
            yoy_change=data.get("yoy_change"),
        )


@dataclass
class CorporateAction:
    """重大事项

    记录上市公司的重大事项公告。
    """

    symbol: str  # 股票代码
    name: str  # 公司名称
    announcement_date: date  # 公告日期
    action_type: str  # 事项类型 (并购/重组/增减持/...)
    title: str  # 公告标题
    content: str = ""  # 摘要内容
    impact: str = ""  # 影响分析

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "announcement_date": self.announcement_date.isoformat() if self.announcement_date else None,
            "action_type": self.action_type,
            "title": self.title,
            "content": self.content,
            "impact": self.impact,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CorporateAction":
        return cls(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            announcement_date=date.fromisoformat(data["announcement_date"]) if data.get("announcement_date") else date.today(),
            action_type=data.get("action_type", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            impact=data.get("impact", ""),
        )


@dataclass
class PolicyEvent:
    """政策事件

    记录重大政策发布及其影响板块。
    """

    event_date: date  # 事件日期
    policy_title: str  # 政策标题
    related_sectors: List[str] = field(default_factory=list)  # 相关板块
    impact_level: str = "中性"  # 影响级别 (正面/中性/负面)
    keywords: List[str] = field(default_factory=list)  # 关键词

    def to_dict(self) -> Dict:
        return {
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "policy_title": self.policy_title,
            "related_sectors": self.related_sectors,
            "impact_level": self.impact_level,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyEvent":
        return cls(
            event_date=date.fromisoformat(data["event_date"]) if data.get("event_date") else date.today(),
            policy_title=data.get("policy_title", ""),
            related_sectors=data.get("related_sectors", []),
            impact_level=data.get("impact_level", "中性"),
            keywords=data.get("keywords", []),
        )
