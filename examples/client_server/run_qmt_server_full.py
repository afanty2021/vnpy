# -*- coding:utf-8 -*-
"""
VeighNa RPC服务端 - 完整交易接口版
需要vnpy_rpcservice包

使用统一的 global_development.yaml 配置文件管理所有配置，避免硬编码敏感信息。
配置文件位置: .vntrader_china/config/global_{environment}.yaml
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_qmt import QmtGateway

# 尝试导入rpcservice
try:
    from vnpy_rpcservice import RpcServiceApp
    from vnpy_rpcservice.rpc_service.engine import RpcEngine
    HAS_RPC = True
except ImportError:
    print("警告: 未安装vnpy_rpcservice，使用内置RPC")
    HAS_RPC = False
    from vnpy.rpc import RpcServer

# 尝试导入配置管理器
try:
    from vnpy_china_config.loader import ConfigManager
    from vnpy_china_config.global_config import GlobalConfig
    HAS_CONFIG = True
except ImportError:
    print("警告: 未安装vnpy_china_config，使用默认配置")
    HAS_CONFIG = False


def load_config():
    """加载配置

    Returns:
        tuple: (QMT_SETTING, RPC_SETTING)

    从 global_development.yaml 读取配置：
    - qmt.account_id: QMT 资金账号
    - qmt.mini_path: miniQMT 路径
    - qmt.session_id: QMT 会话ID（可选）
    - qmt.password: QMT 交易密码（可选）
    - rpc.rep_address: RPC 服务端监听地址（REP模式）
    - rpc.pub_address: RPC 服务端监听地址（PUB模式）
    """
    if not HAS_CONFIG:
        # 默认配置
        return {
            "交易账号": "",
            "mini路径": "",
        }, {
            "req_address": "tcp://0.0.0.0:2014",
            "sub_address": "tcp://0.0.0.0:4102",
        }

    # 从全局配置文件加载
    manager = ConfigManager()
    config = manager.load_global_config()

    # 构建 QMT_SETTING
    qmt_setting = {
        "交易账号": config.qmt.account_id or "",
        "mini路径": config.qmt.mini_path or "",
    }

    # 可选字段
    if config.qmt.session_id:
        qmt_setting["session_id"] = config.qmt.session_id
    if config.qmt.password:
        qmt_setting["密码"] = config.qmt.password

    # 构建 RPC_SETTING（使用全局 RPC 配置）
    rpc_setting = {
        "req_address": config.rpc.rep_address,
        "sub_address": config.rpc.pub_address,
    }

    # 支持环境变量覆盖
    rpc_setting["req_address"] = os.getenv("QMT_RPC_REP_ADDRESS", rpc_setting["req_address"])
    rpc_setting["sub_address"] = os.getenv("QMT_RPC_PUB_ADDRESS", rpc_setting["sub_address"])

    return qmt_setting, rpc_setting


def main():
    print("=" * 60)
    print("VeighNa RPC服务端 - 完整交易版")
    print("=" * 60)

    # 加载配置
    QMT_SETTING, RPC_SETTING = load_config()

    if HAS_CONFIG:
        manager = ConfigManager()
        print(f"\n配置环境: {manager.environment.value}")
        print(f"配置路径: {manager.config_path}")

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加QMT网关
    main_engine.add_gateway(QmtGateway)

    if HAS_RPC:
        # 使用完整的RPC服务
        rpc_engine: RpcEngine = main_engine.add_app(RpcServiceApp)

        print("\n启动RPC服务...")
        rpc_engine.start(
            rep_address=RPC_SETTING["req_address"],
            pub_address=RPC_SETTING["sub_address"]
        )
    else:
        print("错误: 需要安装vnpy_rpcservice")
        return

    print(f"RPC服务已启动:")
    print(f"  请求地址: {RPC_SETTING['req_address']}")
    print(f"  订阅地址: {RPC_SETTING['sub_address']}")

    # 验证 QMT 配置
    if not QMT_SETTING.get("交易账号") or not QMT_SETTING.get("mini路径"):
        print("\n错误: QMT 配置不完整!")
        print("请在配置文件中设置以下必填项:")
        print("  - qmt.account_id: QMT 资金账号")
        print("  - qmt.mini_path: QMT 客户端路径")

        if HAS_CONFIG:
            manager = ConfigManager()
            print(f"\n配置文件位置: {manager.config_path / 'global_development.yaml'}")
            print("\n配置示例:")
            print("qmt:")
            print("  account_id: \"YOUR_ACCOUNT_ID\"")
            print("  mini_path: \"D:/国金证券QMT交易端/userdata_mini/\"")
        return

    # 连接QMT
    print("\n连接QMT...")
    main_engine.connect(QMT_SETTING, "QMT")
    print(f"  账号: {QMT_SETTING['交易账号']}")
    print(f"  路径: {QMT_SETTING['mini路径']}")

    print("\n" + "=" * 60)
    print("服务运行中，按Ctrl+C停止")
    print("=" * 60)

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止服务...")
        main_engine.close()


if __name__ == "__main__":
    main()
