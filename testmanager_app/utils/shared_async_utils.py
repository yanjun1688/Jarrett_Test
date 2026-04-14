"""
统一的异步工具模块
合并了 async_utils.py 和 utils/async_helper.py 的功能

优化版本：
- 移除全局事件循环管理器，依赖 ASGI/Daphne 自动管理
- 同步包装器使用智能事件循环检测
- 减少不必要的上下文切换开销
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from asgiref.sync import sync_to_async, async_to_sync

logger = logging.getLogger(__name__)


def _is_in_async_context() -> bool:
    """
    检测当前是否在异步上下文中
    
    Returns:
        bool: 如果在异步上下文中返回 True
    """
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _run_async_safely(coro) -> Any:
    """
    在同步上下文中执行协程
    
    注意：此函数仅用于同步上下文。如果在异步上下文中调用，
    请直接使用 await 执行协程，而不是调用此函数。
    
    Args:
        coro: 协程对象
        
    Returns:
        协程执行结果
        
    Raises:
        RuntimeError: 如果在异步上下文中被调用
    """
    if _is_in_async_context():
        raise RuntimeError(
            "_run_async_safely() 不能在异步上下文中调用。"
            "请直接使用 'await coro' 执行协程，而不是调用此同步包装器。"
        )
    return asyncio.run(coro)


# ==================== API请求执行 ====================

async def execute_single_request_async(api_request: Any, user: Any = None) -> Dict[str, Any]:
    """
    纯异步函数 - 执行单个 API 请求并验证断言

    参数:
        api_request: ApiRequest 模型实例或字典
        user: 执行用户（可选）

    返回:
        dict: 包含执行结果的字典
    """
    # 如果 api_request 是模型实例，获取实际数据
    from testmanager_app.models import ApiAssertion
    import inspect

    if inspect.isawaitable(api_request):
        api_request = await api_request

    # 如果传入的是字典，直接使用
    if isinstance(api_request, dict):
        api_request_data = api_request
        api_request_obj = None
    else:
        # 如果是模型实例，需要同步提取属性，避免在异步上下文中访问模型属性
        def _extract_api_request_data_sync(api_req):
            """同步函数：从模型对象提取数据字典"""
            return {
                'id': api_req.id,
                'method': api_req.method,
                'url': api_req.url,
                'headers': getattr(api_req, 'headers', '') or '',
                'body': getattr(api_req, 'body', '') or '',
                'timeout': getattr(api_req, 'timeout', 30) or 30,
                'project_id': api_req.project_id if hasattr(api_req, 'project_id') else None,
                'created_by_id': api_req.created_by_id if hasattr(api_req, 'created_by') else None
            }

        api_request_data = await sync_to_async(_extract_api_request_data_sync)(api_request)
        api_request_obj = api_request

    # 提取断言
    assertions = []
    if api_request_obj:
        # 如果是模型实例，异步获取断言
        def _get_assertions_sync(api_req):
            return list(api_req.assertions.all())

        assertions_list = await sync_to_async(_get_assertions_sync)(api_request_obj)
        for assertion in assertions_list:
            assertions.append({
                'id': assertion.id,
                'type': assertion.assertion_type,
                'field_path': assertion.field_path,
                'expected_value': assertion.expected_value,
                'comparison_operator': assertion.comparison_operator,
                'is_critical': assertion.is_critical
            })
    elif 'assertions' in api_request_data:
        # 如果传入的是字典且包含断言
        assertions = api_request_data.get('assertions', [])

    # 执行HTTP请求
    start_time = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=api_request_data.get('timeout', 30)) as client:
            # 准备请求参数
            method = api_request_data.get('method', 'GET').upper()
            url = api_request_data.get('url', '')
            headers = api_request_data.get('headers', {})
            body = api_request_data.get('body', None)

            # SSRF 防护：验证目标 URL
            from shared.utils.url_validator import validate_request_url
            url = validate_request_url(url)

            # 发送请求
            logger.info(f"发送异步请求: {method} {url}")
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body if isinstance(body, (bytes, str)) else json.dumps(body) if body else None
            )

            # 计算响应时间
            response_time = (datetime.now() - start_time).total_seconds()

            # 解析响应
            try:
                response_body = response.json()
                content_type = 'json'
            except (json.JSONDecodeError, ValueError):
                response_body = response.text
                content_type = 'text'

            # 验证断言
            assertion_results = []
            passed_count = 0
            total_assertions = len(assertions)

            for assertion in assertions:
                result = await validate_assertion_async(
                    assertion=assertion,
                    response=response,
                    response_time=response_time,
                    response_body=response_body,
                    content_type=content_type
                )
                assertion_results.append(result)
                if result.get('passed', False):
                    passed_count += 1

            # 构建结果
            execution_result = {
                'status_code': response.status_code,
                'response_time': response_time,
                'response_body': response_body,
                'response_headers': dict(response.headers),
                'assertions': assertion_results,
                'passed_count': passed_count,
                'total_assertions': total_assertions,
                'success': passed_count == total_assertions if total_assertions > 0 else response.status_code < 400,
                'error': None
            }

            logger.info(f"异步请求执行完成: {method} {url} - 状态码: {response.status_code}, 响应时间: {response_time:.2f}s")
            return execution_result

    except Exception as e:
        logger.error(f"异步请求执行失败: {str(e)}")
        return {
            'status_code': None,
            'response_time': (datetime.now() - start_time).total_seconds(),
            'response_body': None,
            'response_headers': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': len(assertions),
            'success': False,
            'error': str(e)
        }


async def validate_assertion_async(
    assertion: Dict[str, Any],
    response: httpx.Response,
    response_time: float,
    response_body: Any,
    content_type: str
) -> Dict[str, Any]:
    """
    异步验证断言

    参数:
        assertion: 断言配置字典
        response: httpx.Response 对象
        response_time: 响应时间（秒）
        response_body: 响应体
        content_type: 响应内容类型（'json' 或 'text'）

    返回:
        dict: 断言验证结果
    """
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
            # 从响应头中获取字段值
            header_name = field_path
            actual_value = response.headers.get(header_name)
        elif assertion_type == 'json_path':
            # JSON路径断言
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
            
            # 使用jsonpath-ng提取值
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

        # 执行比较
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
            passed = float(actual_value) > float(expected_value)
        elif comparison_operator == 'less_than':
            passed = float(actual_value) < float(expected_value)
        elif comparison_operator == 'greater_than_or_equal':
            passed = float(actual_value) >= float(expected_value)
        elif comparison_operator == 'less_than_or_equal':
            passed = float(actual_value) <= float(expected_value)
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


# ==================== 批量执行工具 ====================

async def execute_batch_requests_async(api_requests: List[Any], max_concurrent: int = 10) -> List[Dict[str, Any]]:
    """
    批量异步执行API请求

    参数:
        api_requests: API请求列表（模型实例或字典）
        max_concurrent: 最大并发数

    返回:
        List[Dict]: 执行结果列表
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_with_semaphore(api_request):
        async with semaphore:
            return await execute_single_request_async(api_request)
    
    tasks = [execute_with_semaphore(req) for req in api_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理异常结果
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                'success': False,
                'error': str(result),
                'request_index': i
            })
        else:
            processed_results.append(result)
    
    return processed_results


