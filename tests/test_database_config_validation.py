"""
测试 DatabaseConfig 的连接池验证和密码警告

验证场景：
1. pool_size <= 0 时抛出 ValueError
2. pool_size > 100 时抛出 ValueError
3. max_overflow <= 0 时抛出 ValueError
4. max_overflow > 100 时抛出 ValueError
5. 空密码时发出 UserWarning
6. 默认密码 "password" 时发出 UserWarning
7. 正常值不抛出异常和警告
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import warnings
from pydantic import ValidationError

from vnpy_china_config.global_config import DatabaseConfig


def test_pool_size_zero_raises_error():
    """测试 pool_size = 0 时抛出 ValueError"""
    try:
        DatabaseConfig(pool_size=0)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        assert "连接池大小必须大于0" in error_msg or "pool_size" in error_msg.lower()
        return True


def test_pool_size_negative_raises_error():
    """测试 pool_size < 0 时抛出 ValueError"""
    try:
        DatabaseConfig(pool_size=-5)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        assert "连接池大小必须大于0" in error_msg or "pool_size" in error_msg.lower()
        return True


def test_pool_size_over_100_raises_error():
    """测试 pool_size > 100 时抛出 ValueError"""
    try:
        DatabaseConfig(pool_size=101)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        assert "连接池大小不应超过100" in error_msg or "pool_size" in error_msg.lower()
        return True


def test_pool_size_boundary_100_ok():
    """测试 pool_size = 100 时成功"""
    config = DatabaseConfig(pool_size=100)
    assert config.pool_size == 100
    return True


def test_max_overflow_zero_raises_error():
    """测试 max_overflow = 0 时抛出 ValueError"""
    try:
        DatabaseConfig(max_overflow=0)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        assert "连接池大小必须大于0" in error_msg or "max_overflow" in error_msg.lower()
        return True


def test_max_overflow_negative_raises_error():
    """测试 max_overflow < 0 时抛出 ValueError"""
    try:
        DatabaseConfig(max_overflow=-10)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        assert "连接池大小必须大于0" in error_msg or "max_overflow" in error_msg.lower()
        return True


def test_max_overflow_over_100_raises_error():
    """测试 max_overflow > 100 时抛出 ValueError"""
    try:
        DatabaseConfig(max_overflow=101)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        assert "连接池大小不应超过100" in error_msg or "max_overflow" in error_msg.lower()
        return True


def test_max_overflow_boundary_100_ok():
    """测试 max_overflow = 100 时成功"""
    config = DatabaseConfig(max_overflow=100)
    assert config.max_overflow == 100
    return True


def test_empty_password_warning():
    """测试空密码时发出 UserWarning"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = DatabaseConfig(mysql_password="")

        # 应该有警告
        assert len(w) == 1
        assert "空密码" in str(w[0].message) or "password" in str(w[0].message).lower()
        assert issubclass(w[0].category, UserWarning)

    return True


def test_default_password_warning():
    """测试默认密码 'password' 时发出 UserWarning"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = DatabaseConfig(mysql_password="password")

        # 应该有警告
        assert len(w) == 1
        assert "默认密码" in str(w[0].message) or "password" in str(w[0].message).lower()
        assert issubclass(w[0].category, UserWarning)

    return True


def test_strong_password_no_warning():
    """测试强密码时不发出警告"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = DatabaseConfig(mysql_password="MyStr0ng!Pass")

        # 不应该有警告
        assert len(w) == 0

    return True


def test_normal_values_no_error():
    """测试正常值不抛出异常"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = DatabaseConfig(
            pool_size=10,
            max_overflow=20,
            mysql_password="secure_password"
        )

        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.mysql_password == "secure_password"
        # 不应该有密码警告（因为不是空密码或默认密码）
        assert len(w) == 0

    return True


def test_default_values():
    """测试默认值"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = DatabaseConfig()

        assert config.pool_size == 5
        assert config.max_overflow == 10
        # 默认密码为空，应该有警告
        assert len(w) == 1
        assert "空密码" in str(w[0].message) or "password" in str(w[0].message).lower()

    return True


def test_both_pool_size_and_max_overflow_invalid():
    """测试 pool_size 和 max_overflow 都无效时"""
    try:
        DatabaseConfig(pool_size=0, max_overflow=-1)
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        # 应该包含两个错误信息
        assert "pool_size" in error_msg.lower() or "连接池" in error_msg
        return True


if __name__ == "__main__":
    print("Running DatabaseConfig validation tests...")

    # 测试 pool_size
    if test_pool_size_zero_raises_error():
        print("[PASS] pool_size = 0 raises ValueError")
    else:
        print("[FAIL] pool_size = 0 should raise ValueError")

    if test_pool_size_negative_raises_error():
        print("[PASS] pool_size < 0 raises ValueError")
    else:
        print("[FAIL] pool_size < 0 should raise ValueError")

    if test_pool_size_over_100_raises_error():
        print("[PASS] pool_size > 100 raises ValueError")
    else:
        print("[FAIL] pool_size > 100 should raise ValueError")

    if test_pool_size_boundary_100_ok():
        print("[PASS] pool_size = 100 is valid")
    else:
        print("[FAIL] pool_size = 100 should be valid")

    # 测试 max_overflow
    if test_max_overflow_zero_raises_error():
        print("[PASS] max_overflow = 0 raises ValueError")
    else:
        print("[FAIL] max_overflow = 0 should raise ValueError")

    if test_max_overflow_negative_raises_error():
        print("[PASS] max_overflow < 0 raises ValueError")
    else:
        print("[FAIL] max_overflow < 0 should raise ValueError")

    if test_max_overflow_over_100_raises_error():
        print("[PASS] max_overflow > 100 raises ValueError")
    else:
        print("[FAIL] max_overflow > 100 should raise ValueError")

    if test_max_overflow_boundary_100_ok():
        print("[PASS] max_overflow = 100 is valid")
    else:
        print("[FAIL] max_overflow = 100 should be valid")

    # 测试密码警告
    if test_empty_password_warning():
        print("[PASS] Empty password triggers UserWarning")
    else:
        print("[FAIL] Empty password should trigger UserWarning")

    if test_default_password_warning():
        print("[PASS] Default password 'password' triggers UserWarning")
    else:
        print("[FAIL] Default password 'password' should trigger UserWarning")

    if test_strong_password_no_warning():
        print("[PASS] Strong password does not trigger warning")
    else:
        print("[FAIL] Strong password should not trigger warning")

    # 测试正常值
    if test_normal_values_no_error():
        print("[PASS] Normal values work correctly")
    else:
        print("[FAIL] Normal values should work correctly")

    if test_default_values():
        print("[PASS] Default values are correct (with warning)")
    else:
        print("[FAIL] Default values test failed")

    if test_both_pool_size_and_max_overflow_invalid():
        print("[PASS] Both invalid values raise error")
    else:
        print("[FAIL] Both invalid values should raise error")

    print("\nAll DatabaseConfig validation tests passed!")
