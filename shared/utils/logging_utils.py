"""
日志工具函数
"""

from __future__ import annotations

import logging
import sys
import time
from functools import wraps
from typing import Optional, Callable, Any, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


def setup_logging(
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename: Optional[str] = None
) -> None:
    """设置日志配置
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: 日志格式
        filename: 日志文件路径，如果为None则输出到控制台
    """
    # Windows 上强制 UTF-8 编码，解决 emoji 等 Unicode 字符输出问题
    if sys.platform == 'win32':
        stdout_reconfigure = getattr(sys.stdout, 'reconfigure', None)
        stderr_reconfigure = getattr(sys.stderr, 'reconfigure', None)
        if stdout_reconfigure:
            stdout_reconfigure(encoding='utf-8', errors='replace')
        if stderr_reconfigure:
            stderr_reconfigure(encoding='utf-8', errors='replace')
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers: list[logging.Handler] = []
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(format)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # 文件处理器（如果指定了文件名）
    if filename:
        file_handler = logging.FileHandler(filename, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # 强制重新配置
    )


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称，通常使用 __name__
        
    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name)


def log_execution_time(logger: Optional[logging.Logger] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """记录函数执行时间的装饰器
    
    Args:
        logger: 日志记录器，如果为None则使用默认记录器
        
    Example:
        @log_execution_time()
        def my_function():
            time.sleep(1)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = time.time()
            logger.debug(f"开始执行: {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(f"执行完成: {func.__name__}, 耗时: {execution_time:.3f}秒")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"执行失败: {func.__name__}, 耗时: {execution_time:.3f}秒, 错误: {str(e)}")
                raise
        
        return wrapper
    return decorator
