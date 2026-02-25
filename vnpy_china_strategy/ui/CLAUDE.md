# vnpy_china_strategy UI 组件

> 更新时间：2026-02-25
> 版本：1.0.0

## 模块概述

UI 模块提供 A股策略的图形用户界面组件，包括策略管理、数据查询和策略配置功能。

## 组件架构

```
ui/
├── __init__.py           # 模块入口
├── widget.py             # UI组件实现
└── CLAUDE.md            # 本文档
```

## 核心组件

### ChinaStrategyWidget (主界面)

A股策略主界面，包含6个标签页：

| 标签页 | 组件 | 功能 |
|--------|------|------|
| 策略列表 | StrategyListWidget | 策略管理和监控 |
| 龙虎榜策略 | DragonTigerStrategyWidget | 龙虎榜数据查询和策略配置 |
| 北向资金 | NorthboundStrategyWidget | 北向资金数据查询 |
| 板块轮动 | SectorRotationWidget | 板块强度和轮动信号 |
| 事件驱动 | EventDrivenWidget | 业绩预告和政策事件查询 |
| 可转债 | ConvertibleWidget | 可转债套利机会查询 |

### StrategyListWidget (策略列表)

策略列表监控组件，提供：

- **功能**：
  - 显示所有A股策略的运行状态
  - 策略启动/停止控制
  - 自动定时刷新（5秒间隔）
  - 策略状态颜色显示（运行中=绿色，已停止=红色）

- **表格列**：
  - 策略名称
  - 合约代码
  - 策略类型
  - 状态
  - 仓位
  - 盈亏
  - 创建时间

- **方法**：
  - `refresh_data()`: 刷新策略列表
  - `start_selected_strategy()`: 启动选中策略
  - `stop_selected_strategy()`: 停止选中策略

### DragonTigerStrategyWidget (龙虎榜策略)

龙虎榜策略界面，提供：

- **功能**：
  - 按日期查询龙虎榜数据
  - 显示机构席位和游资动向
  - 数据颜色编码（上涨=红色，下跌=绿色）

- **查询参数**：
  - 查询日期（QDateEdit）

- **表格列**：
  - 代码
  - 名称
  - 交易日期
  - 收盘价
  - 涨跌幅(%)
  - 换手率(%)
  - 机构净买入
  - 上榜原因

- **方法**：
  - `query_dragon_tiger()`: 查询龙虎榜数据
  - `refresh_data()`: 刷新数据（使用当前日期）
  - `update_table(data)`: 更新表格显示

### NorthboundStrategyWidget (北向资金)

北向资金策略界面，提供：

- **功能**：
  - 北向资金流向查询
  - 板块偏好分析
  - 数据分标签页显示

- **查询参数**：
  - 查询日期（QDateEdit）

- **标签页**：
  - 资金流向：显示沪股通、深股通、合计数据
  - 板块偏好：显示各板块净流入和占比

- **方法**：
  - `query_flow()`: 查询资金流向
  - `query_sector()`: 查询板块偏好
  - `refresh_data()`: 刷新数据

### SectorRotationWidget (板块轮动)

板块轮动策略界面，提供：

- **功能**：
  - 板块强度查询和排序
  - 轮动信号识别
  - 强度评分计算

- **查询参数**：
  - 查询日期（QDateEdit）
  - 板块选择（ComboBox）

- **支持的板块**：
  - 半导体、新能源、医药生物
  - 食品饮料、计算机、电子
  - 通信、传媒、有色金属

- **标签页**：
  - 板块强度：显示涨跌幅、成交量、强度评分
  - 轮动信号：显示买入/卖出/持有信号

- **方法**：
  - `query_strength()`: 查询板块强度
  - `query_signal()`: 查询轮动信号
  - `_calculate_strength_score()`: 计算强度评分

### EventDrivenWidget (事件驱动)

事件驱动策略界面，提供：

- **功能**：
  - 业绩预告查询
  - 政策事件查询

- **查询参数**：
  - 股票代码（QLineEdit）

- **标签页**：
  - 业绩预告：显示公告日期、报告期、预告类型、净利润变动
  - 政策事件：显示发布日期、政策类型、影响板块、政策内容

- **方法**：
  - `query_earnings()`: 查询业绩预告
  - `query_policy()`: 查询政策事件
  - `refresh_data()`: 刷新数据

### ConvertibleWidget (可转债)

可转债套利策略界面，提供：

- **功能**：
  - 可转债列表查询
  - 溢价率筛选
  - 套利空间计算

