"""
RPC连接诊断工具

帮助诊断 Mac 客户端与 Windows QMT 服务端的 RPC 连接问题。
"""

import socket
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入配置管理
from vnpy_china_config import ConfigManager


def check_config():
    """检查配置文件"""
    print("=" * 60)
    print("1. 检查配置文件")
    print("=" * 60)

    # 重置单例以清除可能的缓存
    ConfigManager.reset_instance()
    config_manager = ConfigManager()

    # 显示配置文件路径
    config_path = config_manager.config_path
    print(f"配置文件目录: {config_path}")

    # 尝试加载配置（强制重新加载）
    try:
        config = config_manager.load_config(force_reload=True)
        print(f"\n✓ 配置加载成功")
        print(f"  QMT启用: {'是' if config.qmt.enabled else '否'}")
        print(f"  RPC模式: {'启用' if config.qmt.use_rpc else '禁用'}")
        print(f"  请求地址: {config.rpc.rep_address}")
        print(f"  订阅地址: {config.rpc.pub_address}")
        return config
    except Exception as e:
        print(f"\n✗ 配置加载失败: {e}")
        print(f"  将使用默认配置: localhost")
        return None


def check_env_vars():
    """检查环境变量"""
    print("\n" + "=" * 60)
    print("2. 检查环境变量")
    print("=" * 60)

    import os

    req_addr = os.getenv("QMT_RPC_REQ_ADDRESS", "")
    sub_addr = os.getenv("QMT_RPC_SUB_ADDRESS", "")

    if req_addr or sub_addr:
        print("✓ 检测到环境变量:")
        if req_addr:
            print(f"  QMT_RPC_REQ_ADDRESS: {req_addr}")
        if sub_addr:
            print(f"  QMT_RPC_SUB_ADDRESS: {sub_addr}")
        return {"req": req_addr, "sub": sub_addr}
    else:
        print("○ 未设置环境变量")
        return None


def extract_host_address(address: str) -> tuple:
    """从地址中提取主机和端口"""
    # tcp://192.168.2.168:2014 -> (192.168.2.168, 2014)
    try:
        # 移除协议前缀
        if "://" in address:
            address = address.split("://")[1]

        # 分割主机和端口
        if ":" in address:
            host, port = address.rsplit(":", 1)
            return host, int(port)
        else:
            return address, None
    except Exception as e:
        print(f"✗ 解析地址失败: {e}")
        return None, None


def check_network_connectivity(host: str, port: int, timeout: int = 3) -> bool:
    """检查网络连通性"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"  网络检查失败: {e}")
        return False


def check_rpc_server(host: str, port: int):
    """检查 RPC 服务端"""
    print(f"\n正在检查 {host}:{port} ...")

    # 1. 端口扫描
    if check_network_connectivity(host, port):
        print(f"✓ 端口 {port} 可达")
        return True
    else:
        print(f"✗ 端口 {port} 不可达")
        return False


def diagnose():
    """执行完整诊断"""
    print("\n" + "=" * 60)
    print("VeighNa RPC 连接诊断工具")
    print("=" * 60)
    print(f"当前时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 检查配置
    config = check_config()

    # 2. 检查环境变量
    env_vars = check_env_vars()

    # 3. 确定使用的地址
    print("\n" + "=" * 60)
    print("3. 确定使用的连接地址")
    print("=" * 60)

    # 优先级：环境变量 > 配置文件 > 默认值
    if env_vars and env_vars["req"]:
        req_address = env_vars["req"]
        sub_address = env_vars["sub"]
        print("使用环境变量配置:")
    elif config:
        req_address = config.rpc.rep_address
        sub_address = config.rpc.pub_address
        print("使用配置文件配置:")
    else:
        req_address = "tcp://127.0.0.1:2014"
        sub_address = "tcp://127.0.0.1:4102"
        print("使用默认配置:")

    print(f"  请求地址: {req_address}")
    print(f"  订阅地址: {sub_address}")

    # 4. 解析主机和端口
    req_host, req_port = extract_host_address(req_address)
    sub_host, sub_port = extract_host_address(sub_address)

    if not req_host:
        print("\n✗ 无法解析主机地址，请检查配置格式")
        return

    print(f"\n解析结果:")
    print(f"  请求主机: {req_host}, 端口: {req_port}")
    print(f"  订阅主机: {sub_host}, 端口: {sub_port}")

    # 5. 检查网络连通性
    print("\n" + "=" * 60)
    print("4. 网络连通性检查")
    print("=" * 60)

    # 检查请求端口
    req_ok = check_rpc_server(req_host, req_port)

    # 检查订阅端口
    if req_port != sub_port:
        sub_ok = check_rpc_server(sub_host, sub_port)
    else:
        sub_ok = req_ok

    # 6. 诊断结果
    print("\n" + "=" * 60)
    print("5. 诊断结果")
    print("=" * 60)

    if req_ok and sub_ok:
        print("✓ 网络连接正常！")
        print("\n可能的问题:")
        print("  1. Windows 服务端未运行 run_qmt_server.py")
        print("  2. QMT 客户端未登录")
        print("  3. QMT RPC 服务未完全启动")
        print("\n建议:")
        print("  1. 确认 Windows 上运行: python run_qmt_server.py")
        print("  2. 检查 QMT 客户端是否已登录")
        print("  3. 等待 RPC 服务完全启动（约 10 秒）")
    else:
        print("✗ 网络连接失败！")
        print("\n可能的问题:")
        print("  1. IP 地址配置错误")
        print("  2. Windows 防火墙阻止了连接")
        print("  3. 网络不通")
        print("  4. Windows 服务端未启动")
        print("\n建议:")
        print("  1. 检查 IP 地址是否正确")
        print("  2. 在 Windows 上开放防火墙端口:")
        print(f"     netsh advfirewall firewall add rule name=\"VeighNa RPC\" dir=in action=allow protocol=TCP localport={req_port},{sub_port}")
        print("  3. 确认 Windows 服务端运行: python run_qmt_server.py")

    # 7. 配置建议
    print("\n" + "=" * 60)
    print("6. 配置建议")
    print("=" * 60)

    print("\n如果需要修改配置，请选择以下方式之一:")

    print("\n方式1: 创建/修改配置文件")
    print("  文件路径: .vntrader_china/config/config.yaml (Mac/Linux客户端)")
    print("  或 qmt_gateway.yaml (Windows服务端)")
    print("  配置内容:")
    print(f"    rpc.rep_address: \"{req_address}\"")
    print(f"    rpc.pub_address: \"{sub_address}\"")

    print("\n方式2: 设置环境变量")
    print(f"  export QMT_RPC_REQ_ADDRESS=\"{req_address}\"")
    print(f"  export QMT_RPC_SUB_ADDRESS=\"{sub_address}\"")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    diagnose()
