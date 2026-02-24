"""
风险分析器测试
"""

import pytest
import numpy as np
from vnpy_china_reporting.analysis.risk import RiskAnalyzer
from vnpy_china_reporting.core.models import PositionRecord, RiskMetrics
from vnpy_china_reporting.core.enums import PositionSide, RiskLevel


def create_mock_positions():
    """创建模拟持仓数据"""
    return [
        PositionRecord(
            symbol="000001",
            name="平安银行",
            side=PositionSide.LONG,
            volume=10000,
            avg_cost=12.5,
            current_price=13.0,
            market_value=130000,
            unrealized_pnl=5000,
            unrealized_pnl_ratio=0.04
        ),
        PositionRecord(
            symbol="600519",
            name="贵州茅台",
            side=PositionSide.LONG,
            volume=200,
            avg_cost=1800.0,
            current_price=2000.0,
            market_value=400000,
            unrealized_pnl=40000,
            unrealized_pnl_ratio=0.111
        ),
    ]


def test_risk_analyzer_init():
    """测试风险分析器初始化"""
    analyzer = RiskAnalyzer()
    assert analyzer is not None


def test_calculate_var():
    """测试VaR计算"""
    analyzer = RiskAnalyzer()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    var_95 = analyzer.calculate_var(returns, 0.95)

    assert isinstance(var_95, float)
    assert var_95 <= 0  # VaR应该是负数（损失）


def test_calculate_var_empty():
    """测试空VaR计算"""
    analyzer = RiskAnalyzer()

    var_95 = analyzer.calculate_var([], 0.95)

    assert var_95 == 0.0


def test_calculate_cvar():
    """测试CVaR计算"""
    analyzer = RiskAnalyzer()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    cvar_95 = analyzer.calculate_cvar(returns, 0.95)

    assert isinstance(cvar_95, float)
    assert cvar_95 <= 0  # CVaR应该是负数


def test_calculate_cvar_empty():
    """测试空CVaR计算"""
    analyzer = RiskAnalyzer()

    cvar_95 = analyzer.calculate_cvar([], 0.95)

    assert cvar_95 == 0.0


def test_calculate_volatility():
    """测试波动率计算"""
    analyzer = RiskAnalyzer()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    vol = analyzer.calculate_volatility(returns, annualize=True)

    assert isinstance(vol, float)
    assert vol >= 0


def test_calculate_volatility_empty():
    """测试空波动率计算"""
    analyzer = RiskAnalyzer()

    vol = analyzer.calculate_volatility([], annualize=True)

    assert vol == 0.0


def test_calculate_sharpe_ratio():
    """测试夏普比率计算"""
    analyzer = RiskAnalyzer()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    sharpe = analyzer.calculate_sharpe_ratio(returns, 0.03)

    assert isinstance(sharpe, float)


def test_calculate_sharpe_ratio_empty():
    """测试空夏普比率计算"""
    analyzer = RiskAnalyzer()

    sharpe = analyzer.calculate_sharpe_ratio([], 0.03)

    assert sharpe == 0.0


def test_calculate_sortino_ratio():
    """测试索提诺比率计算"""
    analyzer = RiskAnalyzer()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    sortino = analyzer.calculate_sortino_ratio(returns, 0.03)

    assert isinstance(sortino, float)


def test_calculate_sortino_ratio_empty():
    """测试空索提诺比率计算"""
    analyzer = RiskAnalyzer()

    sortino = analyzer.calculate_sortino_ratio([], 0.03)

    assert sortino == 0.0


def test_calculate_max_drawdown():
    """测试最大回撤计算"""
    analyzer = RiskAnalyzer()
    equity_curve = [100000, 105000, 103000, 108000, 102000, 110000, 107000, 112000]

    max_dd = analyzer.calculate_max_drawdown(equity_curve)

    assert isinstance(max_dd, float)
    assert 0 <= max_dd <= 1


def test_calculate_max_drawdown_empty():
    """测试空最大回撤计算"""
    analyzer = RiskAnalyzer()

    max_dd = analyzer.calculate_max_drawdown([])

    assert max_dd == 0.0


def test_calculate_max_drawdown_no_drawdown():
    """测试无回撤情况"""
    analyzer = RiskAnalyzer()
    equity_curve = [100000, 105000, 110000, 115000, 120000]

    max_dd = analyzer.calculate_max_drawdown(equity_curve)

    assert max_dd == 0.0


def test_calculate_calmar_ratio():
    """测试卡玛比率计算"""
    analyzer = RiskAnalyzer()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02]

    calmar = analyzer.calculate_calmar_ratio(returns, 0.1)

    assert isinstance(calmar, float)


def test_calculate_calmar_ratio_empty():
    """测试空卡玛比率计算"""
    analyzer = RiskAnalyzer()

    calmar = analyzer.calculate_calmar_ratio([], 0.1)

    assert calmar == 0.0


def test_calculate_risk_level():
    """测试风险等级计算"""
    analyzer = RiskAnalyzer()

    # 低风险
    level_low = analyzer.calculate_risk_level(0.05, 0.05)
    assert level_low == RiskLevel.LOW

    # 中风险
    level_medium = analyzer.calculate_risk_level(0.2, 0.2)
    assert level_medium == RiskLevel.MEDIUM

    # 高风险
    level_high = analyzer.calculate_risk_level(0.35, 0.35)
    assert level_high == RiskLevel.HIGH


def test_analyze():
    """测试综合风险分析"""
    analyzer = RiskAnalyzer()
    positions = create_mock_positions()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    result = analyzer.analyze(positions, returns)

    assert isinstance(result, RiskMetrics)
    assert isinstance(result.var_95, float)
    assert isinstance(result.volatility, float)
    assert isinstance(result.sharpe_ratio, float)
    assert isinstance(result.max_drawdown, float)
    assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]


def test_calculate_position_risk():
    """测试持仓风险计算"""
    analyzer = RiskAnalyzer()
    positions = create_mock_positions()

    result = analyzer.calculate_position_risk(positions)

    assert isinstance(result, list)
    assert len(result) == 2
    assert "symbol" in result[0]
    assert "weight" in result[0]


def test_get_risk_summary():
    """测试风险摘要"""
    analyzer = RiskAnalyzer()
    positions = create_mock_positions()
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, -0.015, 0.01, -0.02]

    summary = analyzer.get_risk_summary(positions, returns)

    assert "var_95" in summary
    assert "volatility" in summary
    assert "sharpe_ratio" in summary
    assert "max_drawdown" in summary
    assert "risk_level" in summary
    assert summary["position_count"] == 2


def test_get_risk_summary_empty():
    """测试空风险摘要"""
    analyzer = RiskAnalyzer()

    summary = analyzer.get_risk_summary([], [])

    assert summary["var_95"] == 0.0
    assert summary["volatility"] == 0.0
    assert summary["risk_level"] == RiskLevel.LOW.value
