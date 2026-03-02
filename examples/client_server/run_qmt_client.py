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
    """自定义格式化 - 保留2位小数"""
    if isinstance(content, float):
        # 格式化浮点数，保留2位小数
        content = f"{content:.2f}"
    _original_set_content(self, content, data)

# 应用修改
BaseCell.set_content = _new_set_content

# 修改PositionMonitor - 修改显示名称
from vnpy.trader.ui.widget import PositionMonitor

# 直接修改类属性来改变显示名称
PositionMonitor.headers = {
    "symbol": {"display": "代码", "cell": widget.BaseCell, "update": False},
    "exchange": {"display": "交易所", "cell": widget.EnumCell, "update": False},
    "direction": {"display": "方向", "cell": widget.DirectionCell, "update": False},
    "volume": {"display": "数量", "cell": widget.BaseCell, "update": True},
    "yd_volume": {"display": "昨仓", "cell": widget.BaseCell, "update": True},
    "frozen": {"display": "冻结", "cell": widget.BaseCell, "update": True},
    "price": {"display": "成本价", "cell": widget.BaseCell, "update": True},
    "pnl": {"display": "盈亏", "cell": widget.PnlCell, "update": True},
    "gateway_name": {"display": "接口", "cell": widget.BaseCell, "update": False},
}

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

    # 设置配置文件路径
    config_dir = Path(__file__).parent / ".vntrader_china/config"
    config_manager = ConfigManager()
    config_manager.set_config_path(config_dir)

    # 加载客户端配置
    config = config_manager.load_client_config(force_reload=True)

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


def start_gui_with_rpc():
    """启动带RPC的GUI界面"""
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

    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)

    # 加载之前保存的窗口布局
    main_window.load_window_setting("custom")

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


if __name__ == "__main__":
    start_gui_with_rpc()
