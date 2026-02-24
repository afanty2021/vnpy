"""
测试优化报告生成器
"""
import pytest
from vnpy_china_optimize.report.generator import OptimizationReportGenerator
from vnpy_china_optimize.base.result import (
    OptimizationSummary,
    OptimizationResult,
    OptimizationMetrics,
)
from vnpy_china_optimize.overfit.detector import OverfitTestResult


def create_mock_summary():
    """创建模拟的优化汇总"""
    metrics1 = OptimizationMetrics(
        return_value=0.25,
        sharpe_ratio=1.8,
        max_drawdown=-0.12,
        win_rate=0.55,
        total_trades=100
    )

    metrics2 = OptimizationMetrics(
        return_value=0.20,
        sharpe_ratio=1.5,
        max_drawdown=-0.15,
        win_rate=0.50,
        total_trades=80
    )

    result1 = OptimizationResult(
        params={"window": 20, "threshold": 0.02},
        metrics=metrics1
    )

    result2 = OptimizationResult(
        params={"window": 15, "threshold": 0.03},
        metrics=metrics2
    )

    return OptimizationSummary(
        total_evaluations=50,
        best_score=1.8,
        worst_score=0.5,
        avg_score=1.2,
        best_params={"window": 20, "threshold": 0.02},
        best_metrics=metrics1,
        all_results=[result1, result2]
    )


def test_generate_report():
    """测试报告生成"""
    generator = OptimizationReportGenerator()
    summary = create_mock_summary()

    report = generator.generate(summary)

    assert "策略参数优化报告" in report
    assert "总评估次数: 50" in report
    assert "最优分数: 1.8" in report
    assert "window: 20" in report


def test_generate_with_overfit():
    """测试包含过拟合检测的报告"""
    generator = OptimizationReportGenerator()
    summary = create_mock_summary()

    overfit_result = OverfitTestResult(
        test_type="out_sample",
        train_return=0.3,
        train_sharpe=2.0,
        test_return=0.1,
        test_sharpe=0.8,
        return_decay=0.33,
        sharpe_decay=0.4,
        stability_score=0.0,
        is_overfit=True,
        risk_level="high"
    )

    report = generator.generate(summary, overfit_result)

    assert "过拟合检测" in report
    assert "是否过拟合: 是" in report
    assert "风险等级: high" in report


def test_ranking_dataframe():
    """测试参数排名数据框"""
    generator = OptimizationReportGenerator()
    summary = create_mock_summary()
    generator.summary = summary  # 设置summary

    data = generator.generate_ranking_dataframe()

    assert len(data) > 0
    assert "rank" in data[0]
    assert "score" in data[0]
    assert "window" in data[0]


def test_sensitivity_data():
    """测试敏感性分析数据"""
    generator = OptimizationReportGenerator()
    summary = create_mock_summary()
    generator.summary = summary  # 设置summary

    sensitivity = generator.generate_sensitivity_data()

    assert "window" in sensitivity
    assert "threshold" in sensitivity


def test_export_to_txt(tmp_path):
    """测试导出为文本文件"""
    generator = OptimizationReportGenerator()
    summary = create_mock_summary()
    generator.summary = summary  # 设置summary

    filepath = tmp_path / "report.txt"
    generator.export_to_txt(str(filepath))

    assert filepath.exists()
    content = filepath.read_text(encoding='utf-8')
    assert "策略参数优化报告" in content


def test_export_to_markdown(tmp_path):
    """测试导出为Markdown文件"""
    generator = OptimizationReportGenerator()
    summary = create_mock_summary()
    generator.summary = summary  # 设置summary

    filepath = tmp_path / "report.md"
    generator.export_to_markdown(str(filepath))

    assert filepath.exists()
    content = filepath.read_text(encoding='utf-8')
    assert "策略参数优化报告" in content
