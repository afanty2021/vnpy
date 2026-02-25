# -*- coding:utf-8 -*-
"""
简化版RPC连接测试
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.rpc import RpcClient

RPC_SETTING = {
    "req_address": "tcp://192.168.2.168:2014",
    "sub_address": "tcp://192.168.2.168:4102",
}


def test_connection():
    print("=" * 60)
    print("VeighNa RPC连接测试")
    print("=" * 60)

    rpc_client = RpcClient()

    try:
        print("正在连接...")
        rpc_client.start(
            req_address=RPC_SETTING["req_address"],
            sub_address=RPC_SETTING["sub_address"]
        )
        print("✓ RPC连接成功！")

        print("\n测试RPC功能...")

        # 查询所有账户
        accounts = rpc_client.get_all_accounts()
        print(f"  账户数量: {len(accounts)}")
        for account in accounts:
            print(f"    账户ID: {account.accountid}")
            print(f"    余额: {account.balance}")
            print(f"    可用: {account.available}")

        if not accounts:
            print("  警告: 没有找到账户")

        # 测试获取合约列表
        try:
            contracts = rpc_client.get_all_contracts()
            print(f"  合约数量: {len(contracts)}")
        except Exception as e:
            print(f"  获取合约失败: {e}")

        print("\n✓ RPC连接测试完成！")
        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        rpc_client.stop()
        print("\n连接已关闭")


if __name__ == "__main__":
    test_connection()
