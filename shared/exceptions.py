"""
统一异常定义
"""
from typing import Optional, Dict, Any


class JTestError(Exception):
    """JTest基础异常"""
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.message,
            "code": self.code,
            "details": self.details
        }


class ConfigurationError(JTestError):
    """配置错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class ValidationError(JTestError):
    """验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field:
            details = details or {}
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


class PlanningError(JTestError):
    """规划错误"""
    
    def __init__(self, message: str, stage: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if stage:
            details = details or {}
            details["stage"] = stage
        super().__init__(message, "PLANNING_ERROR", details)


class ExecutionError(JTestError):
    """执行错误"""
    
    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if node_id or node_type:
            details = details or {}
            if node_id:
                details["node_id"] = node_id
            if node_type:
                details["node_type"] = node_type
        super().__init__(message, "EXECUTION_ERROR", details)


class ResourceNotFoundError(JTestError):
    """资源未找到错误"""
    
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type}未找到: {resource_id}"
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(message, "RESOURCE_NOT_FOUND", details)


class AuthenticationError(JTestError):
    """认证错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(JTestError):
    """授权错误"""
    
    def __init__(self, message: str, permission: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if permission:
            details = details or {}
            details["permission"] = permission
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class RateLimitError(JTestError):
    """限流错误"""
    
    def __init__(self, message: str, limit: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if limit:
            details = details or {}
            details["limit"] = limit
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class ExternalServiceError(JTestError):
    """外部服务错误"""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"{service}服务错误: {message}"
        details = details or {}
        details["service"] = service
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR", details)


# HTTP相关异常
class RequestError(ExternalServiceError):
    """HTTP请求错误"""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if status_code:
            message = f"HTTP {status_code}: {message}"
        if url:
            message = f"在 {url} 处发生: {message}"
        
        super().__init__("HTTP", message, details)
        if url:
            self.details["url"] = url
        if status_code:
            self.details["status_code"] = status_code


class LLMError(ExternalServiceError):
    """LLM服务错误"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__("LLM", message, details)
        if provider:
            self.details["provider"] = provider


class CodeGenerationError(ExternalServiceError):
    """代码生成错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("CodeGeneration", message, details)


class DatabaseError(JTestError):
    """数据库错误"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if operation:
            details = details or {}
            details["operation"] = operation
        super().__init__(message, "DATABASE_ERROR", details)


class IsolationViolation(JTestError):
    """RAG 检索隔离违规 — 查询缺少必要的 knowledge_base_id 或 project_id 过滤条件"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ISOLATION_VIOLATION", details)


def handle_exception(exception: Exception) -> JTestError:
    """处理异常，转换为JTestError"""
    if isinstance(exception, JTestError):
        return exception
    
    # 处理常见异常类型
    if isinstance(exception, ValueError):
        return ValidationError(str(exception))
    elif isinstance(exception, KeyError):
        return ValidationError(f"缺少必要字段: {exception}")
    elif isinstance(exception, AttributeError):
        return ValidationError(f"属性错误: {exception}")
    elif isinstance(exception, TypeError):
        return ValidationError(f"类型错误: {exception}")
    elif isinstance(exception, FileNotFoundError):
        return ResourceNotFoundError("文件", str(exception))
    elif isinstance(exception, PermissionError):
        return AuthorizationError(f"权限不足: {exception}")
    elif isinstance(exception, TimeoutError):
        return ExecutionError(f"操作超时: {exception}")
    else:
        return JTestError(f"未知错误: {str(exception)}")