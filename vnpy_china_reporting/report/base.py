"""
报表生成器基类

定义报表生成的基本接口和通用方法。数据层对接 vnpy MainEngine 真实 API：
- 账户：main_engine.get_all_accounts()
- 持仓：main_engine.get_all_positions()
- 成交：main_engine.get_all_trades()

盈亏口径：权益变化法 pnl = 期末权益 - 期初权益。
vnpy 仅维护当前账户/持仓快照，不提供历史权益，故期初权益需由调用方传入；
期初权益缺失时当期盈亏记为 None（不伪造数据）。
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Dict, Optional, Any
import logging

from ..core.models import ReportData, TradeRecord, PositionRecord, AccountData, PositionSide
from ..core.enums import ReportType

logger = logging.getLogger(__name__)


class BaseReportGenerator(ABC):
    """
    报表生成器基类

    定义报表生成的基本接口和通用方法。
    所有报表生成器应继承此类，实现统一的接口。
    """

    def __init__(
        self,
        main_engine: Optional[Any] = None,
        equity_source: Optional[Any] = None,
        industry_source: Optional[Any] = None,
    ) -> None:
        """
        初始化报表生成器

        Args:
            main_engine: 主引擎实例，用于获取交易数据
            equity_source: 期初权益源（需有 get_latest_before(date) -> float），
                如 EquitySnapshotStore；注入后 generate_* 自动取上一交易日权益作期初
            industry_source: 行业映射源（需有 get_industry_map(symbols) -> dict），
                如 IndustryStore；注入后持仓自动填充行业
        """
        self.main_engine: Optional[Any] = main_engine
        self.equity_source: Optional[Any] = equity_source
        self.industry_source: Optional[Any] = industry_source
        self.data_cache: Dict[str, Any] = {}

    @abstractmethod
    def generate_daily(
        self,
        report_date: date,
        start_equity: Optional[float] = None
    ) -> ReportData:
        """
        生成日报数据

        Args:
            report_date: 报表日期
            start_equity: 期初权益。vnpy 不提供历史权益快照，权益变化法盈亏
                需调用方传入期初权益；为 None 时当期盈亏记为 None。

        Returns:
            报表数据对象
        """
        ...

    # ---- 盈亏计算（权益变化法） ----
    @staticmethod
    def calculate_pnl(
        start_equity: Optional[float],
        end_equity: Optional[float]
    ) -> Optional[float]:
        """权益变化法计算当期盈亏：pnl = end_equity - start_equity

        Args:
            start_equity: 期初总权益
            end_equity: 期末总权益

        Returns:
            盈亏金额；任一权益缺失则返回 None
        """
        if start_equity is None or end_equity is None:
            return None
        return end_equity - start_equity

    @staticmethod
    def calculate_pnl_ratio(
        pnl: Optional[float],
        start_equity: Optional[float]
    ) -> Optional[float]:
        """计算盈亏比例：pnl / start_equity"""
        if pnl is None or not start_equity:
            return None
        return pnl / start_equity

    def _resolve_start_equity(
        self,
        report_date: date,
        start_equity: Optional[float]
    ) -> Optional[float]:
        """解析期初权益：显式传入优先，否则从 equity_source 取上一交易日快照"""
        if start_equity is not None:
            return start_equity
        if self.equity_source is not None:
            try:
                return self.equity_source.get_latest_before(report_date)
            except Exception as e:
                logger.warning("从 equity_source 取期初权益失败: %s", e)
        return None

    @staticmethod
    def _fmt(value: Optional[float]) -> str:
        """格式化金额，None → 'N/A'"""
        return f"{value:.2f}" if value is not None else "N/A"

    @staticmethod
    def _fmt_pct(value: Optional[float]) -> str:
        """格式化百分比，None → 'N/A'"""
        return f"{value:.2%}" if value is not None else "N/A"

    # ---- 数据获取（对接 vnpy） ----
    def get_account(self) -> Optional[AccountData]:
        """获取当前账户数据（对接 vnpy get_all_accounts）

        Returns:
            账户数据；主引擎缺失或无账户时返回 None（不伪造数据）
        """
        if not self.main_engine:
            logger.warning("主引擎未注入，无法获取账户数据")
            return None

        try:
            accounts = self.main_engine.get_all_accounts()
        except Exception as e:
            logger.error(f"获取账户数据失败: {e}")
            return None

        if not accounts:
            logger.warning("当前无账户数据")
            return None

        acc = accounts[0]
        # 持仓市值与浮盈由持仓累加（vnpy AccountData 不含 position_value/pnl）
        positions = self.get_positions()
        market_value = sum(p.market_value for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)
        # A股 QMT 网关将真实可用现金放入 extra['cash']（见 patches/td.py）；
        # 原生 available=balance-frozen 在A股下≈总资产，不可用作可用现金。
        extra = getattr(acc, "extra", None) or {}

        return AccountData(
            total_equity=acc.balance,
            available_cash=extra.get("cash", acc.available),
            market_value=market_value,
            total_pnl=total_pnl,
            total_pnl_ratio=0.0,  # 权益变化法下当期收益率由 calculate_pnl_ratio 计算
            commission=0.0,       # vnpy TradeData 不含佣金字段
            timestamp=datetime.now(),
        )

    def get_positions(self) -> List[PositionRecord]:
        """获取当前持仓（对接 vnpy get_all_positions）

        盈亏直接采用网关推送的 PositionData.pnl（已按多空方向正确计算），
        从而规避本地按 (price-avg) 计算时做空方向取反的问题。
        """
        if not self.main_engine:
            return []

        try:
            positions = self.main_engine.get_all_positions()
        except Exception as e:
            logger.error(f"获取持仓数据失败: {e}")
            return []

        result: List[PositionRecord] = []
        for pos in positions:
            volume = getattr(pos, "volume", 0)
            if not volume:
                continue

            avg_cost = float(getattr(pos, "price", 0.0))
            pnl = float(getattr(pos, "pnl", 0.0))
            abs_vol = abs(volume)
            # vnpy PositionData 不含现价，由成本+盈亏反推，保证市值与盈亏自洽
            current_price = avg_cost + (pnl / abs_vol) if abs_vol else avg_cost
            side = self._map_side(getattr(pos, "direction", None))

            result.append(PositionRecord(
                symbol=pos.symbol,
                name=getattr(pos, "name", ""),  # vnpy PositionData 无 name 字段
                side=side,
                volume=abs_vol,
                avg_cost=avg_cost,
                current_price=current_price,
                market_value=current_price * abs_vol,
                unrealized_pnl=pnl,
                unrealized_pnl_ratio=(
                    pnl / (avg_cost * abs_vol) if avg_cost and abs_vol else 0.0
                ),
            ))
        self._fill_industry(result)
        return result

    def _fill_industry(self, positions: List[PositionRecord]) -> None:
        """从 industry_source 批量填充持仓行业"""
        if not self.industry_source or not positions:
            return
        try:
            industry_map = self.industry_source.get_industry_map(
                [p.symbol for p in positions]
            )
        except Exception as e:
            logger.warning("从 industry_source 取行业映射失败: %s", e)
            return
        for p in positions:
            ind = industry_map.get(p.symbol)
            if ind:
                p.industry = ind

    @staticmethod
    def _map_side(direction: Any) -> PositionSide:
        """vnpy Direction → PositionSide（用枚举名判定，避免 value 语言差异）"""
        name = getattr(direction, "name", "").upper()
        return PositionSide.SHORT if "SHORT" in name else PositionSide.LONG

    def get_trades(self, start_date: date, end_date: date) -> List[TradeRecord]:
        """获取指定日期范围的成交记录（对接 vnpy get_all_trades）

        vnpy TradeData 的 direction 为多空(LONG/SHORT)、offset 为开平，
        此处按 offset 将开仓记为 'buy'、平仓记为 'sell'（契合 A 股报表口径）。
        """
        if not self.main_engine:
            return []

        try:
            trades = self.main_engine.get_all_trades()
        except Exception as e:
            logger.error(f"获取成交数据失败: {e}")
            return []

        result: List[TradeRecord] = []
        for t in trades:
            t_dt = getattr(t, "datetime", None)
            if t_dt is None:
                continue
            trade_date = t_dt.date() if hasattr(t_dt, "date") else None
            if trade_date is None or not (start_date <= trade_date <= end_date):
                continue

            price = float(getattr(t, "price", 0.0))
            volume = int(getattr(t, "volume", 0))
            result.append(TradeRecord(
                trade_id=getattr(t, "vt_tradeid", "") or getattr(t, "tradeid", ""),
                symbol=t.symbol,
                direction=self._map_trade_direction(getattr(t, "offset", None)),
                volume=volume,
                price=price,
                amount=price * volume,
                commission=0.0,  # vnpy TradeData 不含佣金
                timestamp=t_dt,
            ))
        return result

    @staticmethod
    def _map_trade_direction(offset: Any) -> str:
        """vnpy Offset → 'buy'/'sell'（开仓买入、平仓卖出）"""
        name = getattr(offset, "name", "").upper()
        if "CLOSE" in name:
            return "sell"
        return "buy"

    def clear_cache(self) -> None:
        """清空数据缓存"""
        self.data_cache.clear()
