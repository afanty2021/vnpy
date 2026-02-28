"""测试统一日志配置"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
from pathlib import Path

from vnpy_china_config.logging_config import (
    setup_logging,
    get_logger,
    LoggerMixin,
    ExceptionHandler,
    log_function_call,
)


def test_setup_logging():
    """测试日志配置"""
    import logging
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        setup_logging(
            level=logging.DEBUG,
            log_file=str(log_file),
            console_enabled=False,
        )

        logger = get_logger("test_module")
        logger.debug("这是一条DEBUG日志")
        logger.info("这是一条INFO日志")
        logger.warning("这是一条WARNING日志")
        logger.error("这是一条ERROR日志")

        # 关闭所有handlers以释放文件锁
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)

        assert log_file.exists()
        log_content = log_file.read_text(encoding="utf-8")
        assert "DEBUG日志" in log_content
        assert "INFO日志" in log_content
        assert "WARNING日志" in log_content
        assert "ERROR日志" in log_content


def test_logger_mixin():
    """测试LoggerMixin"""

    class TestService(LoggerMixin):
        def test_log(self):
            self.logger.info("LoggerMixin测试")

    service = TestService()
    service.test_log()


def test_exception_handler():
    """测试异常处理器"""
    logger = get_logger("test_exception")
    handler = ExceptionHandler(logger)

    try:
        1 / 0
    except ZeroDivisionError as e:
        result = handler.handle_and_return(e, context="测试除零", default_return="fallback")
        assert result == "fallback"


def test_log_function_call():
    """测试函数调用日志装饰器"""

    @log_function_call()
    def add(a, b):
        return a + b

    result = add(1, 2)
    assert result == 3


def test_get_logger():
    """测试get_logger函数"""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")

    assert logger1.name == "module1"
    assert logger2.name == "module2"


def test_get_logger_for_module():
    """测试get_logger_for_module函数"""
    from vnpy_china_config.logging_config import get_logger_for_module

    logger = get_logger_for_module("vnpy_china_data")
    assert logger.name == "vnpy_china_data"


if __name__ == "__main__":
    test_setup_logging()
    test_logger_mixin()
    test_exception_handler()
    test_log_function_call()
    test_get_logger()
    test_get_logger_for_module()
    print("所有日志配置测试通过!")
