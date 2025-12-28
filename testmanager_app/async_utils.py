"""
异步执行工具模块

提供异步API请求执行和批量执行功能

创建时间: 2024-11-24
"""
import asyncio
import json
import httpx
import logging
from datetime import datetime
from asgiref.sync import sync_to_async


logger = logging.getLogger(__name__)


async def execute_single_request_async(api_request):
    """
    纯异步函数 - 执行单个 API 请求并验证断言

    参数:
        api_request: ApiRequest 模型实例或字典

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
                'headers': api_req.headers,
                'body': api_req.body,
            }
        
        extract_data_async = sync_to_async(_extract_api_request_data_sync, thread_sensitive=True)
        api_request_data = await extract_data_async(api_request)
        api_request_obj = api_request  # 保留对象引用用于后续断言验证

    headers = {}
    if api_request_data['headers']:
        try:
            headers = json.loads(api_request_data['headers'])
        except json.JSONDecodeError:
            for line in api_request_data['headers'].split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

    response = None
    error_message = None
    request_id = api_request_data.get('id', 'unknown')
    try:
        # 配置代理（从环境变量读取Windows代理）
        import os
        proxy_url = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        client_kwargs = {'proxy': proxy_url} if proxy_url else {}

        logger.info(f"[{request_id}] Starting request: {api_request_data['method']} {api_request_data['url']}")

        async with httpx.AsyncClient(**client_kwargs) as client:
            request_body = api_request_data['body'] or None
            if request_body:
                try:
                    # 尝试解析为JSON
                    json_body = json.loads(request_body)
                    logger.debug(f"[{request_id}] Sending JSON body: {len(request_body)} bytes")
                    response = await client.request(
                        method=api_request_data['method'],
                        url=api_request_data['url'],
                        headers=headers,
                        json=json_body,
                        timeout=60.0
                    )
                except json.JSONDecodeError:
                    # 如果不是JSON，作为普通文本发送
                    logger.debug(f"[{request_id}] Sending text body: {len(request_body)} bytes")
                    response = await client.request(
                        method=api_request_data['method'],
                        url=api_request_data['url'],
                        headers=headers,
                        content=request_body.encode('utf-8'),
                        timeout=60.0
                    )
            else:
                logger.debug(f"[{request_id}] Sending request without body")
                response = await client.request(
                    method=api_request_data['method'],
                    url=api_request_data['url'],
                    headers=headers,
                    timeout=60.0
                )

        logger.info(f"[{request_id}] Request completed: status={response.status_code if response else 'None'}, elapsed={response.elapsed.total_seconds() if response else 'N/A'}s")

    except Exception as e:
        error_message = str(e)
        logger.error(f"[{request_id}] Request failed: {error_message}")

    # 构建结果字典
    result = {
        'api_request_id': api_request_data['id'],
        'request_method': api_request_data['method'],
        'request_url': api_request_data['url'],
        'request_headers': headers,
        'request_body': api_request_data['body'],
        'response_status': response.status_code if response else None,
        'response_headers': dict(response.headers) if response else None,
        'response_body': response.text if response else None,
        'response_time': response.elapsed.total_seconds() if response else None,
        'error_message': error_message,
        'execution_time': datetime.now().isoformat(),
        'success': response is not None and response.status_code < 400 and error_message is None,
    }

    # 验证断言（无论是否有api_request_obj，只要有api_request_id和response就验证）
    if response and api_request_data.get('id'):
        # 使用已经提取的 request_id，避免在异步上下文中访问模型属性
        logger.info(f"开始验证断言，API请求ID: {request_id}")
        try:
            # 使用 sync_to_async 包装数据库查询（定义普通函数而不是lambda）
            # 注意：需要确保在正确的线程中执行，避免 CurrentThreadExecutor 错误
            def _get_assertions_sync(api_req_id):
                """同步函数：获取断言列表，使用 values() 直接获取字典，避免访问模型属性"""
                # 使用 api_request_id 而不是模型对象，完全避免访问模型属性
                # 这样可以避免在异步上下文中触发数据库查询
                from testmanager_app.models import ApiAssertion
                assertions_qs = ApiAssertion.objects.filter(api_request_id=api_req_id)
                # 使用 values() 获取字典列表，包含所有需要的字段
                assertions_list = list(assertions_qs.values(
                    'id', 
                    'assertion_type', 
                    'expected_value', 
                    'comparison',
                    'field_path'  # 修改：从field改为field_path
                ))
                return assertions_list
            
            get_assertions_async = sync_to_async(_get_assertions_sync, thread_sensitive=True)
            # 使用 api_request_data['id'] 获取断言
            assertions_data = await get_assertions_async(api_request_data['id'])

            # 处理无断言的情况
            if len(assertions_data) == 0:
                logger.info(f"API请求ID {request_id} 没有配置断言，跳过断言验证")
                result['assertions'] = []
                result['all_assertions_passed'] = True  # 无断言时视为通过
                result['passed_count'] = 0
                result['total_assertions'] = 0
            else:
                assertion_results = []
                all_passed = True
                passed_count = 0
                total_count = len(assertions_data)

                for assertion_data in assertions_data:
                    # 使用字典数据而不是模型对象来验证断言
                    assertion_result = await _validate_assertion_async_from_dict(assertion_data, response, result)
                    assertion_results.append(assertion_result)
                    if assertion_result['passed']:
                        passed_count += 1
                    else:
                        all_passed = False

                result['assertions'] = assertion_results
                result['all_assertions_passed'] = all_passed
                result['passed_count'] = passed_count
                result['total_assertions'] = total_count

                logger.info(f"断言验证完成，通过: {passed_count}/{total_count}, 全部通过: {all_passed}")

        except Exception as e:
            logger.error(f"验证断言时发生错误: {str(e)}")
            result['assertion_error'] = str(e)
            # 即使断言验证出错，也不影响请求执行结果
            result['assertions'] = []
            result['all_assertions_passed'] = True  # 出错时视为通过，不影响执行
            result['passed_count'] = 0
            result['total_assertions'] = 0

    return result



def _extract_value_by_path(data, field_path):
    """
    根据字段路径提取值
    支持两种格式：
    1. 点号路径：data.id, data.list[0].name, [0].data.capacity
    2. JSONPath：$.data.id, $[*].data.capacity
    
    特殊处理：
    - 当数据是数组且路径不是以索引开头时，自动使用JSONPath在数组中查找所有匹配值，返回第一个
    
    Args:
        data: 要提取的数据（字典或列表）
        field_path: 字段路径
    
    Returns:
        提取的值，如果路径不存在返回None
    """
    if not field_path:
        return None
    
    try:
        # 如果是JSONPath格式（以$开头），使用jsonpath_ng解析
        if field_path.startswith('$'):
            from jsonpath_ng import parse as jsonpath_parse
            expr = jsonpath_parse(field_path)
            matches = [match.value for match in expr.find(data)]
            return matches[0] if matches else None
        else:
            # 点号路径：data.id, data.list[0].name, [0].data.capacity
            # 特殊处理：如果数据是数组且路径不是以索引开头，使用JSONPath查找
            if isinstance(data, list) and not field_path.startswith('['):
                # 自动转换为JSONPath格式：data.capacity -> $[*].data.capacity
                jsonpath_expr = f"$[*].{field_path}"
                from jsonpath_ng import parse as jsonpath_parse
                expr = jsonpath_parse(jsonpath_expr)
                matches = [match.value for match in expr.find(data)]
                # 过滤掉None值
                valid_matches = [m for m in matches if m is not None]
                return valid_matches[0] if valid_matches else None
            
            # 处理数组索引：list[0] -> list.0
            path_parts = field_path.replace('[', '.').replace(']', '').split('.')
            value = data
            
            for part in path_parts:
                if not part:  # 跳过空字符串（可能是由于连续的.或[]）
                    continue
                    
                if isinstance(value, dict):
                    value = value.get(part)
                elif isinstance(value, list):
                    try:
                        index = int(part)
                        value = value[index] if 0 <= index < len(value) else None
                    except (ValueError, IndexError):
                        return None
                else:
                    return None
                if value is None:
                    return None
            return value
    except Exception as e:
        logger.warning(f"提取字段路径值失败: {field_path}, 错误: {str(e)}")
        return None


async def _validate_assertion_async_from_dict(assertion_data, response, request_result):
    """异步验证单个断言（从字典数据）
    
    设计理念：以「值定位」为核心
    - status_code: 状态码断言（特殊值来源，不需要字段路径）
    - response_time: 响应时间断言（特殊值来源，不需要字段路径）
    - response_body_field: 响应体字段断言（需要字段路径定位）
    - response_header_field: 响应头字段断言（需要字段路径定位）
    
    支持模型的比较方式（与值类型解耦）：
    - equals: 等于
    - contains: 包含
    - not_contains: 不包含
    - greater_than: 大于
    - less_than: 小于
    """
    # 初始化变量，防止异常处理块中访问未定义的变量
    assertion_type = None
    comparison = None
    expected_value = None
    field_path = None
    actual_value = ""
    passed = False

    try:
        assertion_type = assertion_data.get('assertion_type')
        comparison = assertion_data.get('comparison', 'equals')  # 默认等于
        expected_value = assertion_data.get('expected_value')
        field_path = assertion_data.get('field_path', '').strip() if assertion_data.get('field_path') else ''

        # 根据断言类型获取实际值
        if assertion_type == 'status_code':
            # 状态码：特殊值来源，不需要字段路径
            actual_value = str(response.status_code)
            
        elif assertion_type == 'response_time':
            # 响应时间：特殊值来源，不需要字段路径
            actual_value = str(request_result.get('response_time', 0))
            
        elif assertion_type == 'response_body_field':
            # 响应体字段：需要字段路径定位
            if not field_path:
                actual_value = "错误: 响应体字段断言必须指定字段路径"
                passed = False
            else:
                try:
                    # 解析响应体为JSON
                    response_json = response.json()
                    # 使用字段路径提取值
                    extracted_value = _extract_value_by_path(response_json, field_path)
                    if extracted_value is None:
                        actual_value = f"错误: 字段路径 '{field_path}' 未找到值"
                        passed = False
                    else:
                        actual_value = str(extracted_value)
                except Exception as e:
                    # 响应体不是JSON或解析失败
                    actual_value = f"错误: 无法解析响应体为JSON - {str(e)}"
                    passed = False
            
        elif assertion_type == 'response_header_field':
            # 响应头字段：需要字段路径（响应头字段名）
            if not field_path:
                actual_value = "错误: 响应头字段断言必须指定字段路径（响应头字段名）"
                passed = False
            else:
                # 字段路径就是响应头字段名
                actual_value = str(response.headers.get(field_path, ''))
            
        else:
            # 处理未知的断言类型（向后兼容旧数据）
            if assertion_type == 'response_body':
                # 兼容旧的response_body类型（无字段路径，断言整个响应体）
                actual_value = response.text
            elif assertion_type == 'response_header':
                # 兼容旧的response_header类型
                old_field = assertion_data.get('field', '')
                header_name = old_field if old_field else expected_value.split(':')[0] if ':' in expected_value else ''
                actual_value = str(response.headers.get(header_name, ''))
            else:
                # 处理未知的断言类型
                passed = False
                actual_value = f"未知的断言类型: {assertion_type}"
                return {
                    'id': assertion_data.get('id'),
                    'assertion_type': assertion_type,
                    'field_path': field_path,  # 添加字段路径到返回结果
                    'comparison': comparison,
                    'expected_value': expected_value,
                    'actual_value': actual_value,
                    'passed': passed,
                }

        # 根据比较方式验证断言
        if comparison == 'equals':
            passed = str(actual_value) == str(expected_value)
        elif comparison == 'contains':
            # 包含比较：实际值是否包含期望值
            # 1. 如果去除空格后相等，直接返回True（处理 "128GB" vs "128 GB" 的情况）
            actual_str = str(actual_value).strip()
            expected_str = str(expected_value).strip()
            
            # 去除所有空格后比较
            actual_no_spaces = actual_str.replace(' ', '')
            expected_no_spaces = expected_str.replace(' ', '')
            
            if actual_no_spaces == expected_no_spaces:
                passed = True
            else:
                # 2. 检查实际值是否包含期望值（去除空格后）
                passed = expected_no_spaces in actual_no_spaces
        elif comparison == 'not_contains':
            # 不包含比较：实际值不包含期望值
            actual_str = str(actual_value).strip()
            expected_str = str(expected_value).strip()
            passed = expected_str not in actual_str
        elif comparison == 'greater_than':
            try:
                passed = float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                passed = False
                actual_value = f"无法比较: {actual_value} 和 {expected_value}"
        elif comparison == 'less_than':
            try:
                passed = float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                passed = False
                actual_value = f"无法比较: {actual_value} 和 {expected_value}"
        else:
            # 未知的比较方式，默认使用等于
            logger.warning(f"未知的比较方式: {comparison}，使用默认的等于比较")
            passed = str(actual_value) == str(expected_value)

        return {
            'id': assertion_data.get('id'),
            'assertion_type': assertion_type,
            'field_path': field_path,  # 添加字段路径到返回结果
            'comparison': comparison,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'passed': passed,
        }

    except Exception as e:
        logger.error(f"验证断言时发生异常: {str(e)}")
        return {
            'id': assertion_data.get('id'),
            'assertion_type': assertion_type,
            'field_path': field_path,  # 添加字段路径到返回结果
            'comparison': comparison,
            'expected_value': expected_value,
            'actual_value': f"验证失败: {str(e)}",
            'passed': False,
        }


async def _validate_assertion_async(assertion, response, request_result):
    """异步验证单个断言（从模型对象，向后兼容）"""
    # 初始化变量，防止异常处理块中访问未定义的变量
    assertion_type = None
    target_value = None
    actual_value = ""
    passed = False
    assertion_id = None

    try:
        # 使用 sync_to_async 包装模型属性访问，避免 CurrentThreadExecutor 错误
        def _extract_assertion_data_sync(assertion_obj):
            """同步函数：从断言对象提取数据"""
            return {
                'id': assertion_obj.id,
                'assertion_type': assertion_obj.assertion_type,
                'expected_value': getattr(assertion_obj, 'expected_value', getattr(assertion_obj, 'target_value', None)),
            }
        
        extract_assertion_async = sync_to_async(_extract_assertion_data_sync, thread_sensitive=True)
        assertion_data = await extract_assertion_async(assertion)
        
        assertion_id = assertion_data['id']
        assertion_type = assertion_data['assertion_type']
        target_value = assertion_data['expected_value']

        if assertion_type == 'status_code':
            actual_value = str(response.status_code)
            passed = actual_value == str(target_value)

        elif assertion_type == 'contains':
            actual_value = response.text
            passed = target_value in actual_value

        elif assertion_type == 'json_equals':
            try:
                response_json = response.json()
                expected_json = json.loads(target_value)
                actual_value = json.dumps(response_json, ensure_ascii=False)
                passed = response_json == expected_json
            except (json.JSONDecodeError, ValueError) as json_error:
                passed = False
                actual_value = f"JSON解析失败: {str(json_error)}"

        elif assertion_type == 'response_time':
            actual_value = str(request_result['response_time'])
            passed = float(actual_value) <= float(target_value)

        elif assertion_type == 'header_exists':
            actual_value = str(response.headers.get(target_value, ''))
            passed = target_value in response.headers

        elif assertion_type == 'header_equals':
            if ':' not in target_value:
                passed = False
                actual_value = "格式错误: header_equals 需要 'header_name:expected_value' 格式"
            else:
                header_name, expected_value = target_value.split(':', 1)
                actual_value = response.headers.get(header_name.strip(), '')
                passed = actual_value.strip() == expected_value.strip()

        else:
            # 处理未知的断言类型
            passed = False
            actual_value = f"未知的断言类型: {assertion_type}"

        return {
            'id': assertion_id,
            'type': assertion_type,
            'target_value': target_value,
            'actual_value': actual_value,
            'passed': passed,
        }

    except Exception as e:
        return {
            'id': assertion_id,
            'type': assertion_type,
            'target_value': target_value,
            'actual_value': f"验证失败: {str(e)}",
            'passed': False,
        }


async def execute_batch_async(requests_data, execution_mode='concurrent', max_concurrent=10):
    """
    异步批量执行API请求

    Args:
        requests_data: 请求数据列表
        execution_mode: 执行模式 ('concurrent', 'sequential', 'chain')
        max_concurrent: 最大并发数

    Returns:
        list: 执行结果列表
    """
    logger.info(f"开始批量执行，模式: {execution_mode}, 请求数量: {len(requests_data)}")

    if execution_mode == 'concurrent':
        # 并发执行，限制最大并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(request_data):
            async with semaphore:
                return await execute_single_request_async(request_data)

        tasks = [execute_with_semaphore(req) for req in requests_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    elif execution_mode == 'sequential':
        # 顺序执行
        results = []
        for request_data in requests_data:
            try:
                result = await execute_single_request_async(request_data)
                results.append(result)
            except Exception as e:
                logger.error(f"顺序执行失败: {str(e)}")
                results.append({'error': str(e), 'request': request_data})

    elif execution_mode == 'chain':
        # 链式执行，前一个请求的结果可能影响后一个请求
        results = []
        previous_result = None

        for request_data in requests_data:
            try:
                # 如果前一个请求成功，可以提取数据用于当前请求
                if previous_result and previous_result.get('all_assertions_passed'):
                    # 这里可以添加数据传递逻辑
                    pass

                result = await execute_single_request_async(request_data)
                results.append(result)
                previous_result = result

            except Exception as e:
                logger.error(f"链式执行失败: {str(e)}")
                results.append({'error': str(e), 'request': request_data})
                break

    else:
        raise ValueError(f"不支持的执行模式: {execution_mode}")

    logger.info(f"批量执行完成，成功: {len([r for r in results if not r.get('error')])}, 失败: {len([r for r in results if r.get('error')])}")
    return results



def validate_assertion_common(assertion_type, actual_value_getter, comparison, expected_value):
    """
    公共的断言验证逻辑（独立函数）

    参数:
        assertion_type: 断言类型（status_code, response_time等）
        actual_value_getter: 获取实际值的回调函数
        comparison: 比较方式（equals, contains等）
        expected_value: 期望值

    返回:
        bool: 验证是否通过
    """
    try:
        # 获取实际值
        actual_value = actual_value_getter()

        # 根据断言类型格式化实际值
        if assertion_type == 'status_code':
            actual = str(actual_value)
        elif assertion_type == 'response_time':
            actual = str(actual_value)
        elif assertion_type == 'response_body':
            actual = actual_value
        elif assertion_type == 'response_header':
            actual = actual_value
        else:
            logger.warning(f"Unknown assertion type: {assertion_type}")
            return False

        # 执行比较
        if comparison == 'equals':
            return actual == expected_value
        elif comparison == 'contains':
            return expected_value in actual
        elif comparison == 'not_contains':
            return expected_value not in actual
        elif comparison == 'greater_than':
            return float(actual) > float(expected_value)
        elif comparison == 'less_than':
            return float(actual) < float(expected_value)
        else:
            logger.warning(f"Unknown comparison type: {comparison}")
            return False

    except (ValueError, TypeError) as e:
        logger.warning(f"Assertion validation error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in assertion validation: {e}")
        return False


# 导出主要函数
__all__ = [
    'execute_single_request_async',
    'execute_batch_async',
    '_validate_assertion_async',
    'validate_assertion_common'
]