"""
策略分析器测试
"""

import pytest
from datetime import datetime
from vnpy_china_reporting.analysis.strategy import StrategyAnalyzer
from vnpy_china_reporting.core.models import TradeRecord


def create_mock_trades():
    """创建模拟交易数据"""
    return [
        TradeRecord(
            trade_id="T001",
            symbol="000001",
            direction="buy",
            volume=1000,
            price=10.0,
            amount=10000.0,
            commission=10.0,
            timestamp=datetime(2025, 1, 10, 10, 0, 0)
        ),
        TradeRecord(
            trade_id="T002",
            symbol="000001",
            direction="sell",
            volume=1000,
            price=11.0,
            amount=11000.0,
            commission=11.0,
            timestamp=datetime(2025, 1, 15, 14, 0, 0)
        ),
        TradeRecord(
            trade_id="T003",
            symbol="600000",
            direction="buy",
            volume=2000,
            price=5.0,
            amount=10000.0,
            commission=10.0,
            timestamp=datetime(2025, 1, 20, 10, 0, 0)
        ),
        TradeRecord(
            trade_id="T004",
            symbol="600000",
            direction="sell",
            volume=2000,
            price=4.5,
            amount=9000.0,
            commission=9.0,
            timestamp=datetime(2025, 1, 25, 14, 0, 0)
        ),
    ]


def create_mock_trades_mixed():
    """创建混合盈亏的交易数据"""
    return [
        TradeRecord(
            trade_id="T001",
            symbol="000001",
            direction="buy",
            volume=1000,
            price=10.0,
            amount=10000.0,
            commission=10.0,
            timestamp=datetime(2025, 1, 10, 10, 0, 0)
        ),
        TradeRecord(
            trade_id="T002",
            symbol="000001",
            direction="sell",
            volume=1000,
            price=12.0,
            amount=12000.0,
            commission=12.0,
            timestamp=datetime(2025, 1, 15, 14, 0, 0)
        ),
        TradeRecord(
            trade_id="T003",
            symbol="600000",
            direction="buy",
            volume=2000,
            price=5.0,
            amount=10000.0,
            commission=10.0,
            timestamp=datetime(2025, 1, 20, 10, 0, 0)
        ),
        TradeRecord(
            trade_id="T004",
            symbol="600000",
            direction="sell",
            volume=2000,
            price=4.0,
            amount=8000.0,
            commission=8.0,
            timestamp=datetime(2025, 1, 25, 14, 0, 0)
        ),
    ]


def test_strategy_analyzer_init():
    """测试策略分析器初始化"""
    analyzer = StrategyAnalyzer()
    assert analyzer is not None


def test_calculate_win_rate():
    """测试胜率计算"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    win_rate = analyzer.calculate_win_rate(trades)

    assert isinstance(win_rate, float)
    assert 0 <= win_rate <= 1


def test_calculate_win_rate_empty():
    """测试空胜率计算"""
    analyzer = StrategyAnalyzer()

    win_rate = analyzer.calculate_win_rate([])

    assert win_rate == 0.0


def test_calculate_profit_loss_ratio():
    """测试盈亏比计算"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    ratio = analyzer.calculate_profit_loss_ratio(trades)

    assert isinstance(ratio, float)
    assert ratio >= 0


def test_calculate_profit_loss_ratio_empty():
    """测试空盈亏比计算"""
    analyzer = StrategyAnalyzer()

    ratio = analyzer.calculate_profit_loss_ratio([])

    assert ratio == 0.0


def test_calculate_summary():
    """测试策略摘要计算"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    summary = analyzer.calculate_summary(trades)

    assert summary["total_trades"] == 4
    assert "win_rate" in summary
    assert "profit_loss_ratio" in summary
    assert "total_pnl" in summary
    assert "total_commission" in summary


def test_calculate_summary_empty():
    """测试空策略摘要"""
    analyzer = StrategyAnalyzer()

    summary = analyzer.calculate_summary([])

    assert summary["total_trades"] == 0
    assert summary["win_rate"] == 0.0


def test_analyze_performance():
    """测试策略表现分析"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    result = analyzer.analyze_performance(trades)

    assert "total_trades" in result
    assert "paired_trades" in result
    assert "win_rate" in result
    assert "avg_return" in result
    assert "total_return" in result


def test_analyze_performance_empty():
    """测试空策略表现分析"""
    analyzer = StrategyAnalyzer()

    result = analyzer.analyze_performance([])

    assert result["total_trades"] == 0
    assert result["paired_trades"] == 0


def test_pair_trades():
    """测试配对交易"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    returns = analyzer._pair_trades(trades)

    assert isinstance(returns, list)
    assert len(returns) > 0


def test_pair_trades_empty():
    """测试空配对交易"""
    analyzer = StrategyAnalyzer()

    returns = analyzer._pair_trades([])

    assert returns == []


def test_analyze_by_month():
    """测试按月分析"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    result = analyzer.analyze_by_month(trades)

    assert isinstance(result, dict)
    # 应该包含2025-01这个月
    assert "2025-01" in result


def test_analyze_by_symbol():
    """测试按股票分析"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    result = analyzer.analyze_by_symbol(trades)

    assert isinstance(result, dict)
    assert "000001" in result
    assert "600000" in result


def test_compare_strategies():
    """测试策略对比"""
    analyzer = StrategyAnalyzer()
    strategies = {
        "策略A": create_mock_trades(),
        "策略B": create_mock_trades_mixed()
    }

    result = analyzer.compare_strategies(strategies)

    assert isinstance(result, dict)
    assert "策略A" in result
    assert "策略B" in result


def test_compare_strategies_empty():
    """测试空策略对比"""
    analyzer = StrategyAnalyzer()

    result = analyzer.compare_strategies({})

    assert result == {}


def test_get_trading_summary():
    """测试交易汇总"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades()

    summary = analyzer.get_trading_summary(trades)

    assert summary["total_trades"] == 4
    assert summary["buy_trades"] == 2
    assert summary["sell_trades"] == 2
    assert summary["total_volume"] > 0
    assert summary["total_amount"] > 0
    assert summary["total_commission"] > 0


def test_get_trading_summary_empty():
    """测试空交易汇总"""
    analyzer = StrategyAnalyzer()

    summary = analyzer.get_trading_summary([])

    assert summary["total_trades"] == 0
    assert summary["buy_trades"] == 0
    assert summary["sell_trades"] == 0
    assert summary["total_volume"] == 0
    assert summary["total_amount"] == 0.0


def test_analyze_performance_win_loss():
    """测试有盈亏的表现分析"""
    analyzer = StrategyAnalyzer()
    trades = create_mock_trades_mixed()

    result = analyzer.analyze_performance(trades)

    # 验证有配对交易
    assert result["paired_trades"] == 2
    # 一胜一负，总收益为0
    assert result["total_return"] == 0
