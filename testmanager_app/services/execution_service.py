"""
测试执行服务
处理所有测试执行相关的业务逻辑
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple, Optional
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
import asyncio

from testmanager_app.models import ApiRequest

logger = logging.getLogger(__name__)


class TestExecutionService:
    """
    测试执行服务类

    处理测试执行的核心逻辑，包括验证、执行、结果处理等
    """

    @staticmethod
    def _process_result(result: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        处理执行结果

        Args:
            result: API执行结果

        Returns:
            tuple[bool, str, str]: (is_passed, status, actual_result)
        """
        passed_count = result.get('passed_count', 0)
        total_count = result.get('total_assertions', 0)

        # 判断测试结果
        if result.get('error'):
            # 请求失败
            return False, 'failed', f"请求失败: {result['error']}"
        elif total_count > 0:
            # 有断言，根据断言结果判断
            if passed_count == total_count:
                return True, 'passed', f"测试通过: {passed_count}/{total_count} 断言通过"
            else:
                return False, 'failed', f"测试失败: {passed_count}/{total_count} 断言通过"
        else:
            # 无断言，请求成功即为通过
            return True, 'passed', "测试通过: 无断言配置"

    @staticmethod
    def execute_single_api_request(api_request: Any, user: Optional[User]) -> Dict[str, Any]:
        """
        执行单个API请求（用于请求集合内部调用）

        注意：此方法现在主要被请求集合执行策略调用。
        单个 API 请求的执行已改为 Celery 异步模式（execute_api_request_task）。

        Args:
            api_request: ApiRequest模型实例
            user: 当前用户

        Returns:
            dict: 执行结果

        Raises:
            Exception: 执行过程中发生错误时抛出
        """
        import json
        from django.utils import timezone
        from core.models import TestExecution

        logs = []

        # 记录开始时间
        start_time = timezone.now()
        logs.append(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] ======== 开始执行API测试 ========")
        logs.append(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] API名称: {api_request.name}")
        logs.append(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 请求URL: {api_request.url}")
        logs.append(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 请求方法: {api_request.method}")

        logger.info(f"[Backend Info] 开始执行API测试, url: {api_request.url}")

        try:
            logs.append(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 正在发送请求...")
            logger.info(f"[Backend Info] 正在通过httpx发送请求...")

            # 使用纯同步 httpx 执行请求（不使用 event loop）
            from testmanager_app.utils.sync_http_utils import execute_request_direct
            result = execute_request_direct(api_request)

            logger.info(f"[Backend Info] httpx请求完成, status_code: {result.get('status_code')}")
            logs.append(f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 请求发送完成")

            # 计算执行时间
            end_time = timezone.now()

            # 更新日志
            if result.get('error'):
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 请求失败")
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 错误信息: {result['error']}")
                logger.warning(f"[Backend Warning] API请求失败: {result['error']}")
            else:
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ 收到响应")
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP状态码: {result['status_code']}")
                # 检查 response_time 是否为 None
                if result['response_time'] is not None:
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应时间: {result['response_time']:.4f} 秒")
                    logger.info(f"[Backend Info] 收到响应, status_code: {result['status_code']}, response_time: {result['response_time']:.4f}s")
                else:
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应时间: N/A")
                    logger.info(f"[Backend Info] 收到响应, status_code: {result['status_code']}, response_time: N/A")

                # 解析响应体
                try:
                    raw_body = result['response_body']
                    if isinstance(raw_body, dict):
                        response_body = raw_body
                    else:
                        response_body = json.loads(raw_body)
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应体格式: JSON")
                    # 美化打印JSON格式
                    formatted_json = json.dumps(response_body, indent=2, ensure_ascii=False)
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应体内容:\n{formatted_json}")
                except (json.JSONDecodeError, ValueError, TypeError):
                    response_body = result['response_body']
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应体格式: 文本")
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应体内容:\n{response_body}")

                # 断言结果
                if result.get('assertions'):
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 开始验证断言...")
                    for assertion in result['assertions']:
                        status_str = "✅ 通过" if assertion['passed'] else "❌ 失败"
                        logs.append(f"  [{status_str}] 断言类型: {assertion['assertion_type']}")

                    logger.info(f"[Backend Info] 断言验证完成, 通过: {result.get('passed_count')}/{result.get('total_assertions')}")

                passed_count = result.get('passed_count', 0)
                total_count = result.get('total_assertions', 0)

                if total_count > 0:
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 📊 断言统计: {passed_count}/{total_count} 通过")

            logs.append(f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ======== 执行完成 ========")

            # 创建TestExecution记录（用于统计和日志查看）
            execution_status = 'failed'
            actual_result = f"请求失败: {result['error']}"
            if not result.get('error'):
                passed = result.get('passed_count', 0)
                total = result.get('total_assertions', 0)
                
                # 处理无断言的情况：如果没有断言，只要请求成功就视为通过
                if total == 0:
                    execution_status = 'passed'
                    actual_result = "测试通过: 请求成功（无断言配置）"
                else:
                    # 有断言时，需要所有断言都通过才算通过
                    execution_status = 'passed' if passed == total else 'failed'
                    actual_result = f"测试通过: {passed}/{total} 断言通过" if passed == total else f"测试失败: {passed}/{total} 断言通过"

            execution_record = TestExecution.objects.create(
                test_type='api',
                api_request=api_request,
                executed_by=user,
                status=execution_status,
                actual_result=actual_result,
                executed_at=timezone.now(),
                duration=(end_time - start_time).total_seconds(),
                api_response_data=result,
                api_logs="\n".join(logs)
            )
            
            # 清除项目统计缓存（执行记录变化会影响统计）
            if api_request.project:
                from testmanager_app.utils.cache_helper import invalidate_project_statistics
                invalidate_project_statistics(api_request.project.id)
            
            logger.info(f"[Backend] 已创建TestExecution记录并保存日志")

            logger.info(f"[Backend] 执行完成，准备返回结果")
            logger.info(f"[Backend] Result keys: {list(result.keys())}")
            logger.info(f"[Backend] Result: {result}")
            return result

        except Exception as e:
            logger.error(f"[Backend] 执行API请求失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def execute_batch_api_requests(request_ids, user):
        """
        批量执行API请求（优化版 - 真正的并发执行 + 异步ORM）

        性能优化：
        1. 批量预加载所有ApiRequest对象（一次异步查询，避免N+1问题）
        2. 真正的并发执行（使用asyncio.gather，而不是顺序执行）
        3. 直接使用异步ORM（避免sync_to_async的开销）
        4. 批量处理缓存失效（最后统一清除，而不是每个请求都清除）

        行为一致性：
        - 每个请求都会创建 TestExecution 记录（与 execute_single_api_request 一致）
        - 记录详细执行日志
        - 执行断言验证
        - 返回执行结果列表

        Args:
            request_ids: API请求ID列表
            user: 当前用户

        Returns:
            list: 包含每个请求的执行结果，按request_ids顺序返回

        Raises:
            ValidationError: 参数验证失败时抛出
        """
        from core.models import TestExecution
        from testmanager_app.models import ApiRequest
        from testmanager_app.utils.shared_async_utils import execute_single_request_async
        from django.utils import timezone
        import asyncio

        # 参数验证
        if not request_ids:
            raise ValidationError("request_ids is required")

        if len(request_ids) > 1000:
            raise ValidationError("Cannot execute more than 1000 requests in a batch")

        logger.info(f"Starting batch execution of {len(request_ids)} API requests (optimized concurrent mode with async ORM)")

        api_requests_list = []
        queryset = ApiRequest.objects.filter(id__in=request_ids).select_related('project').prefetch_related('assertions')
        async for req in queryset.aiterator():
            api_requests_list.append(req)
        
        # 创建ID到对象的映射，便于快速查找
        api_requests_dict = {req.id: req for req in api_requests_list}
        
        # 记录未找到的请求ID
        missing_ids = set(request_ids) - set(api_requests_dict.keys())
        if missing_ids:
            logger.warning(f"Missing API requests: {missing_ids}")

        # 优化2: 创建并发执行任务（真正的并发，而不是顺序执行）
        async def execute_single_with_logging(api_request, req_id):
            """执行单个请求并创建TestExecution记录"""
            try:
                # 优化3: 直接使用异步函数
                result = await execute_single_request_async(api_request)
                
                # 计算执行状态
                execution_status = 'failed'
                actual_result = f"请求失败: {result.get('error', 'Unknown error')}"
                
                if not result.get('error'):
                    passed = result.get('passed_count', 0)
                    total = result.get('total_assertions', 0)
                    execution_status = 'passed' if passed == total else 'failed'
                    actual_result = f"测试通过: {passed}/{total} 断言通过" if passed == total else f"测试失败: {passed}/{total} 断言通过"
                
                # 生成日志（简化版，避免过多日志影响性能）
                now = timezone.now()
                logs = [
                    f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ======== 开始执行API测试 ========",
                    f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] API名称: {api_request.name}",
                    f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 请求URL: {api_request.url}",
                    f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 请求方法: {api_request.method}",
                ]
                
                if result.get('error'):
                    logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 请求失败: {result['error']}")
                else:
                    logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ✅ 收到响应")
                    logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] HTTP状态码: {result.get('status_code')}")
                    if result.get('response_time') is not None:
                        logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 响应时间: {result['response_time']:.4f} 秒")
                    
                    if result.get('assertions'):
                        passed_count = result.get('passed_count', 0)
                        total_count = result.get('total_assertions', 0)
                        logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 📊 断言统计: {passed_count}/{total_count} 通过")
                
                logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ======== 执行完成 ========")
                
                await TestExecution.objects.acreate(
                    test_type='api',
                    api_request=api_request,
                    executed_by=user,
                    status=execution_status,
                    actual_result=actual_result,
                    executed_at=now,
                    api_response_data=result,
                    api_logs="\n".join(logs)
                )
                
                # 返回结果（添加request_id以便后续处理）
                result['request_id'] = req_id
                return result
                
            except Exception as e:
                logger.error(f"Failed to execute request {req_id}: {str(e)}", exc_info=True)
                try:
                    await TestExecution.objects.acreate(
                        test_type='api',
                        api_request=api_request,
                        executed_by=user,
                        status='failed',
                        actual_result=f'执行失败: {str(e)}',
                        executed_at=timezone.now(),
                        api_logs=f"执行失败: {str(e)}"
                    )
                except Exception as db_error:
                    logger.error(f"Failed to create execution record: {str(db_error)}")
                
                return {
                    'request_id': req_id,
                    'error': str(e),
                    'status_code': None,
                    'response_time': 0,
                    'response_body': '',
                    'assertions': [],
                    'passed_count': 0,
                    'total_assertions': 0,
                    'success': False
                }

        # 创建任务列表（只包含存在的请求）
        tasks = []
        
        async def create_error_result(req_id):
            """创建错误结果的协程"""
            return {
                'request_id': req_id,
                'error': 'ApiRequest not found',
                'status_code': None,
                'response_time': 0,
                'response_body': '',
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'success': False
            }
        
        for req_id in request_ids:
            if req_id in api_requests_dict:
                api_request = api_requests_dict[req_id]
                task = execute_single_with_logging(api_request, req_id)
                tasks.append(task)
            else:
                # 不存在的请求，创建错误结果
                tasks.append(create_error_result(req_id))

        # 优化2: 真正的并发执行（所有请求同时执行）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        final_results: List[Dict[str, Any]] = []
        for idx, result in enumerate(results):
            if isinstance(result, BaseException):
                req_id = request_ids[idx] if idx < len(request_ids) else None
                logger.error(f"Request {req_id} failed with exception: {str(result)}", exc_info=True)
                final_results.append({
                    'request_id': req_id,
                    'error': str(result),
                    'status_code': None,
                    'response_time': 0,
                    'response_body': '',
                    'assertions': [],
                    'passed_count': 0,
                    'total_assertions': 0,
                    'success': False
                })
            else:
                final_results.append(result)

        # 优化4: 批量处理缓存失效（最后统一清除，而不是每个请求都清除）
        # 收集所有涉及的项目ID
        project_ids = set()
        for req_id in request_ids:
            if req_id in api_requests_dict:
                api_request = api_requests_dict[req_id]
                if api_request.project_id:  # 使用project_id避免额外查询
                    project_ids.add(api_request.project_id)
        
        # 批量清除项目统计缓存（使用 sync_to_async 包装同步操作）
        if project_ids:
            from testmanager_app.utils.cache_helper import invalidate_project_statistics
            from asgiref.sync import sync_to_async
            
            # 将同步的缓存操作包装为异步
            async_invalidate = sync_to_async(invalidate_project_statistics, thread_sensitive=True)
            for pid in project_ids:
                await async_invalidate(pid)

        logger.info(f"Batch execution completed with {len(final_results)} results (concurrent mode with async ORM)")
        return final_results


