"""
风险分析器模块

提供VaR、波动率、夏普比率、最大回撤等风险指标计算功能。
"""

from typing import List, Dict, Optional
import numpy as np
from ..core.models import PositionRecord, RiskMetrics
from ..core.enums import RiskLevel


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

    @staticmethod
    def _returns_to_equity(returns: List[float]) -> List[float]:
        """收益率序列 → 归一化权益曲线（初始为1，cumprod(1+r)）

        calculate_max_drawdown 要求资金曲线而非收益率序列，调用前需先转换。
        """
        if not returns:
            return []
        arr = np.array(returns, dtype=float)
        return np.cumprod(1.0 + arr).tolist()

    def calculate_calmar_ratio(
        self,
        returns: List[float],
        max_drawdown: float
    ) -> float:
        """
        计算卡玛比率

        Args:
            returns: 收益率序列
            max_drawdown: 最大回撤

        Returns:
            卡玛比率
        """
        if not returns or max_drawdown == 0:
            return 0.0

        annual_return = np.mean(returns) * 252
        calmar = annual_return / max_drawdown

        return float(calmar)

    def calculate_risk_level(
        self,
        volatility: float,
        max_drawdown: float
    ) -> RiskLevel:
        """
        计算风险等级

        Args:
            volatility: 波动率
            max_drawdown: 最大回撤

        Returns:
            风险等级
        """
        # 基于波动率和最大回撤判断风险等级
        if volatility < 0.1 and max_drawdown < 0.1:
            return RiskLevel.LOW
        elif volatility > 0.3 or max_drawdown > 0.3:
            return RiskLevel.HIGH
        else:
            return RiskLevel.MEDIUM

    def analyze(
        self,
        positions: List[PositionRecord],
        history_returns: List[float]
    ) -> RiskMetrics:
        """
        综合风险分析

        Args:
            positions: 当前持仓
            history_returns: 历史收益率序列

        Returns:
            RiskMetrics对象
        """
        # 组合风险指标
        portfolio_vol = self.calculate_volatility(history_returns)
        portfolio_var_95 = self.calculate_var(history_returns, 0.95)
        max_dd = self.calculate_max_drawdown(self._returns_to_equity(history_returns))

        # 收益指标
        sharpe = self.calculate_sharpe_ratio(history_returns)
        risk_level = self.calculate_risk_level(portfolio_vol, max_dd)

        return RiskMetrics(
            var_95=portfolio_var_95,
            volatility=portfolio_vol,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            risk_level=risk_level
        )

    def calculate_position_risk(
        self,
        positions: List[PositionRecord]
    ) -> List[Dict]:
        """
        计算各持仓的风险指标

        Args:
            positions: 持仓列表

        Returns:
            持仓风险列表
        """
        if not positions:
            return []

        total_value = sum(p.market_value for p in positions)
        position_risks: List[Dict] = []

        for pos in positions:
            weight = pos.market_value / total_value if total_value > 0 else 0.0

            position_risks.append({
                "symbol": pos.symbol,
                "name": pos.name,
                "weight": weight,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_ratio": pos.unrealized_pnl_ratio,
                "risk_contribution": weight * abs(pos.unrealized_pnl_ratio)
            })

        return position_risks

    def get_risk_summary(
        self,
        positions: List[PositionRecord],
        returns: List[float]
    ) -> Dict:
        """
        获取风险摘要

        Args:
            positions: 持仓列表
            returns: 收益率序列

        Returns:
            风险摘要字典
        """
        if not returns:
            return {
                "var_95": 0.0,
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "risk_level": RiskLevel.LOW.value
            }

        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        volatility = self.calculate_volatility(returns)
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        max_dd = self.calculate_max_drawdown(self._returns_to_equity(returns))
        calmar = self.calculate_calmar_ratio(returns, max_dd)
        risk_level = self.calculate_risk_level(volatility, max_dd)

        return {
            "var_95": var_95,
            "var_99": var_99,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_dd,
            "calmar_ratio": calmar,
            "risk_level": risk_level.value,
            "position_count": len(positions),
            "position_risks": self.calculate_position_risk(positions)
        }
