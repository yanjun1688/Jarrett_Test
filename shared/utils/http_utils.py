"""
HTTP工具函数
提供HTTP请求相关的通用功能
"""

from __future__ import annotations

import httpx
import json
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def make_http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Union[str, Dict, bytes]] = None,
    timeout: float = 30.0,
    verify_ssl: bool = True
) -> Dict[str, Any]:
    """
    发送HTTP请求
    
    Args:
        method: HTTP方法 (GET, POST, PUT, DELETE等)
        url: 请求URL
        headers: 请求头
        body: 请求体
        timeout: 超时时间（秒）
        verify_ssl: 是否验证SSL证书
        
    Returns:
        包含响应信息的字典
    """
    try:
        # SSRF 防护：验证目标 URL
        from shared.utils.url_validator import validate_request_url
        url = validate_request_url(url)

        with httpx.Client(timeout=timeout, verify=verify_ssl) as client:
            # 准备请求参数
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'headers': headers or {}
            }
            
            # 处理请求体
            if body is not None:
                if isinstance(body, dict):
                    request_kwargs['json'] = body
                elif isinstance(body, str):
                    request_kwargs['content'] = body.encode('utf-8')
                elif isinstance(body, bytes):
                    request_kwargs['content'] = body
            
            # 发送请求
            response = client.request(**request_kwargs)
            
            # 解析响应
            try:
                response_body = response.json()
                content_type = 'json'
            except (json.JSONDecodeError, ValueError):
                response_body = response.text
                content_type = 'text'
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_body,
                'content_type': content_type,
                'elapsed': response.elapsed.total_seconds(),
                'success': response.status_code < 400
            }
            
    except httpx.TimeoutException:
        logger.error(f"HTTP请求超时: {method} {url}")
        return {
            'status_code': 408,
            'error': '请求超时',
            'success': False
        }
    except httpx.RequestError as e:
        logger.error(f"HTTP请求失败: {method} {url} - {str(e)}")
        return {
            'status_code': 500,
            'error': str(e),
            'success': False
        }
    except Exception as e:
        logger.error(f"HTTP请求异常: {method} {url} - {str(e)}")
        return {
            'status_code': 500,
            'error': str(e),
            'success': False
        }


def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: 要验证的URL
        
    Returns:
        是否有效的URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def parse_headers(headers_str: str) -> Dict[str, str]:
    """
    解析HTTP头字符串
    
    Args:
        headers_str: HTTP头字符串（每行一个header）
        
    Returns:
        解析后的header字典
    """
    headers = {}
    if not headers_str:
        return headers
    
    for line in headers_str.strip().split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    return headers


def build_query_string(params: Dict[str, Any]) -> str:
    """
    构建查询字符串
    
    Args:
        params: 查询参数字典
        
    Returns:
        查询字符串
    """
    if not params:
        return ''
    
    query_parts = []
    for key, value in params.items():
        if value is not None:
            query_parts.append(f"{key}={value}")
    
    return '&'.join(query_parts)