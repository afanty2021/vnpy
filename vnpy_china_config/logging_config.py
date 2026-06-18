"""
统一日志配置模块

为所有vnpy_china_*模块提供统一的日志配置。
"""

import logging
import sys
import functools
from pathlib import Path
from typing import Optional, Any, Callable, TypeVar, Union
from logging.handlers import RotatingFileHandler


# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_DETAILED = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_enabled: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    detailed_format: bool = False
) -> None:
    """
    配置根日志记录器

    Args:
        level: 日志级别，默认为 INFO
        log_file: 日志文件路径，如果为 None 则不写入文件
        console_enabled: 是否启用控制台输出，默认为 True
        max_bytes: 日志文件最大字节数，默认为 10MB
        backup_count: 保留的备份文件数量，默认为 5
        detailed_format: 是否使用详细格式（包含文件名和行号），默认为 False
    """
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 选择日志格式
    fmt = LOG_FORMAT_DETAILED if detailed_format else LOG_FORMAT
    formatter = logging.Formatter(fmt, datefmt=DATE_FORMAT)

    # 添加控制台处理器
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 添加文件处理器
    if log_file:
        log_path = Path(log_file)
        # 确保目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 防御：至少保留一个 handler，避免 console_enabled=False 且 log_file=None 时日志静默丢失
    if not root_logger.handlers:
        fallback = logging.StreamHandler(sys.stdout)
        fallback.setLevel(level)
        fallback.setFormatter(formatter)
        root_logger.addHandler(fallback)


def setup_logging_from_config(config: Any) -> None:
    """从 GlobalConfig 应用日志配置（统一入口）

    读取 config.logging 字段并调用 setup_logging，供 client/server 启动时一行接入。
    须在 EventEngine / MainEngine 创建前调用。

    Args:
        config: vnpy_china_config.GlobalConfig 实例（需含 logging 字段）
    """
    log_cfg = config.logging
    level = getattr(logging, log_cfg.level, logging.INFO)
    log_file = str(log_cfg.file_path) if log_cfg.file_enabled else None
    setup_logging(
        level=level,
        log_file=log_file,
        console_enabled=log_cfg.console_enabled,
        max_bytes=log_cfg.max_bytes,
        backup_count=log_cfg.backup_count,
        detailed_format=("%(filename)s" in log_cfg.format or "%(lineno)d" in log_cfg.format),
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(name)


def get_logger_for_module(module_name: str) -> logging.Logger:
    """
    获取指定模块的日志记录器

    Args:
        module_name: 模块名称

    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(module_name)


class LoggerMixin:
    """
    日志混入类

    提供 logger 属性，返回当前类所在模块的日志记录器
    """

    @property
    def logger(self) -> logging.Logger:
        """
        获取当前类所在模块的日志记录器

        Returns:
            logging.Logger 实例
        """
        return logging.getLogger(self.__class__.__module__)


class ExceptionHandler:
    """
    异常处理器

    提供统一的异常处理和日志记录功能
    """

    def __init__(self, logger: logging.Logger):
        """
        初始化异常处理器

        Args:
            logger: 日志记录器实例
        """
        self.logger = logger

    def handle(
        self,
        exception: BaseException,
        context: str = "",
        level: int = logging.ERROR,
        reraise: bool = True
    ) -> None:
        """
        处理异常并记录日志

        Args:
            exception: 异常对象
            context: 异常上下文信息
            level: 日志级别，默认为 ERROR
            reraise: 是否重新抛出异常，默认为 True
        """
        msg = f"{context}: {type(exception).__name__}: {str(exception)}" if context else f"{type(exception).__name__}: {str(exception)}"
        self.logger.log(level, msg, exc_info=True)

        if reraise:
            raise exception

    def handle_and_return(
        self,
        exception: BaseException,
        context: str = "",
        default_return: Any = None
    ) -> Any:
        """
        处理异常并返回默认值

        Args:
            exception: 异常对象
            context: 异常上下文信息
            default_return: 异常时返回的默认值

        Returns:
            default_return 或重新抛出异常
        """
        msg = f"{context}: {type(exception).__name__}: {str(exception)}" if context else f"{type(exception).__name__}: {str(exception)}"
        self.logger.error(msg, exc_info=True)
        return default_return


# 类型变量，用于装饰器的返回类型
F = TypeVar('F', bound=Callable[..., Any])


def log_function_call(logger: Optional[logging.Logger] = None) -> Callable[[F], F]:
    """
    函数调用日志装饰器

    记录函数的调用和返回，支持异常日志记录

    Args:
        logger: 日志记录器，如果为 None 则使用根日志记录器

    Returns:
        装饰器函数
    """
    def decorator(func: F) -> F:
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__
            # 记录函数调用
            logger.debug(f"调用函数: {func_name}, args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"函数返回: {func_name}, result={result}")
                return result
            except Exception as e:
                logger.exception(f"函数执行异常: {func_name}, exception={type(e).__name__}: {str(e)}")
                raise

        return wrapper  # type: ignore
    return decorator
