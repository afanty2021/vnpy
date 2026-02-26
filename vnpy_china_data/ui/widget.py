"""A股数据UI组件"""
from datetime import date, timedelta
from typing import Any, Optional, List

from vnpy.trader.ui.qt import QtWidgets, QtCore, QtGui
from vnpy.trader.ui.widget import BaseCell
from vnpy.trader.constant import Interval
from vnpy.trader.locale import _
from .table import DragonTigerTable, NorthboundTable


class ChinaDataWidget(QtWidgets.QWidget):
    """A股数据服务主界面"""

    def __init__(self, main_engine: Any, event_engine: Any):
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取GUI引擎
        self.gui_engine: Optional[Any] = None
        try:
            self.gui_engine = main_engine.get_engine("ChinaDataApp")
        except Exception:
            pass

        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle(_("A股数据服务"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab = QtWidgets.QTabWidget()
        layout.addWidget(tab)

        # 历史数据下载标签页
        download_widget = self.create_download_tab()
        tab.addTab(download_widget, _("历史数据"))

        # 龙虎榜数据标签页
        dt_widget = self.create_dragon_tiger_tab()
        tab.addTab(dt_widget, _("龙虎榜"))

        # 北向资金标签页
        nb_widget = self.create_northbound_tab()
        tab.addTab(nb_widget, _("北向资金"))

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def create_download_tab(self) -> QtWidgets.QWidget:
        """创建历史数据下载标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 说明文本
        desc = QtWidgets.QLabel(
            _("下载历史K线数据，用于机器学习模型训练和回测。"
              "首次使用建议下载至少3个月的历史数据。")
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(desc)

        # 配置区域
        config_group = QtWidgets.QGroupBox(_("下载配置"))
        config_layout = QtWidgets.QGridLayout()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 股票代码
        config_layout.addWidget(QtWidgets.QLabel(_("股票代码：")), 0, 0)
        self.symbols_input = QtWidgets.QPlainTextEdit()
        self.symbols_input.setPlaceholderText(
            _("每行一个股票代码，如：\n000001.SZ\n600000.SH\n\n留空则使用默认蓝筹股列表")
        )
        self.symbols_input.setMaximumHeight(80)
        config_layout.addWidget(self.symbols_input, 0, 1, 2, 3)

        # 快速填充按钮
        fill_default_btn = QtWidgets.QPushButton(_("使用默认股票"))
        fill_default_btn.clicked.connect(self.fill_default_symbols)
        config_layout.addWidget(fill_default_btn, 0, 4)

        # 日期范围
        config_layout.addWidget(QtWidgets.QLabel(_("开始日期：")), 2, 0)
        self.start_date_edit = QtWidgets.QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QtCore.QDate.currentDate().addMonths(-3))
        config_layout.addWidget(self.start_date_edit, 2, 1)

        config_layout.addWidget(QtWidgets.QLabel(_("结束日期：")), 2, 2)
        self.end_date_edit = QtWidgets.QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QtCore.QDate.currentDate())
        config_layout.addWidget(self.end_date_edit, 2, 3)

        # K线周期
        config_layout.addWidget(QtWidgets.QLabel(_("K线周期：")), 3, 0)
        self.interval_combo = QtWidgets.QComboBox()
        self.interval_combo.addItem(_("1分钟线"), Interval.MINUTE)
        self.interval_combo.addItem(_("5分钟线"), Interval.MINUTE)  # Tushare暂不支持
        self.interval_combo.addItem(_("日线"), Interval.DAILY)
        config_layout.addWidget(self.interval_combo, 3, 1, 1, 3)

        # 下载按钮
        button_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(button_layout)

        self.download_btn = QtWidgets.QPushButton(_("开始下载"))
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setStyleSheet("padding: 8px; font-weight: bold;")
        button_layout.addWidget(self.download_btn)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 日志区域
        log_group = QtWidgets.QGroupBox(_("下载日志"))
        log_layout = QtWidgets.QVBoxLayout()
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        # 统计信息
        self.stats_label = QtWidgets.QLabel(_("未开始下载"))
        self.stats_label.setStyleSheet("padding: 5px; background: #f0f0f0; font-weight: bold;")
        layout.addWidget(self.stats_label)

        return widget

    def fill_default_symbols(self) -> None:
        """填充默认股票代码"""
        if not self.gui_engine:
            return

        symbols = self.gui_engine.get_default_symbols()
        self.symbols_input.setPlainText("\n".join(symbols))
        self.show_status(_(f"已填充 {len(symbols)} 只默认股票"))

    def start_download(self) -> None:
        """开始下载历史数据"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        if self.gui_engine.is_downloading():
            self.show_status(_("下载任务正在进行中"))
            return

        # 获取股票列表
        symbols_text = self.symbols_input.toPlainText().strip()
        if symbols_text:
            symbols = [s.strip() for s in symbols_text.split("\n") if s.strip()]
        else:
            symbols = self.gui_engine.get_default_symbols()

        if not symbols:
            self.show_status(_("请输入或选择股票代码"))
            return

        # 获取日期范围
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()

        # 获取K线周期
        interval = self.interval_combo.currentData()

        # 清空日志
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.download_btn.setEnabled(False)
        self.download_btn.setText(_("下载中..."))

        # 异步下载
        QtCore.QTimer.singleShot(100, lambda: self._do_download(
            symbols, start_date, end_date, interval
        ))

    def _do_download(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: Interval
    ) -> None:
        """执行下载"""
        self.append_log(f"开始下载 {len(symbols)} 只股票的历史数据...")
        self.append_log(f"日期范围: {start_date} 至 {end_date}")
        self.append_log(f"K线周期: {interval.value}")

        result = self.gui_engine.download_history_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        # 更新结果
        if result["success"]:
            self.progress_bar.setValue(100)
            self.append_log(f"✓ 下载完成！")
            self.append_log(f"  成功: {result['downloaded_count']} 条数据")
            if result["failed_symbols"]:
                self.append_log(f"  失败: {len(result['failed_symbols'])} 只股票")
                for symbol in result["failed_symbols"]:
                    self.append_log(f"    - {symbol}")

            self.stats_label.setText(
                _(f"下载完成：{result['downloaded_count']} 条数据，"
                  f"{len(result['failed_symbols'])} 只股票失败")
            )
            self.show_status(_("下载完成"))
        else:
            self.append_log(f"✗ 下载失败: {result.get('error', '未知错误')}")
            self.stats_label.setText(_("下载失败"))
            self.show_status(_("下载失败"))

        self.download_btn.setEnabled(True)
        self.download_btn.setText(_("开始下载"))

    def append_log(self, message: str) -> None:
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def create_dragon_tiger_tab(self) -> QtWidgets.QWidget:
        """创建龙虎榜标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 控制面板
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_panel.setLayout(control_layout)

        # 日期选择
        control_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.dt_date_edit = QtWidgets.QDateEdit()
        self.dt_date_edit.setCalendarPopup(True)
        self.dt_date_edit.setDate(QtCore.QDate.currentDate())
        control_layout.addWidget(self.dt_date_edit)

        # 查询按钮
        self.dt_query_btn = QtWidgets.QPushButton(_("查询"))
        self.dt_query_btn.clicked.connect(self.query_dragon_tiger)
        control_layout.addWidget(self.dt_query_btn)

        # 刷新按钮
        self.dt_refresh_btn = QtWidgets.QPushButton(_("刷新"))
        self.dt_refresh_btn.clicked.connect(self.refresh_dragon_tiger)
        control_layout.addWidget(self.dt_refresh_btn)

        control_layout.addStretch()
        layout.addWidget(control_panel)

        # 数据表格
        self.dt_table = DragonTigerTable()
        layout.addWidget(self.dt_table)

        return widget

    def create_northbound_tab(self) -> QtWidgets.QWidget:
        """创建北向资金标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 控制面板
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_panel.setLayout(control_layout)

        # 日期选择
        control_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.nb_date_edit = QtWidgets.QDateEdit()
        self.nb_date_edit.setCalendarPopup(True)
        self.nb_date_edit.setDate(QtCore.QDate.currentDate())
        control_layout.addWidget(self.nb_date_edit)

        # 查询按钮
        self.nb_query_btn = QtWidgets.QPushButton(_("查询"))
        self.nb_query_btn.clicked.connect(self.query_northbound)
        control_layout.addWidget(self.nb_query_btn)

        # 刷新按钮
        self.nb_refresh_btn = QtWidgets.QPushButton(_("刷新"))
        self.nb_refresh_btn.clicked.connect(self.refresh_northbound)
        control_layout.addWidget(self.nb_refresh_btn)

        control_layout.addStretch()
        layout.addWidget(control_panel)

        # 数据表格
        self.nb_table = NorthboundTable()
        layout.addWidget(self.nb_table)

        return widget

    def query_dragon_tiger(self) -> None:
        """查询龙虎榜数据"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.dt_date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询龙虎榜数据..."))
        data = self.gui_engine.query_dragon_tiger(trade_date)

        self.dt_table.update_data(data)

        if data:
            self.show_status(_(f"查询完成，共{len(data)}条记录"))
        else:
            self.show_status(_("未查询到数据"))

    def refresh_dragon_tiger(self) -> None:
        """刷新龙虎榜数据（使用当前日期）"""
        self.dt_date_edit.setDate(QtCore.QDate.currentDate())
        self.query_dragon_tiger()

    def query_northbound(self) -> None:
        """查询北向资金数据"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.nb_date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询北向资金数据..."))
        data = self.gui_engine.query_northbound_flow(trade_date)

        self.nb_table.update_data(data)

        if data:
            self.show_status(_(f"查询完成，净流入：{data.total_net_inflow:.2f}亿元"))
        else:
            self.show_status(_("未查询到数据"))

    def refresh_northbound(self) -> None:
        """刷新北向资金数据（使用当前日期）"""
        self.nb_date_edit.setDate(QtCore.QDate.currentDate())
        self.query_northbound()

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaDataWidget"]
