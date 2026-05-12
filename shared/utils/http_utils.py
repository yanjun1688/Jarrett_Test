"""
HTTP工具函数
提供HTTP请求相关的通用功能
"""

from __future__ import annotations

import httpx
import json
import logging
from typing import Dict, Any, Optional, Union


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
        method: HTTP方法
        url: 请求URL
        headers: 请求头
        body: 请求体
        timeout: 超时时间
        verify_ssl: 是否验证SSL证书

    Returns:
        包含响应信息的字典
    """
    try:
        from shared.utils.url_validator import validate_request_url
        url = validate_request_url(url)

        with httpx.Client(timeout=timeout, verify=verify_ssl) as client:
            request_kwargs: Dict[str, Any] = {
                'method': method.upper(),
                'url': url,
                'headers': headers or {}
            }

            if body is not None:
                if isinstance(body, dict):
                    request_kwargs['json'] = body
                elif isinstance(body, str):
                    request_kwargs['content'] = body.encode('utf-8')
                elif isinstance(body, bytes):
                    request_kwargs['content'] = body

            response = client.request(**request_kwargs)

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
        return {'status_code': 408, 'error': '请求超时', 'success': False}
    except httpx.RequestError as e:
        logger.error(f"HTTP请求失败: {method} {url} - {str(e)}")
        return {'status_code': 500, 'error': str(e), 'success': False}
    except Exception as e:
        logger.error(f"HTTP请求异常: {method} {url} - {str(e)}")
        return {'status_code': 500, 'error': str(e), 'success': False}
