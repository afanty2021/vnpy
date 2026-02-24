"""
测试过拟合检测器
"""
import pytest
from vnpy_china_optimize.overfit.detector import OverfitDetector
from vnpy_china_optimize.base.result import OptimizationMetrics


def mock_backtest_func(params, start_date, end_date):
    """模拟回测函数"""
    # 简单模拟：训练集表现好，测试集表现差
    if "2023-01" in start_date or "2023-06" in start_date:
        # 训练集
        return OptimizationMetrics(
            return_value=0.3,
            sharpe_ratio=2.0,
            max_drawdown=-0.1,
            win_rate=0.6,
            total_trades=50
        )
    else:
        # 测试集（表现差一些）
        return OptimizationMetrics(
            return_value=0.1,
            sharpe_ratio=0.8,
            max_drawdown=-0.15,
            win_rate=0.5,
            total_trades=30
        )


def test_out_sample_test():
    """测试样本外测试"""
    detector = OverfitDetector(
        backtest_func=mock_backtest_func,
        decay_threshold=0.5
    )

    result = detector.out_sample_test(
        params={"window": 20, "threshold": 0.02},
        train_start="2023-01-01",
        train_end="2023-06-30",
        test_start="2023-07-01",
        test_end="2023-12-31"
    )

    assert result.test_type == "out_sample"
    assert result.train_return == 0.3
    assert result.test_return == 0.1
    assert result.return_decay < 0.5  # 衰减超过50%
    assert result.is_overfit is True


def test_walk_forward_validation():
    """测试前向验证"""
    detector = OverfitDetector(
        backtest_func=mock_backtest_func
    )

    result = detector.walk_forward_validation(
        params={"window": 20},
        start_date="2023-01-01",
        end_date="2023-12-31",
        train_days=60,
        test_days=30,
        step_days=30
    )

    assert result.test_type == "walk_forward"
    assert 0 <= result.stability_score <= 1


def test_check_stability():
    """测试稳定性分析"""
    detector = OverfitDetector(
        backtest_func=mock_backtest_func
    )

    params_list = [
        {"window": 18},
        {"window": 20},
        {"window": 22},
    ]

    result = detector.check_stability(
        params_list=params_list,
        start_date="2023-01-01",
        end_date="2023-12-31",
        tolerance=0.5
    )

    assert "is_stable" in result
    assert "variance" in result
    assert "mean_return" in result


def test_risk_assessment():
    """测试风险评估"""
    # 低风险
    assert "low" in OverfitDetector(lambda *args: None)._assess_risk_level(0.9, 0.9)
    # 中风险
    assert "medium" in OverfitDetector(lambda *args: None)._assess_risk_level(0.6, 0.6)
    # 高风险
    assert "high" in OverfitDetector(lambda *args: None)._assess_risk_level(0.3, 0.3)


def test_empty_result():
    """测试空结果"""
    def failing_backtest(params, start, end):
        raise Exception("No data")

    detector = OverfitDetector(
        backtest_func=failing_backtest
    )

    result = detector.walk_forward_validation(
        params={},
        start_date="2023-01-01",
        end_date="2023-01-31",  # 时间太短，无法完成一次验证
        train_days=60,
        test_days=30
    )

    assert result.test_type == "walk_forward"
    assert result.is_overfit is True
    assert result.risk_level == "high"
