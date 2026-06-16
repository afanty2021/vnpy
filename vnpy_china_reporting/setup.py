"""
A股报表生成模块安装配置
"""

from pathlib import Path
from setuptools import setup, find_packages

# 读取README
this_directory = Path(__file__).parent
readme = this_directory / "CLAUDE.md"
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="vnpy_china_reporting",
    version="0.1.0",
    author="Berton",
    author_email="berton@example.com",
    description="VeighNa A股报表生成模块",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/berton/vnpy_china_reporting",
    packages=find_packages(exclude=["tests", "tests.*", "*.tests", "*.tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    # 核心依赖：报表生成与分析所需，pip install 本包即装齐
    install_requires=[
        "numpy>=1.24.0",
        "openpyxl>=3.1.0",
        "vnpy",
        "pymysql>=1.1.0",
        "dbutils>=3.1.0",
    ],
    extras_require={
        # PDF导出：pip install vnpy_china_reporting[pdf]
        "pdf": ["reportlab>=4.0.0"],
        # 图表生成：pip install vnpy_china_reporting[chart]
        "chart": ["matplotlib>=3.7.0"],
        # 全部可选导出：pip install vnpy_china_reporting[all]
        "all": [
            "reportlab>=4.0.0",
            "matplotlib>=3.7.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
)
