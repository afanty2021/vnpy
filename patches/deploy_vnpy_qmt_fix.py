# -*- coding:utf-8 -*-
"""
vnpy_qmt 历史数据下载修复部署脚本

自动将修复后的 vnpy_qmt/md.py 部署到 conda 环境中。
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime


def find_conda_env():
    """查找 conda 环境路径"""
    # 检查是否在 conda 环境中运行
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix:
        return Path(conda_prefix)

    # 尝试常见的 conda 环境路径
    env_name = os.environ.get('CONDA_DEFAULT_ENV', 'Quant-3.11')

    # Windows Scoop 安装路径
    scoop_path = Path(f"D:/scoop/apps/miniconda/current/envs/{env_name}")
    if scoop_path.exists():
        return scoop_path

    # macOS/Linux Homebrew 安装路径
    homebrew_path = Path(f"/opt/homebrew/caskroom/miniconda/base/envs/{env_name}")
    if homebrew_path.exists():
        return homebrew_path

    # 标准路径
    for base in [
        Path.home() / "miniconda3" / "envs" / env_name,
        Path.home() / "anaconda3" / "envs" / env_name,
        Path("/usr/local/miniconda3") / "envs" / env_name,
    ]:
        if base.exists():
            return base

    return None


def deploy_fix():
    """部署 vnpy_qmt 修复"""

    print("=" * 60)
    print("vnpy_qmt 历史数据下载修复部署")
    print("=" * 60)

    # 查找 conda 环境
    print("\n[1/5] 查找 conda 环境...")
    conda_env = find_conda_env()
    if not conda_env:
        print("ERROR: 无法找到 conda 环境")
        print("请确保在 conda 环境中运行此脚本")
        return False

    print(f"   找到环境: {conda_env}")

    # 目标路径
    target_dir = conda_env / "Lib" / "site-packages" / "vnpy_qmt"
    target_file = target_dir / "md.py"

    if not target_dir.exists():
        print(f"ERROR: vnpy_qmt 未安装在环境中: {target_dir}")
        return False

    print(f"   目标路径: {target_file}")

    # 源文件路径
    script_dir = Path(__file__).parent
    source_file = script_dir / "vnpy_qmt" / "md.py"

    if not source_file.exists():
        print(f"ERROR: 修复文件不存在: {source_file}")
        print("请确保 patches/vnpy_qmt/md.py 存在")
        return False

    print(f"   源文件: {source_file}")

    # 备份原始文件
    print("\n[2/5] 备份原始文件...")
    backup_dir = script_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_file = backup_dir / f"md.py.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if target_file.exists():
        shutil.copy2(target_file, backup_file)
        print(f"   备份到: {backup_file}")
    else:
        print("   原始文件不存在，跳过备份")

    # 复制修复文件
    print("\n[3/5] 部署修复文件...")
    try:
        shutil.copy2(source_file, target_file)
        print(f"   已复制: {source_file} -> {target_file}")
    except Exception as e:
        print(f"ERROR: 复制失败: {e}")
        return False

    # 验证文件
    print("\n[4/5] 验证修复...")
    if target_file.exists():
        size = target_file.stat().st_size
        print(f"   文件大小: {size} 字节")
        print(f"   修改时间: {datetime.fromtimestamp(target_file.stat().st_mtime)}")
    else:
        print("ERROR: 目标文件不存在")
        return False

    print("\n[5/5] 测试验证...")
    print("   请运行以下命令测试:")
    print("   cd examples/client_server")
    print("   python test_qmt_simple.py")

    print("\n" + "=" * 60)
    print("部署完成！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = deploy_fix()
    sys.exit(0 if success else 1)
