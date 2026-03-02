#!/usr/bin/env python3
"""
配置加载测试脚本
测试 ConfigManager 的 load_config() 和 load_qmt_gateway_config() 方法
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy_china_config import ConfigManager


def test_load_config():
    """测试客户端配置加载"""
    print("=" * 60)
    print("测试 1: load_config() - 客户端配置")
    print("=" * 60)

    try:
        config_dir = project_root / ".vntrader_china/config"
        config_manager = ConfigManager()
        config_manager.set_config_path(config_dir)

        config = config_manager.load_config(force_reload=True)

        print("✓ 配置文件加载成功")
        print(f"  RPC 请求地址: {config.rpc.rep_address}")
        print(f"  RPC 订阅地址: {config.rpc.pub_address}")
        print(f"  日志级别: {config.logging.level}")
        print(f"  数据库启用: {config.database.enabled}")
        print(f"  最大持仓比例: {config.risk.max_position_ratio}")
        return True

    except FileNotFoundError as e:
        print(f"✗ 配置文件不存在: {e}")
        print(f"  请确保 {config_dir}/config.yaml 存在")
        return False
    except Exception as e:
        print(f"✗ 加载失败: {e}")
        return False


def test_load_qmt_gateway_config():
    """测试 QMT 网关配置加载"""
    print("\n" + "=" * 60)
    print("测试 2: load_qmt_gateway_config() - QMT 网关配置")
    print("=" * 60)

    try:
        config_dir = project_root / ".vntrader_china/config"
        config_manager = ConfigManager()
        config_manager.set_config_path(config_dir)

        config = config_manager.load_qmt_gateway_config(force_reload=True)

        print("✓ 配置文件加载成功")
        print(f"  QMT 账号: {config.qmt.account_id or '(未配置)'}")
        print(f"  Mini路径: {config.qmt.mini_path or '(未配置)'}")
        print(f"  会话ID: {config.qmt.session_id}")
        return True

    except FileNotFoundError as e:
        print(f"✗ 配置文件不存在: {e}")
        print(f"  请确保 {config_dir}/qmt_gateway.yaml 存在")
        return False
    except Exception as e:
        print(f"✗ 加载失败: {e}")
        return False


def test_fallback_to_global():
    """测试回退到全局配置"""
    print("\n" + "=" * 60)
    print("测试 3: 回退机制 - 使用全局配置")
    print("=" * 60)

    try:
        # 使用不存在的配置目录
        config_dir = project_root / "non_existent_config"
        config_manager = ConfigManager()
        config_manager.set_config_path(config_dir)

        # 应该回退到 load_global_config()
        config = config_manager.load_config(force_reload=True)

        print("✓ 回退到全局配置成功")
        return True

    except Exception as e:
        print(f"✗ 回退失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n配置加载测试\n")

    results = {
        "客户端配置加载": test_load_config(),
        "QMT网关配置加载": test_load_qmt_gateway_config(),
        "回退机制": test_fallback_to_global(),
    }

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status}  {name}")

    all_passed = all(results.values())
    print("\n" + ("✓ 所有测试通过" if all_passed else "✗ 部分测试失败"))
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
