"""A股回测UI组件"""
import csv
from typing import Any, Optional
from datetime import datetime, date

from vnpy.trader.ui.qt import QtCore, QtWidgets
from vnpy.trader.locale import _
from vnpy.trader.constant import Exchange, Interval, Direction
from vnpy.trader.utility import extract_vt_symbol


# 交易所缩写规范化（SH/SZ → SSE/SZSE），其余原样交给标准 extract_vt_symbol
_EXCHANGE_ALIASES = {
    "SH": "SSE",
    "SZ": "SZSE",
}


def _parse_vt_symbol(vt_symbol: str) -> tuple:
    """解析 vt_symbol 为 (symbol, exchange)

    支持格式: "600660.SSE"、"600660.SH"、"000001.SZSE"、"000001.SZ"。
    复用 vnpy.trader.utility.extract_vt_symbol，仅补充 SH/SZ 缩写规范化，
    不再做不可靠的代码前缀自动推断。
    """
    vt_symbol = vt_symbol.strip()
    if "." not in vt_symbol:
        raise ValueError(
            f"股票代码需包含交易所后缀，如 600660.SSE 或 000001.SZ: {vt_symbol}"
        )
    symbol, suffix = vt_symbol.split(".", 1)
    suffix = _EXCHANGE_ALIASES.get(suffix.upper(), suffix)
    return extract_vt_symbol(f"{symbol}.{suffix}")


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
        self.trades: list = []
        self.equity_curve: list = []
        self.daily_logs: list = []

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

        # 股票代码
        param_layout.addWidget(QtWidgets.QLabel(_("股票代码：")), 0, 0)
        self.symbol_input = QtWidgets.QLineEdit("600660.SSE")
        self.symbol_input.setPlaceholderText(_("如：600660.SSE 或 000001.SZ"))
        param_layout.addWidget(self.symbol_input, 0, 1)

        # 策略选择
        param_layout.addWidget(QtWidgets.QLabel(_("回测策略：")), 1, 0)
        self.strategy_combo = QtWidgets.QComboBox()
        self.strategy_combo.addItem(_("均线策略（MA5/MA20 金叉死叉）"), "ma_cross")
        self.strategy_combo.addItem(_("买入持有（基准对比）"), "buy_hold")
        param_layout.addWidget(self.strategy_combo, 1, 1)

        # 初始资金
        param_layout.addWidget(QtWidgets.QLabel(_("初始资金：")), 2, 0)
        self.capital_input = QtWidgets.QLineEdit("1000000")
        param_layout.addWidget(self.capital_input, 2, 1)
        param_layout.addWidget(QtWidgets.QLabel(_("元")), 2, 2)

        # 开始日期
        param_layout.addWidget(QtWidgets.QLabel(_("开始日期：")), 3, 0)
        self.start_date_edit = QtWidgets.QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QtCore.QDate.currentDate().addYears(-1))
        param_layout.addWidget(self.start_date_edit, 3, 1)

        # 结束日期
        param_layout.addWidget(QtWidgets.QLabel(_("结束日期：")), 4, 0)
        self.end_date_edit = QtWidgets.QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QtCore.QDate.currentDate())
        param_layout.addWidget(self.end_date_edit, 4, 1)

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

        # 交易统计区
        stats_group = QtWidgets.QGroupBox(_("交易统计"))
        stats_layout = QtWidgets.QGridLayout()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        stats_layout.addWidget(QtWidgets.QLabel(_("总交易次数：")), 0, 0)
        self.total_trades_label = QtWidgets.QLabel("--")
        stats_layout.addWidget(self.total_trades_label, 0, 1)

        stats_layout.addWidget(QtWidgets.QLabel(_("被阻止订单：")), 0, 2)
        self.blocked_label = QtWidgets.QLabel("--")
        stats_layout.addWidget(self.blocked_label, 0, 3)

        stats_layout.addWidget(QtWidgets.QLabel(_("最终权益：")), 1, 0)
        self.final_equity_label = QtWidgets.QLabel("--")
        stats_layout.addWidget(self.final_equity_label, 1, 1)

        stats_layout.addWidget(QtWidgets.QLabel(_("数据条数：")), 1, 2)
        self.bar_count_label = QtWidgets.QLabel("--")
        stats_layout.addWidget(self.bar_count_label, 1, 3)

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

    # ── 回测执行 ──────────────────────────────────────────────

    def start_backtest(self) -> None:
        """开始回测"""
        # 解析股票代码
        vt_symbol = self.symbol_input.text().strip()
        if not vt_symbol:
            self.show_status(_("请输入股票代码"))
            return

        try:
            symbol, exchange = _parse_vt_symbol(vt_symbol)
        except ValueError as e:
            self.show_status(str(e))
            return

        # 解析资金
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

        self.show_status(_("正在加载数据..."))
        self.progress_bar.setValue(5)

        # 加载K线数据
        bars = self._load_bar_data(symbol, exchange, start_date, end_date)
        if not bars:
            self.show_status(_("未能加载到数据，请检查股票代码和日期范围"))
            self.progress_bar.setValue(0)
            return

        self.show_status(_("正在执行回测..."))
        self.progress_bar.setValue(20)

        # 获取策略类型
        strategy_key = self.strategy_combo.currentData()

        # 执行回测
        self._run_backtest(
            vt_symbol=f"{symbol}.{exchange.value}",
            bars=bars,
            capital=capital,
            strategy_key=strategy_key,
        )

    def _load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        start_date: date,
        end_date: date,
    ) -> list:
        """通过数据服务加载K线数据

        复用 ChinaDataService 单例：仅在未连接时 connect，不主动 disconnect，
        避免每次回测都重建数据库/缓存连接的开销。
        """
        try:
            from vnpy_china_data.service import get_data_service

            service = get_data_service()
            if not service.connected:
                service.connect()

            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            return service.get_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=start_dt,
                end=end_dt,
            )

        except ImportError:
            self.show_status(_("未安装 vnpy_china_data，无法加载数据"))
            return []
        except Exception as e:
            self.show_status(_("数据加载失败: {}").format(e))
            return []

    def _run_backtest(
        self,
        vt_symbol: str,
        bars: list,
        capital: float,
        strategy_key: str,
    ) -> None:
        """执行真实回测"""
        from vnpy_china_backtest.engine import EnhancedBacktestEngine
        from vnpy_china_backtest.strategies import get_strategy

        # 创建引擎
        engine = EnhancedBacktestEngine()
        engine.capital = capital
        engine.cash = capital
        engine.enable_cost = self.enable_cost_checkbox.isChecked()
        engine.enable_slippage = self.enable_slippage_checkbox.isChecked()
        engine.enable_price_limit = self.enable_price_limit_checkbox.isChecked()
        engine.enable_t1 = self.enable_t1_checkbox.isChecked()

        # 加载数据（load_data 会初始化权益曲线首点为初始资金）
        engine.load_data(bars)

        total_bars = len(bars)

        # 策略进度（0-100）映射到 widget 进度区间 20-90
        def on_progress(percent: int) -> None:
            self.progress_bar.setValue(20 + int(percent * 0.7))

        # 执行策略（交易逻辑由 strategies.py 提供，与 UI 解耦）
        strategy = get_strategy(strategy_key)
        self.daily_logs = strategy.run(
            engine, bars, vt_symbol, on_progress=on_progress
        )

        # 计算指标（engine 维护完整权益曲线与真实回测天数）
        metrics = engine.calculate_metrics()

        # 权益曲线由 engine 维护，widget 仅取副本用于展示/导出
        self.equity_curve = list(engine.equity_curve)

        # 收集结果
        self.backtest_results = {
            "total_return": metrics.total_return,
            "annual_return": metrics.annual_return,
            "max_drawdown": metrics.max_drawdown,
            "sharpe_ratio": metrics.sharpe_ratio,
            "win_rate": metrics.win_rate,
            "profit_loss_ratio": metrics.profit_loss_ratio,
            "avg_holding_days": metrics.avg_holding_days,
            "total_cost": engine.total_cost,
            "total_trades": metrics.total_trades,
            "blocked_orders": engine.blocked_orders,
            "final_equity": engine.get_equity(),
            "bar_count": total_bars,
        }
        self.trades = list(engine.trades.values())

        # 更新界面
        self.update_results()
        self.progress_bar.setValue(100)
        self.show_status(
            _("回测完成：{} 条数据，{} 笔交易").format(total_bars, len(self.trades))
        )

    # ── 结果展示 ──────────────────────────────────────────────

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

        # 更新交易统计
        self.total_trades_label.setText(str(r.get("total_trades", 0)))
        self.blocked_label.setText(str(r.get("blocked_orders", 0)))
        self.final_equity_label.setText(f"¥{r.get('final_equity', 0):,.2f}")
        self.bar_count_label.setText(str(r.get("bar_count", 0)))

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

    # ── 导出报告 ──────────────────────────────────────────────

    def export_report(self) -> None:
        """导出回测报告为CSV"""
        if not self.backtest_results:
            self.show_status(_("无可导出的数据"))
            return

        # 选择保存路径
        default_name = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            _("导出回测报告"),
            default_name,
            _("CSV文件 (*.csv)")
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)

                # 绩效指标摘要
                writer.writerow(["=== 绩效指标 ==="])
                writer.writerow(["指标", "值"])
                r = self.backtest_results
                writer.writerow(["总收益率", f"{r['total_return']:.2%}"])
                writer.writerow(["年化收益率", f"{r['annual_return']:.2%}"])
                writer.writerow(["最大回撤", f"{r['max_drawdown']:.2%}"])
                writer.writerow(["夏普比率", f"{r['sharpe_ratio']:.2f}"])
                writer.writerow(["胜率", f"{r['win_rate']:.2%}"])
                writer.writerow(["盈亏比", f"{r['profit_loss_ratio']:.2f}"])
                writer.writerow(["平均持股天数", f"{r['avg_holding_days']:.1f}"])
                writer.writerow(["总交易成本", f"¥{r['total_cost']:,.2f}"])
                writer.writerow(["总交易次数", r.get("total_trades", 0)])
                writer.writerow(["被阻止订单", r.get("blocked_orders", 0)])
                writer.writerow(["最终权益", f"¥{r.get('final_equity', 0):,.2f}"])
                writer.writerow([])

                # 交易明细
                if self.trades:
                    writer.writerow(["=== 交易明细 ==="])
                    writer.writerow(["时间", "代码", "方向", "价格", "数量", "金额"])
                    for t in self.trades:
                        direction = "买入" if t.direction == Direction.LONG else "卖出"
                        amount = t.price * t.volume
                        writer.writerow([
                            t.datetime,
                            t.vt_symbol,
                            direction,
                            f"{t.price:.2f}",
                            int(t.volume),
                            f"{amount:,.2f}",
                        ])
                    writer.writerow([])

                # 日度权益曲线
                if self.equity_curve:
                    writer.writerow(["=== 权益曲线 ==="])
                    writer.writerow(["序号", "权益"])
                    for i, eq in enumerate(self.equity_curve):
                        writer.writerow([i, f"{eq:,.2f}"])

            self.show_status(_("报告已导出: {}").format(file_path))

        except Exception as e:
            self.show_status(_("导出失败: {}").format(e))

    def stop_backtest(self) -> None:
        """停止回测"""
        self.show_status(_("回测已停止"))
        self.progress_bar.setValue(0)

    def clear_results(self) -> None:
        """清空结果"""
        self.backtest_results = {}
        self.trades = []
        self.equity_curve = []
        self.daily_logs = []

        self.total_return_label.setText("--")
        self.annual_return_label.setText("--")
        self.max_drawdown_label.setText("--")
        self.sharpe_label.setText("--")
        self.win_rate_label.setText("--")
        self.profit_loss_ratio_label.setText("--")
        self.avg_holding_days_label.setText("--")
        self.total_cost_label.setText("--")
        self.total_trades_label.setText("--")
        self.blocked_label.setText("--")
        self.final_equity_label.setText("--")
        self.bar_count_label.setText("--")
        self.progress_bar.setValue(0)
        self.show_status(_("结果已清空"))

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaBacktestWidget"]
