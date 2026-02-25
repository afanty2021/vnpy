"""
测试RPC QMT适配器连接

验证RPC模式下的QMT数据访问功能。
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy_china_data.adapter import RpcQmtDataAdapter


def test_rpc_qmt_adapter():
    """测试RPC QMT适配器"""
    print("=" * 60)
    print("RPC QMT 适配器连接测试")
    print("=" * 60)

    # 创建RPC QMT适配器
    # 默认连接本地地址（适用于Parallels虚拟机或局域网）
    adapter = RpcQmtDataAdapter(
        req_address="tcp://127.0.0.1:2014",
        sub_address="tcp://127.0.0.1:4102"
    )

    print("\n配置信息:")
    print(f"  请求地址: {adapter.req_address}")
    print(f"  订阅地址: {adapter.sub_address}")

    print("\n正在连接RPC QMT服务...")

    # 连接RPC服务
    if not adapter.connect():
        print("\n连接失败！")
        print("\n可能原因:")
        print("1. Windows QMT RPC服务未启动")
        print("2. 网络连接问题（请检查IP地址和端口）")
        print("3. 防火墙阻止了连接")
        print("\n建议:")
        print("1. 在Windows机器上运行: python examples/client_server/run_qmt_server.py")
        print("2. 检查Windows防火墙是否开放2014和4102端口")
        print("3. 如果是局域网，请使用Windows机器的实际IP地址")
        return

    print("连接成功！")

    # 测试订阅
    print("\n测试订阅功能...")
    test_symbols = ["000001", "000002"]
    if adapter.subscribe(test_symbols):
        print(f"成功订阅: {test_symbols}")
    else:
        print("订阅失败")

    # 显示统计信息
    print("\n统计信息:")
    print(f"  订阅数量: {adapter.subscribed_count}")

    # 保持连接一段时间以接收数据
    print("\n保持连接以接收行情数据...")
    print("（按Ctrl+C退出）")

    import time
    try:
        for i in range(10):
            time.sleep(1)
            print(f"\r运行时间: {i+1}秒 | Tick数: {adapter.tick_count}", end="")
    except KeyboardInterrupt:
        print("\n\n用户中断")

    # 断开连接
    print("\n\n正在断开连接...")
    adapter.disconnect()
    print("已断开连接")
    print("\n测试完成")


if __name__ == "__main__":
    test_rpc_qmt_adapter()
