"""
纯同步HTTP执行工具
提供不使用 event loop 的同步 HTTP 请求执行功能
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _parse_headers(headers: Any) -> Dict[str, str]:
    """
    解析请求头 - 只支持 JSON 字符串和字典格式
    
    Args:
        headers: 请求头数据（JSON字符串或字典）
    
    Returns:
        Dict[str, str]: 解析后的请求头字典
    
    Raises:
        ValueError: 如果格式不正确
    """
    if not headers:
        return {}
    
    if isinstance(headers, dict):
        return headers
    
    if isinstance(headers, str):
        headers_str = headers.strip()
        if not headers_str:
            return {}
        
        if headers_str.startswith('{'):
            try:
                parsed = json.loads(headers_str)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    logger.warning(f"[Sync] Headers 解析结果不是字典: {type(parsed)}")
                    return {}
            except json.JSONDecodeError as e:
                logger.error(f"[Sync] Headers JSON 解析失败: {e}")
                return {}
        
        logger.warning(f"[Sync] Headers 不是 JSON 格式，请使用标准 JSON 格式")
        return {}
    
    logger.warning(f"[Sync] Headers 类型不支持: {type(headers)}")
    return {}


def execute_request_direct(api_request: Any, user: Any = None) -> Dict[str, Any]:
    """
    纯同步执行单个API请求 - 不涉及任何异步/event loop
    
    使用 httpx.Client (同步) 而不是 httpx.AsyncClient
    
    Args:
        api_request: ApiRequest 模型实例或字典
        user: 执行用户（可选）
    
    Returns:
        dict: 执行结果
    """
    if isinstance(api_request, dict):
        api_request_data = api_request
    else:
        api_request_data = {
            'id': api_request.id,
            'method': api_request.method,
            'url': api_request.url,
            'headers': getattr(api_request, 'headers', '') or '',
            'body': getattr(api_request, 'body', '') or '',
            'timeout': getattr(api_request, 'timeout', 30) or 30,
            'project_id': api_request.project_id if hasattr(api_request, 'project_id') else None,
        }
        if hasattr(api_request, 'assertions'):
            api_request_data['assertions'] = [
                {
                    'id': a.id,
                    'type': a.assertion_type,
                    'field_path': a.field_path,
                    'expected_value': a.expected_value,
                    'comparison_operator': a.comparison_operator,
                    'is_critical': a.is_critical
                }
                for a in api_request.assertions.all()
            ]
    
    start_time = datetime.now()
    try:
        with httpx.Client(timeout=api_request_data.get('timeout', 30)) as client:
            method = api_request_data.get('method', 'GET').upper()
            url = api_request_data.get('url', '')
            headers = _parse_headers(api_request_data.get('headers', {}))
            
            from shared.utils.url_validator import validate_request_url
            url = validate_request_url(url)
            
            logger.info(f"[Sync] 发送同步请求: {method} {url}")
            
            body = api_request_data.get('body')
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                content=body if isinstance(body, (bytes, str)) else json.dumps(body) if body else None
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            try:
                response_body = response.json()
                content_type = 'json'
            except (json.JSONDecodeError, ValueError):
                response_body = response.text
                content_type = 'text'
            
            assertions = api_request_data.get('assertions', [])
            assertion_results = []
            passed_count = 0
            
            for assertion in assertions:
                result = _validate_assertion_sync(
                    assertion=assertion,
                    response=response,
                    response_time=response_time,
                    response_body=response_body,
                    content_type=content_type
                )
                assertion_results.append(result)
                if result.get('passed'):
                    passed_count += 1
            
            return {
                'status_code': response.status_code,
                'response_time': response_time,
                'response_body': response_body,
                'response_headers': dict(response.headers),
                'assertions': assertion_results,
                'passed_count': passed_count,
                'total_assertions': len(assertions),
                'success': passed_count == len(assertions) if assertions else response.status_code < 400,
                'error': None
            }
    
    except Exception as e:
        logger.error(f"[Sync] 请求执行失败: {str(e)}")
        return {
            'status_code': None,
            'response_time': (datetime.now() - start_time).total_seconds(),
            'response_body': None,
            'response_headers': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': len(api_request_data.get('assertions', [])),
            'success': False,
            'error': str(e)
        }


def execute_batch_requests_direct(api_requests: List[Any], max_concurrent: int = 10) -> List[Dict[str, Any]]:
    """
    批量同步执行API请求（顺序执行）
    
    Args:
        api_requests: API请求列表
        max_concurrent: 最大并发数（本函数忽略，始终顺序执行）
    
    Returns:
        List[Dict[str, Any]]: 执行结果列表
    """
    results = []
    for api_request in api_requests:
        result = execute_request_direct(api_request)
        results.append(result)
    return results


def _validate_assertion_sync(
    assertion: Dict[str, Any],
    response: httpx.Response,
    response_time: float,
    response_body: Any,
    content_type: str
) -> Dict[str, Any]:
    """同步断言验证"""
    assertion_type = assertion.get('type')
    field_path = assertion.get('field_path', '')
    expected_value = assertion.get('expected_value')
    comparison_operator = assertion.get('comparison_operator', 'equals')
    is_critical = assertion.get('is_critical', False)
    
    try:
        if assertion_type == 'status_code':
            actual_value = response.status_code
        elif assertion_type == 'response_time':
            actual_value = response_time
        elif assertion_type == 'response_body':
            actual_value = response_body
        elif assertion_type == 'response_header':
            header_name = field_path
            actual_value = response.headers.get(header_name)
        elif assertion_type == 'json_path':
            if content_type != 'json':
                return {
                    'assertion_type': assertion_type,
                    'field_path': field_path,
                    'expected_value': expected_value,
                    'actual_value': None,
                    'passed': False,
                    'error': '响应不是JSON格式',
                    'is_critical': is_critical
                }
            
            from jsonpath_ng import parse
            jsonpath_expr = parse(field_path)
            matches = [match.value for match in jsonpath_expr.find(response_body)]
            actual_value = matches[0] if matches else None
        else:
            return {
                'assertion_type': assertion_type,
                'field_path': field_path,
                'expected_value': expected_value,
                'actual_value': None,
                'passed': False,
                'error': f'不支持的断言类型: {assertion_type}',
                'is_critical': is_critical
            }
        
        passed = False
        if comparison_operator == 'equals':
            passed = actual_value == expected_value
        elif comparison_operator == 'not_equals':
            passed = actual_value != expected_value
        elif comparison_operator == 'contains':
            passed = str(expected_value) in str(actual_value)
        elif comparison_operator == 'not_contains':
            passed = str(expected_value) not in str(actual_value)
        elif comparison_operator == 'greater_than':
            if actual_value is not None and expected_value is not None:
                passed = float(actual_value) > float(expected_value)
            else:
                passed = False
        elif comparison_operator == 'less_than':
            if actual_value is not None and expected_value is not None:
                passed = float(actual_value) < float(expected_value)
            else:
                passed = False
        elif comparison_operator == 'greater_than_or_equal':
            if actual_value is not None and expected_value is not None:
                passed = float(actual_value) >= float(expected_value)
            else:
                passed = False
        elif comparison_operator == 'less_than_or_equal':
            if actual_value is not None and expected_value is not None:
                passed = float(actual_value) <= float(expected_value)
            else:
                passed = False
        elif comparison_operator == 'regex_match':
            import re
            passed = bool(re.match(str(expected_value), str(actual_value)))
        else:
            passed = actual_value == expected_value
        
        return {
            'assertion_type': assertion_type,
            'field_path': field_path,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'passed': passed,
            'error': None,
            'is_critical': is_critical
        }
    
    except Exception as e:
        logger.error(f"断言验证失败: {str(e)}")
        return {
            'assertion_type': assertion_type,
            'field_path': field_path,
            'expected_value': expected_value,
            'actual_value': None,
            'passed': False,
            'error': str(e),
            'is_critical': is_critical
        }