# -*- coding:utf-8 -*-
"""
VeighNa RPC服务端 - 带QMT自动连接
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.rpcservice import RpcServiceApp
from vnpy_qmt import QmtGateway

# RPC服务配置
RPC_SETTING = {
    "req_address": "tcp://0.0.0.0:2014",
    "sub_address": "tcp://0.0.0.0:4102",
}

# QMT配置 - 替换为你的配置
QMT_SETTING = {
    "交易账号": "40218291",
    "mini路径": "D:/国金证券QMT交易端/userdata_mini/",
}


def main():
    print("=" * 60)
    print("VeighNa RPC服务端 - QMT自动连接版")
    print("=" * 60)

    # 创建事件引擎
    event_engine = EventEngine()

    # 创建主引擎
    main_engine = MainEngine(event_engine)

    # 添加QMT网关
    main_engine.add_gateway(QmtGateway)

    # 添加RPC服务
    rpc_service = RpcServiceApp()
    main_engine.add_app(rpc_service)

    # 启动RPC服务
    rpc_service.start_server(
        req_address=RPC_SETTING["req_address"],
        sub_address=RPC_SETTING["sub_address"]
    )

    print("\nRPC服务已启动:")
    print(f"  请求地址: {RPC_SETTING['req_address']}")
    print(f"  订阅地址: {RPC_SETTING['sub_address']}")

    # 自动连接QMT
    print("\n正在连接QMT...")
    main_engine.connect(QMT_SETTING, "QMT")

    print(f"  账号: {QMT_SETTING['交易账号']}")
    print(f"  路径: {QMT_SETTING['mini路径']}")

    print("\n" + "=" * 60)
    print("请在VeighNa Trader界面确认QMT连接状态")
    print("或等待账户登录成功后即可远程交易")
    print("=" * 60)

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        main_engine.close()


if __name__ == "__main__":
    main()
