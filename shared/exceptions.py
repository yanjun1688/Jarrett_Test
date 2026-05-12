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


class ValidationError(JTestError):
    """验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field:
            details = details or {}
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


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


class IsolationViolation(JTestError):
    """RAG 检索隔离违规 — 查询缺少必要的 knowledge_base_id 或 project_id 过滤条件"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ISOLATION_VIOLATION", details)

