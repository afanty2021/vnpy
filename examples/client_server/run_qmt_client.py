# -*- coding:utf-8 -*-
"""
VeighNa RPC客户端 - Mac版本
使用RpcGateway连接远程QMT
自定义显示配置
"""

import sys
import os
from pathlib import Path
from typing import Any

# 消除macOS Qt输入法警告
os.environ["QT_MAC_DISABLE_IMK"] = "1"

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 修改全局小数位数显示
import vnpy.trader.ui.widget as widget
from vnpy.trader.ui.widget import BaseCell

# 保存原始方法
_original_set_content = BaseCell.set_content

def _new_set_content(self, content: Any, data: Any) -> None:
    """自定义格式化 - 成交额等大数显示亿/万，其余保留2位小数。

    保留原始数值到 _sort_value 供 BaseCell.__lt__ 数值排序（格式化成"5.12亿"后
    仍按原值排序，避免字符串排序错乱）。
    """
    if isinstance(content, float):
        self._sort_value = content
        abs_v = abs(content)
        if abs_v >= 1e8:        # ≥1亿：显示 X.XX亿（成交额）
            content = f"{content/1e8:.2f}亿"
        elif abs_v >= 1e4:      # ≥1万：<1亿的成交额显示 X.XX万
            content = f"{content/1e4:.2f}万"
        else:                   # 价格/量比/均价等小数：保留2位
            content = f"{content:.2f}"
    else:
        self._sort_value = None
    _original_set_content(self, content, data)

# 应用修改
BaseCell.set_content = _new_set_content

# 修改PositionMonitor - 修改显示名称
from vnpy.trader.ui.widget import PositionMonitor

# 直接修改类属性来改变显示名称
PositionMonitor.headers = {
    "symbol": {"display": "代码", "cell": widget.BaseCell, "update": False},
    "name": {"display": "名称", "cell": widget.BaseCell, "update": False},
    "volume": {"display": "数量", "cell": widget.BaseCell, "update": True},
    "yd_volume": {"display": "昨仓", "cell": widget.BaseCell, "update": True},
    "price": {"display": "成本价", "cell": widget.BaseCell, "update": True},
    "pnl": {"display": "盈亏", "cell": widget.PnlCell, "update": True},
    "gateway_name": {"display": "接口", "cell": widget.BaseCell, "update": False},
}

# 修改AccountMonitor - 添加可用现金字段
from vnpy.trader.ui.widget import AccountMonitor
from vnpy.trader.object import AccountData

AccountMonitor.headers = {
    "accountid": {"display": "账号", "cell": widget.BaseCell, "update": False},
    "balance": {"display": "总资产", "cell": widget.BaseCell, "update": True},
    "cash": {"display": "可用现金", "cell": widget.BaseCell, "update": True},
    "gateway_name": {"display": "接口", "cell": widget.BaseCell, "update": False},
}

# 重写 insert_new_row 方法来处理 cash 字段
_original_insert_new_row = AccountMonitor.insert_new_row
def _insert_new_row(self, data):
    """插入新行 - 特殊处理 cash 字段"""
    self.insertRow(0)

    row_cells = {}
    for column, header in enumerate(self.headers.keys()):
        setting = self.headers[header]

        # 特殊处理 cash 字段 - 从 extra 中获取
        if header == "cash":
            extra = getattr(data, 'extra', None) or {}
            content = extra.get('cash', 0)
        else:
            # 安全获取属性，使用 getattr 而不是 __getattribute__
            content = getattr(data, header, 0)

        cell = setting["cell"](content, data)
        self.setItem(0, column, cell)

        if setting["update"]:
            row_cells[header] = cell

    if self.data_key:
        key = getattr(data, self.data_key, None)
        if key is not None:
            self.cells[key] = row_cells

AccountMonitor.insert_new_row = _insert_new_row

# 重写 update_old_row 方法来处理 cash 字段
_original_update_old_row = AccountMonitor.update_old_row
def _update_old_row(self, data):
    """更新旧行 - 特殊处理 cash 字段"""
    key = getattr(data, self.data_key, None)
    if key is None:
        return

    row_cells = self.cells.get(key)
    if row_cells is None:
        return

    for header, cell in row_cells.items():
        # 特殊处理 cash 字段 - 从 extra 中获取
        if header == "cash":
            extra = getattr(data, 'extra', None) or {}
            content = extra.get('cash', 0)
        else:
            # 安全获取属性，使用 getattr 而不是 __getattribute__
            content = getattr(data, header, 0)
        cell.set_content(content, data)

