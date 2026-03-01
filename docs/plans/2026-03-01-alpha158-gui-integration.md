# Alpha158 GUI集成实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在A股机器学习模块GUI中添加Alpha158因子训练功能的新标签页

**Architecture:** 基于现有train_alpha158_model.py的成功逻辑，创建新的GUI标签页，允许用户选择股票、设置日期范围、配置模型参数并执行训练

**Tech Stack:** PySide6 GUI, vnpy.alpha.dataset, vnpy_china_ml

---

## 实现任务

### Task 1: 在widget.py中添加Alpha158标签页UI

**Files:**
- Modify: `vnpy_china_ml/ui/widget.py:80-85`

**Step 1: 添加新标签页**

在create_feature_tab之后添加Alpha158标签页：

```python
# Alpha158标签页
alpha158_widget = self.create_alpha158_tab()
tab.addTab(alpha158_widget, "Alpha158训练")
```

**Step 2: 创建Alpha158标签页UI**

在widget.py末尾添加方法：

```python
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
    self.alpha158_symbols_input.setPlaceholderText("请输入股票代码，用逗号分隔，如：000001,000002")
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
```

**Step 3: 添加训练方法**

```python
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
            log_evaluation_period=rounds // 5,
            seed=42
        )

        model.fit(dataset)

        # 保存模型
        from pathlib import Path
        model_path = Path.home() / "vnpy_lab/model"
        model_path.mkdir(parents=True, exist_ok=True)
        model.model.save_model(str(model_path / "gui_alpha158_lgb.txt"))

        self.alpha158_progress.setValue(100)
        self.alpha158_log.append(_("训练完成！模型已保存"))
        self.alpha158_status.setText(_("训练完成"))

    except Exception as e:
        import traceback
        self.alpha158_log.append(_(f"错误: {str(e)}"))
        self.alpha158_log.append(traceback.format_exc())
        self.alpha158_status.setText(_("训练失败"))
        self.alpha158_progress.setValue(0)
```

### Task 2: 添加国际化翻译支持

**Files:**
- Modify: 需要检查是否有翻译文件

确保"Alpha158训练"等文本有翻译支持。

### Task 3: 测试验证

**Step 1: 验证GUI可以启动**

```bash
conda run -n Quant-3.11 python -c "
from vnpy_china_ml.ui.widget import ChinaMlWidget
print('UI模块导入成功')
"
```

---

## 执行选项

**Plan complete and saved. Two execution options:**

1. **Subagent-Driven** - 我在这里逐个任务执行
2. **Parallel Session** - 在新会话中执行

需要我开始执行这个计划吗？
