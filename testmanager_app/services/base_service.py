"""
基础服务类
提供统一的异常处理、日志记录和返回格式
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class ServiceException(APIException):
    """服务层异常基类"""
    status_code: int = 400
    default_detail: str = '服务执行失败'
    default_code: str = 'service_error'

    def __init__(self, detail: str | None = None, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(detail=detail, code=code)
        if status_code is not None:
            self.status_code = status_code


class ValidationServiceException(ServiceException):
    """验证异常"""
    status_code: int = 400
    default_detail: str = '数据验证失败'
    default_code: str = 'validation_error'


class NotFoundServiceException(ServiceException):
    """资源未找到异常"""
    status_code: int = 404
    default_detail: str = '资源未找到'
    default_code: str = 'not_found'


class BaseService:
    """基础服务类"""
    
    @classmethod
    def handle_exception(cls, e: Exception, context: str = "") -> Dict[str, Any]:
        """
        统一异常处理
        
        Args:
            e: 异常对象
            context: 异常上下文描述
            
        Returns:
            标准化的错误响应
        """
        logger.error(f"{context}异常: {str(e)}", exc_info=True)
        
        if isinstance(e, ValidationError):
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'status_code': 400
            }
        elif isinstance(e, ObjectDoesNotExist):
            return {
                'success': False,
                'error': str(e),
                'error_type': 'not_found',
                'status_code': 404
            }
        elif isinstance(e, ServiceException):
            return {
                'success': False,
                'error': str(e.detail) if hasattr(e, 'detail') else str(e),
                'error_type': e.default_code,
                'status_code': e.status_code
            }
        else:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'internal_error',
                'status_code': 500
            }
    
    @classmethod
    def create_success_response(cls, data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 成功消息
            
        Returns:
            标准化的成功响应
        """
        response: Dict[str, Any] = {
            'success': True,
            'message': message,
            'status_code': 200
        }
        
        if data is not None:
            response['data'] = data
            
        return response
    
    @classmethod
    def create_error_response(cls, error: str, error_type: str = "internal_error", 
                             status_code: int = 500) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            error: 错误信息
            error_type: 错误类型
            status_code: HTTP状态码
            
        Returns:
            标准化的错误响应
        """
        return {
            'success': False,
            'error': error,
            'error_type': error_type,
            'status_code': status_code
        }
    
    @classmethod
    def validate_required_fields(cls, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        验证必填字段
        
        Args:
            data: 数据字典
            required_fields: 必填字段列表
            
        Raises:
            ValidationServiceException: 字段缺失时抛出
        """
        missing_fields: List[str] = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationServiceException(f"缺少必填字段: {', '.join(missing_fields)}")
    
    @classmethod
    def log_operation(cls, operation: str, details: Dict[str, Any], level: str = "info") -> None:
        """
        统一日志记录
        
        Args:
            operation: 操作名称
            details: 操作详情
            level: 日志级别
        """
        log_message = f"{operation}: {details}"
        
        if level == "debug":
            logger.debug(log_message)
        elif level == "info":
            logger.info(log_message)
        elif level == "warning":
            logger.warning(log_message)
        elif level == "error":
            logger.error(log_message)
        else:
            logger.info(log_message)