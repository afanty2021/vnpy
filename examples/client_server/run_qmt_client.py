# -*- coding:utf-8 -*-
"""
VeighNa RPC客户端 - Mac版本

运行在Mac上，负责：
1. 连接到Windows端的RPC服务
2. 在Mac上进行策略开发和回测
3. 通过RPC发送交易请求到Windows端执行

适用场景：
- Mac用户进行量化交易
- 远程策略管理
- 分布式交易系统

环境要求：
- macOS (任意版本)
- VeighNa框架
- 网络连接到Windows服务器
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.rpc import RpcClient
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp
from vnpy_datamanager import DataManagerApp

# RPC连接配置
RPC_SETTING = {
    "req_address": "tcp://192.168.1.100:2014",  # Windows服务器IP
    "sub_address": "tcp://192.168.1.100:4102",  # Windows服务器IP
}


class QmtRpcClient:
    """QMT RPC客户端"""

    def __init__(self):
        """初始化"""
        self.rpc_client = None

    def connect(self):
        """连接到RPC服务端"""
        print("=" * 60)
        print("VeighNa RPC客户端 - 连接QMT服务端")
        print("=" * 60)

        # 创建RPC客户端
        self.rpc_client = RpcClient()

        print("\n正在连接到Windows RPC服务端...")
        print(f"  请求地址: {RPC_SETTING['req_address']}")
        print(f"  订阅地址: {RPC_SETTING['sub_address']}")

        # 连接服务器
        try:
            self.rpc_client.connect(
                req_address=RPC_SETTING["req_address"],
                sub_address=RPC_SETTING["sub_address"]
            )
            print("✓ RPC连接成功！")
            return True
        except Exception as e:
            print(f"✗ RPC连接失败: {e}")
            print("\n请检查：")
            print("  1. Windows端RPC服务是否已启动")
            print("  2. IP地址是否正确")
            print("  3. 网络连接是否正常")
            print("  4. 防火墙是否开放端口")
            return False

    def test_connection(self):
        """测试连接"""
        print("\n" + "=" * 60)
        print("测试RPC连接功能")
        print("=" * 60)

        try:
            # 查询账户信息
            account = self.rpc_client.get_account()
            print(f"\n账户信息：")
            print(f"  账户ID: {account.accountid}")
            print(f"  余额: {account.balance}")
            print(f"  可用: {account.available}")

            # 查询持仓
            positions = self.rpc_client.get_positions()
            print(f"\n持仓数量: {len(positions)}")

            # 查询委托
            orders = self.rpc_client.get_orders()
            print(f"委托数量: {len(orders)}")

            # 查询成交
            trades = self.rpc_client.get_trades()
            print(f"成交数量: {len(trades)}")

            print("\n✓ RPC功能测试通过！")
            return True

        except Exception as e:
            print(f"\n✗ RPC功能测试失败: {e}")
            return False

    def send_order_test(self):
        """发送测试委托（谨慎使用）"""
        print("\n" + "=" * 60)
        print("发送测试委托")
        print("=" * 60)

        # 警告提示
        print("\n⚠️  警告：这将发送真实委托到QMT！")
        print("请确认：")
        print("  1. QMT已登录")
        print("  2. 使用的是模拟账户")
        print("  3. 委托参数正确")

        choice = input("\n是否继续？(yes/no): ")
        if choice.lower() != "yes":
            print("已取消")
            return

        try:
            # 发送测试委托（示例）
            order_id = self.rpc_client.send_order(
                symbol="000001",
                exchange="SZSE",
                direction="LONG",
                type="LIMIT",
                volume=100,
                price=10.0,
                reference="TEST_001"
            )
            print(f"\n✓ 委托已发送，委托号: {order_id}")

        except Exception as e:
            print(f"\n✗ 委托发送失败: {e}")

    def disconnect(self):
        """断开连接"""
        if self.rpc_client:
            self.rpc_client.close()
            print("RPC连接已关闭")


def start_gui_with_rpc():
    """启动带RPC的GUI界面（Mac）"""
    qapp = create_qapp()

    # 创建事件引擎
    event_engine = EventEngine()

    # 创建主引擎
    main_engine = MainEngine(event_engine)

    # 添加应用模块（策略、回测等在Mac上运行）
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)
    main_engine.add_app(DataManagerApp)

    # 连接RPC
    rpc_client = RpcClient()
    try:
        rpc_client.connect(
            req_address=RPC_SETTING["req_address"],
            sub_address=RPC_SETTING["sub_address"]
        )
        print("✓ 已连接到Windows QMT服务端")
    except Exception as e:
        print(f"✗ RPC连接失败: {e}")
        print("\n系统将在无接口模式下运行")

    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    # 显示提示信息
    print("\n" + "=" * 60)
    print("VeighNa Trader - Mac版本")
    print("=" * 60)
    print("  策略开发: Mac本地运行")
    print("  交易执行: 通过RPC连接到Windows QMT")
    print("=" * 60)

    qapp.exec()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VeighNa RPC客户端 - Mac版本")
    parser.add_argument("--mode", choices=["test", "gui"], default="test",
                       help="运行模式: test(测试连接) 或 gui(启动界面)")

    args = parser.parse_args()

    if args.mode == "test":
        # 测试模式
        client = QmtRpcClient()
        if client.connect():
            client.test_connection()
            # client.send_order_test()  # 取消注释以测试委托
            input("\n按回车键退出...")
            client.disconnect()
    else:
        # GUI模式
        start_gui_with_rpc()


if __name__ == "__main__":
    main()