AccountMonitor.update_old_row = _update_old_row

# === 委托/成交表：去 委托号/交易所/开平，增 股票名称（复用持仓表的合约查名逻辑）===
# OrderData/TradeData 与 PositionData 一样自身不带 name 字段，股票名称需从
# ContractData.name 实时查询，来源同 vnpy 原生 PositionMonitor._get_position_name。
from vnpy.trader.ui.widget import OrderMonitor, TradeMonitor


def _resolve_contract_name(monitor, data: Any) -> str:
    """股票名称取自合约信息。

    OrderData/TradeData 自身不带名称，通过 vt_symbol 查 ContractData.name 补全，
    与持仓列表的 _get_position_name 同一来源。
    """
    try:
        vt_symbol: str = f"{data.symbol}.{data.exchange.value}"
        contract = monitor.main_engine.get_contract(vt_symbol)
        if contract and contract.name:
            return contract.name
    except Exception:
        pass
    return ""


def _insert_new_row_with_name(self, data: Any) -> None:
    """插入新行 - name 列走合约查名，其余列复用 BaseMonitor._get_attr 安全取值。"""
    self.insertRow(0)

    row_cells: dict = {}
    for column, header in enumerate(self.headers.keys()):
        setting: dict = self.headers[header]

        if header == "name":
            content = _resolve_contract_name(self, data)
        else:
            content = self._get_attr(data, header, "")

        cell = setting["cell"](content, data)
        self.setItem(0, column, cell)

        if setting["update"]:
            row_cells[header] = cell

    if self.data_key:
        key = self._get_attr(data, self.data_key, "")
        self.cells[key] = row_cells


def _update_old_row_with_name(self, data: Any) -> None:
    """更新旧行 - name 列走合约查名。"""
    key = self._get_attr(data, self.data_key, "")
    row_cells = self.cells.get(key)
    if row_cells is None:
        return

    for header, cell in row_cells.items():
        if header == "name":
            content = _resolve_contract_name(self, data)
        else:
            content = self._get_attr(data, header, "")
        cell.set_content(content, data)


# 委托表：去 委托号(orderid)/交易所(exchange)/开平(offset)，增 名称
# 活动委托表 ActiveOrderMonitor 继承自 OrderMonitor，自动生效
OrderMonitor.headers = {
    "reference": {"display": "来源", "cell": widget.BaseCell, "update": False},
    "symbol": {"display": "代码", "cell": widget.BaseCell, "update": False},
    "name": {"display": "名称", "cell": widget.BaseCell, "update": False},
    "type": {"display": "类型", "cell": widget.EnumCell, "update": False},
    "direction": {"display": "方向", "cell": widget.DirectionCell, "update": False},
    "price": {"display": "价格", "cell": widget.BaseCell, "update": False},
    "volume": {"display": "总数量", "cell": widget.BaseCell, "update": True},
    "traded": {"display": "已成交", "cell": widget.BaseCell, "update": True},
    "status": {"display": "状态", "cell": widget.EnumCell, "update": True},
    "datetime": {"display": "时间", "cell": widget.TimeCell, "update": True},
    "gateway_name": {"display": "接口", "cell": widget.BaseCell, "update": False},
}
OrderMonitor.insert_new_row = _insert_new_row_with_name
OrderMonitor.update_old_row = _update_old_row_with_name

# 成交表：去 委托号(orderid)/交易所(exchange)/开平(offset)，增 名称
TradeMonitor.headers = {
    "tradeid": {"display": "成交号", "cell": widget.BaseCell, "update": False},
    "symbol": {"display": "代码", "cell": widget.BaseCell, "update": False},
    "name": {"display": "名称", "cell": widget.BaseCell, "update": False},
    "direction": {"display": "方向", "cell": widget.DirectionCell, "update": False},
    "price": {"display": "价格", "cell": widget.BaseCell, "update": False},
    "volume": {"display": "数量", "cell": widget.BaseCell, "update": False},
    "datetime": {"display": "时间", "cell": widget.TimeCell, "update": False},
    "gateway_name": {"display": "接口", "cell": widget.BaseCell, "update": False},
}
TradeMonitor.insert_new_row = _insert_new_row_with_name
TradeMonitor.update_old_row = _update_old_row_with_name

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_rpcservice.rpc_gateway import RpcGateway