- **查询参数**：
  - 溢价率筛选（QDoubleSpinBox，-50% ~ 50%）

- **表格列**：
  - 转债代码
  - 转债名称
  - 正股代码
  - 正股名称
  - 转债价格
  - 转股溢价率(%)
  - 套利空间

- **方法**：
  - `query_convertible()`: 查询可转债列表
  - `refresh_data()`: 刷新数据

## UI设计规范

### 颜色编码

| 类型 | 颜色 | 说明 |
|------|------|------|
| 正值/上涨 | 红色 | 表示收益或上涨 |
| 负值/下跌 | 绿色 | 表示亏损或下跌 |
| 运行中状态 | 绿色 | 策略正在运行 |
| 停止状态 | 红色 | 策略已停止 |

### 布局结构

```python
# 标准布局
layout = QVBoxLayout()

# 1. 标题
title = QLabel("策略名称")
title.setStyleSheet("font-size: 16px; font-weight: bold;")
layout.addWidget(title)

# 2. 策略说明
desc = QLabel("策略说明...")
desc.setWordWrap(True)
layout.addWidget(desc)

# 3. 查询控制区
query_group = QGroupBox("数据查询")
query_layout = QHBoxLayout()
# ... 添加控件
layout.addWidget(query_group)

# 4. 状态标签
status_label = QLabel("就绪")
status_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
layout.addWidget(status_label)

# 5. 数据表格
table = QTableWidget()
layout.addWidget(table)
```

### 表格设置

```python
# 标准表格设置
table.setSelectionBehavior(QAbstractItemView.SelectRows)
table.setEditTriggers(QAbstractItemView.NoEditTriggers)
table.setAlternatingRowColors(True)
table.resizeColumnsToContents()
```

## 使用示例

### 基本使用

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_china_strategy.ui import ChinaStrategyWidget

# 创建主引擎
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 添加A股策略应用
main_engine.add_app(ChinaStrategyApp)

# 创建UI组件
widget = ChinaStrategyWidget(main_engine, event_engine)
widget.show()
```

### 独立组件使用

```python
from vnpy_china_strategy.ui import DragonTigerStrategyWidget

# 创建龙虎榜组件
dragon_widget = DragonTigerStrategyWidget(main_engine, event_engine, gui_engine)
dragon_widget.show()

# 查询数据
dragon_widget.query_dragon_tiger()
```

## 依赖项

- vnpy.trader.ui (VeighNa UI组件)
- vnpy.trader.locale (国际化)
- PyQt6/PySide6 (Qt框架)
- gui_engine (ChinaStrategyGuiEngine)

## 开发指南

### 添加新的策略页面

1. 在 `widget.py` 中创建新的 Widget 类：

```python
class NewStrategyWidget(QtWidgets.QWidget):
    """新策略界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

    def init_ui(self) -> None:
        # 实现UI初始化
        pass
```

2. 在 `ChinaStrategyWidget` 中添加标签页：

```python
new_widget = NewStrategyWidget(self.main_engine, self.event_engine, self.gui_engine)
tab_widget.addTab(new_widget, _("新策略"))
```

3. 在 `__all__` 中导出新组件：

```python
__all__ = [
    # ...
    "NewStrategyWidget",
]
```

### 添加新的查询方法

1. 在 `gui_engine.py` 中添加查询方法：

```python
def query_new_data(self, param: str) -> List[Dict[str, Any]]:
    """查询新数据"""
    # 实现查询逻辑
    pass
```

2. 在 UI 组件中调用：

```python
def query_new_data(self) -> None:
    """查询新数据"""
    if not self.gui_engine:
        return

    data = self.gui_engine.query_new_data(param)
    self.update_table(data)
```

## 变更记录

### 2026-02-25 (第一版)
- ✨ 创建 UI 组件模块
- 📊 实现 ChinaStrategyWidget 主界面
- 🔧 实现 StrategyListWidget 策略列表组件
- 🔧 实现 DragonTigerStrategyWidget 龙虎榜策略界面
- 🔧 实现 NorthboundStrategyWidget 北向资金策略界面
- 🔧 实现 SectorRotationWidget 板块轮动策略界面
- 🔧 实现 EventDrivenWidget 事件驱动策略界面
- 🔧 实现 ConvertibleWidget 可转债策略界面
- 🎨 实现颜色编码和状态显示
- 📖 完成文档编写


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Feb 25, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #7105 | 4:16 PM | 🟣 | vnpy_china_strategy UI module initialized | ~149 |
</claude-mem-context>