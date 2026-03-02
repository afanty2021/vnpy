# -*- coding:utf-8 -*-
"""
VeighNa RPC服务端 - QMT版本

运行在Windows上，负责：
1. 连接QMT接口
2. 启动RPC服务
3. 接收Mac客户端的请求并执行交易

适用场景：
- Mac用户需要使用QMT接口
- 分布式部署
- 远程交易

环境要求：
- Windows 10/11
- QMT已安装并配置
- VeighNa框架
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置配置文件路径为当前目录
from vnpy_china_config import ConfigManager

config_dir = Path(__file__).parent.parent.parent / ".vntrader_china/config"
config_manager = ConfigManager()
config_manager.set_config_path(config_dir)

# 加载服务端配置
global_config = config_manager.load_qmt_gateway_config(force_reload=True)

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import TickData, BarData, OrderData, TradeData, PositionData, AccountData
from vnpy_rpcservice import RpcServiceApp
from vnpy_qmt import QmtGateway

# 从配置获取设置
RPC_SETTING = {
    "req_address": global_config.rpc.rep_address,
    "sub_address": global_config.rpc.pub_address,
}

QMT_SETTING = {
    "交易账号": global_config.qmt.account_id,
    "mini路径": global_config.qmt.mini_path,
}


class QmtRpcServer:
    """QMT RPC服务端"""

    def __init__(self):
        """初始化"""
        # 创建事件引擎
        self.event_engine = EventEngine()

        # 创建主引擎
        self.main_engine = MainEngine(self.event_engine)

        # 添加QMT网关
        self.main_engine.add_gateway(QmtGateway)

        # 添加RPC服务（传入类，不是实例）
        self.main_engine.add_app(RpcServiceApp)

        print("=" * 60)
        print("VeighNa RPC服务端 - QMT版本")
        print("=" * 60)

    def start(self):
        """启动服务"""
        # 获取RPC引擎并启动服务
        self.rpc_engine = self.main_engine.get_engine("RpcService")
        self.rpc_engine.start(
            rep_address=RPC_SETTING["req_address"],
            pub_address=RPC_SETTING["sub_address"]
        )

        print("\nRPC服务已启动：")
        print(f"  请求地址: {RPC_SETTING['req_address']}")
        print(f"  订阅地址: {RPC_SETTING['sub_address']}")

        print("\n网络配置提示：")
        print("  1. 本地测试：使用 127.0.0.1 即可")
        print("  2. 局域网：使用实际IP地址，如 192.168.1.100")
        print("  3. 外网访问：需要端口映射和防火墙配置")

        print("\nQMT连接配置：")
        print(f"  账号: {QMT_SETTING['交易账号']}")
        print(f"  路径: {QMT_SETTING['mini路径']}")

        print("\n" + "=" * 60)
        print("请在VeighNa Trader界面中配置QMT连接信息")
        print("或等待RPC客户端连接后远程配置")
        print("=" * 60)

        # 保持运行
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n正在停止服务...")
            self.stop()

    def stop(self):
        """停止服务"""
        self.rpc_engine.stop()
        self.main_engine.close()
        self.event_engine.stop()
        print("RPC服务已停止")


def main():
    """主函数"""
    server = QmtRpcServer()
    server.start()


if __name__ == "__main__":
    main()
