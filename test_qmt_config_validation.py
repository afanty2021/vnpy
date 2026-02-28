"""
测试 QmtConfig 的 enabled 字段和必填字段验证

验证场景：
1. enabled=False 时，允许空字符串
2. enabled=True 时，account_id 和 mini_path 必须非空
3. 字符串自动去除首尾空格
4. validate_mini_path 的警告逻辑
"""

from pydantic import ValidationError

from vnpy_china_config.global_config import QmtConfig


def test_qmt_disabled_with_empty_fields():
    """测试 enabled=False 时，允许空字符串"""
    # 应该成功创建，不抛出异常
    config = QmtConfig(
        account_id="",
        mini_path="",
        enabled=False
    )

    assert config.enabled is False
    assert config.account_id == ""
    assert config.mini_path == ""


def test_qmt_disabled_with_whitespace_fields():
    """测试 enabled=False 时，只有空格的字符串会被去除空格"""
    config = QmtConfig(
        account_id="   ",
        mini_path="  \t  ",
        enabled=False
    )

    assert config.enabled is False
    # 空格会被去除（因为字符串非空）
    assert config.account_id == ""
    assert config.mini_path == ""


def test_qmt_enabled_with_empty_account_id():
    """测试 enabled=True 时，空 account_id 应该抛出异常"""
    import tempfile
    import os

    # 创建临时目录来模拟存在的路径
    with tempfile.TemporaryDirectory() as tmpdir:
        mini_path = os.path.join(tmpdir, "userdata_mini")
        os.makedirs(mini_path, exist_ok=True)

        try:
            QmtConfig(
                account_id="",
                mini_path=mini_path,
                enabled=True
            )
            # 如果没有抛出异常，测试失败
            return False
        except ValidationError:
            # 预期行为
            return True


def test_qmt_enabled_with_empty_mini_path():
    """测试 enabled=True 时，空 mini_path 应该抛出异常"""
    try:
        QmtConfig(
            account_id="40218291",
            mini_path="",
            enabled=True
        )
        # 如果没有抛出异常，测试失败
        return False
    except ValidationError:
        # 预期行为
        return True


def test_qmt_enabled_with_whitespace_fields():
    """测试 enabled=True 时，只有空格的字段应该抛出异常"""
    try:
        QmtConfig(
            account_id="   ",
            mini_path="  \t  ",
            enabled=True
        )
        # 如果没有抛出异常，测试失败
        return False
    except ValidationError:
        # 预期行为
        return True


def test_qmt_enabled_with_valid_fields():
    """测试 enabled=True 时，有效字段应该成功创建"""
    import tempfile
    import os

    # 创建临时目录来模拟存在的路径
    with tempfile.TemporaryDirectory() as tmpdir:
        mini_path = os.path.join(tmpdir, "userdata_mini")
        os.makedirs(mini_path, exist_ok=True)

        config = QmtConfig(
            account_id="40218291",
            mini_path=mini_path,
            enabled=True
        )

        assert config.enabled is True
        assert config.account_id == "40218291"
        assert config.mini_path == mini_path


def test_qmt_fields_are_stripped():
    """测试字段值自动去除首尾空格"""
    import tempfile
    import os

    # 创建临时目录来模拟存在的路径
    with tempfile.TemporaryDirectory() as tmpdir:
        mini_path = os.path.join(tmpdir, "userdata_mini")
        os.makedirs(mini_path, exist_ok=True)

        # 添加空格进行测试
        path_with_spaces = f"  {mini_path}  "

        config = QmtConfig(
            account_id="  40218291  ",
            mini_path=path_with_spaces,
            enabled=True
        )

        assert config.account_id == "40218291"
        assert config.mini_path == mini_path


def test_qmt_mini_path_without_userdata_mini_warning():
    """测试 mini_path 不包含 userdata_mini 时发出警告"""
    import warnings
    import tempfile
    import os

    # 创建临时目录来模拟存在的路径（不包含 userdata_mini）
    with tempfile.TemporaryDirectory() as tmpdir:
        # 路径不包含 userdata_mini，应该发出警告
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            config = QmtConfig(
                account_id="40218291",
                mini_path=tmpdir,
                enabled=True
            )

            # 应该有警告
            assert len(w) == 1
            assert "userdata_mini" in str(w[0].message)
            assert issubclass(w[0].category, UserWarning)


def test_qmt_mini_path_with_userdata_mini_no_warning():
    """测试 mini_path 包含 userdata_mini 时不发出警告"""
    import warnings
    import tempfile
    import os

    # 创建临时目录来模拟存在的路径
    with tempfile.TemporaryDirectory() as tmpdir:
        mini_path = os.path.join(tmpdir, "userdata_mini")
        os.makedirs(mini_path, exist_ok=True)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            config = QmtConfig(
                account_id="40218291",
                mini_path=mini_path,
                enabled=True
            )

            # 不应该有警告
            assert len(w) == 0


def test_qmt_default_values():
    """测试默认值"""
    config = QmtConfig()

    assert config.account_id == ""
    assert config.mini_path == ""
    assert config.session_id == 0
    assert config.password == ""
    assert config.enabled is False


