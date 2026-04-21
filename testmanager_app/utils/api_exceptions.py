"""
统一的API异常处理模块

提供自定义业务异常类和统一的异常处理装饰器
"""
# pyright: reportArgumentType=false, reportReturnType=false

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, message: str, code: Optional[str] = None, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message: str = message
        self.code: Optional[str] = code
        self.status_code: int = status_code
        super().__init__(self.message)


class ResourceNotFoundException(BusinessException):
    """资源未找到异常"""
    def __init__(self, resource_name: str, resource_id: Union[int, str]):
        super().__init__(
            message=f"{resource_name} (ID: {resource_id}) 未找到",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ValidationFailedException(BusinessException):
    """验证失败异常"""
    def __init__(self, detail: Any):
        super().__init__(
            message=str(detail),
            code="VALIDATION_FAILED",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class DuplicateResourceException(BusinessException):
    """重复资源异常"""
    def __init__(self, resource_name: str, field: str, value: Any):
        super().__init__(
            message=f"{resource_name} 已存在: {field}={value}",
            code="DUPLICATE_RESOURCE",
            status_code=status.HTTP_409_CONFLICT
        )


class PermissionDeniedException(BusinessException):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )


def api_exception_handler(func: F) -> F:
    """
    统一API异常处理装饰器（同步方法）

    使用方法：
        @api_exception_handler
        def my_api_view(request, pk):
            ...
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
        # 获取请求对象和执行的函数名
        request: Any = None
        func_name: str = func.__name__

        # 从args中查找request对象（支持函数视图和类方法视图）
        for arg in args:
            if hasattr(arg, 'user'):  # 简单的request对象判断
                request = arg
                break

        # 生成请求ID用于日志追踪
        request_id: str = f"req_{id(request)}" if request else f"func_{id(func)}"

        try:
            logger.debug(f"[API] 开始执行 {func_name} - RequestID: {request_id}")
            result = func(*args, **kwargs)
            logger.debug(f"[API] 执行完成 {func_name} - RequestID: {request_id}")
            return result

        except BusinessException as e:
            # 业务异常
            logger.warning(f"[Business] {func_name} - {e.message} - RequestID: {request_id}")
            return Response(
                {'error': e.message, 'code': e.code, 'request_id': request_id},
                status=e.status_code
            )

        except ValidationError as e:
            # DRF验证异常
            logger.warning(f"[Validation] {func_name} - {str(e)} - RequestID: {request_id}")
            return Response(
                {'error': '参数验证失败', 'detail': str(e), 'code': 'VALIDATION_ERROR', 'request_id': request_id},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Http404:
            # Django的404异常
            logger.warning(f"[NotFound] {func_name} - 资源不存在 - RequestID: {request_id}")
            return Response(
                {'error': '请求的资源不存在', 'code': 'NOT_FOUND', 'request_id': request_id},
                status=status.HTTP_404_NOT_FOUND
            )

        except ObjectDoesNotExist as e:
            # Django模型不存在异常
            logger.warning(f"[NotFound] {func_name} - {str(e)} - RequestID: {request_id}")
            return Response(
                {'error': '请求的资源不存在', 'detail': str(e), 'code': 'NOT_FOUND', 'request_id': request_id},
                status=status.HTTP_404_NOT_FOUND
            )

        except IntegrityError as e:
            # 数据库完整性错误（如唯一键冲突）
            logger.error(f"[Database] {func_name} - 数据完整性错误: {str(e)} - RequestID: {request_id}")
            return Response(
                {'error': '数据冲突，可能已存在相同记录', 'code': 'INTEGRITY_ERROR', 'request_id': request_id},
                status=status.HTTP_409_CONFLICT
            )

        except Exception as e:
            # 未知异常
            logger.error(f"[Internal] {func_name} - 内部错误: {str(e)} - RequestID: {request_id}", exc_info=True)
            return Response(
                {'error': '服务器内部错误', 'detail': str(e), 'code': 'INTERNAL_ERROR', 'request_id': request_id},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return wrapper  # type: ignore[return-value]


def async_api_exception_handler(func: F) -> F:
    """
    统一的异步API异常处理装饰器

    使用方法：
        @async_api_exception_handler
        async def my_async_view(request):
            ...
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
        request: Any = None
        func_name: str = func.__name__

        for arg in args:
            if hasattr(arg, 'user'):
                request = arg
                break

        request_id: str = f"req_{id(request)}" if request else f"func_{id(func)}"

        try:
            logger.debug(f"[API] 开始执行异步方法 {func_name} - RequestID: {request_id}")
            result = await func(*args, **kwargs)
            logger.debug(f"[API] 异步方法执行完成 {func_name} - RequestID: {request_id}")
            return result

        except BusinessException as e:
            logger.warning(f"[Business] {func_name} - {e.message} - RequestID: {request_id}")
            from django.http import JsonResponse
            return JsonResponse(
                {'error': e.message, 'code': e.code, 'request_id': request_id},
                status=e.status_code
            )

        except ValidationError as e:
            logger.warning(f"[Validation] {func_name} - {str(e)} - RequestID: {request_id}")
            from django.http import JsonResponse
            return JsonResponse(
                {'error': '参数验证失败', 'detail': str(e), 'code': 'VALIDATION_ERROR', 'request_id': request_id},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"[Internal] {func_name} - 内部错误: {str(e)} - RequestID: {request_id}", exc_info=True)
            from django.http import JsonResponse
            return JsonResponse(
                {'error': '服务器内部错误', 'detail': str(e), 'code': 'INTERNAL_ERROR', 'request_id': request_id},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return wrapper  # type: ignore[return-value]