# ==================== 同步包装器 ====================

def execute_single_request_sync(api_request: Any, user: Any = None) -> Dict[str, Any]:
    """
    同步包装器 - 执行单个API请求

    智能执行：根据当前上下文自动选择正确的执行方式
    - 在异步上下文中：使用 async_to_sync
    - 在同步上下文中：使用 asyncio.run()

    参数:
        api_request: ApiRequest 模型实例或字典
        user: 执行用户（可选）

    返回:
        dict: 执行结果
    """
    return _run_async_safely(execute_single_request_async(api_request, user))


def execute_batch_requests_sync(api_requests: List[Any], max_concurrent: int = 10) -> List[Dict[str, Any]]:
    """
    同步包装器 - 批量执行API请求

    智能执行：根据当前上下文自动选择正确的执行方式

    参数:
        api_requests: API请求列表
        max_concurrent: 最大并发数

    返回:
        List[Dict]: 执行结果列表
    """
    return _run_async_safely(execute_batch_requests_async(api_requests, max_concurrent))


# ==================== 工具函数 ====================

def validate_assertion_common(
    assertion_type: str,
    field_path: str,
    expected_value: Any,
    actual_value: Any,
    comparison_operator: str = 'equals'
) -> Dict[str, Any]:
    """
    通用的断言验证函数（同步）

    参数:
        assertion_type: 断言类型
        field_path: 字段路径
        expected_value: 期望值
        actual_value: 实际值
        comparison_operator: 比较操作符

    返回:
        dict: 验证结果
    """
    try:
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
            passed = float(actual_value) > float(expected_value)
        elif comparison_operator == 'less_than':
            passed = float(actual_value) < float(expected_value)
        else:
            passed = actual_value == expected_value

        return {
            'assertion_type': assertion_type,
            'field_path': field_path,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'passed': passed,
            'error': None
        }
    except Exception as e:
        return {
            'assertion_type': assertion_type,
            'field_path': field_path,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'passed': False,
            'error': str(e)
        }