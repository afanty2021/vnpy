# -*- coding:utf-8 -*-
"""
vnpy_qmt 修复部署脚本

自动将修复后的 vnpy_qmt 文件部署到 conda 环境中。
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


def deploy_file(source_file, target_file, backup_dir):
    """部署单个文件"""
    # 备份原始文件
    if target_file.exists():
        backup_file = backup_dir / f"{target_file.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(target_file, backup_file)
        print(f"   备份: {target_file.name} -> {backup_file.name}")

    # 复制修复文件
    shutil.copy2(source_file, target_file)
    print(f"   部署: {source_file.name} -> {target_file}")

    return True


def deploy_fix():
    """部署 vnpy_qmt 修复"""

    print("=" * 60)
    print("vnpy_qmt 修复部署")
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
    if not target_dir.exists():
        print(f"ERROR: vnpy_qmt 未安装在环境中: {target_dir}")
        return False

    print(f"   目标路径: {target_dir}")

    # 源文件路径（patches 目录）
    script_dir = Path(__file__).parent

    # 备份目录
    backup_dir = script_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    # 部署的文件列表
    files_to_deploy = [
        ("md.py", "历史数据修复"),
        ("td.py", "账户数据修复（balance 使用现金而非总资产）"),
    ]

    print("\n[2/5] 部署修复文件...")
    success_count = 0

    for filename, description in files_to_deploy:
        print(f"\n   部署 {filename} ({description}):")
        source_file = script_dir / filename
        target_file = target_dir / filename

        if not source_file.exists():
            print(f"      ERROR: 源文件不存在: {source_file}")
            continue

        try:
            if deploy_file(source_file, target_file, backup_dir):
                success_count += 1
        except Exception as e:
            print(f"      ERROR: 部署失败: {e}")

    print(f"\n   成功部署: {success_count}/{len(files_to_deploy)} 个文件")

    # 验证文件
    print("\n[3/5] 验证部署...")
    for filename, _ in files_to_deploy:
        target_file = target_dir / filename
        if target_file.exists():
            size = target_file.stat().st_size
            mtime = datetime.fromtimestamp(target_file.stat().st_mtime)
            print(f"   {filename}: {size} 字节, {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"   {filename}: 文件不存在")

    print("\n[4/5] 修复说明:")
    print("   md.py - 历史数据下载修复")
    print("   td.py - 账户数据修复:")
    print("     * balance 字段现在使用 asset.cash（可用现金）")
    print("     * 而不是 asset.total_asset（总资产）")
    print("     * 这样 '可用' 字段将正确显示可用现金")

    print("\n[5/5] 测试验证:")
    print("   请在 Windows 服务端重启 QMT 服务，")
    print("   然后在 Mac 客户端验证账户数据显示。")

    print("\n" + "=" * 60)
    print("部署完成！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = deploy_fix()
    sys.exit(0 if success else 1)
