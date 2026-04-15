"""
日志工具函数
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Optional, Callable, Any, TypeVar, Union
from ..exceptions import ConfigurationError

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


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """记录DEBUG级别日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """记录INFO级别日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """记录WARNING级别日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """记录ERROR级别日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """记录CRITICAL级别日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """内部日志记录方法"""
        if kwargs:
            # 构建结构化消息
            structured_message = f"{message}"
            for key, value in kwargs.items():
                if key != "exc_info":
                    structured_message += f" | {key}={value}"
            
            if "exc_info" in kwargs and kwargs["exc_info"]:
                self.logger.log(level, structured_message, exc_info=True)
            else:
                self.logger.log(level, structured_message)
        else:
            self.logger.log(level, message)


def log_api_call(func: Callable[..., Any]) -> Callable[..., Any]:
    """记录API调用的装饰器"""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(func.__module__)
        
        # 提取请求信息
        request = None
        for arg in args:
            if hasattr(arg, 'method') and hasattr(arg, 'path'):
                request = arg
                break
        
        if request:
            logger.info(f"API调用: {request.method} {request.path}")
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 记录响应信息
            if hasattr(result, 'status_code'):
                logger.info(f"API响应: {result.status_code}, 耗时: {execution_time:.3f}秒")
            else:
                logger.info(f"API完成, 耗时: {execution_time:.3f}秒")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"API错误: {str(e)}, 耗时: {execution_time:.3f}秒", exc_info=True)
            raise
    
    return wrapper


def log_database_query(func: Callable[..., Any]) -> Callable[..., Any]:
    """记录数据库查询的装饰器"""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(func.__module__)
        
        # 提取查询信息
        query_info = None
        for arg in args:
            if isinstance(arg, str) and ("SELECT" in arg.upper() or "INSERT" in arg.upper() or 
                                         "UPDATE" in arg.upper() or "DELETE" in arg.upper()):
                query_info = arg[:100] + "..." if len(arg) > 100 else arg
                break
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if query_info:
                logger.debug(f"数据库查询: {query_info}, 耗时: {execution_time:.3f}秒")
            else:
                logger.debug(f"数据库操作完成, 耗时: {execution_time:.3f}秒")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"数据库错误: {str(e)}, 耗时: {execution_time:.3f}秒", exc_info=True)
            raise
    
    return wrapper


def log_external_service_call(service_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """记录外部服务调用的装饰器工厂"""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            
            logger.info(f"调用外部服务: {service_name}")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"外部服务调用成功: {service_name}, 耗时: {execution_time:.3f}秒")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"外部服务调用失败: {service_name}, 错误: {str(e)}, 耗时: {execution_time:.3f}秒", exc_info=True)
                raise
        
        return wrapper
    return decorator