# 导入A股增强模块App
from vnpy_china_strategy import ChinaStrategyApp
from vnpy_china_analysis import ChinaAnalysisApp
from vnpy_china_rules import ChinaRulesApp
from vnpy_china_data import ChinaDataApp
from vnpy_china_backtest import ChinaBacktestApp
from vnpy_china_capital import ChinaCapitalApp
from vnpy_china_ml import ChinaMlApp

# 导入配置管理
from vnpy_china_config import ConfigManager, GlobalConfig


def load_rpc_config() -> dict:
    """加载RPC配置

    优先级：
    1. 配置文件（client.yaml）
    2. 环境变量
    3. 默认值
    """
    import os

    # 重置单例以清除可能的缓存
    ConfigManager.reset_instance()

    # 设置配置文件路径（项目根目录/.vntrader_china/config）
    config_dir = Path(__file__).parent.parent.parent / ".vntrader_china/config"
    config_manager = ConfigManager()
    config_manager.set_config_path(config_dir)

    # 加载客户端配置
    config = config_manager.load_config(force_reload=True)

    # 从配置获取RPC地址
    req_address = config.rpc.rep_address
    sub_address = config.rpc.pub_address

    # 支持环境变量覆盖
    req_address = os.getenv("QMT_RPC_REQ_ADDRESS", req_address)
    sub_address = os.getenv("QMT_RPC_SUB_ADDRESS", sub_address)

    return {
        "主动请求地址": req_address,
        "推送订阅地址": sub_address,
    }


def restore_submitted_layout(main_window) -> None:
    """从项目文件恢复提交的布局，跨平台兼容。

    1. 给所有 dock 设固定英文 objectName（saveState/restoreState 用 objectName 匹配，
       不依赖 windowTitle，保证 Windows ↔ macOS 之间正确识别）。
    2. 若布局文件存在：restoreState（文件布局覆盖注册表 custom 布局）。
    3. 若文件不存在：保持 load_window_setting("custom") 的注册表布局。
    """
    import json
    from PySide6 import QtCore, QtWidgets

    # 给 dock 设固定英文 objectName（跨平台一致）
    _DOCK_NAMES: dict[str, str] = {
        "交易": "trade_input",
        "行情": "tick_monitor",
        "委托": "order_monitor",
        "活动": "active_order_monitor",
        "成交": "trade_monitor",
        "日志": "log_monitor",
        "资金": "account_monitor",
        "持仓": "position_monitor",
    }
    for dock in main_window.findChildren(QtWidgets.QDockWidget):
        name = _DOCK_NAMES.get(dock.windowTitle())
        if name:
            dock.setObjectName(name)

    layout_path = Path(__file__).parent / "layout" / "custom_layout.json"
    if not layout_path.exists():
        return
    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        state_b64 = layout.get("state", "")
        if state_b64:
            state = QtCore.QByteArray.fromBase64(state_b64.encode())
            main_window.restoreState(state)
        geo_b64 = layout.get("geometry", "")
        if geo_b64:
            geom = QtCore.QByteArray.fromBase64(geo_b64.encode())
            main_window.restoreGeometry(geom)
        print(f"✓ 已加载提交的布局: {layout_path.name}")
    except Exception as e:
        print(f"⚠ 加载布局文件失败（使用注册表布局）: {e}")


