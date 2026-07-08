#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VeighNa A股量化交易系统 — 一键部署脚本

功能：
  --install    安装依赖包 + 应用补丁 + 初始化数据库（默认）
  --verify     验证所有组件是否就绪
  --patch-only 仅应用补丁

使用方法：
  conda activate Quant-3.11
  python scripts/deploy.py              # 完整部署
  python scripts/deploy.py --verify     # 仅验证
  python scripts/deploy.py --patch-only # 仅打补丁
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
PATCHES_DIR = PROJECT_ROOT / "patches"
CONFIG_DIR = PROJECT_ROOT / ".vntrader_china" / "config"

# 补丁文件列表
PATCH_FILES = [
    ("md.py", "历史数据查询（query_history 方法）"),
    ("qmt_gateway.py", "网关委托 + 港股通交易所"),
    ("utils.py", "港股通交易所映射"),
    ("td.py", "账户 balance 字段修复"),
]

# 需要安装的额外依赖（pyproject.toml 之外的）
EXTRA_PACKAGES = [
    "vnpy_qmt",
    "vnpy_rpcservice",
    "vnpy_sqlite",
    "pymysql",
    "dbutils",
    "redis",
    "qdarkstyle",
    # Web 监控（vnpy_china_monitor.web）依赖：FastAPI + JWT + TestClient
    "fastapi",
    "python-jose[cryptography]",
    "httpx",
]


def run_cmd(cmd, check=True, capture=False):
    """执行命令"""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"  [FAIL] {result.stderr.strip()}")
            return False
        return result.stdout.strip()
    else:
        result = subprocess.run(cmd, shell=True)
        if check and result.returncode != 0:
            return False
        return True


