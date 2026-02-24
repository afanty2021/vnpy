"""
优化报告生成器

生成参数优化报告，包括参数排名、敏感性分析等。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
from io import StringIO

from ..base.result import OptimizationSummary, OptimizationResult
from ..overfit.detector import OverfitTestResult


class OptimizationReportGenerator:
    """
    优化报告生成器

    生成详细的优化报告，包括：
    - 参数排名
    - 敏感性分析
    - 统计摘要
    """

    def __init__(self) -> None:
        """初始化报告生成器"""
        self.summary: Optional[OptimizationSummary] = None
        self.overfit_result: Optional[OverfitTestResult] = None

    def generate(
        self,
        summary: OptimizationSummary,
        overfit_result: Optional[OverfitTestResult] = None
    ) -> str:
        """
        生成优化报告

        Args:
            summary: 优化汇总结果
            overfit_result: 过拟合检测结果

        Returns:
            报告文本
        """
        self.summary = summary
        self.overfit_result = overfit_result

        report = StringIO()

        # 标题
        report.write("=" * 60 + "\n")
        report.write(" " * 15 + "策略参数优化报告\n")
        report.write("=" * 60 + "\n\n")

        # 生成时间
        report.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 一、优化结果统计
        self._write_summary_section(report)

        # 二、最优参数
        self._write_best_params_section(report)

        # 三、参数排名
        self._write_ranking_section(report)

        # 四、敏感性分析
        self._write_sensitivity_section(report)

        # 五、过拟合检测
        if overfit_result:
            self._write_overfit_section(report)

        # 结束
        report.write("\n" + "=" * 60 + "\n")

        return report.getvalue()

    def _write_summary_section(self, report: StringIO) -> None:
        """写入摘要部分"""
        report.write("一、优化结果统计\n")
        report.write("-" * 40 + "\n")
        report.write(f"总评估次数: {self.summary.total_evaluations}\n")
        report.write(f"最优分数: {self.summary.best_score:.4f}\n")
        report.write(f"最差分数: {self.summary.worst_score:.4f}\n")
        report.write(f"平均分数: {self.summary.avg_score:.4f}\n")
        report.write(f"分数标准差: {self._calculate_std():.4f}\n\n")

        # 最优指标
        m = self.summary.best_metrics
        report.write("最优参数指标:\n")
        report.write(f"  收益率: {m.return_value:.2%}\n")
        report.write(f"  夏普比率: {m.sharpe_ratio:.2f}\n")
        report.write(f"  最大回撤: {m.max_drawdown:.2%}\n")
        report.write(f"  胜率: {m.win_rate:.2%}\n")
        report.write(f"  交易次数: {m.total_trades}\n\n")

    def _write_best_params_section(self, report: StringIO) -> None:
        """写入最优参数部分"""
        report.write("二、最优参数\n")
        report.write("-" * 40 + "\n")
        for param, value in self.summary.best_params.items():
            if isinstance(value, float):
                report.write(f"{param}: {value:.4f}\n")
            else:
                report.write(f"{param}: {value}\n")
        report.write("\n")

    def _write_ranking_section(self, report: StringIO) -> None:
        """写入参数排名部分"""
        report.write("三、Top 10 参数组合\n")
        report.write("-" * 40 + "\n")

        top_results = self.summary.get_top_n(10)

        for i, result in enumerate(top_results, 1):
            report.write(f"\n#{i} 分数: {result.score:.4f}\n")
            for param, value in result.params.items():
                if isinstance(value, float):
                    report.write(f"  {param}: {value:.4f}\n")
                else:
                    report.write(f"  {param}: {value}\n")

        report.write("\n")

    def _write_sensitivity_section(self, report: StringIO) -> None:
        """写入敏感性分析部分"""
        report.write("四、参数敏感性分析\n")
        report.write("-" * 40 + "\n")

        # 获取第一个参数名
        if self.summary.best_params:
            param_names = list(self.summary.best_params.keys())

            for param_name in param_names:
                ranking = self.summary.get_parameter_ranking(param_name)

                if ranking:
                    # 按分数排序
                    sorted_ranking = sorted(
                        ranking.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    report.write(f"\n参数: {param_name}\n")

                    for value, avg_score in sorted_ranking[:5]:  # 只显示前5
                        if isinstance(value, float):
                            report.write(f"  {value:.4f}: {avg_score:.4f}\n")
                        else:
                            report.write(f"  {value}: {avg_score:.4f}\n")

        report.write("\n")

    def _write_overfit_section(self, report: StringIO) -> None:
        """写入过拟合检测部分"""
        report.write("五、过拟合检测\n")
        report.write("-" * 40 + "\n")

        if not self.overfit_result:
            report.write("未进行过拟合检测\n")
            return

        r = self.overfit_result

        report.write(f"测试类型: {r.test_type}\n")
        report.write(f"\n训练集指标:\n")
        report.write(f"  收益率: {r.train_return:.2%}\n")
        report.write(f"  夏普比率: {r.train_sharpe:.2f}\n")

        report.write(f"\n测试集指标:\n")
        report.write(f"  收益率: {r.test_return:.2%}\n")
        report.write(f"  夏普比率: {r.test_sharpe:.2f}\n")

        report.write(f"\n衰减分析:\n")
        report.write(f"  收益率衰减: {r.return_decay:.2%}\n")
        report.write(f"  夏普比率衰减: {r.sharpe_decay:.2%}\n")

        if r.stability_score > 0:
            report.write(f"  稳定性评分: {r.stability_score:.2f}\n")

        report.write(f"\n风险评估:\n")
        report.write(f"  是否过拟合: {'是' if r.is_overfit else '否'}\n")
        report.write(f"  风险等级: {r.risk_level}\n")

        # 建议
        report.write(f"\n建议:\n")
        if r.is_overfit:
            report.write("  ⚠️ 检测到过拟合风险！建议:\n")
            report.write("  1. 减少参数数量\n")
            report.write("  2. 增加训练数据\n")
            report.write("  3. 使用正则化\n")
            report.write("  4. 在样本外数据上验证\n")
        else:
            report.write("  ✅ 未检测到明显过拟合\n")

        report.write("\n")

    def _calculate_std(self) -> float:
        """计算分数标准差"""
        if not self.summary.all_results:
            return 0.0

        scores = [r.score for r in self.summary.all_results]
        return np.std(scores)

    def generate_ranking_dataframe(self) -> List[Dict[str, Any]]:
        """
        生成参数排名数据框

        Returns:
            可转换为DataFrame的字典列表
        """
        if not self.summary:
            return []

        top_results = self.summary.get_top_n(20)

        data = []
        for i, result in enumerate(top_results, 1):
            row = {
                "rank": i,
                "score": result.score,
                "return": result.metrics.return_value,
                "sharpe": result.metrics.sharpe_ratio,
                "max_drawdown": result.metrics.max_drawdown,
            }
            row.update(result.params)
            data.append(row)

        return data

    def generate_sensitivity_data(self) -> Dict[str, Dict[Any, float]]:
        """
        生成敏感性分析数据

        Returns:
            参数敏感性字典
        """
        if not self.summary or not self.summary.best_params:
            return {}

        sensitivity_data = {}

        for param_name in self.summary.best_params.keys():
            ranking = self.summary.get_parameter_ranking(param_name)
            if ranking:
                sensitivity_data[param_name] = ranking

        return sensitivity_data

    def export_to_markdown(self, filepath: str) -> None:
        """
        导出报告为Markdown文件

        Args:
            filepath: 文件路径
        """
        report = self.generate(self.summary, self.overfit_result)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

    def export_to_txt(self, filepath: str) -> None:
        """
        导出报告为文本文件

        Args:
            filepath: 文件路径
        """
        report = self.generate(self.summary, self.overfit_result)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