def start_gui_with_rpc():
    """启动带RPC的GUI界面"""
    # 初始化日志（须在 EventEngine/MainEngine 之前，统一读取 config.yaml 的 logging 配置）
    ConfigManager.reset_instance()
    _cm = ConfigManager()
    _cm.set_config_path(Path(__file__).parent.parent.parent / ".vntrader_china/config")
    from vnpy_china_config.logging_config import setup_logging_from_config
    setup_logging_from_config(_cm.load_config(force_reload=True))

    # 加载RPC配置
    RPC_SETTING = load_rpc_config()

    qapp = create_qapp()
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加RPC网关
    rpc_gateway = main_engine.add_gateway(RpcGateway, "RPC")

    # 连接RPC
    print("正在连接RPC...")
    main_engine.connect(RPC_SETTING, "RPC")
    print("✓ 已连接到Windows QMT服务端")

    # 添加A股增强模块
    print("\n正在加载A股增强模块...")
    main_engine.add_app(ChinaStrategyApp)
    print("  ✓ A股策略模块")
    main_engine.add_app(ChinaAnalysisApp)
    print("  ✓ A股分析模块")
    main_engine.add_app(ChinaRulesApp)
    print("  ✓ A股规则模块")
    main_engine.add_app(ChinaDataApp)
    print("  ✓ A股数据模块")
    main_engine.add_app(ChinaBacktestApp)
    print("  ✓ A股回测模块")
    main_engine.add_app(ChinaCapitalApp)
    print("  ✓ A股资金模块")
    main_engine.add_app(ChinaMlApp)
    print("  ✓ A股机器学习模块")
    print("✓ A股增强模块加载完成")

    # 报表数据源：每日18:30自动落库权益快照（权益变化法盈亏的期初权益源）
    reporting_svc = None
    try:
        from vnpy_china_reporting.data_source import ReportingDataService
        ConfigManager.reset_instance()
        _cm = ConfigManager()
        _cm.set_config_path(Path(__file__).parent.parent.parent / ".vntrader_china/config")
        _global_config = _cm.load_config(force_reload=True)
        reporting_svc = ReportingDataService(main_engine=main_engine, config=_global_config)
        reporting_svc.setup()
        reporting_svc.start_daily_equity("18:30")
        print("  ✓ 报表数据源已启动（每日18:30自动落库权益快照，跳过周末）")
    except Exception as e:
        print(f"  ⚠ 报表数据源启动失败（不影响交易主流程）: {e}")

    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)

    # 回补委托/成交快照（RPC 模式时序修复）
    # RpcGateway.connect 的 query_all 在 MainWindow 创建前执行，此时
    # OrderMonitor/TradeMonitor 尚未注册，委托/成交快照事件被 EventEngine 丢弃。
    # 而 QMT 网关对“已稳定委托”有状态去重（td.py on_stock_order）、对成交仅首帧
    # 查询一次（qmt_gateway.process_timer_event），收盘后重连无法靠实时事件补回。
    # 此处 Monitor 已就绪（MainWindow.__init__ 内已 register_event），用 main_engine
    # 缓存重新推送即可显示。（connect 时 RpcGateway.on_order/on_trade 已把快照写入
    # 客户端 main_engine.orders/trades 缓存，与持仓/资金同一来源。）
    from vnpy.event import Event
    from vnpy.trader.event import EVENT_ORDER, EVENT_TRADE
    for order in main_engine.get_all_orders():
        event_engine.put(Event(EVENT_ORDER, order))
    for trade in main_engine.get_all_trades():
        event_engine.put(Event(EVENT_TRADE, trade))

    # 加载之前保存的窗口布局
    main_window.load_window_setting("custom")

    # 恢复 git 提交的布局文件（如存在，跨平台兼容；否则用注册表 custom 布局）
    restore_submitted_layout(main_window)

    # 布局请手动调整：拖动 dock 至期望位置 → 关闭客户端时 vnpy 自动保存 custom 布局 →
    # 下次启动自动加载。如需代码固化布局，改用 QTabWidget 方案（避免 dock API）。

    main_window.showMaximized()

    print("\n" + "=" * 60)
    print("VeighNa Trader - RPC连接模式")
    print("=" * 60)
    print(f"  请求地址: {RPC_SETTING['主动请求地址']}")
    print(f"  订阅地址: {RPC_SETTING['推送订阅地址']}")
    print("  显示精度: 2位小数")
    print("  功能模块: A股策略、分析、规则、数据、回测、资金、机器学习")
    print("\n配置说明:")
    print("  配置文件: .vntrader_china/config/global_development.yaml")
    print("  环境变量: QMT_RPC_REQ_ADDRESS, QMT_RPC_SUB_ADDRESS")
    print("=" * 60)

    qapp.exec()

    # 主窗口关闭后停止报表定时任务（scheduler 为 daemon 线程，此处优雅退出）
    if reporting_svc:
        reporting_svc.stop()


if __name__ == "__main__":
    start_gui_with_rpc()
