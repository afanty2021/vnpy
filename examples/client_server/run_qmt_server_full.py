# -*- coding:utf-8 -*-
"""
VeighNa RPC服务端 - 完整交易接口版
需要vnpy_rpcservice包
"""

import sys
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

# QMT配置
QMT_SETTING = {
    "交易账号": "40218291",
    "mini路径": "D:/国金证券QMT交易端/userdata_mini/",
}

RPC_SETTING = {
    "req_address": "tcp://0.0.0.0:2014",
    "sub_address": "tcp://0.0.0.0:4102",
}


def main():
    print("=" * 60)
    print("VeighNa RPC服务端 - 完整交易版")
    print("=" * 60)

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

    # 连接QMT
    print("\n连接QMT...")
    main_engine.connect(QMT_SETTING, "QMT")
    print(f"  账号: {QMT_SETTING['交易账号']}")

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
