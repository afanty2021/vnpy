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
    # 优先：通过 vnpy_qmt 的安装位置反推
    try:
        import vnpy_qmt
        vnpy_qmt_path = Path(vnpy_qmt.__file__).parent
        # vnpy_qmt 路径 = env_root/Lib/site-packages/vnpy_qmt
        # 所以 env_root = vnpy_qmt_path.parent.parent (Windows)
        # 或者 = vnpy_qmt_path.parent (Unix)
        site_packages = vnpy_qmt_path.parent
        if site_packages.name == "site-packages":
            lib_dir = site_packages.parent
            if lib_dir.name == "Lib":
                return lib_dir.parent  # Windows: env_root
            else:
                return lib_dir  # Unix: env_root
    except ImportError:
        pass

    # 其次：检查 CONDA_PREFIX 环境变量
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix:
        return Path(conda_prefix)

    # 尝试常见的 conda 环境路径
    env_name = os.environ.get('CONDA_DEFAULT_ENV', 'Quant-3.11')

    # Windows Scoop 安装路径（大小写兼容）
    for scoop_base in ["D:/scoop/apps/miniconda/current",
                        "D:/Scoop/apps/miniconda3/current"]:
        scoop_path = Path(f"{scoop_base}/envs/{env_name}")
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
        ("md.py", "历史数据查询（添加 query_history 方法）"),
        ("qmt_gateway.py", "网关主入口（添加 query_history 委托 + 港股通交易所支持）"),
        ("utils.py", "工具函数（添加港股通交易所映射 SHHK/SZHK/SEHK）"),
        ("td.py", "交易模块（balance 使用 asset.cash 而非 asset.total_asset）"),
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
    print("   md.py - 添加 query_history 方法，通过 xtquant 下载历史 K 线数据")
    print("   qmt_gateway.py - 添加 query_history 委托方法 + 港股通交易所支持")
    print("   utils.py - 添加港股通交易所映射（SHHK/SZHK/SEHK）")
    print("   td.py - balance 字段使用 asset.cash（可用现金）")

    print("\n[5/5] 测试验证:")
    print("   1. 重启 QMT RPC 服务端")
    print("   2. 验证 query_history 补丁:")
    print("      python -c \"from vnpy_qmt.md import MD; print('query_history' in dir(MD))\"")
    print("   3. 验证网关委托:")
    print("      python -c \"from vnpy_qmt import QmtGateway; print('query_history' in dir(QmtGateway))\"")
    print("   4. 界面测试：下载 600660.SSE 日线数据")

    print("\n" + "=" * 60)
    print("部署完成！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = deploy_fix()
    sys.exit(0 if success else 1)
