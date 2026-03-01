"""A股机器学习UI组件"""
from typing import Any, Optional
from datetime import datetime, date, timedelta
import numpy as np

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.locale import _

from ..model.manager import ModelMetadata
from ..utils.types import ModelType, PredictionResult, SignalType

# 导入新增功能模块
from ..data import DataPreloader, DataUpdateScheduler, PreloadConfig, UpdateConfig
from ..backtesting import FactorBacktester, create_factor_backtester
from ..factors import FactorCombiner, WeightMethod, OrthogonalMethod


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

        # 数据管理标签页
        data_mgmt_widget = self.create_data_management_tab()
        tab.addTab(data_mgmt_widget, _("数据管理"))

        # 因子回测标签页
        backtest_widget = self.create_backtest_tab()
        tab.addTab(backtest_widget, _("因子回测"))

        # 因子组合标签页
        combination_widget = self.create_combination_tab()
        tab.addTab(combination_widget, _("因子组合"))

        # 版本管理标签页
        version_widget = self.create_version_management_tab()
        tab.addTab(version_widget, _("版本管理"))

        # A/B测试标签页
        ab_test_widget = self.create_ab_test_tab()
        tab.addTab(ab_test_widget, _("A/B测试"))

        # Alpha158训练标签页
        alpha158_widget = self.create_alpha158_tab()
        tab.addTab(alpha158_widget, "Alpha158")

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

    # ==================== 数据管理功能 ====================

    def create_data_management_tab(self) -> QtWidgets.QWidget:
        """创建数据管理标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("数据管理"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 预加载区
        preload_group = QtWidgets.QGroupBox(_("数据预加载"))
        preload_layout = QtWidgets.QGridLayout()
        preload_group.setLayout(preload_layout)
        layout.addWidget(preload_group)

        # 预加载配置
        preload_layout.addWidget(QtWidgets.QLabel(_("起始天数：")), 0, 0)
        self.preload_start_days = QtWidgets.QSpinBox()
        self.preload_start_days.setRange(30, 3650)
        self.preload_start_days.setValue(365 * 3)
        preload_layout.addWidget(self.preload_start_days, 0, 1)

        preload_layout.addWidget(QtWidgets.QLabel(_("结束日期：")), 0, 2)
        self.preload_end_date = QtWidgets.QDateEdit()
        self.preload_end_date.setCalendarPopup(True)
        self.preload_end_date.setDate(QtCore.QDate.currentDate())
        preload_layout.addWidget(self.preload_end_date, 0, 3)

        # 数据类型选择
        self.enable_bar_data = QtWidgets.QCheckBox(_("K线数据"))
        self.enable_bar_data.setChecked(True)
        preload_layout.addWidget(self.enable_bar_data, 1, 0)

        self.enable_dragon_tiger = QtWidgets.QCheckBox(_("龙虎榜数据"))
        self.enable_dragon_tiger.setChecked(True)
        preload_layout.addWidget(self.enable_dragon_tiger, 1, 1)

        self.enable_northbound = QtWidgets.QCheckBox(_("北向资金数据"))
        self.enable_northbound.setChecked(True)
        preload_layout.addWidget(self.enable_northbound, 1, 2)

        self.enable_sector = QtWidgets.QCheckBox(_("板块数据"))
        self.enable_sector.setChecked(True)
        preload_layout.addWidget(self.enable_sector, 1, 3)

        # 预加载按钮
        preload_btn = QtWidgets.QPushButton(_("开始预加载"))
        preload_btn.clicked.connect(self.start_preload)
        preload_layout.addWidget(preload_btn, 2, 0, 1, 4)

        # 预加载进度
        self.preload_progress = QtWidgets.QProgressBar()
        self.preload_progress.setRange(0, 100)
        preload_layout.addWidget(self.preload_progress, 3, 0, 1, 4)

        # 预加载状态
        self.preload_status = QtWidgets.QLabel(_("未开始"))
        preload_layout.addWidget(self.preload_status, 4, 0, 1, 4)

        # 调度器区
        scheduler_group = QtWidgets.QGroupBox(_("定时更新调度"))
        scheduler_layout = QtWidgets.QGridLayout()
        scheduler_group.setLayout(scheduler_layout)
        layout.addWidget(scheduler_group)

        # 调度器配置
        scheduler_layout.addWidget(QtWidgets.QLabel(_("更新时间：")), 0, 0)
        self.update_time = QtWidgets.QTimeEdit()
        self.update_time.setTime(QtCore.QTime(15, 30))
        scheduler_layout.addWidget(self.update_time, 0, 1)

        scheduler_layout.addWidget(QtWidgets.QLabel(_("回看天数：")), 0, 2)
        self.lookback_days = QtWidgets.QSpinBox()
        self.lookback_days.setRange(1, 30)
        self.lookback_days.setValue(5)
        scheduler_layout.addWidget(self.lookback_days, 0, 3)

        # 调度器状态
        self.scheduler_status = QtWidgets.QLabel(_("调度器未启动"))
        scheduler_layout.addWidget(self.scheduler_status, 1, 0, 1, 4)

        self.start_scheduler_btn = QtWidgets.QPushButton(_("启动调度器"))
        self.start_scheduler_btn.clicked.connect(self.toggle_scheduler)
        scheduler_layout.addWidget(self.start_scheduler_btn, 2, 0)

        self.trigger_update_btn = QtWidgets.QPushButton(_("立即更新"))
        self.trigger_update_btn.clicked.connect(self.trigger_data_update)
        self.trigger_update_btn.setEnabled(False)
        scheduler_layout.addWidget(self.trigger_update_btn, 2, 1)

        return widget

    def start_preload(self) -> None:
        """开始预加载数据"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        start_days = self.preload_start_days.value()
        end_date = self.preload_end_date.date().toPython()
        start_date = end_date - timedelta(days=start_days)

        self.show_status(_("开始预加载数据..."))
        self.preload_progress.setValue(0)
        self.preload_status.setText(_("预加载中..."))

        def progress_callback(completed: int, total: int, task: str):
            self.preload_progress.setValue(int(completed * 100 / total) if total > 0 else 0)
            self.preload_status.setText(f"{task} ({completed}/{total})")

        # 异步执行预加载
        QtCore.QTimer.singleShot(100, lambda: self._do_preload(start_date, end_date, progress_callback))

    def _do_preload(self, start_date: date, end_date: date, callback) -> None:
        """执行预加载"""
        try:
            stats = self.gui_engine.preload_data(
                start_date=start_date,
                end_date=end_date,
                enable_bar_data=self.enable_bar_data.isChecked(),
                enable_dragon_tiger=self.enable_dragon_tiger.isChecked(),
                enable_northbound=self.enable_northbound.isChecked(),
                enable_sector=self.enable_sector.isChecked(),
                progress_callback=callback
            )

            total = sum(stats.values())
            self.preload_progress.setValue(100)
            self.preload_status.setText(_("预加载完成"))
            self.show_status(_(f"数据预加载完成，共{total}条记录"))
        except Exception as e:
            self.preload_status.setText(_("预加载失败"))
            self.show_status(_(f"预加载失败: {e}"))

    def toggle_scheduler(self) -> None:
        """切换调度器状态"""
        if not self.gui_engine:
            return

        status = self.gui_engine.get_data_scheduler_status()
        is_running = status.get("is_running", False)

        if is_running:
            # 停止调度器
            self.gui_engine.data_scheduler.stop()
            self.scheduler_status.setText(_("调度器未启动"))
            self.start_scheduler_btn.setText(_("启动调度器"))
            self.trigger_update_btn.setEnabled(False)
            self.show_status(_("调度器已停止"))
        else:
            # 启动调度器
            update_time = self.update_time.time().toString("HH:mm")
            self.gui_engine.update_scheduler_config(update_time=update_time)

            if self.gui_engine.data_scheduler.start():
                self.scheduler_status.setText(_("调度器运行中"))
                self.start_scheduler_btn.setText(_("停止调度器"))
                self.trigger_update_btn.setEnabled(True)
                self.show_status(_("调度器已启动"))
            else:
                self.show_status(_("调度器启动失败"))

    def trigger_data_update(self) -> None:
        """立即触发数据更新"""
        if not self.gui_engine:
            return

        self.show_status(_("正在触发数据更新..."))
        result = self.gui_engine.trigger_data_update()

        if result:
            self.show_status(_("数据更新已触发"))
        else:
            self.show_status(_("数据更新触发失败"))

    # ==================== 因子回测功能 ====================

    def create_backtest_tab(self) -> QtWidgets.QWidget:
        """创建因子回测标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("因子有效性回测"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 回测配置区
        config_group = QtWidgets.QGroupBox(_("回测配置"))
        config_layout = QtWidgets.QGridLayout()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 日期范围
        config_layout.addWidget(QtWidgets.QLabel(_("回测开始：")), 0, 0)
        self.backtest_start_date = QtWidgets.QDateEdit()
        self.backtest_start_date.setCalendarPopup(True)
        self.backtest_start_date.setDate(QtCore.QDate.currentDate().addMonths(-3))
        config_layout.addWidget(self.backtest_start_date, 0, 1)

        config_layout.addWidget(QtWidgets.QLabel(_("回测结束：")), 0, 2)
        self.backtest_end_date = QtWidgets.QDateEdit()
        self.backtest_end_date.setCalendarPopup(True)
        self.backtest_end_date.setDate(QtCore.QDate.currentDate())
        config_layout.addWidget(self.backtest_end_date, 0, 3)

        config_layout.addWidget(QtWidgets.QLabel(_("预测天数：")), 1, 0)
        self.forward_days = QtWidgets.QSpinBox()
        self.forward_days.setRange(1, 20)
        self.forward_days.setValue(5)
        config_layout.addWidget(self.forward_days, 1, 1)

        config_layout.addWidget(QtWidgets.QLabel(_("分层数量：")), 1, 2)
        self.n_layers = QtWidgets.QSpinBox()
        self.n_layers.setRange(3, 10)
        self.n_layers.setValue(5)
        config_layout.addWidget(self.n_layers, 1, 3)

        # 开始回测按钮
        backtest_btn = QtWidgets.QPushButton(_("开始回测"))
        backtest_btn.clicked.connect(self.start_backtest)
        config_layout.addWidget(backtest_btn, 2, 0, 1, 4)

        # 回测结果区
        result_group = QtWidgets.QGroupBox(_("回测结果"))
        result_layout = QtWidgets.QVBoxLayout()
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # IC统计表格
        self.ic_table = QtWidgets.QTableWidget()
        self.ic_table.setColumnCount(4)
        self.ic_table.setHorizontalHeaderLabels([
            _("IC均值"), _("IC标准差"), _("IC_IR"), _("胜率")
        ])
        self.ic_table.setRowCount(1)
        result_layout.addWidget(self.ic_table)

        # 分层结果表格
        layer_label = QtWidgets.QLabel(_("分层收益分析"))
        layer_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        result_layout.addWidget(layer_label)

        self.layer_table = QtWidgets.QTableWidget()
        self.layer_table.setColumnCount(4)
        self.layer_table.setHorizontalHeaderLabels([
            _("分层"), _("年化收益"), _("夏普比率"), _("最大回撤")
        ])
        self.layer_table.setRowCount(5)
        result_layout.addWidget(self.layer_table)

        # 回测进度
        self.backtest_progress = QtWidgets.QProgressBar()
        result_layout.addWidget(self.backtest_progress)

        return widget

    def start_backtest(self) -> None:
        """开始因子回测"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        start_date = self.backtest_start_date.date().toPython()
        end_date = self.backtest_end_date.date().toPython()
        forward_days = self.forward_days.value()
        n_layers = self.n_layers.value()

        self.show_status(_("正在执行因子回测..."))
        self.backtest_progress.setValue(10)

        # 异步执行回测
        QtCore.QTimer.singleShot(100, lambda: self._do_backtest(start_date, end_date, forward_days, n_layers))

    def _do_backtest(self, start_date: date, end_date: date, forward_days: int, n_layers: int) -> None:
        """执行回测"""
        try:
            from ..dataset import create_alpha_dataset

            self.backtest_progress.setValue(30)

            # 准备数据
            symbols = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "600519.SH"]
            dataset = create_alpha_dataset(symbols, start_date, end_date)
            factor_df, price_df = dataset.get_backtest_data()

            self.backtest_progress.setValue(50)

            # 创建回测器
            backtester = create_factor_backtester()
            report = backtester.backtest_factor(
                factor_data=factor_df,
                price_data=price_df,
                start_date=start_date,
                end_date=end_date,
                forward_days=forward_days,
                n_layers=n_layers
            )

            self.backtest_progress.setValue(80)

            # 更新结果表格
            self._update_backtest_results(report)

            self.backtest_progress.setValue(100)
            self.show_status(_(f"回测完成，IC: {report.ic_stats.ic_mean:.4f}, IR: {report.ic_stats.ic_ir:.4f}"))
        except Exception as e:
            self.backtest_progress.setValue(0)
            self.show_status(_(f"回测失败: {e}"))

    def _update_backtest_results(self, report) -> None:
        """更新回测结果表格"""
        # 更新IC统计
        ic_stats = report.ic_stats
        self.ic_table.setItem(0, 0, QtWidgets.QTableWidgetItem(f"{ic_stats.ic_mean:.4f}"))
        self.ic_table.setItem(0, 1, QtWidgets.QTableWidgetItem(f"{ic_stats.ic_std:.4f}"))
        self.ic_table.setItem(0, 2, QtWidgets.QTableWidgetItem(f"{ic_stats.ic_ir:.4f}"))
        self.ic_table.setItem(0, 3, QtWidgets.QTableWidgetItem(f"{ic_stats.win_rate:.2%}"))
        self.ic_table.resizeColumnsToContents()

        # 更新分层结果
        for i, layer_result in enumerate(report.layer_results):
            self.layer_table.setItem(i, 0, QtWidgets.QTableWidgetItem(f"第{i+1}层"))
            self.layer_table.setItem(i, 1, QtWidgets.QTableWidgetItem(f"{layer_result.annual_return:.2%}"))
            self.layer_table.setItem(i, 2, QtWidgets.QTableWidgetItem(f"{layer_result.sharpe_ratio:.2f}"))
            self.layer_table.setItem(i, 3, QtWidgets.QTableWidgetItem(f"{layer_result.max_drawdown:.2%}"))
        self.layer_table.resizeColumnsToContents()

    # ==================== 因子组合功能 ====================

    def create_combination_tab(self) -> QtWidgets.QWidget:
        """创建因子组合标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("自定义因子组合"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 因子选择区
        factor_group = QtWidgets.QGroupBox(_("选择因子"))
        factor_layout = QtWidgets.QVBoxLayout()
        factor_group.setLayout(factor_layout)
        layout.addWidget(factor_group)

        # 因子列表
        factor_list = [
            "Return_5d", "Return_10d", "Return_20d",
            "Volume_Ratio", "Volume_Change_5d",
            "MACD", "RSI_14", "Bollinger_Width",
            "ATR_14_Simple", "ROC_10"
        ]
        self.factor_checkboxes = {}
        for factor in factor_list:
            checkbox = QtWidgets.QCheckBox(factor)
            checkbox.setChecked(True)
            self.factor_checkboxes[factor] = checkbox
            factor_layout.addWidget(checkbox)

        # 权重方法选择
        weight_group = QtWidgets.QGroupBox(_("权重方法"))
        weight_layout = QtWidgets.QGridLayout()
        weight_group.setLayout(weight_layout)
        layout.addWidget(weight_group)

        weight_layout.addWidget(QtWidgets.QLabel(_("权重方法：")), 0, 0)
        self.weight_method_combo = QtWidgets.QComboBox()
        self.weight_method_combo.addItem(_("等权重"), "equal")
        self.weight_method_combo.addItem(_("IC加权"), "ic_weighted")
        self.weight_method_combo.addItem(_("IR加权"), "ir_weighted")
        self.weight_method_combo.addItem(_("自定义"), "custom")
        weight_layout.addWidget(self.weight_method_combo, 0, 1)

        # 自定义权重输入
        self.custom_weights_input = QtWidgets.QLineEdit()
        self.custom_weights_input.setPlaceholderText("Return_5d:0.5, Volume_Ratio:0.3")
        self.custom_weights_input.setEnabled(False)
        weight_layout.addWidget(QtWidgets.QLabel(_("自定义权重：")), 1, 0)
        weight_layout.addWidget(self.custom_weights_input, 1, 1, 1, 3)

        # 监听权重方法变化
        self.weight_method_combo.currentTextChanged.connect(self._on_weight_method_changed)

        # 正交化方法选择
        ortho_group = QtWidgets.QGroupBox(_("正交化"))
        ortho_layout = QtWidgets.QHBoxLayout()
        ortho_group.setLayout(ortho_layout)
        layout.addWidget(ortho_group)

        ortho_layout.addWidget(QtWidgets.QLabel(_("正交化方法：")))
        self.ortho_method_combo = QtWidgets.QComboBox()
        self.ortho_method_combo.addItem(_("无"), "none")
        self.ortho_method_combo.addItem(_("Gram-Schmidt"), "gram_schmidt")
        self.ortho_method_combo.addItem(_("PCA"), "pca")
        ortho_layout.addWidget(self.ortho_method_combo)
        ortho_layout.addStretch()

        # 操作按钮
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        combine_btn = QtWidgets.QPushButton(_("组合因子"))
        combine_btn.clicked.connect(self.combine_factors)
        btn_layout.addWidget(combine_btn)

        export_btn = QtWidgets.QPushButton(_("导出组合"))
        export_btn.clicked.connect(self.export_combination)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()

        # 组合结果区
        result_group = QtWidgets.QGroupBox(_("组合结果"))
        result_layout = QtWidgets.QVBoxLayout()
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.combination_result = QtWidgets.QTextEdit()
        self.combination_result.setReadOnly(True)
        self.combination_result.setMaximumHeight(150)
        result_layout.addWidget(self.combination_result)

        return widget

    def _on_weight_method_changed(self, method: str) -> None:
        """权重方法变化时"""
        self.custom_weights_input.setEnabled(method == "custom")

    def combine_factors(self) -> None:
        """组合因子"""
        if not self.gui_engine:
            self.show_status(_("GUI引擎未初始化"))
            return

        # 获取选中的因子
        selected_factors = [
            name for name, checkbox in self.factor_checkboxes.items()
            if checkbox.isChecked()
        ]

        if not selected_factors:
            self.show_status(_("请至少选择一个因子"))
            return

        weight_method_str = self.weight_method_combo.currentData()
        ortho_method_str = self.ortho_method_combo.currentData()

        # 自定义权重解析
        custom_weights = None
        if weight_method_str == "custom":
            try:
                custom_weights = {}
                for pair in self.custom_weights_input.text().split(","):
                    name, weight = pair.strip().split(":")
                    custom_weights[name.strip()] = float(weight.strip())
            except Exception:
                self.show_status(_("自定义权重格式错误，应如：Factor:0.5, Factor2:0.3"))
                return

        # 创建组合器并显示结果
        try:
            from ..factors import create_factor_combiner

            combiner = create_factor_combiner(
                factors=selected_factors,
                weight_method=weight_method_str,
                orthogonal_method=ortho_method_str,
                custom_weights=custom_weights
            )

            # 获取权重信息
            weights = combiner.get_weights()

            # 显示结果
            result_text = f"# 因子组合结果\n\n"
            result_text += f"选中因子: {', '.join(selected_factors)}\n"
            result_text += f"权重方法: {self.weight_method_combo.currentText()}\n"
            result_text += f"正交化方法: {self.ortho_method_combo.currentText()}\n\n"
            result_text += "## 因子权重:\n"

            for w in weights:
                result_text += f"- {w.factor_name}: {w.weight:.4f}"
                if w.ic != 0:
                    result_text += f" (IC: {w.ic:.4f})"
                result_text += "\n"

            self.combination_result.setText(result_text)
            self.show_status(_("因子组合完成"))
        except Exception as e:
            self.combination_result.setText(f"组合失败: {e}")
            self.show_status(_(f"因子组合失败: {e}"))

    def export_combination(self) -> None:
        """导出组合配置"""
        result = self.combination_result.toPlainText()
        if not result or "组合失败" in result:
            self.show_status(_("无可导出的组合配置"))
            return

        # TODO: 实现文件导出
        self.show_status(_("组合配置导出功能待实现"))

    # ==================== 版本管理功能 ====================

    def create_version_management_tab(self) -> QtWidgets.QWidget:
        """创建版本管理标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("模型版本管理"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 模型选择区
        model_group = QtWidgets.QGroupBox(_("选择模型"))
        model_layout = QtWidgets.QHBoxLayout()
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        model_layout.addWidget(QtWidgets.QLabel(_("模型名称：")))
        self.version_model_combo = QtWidgets.QComboBox()
        self.version_model_combo.currentTextChanged.connect(self.on_version_model_changed)
        model_layout.addWidget(self.version_model_combo)

        refresh_versions_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_versions_btn.clicked.connect(self.refresh_version_models)
        model_layout.addWidget(refresh_versions_btn)

        # 版本列表区
        version_group = QtWidgets.QGroupBox(_("版本历史"))
        version_layout = QtWidgets.QVBoxLayout()
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)

        # 版本表格
        self.version_table = QtWidgets.QTableWidget()
        self.version_table.setColumnCount(7)
        self.version_table.setHorizontalHeaderLabels([
            _("版本号"), _("模型名称"), _("类型"), _("训练时间"),
            _("准确率"), _("标签"), _("状态")
        ])
        self.version_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.version_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        version_layout.addWidget(self.version_table)

        # 版本操作按钮
        version_btn_layout = QtWidgets.QHBoxLayout()
        version_layout.addLayout(version_btn_layout)

        set_production_btn = QtWidgets.QPushButton(_("设为生产版本"))
        set_production_btn.clicked.connect(self.set_production_version)
        version_btn_layout.addWidget(set_production_btn)

        rollback_btn = QtWidgets.QPushButton(_("回滚到选中版本"))
        rollback_btn.clicked.connect(self.rollback_to_version)
        version_btn_layout.addWidget(rollback_btn)

        compare_btn = QtWidgets.QPushButton(_("对比选中版本"))
        compare_btn.clicked.connect(self.compare_versions)
        version_btn_layout.addWidget(compare_btn)

        # 创建新版本区
        create_group = QtWidgets.QGroupBox(_("创建新版本"))
        create_layout = QtWidgets.QGridLayout()
        create_group.setLayout(create_layout)
        layout.addWidget(create_group)

        create_layout.addWidget(QtWidgets.QLabel(_("版本号：")), 0, 0)
        self.new_version_input = QtWidgets.QLineEdit("1.0.1")
        create_layout.addWidget(self.new_version_input, 0, 1)

        create_layout.addWidget(QtWidgets.QLabel(_("标签：")), 0, 2)
        self.version_tag_combo = QtWidgets.QComboBox()
        self.version_tag_combo.addItem(_("开发版本"), "development")
        self.version_tag_combo.addItem(_("测试版本"), "staging")
        self.version_tag_combo.addItem(_("生产版本"), "production")
        create_layout.addWidget(self.version_tag_combo, 0, 3)

        create_layout.addWidget(QtWidgets.QLabel(_("变更日志：")), 1, 0)
        self.changelog_input = QtWidgets.QLineEdit()
        self.changelog_input.setPlaceholderText("描述本次变更内容...")
        create_layout.addWidget(self.changelog_input, 1, 1, 1, 3)

        create_version_btn = QtWidgets.QPushButton(_("创建版本"))
        create_version_btn.clicked.connect(self.create_new_version)
        create_layout.addWidget(create_version_btn, 2, 0, 1, 4)

        return widget

    def on_version_model_changed(self, model_name: str) -> None:
        """模型选择变化时"""
        if model_name and self.gui_engine:
            self.refresh_version_list(model_name)

    def refresh_version_models(self) -> None:
        """刷新版本模型列表"""
        if not self.gui_engine:
            return

        self.version_model_combo.clear()

        # 获取所有唯一的模型名称
        models = self.gui_engine.get_all_models()
        model_names = set(m.model_name for m in models)

        for name in sorted(model_names):
            self.version_model_combo.addItem(name)

        if model_names:
            self.refresh_version_list(sorted(model_names)[0])

    def refresh_version_list(self, model_name: str) -> None:
        """刷新版本列表"""
        if not self.gui_engine:
            return

        version_tree = self.gui_engine.get_version_tree(model_name)

        self.version_table.setRowCount(len(version_tree))

        for row, version_info in enumerate(version_tree):
            self.version_table.setItem(row, 0, QtWidgets.QTableWidgetItem(version_info["version"]))
            self.version_table.setItem(row, 1, QtWidgets.QTableWidgetItem(model_name))
            self.version_table.setItem(row, 2, QtWidgets.QTableWidgetItem(version_info.get("type", "")))

            time_str = ""
            if version_info.get("training_date"):
                time_str = version_info["training_date"].strftime("%Y-%m-%d %H:%M")
            self.version_table.setItem(row, 3, QtWidgets.QTableWidgetItem(time_str))

            acc_item = QtWidgets.QTableWidgetItem(f"{version_info.get('accuracy', 0):.2%}")
            self.version_table.setItem(row, 4, acc_item)

            tag = version_info.get("tag", "development")
            tag_item = QtWidgets.QTableWidgetItem(tag)
            if tag == "production":
                tag_item.setForeground(QtGui.QColor("green"))
            elif tag == "staging":
                tag_item.setForeground(QtGui.QColor("orange"))
            self.version_table.setItem(row, 5, tag_item)

            status = "生产" if version_info.get("is_production") else "开发"
            self.version_table.setItem(row, 6, QtWidgets.QTableWidgetItem(status))

        self.version_table.resizeColumnsToContents()

    def create_new_version(self) -> None:
        """创建新版本"""
        if not self.gui_engine:
            return

        model_name = self.version_model_combo.currentText()
        if not model_name:
            self.show_status(_("请先选择模型"))
            return

        version = self.new_version_input.text()
        tag = self.version_tag_combo.currentData()
        changelog = self.changelog_input.text()

        new_id = self.gui_engine.create_model_version(
            model_name=model_name,
            version=version,
            tag=tag,
            changelog=changelog
        )

        if new_id:
            self.refresh_version_list(model_name)
            self.show_status(_(f"已创建版本: {version}"))
        else:
            self.show_status(_("创建版本失败"))

    def set_production_version(self) -> None:
        """设置生产版本"""
        if not self.gui_engine:
            return

        current_row = self.version_table.currentRow()
        if current_row < 0:
            self.show_status(_("请先选择版本"))
            return

        # 获取模型ID（从版本树中获取）
        model_name = self.version_model_combo.currentText()
        version_tree = self.gui_engine.get_version_tree(model_name)

        if current_row < len(version_tree):
            model_id = version_tree[current_row]["model_id"]
            if self.gui_engine.set_production_version(model_id):
                self.refresh_version_list(model_name)
                self.show_status(_("已设置为生产版本"))

    def rollback_to_version(self) -> None:
        """回滚到选中版本"""
        if not self.gui_engine:
            return

        current_row = self.version_table.currentRow()
        if current_row < 0:
            self.show_status(_("请先选择版本"))
            return

        model_name = self.version_model_combo.currentText()
        version_tree = self.gui_engine.get_version_tree(model_name)

        if current_row < len(version_tree):
            model_id = version_tree[current_row]["model_id"]
            if self.gui_engine.rollback_model(model_id):
                self.refresh_version_list(model_name)
                self.show_status(_("已回滚到选中版本"))

    def compare_versions(self) -> None:
        """对比选中版本"""
        if not self.gui_engine:
            return

        selected = self.version_table.selectedRanges()
        if len(selected) < 2 or selected[0].rowCount() < 2:
            self.show_status(_("请选择两个版本进行对比"))
            return

        model_name = self.version_model_combo.currentText()
        version_tree = self.gui_engine.get_version_tree(model_name)

        rows = [r for r in range(self.version_table.rowCount())
                if self.version_table.item(r, 0).isSelected()]

        if len(rows) >= 2:
            model_id_1 = version_tree[rows[0]]["model_id"]
            model_id_2 = version_tree[rows[1]]["model_id"]

            comparison = self.gui_engine.compare_model_versions(model_id_1, model_id_2)

            # 显示对比结果（使用消息框）
            result_text = f"# 版本对比结果\n\n"
            result_text += f"模型1: {comparison['model_1']['version']} (准确率: {comparison['model_1']['accuracy']:.2%})\n"
            result_text += f"模型2: {comparison['model_2']['version']} (准确率: {comparison['model_2']['accuracy']:.2%})\n\n"
            result_text += f"准确率差异: {comparison['differences']['accuracy']:.2%}\n"

            QtWidgets.QMessageBox.information(
                self, _("版本对比结果"), result_text
            )
            self.show_status(_("版本对比完成"))

    # ==================== A/B测试功能 ====================

    def create_ab_test_tab(self) -> QtWidgets.QWidget:
        """创建A/B测试标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("模型A/B测试"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 测试配置区
        config_group = QtWidgets.QGroupBox(_("测试配置"))
        config_layout = QtWidgets.QGridLayout()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 测试名称
        config_layout.addWidget(QtWidgets.QLabel(_("测试名称：")), 0, 0)
        self.ab_test_name_input = QtWidgets.QLineEdit()
        self.ab_test_name_input.setPlaceholderText("例如: LightGBM_vs_XGBoost")
        config_layout.addWidget(self.ab_test_name_input, 0, 1)

        # 模型选择（多选）
        config_layout.addWidget(QtWidgets.QLabel(_("选择模型：")), 1, 0)
        self.ab_test_model_list = QtWidgets.QListWidget()
        self.ab_test_model_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        config_layout.addWidget(self.ab_test_model_list, 1, 1, 1, 3)

        refresh_ab_models_btn = QtWidgets.QPushButton(_("刷新模型列表"))
        refresh_ab_models_btn.clicked.connect(self.refresh_ab_test_models)
        config_layout.addWidget(refresh_ab_models_btn, 1, 4)

        # 日期范围
        config_layout.addWidget(QtWidgets.QLabel(_("测试开始：")), 2, 0)
        self.ab_test_start_date = QtWidgets.QDateEdit()
        self.ab_test_start_date.setCalendarPopup(True)
        self.ab_test_start_date.setDate(QtCore.QDate.currentDate().addMonths(-1))
        config_layout.addWidget(self.ab_test_start_date, 2, 1)

        config_layout.addWidget(QtWidgets.QLabel(_("测试结束：")), 2, 2)
        self.ab_test_end_date = QtWidgets.QDateEdit()
        self.ab_test_end_date.setCalendarPopup(True)
        self.ab_test_end_date.setDate(QtCore.QDate.currentDate())
        config_layout.addWidget(self.ab_test_end_date, 2, 3)

        # 运行测试按钮
        run_ab_test_btn = QtWidgets.QPushButton(_("运行A/B测试"))
        run_ab_test_btn.clicked.connect(self.run_ab_test)
        config_layout.addWidget(run_ab_test_btn, 3, 0, 1, 5)

        # 测试结果区
        result_group = QtWidgets.QGroupBox(_("测试结果"))
        result_layout = QtWidgets.QVBoxLayout()
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 结果对比表格
        self.ab_result_table = QtWidgets.QTableWidget()
        self.ab_result_table.setColumnCount(6)
        self.ab_result_table.setHorizontalHeaderLabels([
            _("模型名称"), _("准确率"), _("IC"), _("MSE"),
            _("MAE"), _("夏普比率")
        ])
        result_layout.addWidget(self.ab_result_table)

        # 测试历史
        history_label = QtWidgets.QLabel(_("测试历史"))
        history_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        result_layout.addWidget(history_label)

        self.ab_test_history_table = QtWidgets.QTableWidget()
        self.ab_test_history_table.setColumnCount(4)
        self.ab_test_history_table.setHorizontalHeaderLabels([
            _("测试名称"), _("测试时间"), _("推荐模型"), _("显著性")
        ])
        self.ab_test_history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.ab_test_history_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        result_layout.addWidget(self.ab_test_history_table)

        return widget

    def refresh_ab_test_models(self) -> None:
        """刷新A/B测试模型列表"""
        if not self.gui_engine:
            return

        self.ab_test_model_list.clear()

        models = self.gui_engine.get_all_models()
        trained_models = [m for m in models if m.is_trained]

        for metadata in trained_models:
            item = QtWidgets.QTableWidgetItem(
                f"{metadata.model_name} ({metadata.model_type.value}) - {metadata.accuracy:.2%}"
            )
            item.setData(QtCore.Qt.UserRole, metadata.model_id)
            self.ab_test_model_list.addItem(item)

    def run_ab_test(self) -> None:
        """运行A/B测试"""
        if not self.gui_engine:
            return

        # 获取选中的模型
        selected_items = self.ab_test_model_list.selectedItems()
        if len(selected_items) < 2:
            self.show_status(_("请至少选择2个模型进行对比"))
            return

        model_ids = [item.data(QtCore.Qt.UserRole) for item in selected_items]
        test_name = self.ab_test_name_input.text() or f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_date = self.ab_test_start_date.date().toPython()
        end_date = self.ab_test_end_date.date().toPython()

        self.show_status(_("正在创建A/B测试..."))

        # 创建测试
        test_id = self.gui_engine.create_ab_test(
            test_name=test_name,
            model_ids=model_ids,
            start_date=start_date,
            end_date=end_date
        )

        if not test_id:
            self.show_status(_("创建A/B测试失败"))
            return

        # 生成测试数据（模拟）
        import numpy as np
        n_samples = 1000
        n_features = 20
        X = np.random.randn(n_samples, n_features)
        y = np.random.randn(n_samples) * 0.02

        self.show_status(_("正在运行A/B测试..."))

        # 异步运行测试
        QtCore.QTimer.singleShot(100, lambda: self._do_run_ab_test(test_id, X, y))

    def _do_run_ab_test(self, test_id: str, X: np.ndarray, y: np.ndarray) -> None:
        """执行A/B测试"""
        result = self.gui_engine.run_ab_test(test_id, X, y)

        if result:
            self._update_ab_test_results(result)
            self._update_ab_test_history()
            self.show_status(_(f"A/B测试完成: {result.test_name}"))
        else:
            self.show_status(_("A/B测试失败"))

    def _update_ab_test_results(self, result) -> None:
        """更新A/B测试结果表格"""
        self.ab_result_table.setRowCount(len(result.model_results))

        for row, (model_id, metrics) in enumerate(result.model_results.items()):
            # 获取模型名称
            metadata = self.gui_engine.model_manager.get_model_metadata(model_id)
            model_name = metadata.model_name if metadata else model_id

            self.ab_result_table.setItem(row, 0, QtWidgets.QTableWidgetItem(model_name))

            # 填充指标
            self.ab_result_table.setItem(row, 1, QtWidgets.QTableWidgetItem(
                f"{metrics.get('accuracy', 0):.2%}"))
            self.ab_result_table.setItem(row, 2, QtWidgets.QTableWidgetItem(
                f"{metrics.get('ic', 0):.4f}"))
            self.ab_result_table.setItem(row, 3, QtWidgets.QTableWidgetItem(
                f"{metrics.get('mse', 0):.6f}"))
            self.ab_result_table.setItem(row, 4, QtWidgets.QTableWidgetItem(
                f"{metrics.get('mae', 0):.6f}"))
            self.ab_result_table.setItem(row, 5, QtWidgets.QTableWidgetItem(
                f"{metrics.get('sharpe_ratio', 0):.4f}"))

        self.ab_result_table.resizeColumnsToContents()

    def _update_ab_test_history(self) -> None:
        """更新A/B测试历史"""
        if not self.gui_engine:
            return

        history = self.gui_engine.get_ab_test_history()

        self.ab_test_history_table.setRowCount(len(history))

        for row, result in enumerate(history):
            self.ab_test_history_table.setItem(row, 0, QtWidgets.QTableWidgetItem(result.test_name))

            time_str = result.timestamp.strftime("%Y-%m-%d %H:%M")
            self.ab_test_history_table.setItem(row, 1, QtWidgets.QTableWidgetItem(time_str))

            winner = result.winner or "无"
            self.ab_test_history_table.setItem(row, 2, QtWidgets.QTableWidgetItem(winner))

            sig_text = ""
            if result.significance is not None:
                sig_status = _("显著") if result.is_significant() else _("不显著")
                sig_text = f"{sig_status} (p={result.significance:.4f})"
            self.ab_test_history_table.setItem(row, 3, QtWidgets.QTableWidgetItem(sig_text))

        self.ab_test_history_table.resizeColumnsToContents()

    # ==================== Alpha158训练功能 ====================

    def create_alpha158_tab(self) -> QtWidgets.QWidget:
        """创建Alpha158训练标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("Alpha158因子模型训练"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 股票选择
        stock_group = QtWidgets.QGroupBox(_("股票选择"))
        stock_layout = QtWidgets.QVBoxLayout()
        stock_group.setLayout(stock_layout)
        layout.addWidget(stock_group)

        # 股票代码输入（逗号分隔）
        self.alpha158_symbols_input = QtWidgets.QLineEdit("000001,000002,000004")
        self.alpha158_symbols_input.setPlaceholderText(_("请输入股票代码，用逗号分隔，如：000001,000002"))
        stock_layout.addWidget(self.alpha158_symbols_input)

        # 日期范围
        date_group = QtWidgets.QGroupBox(_("日期范围"))
        date_layout = QtWidgets.QGridLayout()
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        date_layout.addWidget(QtWidgets.QLabel(_("开始日期：")), 0, 0)
        self.alpha158_start_date = QtWidgets.QDateEdit()
        self.alpha158_start_date.setCalendarPopup(True)
        self.alpha158_start_date.setDate(QtCore.QDate(2025, 1, 1))
        date_layout.addWidget(self.alpha158_start_date, 0, 1)

        date_layout.addWidget(QtWidgets.QLabel(_("结束日期：")), 0, 2)
        self.alpha158_end_date = QtWidgets.QDateEdit()
        self.alpha158_end_date.setCalendarPopup(True)
        self.alpha158_end_date.setDate(QtCore.QDate(2026, 2, 1))
        date_layout.addWidget(self.alpha158_end_date, 0, 3)

        # 训练配置
        config_group = QtWidgets.QGroupBox(_("训练配置"))
        config_layout = QtWidgets.QGridLayout()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        config_layout.addWidget(QtWidgets.QLabel(_("训练集结束：")), 0, 0)
        self.alpha158_train_end = QtWidgets.QDateEdit()
        self.alpha158_train_end.setCalendarPopup(True)
        self.alpha158_train_end.setDate(QtCore.QDate(2025, 6, 30))
        config_layout.addWidget(self.alpha158_train_end, 0, 1)

        config_layout.addWidget(QtWidgets.QLabel(_("验证集结束：")), 0, 2)
        self.alpha158_val_end = QtWidgets.QDateEdit()
        self.alpha158_val_end.setCalendarPopup(True)
        self.alpha158_val_end.setDate(QtCore.QDate(2025, 9, 30))
        config_layout.addWidget(self.alpha158_val_end, 0, 3)

        config_layout.addWidget(QtWidgets.QLabel(_("训练轮数：")), 1, 0)
        self.alpha158_rounds = QtWidgets.QSpinBox()
        self.alpha158_rounds.setRange(10, 5000)
        self.alpha158_rounds.setValue(100)
        config_layout.addWidget(self.alpha158_rounds, 1, 1)

        # 训练按钮
        train_btn = QtWidgets.QPushButton(_("开始训练"))
        train_btn.clicked.connect(self.start_alpha158_training)
        config_layout.addWidget(train_btn, 1, 2, 1, 2)

        # 进度条
        self.alpha158_progress = QtWidgets.QProgressBar()
        layout.addWidget(self.alpha158_progress)

        # 状态显示
        self.alpha158_status = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.alpha158_status)

        # 日志显示
        log_group = QtWidgets.QGroupBox(_("训练日志"))
        log_layout = QtWidgets.QVBoxLayout()
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.alpha158_log = QtWidgets.QTextEdit()
        self.alpha158_log.setReadOnly(True)
        self.alpha158_log.setMaximumHeight(200)
        log_layout.addWidget(self.alpha158_log)

        return widget

    def start_alpha158_training(self) -> None:
        """开始Alpha158训练"""
        # 获取参数
        symbols_text = self.alpha158_symbols_input.text()
        symbols = [s.strip() for s in symbols_text.split(",") if s.strip()]

        if not symbols:
            self.alpha158_status.setText(_("请输入股票代码"))
            return

        start_date = self.alpha158_start_date.date().toString("yyyy-MM-dd")
        end_date = self.alpha158_end_date.date().toString("yyyy-MM-dd")
        train_end = self.alpha158_train_end.date().toString("yyyy-MM-dd")
        val_end = self.alpha158_val_end.date().toString("yyyy-MM-dd")
        rounds = self.alpha158_rounds.value()

        self.alpha158_status.setText(_("正在训练..."))
        self.alpha158_progress.setValue(10)
        self.alpha158_log.clear()

        # 异步执行训练
        QtCore.QTimer.singleShot(100, lambda: self._do_alpha158_training(
            symbols, start_date, end_date, train_end, val_end, rounds
        ))

    def _do_alpha158_training(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        train_end: str,
        val_end: str,
        rounds: int
    ) -> None:
        """执行Alpha158训练"""
        try:
            import os
            os.environ['MYSQL_PASSWORD'] = 'Vnpy2024!'

            from vnpy_china_data.database import DatabaseManager
            import polars as pl
            import pymysql

            self.alpha158_log.append(_("正在加载数据..."))

            # 连接数据库
            db = DatabaseManager()
            db.connect()

            # 查询数据
            MYSQL_CONFIG = {
                'host': 'localhost',
                'port': 3306,
                'user': 'vnpy',
                'password': 'Vnpy2024!',
                'database': 'vnpy_china',
                'charset': 'utf8mb4',
            }

            conn = pymysql.connect(**MYSQL_CONFIG)
            placeholders = ','.join(['%s'] * len(symbols))
            query = f"""
                SELECT datetime, symbol, exchange, open_price, high_price, low_price, close_price, volume, turnover
                FROM db_bar_data
                WHERE datetime >= '{start_date}' AND datetime <= '{end_date}'
                AND symbol IN ({placeholders}) AND `interval` = 'd'
                ORDER BY symbol, datetime
            """

            with conn.cursor() as cursor:
                cursor.execute(query, symbols)
                rows = cursor.fetchall()
            conn.close()

            self.alpha158_log.append(_(f"加载了 {len(rows)} 条记录"))

            if len(rows) == 0:
                self.alpha158_log.append(_("错误：没有查询到数据"))
                self.alpha158_status.setText(_("无数据"))
                self.alpha158_progress.setValue(0)
                return

            # 创建DataFrame
            df = pl.DataFrame(
                rows,
                schema=['datetime', 'symbol', 'exchange', 'open', 'high', 'low', 'close', 'volume', 'turnover'],
                orient='row'
            )

            # 转换类型
            numeric_cols = ["open", "high", "low", "close", "volume", "turnover"]
            df = df.with_columns([pl.col(c).cast(pl.Float64).alias(c) for c in numeric_cols])

            # 计算vwap
            df = df.with_columns([
                ((pl.col("high") + pl.col("low") + pl.col("close")) / 3 * pl.col("volume")).alias("vwap")
            ])

            df = df.with_columns([
                (pl.col("symbol") + "." + pl.col("exchange")).alias("vt_symbol")
            ]).drop("exchange")

            self.alpha158_progress.setValue(30)
            self.alpha158_log.append(_("正在创建Alpha158数据集..."))

            # 创建Alpha158数据集
            from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158

            dataset = Alpha158(
                df=df,
                train_period=(start_date, train_end),
                valid_period=(train_end, val_end),
                test_period=(val_end, end_date)
            )

            self.alpha158_log.append(_("正在计算Alpha158因子..."))
            self.alpha158_progress.setValue(40)

            dataset.prepare_data()

            self.alpha158_progress.setValue(70)
            self.alpha158_log.append(_("正在训练模型..."))

            # 训练模型
            from vnpy.alpha.model.models.lgb_model import LgbModel

            model = LgbModel(
                learning_rate=0.1,
                num_leaves=31,
                num_boost_round=rounds,
                early_stopping_rounds=50,
                log_evaluation_period=rounds // 5 if rounds > 5 else 1,
                seed=42
            )

            model.fit(dataset)

            # 保存模型
            from pathlib import Path
            model_path = Path.home() / "vnpy_lab/model"
            model_path.mkdir(parents=True, exist_ok=True)
            model.model.save_model(str(model_path / "gui_alpha158_lgb.txt"))

            self.alpha158_progress.setValue(100)
            self.alpha158_log.append(_("训练完成！模型已保存到 ~/vnpy_lab/model/gui_alpha158_lgb.txt"))
            self.alpha158_status.setText(_("训练完成"))

        except Exception as e:
            import traceback
            self.alpha158_log.append(_(f"错误: {str(e)}"))
            self.alpha158_log.append(traceback.format_exc())
            self.alpha158_status.setText(_("训练失败"))
            self.alpha158_progress.setValue(0)

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaMlWidget"]
