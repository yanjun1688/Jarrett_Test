"""
统一的API日志记录模块

提供统一的日志格式和自动化的日志记录工具
"""

from __future__ import annotations

import logging
import functools
from typing import Any, Optional, TypeVar, Callable, Dict, Union, cast
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class RequestLogger:
    """请求日志记录器（上下文管理器）"""

    def __init__(self, func_name: str, request: Any = None) -> None:
        self.func_name: str = func_name
        self.request: Any = request
        self.start_time: Optional[datetime] = None
        self.request_id: str = f"req_{id(request)}" if request else f"func_{id(func_name)}"

        # 提取请求信息
        self.user_id: Optional[int] = request.user.id if request and request.user.is_authenticated else None
        self.username: str = request.user.username if request and request.user.is_authenticated else 'anonymous'

    def __enter__(self) -> RequestLogger:
        self.start_time = timezone.now()

        # 记录请求开始
        logger.info(f"[Request] {'=' * 60}")
        logger.info(f"[Request] 开始: {self.func_name}")
        logger.info(f"[Request] ID: {self.request_id}")
        logger.info(f"[Request] 用户: {self.username} (ID: {self.user_id})")

        if self.request:
            logger.info(f"[Request] 方法: {self.request.method}")
            if hasattr(self.request, 'path'):
                logger.info(f"[Request] 路径: {self.request.path}")

            # 记录查询参数
            if hasattr(self.request, 'query_params') and self.request.query_params:
                logger.debug(f"[Request] 查询参数: {dict(self.request.query_params)}")

            # 记录请求体（部分）
            if hasattr(self.request, 'data') and self.request.data:
                body_str = str(self.request.data)
                logger.debug(f"[Request] 请求体: {body_str[:500]}{'...' if len(body_str) > 500 else ''}")

        logger.info(f"[Request] {'=' * 60}")
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Any) -> None:
        duration = (timezone.now() - self.start_time).total_seconds() if self.start_time else 0

        if exc_type is None:
            # 正常完成
            logger.info(f"[Request] {'=' * 60}")
            logger.info(f"[Request] 完成: {self.func_name}")
            logger.info(f"[Request] ID: {self.request_id}")
            logger.info(f"[Request] 状态: success")
            logger.info(f"[Request] 耗时: {duration:.3f}s")
            logger.info(f"[Request] {'=' * 60}")
        else:
            # 发生异常
            logger.error(f"[Request] {'=' * 60}")
            logger.error(f"[Request] 异常: {self.func_name}")
            logger.error(f"[Request] ID: {self.request_id}")
            logger.error(f"[Request] 错误类型: {exc_type.__name__}")
            logger.error(f"[Request] 错误信息: {str(exc_val)}")
            logger.error(f"[Request] {'=' * 60}")


class DatabaseLogger:
    """数据库操作日志记录器"""

    @staticmethod
    def log_query_start(model_name: str, filter_kwargs: Optional[Dict[str, Any]] = None) -> None:
        """记录查询开始"""
        filters_msg = f" (filters: {filter_kwargs})" if filter_kwargs else ""
        logger.debug(f"[Database] 开始查询 {model_name}{filters_msg}")

    @staticmethod
    def log_query_end(model_name: str, count: Optional[int] = None, duration: Optional[float] = None) -> None:
        """记录查询结束"""
        count_msg = f" - 返回 {count}条记录" if count is not None else ""
        duration_msg = f" - 耗时: {duration:.3f}s" if duration else ""
        logger.debug(f"[Database] 完成查询 {model_name}{count_msg}{duration_msg}")

    @staticmethod
    def log_save_start(model_name: str, instance_id: Optional[Union[int, str]] = None) -> None:
        """记录保存开始"""
        id_msg = f" ID: {instance_id}" if instance_id else ""
        logger.debug(f"[Database] 开始保存 {model_name}{id_msg}")

    @staticmethod
    def log_save_end(model_name: str, instance_id: Union[int, str], created: bool = False, duration: Optional[float] = None) -> None:
        """记录保存结束"""
        action = "创建" if created else "更新"
        duration_msg = f" - 耗时: {duration:.3f}s" if duration else ""
        logger.debug(f"[Database] 完成{action} {model_name} ID: {instance_id}{duration_msg}")


def log_api_request(func: F) -> F:
    """API请求日志装饰器（同步方法）"""
    @functools.wraps(func)
    def wrapper(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        with RequestLogger(func.__name__, request):
            return func(self, request, *args, **kwargs)
    return cast(F, wrapper)


def log_async_api_request(func: F) -> F:
    """API请求日志装饰器（异步方法）"""
    @functools.wraps(func)
    async def wrapper(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        with RequestLogger(func.__name__, request):
            return await func(self, request, *args, **kwargs)
    return cast(F, wrapper)
