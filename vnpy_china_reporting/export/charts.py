"""
图表生成器

生成各种分析图表用于报表展示。
"""

from typing import List, Optional, Dict
from pathlib import Path
import numpy as np

from ..core.models import ReportData, PositionRecord


class ChartGenerator:
    """
    图表生成器

    生成各种分析图表用于报表展示，包括资金曲线、盈亏分布、持仓饼图等。
    """

    def __init__(self, dpi: int = 300, figsize: tuple = (10, 6)):
        """
        初始化图表生成器

        Args:
            dpi: 图像分辨率
            figsize: 图像尺寸 (宽, 高)
        """
        self.default_dpi = dpi
        self.default_figsize = figsize

        # 尝试导入matplotlib
        self._matplotlib_available = False
        self._plt = None
        self._mdates = None
        self._try_import_matplotlib()

    def _try_import_matplotlib(self) -> None:
        """尝试导入matplotlib库"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            self._matplotlib_available = True
            self._plt = plt
            self._mdates = mdates

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
            plt.rcParams['axes.unicode_minus'] = False

        except ImportError:
            print("警告: matplotlib库未安装，图表生成功能不可用")
            print("请使用 pip install matplotlib 安装")

    def generate_equity_curve(
        self,
        equity_data: List[float],
        dates: Optional[List[str]] = None,
        filepath: str = "equity_curve.png"
    ) -> bool:
        """
        生成资金曲线图

        Args:
            equity_data: 资金数据列表
            dates: 日期列表（可选）
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            fig, ax = self._plt.subplots(figsize=self.default_figsize)

            if dates:
                x_data = range(len(equity_data))
                ax.plot(x_data, equity_data, linewidth=2, color='#4472C4')
                ax.fill_between(x_data, equity_data, alpha=0.3, color='#4472C4')

                # 设置日期标签
                ax.set_xticks(range(0, len(dates), max(1, len(dates) // 10)))
                ax.set_xticklabels([dates[i] for i in range(0, len(dates),
                            max(1, len(dates) // 10))], rotation=45)
            else:
                ax.plot(equity_data, linewidth=2, color='#4472C4')
                ax.fill_between(range(len(equity_data)), equity_data,
                               alpha=0.3, color='#4472C4')

            ax.set_title('资金曲线', fontsize=14, fontweight='bold')
            ax.set_xlabel('时间', fontsize=12)
            ax.set_ylabel('资金', fontsize=12)
            ax.grid(True, alpha=0.3)

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成资金曲线图失败: {e}")
            return False

    def generate_pnl_distribution(
        self,
        pnl_data: List[float],
        filepath: str = "pnl_distribution.png"
    ) -> bool:
        """
        生成盈亏分布图

        Args:
            pnl_data: 盈亏数据列表
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            fig, axes = self._plt.subplots(1, 2, figsize=(14, 5))

            # 直方图
            axes[0].hist(pnl_data, bins=30, color='#4472C4', alpha=0.7, edgecolor='white')
            axes[0].axvline(x=0, color='red', linestyle='--', linewidth=1)
            axes[0].set_title('盈亏分布直方图', fontsize=12, fontweight='bold')
            axes[0].set_xlabel('盈亏金额', fontsize=10)
            axes[0].set_ylabel('频次', fontsize=10)
            axes[0].grid(True, alpha=0.3, axis='y')

            # 累计收益曲线
            sorted_pnl = sorted(pnl_data)
            cumulative = np.cumsum(sorted_pnl)
            axes[1].plot(sorted_pnl, cumulative, color='#4472C4', linewidth=2)
            axes[1].fill_between(sorted_pnl, cumulative, alpha=0.3, color='#4472C4')
            axes[1].axvline(x=0, color='red', linestyle='--', linewidth=1)
            axes[1].set_title('累计盈亏曲线', fontsize=12, fontweight='bold')
            axes[1].set_xlabel('盈亏金额', fontsize=10)
            axes[1].set_ylabel('累计盈亏', fontsize=10)
            axes[1].grid(True, alpha=0.3)

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成盈亏分布图失败: {e}")
            return False

    def generate_industry_pie(
        self,
        industry_data: dict,
        filepath: str = "industry_pie.png"
    ) -> bool:
        """
        生成行业分布饼图

        Args:
            industry_data: 行业数据 {行业: 数据}
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            if not industry_data:
                return False

            # 提取数据
            labels = list(industry_data.keys())
            values = [data.get('value', data) for data in industry_data.values()]

            # 过滤掉零值
            non_zero_idx = [i for i, v in enumerate(values) if v > 0]
            labels = [labels[i] for i in non_zero_idx]
            values = [values[i] for i in non_zero_idx]

            if not values:
                return False

            fig, ax = self._plt.subplots(figsize=(10, 8))

            # 使用颜色映射
            colors = self._plt.cm.Set3(range(len(labels)))

            wedges, texts, autotexts = ax.pie(
                values,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 10}
            )

            # 设置百分比文字样式
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

            ax.set_title('行业分布', fontsize=14, fontweight='bold')

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成行业饼图失败: {e}")
            return False

    def generate_position_bar(
        self,
        position_data: List[dict],
        filepath: str = "position_bar.png"
    ) -> bool:
        """
        生成持仓柱状图

        Args:
            position_data: 持仓数据 [{symbol, name, market_value, pnl}, ...]
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            if not position_data:
                return False

            # 排序并取前15只
            sorted_data = sorted(position_data,
                               key=lambda x: x.get('market_value', 0),
                               reverse=True)[:15]

            symbols = [d.get('symbol', '') for d in sorted_data]
            market_values = [d.get('market_value', 0) for d in sorted_data]
            pnls = [d.get('pnl', 0) for d in sorted_data]

            fig, axes = self._plt.subplots(1, 2, figsize=(14, 6))

            # 市值柱状图
            colors = ['#4472C4' for _ in market_values]
            bars = axes[0].bar(range(len(symbols)), market_values, color=colors, alpha=0.8)
            axes[0].set_title('持仓市值排名', fontsize=12, fontweight='bold')
            axes[0].set_xlabel('股票', fontsize=10)
            axes[0].set_ylabel('市值', fontsize=10)
            axes[0].set_xticks(range(len(symbols)))
            axes[0].set_xticklabels(symbols, rotation=45, ha='right', fontsize=8)
            axes[0].grid(True, alpha=0.3, axis='y')

            # 盈亏柱状图
            pnl_colors = ['#FF0000' if p > 0 else '#00AA00' for p in pnls]
            axes[1].bar(range(len(symbols)), pnls, color=pnl_colors, alpha=0.8)
            axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            axes[1].set_title('持仓盈亏排名', fontsize=12, fontweight='bold')
            axes[1].set_xlabel('股票', fontsize=10)
            axes[1].set_ylabel('盈亏', fontsize=10)
            axes[1].set_xticks(range(len(symbols)))
            axes[1].set_xticklabels(symbols, rotation=45, ha='right', fontsize=8)
            axes[1].grid(True, alpha=0.3, axis='y')

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成持仓柱状图失败: {e}")
            return False

    def generate_daily_return_bar(
        self,
        returns: List[float],
        dates: Optional[List[str]] = None,
        filepath: str = "daily_return.png"
    ) -> bool:
        """
        生成日收益率柱状图

        Args:
            returns: 日收益率列表
            dates: 日期列表（可选）
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            fig, ax = self._plt.subplots(figsize=(12, 6))

            # 根据正负设置颜色
            colors = ['#FF0000' if r >= 0 else '#00AA00' for r in returns]

            if dates:
                x_data = range(len(returns))
                ax.bar(x_data, [r * 100 for r in returns], color=colors, alpha=0.7)

                # 设置日期标签
                ax.set_xticks(range(0, len(dates), max(1, len(dates) // 15)))
                ax.set_xticklabels([dates[i] for i in range(0, len(dates),
                            max(1, len(dates) // 15))], rotation=45)
            else:
                ax.bar(range(len(returns)), [r * 100 for r in returns],
                      color=colors, alpha=0.7)

            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

            ax.set_title('日收益率', fontsize=14, fontweight='bold')
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('收益率(%)', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成日收益柱状图失败: {e}")
            return False

    def generate_position_pie(
        self,
        positions: List[PositionRecord],
        filepath: str = "position_pie.png"
    ) -> bool:
        """
        生成持仓分布饼图

        Args:
            positions: 持仓列表
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            if not positions:
                return False

            # 按市值排序取前10
            sorted_positions = sorted(
                positions,
                key=lambda p: p.market_value,
                reverse=True
            )[:10]

            labels = [f"{p.symbol}\n{p.name[:4]}" for p in sorted_positions]
            sizes = [p.market_value for p in sorted_positions]

            fig, ax = self._plt.subplots(figsize=(10, 10))

            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=self._plt.cm.Set3(range(len(labels)))
            )

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

            ax.set_title('持仓分布', fontsize=14, fontweight='bold')

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成持仓饼图失败: {e}")
            return False

    def generate_sharpe_chart(
        self,
        returns: List[float],
        filepath: str = "sharpe_chart.png"
    ) -> bool:
        """
        生成夏普比率图

        Args:
            returns: 收益率序列
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            if not returns:
                return False

            # 计算滚动夏普比率
            window = min(20, len(returns) // 2)
            if window < 5:
                return False

            rolling_returns = []
            rolling_sharpe = []

            for i in range(window, len(returns)):
                window_returns = returns[i-window:i]
                rolling_returns.append(i)

                # 计算滚动夏普
                if np.std(window_returns) > 0:
                    sharpe = np.mean(window_returns) / np.std(window_returns) * np.sqrt(252)
                    rolling_sharpe.append(sharpe)
                else:
                    rolling_sharpe.append(0)

            fig, ax = self._plt.subplots(figsize=(12, 6))

            ax.plot(rolling_returns, rolling_sharpe, color='#4472C4', linewidth=2)
            ax.fill_between(rolling_returns, rolling_sharpe, alpha=0.3, color='#4472C4')
            ax.axhline(y=0, color='red', linestyle='--', linewidth=1)

            ax.set_title('滚动夏普比率', fontsize=14, fontweight='bold')
            ax.set_xlabel('时间', fontsize=12)
            ax.set_ylabel('夏普比率', fontsize=12)
            ax.grid(True, alpha=0.3)

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成夏普比率图失败: {e}")
            return False

    def generate_drawdown_chart(
        self,
        equity_curve: List[float],
        filepath: str = "drawdown_chart.png"
    ) -> bool:
        """
        生成回撤图

        Args:
            equity_curve: 资金曲线
            filepath: 保存路径

        Returns:
            是否生成成功
        """
        if not self._matplotlib_available:
            return False

        try:
            if not equity_curve:
                return False

            # 计算回撤
            peak = equity_curve[0]
            drawdowns = []

            for value in equity_curve:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak if peak > 0 else 0
                drawdowns.append(drawdown)

            fig, ax = self._plt.subplots(figsize=(12, 6))

            ax.fill_between(range(len(drawdowns)), drawdowns, alpha=0.5, color='#FF6B6B')
            ax.plot(drawdowns, color='#FF6B6B', linewidth=1)

            ax.set_title('回撤曲线', fontsize=14, fontweight='bold')
            ax.set_xlabel('时间', fontsize=12)
            ax.set_ylabel('回撤比例', fontsize=12)
            ax.grid(True, alpha=0.3)

            self._plt.tight_layout()
            self._plt.savefig(filepath, dpi=self.default_dpi, bbox_inches='tight')
            self._plt.close()

            return True

        except Exception as e:
            print(f"生成回撤图失败: {e}")
            return False
