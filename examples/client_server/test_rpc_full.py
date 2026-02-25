# -*- coding:utf-8 -*-
"""
完整的RPC交易测试
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


def test_full():
    print("=" * 60)
    print("完整RPC交易测试")
    print("=" * 60)

    rpc_client = RpcClient()

    try:
        print("连接RPC...")
        rpc_client.start(
            req_address=RPC_SETTING["req_address"],
            sub_address=RPC_SETTING["sub_address"]
        )
        print("✓ 连接成功！")

        # 1. 获取账户
        print("\n1. 查询账户:")
        accounts = rpc_client.get_all_accounts()
        print(f"   账户数量: {len(accounts)}")
        for a in accounts:
            print(f"   - {a.accountid}: 可用 {a.available}")

        # 2. 获取持仓
        print("\n2. 查询持仓:")
        positions = rpc_client.get_all_positions()
        print(f"   持仓数量: {len(positions)}")

        # 3. 获取合约
        print("\n3. 查询合约:")
        contracts = rpc_client.get_all_contracts()
        print(f"   合约数量: {len(contracts)}")
        # 显示前5个
        for c in contracts[:5]:
            print(f"   - {c.symbol} {c.name}")

        # 4. 订阅行情
        print("\n4. 订阅行情:")
        # 订阅000001平安银行
        rpc_client.subscribe("000001.SZSE", "QMT")
        print("   已订阅 000001.SZSE")

        print("\n✓ 所有测试完成！")

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        rpc_client.stop()


if __name__ == "__main__":
    test_full()
