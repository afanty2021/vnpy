"""
Pytest配置文件
"""

import pytest
import asyncio
from unittest.mock import Mock, patch


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """模拟配置"""
    return {
        "rpc": {
            "rep_address": "tcp://127.0.0.1:2014",
            "pub_address": "tcp://127.0.0.1:4102"
        },
        "server": {
            "host": "127.0.0.1",
            "port": 8000
        },
        "jwt": {
            "secret_key": "test_secret_key",
            "algorithm": "HS256",
            "expire_minutes": 60
        },
        "users": [
            {
                "username": "admin",
                "password_hash": "hashed_password_here",
                "role": "admin"
            }
        ]
    }


@pytest.fixture
def temp_config_file(mock_config, tmp_path):
    """创建临时配置文件"""
    import yaml

    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)

    return config_file


# 测试标记
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
