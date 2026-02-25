"""A股机器学习UI组件"""
from typing import Any, Optional
from datetime import datetime

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.locale import _


class ChinaMlWidget(QtWidgets.QWidget):
    """A股机器学习主界面"""

    def __init__(self, main_engine: Any, event_engine: Any):
        """初始化界面"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取GUI引擎
        self.gui_engine: Optional[Any] = None
        try:
            self.gui_engine = main_engine.get_engine("ChinaMlApp")
        except Exception:
            pass

        # 预测结果数据
        self.predictions: list = []

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(_("A股机器学习"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab = QtWidgets.QTabWidget()
        layout.addWidget(tab)

        # 模型管理标签页
        model_widget = self.create_model_tab()
        tab.addTab(model_widget, _("模型管理"))

        # 特征工程标签页
        feature_widget = self.create_feature_tab()
        tab.addTab(feature_widget, _("特征工程"))

        # 预测结果标签页
        prediction_widget = self.create_prediction_tab()
        tab.addTab(prediction_widget, _("预测结果"))

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def create_model_tab(self) -> QtWidgets.QWidget:
        """创建模型管理标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("模型管理"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 模型列表区
        model_group = QtWidgets.QGroupBox(_("已训练模型"))
        model_layout = QtWidgets.QVBoxLayout()
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 模型表格
        self.model_table = QtWidgets.QTableWidget()
        self.model_table.setColumnCount(5)
        self.model_table.setHorizontalHeaderLabels([
            _("模型名称"), _("类型"), _("训练时间"),
            _("准确率"), _("状态")
        ])
        self.model_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.model_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.model_table.resizeColumnsToContents()
        model_layout.addWidget(self.model_table)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        model_layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_models)
        toolbar.addWidget(refresh_btn)

        train_btn = QtWidgets.QPushButton(_("训练新模型"))
        train_btn.clicked.connect(self.train_model)
        toolbar.addWidget(train_btn)

        delete_btn = QtWidgets.QPushButton(_("删除模型"))
        delete_btn.clicked.connect(self.delete_model)
        toolbar.addWidget(delete_btn)

        toolbar.addStretch()

        # 训练配置区
        config_group = QtWidgets.QGroupBox(_("训练配置"))
        config_layout = QtWidgets.QGridLayout()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 模型类型
        config_layout.addWidget(QtWidgets.QLabel(_("模型类型：")), 0, 0)
        self.model_type_combo = QtWidgets.QComboBox()
        self.model_type_combo.addItems([_("LightGBM"), _("XGBoost"), ("随机森林"), ("LSTM")])
        config_layout.addWidget(self.model_type_combo, 0, 1)

        # 训练天数
        config_layout.addWidget(QtWidgets.QLabel(_("训练天数：")), 0, 2)
        self.train_days_input = QtWidgets.QLineEdit("252")
        config_layout.addWidget(self.train_days_input, 0, 3)

        # 特征数量
        config_layout.addWidget(QtWidgets.QLabel(_("特征数量：")), 1, 0)
        self.feature_count_input = QtWidgets.QLineEdit("158")
        config_layout.addWidget(self.feature_count_input, 1, 1)

        # 开始训练按钮
        start_train_btn = QtWidgets.QPushButton(_("开始训练"))
        start_train_btn.clicked.connect(self.start_training)
        config_layout.addWidget(start_train_btn, 1, 2, 1, 2)

        # 训练进度
        self.train_progress = QtWidgets.QProgressBar()
        self.train_progress.setRange(0, 100)
        self.train_progress.setValue(0)
        layout.addWidget(self.train_progress)

        return widget

    def create_feature_tab(self) -> QtWidgets.QWidget:
        """创建特征工程标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("特征工程"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 特征列表区
        feature_group = QtWidgets.QGroupBox(_("Alpha 158因子"))
        feature_layout = QtWidgets.QVBoxLayout()
        feature_group.setLayout(feature_layout)
        layout.addWidget(feature_group)

        # 特征表格
        self.feature_table = QtWidgets.QTableWidget()
        self.feature_table.setColumnCount(4)
        self.feature_table.setHorizontalHeaderLabels([
            _("因子名称"), _("类型"), _("重要性"), _("相关系数")
        ])
        self.feature_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.feature_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.feature_table.setRowCount(20)  # 显示前20个因子
        feature_layout.addWidget(self.feature_table)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新重要性"))
        refresh_btn.clicked.connect(self.refresh_feature_importance)
        toolbar.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton(_("导出特征"))
        export_btn.clicked.connect(self.export_features)
        toolbar.addWidget(export_btn)

        toolbar.addStretch()

        # 填充示例特征数据
        self._populate_mock_features()

        return widget

    def create_prediction_tab(self) -> QtWidgets.QWidget:
        """创建预测结果标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("预测结果"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 预测控制区
        control_group = QtWidgets.QGroupBox(_("预测控制"))
        control_layout = QtWidgets.QHBoxLayout()
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 模型选择
        control_layout.addWidget(QtWidgets.QLabel(_("选择模型：")))
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.addItems([_("LightGBM_v1"), _("XGBoost_v2"), ("随机森林_v1")])
        control_layout.addWidget(self.model_combo)

        # 预测日期
        control_layout.addWidget(QtWidgets.QLabel(_("预测日期：")))
        self.predict_date_edit = QtWidgets.QDateEdit()
        self.predict_date_edit.setCalendarPopup(True)
        self.predict_date_edit.setDate(QtCore.QDate.currentDate())
        control_layout.addWidget(self.predict_date_edit)

        # 预测按钮
        predict_btn = QtWidgets.QPushButton(_("开始预测"))
        predict_btn.clicked.connect(self.start_prediction)
        control_layout.addWidget(predict_btn)

        control_layout.addStretch()

        # 预测结果区
        result_group = QtWidgets.QGroupBox(_("预测列表"))
        result_layout = QtWidgets.QVBoxLayout()
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 预测表格
        self.prediction_table = QtWidgets.QTableWidget()
        self.prediction_table.setColumnCount(5)
        self.prediction_table.setHorizontalHeaderLabels([
            _("股票代码"), _("股票名称"), _("预测方向"),
            _("置信度"), _("预测时间")
        ])
        self.prediction_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.prediction_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        result_layout.addWidget(self.prediction_table)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_predictions)
        toolbar.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton(_("导出结果"))
        export_btn.clicked.connect(self.export_predictions)
        toolbar.addWidget(export_btn)

        clear_btn = QtWidgets.QPushButton(_("清空"))
        clear_btn.clicked.connect(self.clear_predictions)
        toolbar.addWidget(clear_btn)

        return widget

    def refresh_models(self) -> None:
        """刷新模型列表"""
        # 模拟数据
        models = [
            {"name": "LightGBM_v1", "type": "LightGBM", "time": "2026-02-20", "accuracy": 0.65, "status": "已部署"},
            {"name": "XGBoost_v2", "type": "XGBoost", "time": "2026-02-18", "accuracy": 0.62, "status": "待部署"},
            {"name": "RandomForest_v1", "type": "随机森林", "time": "2026-02-15", "accuracy": 0.58, "status": "已部署"},
        ]

        self.model_table.setRowCount(len(models))
        for row, model in enumerate(models):
            self.model_table.setItem(row, 0, QtWidgets.QTableWidgetItem(model["name"]))
            self.model_table.setItem(row, 1, QtWidgets.QTableWidgetItem(model["type"]))
            self.model_table.setItem(row, 2, QtWidgets.QTableWidgetItem(model["time"]))
            acc_item = QtWidgets.QTableWidgetItem(f"{model['accuracy']:.2%}")
            self.model_table.setItem(row, 3, acc_item)
            self.model_table.setItem(row, 4, QtWidgets.QTableWidgetItem(model["status"]))

        self.model_table.resizeColumnsToContents()
        self.show_status(_("模型列表已更新"))

    def train_model(self) -> None:
        """训练新模型"""
        self.show_status(_("请在下方配置训练参数后点击开始训练"))

    def delete_model(self) -> None:
        """删除选中的模型"""
        current_row = self.model_table.currentRow()
        if current_row >= 0:
            self.model_table.removeRow(current_row)
            self.show_status(_("模型已删除"))
        else:
            self.show_status(_("请先选择要删除的模型"))

    def start_training(self) -> None:
        """开始训练"""
        model_type = self.model_type_combo.currentText()
        self.show_status(_(f"正在训练{model_type}模型..."))

        # 模拟训练进度
        for i in range(0, 101, 10):
            self.train_progress.setValue(i)
            QtCore.QTimer.singleShot(100, lambda: None)

        # 添加新模型到列表
        row = self.model_table.rowCount()
        self.model_table.insertRow(row)
        self.model_table.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{model_type}_v{row + 1}"))
        self.model_table.setItem(row, 1, QtWidgets.QTableWidgetItem(model_type))
        self.model_table.setItem(row, 2, QtWidgets.QTableWidgetItem(datetime.now().strftime("%Y-%m-%d")))
        self.model_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{0.60 + row * 0.01:.2%}"))
        self.model_table.setItem(row, 4, QtWidgets.QTableWidgetItem("待部署"))

        self.show_status(_(f"{model_type}模型训练完成"))
        self.train_progress.setValue(0)

    def refresh_feature_importance(self) -> None:
        """刷新特征重要性"""
        self._populate_mock_features()
        self.show_status(_("特征重要性已更新"))

    def _populate_mock_features(self) -> None:
        """填充模拟特征数据"""
        # Alpha 158因子示例
        features = [
            ("Return_5d", "动量", 0.85, 0.65),
            ("Return_10d", "动量", 0.78, 0.58),
            ("Volume_Ratio", "成交量", 0.72, 0.45),
            ("MACD_Signal", "技术指标", 0.68, 0.52),
            ("RSI_14", "技术指标", 0.65, 0.38),
            ("Bollinger_Width", "波动率", 0.62, 0.42),
            ("ATR_14", "波动率", 0.58, 0.35),
            ("STOCH_K", "技术指标", 0.55, 0.31),
            ("CCI_20", "技术指标", 0.52, 0.28),
            ("MFI_14", "资金流", 0.48, 0.25),
            ("OBV", "资金流", 0.45, 0.22),
            ("ADXR", "趋势", 0.42, 0.19),
            ("Minus_DI", "趋势", 0.38, 0.15),
            ("Plus_DM", "趋势", 0.35, 0.12),
            ("TRIX", "趋势", 0.32, 0.10),
            ("Mass_Index", "波动率", 0.28, 0.08),
            ("Chaikin_Volatility", "波动率", 0.25, 0.06),
            ("ROC", "动量", 0.22, 0.05),
            ("Williams_R", "技术指标", 0.18, 0.03),
            ("Ultimate_Oscillator", "技术指标", 0.15, 0.02),
        ]

        for row, (name, ftype, importance, correlation) in enumerate(features):
            self.feature_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.feature_table.setItem(row, 1, QtWidgets.QTableWidgetItem(ftype))
            imp_item = QtWidgets.QTableWidgetItem(f"{importance:.2f}")
            imp_item.setForeground(QtGui.QColor("red"))
            self.feature_table.setItem(row, 2, imp_item)
            corr_item = QtWidgets.QTableWidgetItem(f"{correlation:.2f}")
            self.feature_table.setItem(row, 3, corr_item)

        self.feature_table.resizeColumnsToContents()

    def export_features(self) -> None:
        """导出特征"""
        self.show_status(_("特征已导出（模拟）"))

    def start_prediction(self) -> None:
        """开始预测"""
        model = self.model_combo.currentText()
        predict_date = self.predict_date_edit.date().toPython()

        self.show_status(_(f"正在使用{model}进行预测..."))

        # 模拟预测结果
        import random
        predictions = []
        symbols = ["000001", "000002", "600000", "600036", "600519"]
        names = ["平安银行", "万科A", "浦发银行", "招商银行", "贵州茅台"]
        directions = ["上涨", "下跌", "中性"]

        for i in range(10):
            idx = random.randint(0, len(symbols) - 1)
            pred = {
                "symbol": f"{symbols[idx]}.SZSE" if symbols[idx].startswith("000") else f"{symbols[idx]}.SSE",
                "name": names[idx],
                "direction": random.choice(directions),
                "confidence": random.uniform(0.55, 0.90),
                "time": datetime.now().strftime("%H:%M:%S"),
            }
            predictions.append(pred)

        self.predictions = predictions
        self._update_prediction_table()
        self.show_status(_(f"预测完成，共{len(predictions)}只股票"))

    def refresh_predictions(self) -> None:
        """刷新预测结果"""
        self._update_prediction_table()
        self.show_status(_(f"预测列表已更新，共{len(self.predictions)}条记录"))

    def _update_prediction_table(self) -> None:
        """更新预测表格"""
        self.prediction_table.setRowCount(len(self.predictions))

        for row, pred in enumerate(self.predictions):
            self.prediction_table.setItem(row, 0, QtWidgets.QTableWidgetItem(pred["symbol"]))
            self.prediction_table.setItem(row, 1, QtWidgets.QTableWidgetItem(pred["name"]))

            # 方向（带颜色）
            direction_item = QtWidgets.QTableWidgetItem(pred["direction"])
            if pred["direction"] == "上涨":
                direction_item.setForeground(QtGui.QColor("red"))
            elif pred["direction"] == "下跌":
                direction_item.setForeground(QtGui.QColor("green"))
            self.prediction_table.setItem(row, 2, direction_item)

            # 置信度
            conf_item = QtWidgets.QTableWidgetItem(f"{pred['confidence']:.2%}")
            if pred['confidence'] > 0.7:
                conf_item.setForeground(QtGui.QColor("red"))
            self.prediction_table.setItem(row, 3, conf_item)

            self.prediction_table.setItem(row, 4, QtWidgets.QTableWidgetItem(pred["time"]))

        self.prediction_table.resizeColumnsToContents()

    def export_predictions(self) -> None:
        """导出预测结果"""
        if not self.predictions:
            self.show_status(_("无可导出的数据"))
            return
        self.show_status(_("预测结果已导出（模拟）"))

    def clear_predictions(self) -> None:
        """清空预测结果"""
        self.predictions = []
        self.prediction_table.setRowCount(0)
        self.show_status(_("预测结果已清空"))

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaMlWidget"]