def separator(title):
    """打印分隔线"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ── 步骤1：环境检查 ──────────────────────────────────────────────

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    print(f"  Python 版本: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 10:
        print("  [OK] Python 版本符合要求 (>=3.10)")
        return True
    else:
        print("  [FAIL] 需要 Python >= 3.10")
        return False


def check_conda_env():
    """检查 conda 环境"""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    print(f"  当前 conda 环境: {conda_env or '未检测到'}")
    if conda_env:
        print(f"  [OK] conda 环境已激活")
        return True
    else:
        print("  [WARN] 未检测到 conda 环境，确保在正确的 Python 环境中运行")
        return True


# ── 步骤2：安装依赖 ──────────────────────────────────────────────

def install_dependencies():
    """安装依赖包"""
    separator("步骤1：安装依赖")

    # 安装项目本身（编辑模式）
    print("\n  安装项目（编辑模式）...")
    if not run_cmd(f"pip install -e \"{PROJECT_ROOT}\"", capture=False):
        print("  [WARN] pip install -e . 失败，尝试继续...")

    # 安装额外依赖
    print("\n  安装额外依赖包...")
    for pkg in EXTRA_PACKAGES:
        print(f"    安装 {pkg}...", end=" ")
        result = run_cmd(f"pip install {pkg}", capture=True)
        if result is not False:
            print("OK")
        else:
            print("FAIL（可能已安装）")

    print("\n  [OK] 依赖安装完成")
    return True


# ── 步骤3：应用补丁 ──────────────────────────────────────────────

def find_site_packages():
    """查找 vnpy_qmt 安装路径"""
    try:
        import vnpy_qmt
        return Path(vnpy_qmt.__file__).parent
    except ImportError:
        # 尝试从 sys.path 查找
        for p in sys.path:
            candidate = Path(p) / "vnpy_qmt"
            if candidate.exists():
                return candidate
    return None


def apply_patches():
    """应用补丁"""
    separator("步骤2：应用补丁")

    # 查找目标路径
    target_dir = find_site_packages()
    if not target_dir:
        print("  [FAIL] 找不到 vnpy_qmt 安装路径")
        print("  请确认已运行: pip install vnpy_qmt")
        return False

    print(f"  目标路径: {target_dir}")

    # 创建备份目录
    backup_dir = PATCHES_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)

    success = 0
    for filename, description in PATCH_FILES:
        source = PATCHES_DIR / filename
        target = target_dir / filename

        if not source.exists():
            print(f"  [WARN] 补丁文件不存在: {source}")
            continue

        # 备份
        if target.exists():
            backup_name = f"{filename}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(target, backup_dir / backup_name)

        # 复制
        import shutil
        shutil.copy2(source, target)
        print(f"  [OK] {filename} ({description})")
        success += 1

    print(f"\n  成功部署: {success}/{len(PATCH_FILES)} 个文件")
    return success == len(PATCH_FILES)


# ── 步骤4：初始化数据库 ──────────────────────────────────────────

def init_database():
    """初始化数据库表"""
    separator("步骤3：初始化数据库")

    init_script = PROJECT_ROOT / "init_database.py"
    if init_script.exists():
        print("  运行 init_database.py...")
        run_cmd(f"python \"{init_script}\"", capture=False)
    else:
        print("  [WARN] init_database.py 不存在，跳过数据库初始化")
        print("  请手动运行: python init_database.py")

    return True


# ── 验证 ──────────────────────────────────────────────────────────

def _load_mysql_config():
    """从本地 config.yaml 读取 MySQL 连接参数（config.yaml 未跟踪，避免硬编码凭据）。

    回退顺序：config.yaml 的 mysql_* 字段 → 环境变量 MYSQL_PASSWORD → 默认值。
    返回 (host, port, user, password, database)。
    """
    host, port, user, password, database = "localhost", 3306, "vnpy_dev", None, "vnpy_china"
    password = os.environ.get("MYSQL_PASSWORD") or password

    config_path = CONFIG_DIR / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            # mysql_* 字段可能在某个顶层段下（如 database:），扁平化搜索以兼容段名变化
            def _find(node, key):
                if isinstance(node, dict):
                    if key in node:
                        return node[key]
                    for v in node.values():
                        found = _find(v, key)
                        if found is not None:
                            return found
                return None
            host = _find(cfg, "mysql_host") or host
            port = _find(cfg, "mysql_port") or port
            user = _find(cfg, "mysql_user") or user
            password = _find(cfg, "mysql_password") or password
            database = _find(cfg, "mysql_database") or database
        except Exception as e:
            print(f"  [WARN] 读取 {config_path} 失败: {e}，回退环境变量/默认值")

    return host, port, user, password, database


def verify():
    """验证所有组件"""
    separator("验证部署")
    all_ok = True

    checks = [
        ("Python 版本", check_python_version),
        ("conda 环境", check_conda_env),
    ]

    # 检查核心包
    print("\n  核心包:")
    core_packages = ["vnpy", "vnpy_qmt", "vnpy_rpcservice", "vnpy_sqlite",
                     "xtquant", "pymysql", "redis", "PySide6", "qdarkstyle"]
    for pkg in core_packages:
        try:
            __import__(pkg)
            print(f"    [OK] {pkg}")
        except ImportError:
            print(f"    [FAIL] {pkg} 未安装")
            all_ok = False

    # 检查补丁
    print("\n  补丁:")
    try:
        from vnpy_qmt.md import MD
        if 'query_history' in dir(MD):
            print("    [OK] md.py — query_history 方法存在")
        else:
            print("    [FAIL] md.py — query_history 方法缺失，补丁未应用")
            all_ok = False
    except ImportError:
        print("    [FAIL] vnpy_qmt 无法导入")
        all_ok = False

    try:
        from vnpy_qmt import QmtGateway
        if 'query_history' in dir(QmtGateway):
            print("    [OK] qmt_gateway.py — query_history 委托方法存在")
        else:
            print("    [FAIL] qmt_gateway.py — query_history 委托缺失，补丁未应用")
            all_ok = False
    except ImportError:
        pass  # 已在上面报告

    # 检查 MySQL
    print("\n  MySQL:")
    try:
        import pymysql
        try:
            # 从本地 config.yaml 读连接参数（避免硬编码凭据），回退环境变量 MYSQL_PASSWORD
            mhost, mport, muser, mpass, mdb = _load_mysql_config()
            if not mpass:
                print("    [FAIL] 未配置 MySQL 密码（config.yaml 的 mysql_password 或环境变量 MYSQL_PASSWORD）")
                all_ok = False
            else:
                conn = pymysql.connect(
                    host=mhost, port=mport,
                    user=muser, password=mpass,
                    database=mdb, charset='utf8mb4'
                )
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES LIKE 'db_%'")
                tables = cursor.fetchall()
                conn.close()
                if tables:
                    print(f"    [OK] MySQL 连接成功（{mdb}），{len(tables)} 个数据表")
                else:
                    print("    [WARN] MySQL 连接成功但无数据表，请运行 init_database.py")
        except Exception as e:
            print(f"    [FAIL] MySQL 连接失败: {e}")
            all_ok = False
    except ImportError:
        print("    [FAIL] pymysql 未安装")
        all_ok = False

    # 检查 Redis
    print("\n  Redis:")
    try:
        import redis
        try:
            r = redis.Redis(host='localhost', port=6379)
            r.ping()
            print("    [OK] Redis 连接成功")
        except Exception as e:
            print(f"    [FAIL] Redis 连接失败: {e}")
            print("    启动 Redis: redis-server")
            all_ok = False
    except ImportError:
        print("    [FAIL] redis 包未安装")
        all_ok = False

    # 检查配置文件
    print("\n  配置文件:")
    config_files = [
        CONFIG_DIR / "global_development.yaml",
        CONFIG_DIR / "qmt_gateway.yaml",
    ]
    for cf in config_files:
        if cf.exists():
            print(f"    [OK] {cf.name}")
        else:
            print(f"    [WARN] {cf.name} 不存在")

    # 检查 RPC 端口
    print("\n  RPC 服务:")
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', 2014))
    sock.close()
    if result == 0:
        print("    [OK] 端口 2014 已监听（RPC 服务端运行中）")
    else:
        print("    [INFO] 端口 2014 未监听（RPC 服务端未启动，这不影响部署）")

    # 总结
    print(f"\n  {'=' * 50}")
    if all_ok:
        print("  [OK] 所有验证通过！系统已就绪。")
    else:
        print("  [FAIL] 部分检查未通过，请参考上述提示修复。")
    print(f"  {'=' * 50}")

    return all_ok


# ── 主入口 ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  VeighNa A股量化交易系统 — 部署工具")
    print("=" * 60)

    # 解析参数
    args = set(sys.argv[1:])
    if "--verify" in args:
        verify()
        return
    elif "--patch-only" in args:
        apply_patches()
        return

    # 完整部署
    check_python_version()
    check_conda_env()

    install_dependencies()
    apply_patches()
    init_database()

    print("\n")
    verify()

    print(f"\n{'=' * 60}")
    print("  部署完成！")
    print("  下一步：启动 MiniQMT → 运行 RPC 服务端 → 启动客户端")
    print("  详细步骤请参考 DEPLOYMENT_GUIDE.md")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