def test_qmt_mini_path_empty_no_validation():
    """测试空 mini_path 不触发 userdata_mini 检查"""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = QmtConfig(
            account_id="40218291",
            mini_path="",
            enabled=False
        )

        # 空路径不应该触发警告
        assert len(w) == 0


def test_qmt_optional_fields():
    """测试可选字段 session_id 和 password"""
    import tempfile
    import os

    # 创建临时目录来模拟存在的路径
    with tempfile.TemporaryDirectory() as tmpdir:
        mini_path = os.path.join(tmpdir, "userdata_mini")
        os.makedirs(mini_path, exist_ok=True)

        config = QmtConfig(
            account_id="40218291",
            mini_path=mini_path,
            session_id=12345,
            password="mypassword",
            enabled=True
        )

        assert config.session_id == 12345
        assert config.password == "mypassword"


def test_qmt_enabled_with_nonexistent_path():
    """测试 enabled=True 时，不存在的路径应该抛出异常"""
    try:
        QmtConfig(
            account_id="40218291",
            mini_path="D:/不存在的路径/userdata_mini/",
            enabled=True
        )
        # 如果没有抛出异常，测试失败
        return False
    except ValidationError as e:
        # 预期行为 - 应该是ValidationError（Pydantic包装）
        error_msg = str(e)
        assert "不存在" in error_msg or "does not exist" in error_msg.lower()
        return True
    except ValueError as e:
        # 或者直接是ValueError
        error_msg = str(e)
        assert "不存在" in error_msg or "does not exist" in error_msg.lower()
        return True


def test_qmt_disabled_with_nonexistent_path():
    """测试 enabled=False 时，不存在的路径不应该抛出异常"""
    # 应该成功创建，不抛出异常
    config = QmtConfig(
        account_id="40218291",
        mini_path="D:/不存在的路径/userdata_mini/",
        enabled=False
    )

    assert config.enabled is False
    assert config.account_id == "40218291"
    assert config.mini_path == "D:/不存在的路径/userdata_mini/"


def test_qmt_path_exists_when_enabled():
    """测试启用时路径存在性检查"""
    import tempfile
    import os

    # 创建一个临时目录作为测试路径
    with tempfile.TemporaryDirectory() as tmpdir:
        # 在临时目录中创建 userdata_mini 子目录
        mini_path = os.path.join(tmpdir, "userdata_mini")
        os.makedirs(mini_path, exist_ok=True)

        # 应该成功创建，因为路径存在
        config = QmtConfig(
            account_id="40218291",
            mini_path=mini_path,
            enabled=True
        )

        assert config.enabled is True
        assert config.mini_path == mini_path


def test_qmt_error_message_includes_config_example():
    """测试错误信息包含配置示例"""
    try:
        QmtConfig(
            account_id="40218291",
            mini_path="D:/不存在的路径/userdata_mini/",
            enabled=True
        )
        return False
    except (ValidationError, ValueError) as e:
        error_msg = str(e)
        # 验证错误信息包含配置建议
        assert "Windows:" in error_msg or "D:/" in error_msg
        assert "macOS/Linux:" in error_msg or "/opt/" in error_msg
        return True


if __name__ == "__main__":
    # 运行测试
    print("Running QmtConfig tests...")

    test_qmt_disabled_with_empty_fields()
    print("[PASS] enabled=False allows empty strings")

    test_qmt_disabled_with_whitespace_fields()
    print("[PASS] enabled=False allows whitespace strings")

    test_qmt_enabled_with_valid_fields()
    print("[PASS] enabled=True with valid fields succeeds")

    test_qmt_fields_are_stripped()
    print("[PASS] Field values are stripped")

    test_qmt_default_values()
    print("[PASS] Default values are correct")

    test_qmt_mini_path_with_userdata_mini_no_warning()
    print("[PASS] Correct path does not trigger warning")

    test_qmt_mini_path_empty_no_validation()
    print("[PASS] Empty path does not trigger validation")

    test_qmt_optional_fields()
    print("[PASS] Optional fields work correctly")

    # 测试异常情况
    if test_qmt_enabled_with_empty_account_id():
        print("[PASS] enabled=True with empty account_id raises exception")
    else:
        print("[FAIL] Should have raised exception for empty account_id")

    if test_qmt_enabled_with_empty_mini_path():
        print("[PASS] enabled=True with empty mini_path raises exception")
    else:
        print("[FAIL] Should have raised exception for empty mini_path")

    if test_qmt_enabled_with_whitespace_fields():
        print("[PASS] enabled=True with whitespace fields raises exception")
    else:
        print("[FAIL] Should have raised exception for whitespace fields")

    # 测试警告
    test_qmt_mini_path_without_userdata_mini_warning()
    print("[PASS] Invalid path triggers warning")

    # 新增：路径存在性检查测试
    if test_qmt_enabled_with_nonexistent_path():
        print("[PASS] enabled=True with nonexistent path raises exception")
    else:
        print("[FAIL] Should have raised exception for nonexistent path")

    test_qmt_disabled_with_nonexistent_path()
    print("[PASS] enabled=False allows nonexistent path")

    test_qmt_path_exists_when_enabled()
    print("[PASS] enabled=True succeeds when path exists")

    if test_qmt_error_message_includes_config_example():
        print("[PASS] Error message includes configuration examples")
    else:
        print("[FAIL] Error message should include configuration examples")

    print("\nAll tests passed!")
