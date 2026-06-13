#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试配置文件加载情况
"""

import re
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def mask_secret(secret: str) -> str:
    """脱敏显示密钥：仅保留首末字符与长度，不输出明文

    用于避免在测试输出/CI 日志/共享屏幕中泄露数据库密码等敏感信息。
    """
    if not secret:
        return "{空}"
    if len(secret) <= 2:
        return "*" * len(secret)
    return f"{secret[0]}{'*' * (len(secret) - 2)}{secret[-1]} (长度{len(secret)})"


def mask_password_line(line: str) -> str:
    """对 'mysql_password: xxx' 这类配置行脱敏，仅掩码冒号后的值部分"""
    _quotes = "\"'"  # YAML 值可能用引号包裹，strip 时去除

    def _mask_value(m):
        value = m.group(2).strip().strip(_quotes)
        return f"{m.group(1)}{mask_secret(value)}"

    return re.sub(r'(:\s*)(.+)', _mask_value, line, count=1)


def test_config_loading():
    """测试配置加载"""
    print("=" * 70)
    print("配置文件加载测试")
    print("=" * 70)

    # 1. 测试ConfigManager
    print("\n1. 测试ConfigManager加载...")
    try:
        from vnpy_china_config import ConfigManager
        config_manager = ConfigManager()

        # 加载全局配置
        global_config = config_manager.load_global_config()

        print(f"  数据库配置:")
        print(f"    主机: {global_config.database.mysql_host}")
        print(f"    端口: {global_config.database.mysql_port}")
        print(f"    用户: {global_config.database.mysql_user}")
        print(f"    密码: {mask_secret(global_config.database.mysql_password)}")
        print(f"    数据库: {global_config.database.mysql_database}")

        # 检查密码是否为默认值
        if global_config.database.mysql_password in ['', 'password', 'root']:
            print(f"    [WARNING] 使用了不安全的密码！")
        else:
            print(f"    [OK] 密码安全")

    except Exception as e:
        print(f"  [ERROR] 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

    # 2. 测试数据库连接
    print("\n2. 测试数据库连接...")
    try:
        from vnpy.trader.database import get_database
        import os

        # 检查环境变量
        mysql_pwd = os.getenv('MYSQL_PASSWORD')
        print(f"  环境变量 MYSQL_PASSWORD: {'{已设置}' if mysql_pwd else '{未设置}'}")

        # 尝试获取数据库
        db = get_database()
        print(f"  数据库类型: {type(db).__name__}")

    except Exception as e:
        print(f"  [ERROR] 数据库连接失败: {e}")

    # 3. 检查配置文件路径
    print("\n3. 检查配置文件路径...")
    config_paths = [
        project_root / ".vntrader_china" / "config" / "global_development.yaml",
        project_root / ".vntrader_china" / "config" / "global_production.yaml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            print(f"  [存在] {config_path}")
            # 读取文件内容查看密码
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'mysql_password' in content:
                    lines = [line for line in content.split('\n') if 'mysql_password' in line]
                    for line in lines:
                        print(f"    {mask_password_line(line.strip())}")
        else:
            print(f"  [不存在] {config_path}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    test_config_loading()
