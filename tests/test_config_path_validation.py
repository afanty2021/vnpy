"""测试配置路径验证"""

import tempfile
from pathlib import Path
import sys

# 确保可以导入vnpy_china_config
sys.path.insert(0, str(Path(__file__).parent.parent))

from vnpy_china_config.utils import (
    is_valid_project_directory,
    find_project_root,
    validate_yaml_file,
    list_config_files,
)


def test_is_valid_project_directory():
    """测试项目目录验证"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # 空目录不是项目目录
        assert not is_valid_project_directory(project_dir), "空目录应该是无效的项目目录"

        # 添加setup.py后变成项目目录
        (project_dir / "setup.py").touch()
        assert is_valid_project_directory(project_dir), "有setup.py的目录应该是有效的项目目录"

        # 添加CLAUDE.md也是项目目录
        project_dir2 = Path(tmpdir) / "project2"
        project_dir2.mkdir()
        (project_dir2 / "CLAUDE.md").touch()
        assert is_valid_project_directory(project_dir2), "有CLAUDE.md的目录应该是有效的项目目录"

        # 不存在的目录返回False
        nonexistent = Path(tmpdir) / "nonexistent"
        assert not is_valid_project_directory(nonexistent), "不存在的目录应该返回False"

        print("[PASS] test_is_valid_project_directory")


def test_find_project_root():
    """测试查找项目根目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "myproject"
        root.mkdir()

        # 创建项目标识
        (root / "setup.py").touch()

        # 创建子目录
        subdir = root / "subdir" / "nested"
        subdir.mkdir(parents=True)

        # 从子目录查找应该能找到根目录
        found = find_project_root(subdir)
        assert found == root, f"期望找到 {root}, 但找到了 {found}"

        # 从根目录查找应该返回根目录
        found = find_project_root(root)
        assert found == root, f"期望找到 {root}, 但找到了 {found}"

        # 从不存在的目录查找应该返回None
        found = find_project_root(Path(tmpdir) / "nonexistent")
        assert found is None, f"期望返回None, 但找到了 {found}"

        print("[PASS] test_find_project_root")


def test_validate_yaml_file():
    """测试YAML文件验证"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 有效的YAML文件
        valid_yaml = Path(tmpdir) / "valid.yaml"
        valid_yaml.write_text("key: value\nlist:\n  - item1\n  - item2\n", encoding="utf-8")
        is_valid, error = validate_yaml_file(valid_yaml)
        assert is_valid, f"有效的YAML文件应该验证通过: {error}"
        assert error == ""

        # 不存在的文件
        missing = Path(tmpdir) / "missing.yaml"
        is_valid, error = validate_yaml_file(missing)
        assert not is_valid, "不存在的文件应该验证失败"
        assert "文件不存在" in error, f"错误信息应该包含'文件不存在', 实际: {error}"

        # 不是文件的路径
        not_file = Path(tmpdir)
        is_valid, error = validate_yaml_file(not_file)
        assert not is_valid, "目录应该验证失败"
        assert "不是文件" in error, f"错误信息应该包含'不是文件', 实际: {error}"

        print("[PASS] test_validate_yaml_file")


def test_list_config_files():
    """测试列出配置文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()

        # 创建配置文件
        (config_dir / "global_development.yaml").touch()
        (config_dir / "global_production.yaml").touch()
        (config_dir / "data_development.yaml").touch()
        (config_dir / "readme.txt").touch()  # 非YAML文件

        files = list_config_files(config_dir)
        assert len(files) == 3, f"期望3个YAML文件, 实际: {len(files)}"
        assert all(f.suffix == ".yaml" for f in files), "所有文件应该是.yaml文件"

        # 空目录
        empty_dir = Path(tmpdir) / "empty"
        empty_dir.mkdir()
        files = list_config_files(empty_dir)
        assert len(files) == 0, "空目录应该返回空列表"

        print("[PASS] test_list_config_files")


def test_config_manager_path_detection():
    """测试ConfigManager路径检测"""
    from vnpy_china_config.loader import ConfigManager

    # 重置单例
    ConfigManager.reset_instance()

    # 获取实例
    manager = ConfigManager()

    # 验证项目根目录被正确检测
    info = manager.get_config_info()
    assert "project_root" in info
    assert "environment" in info
    assert "config_path" in info

    print(f"  配置信息: {info}")
    print("[PASS] test_config_manager_path_detection")


def test_config_manager_project_root():
    """测试ConfigManager项目根目录属性"""
    from vnpy_china_config.loader import ConfigManager

    # 重置单例
    ConfigManager.reset_instance()

    manager = ConfigManager()

    # 验证project_root属性
    assert manager.project_root is not None
    assert manager.project_root.exists()

    print(f"  项目根目录: {manager.project_root}")
    print("[PASS] test_config_manager_project_root")


def test_current_project_validation():
    """测试当前项目目录验证"""
    from vnpy_china_config.loader import ConfigManager

    # 重置单例
    ConfigManager.reset_instance()

    manager = ConfigManager()

    # 验证当前项目是有效的项目目录
    is_valid = manager._is_valid_project_directory(manager.project_root)
    assert is_valid, f"当前项目目录应该是有效的: {manager.project_root}"

    # 验证配置路径有配置文件
    has_files = manager._has_config_files(manager.config_path)
    print(f"  配置路径: {manager.config_path}")
    print(f"  有配置文件: {has_files}")
    print("[PASS] test_current_project_validation")


if __name__ == "__main__":
    print("=" * 60)
    print("配置路径验证测试")
    print("=" * 60)

    test_is_valid_project_directory()
    test_find_project_root()
    test_validate_yaml_file()
    test_list_config_files()
    test_config_manager_path_detection()
    test_config_manager_project_root()
    test_current_project_validation()

    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)
