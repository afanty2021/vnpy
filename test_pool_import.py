"""
简单测试连接池导入
"""
import sys

# 直接测试导入
try:
    from dbutils.pooled_db import PooledDB
    print("✓ DBUtils.PooledDB 导入成功")
    print(f"✓ PooledDB 类型: {type(PooledDB)}")
except ImportError as e:
    print(f"✗ DBUtils 导入失败: {e}")
    sys.exit(1)

# 检查导入路径
import dbutils
print(f"✓ dbutils 模块路径: {dbutils.__file__}")

# 测试连接池配置常量
from vnpy_china_data.database import DEFAULT_POOL_SIZE, DEFAULT_MAX_OVERFLOW
print(f"✓ DEFAULT_POOL_SIZE = {DEFAULT_POOL_SIZE}")
print(f"✓ DEFAULT_MAX_OVERFLOW = {DEFAULT_MAX_OVERFLOW}")

print("\n所有导入测试通过！")
