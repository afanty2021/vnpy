# -*- coding: utf-8 -*-
"""
A股交易引擎 UI 组件

提供信号监控和风险告警面板组件。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vnpy_china_trading.object import (
    RiskCheckResult,
    SignalDirection,
    SignalSource,
    SignalStatus,
    TradingSignal,
)

logger = logging.getLogger(__name__)


class SignalMonitor(QWidget):
    """信号监控窗口

    提供交易信号的显示、确认和取消功能。

    Attributes:
        signal: 选中信号时发出信号
    """

    # 选中信号时发出的信号
    signal_selected = Signal(object)

    def __init__(
        self,
        signal_engine: Any,
        risk_engine: Any,
        main_engine: Any,
    ) -> None:
        """初始化信号监控窗口

        Args:
            signal_engine: 信号引擎实例
            risk_engine: 风险引擎实例
            main_engine: 主引擎实例
        """
        super().__init__()

        self.signal_engine = signal_engine
        self.risk_engine = risk_engine
        self.main_engine = main_engine

        self.signals: Dict[str, TradingSignal] = {}
        self.selected_signal: Optional[TradingSignal] = None

        self.init_ui()
        self.start_auto_refresh()

        logger.info("信号监控窗口初始化完成")

    def init_ui(self) -> None:
        """初始化UI组件"""
        self.setWindowTitle("交易信号监控")
        self.setGeometry(100, 100, 1000, 600)

        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 工具栏
        toolbar_layout = QHBoxLayout()
        main_layout.addLayout(toolbar_layout)

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        toolbar_layout.addWidget(self.refresh_button)

        # 确认下单按钮
        self.confirm_button = QPushButton("确认下单")
        self.confirm_button.clicked.connect(self.on_confirm_clicked)
        toolbar_layout.addWidget(self.confirm_button)

        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        toolbar_layout.addWidget(self.cancel_button)

        # 添加伸缩
        toolbar_layout.addStretch()

        # 信号表格
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(10)
        self.signal_table.setHorizontalHeaderLabels([
            "时间",
            "股票代码",
            "方向",
            "信号强度",
            "来源",
            "模型",
            "预测收益",
            "风控状态",
            "拒绝原因",
            "操作"
        ])
        self.signal_table.setAlternatingRowColors(True)
        self.signal_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.signal_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.signal_table.verticalHeader().setVisible(False)
        self.signal_table.itemSelectionChanged.connect(self.on_selection_changed)

        # 设置列宽
        header = self.signal_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)

        main_layout.addWidget(self.signal_table)

        # 详情面板
        detail_label = QLabel("信号详情:")
        detail_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        main_layout.addWidget(detail_label)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(150)
        main_layout.addWidget(self.detail_text)

        # 初始刷新
        self.refresh_signals()

    def start_auto_refresh(self) -> None:
        """启动自动刷新定时器"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_signals)
        self.refresh_timer.start(2000)  # 每2秒刷新

    def refresh_signals(self) -> None:
        """刷新信号列表"""
        # 获取所有待处理和已处理的信号
        pending_signals = self.signal_engine.get_pending_signals()
        all_signals = self.signal_engine.get_all_signals()

        # 更新信号字典
        self.signals = {s.signal_id: s for s in all_signals}

        # 清空表格
        self.signal_table.setRowCount(0)

        # 按时间排序（最新的在前）
        sorted_signals = sorted(
            all_signals,
            key=lambda x: x.created_time,
            reverse=True
        )

        # 填充表格
        for signal in sorted_signals:
            self._add_signal_row(signal)

    def _add_signal_row(self, signal: TradingSignal) -> None:
        """添加信号行到表格

        Args:
            signal: 信号对象
        """
        row = self.signal_table.rowCount()
        self.signal_table.insertRow(row)

        # 时间
        time_item = QTableWidgetItem(signal.created_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.signal_table.setItem(row, 0, time_item)

        # 股票代码
        symbol_item = QTableWidgetItem(signal.symbol)
        self.signal_table.setItem(row, 1, symbol_item)

        # 方向
        direction_text = {
            SignalDirection.LONG: "做多",
            SignalDirection.SHORT: "做空",
            SignalDirection.CLOSE: "平仓",
            SignalDirection.HOLD: "持仓"
        }.get(signal.direction, str(signal.direction))
        direction_item = QTableWidgetItem(direction_text)
        self.signal_table.setItem(row, 2, direction_item)

        # 信号强度
        strength_item = QTableWidgetItem(f"{signal.strength:.2f}")
        self.signal_table.setItem(row, 3, strength_item)

        # 来源
        source_text = {
            SignalSource.ALPHA158: "Alpha158",
            SignalSource.CUSTOM: "自定义",
            SignalSource.MANUAL: "人工",
            SignalSource.ML_MODEL: "机器学习"
        }.get(signal.source, str(signal.source))
        source_item = QTableWidgetItem(source_text)
        self.signal_table.setItem(row, 4, source_item)

        # 模型名称
        model_item = QTableWidgetItem(signal.model_name or "-")
        self.signal_table.setItem(row, 5, model_item)

        # 预测收益
        predicted = signal.predicted_return
        predicted_text = f"{predicted:.4f}" if predicted is not None else "-"
        predicted_item = QTableWidgetItem(predicted_text)
        self.signal_table.setItem(row, 6, predicted_item)

        # 风控状态
        status_text = {
            SignalStatus.PENDING: "待处理",
            SignalStatus.RISK_CHECKING: "风控检查中",
            SignalStatus.RISK_PASSED: "风控通过",
            SignalStatus.RISK_REJECTED: "风控拒绝",
            SignalStatus.CONFIRMED: "已确认",
            SignalStatus.EXECUTED: "已执行",
            SignalStatus.CANCELLED: "已取消"
        }.get(signal.status, str(signal.status))
        status_item = QTableWidgetItem(status_text)
        self.signal_table.setItem(row, 7, status_item)

        # 拒绝原因
        reject_reason = ""
        if signal.risk_check_result and not signal.risk_check_result.passed:
            reject_reason = "; ".join(signal.risk_check_result.reasons)
        reject_item = QTableWidgetItem(reject_reason)
        self.signal_table.setItem(row, 8, reject_item)

        # 操作
        action_text = self._get_action_text(signal)
        action_item = QTableWidgetItem(action_text)
        self.signal_table.setItem(row, 9, action_item)

        # 根据状态设置行颜色
        self._set_row_color(row, signal)

    def _get_action_text(self, signal: TradingSignal) -> str:
        """获取操作提示文本

        Args:
            signal: 信号对象

        Returns:
            操作提示文本
        """
        if signal.status == SignalStatus.PENDING:
            return "待确认"
        elif signal.status == SignalStatus.RISK_CHECKING:
            return "检查中"
        elif signal.status == SignalStatus.RISK_PASSED:
            return "可确认"
        elif signal.status == SignalStatus.RISK_REJECTED:
            return "已拒绝"
        elif signal.status == SignalStatus.CONFIRMED:
            return "已确认"
        elif signal.status == SignalStatus.EXECUTED:
            return "已执行"
        elif signal.status == SignalStatus.CANCELLED:
            return "已取消"
        return "未知"

    def _set_row_color(self, row: int, signal: TradingSignal) -> None:
        """根据信号状态设置行颜色

        Args:
            row: 行索引
            signal: 信号对象
        """
        # 待处理和风控检查中 - 黄色
        if signal.status in (SignalStatus.PENDING, SignalStatus.RISK_CHECKING):
            color = QColor(255, 255, 200)  # 浅黄色
        # 风控通过 - 绿色
        elif signal.status == SignalStatus.RISK_PASSED:
            color = QColor(200, 255, 200)  # 浅绿色
        # 风控拒绝 - 红色
        elif signal.status == SignalStatus.RISK_REJECTED:
            color = QColor(255, 200, 200)  # 浅红色
        # 已确认、已执行 - 蓝色
        elif signal.status in (SignalStatus.CONFIRMED, SignalStatus.EXECUTED):
            color = QColor(200, 220, 255)  # 浅蓝色
        # 已取消 - 灰色
        elif signal.status == SignalStatus.CANCELLED:
            color = QColor(230, 230, 230)  # 浅灰色
        else:
            return

        for col in range(self.signal_table.columnCount()):
            item = self.signal_table.item(row, col)
            if item:
                item.setBackground(color)

    def on_selection_changed(self) -> None:
        """选中信号变化时的处理"""
        selected_rows = self.signal_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_signal = None
            self.detail_text.clear()
            return

        row = selected_rows[0].row()
        signal_id_item = self.signal_table.item(row, 0)
        if not signal_id_item:
            return

        # 通过时间查找信号（简化实现）
        time_str = signal_id_item.text()
        for signal in self.signals.values():
            if signal.created_time.strftime("%Y-%m-%d %H:%M:%S") == time_str:
                self.selected_signal = signal
                self._update_detail_panel(signal)
                self.signal_selected.emit(signal)
                break

    def _update_detail_panel(self, signal: TradingSignal) -> None:
        """更新详情面板

        Args:
            signal: 信号对象
        """
        detail_lines = [
            f"信号ID: {signal.signal_id}",
            f"股票代码: {signal.symbol}",
            f"交易所: {signal.exchange}",
            f"方向: {signal.direction.value}",
            f"信号强度: {signal.strength:.2f}",
            f"来源: {signal.source.value}",
            f"模型: {signal.model_name or 'N/A'}",
            f"预测收益率: {signal.predicted_return:.4f}" if signal.predicted_return else "预测收益率: N/A",
            f"置信度: {signal.confidence:.2f}" if signal.confidence else "置信度: N/A",
            f"创建时间: {signal.created_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"状态: {signal.status.value}",
        ]

        if signal.risk_check_result:
            result = signal.risk_check_result
            detail_lines.append(f"\n风控检查结果:")
            detail_lines.append(f"  通过: {'是' if result.passed else '否'}")
            if result.reasons:
                detail_lines.append(f"  拒绝原因: {'; '.join(result.reasons)}")
            if result.warnings:
                detail_lines.append(f"  警告: {'; '.join(result.warnings)}")

        self.detail_text.setText("\n".join(detail_lines))

    def on_refresh_clicked(self) -> None:
        """刷新按钮点击处理"""
        self.refresh_signals()
        logger.info("手动刷新信号列表")

    def on_confirm_clicked(self) -> None:
        """确认下单按钮点击处理"""
        if not self.selected_signal:
            QMessageBox.warning(self, "警告", "请先选择要确认的信号")
            return

        signal = self.selected_signal

        # 检查是否已确认或已执行
        if signal.status in (SignalStatus.CONFIRMED, SignalStatus.EXECUTED):
            QMessageBox.information(self, "提示", "该信号已确认或已执行")
            return

        # 检查是否已取消
        if signal.status == SignalStatus.CANCELLED:
            QMessageBox.warning(self, "警告", "该信号已取消")
            return

        # 执行风控检查
        risk_result = self.risk_engine.check_signal(signal)

        if risk_result.passed:
            # 风控通过，更新信号状态
            self.signal_engine.update_signal_status(
                signal.signal_id,
                SignalStatus.RISK_PASSED,
                risk_result
            )
            self.signal_engine.confirm_signal(signal.signal_id)

            QMessageBox.information(self, "成功", f"信号 {signal.signal_id} 已确认")
            logger.info(f"信号确认成功: {signal.signal_id}")
        else:
            # 风控拒绝
            reject_reason = "; ".join(risk_result.reasons)
            self.signal_engine.update_signal_status(
                signal.signal_id,
                SignalStatus.RISK_REJECTED,
                risk_result
            )

            QMessageBox.warning(self, "风控拒绝", f"信号被风控拒绝:\n{reject_reason}")
            logger.warning(f"信号风控拒绝: {signal.signal_id}, 原因: {reject_reason}")

        self.refresh_signals()

    def on_cancel_clicked(self) -> None:
        """取消按钮点击处理"""
        if not self.selected_signal:
            QMessageBox.warning(self, "警告", "请先选择要取消的信号")
            return

        signal = self.selected_signal

        # 检查是否已确认或已执行
        if signal.status in (SignalStatus.CONFIRMED, SignalStatus.EXECUTED):
            QMessageBox.warning(self, "警告", "已确认或已执行的信号无法取消")
            return

        # 确认取消
        reply = QMessageBox.question(
            self,
            "确认取消",
            f"确定要取消信号 {signal.signal_id} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.signal_engine.cancel_signal(signal.signal_id)
            QMessageBox.information(self, "成功", f"信号 {signal.signal_id} 已取消")
            logger.info(f"信号取消成功: {signal.signal_id}")
            self.refresh_signals()

    def closeEvent(self, event: Any) -> None:
        """窗口关闭事件

        Args:
            event: 关闭事件
        """
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        logger.info("信号监控窗口已关闭")
        event.accept()


class RiskAlertPanel(QWidget):
    """风险告警面板

    显示风险检查告警信息。
    """

    # 告警类型常量
    ALERT_TYPE_WARNING = "警告"
    ALERT_TYPE_ERROR = "错误"
    ALERT_TYPE_INFO = "信息"

    def __init__(self, risk_engine: Any) -> None:
        """初始化风险告警面板

        Args:
            risk_engine: 风险引擎实例
        """
        super().__init__()

        self.risk_engine = risk_engine
        self.alerts: List[Dict[str, Any]] = []

        self.init_ui()
        logger.info("风险告警面板初始化完成")

    def init_ui(self) -> None:
        """初始化UI组件"""
        self.setWindowTitle("风险告警")
        self.setGeometry(150, 150, 600, 400)

        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 标题
        title_label = QLabel("风险告警记录")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        main_layout.addWidget(title_label)

        # 告警表格
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(4)
        self.alert_table.setHorizontalHeaderLabels([
            "时间",
            "类型",
            "股票代码",
            "描述"
        ])
        self.alert_table.setAlternatingRowColors(True)
        self.alert_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.alert_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.alert_table.verticalHeader().setVisible(False)

        # 设置列宽模式
        header = self.alert_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        main_layout.addWidget(self.alert_table)

        # 清空按钮
        clear_button = QPushButton("清空告警")
        clear_button.clicked.connect(self.clear_alerts)
        main_layout.addWidget(clear_button)

    def add_alert(
        self,
        alert_type: str,
        symbol: str,
        message: str
    ) -> None:
        """添加告警

        Args:
            alert_type: 告警类型（警告/错误/信息）
            symbol: 股票代码
            message: 告警消息
        """
        alert = {
            "time": datetime.now(),
            "type": alert_type,
            "symbol": symbol,
            "message": message
        }

        self.alerts.append(alert)
        logger.info(f"添加风险告警: {alert_type} - {symbol} - {message}")

        # 更新表格
        self._refresh_alert_table()

    def _refresh_alert_table(self) -> None:
        """刷新告警表格"""
        self.alert_table.setRowCount(0)

        # 按时间倒序显示
        for alert in reversed(self.alerts):
            row = self.alert_table.rowCount()
            self.alert_table.insertRow(row)

            # 时间
            time_item = QTableWidgetItem(
                alert["time"].strftime("%Y-%m-%d %H:%M:%S")
            )
            self.alert_table.setItem(row, 0, time_item)

            # 类型
            type_item = QTableWidgetItem(alert["type"])
            self.alert_table.setItem(row, 1, type_item)

            # 股票代码
            symbol_item = QTableWidgetItem(alert["symbol"])
            self.alert_table.setItem(row, 2, symbol_item)

            # 描述
            message_item = QTableWidgetItem(alert["message"])
            self.alert_table.setItem(row, 3, message_item)

            # 根据告警类型设置颜色
            self._set_alert_row_color(row, alert["type"])

    def _set_alert_row_color(self, row: int, alert_type: str) -> None:
        """根据告警类型设置行颜色

        Args:
            row: 行索引
            alert_type: 告警类型
        """
        if alert_type == self.ALERT_TYPE_ERROR:
            color = QColor(255, 200, 200)  # 浅红色
        elif alert_type == self.ALERT_TYPE_WARNING:
            color = QColor(255, 255, 200)  # 浅黄色
        elif alert_type == self.ALERT_TYPE_INFO:
            color = QColor(200, 255, 200)  # 浅绿色
        else:
            return

        for col in range(self.alert_table.columnCount()):
            item = self.alert_table.item(row, col)
            if item:
                item.setBackground(color)

    def clear_alerts(self) -> None:
        """清空所有告警"""
        self.alerts.clear()
        self.alert_table.setRowCount(0)
        logger.info("清空风险告警记录")


__all__ = ["SignalMonitor", "RiskAlertPanel"]
