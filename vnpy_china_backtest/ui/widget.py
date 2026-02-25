"""A股回测UI组件"""
from typing import Any, Optional
from datetime import datetime, date

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.locale import _


class ChinaBacktestWidget(QtWidgets.QWidget):
    """A股回测主界面"""

    def __init__(self, main_engine: Any, event_engine: Any):
        """初始化界面"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取GUI引擎
        self.gui_engine: Optional[Any] = None
        try:
            self.gui_engine = main_engine.get_engine("ChinaBacktestApp")
        except Exception:
            pass

        # 回测结果数据
        self.backtest_results: dict = {}

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(_("A股策略回测"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab = QtWidgets.QTabWidget()
        layout.addWidget(tab)

        # 回测配置标签页
        config_widget = self.create_config_tab()
        tab.addTab(config_widget, _("回测配置"))

        # 回测结果标签页
        result_widget = self.create_result_tab()
        tab.addTab(result_widget, _("回测结果"))

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def create_config_tab(self) -> QtWidgets.QWidget:
        """创建回测配置标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("回测参数配置"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 参数配置区
        param_group = QtWidgets.QGroupBox(_("基本参数"))
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # 初始资金
        param_layout.addWidget(QtWidgets.QLabel(_("初始资金：")), 0, 0)
        self.capital_input = QtWidgets.QLineEdit("1000000")
        param_layout.addWidget(self.capital_input, 0, 1)
        param_layout.addWidget(QtWidgets.QLabel(_("元")), 0, 2)

        # 开始日期
        param_layout.addWidget(QtWidgets.QLabel(_("开始日期：")), 1, 0)
        self.start_date_edit = QtWidgets.QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QtCore.QDate.currentDate().addYears(-1))
        param_layout.addWidget(self.start_date_edit, 1, 1)

        # 结束日期
        param_layout.addWidget(QtWidgets.QLabel(_("结束日期：")), 2, 0)
        self.end_date_edit = QtWidgets.QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QtCore.QDate.currentDate())
        param_layout.addWidget(self.end_date_edit, 2, 1)

        # A股特色功能
        feature_group = QtWidgets.QGroupBox(_("A股特色功能"))
        feature_layout = QtWidgets.QGridLayout()
        feature_group.setLayout(feature_layout)
        layout.addWidget(feature_group)

        # 交易成本
        self.enable_cost_checkbox = QtWidgets.QCheckBox(_("启用交易成本"))
        self.enable_cost_checkbox.setChecked(True)
        feature_layout.addWidget(self.enable_cost_checkbox, 0, 0)

        # 滑点
        self.enable_slippage_checkbox = QtWidgets.QCheckBox(_("启用滑点"))
        self.enable_slippage_checkbox.setChecked(True)
        feature_layout.addWidget(self.enable_slippage_checkbox, 0, 1)

        # 涨跌停
        self.enable_price_limit_checkbox = QtWidgets.QCheckBox(_("启用涨跌停限制"))
        self.enable_price_limit_checkbox.setChecked(True)
        feature_layout.addWidget(self.enable_price_limit_checkbox, 1, 0)

        # T+1规则
        self.enable_t1_checkbox = QtWidgets.QCheckBox(_("启用T+1规则"))
        self.enable_t1_checkbox.setChecked(True)
        feature_layout.addWidget(self.enable_t1_checkbox, 1, 1)

        layout.addStretch()

        # 操作按钮
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        start_btn = QtWidgets.QPushButton(_("开始回测"))
        start_btn.clicked.connect(self.start_backtest)
        btn_layout.addWidget(start_btn)

        stop_btn = QtWidgets.QPushButton(_("停止回测"))
        stop_btn.clicked.connect(self.stop_backtest)
        btn_layout.addWidget(stop_btn)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        return widget

    def create_result_tab(self) -> QtWidgets.QWidget:
        """创建回测结果标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("回测结果"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 基础指标区
        basic_group = QtWidgets.QGroupBox(_("基础指标"))
        basic_layout = QtWidgets.QGridLayout()
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 总收益
        basic_layout.addWidget(QtWidgets.QLabel(_("总收益：")), 0, 0)
        self.total_return_label = QtWidgets.QLabel("--")
        basic_layout.addWidget(self.total_return_label, 0, 1)

        # 年化收益
        basic_layout.addWidget(QtWidgets.QLabel(_("年化收益：")), 0, 2)
        self.annual_return_label = QtWidgets.QLabel("--")
        basic_layout.addWidget(self.annual_return_label, 0, 3)

        # 最大回撤
        basic_layout.addWidget(QtWidgets.QLabel(_("最大回撤：")), 1, 0)
        self.max_drawdown_label = QtWidgets.QLabel("--")
        basic_layout.addWidget(self.max_drawdown_label, 1, 1)

        # 夏普比率
        basic_layout.addWidget(QtWidgets.QLabel(_("夏普比率：")), 1, 2)
        self.sharpe_label = QtWidgets.QLabel("--")
        basic_layout.addWidget(self.sharpe_label, 1, 3)

        # A股特色指标区
        china_group = QtWidgets.QGroupBox(_("A股特色指标"))
        china_layout = QtWidgets.QGridLayout()
        china_group.setLayout(china_layout)
        layout.addWidget(china_group)

        # 胜率
        china_layout.addWidget(QtWidgets.QLabel(_("胜率：")), 0, 0)
        self.win_rate_label = QtWidgets.QLabel("--")
        china_layout.addWidget(self.win_rate_label, 0, 1)

        # 盈亏比
        china_layout.addWidget(QtWidgets.QLabel(_("盈亏比：")), 0, 2)
        self.profit_loss_ratio_label = QtWidgets.QLabel("--")
        china_layout.addWidget(self.profit_loss_ratio_label, 0, 3)

        # 平均持股天数
        china_layout.addWidget(QtWidgets.QLabel(_("平均持股天数：")), 1, 0)
        self.avg_holding_days_label = QtWidgets.QLabel("--")
        china_layout.addWidget(self.avg_holding_days_label, 1, 1)

        # 交易成本
        china_layout.addWidget(QtWidgets.QLabel(_("总交易成本：")), 1, 2)
        self.total_cost_label = QtWidgets.QLabel("--")
        china_layout.addWidget(self.total_cost_label, 1, 3)

        layout.addStretch()

        # 操作按钮
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        export_btn = QtWidgets.QPushButton(_("导出报告"))
        export_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(export_btn)

        clear_btn = QtWidgets.QPushButton(_("清空结果"))
        clear_btn.clicked.connect(self.clear_results)
        btn_layout.addWidget(clear_btn)

        return widget

    def start_backtest(self) -> None:
        """开始回测"""
        # 获取参数
        try:
            capital = float(self.capital_input.text())
        except ValueError:
            self.show_status(_("初始资金格式错误"))
            return

        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()

        if start_date >= end_date:
            self.show_status(_("开始日期必须早于结束日期"))
            return

        self.show_status(_("正在执行回测..."))
        self.progress_bar.setValue(10)

        # 模拟回测执行（实际应调用GUI引擎）
        self._simulate_backtest(capital, start_date, end_date)

    def stop_backtest(self) -> None:
        """停止回测"""
        self.show_status(_("回测已停止"))
        self.progress_bar.setValue(0)

    def _simulate_backtest(self, capital: float, start_date: date, end_date: date) -> None:
        """模拟回测执行"""
        import random

        # 模拟进度
        for i in range(10, 101, 10):
            self.progress_bar.setValue(i)
            QtCore.QTimer.singleShot(100, lambda: None)

        # 生成模拟结果
        total_return = random.uniform(-0.3, 0.5)  # -30% 到 50%
        annual_return = random.uniform(-0.2, 0.4)
        max_drawdown = -random.uniform(0.05, 0.3)
        sharpe = random.uniform(0.5, 2.5)
        win_rate = random.uniform(0.4, 0.7)
        profit_loss_ratio = random.uniform(1.0, 3.0)
        avg_holding_days = random.uniform(3, 20)
        total_cost = capital * random.uniform(0.001, 0.01)

        self.backtest_results = {
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "win_rate": win_rate,
            "profit_loss_ratio": profit_loss_ratio,
            "avg_holding_days": avg_holding_days,
            "total_cost": total_cost,
        }

        # 更新结果
        self.update_results()
        self.show_status(_("回测完成"))
        self.progress_bar.setValue(100)

    def update_results(self) -> None:
        """更新回测结果显示"""
        if not self.backtest_results:
            return

        r = self.backtest_results

        # 更新基础指标
        self._update_metric_label(self.total_return_label, r["total_return"], is_percent=True)
        self._update_metric_label(self.annual_return_label, r["annual_return"], is_percent=True)
        self._update_metric_label(self.max_drawdown_label, r["max_drawdown"], is_percent=True)
        self._update_metric_label(self.sharpe_label, r["sharpe_ratio"], is_percent=False, fmt=".2f")

        # 更新A股特色指标
        self._update_metric_label(self.win_rate_label, r["win_rate"], is_percent=True)
        self._update_metric_label(self.profit_loss_ratio_label, r["profit_loss_ratio"], is_percent=False, fmt=".2f")
        self._update_metric_label(self.avg_holding_days_label, r["avg_holding_days"], is_percent=False, fmt=".1f")
        self.total_cost_label.setText(f"¥{r['total_cost']:,.2f}")

    def _update_metric_label(
        self,
        label: QtWidgets.QLabel,
        value: float,
        is_percent: bool = False,
        fmt: str = ".2f"
    ) -> None:
        """更新指标标签颜色和格式"""
        text = f"{value:{fmt}}%" if is_percent else f"{value:{fmt}}"

        if value > 0:
            label.setStyleSheet("color: red; font-weight: bold;")
            label.setText(f"+{text}")
        elif value < 0:
            label.setStyleSheet("color: green; font-weight: bold;")
            label.setText(text)
        else:
            label.setStyleSheet("color: black; font-weight: bold;")
            label.setText(text)

    def export_report(self) -> None:
        """导出回测报告"""
        if not self.backtest_results:
            self.show_status(_("无可导出的数据"))
            return

        # 模拟导出
        self.show_status(_("报告已导出（模拟）"))

    def clear_results(self) -> None:
        """清空结果"""
        self.backtest_results = {}
        self.total_return_label.setText("--")
        self.annual_return_label.setText("--")
        self.max_drawdown_label.setText("--")
        self.sharpe_label.setText("--")
        self.win_rate_label.setText("--")
        self.profit_loss_ratio_label.setText("--")
        self.avg_holding_days_label.setText("--")
        self.total_cost_label.setText("--")
        self.progress_bar.setValue(0)
        self.show_status(_("结果已清空"))

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaBacktestWidget"]
