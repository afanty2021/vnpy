"""A股机器学习UI组件"""
from typing import Any, Optional
from datetime import datetime, date

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.locale import _

from ..model.manager import ModelMetadata
from ..utils.types import ModelType, PredictionResult, SignalType


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

        # 模型ID映射（用于UI选择）
        self._model_ids: dict = {}

        self.init_ui()

        # 初始化时加载模型和特征数据（不阻塞启动）
        if self.gui_engine:
            self.refresh_models()
            # 尝试计算特征数据（失败不阻塞）
            try:
                self.gui_engine.calculate_features(
                    symbols=["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "600519.SH"],
                    start_date=date.today().replace(day=1),
                    end_date=date.today()
                )
                self._update_feature_table_from_engine()
            except Exception as e:
                # 特征计算失败不影响界面启动
                self.show_status(_("提示：请先下载历史数据以使用预测功能"))

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
        self.model_type_combo.addItem(_("LightGBM"), ModelType.LIGHTGBM)
        self.model_type_combo.addItem(_("XGBoost"), ModelType.XGBOOST)
        self.model_type_combo.addItem(_("随机森林"), ModelType.RANDOM_FOREST)
        self.model_type_combo.addItem(_("LSTM"), ModelType.LSTM)
        config_layout.addWidget(self.model_type_combo, 0, 1)

        # 训练天数
        config_layout.addWidget(QtWidgets.QLabel(_("训练天数：")), 0, 2)
        self.train_days_input = QtWidgets.QLineEdit("252")
        config_layout.addWidget(self.train_days_input, 0, 3)

        # 特征数量
        config_layout.addWidget(QtWidgets.QLabel(_("特征数量：")), 1, 0)
        self.feature_count_input = QtWidgets.QLineEdit("20")
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

    # ==================== 模型管理功能 ====================

    def refresh_models(self) -> None:
        """刷新模型列表"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        models = self.gui_engine.get_all_models()

        self.model_table.setRowCount(len(models))
        self._model_ids.clear()
        self.model_combo.clear()

        for row, metadata in enumerate(models):
            self._model_ids[row] = metadata.model_id

            self.model_table.setItem(row, 0, QtWidgets.QTableWidgetItem(metadata.model_name))
            self.model_table.setItem(row, 1, QtWidgets.QTableWidgetItem(metadata.model_type.value))

            time_str = metadata.training_date.strftime("%Y-%m-%d") if metadata.training_date else ""
            self.model_table.setItem(row, 2, QtWidgets.QTableWidgetItem(time_str))

            acc_item = QtWidgets.QTableWidgetItem(f"{metadata.accuracy:.2%}")
            self.model_table.setItem(row, 3, acc_item)
            self.model_table.setItem(row, 4, QtWidgets.QTableWidgetItem(metadata.status))

            # 添加到预测下拉框
            display_name = f"{metadata.model_name} ({metadata.model_type.value})"
            self.model_combo.addItem(display_name, metadata.model_id)

        self.model_table.resizeColumnsToContents()
        self.show_status(_(f"模型列表已更新，共{len(models)}个模型"))

    def train_model(self) -> None:
        """训练新模型提示"""
        self.show_status(_("请在下方配置训练参数后点击开始训练"))

    def delete_model(self) -> None:
        """删除选中的模型"""
        if not self.gui_engine:
            return

        current_row = self.model_table.currentRow()
        if current_row >= 0 and current_row in self._model_ids:
            model_id = self._model_ids[current_row]
            if self.gui_engine.delete_model(model_id):
                self.model_table.removeRow(current_row)
                del self._model_ids[current_row]
                self.show_status(_("模型已删除"))
            else:
                self.show_status(_("删除模型失败"))
        else:
            self.show_status(_("请先选择要删除的模型"))

    def start_training(self) -> None:
        """开始训练"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        # 获取训练参数
        model_type = self.model_type_combo.currentData()
        train_days_str = self.train_days_input.text()

        try:
            train_days = int(train_days_str)
        except ValueError:
            self.show_status(_("训练天数必须是数字"))
            return

        # 计算训练日期范围
        end_date = date.today()
        start_date = end_date.replace(day=1)  # 简单处理，使用月初
        # 实际应该减去train_days天

        model_name = f"{model_type.value}_model"

        self.show_status(_(f"正在训练{model_type.value}模型..."))
        self.train_progress.setValue(10)

        # 设置进度回调
        self.gui_engine.set_progress_callback(lambda v: self.train_progress.setValue(v))

        # 异步训练（使用定时器模拟）
        QtCore.QTimer.singleShot(100, lambda: self._do_training(
            model_type, model_name, start_date, end_date
        ))

    def _do_training(
        self,
        model_type: ModelType,
        model_name: str,
        start_date: date,
        end_date: date
    ) -> None:
        """执行训练"""
        if not self.gui_engine:
            return

        try:
            model_id = self.gui_engine.train_model(
                model_type=model_type,
                model_name=model_name,
                train_start=start_date,
                train_end=end_date,
                lookback_days=60,
                forward_days=5
            )

            if model_id:
                self.show_status(_(f"{model_type.value}模型训练完成"))
                self.refresh_models()
            else:
                self.show_status(_("模型训练失败"))

        except RuntimeError as e:
            # 显示详细错误信息
            error_msg = str(e)
            QtWidgets.QMessageBox.warning(
                self,
                _("训练失败"),
                _("无法训练模型：\n\n{error}\n\n请先下载历史数据后再试").format(error=error_msg)
            )
            self.show_status(_("训练失败 - 请先下载历史数据"))
        except Exception as e:
            self.show_status(_(f"模型训练失败: {e}"))

        self.train_progress.setValue(0)

    # ==================== 特征工程功能 ====================

    def refresh_feature_importance(self) -> None:
        """刷新特征重要性"""
        if not self.gui_engine:
            return

        # 获取当前选中的模型
        current_row = self.model_table.currentRow()
        if current_row >= 0 and current_row in self._model_ids:
            model_id = self._model_ids[current_row]
            try:
                importance_dict = self.gui_engine.get_feature_importance(model_id)

                if importance_dict:
                    self._update_feature_table_from_importance(importance_dict)
                    self.show_status(_("特征重要性已更新"))
                else:
                    self.show_status(_("无法获取特征重要性"))
            except RuntimeError as e:
                error_msg = str(e)
                QtWidgets.QMessageBox.warning(
                    self,
                    _("获取特征重要性失败"),
                    _("无法获取特征重要性：\n\n{error}").format(error=error_msg)
                )
                self.show_status(_("特征重要性获取失败"))
        else:
            self.show_status(_("请先选择一个模型"))

    def _update_feature_table_from_importance(self, importance_dict: dict) -> None:
        """从特征重要性更新表格"""
        self.feature_table.setRowCount(len(importance_dict))

        for row, (name, importance) in enumerate(importance_dict.items()):
            self.feature_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))

            # 根据因子名称推断类型
            ftype = self._infer_factor_type(name)
            self.feature_table.setItem(row, 1, QtWidgets.QTableWidgetItem(ftype))

            imp_item = QtWidgets.QTableWidgetItem(f"{importance:.4f}")
            imp_item.setForeground(QtGui.QColor("red"))
            self.feature_table.setItem(row, 2, imp_item)

            # 相关系数暂时留空
            self.feature_table.setItem(row, 3, QtWidgets.QTableWidgetItem(""))

        self.feature_table.resizeColumnsToContents()

    def _update_feature_table_from_engine(self) -> None:
        """从引擎更新特征表格"""
        if not self.gui_engine:
            return

        df = self.gui_engine.get_cached_features()
        if df is None:
            return

        # 将Polars DataFrame转换为列表
        features = df.rows()

        for row, (name, ftype, importance, correlation) in enumerate(features[:20]):
            self.feature_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.feature_table.setItem(row, 1, QtWidgets.QTableWidgetItem(ftype))

            imp_item = QtWidgets.QTableWidgetItem(f"{importance:.2f}")
            imp_item.setForeground(QtGui.QColor("red"))
            self.feature_table.setItem(row, 2, imp_item)

            corr_item = QtWidgets.QTableWidgetItem(f"{correlation:.2f}")
            self.feature_table.setItem(row, 3, corr_item)

        self.feature_table.resizeColumnsToContents()

    def _infer_factor_type(self, factor_name: str) -> str:
        """根据因子名称推断类型"""
        name_lower = factor_name.lower()

        if "return" in name_lower or "roc" in name_lower:
            return "动量"
        elif "volume" in name_lower or "obv" in name_lower or "mfi" in name_lower:
            return "成交量" if "volume" in name_lower else "资金流"
        elif "macd" in name_lower or "rsi" in name_lower or "stoch" in name_lower or "cci" in name_lower or "williams" in name_lower:
            return "技术指标"
        elif "bollinger" in name_lower or "atr" in name_lower or "volatility" in name_lower:
            return "波动率"
        elif "adx" in name_lower or "di" in name_lower or "trix" in name_lower:
            return "趋势"
        else:
            return "其他"

    def export_features(self) -> None:
        """导出特征"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        df = self.gui_engine.get_cached_features()
        if df is None:
            self.show_status(_("无可导出的特征数据"))
            return

        # TODO: 实现Excel导出
        self.show_status(_("特征导出功能待实现"))

    # ==================== 预测功能 ====================

    def start_prediction(self) -> None:
        """开始预测"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        # 获取选中的模型
        model_id = self.model_combo.currentData()
        if not model_id:
            self.show_status(_("请先选择模型"))
            return

        predict_date = self.predict_date_edit.date().toPython()

        self.show_status(_(f"正在使用模型 {model_id} 进行预测..."))

        # 预测股票列表
        symbols = [
            "000001.SZ", "000002.SZ", "600000.SH",
            "600036.SH", "600519.SH"
        ]

        # 异步预测
        QtCore.QTimer.singleShot(100, lambda: self._do_prediction(
            model_id, symbols, predict_date
        ))

    def _do_prediction(self, model_id: str, symbols: list, predict_date: date) -> None:
        """执行预测"""
        try:
            predictions = self.gui_engine.predict(
                model_id=model_id,
                symbols=symbols,
                predict_date=predict_date
            )

            if predictions:
                self.predictions = predictions
                self._update_prediction_table()
                self.show_status(_(f"预测完成，共{len(predictions)}只股票"))
            else:
                self.show_status(_("预测失败"))
        except RuntimeError as e:
            # 显示详细错误信息
            error_msg = str(e)
            QtWidgets.QMessageBox.warning(
                self,
                _("预测失败"),
                _("无法进行预测：\n\n{error}\n\n请先下载历史数据后再试").format(error=error_msg)
            )
            self.show_status(_("预测失败 - 请先下载历史数据"))
        except Exception as e:
            self.show_status(_(f"预测失败: {e}"))

    def refresh_predictions(self) -> None:
        """刷新预测结果"""
        if not self.gui_engine:
            return

        self.predictions = self.gui_engine.get_predictions()
        self._update_prediction_table()
        self.show_status(_(f"预测列表已更新，共{len(self.predictions)}条记录"))

    def _update_prediction_table(self) -> None:
        """更新预测表格"""
        self.prediction_table.setRowCount(len(self.predictions))

        for row, pred in enumerate(self.predictions):
            # 股票名称
            if "(" in pred.model_name:
                stock_name = pred.model_name.split("(")[-1].rstrip(")")
            else:
                stock_name = pred.model_name

            self.prediction_table.setItem(row, 0, QtWidgets.QTableWidgetItem(pred.symbol))
            self.prediction_table.setItem(row, 1, QtWidgets.QTableWidgetItem(stock_name))

            # 方向（带颜色）
            direction_map = {
                SignalType.BUY: "上涨",
                SignalType.SELL: "下跌",
                SignalType.HOLD: "中性",
                SignalType.CLOSE: "平仓"
            }
            direction = direction_map.get(pred.signal, "未知")

            direction_item = QtWidgets.QTableWidgetItem(direction)
            if pred.signal == SignalType.BUY:
                direction_item.setForeground(QtGui.QColor("red"))
            elif pred.signal == SignalType.SELL:
                direction_item.setForeground(QtGui.QColor("green"))
            self.prediction_table.setItem(row, 2, direction_item)

            # 置信度
            conf_item = QtWidgets.QTableWidgetItem(f"{pred.confidence:.2%}")
            if pred.confidence > 0.7:
                conf_item.setForeground(QtGui.QColor("red"))
            self.prediction_table.setItem(row, 3, conf_item)

            # 预测时间
            time_str = pred.datetime.strftime("%H:%M:%S")
            self.prediction_table.setItem(row, 4, QtWidgets.QTableWidgetItem(time_str))

        self.prediction_table.resizeColumnsToContents()

    def export_predictions(self) -> None:
        """导出预测结果"""
        if not self.predictions:
            self.show_status(_("无可导出的数据"))
            return

        # TODO: 实现Excel导出
        self.show_status(_("预测结果导出功能待实现"))

    def clear_predictions(self) -> None:
        """清空预测结果"""
        if not self.gui_engine:
            return

        self.gui_engine.clear_predictions()
        self.predictions = []
        self.prediction_table.setRowCount(0)
        self.show_status(_("预测结果已清空"))

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaMlWidget"]
