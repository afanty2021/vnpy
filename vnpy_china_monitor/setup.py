"""
A股监控告警模块安装配置
"""

from pathlib import Path
from setuptools import setup, find_packages

# 读取README
this_directory = Path(__file__).parent
long_description = (this_directory / "CLAUDE.md").read_text(encoding="utf-8") if (this_directory / "CLAUDE.md").exists() else ""

# 读取requirements
requirements = []
if (this_directory / "requirements.txt").exists():
    requirements = (this_directory / "requirements.txt").read_text(encoding="utf-8").strip().split("\n")
    requirements = [r for r in requirements if r and not r.startswith("#")]

setup(
    name="vnpy_china_monitor",
    version="0.1.0",
    author="Berton",
    author_email="berton@example.com",
    description="VeighNa A股交易系统监控告警模块",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/berton/vnpy_china_monitor",
    packages=find_packages(exclude=["tests", "tests.*", "*.tests", "*.tests.*", "web.frontend", "web.frontend.*"]),
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
    install_requires=requirements,
    extras_require={
        "web": [
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.23.0",
            "websockets>=11.0",
            "pydantic>=2.0.0",
            "pydantic-settings>=2.0.0",
            "python-multipart>=0.0.6",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "aiofiles>=23.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "httpx>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vnpy-china-monitor-web=vnpy_china_monitor.run_web:main",
        ],
    },
)
