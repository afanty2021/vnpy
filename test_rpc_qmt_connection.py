#!/usr/bin/env python3
"""
RPC-QMT连接测试脚本

测试macOS客户端是否能连接到Windows QMT RPC服务端
"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy.rpc import RpcClient


class TestRpcClient(RpcClient):
    """测试用的RPC客户端，实现callback方法"""

    def __init__(self):
        super().__init__()
        self.received_data = []

    def callback(self, topic: str, data) -> None:
        """接收服务器推送的数据"""
        self.received_data.append((topic, data))
        print(f"  [推送] {topic}: {type(data).__name__}")


def test_rpc_connection(req_address: str, sub_address: str, timeout: int = 10) -> dict:
    """
    测试RPC连接

    Parameters
    ----------
    req_address : str
        RPC请求地址
    sub_address : str
        RPC订阅地址
    timeout : int
        连接超时时间（秒）

    Returns
    -------
    dict
        测试结果
    """
    result = {
        "connected": False,
        "error": None,
        "latency": None,
        "server_info": None
    }

    print(f"\n{'='*60}")
    print(f"RPC-QMT 连接测试")
    print(f"{'='*60}")
    print(f"请求地址: {req_address}")
    print(f"订阅地址: {sub_address}")
    print(f"超时时间: {timeout}秒")

    # 创建RPC客户端
    client = TestRpcClient()

    # 记录连接开始时间
    start_time = time.time()

    try:
        # 尝试连接
        print(f"\n正在连接RPC...")
        client.start(req_address, sub_address)

        # 等待连接建立
        time.sleep(0.5)  # 给连接一点时间建立

        latency = (time.time() - start_time) * 1000
        result["connected"] = True
        result["latency"] = f"{latency:.2f}ms"
        print(f"✓ 连接成功！延迟: {result['latency']}")

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ 连接失败: {result['error']}")

    finally:
        # 清理
        try:
            client.stop()
        except:
            pass

    return result


def test_rpc_api_calls(req_address: str, sub_address: str) -> dict:
    """
    测试RPC API调用

    Parameters
    ----------
    req_address : str
        RPC请求地址
    sub_address : str
        RPC订阅地址

    Returns
    -------
    dict
        API测试结果
    """
    print(f"\n{'='*60}")
    print(f"RPC API 调用测试")
    print(f"{'='*60}")

    result = {
        "queries": {},
        "errors": []
    }

    client = TestRpcClient()

    try:
        print(f"\n正在连接...")
        client.start(req_address, sub_address)
        print(f"✓ 已连接")

        # 测试API调用 - 通过RpcClient的__getattr__机制
        tests = [
            ("查询合约", "query_contracts"),
            ("查询账户", "query_accounts"),
            ("查询持仓", "query_positions"),
        ]

        for name, method in tests:
            try:
                print(f"\n{name}...")
                # 通过RPC调用远程方法
                data = getattr(client, method)(timeout=5000)
                if data:
                    if isinstance(data, list):
                        print(f"  ✓ 返回 {len(data)} 条数据")
                        result["queries"][name] = len(data)
                    else:
                        print(f"  ✓ 返回数据: {type(data).__name__}")
                        result["queries"][name] = 1
                else:
                    print(f"  ⚠ 无数据返回")
                    result["queries"][name] = 0
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                result["errors"].append(f"{name}: {e}")

    except Exception as e:
        print(f"\n✗ API测试失败: {e}")
        result["errors"].append(f"连接失败: {e}")

    finally:
        try:
            client.stop()
        except:
            pass

    return result


def main():
    """主函数"""
    print("\n" + "="*60)
    print(" RPC-QMT 连接测试工具")
    print("="*60)

    # 默认配置 - 根据实际环境修改
    default_configs = [
        {
            "name": "局域网（Parallels默认）",
            "req": "tcp://192.168.2.168:2014",
            "sub": "tcp://192.168.2.168:4102",
        },
        {
            "name": "本地（端口转发）",
            "req": "tcp://127.0.0.1:2014",
            "sub": "tcp://127.0.0.1:4102",
        },
    ]

    print("\n可用配置：")
    for i, config in enumerate(default_configs, 1):
        print(f"  {i}. {config['name']}")
        print(f"     REQ: {config['req']}")
        print(f"     SUB: {config['sub']}")

    print(f"\n  0. 自定义配置")

    choice = input("\n请选择配置编号（默认1）: ").strip() or "1"

    if choice == "0":
        req = input("请输入请求地址（tcp://IP:PORT）: ").strip()
        sub = input("请输入订阅地址（tcp://IP:PORT）: ").strip()
    else:
        idx = int(choice) - 1
        if 0 <= idx < len(default_configs):
            config = default_configs[idx]
            req, sub = config["req"], config["sub"]
            print(f"\n使用配置: {config['name']}")
        else:
            print("无效选择")
            return

    # 执行连接测试
    result = test_rpc_connection(req, sub)

    if result["connected"]:
        # 执行API测试
        api_result = test_rpc_api_calls(req, sub)

        # 输出总结
        print(f"\n{'='*60}")
        print(f"测试总结")
        print(f"{'='*60}")
        print(f"连接状态: ✓ 成功")
        print(f"连接延迟: {result['latency']}")

        if api_result["queries"]:
            print(f"\nAPI调用:")
            for name, count in api_result["queries"].items():
                print(f"  {name}: {count} 条")

        if api_result["errors"]:
            print(f"\n警告:")
            for err in api_result["errors"]:
                print(f"  ⚠ {err}")

        print(f"\n✓ RPC连接测试通过！可以继续进行模型训练测试。")
    else:
        print(f"\n{'='*60}")
        print(f"测试总结")
        print(f"{'='*60}")
        print(f"连接状态: ✗ 失败")
        print(f"错误信息: {result['error']}")
        print(f"\n请检查：")
        print(f"  1. Windows服务端是否运行 run_qmt_server.py")
        print(f"  2. Windows防火墙是否开放端口")
        print(f"  3. 网络连通性（ping命令测试）")
        print(f"  4. RPC地址配置是否正确")


if __name__ == "__main__":
    main()
