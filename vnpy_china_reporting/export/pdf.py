"""
PDF导出器

将报表数据导出为PDF格式。
"""

from __future__ import annotations

from typing import List, Optional, Any
from datetime import date, datetime

from ..core.models import ReportData, PositionAnalysis, PositionRecord


class PDFExporter:
    """
    PDF导出器

    将报表数据导出为PDF文件，支持日报、月报、持仓分析等格式。
    """

    def __init__(self) -> None:
        """初始化PDF导出器"""
        self.page_size: str = "A4"
        self.orientation: str = "portrait"

        # 尝试导入reportlab
        self._reportlab_available: bool = False
        self._pdfmetrics: Any = None
        self._TTFont: Any = None
        self._colors: Any = None
        self._A4: Any = None
        self._cm: Any = None
        self._SimpleDocTemplate: Any = None
        self._Table: Any = None
        self._TableStyle: Any = None
        self._Paragraph: Any = None
        self._Spacer: Any = None
        self._getSampleStyleSheet: Any = None
        self._ParagraphStyle: Any = None
        self._try_import_reportlab()

    def _try_import_reportlab(self) -> None:
        """尝试导入reportlab库"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            self._reportlab_available = True
            self._colors = colors
            self._A4 = A4
            self._cm = cm
            self._SimpleDocTemplate = SimpleDocTemplate
            self._Table = Table
            self._TableStyle = TableStyle
            self._Paragraph = Paragraph
            self._Spacer = Spacer
            self._getSampleStyleSheet = getSampleStyleSheet
            self._ParagraphStyle = ParagraphStyle
            self._pdfmetrics = pdfmetrics
            self._TTFont = TTFont

            # 尝试注册中文字体
            self._register_chinese_fonts()

        except ImportError:
            print("警告: reportlab库未安装，PDF导出功能不可用")
            print("请使用 pip install reportlab 安装")

    def _register_chinese_fonts(self) -> None:
        """注册中文字体"""
        if not self._reportlab_available:
            return

        try:
            # 尝试注册常见中文字体
            import os
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Windows常见字体路径
            font_paths = [
                'C:/Windows/Fonts/simsun.ttc',  # 宋体
                'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_name = os.path.splitext(os.path.basename(font_path))[0]
                    try:
                        self._pdfmetrics.registerFont(TTFont(font_name, font_path))
                    except:
                        pass

        except Exception as e:
            print(f"字体注册警告: {e}")

    def _check_reportlab(self) -> bool:
        """检查reportlab是否可用"""
        if not self._reportlab_available:
            return False
        # 验证所有必要的属性都已初始化
        return (
            self._colors is not None
            and self._A4 is not None
            and self._cm is not None
            and self._SimpleDocTemplate is not None
            and self._Table is not None
            and self._TableStyle is not None
            and self._Paragraph is not None
            and self._Spacer is not None
            and self._getSampleStyleSheet is not None
            and self._ParagraphStyle is not None
        )

    def export_daily_report(
        self,
        report: ReportData,
        filepath: str
    ) -> bool:
        """
        导出日报为PDF文件

        Args:
            report: 报表数据对象
            filepath: 导出文件路径

        Returns:
            是否导出成功
        """
        if not self._reportlab_available:
            return self._export_daily_report_fallback(report, filepath)

        try:
            doc = self._SimpleDocTemplate(
                filepath,
                pagesize=self._A4,
                rightMargin=2 * self._cm,
                leftMargin=2 * self._cm,
                topMargin=2 * self._cm,
                bottomMargin=2 * self._cm
            )

            elements = []

            # 标题
            title_style = self._ParagraphStyle(
                'CustomTitle',
                parent=self._getSampleStyleSheet()['Heading1'],
                fontSize=18,
                textColor=self._colors.HexColor('#4472C4'),
                alignment=1  # 居中
            )
            elements.append(self._Paragraph(
                f"每日交易报告 - {report.start_date}",
                title_style
            ))
            elements.append(self._Spacer(1, 1 * self._cm))

            # 资金情况
            if report.account:
                account_data = [
                    ["总权益", f"{report.account.total_equity:.2f}"],
                    ["可用资金", f"{report.account.available_cash:.2f}"],
                    ["持仓市值", f"{report.account.market_value:.2f}"],
                    ["总盈亏", f"{report.account.total_pnl:.2f}"],
                    ["盈亏比例", f"{report.account.total_pnl_ratio:.2%}"]
                ]
                elements.extend(self._create_section("资金情况", account_data))

            # 当期盈亏
            pnl_data = [
                ["当日盈亏", f"{report.daily_pnl:.2f}" if report.daily_pnl is not None else "N/A"],
                ["盈亏比例", f"{report.daily_pnl_ratio:.2%}" if report.daily_pnl_ratio is not None else "N/A"]
            ]
            elements.extend(self._create_section("当日盈亏", pnl_data))

            # 交易统计
            if report.trades:
                buy_count = sum(1 for t in report.trades if t.direction == "buy")
                sell_count = sum(1 for t in report.trades if t.direction == "sell")
                total_amount = sum(t.amount for t in report.trades)

                trade_data = [
                    ["总成交笔数", str(len(report.trades))],
                    ["买入笔数", str(buy_count)],
                    ["卖出笔数", str(sell_count)],
                    ["总成交金额", f"{total_amount:.2f}"]
                ]
                elements.extend(self._create_section("交易统计", trade_data))

            # 持仓明细
            if report.positions:
                elements.extend(self._create_position_table(report.positions))

            doc.build(elements)
            return True

        except Exception as e:
            print(f"导出PDF日报失败: {e}")
            return False

    def export_monthly_report(
        self,
        report: ReportData,
        filepath: str
    ) -> bool:
        """
        导出月报为PDF文件

        Args:
            report: 报表数据对象
            filepath: 导出文件路径

        Returns:
            是否导出成功
        """
        if not self._reportlab_available:
            return self._export_monthly_report_fallback(report, filepath)

        try:
            doc = self._SimpleDocTemplate(
                filepath,
                pagesize=self._A4,
                rightMargin=2 * self._cm,
                leftMargin=2 * self._cm,
                topMargin=2 * self._cm,
                bottomMargin=2 * self._cm
            )

            elements = []

            # 标题
            title_style = self._ParagraphStyle(
                'CustomTitle',
                parent=self._getSampleStyleSheet()['Heading1'],
                fontSize=18,
                textColor=self._colors.HexColor('#4472C4'),
                alignment=1
            )
            month_text = f"{report.start_date.year}年{report.start_date.month:02d}月交易报告"
            elements.append(self._Paragraph(month_text, title_style))
            elements.append(self._Spacer(1, 1 * self._cm))

            # 资金情况
            if report.account:
                account_data = [
                    ["期末资金", f"{report.account.total_equity:.2f}"],
                    ["可用资金", f"{report.account.available_cash:.2f}"],
                    ["持仓市值", f"{report.account.market_value:.2f}"]
                ]
                elements.extend(self._create_section("账户概况", account_data))

            # 月度盈亏
            pnl_data = [
                ["月度盈亏", f"{report.daily_pnl:.2f}" if report.daily_pnl is not None else "N/A"],
                ["盈亏比例", f"{report.daily_pnl_ratio:.2%}" if report.daily_pnl_ratio is not None else "N/A"]
            ]
            elements.extend(self._create_section("月度盈亏", pnl_data))

            # 持仓明细
            if report.positions:
                elements.extend(self._create_position_table(report.positions))

            doc.build(elements)
            return True

        except Exception as e:
            print(f"导出PDF月报失败: {e}")
            return False

    def export_position_analysis(
        self,
        analysis: PositionAnalysis,
        filepath: str
    ) -> bool:
        """
        导出持仓分析为PDF文件

        Args:
            analysis: 持仓分析数据对象
            filepath: 导出文件路径

        Returns:
            是否导出成功
        """
        if not self._reportlab_available:
            return self._export_position_analysis_fallback(analysis, filepath)

        try:
            doc = self._SimpleDocTemplate(
                filepath,
                pagesize=self._A4,
                rightMargin=2 * self._cm,
                leftMargin=2 * self._cm,
                topMargin=2 * self._cm,
                bottomMargin=2 * self._cm
            )

            elements = []

            # 标题
            title_style = self._ParagraphStyle(
                'CustomTitle',
                parent=self._getSampleStyleSheet()['Heading1'],
                fontSize=18,
                textColor=self._colors.HexColor('#4472C4'),
                alignment=1
            )
            elements.append(self._Paragraph("持仓分析报告", title_style))
            elements.append(self._Spacer(1, 1 * self._cm))

            # 总体统计
            summary_data = [
                ["持仓数量", str(analysis.total_positions)],
                ["总市值", f"{analysis.total_market_value:.2f}"],
                ["集中度", f"{analysis.concentration:.2%}"]
            ]
            elements.extend(self._create_section("总体统计", summary_data))

            # 行业分布
            if analysis.industry_distribution:
                elements.extend(
                    self._create_industry_table(analysis.industry_distribution)
                )

            doc.build(elements)
            return True

        except Exception as e:
            print(f"导出PDF持仓分析失败: {e}")
            return False

    def _create_section(
        self,
        title: str,
        data: List[List]
    ) -> List:
        """
        创建一个数据区块

        Args:
            title: 区块标题
            data: 数据列表 [[label, value], ...]

        Returns:
            元素列表
        """
        elements = []

        # 标题样式
        title_style = self._ParagraphStyle(
            'SectionTitle',
            parent=self._getSampleStyleSheet()['Heading2'],
            fontSize=14,
            textColor=self._colors.HexColor('#333333')
        )
        elements.append(self._Paragraph(title, title_style))

        # 数据表格
        table_data = [[label, value] for label, value in data]
        table = self._Table(table_data, colWidths=[4 * self._cm, 5 * self._cm])
        table.setStyle(self._TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self._colors.HexColor('#D9E1F2')),
            ('TEXTCOLOR', (0, 0), (0, -1), self._colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, self._colors.grey)
        ]))
        elements.append(table)
        elements.append(self._Spacer(1, 0.5 * self._cm))

        return elements

    def _create_position_table(
        self,
        positions: List[PositionRecord]
    ) -> List:
        """
        创建持仓表格

        Args:
            positions: 持仓列表

        Returns:
            元素列表
        """
        elements = []

        title_style = self._ParagraphStyle(
            'SectionTitle',
            parent=self._getSampleStyleSheet()['Heading2'],
            fontSize=14,
            textColor=self._colors.HexColor('#333333')
        )
        elements.append(self._Paragraph("持仓明细", title_style))

        # 表头
        headers = ["代码", "名称", "数量", "成本", "现价", "市值", "盈亏"]
        table_data = [headers]

        # 数据行
        for pos in positions[:20]:  # 限制最多20行
            row = [
                pos.symbol,
                pos.name[:6] if len(pos.name) > 6 else pos.name,  # 截断过长的名称
                str(pos.volume),
                f"{pos.avg_cost:.2f}",
                f"{pos.current_price:.2f}",
                f"{pos.market_value:.2f}",
                f"{pos.unrealized_pnl:.2f}"
            ]
            table_data.append(row)

        table = self._Table(
            table_data,
            colWidths=[1.5 * self._cm, 2.5 * self._cm, 1.2 * self._cm,
                       1.2 * self._cm, 1.2 * self._cm, 1.8 * self._cm, 1.5 * self._cm]
        )
        table.setStyle(self._TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self._colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), self._colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), self._colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 1, self._colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [self._colors.white, self._colors.HexColor('#F2F2F2')])
        ]))
        elements.append(table)
        elements.append(self._Spacer(1, 0.5 * self._cm))

        return elements

    def _create_industry_table(
        self,
        industry_data: dict
    ) -> List:
        """
        创建行业分布表格

        Args:
            industry_data: 行业分布数据

        Returns:
            元素列表
        """
        elements = []

        title_style = self._ParagraphStyle(
            'SectionTitle',
            parent=self._getSampleStyleSheet()['Heading2'],
            fontSize=14,
            textColor=self._colors.HexColor('#333333')
        )
        elements.append(self._Paragraph("行业分布", title_style))

        # 表头
        headers = ["行业", "市值", "占比", "数量"]
        table_data = [headers]

        # 数据行
        for industry, stats in industry_data.items():
            row = [
                industry[:10],  # 截断过长的行业名
                f"{stats.get('value', 0):.2f}",
                f"{stats.get('ratio', 0):.2%}",
                str(stats.get('count', 0))
            ]
            table_data.append(row)

        table = self._Table(table_data, colWidths=[3 * self._cm, 2.5 * self._cm,
                                                     2 * self._cm, 1.5 * self._cm])
        table.setStyle(self._TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self._colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), self._colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), self._colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 1, self._colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [self._colors.white, self._colors.HexColor('#F2F2F2')])
        ]))
        elements.append(table)
        elements.append(self._Spacer(1, 0.5 * self._cm))

        return elements

    def _export_daily_report_fallback(
        self,
        report: ReportData,
        filepath: str
    ) -> bool:
        """
        回退方法：当reportlab不可用时生成文本文件

        Args:
            report: 报表数据对象
            filepath: 导出文件路径

        Returns:
            是否导出成功
        """
        try:
            # 生成文本格式的报告
            txt_filepath = filepath.replace('.pdf', '.txt')

            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write(f"每日交易报告 - {report.start_date}\n")
                f.write("=" * 50 + "\n\n")

                if report.account:
                    f.write("资金情况\n")
                    f.write("-" * 30 + "\n")
                    f.write(f"总权益: {report.account.total_equity:.2f}\n")
                    f.write(f"可用资金: {report.account.available_cash:.2f}\n")
                    f.write(f"持仓市值: {report.account.market_value:.2f}\n")
                    f.write(f"总盈亏: {report.account.total_pnl:.2f}\n")
                    f.write(f"盈亏比例: {report.account.total_pnl_ratio:.2%}\n\n")

                f.write("当日盈亏\n")
                f.write("-" * 30 + "\n")
                _pnl = f"{report.daily_pnl:.2f}" if report.daily_pnl is not None else "N/A"
                _ratio = f"{report.daily_pnl_ratio:.2%}" if report.daily_pnl_ratio is not None else "N/A"
                f.write(f"当日盈亏: {_pnl}\n")
                f.write(f"盈亏比例: {_ratio}\n\n")

            return True

        except Exception as e:
            print(f"导出文本文件失败: {e}")
            return False

    def _export_monthly_report_fallback(
        self,
        report: ReportData,
        filepath: str
    ) -> bool:
        """月报回退方法"""
        return self._export_daily_report_fallback(report, filepath)

    def _export_position_analysis_fallback(
        self,
        analysis: PositionAnalysis,
        filepath: str
    ) -> bool:
        """持仓分析回退方法"""
        try:
            txt_filepath = filepath.replace('.pdf', '.txt')

            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write("持仓分析报告\n")
                f.write("=" * 50 + "\n\n")

                f.write("总体统计\n")
                f.write("-" * 30 + "\n")
                f.write(f"持仓数量: {analysis.total_positions}\n")
                f.write(f"总市值: {analysis.total_market_value:.2f}\n")
                f.write(f"集中度: {analysis.concentration:.2%}\n\n")

            return True

        except Exception as e:
            print(f"导出文本文件失败: {e}")
            return False
