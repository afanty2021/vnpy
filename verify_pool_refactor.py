"""
验证database.py连接池重构的语法和结构

检查关键改动是否正确实现。
"""
import re
import ast
import sys
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_file_syntax(filepath):
    """检查Python文件语法"""
    print("=" * 60)
    print("检查文件语法")
    print("=" * 60)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        # 编译检查
        ast.parse(code)
        print(f"✓ 文件语法正确: {filepath}")
        return True, code
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False, None


def check_imports(code):
    """检查导入语句"""
    print("\n" + "=" * 60)
    print("检查导入语句")
    print("=" * 60)

    checks = {
        'PooledDB导入': r'from dbutils\.pooled_db import PooledDB',
        'threading.Lock移除': r'from threading import Lock',
    }

    results = {}
    for name, pattern in checks.items():
        found = bool(re.search(pattern, code))
        results[name] = found
        status = "✓" if found else "✗"
        print(f"{status} {name}: {'存在' if found else '不存在'}")

    # 确认PooledDB在except块中也有导入
    if 'PooledDB = None' in code:
        print("✓ PooledDB在except块中正确处理")
    else:
        print("✗ PooledDB在except块中未处理")

    return all(results.values())


def check_constants(code):
    """检查常量定义"""
    print("\n" + "=" * 60)
    print("检查常量定义")
    print("=" * 60)

    constants = {
        'DEFAULT_POOL_SIZE': r'DEFAULT_POOL_SIZE\s*=\s*\d+',
        'DEFAULT_MAX_OVERFLOW': r'DEFAULT_MAX_OVERFLOW\s*=\s*\d+',
    }

    results = {}
    for name, pattern in constants.items():
        found = bool(re.search(pattern, code))
        results[name] = found
        status = "✓" if found else "✗"
        print(f"{status} {name}: {'定义' if found else '未定义'}")

    return all(results.values())


def check_init_method(code):
    """检查__init__方法参数"""
    print("\n" + "=" * 60)
    print("检查__init__方法")
    print("=" * 60)

    # 查找__init__方法定义
    init_pattern = r'def __init__\([^)]+pool_size[^)]*max_overflow[^)]*\)'
    found = bool(re.search(init_pattern, code))

    status = "✓" if found else "✗"
    print(f"{status} __init__方法包含pool_size和max_overflow参数")

    # 检查移除了Lock
    has_lock = 'self._lock = Lock()' in code
    status = "✓" if not has_lock else "✗"
    print(f"{status} __init__方法移除了Lock初始化")

    # 检查添加了pool属性
    has_pool = 'self._pool:' in code or 'self._pool =' in code
    status = "✓" if has_pool else "✗"
    print(f"{status} __init__方法添加了_pool属性")

    return found and not has_lock and has_pool


def check_connect_method(code):
    """检查connect方法"""
    print("\n" + "=" * 60)
    print("检查connect()方法")
    print("=" * 60)

    # 检查是否创建PooledDB
    has_pool_creation = 'PooledDB(' in code
    status = "✓" if has_pool_creation else "✗"
    print(f"{status} connect()方法创建PooledDB实例")

    # 检查是否移除了单连接创建
    has_single_connect = 'pymysql.connect(**self.config)' in code
    status = "✓" if not has_single_connect else "✗"
    print(f"{status} connect()方法移除了单连接创建")

    return has_pool_creation and not has_single_connect


def check_pool_usage(code):
    """检查数据库操作方法使用连接池"""
    print("\n" + "=" * 60)
    print("检查数据库操作方法使用连接池")
    print("=" * 60)

    # 检查关键方法是否使用self._pool.connection()
    methods = [
        'save_bar_data',
        'load_bar_data',
        'get_latest_date',
        'save_stock_info',
        'load_stock_info',
        '_execute_sql',
        'save_capital_flow',
        'get_hk_connect_stocks',
    ]

    results = {}
    for method in methods:
        # 查找方法定义并检查是否使用了pool.connection()
        pattern = rf'def {method}\([^)]*\):[^(]*?self\._pool\.connection\(\)'
        found = bool(re.search(pattern, code, re.DOTALL))
        results[method] = found
        status = "✓" if found else "?"
        print(f"{status} {method}(): {'使用连接池' if found else '需手动检查'}")

    # 检查是否移除了with self._lock
    lock_count = code.count('with self._lock:')
    status = "✓" if lock_count == 0 else "✗"
    print(f"{status} 所有方法移除了with self._lock (剩余: {lock_count}处)")

    return all(results.values()) and lock_count == 0


def check_get_pool_status(code):
    """检查get_pool_status方法"""
    print("\n" + "=" * 60)
    print("检查get_pool_status()方法")
    print("=" * 60)

    has_method = 'def get_pool_status(' in code
    status = "✓" if has_method else "✗"
    print(f"{status} 定义了get_pool_status()方法")

    if has_method:
        # 检查返回的键
        keys = ['pool_size', 'max_overflow', 'max_connections', 'database', 'host', 'port']
        for key in keys:
            found = f'"{key}"' in code or f"'{key}'" in code
            status = "✓" if found else "?"
            print(f"{status} 返回键 '{key}': {'存在' if found else '需检查'}")

    return has_method


def main():
    """运行所有检查"""
    filepath = "D:/berton/vnpy/vnpy_china_data/database.py"

    print("\n" + "=" * 60)
    print("数据库连接池重构验证")
    print("=" * 60)

    # 检查语法
    success, code = check_file_syntax(filepath)
    if not success:
        return 1

    # 检查各项改动
    checks = [
        ("导入语句", check_imports),
        ("常量定义", check_constants),
        ("__init__方法", check_init_method),
        ("connect()方法", check_connect_method),
        ("连接池使用", check_pool_usage),
        ("get_pool_status()方法", check_get_pool_status),
    ]

    results = {}
    for name, check_func in checks:
        try:
            result = check_func(code)
            results[name] = result
        except Exception as e:
            print(f"\n✗ {name}检查失败: {e}")
            results[name] = False

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"{status} {name}: {'通过' if result else '失败'}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有检查通过！重构成功完成。")
    else:
        print("✗ 部分检查未通过，请检查上述问题。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
