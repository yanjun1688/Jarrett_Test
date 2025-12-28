"""
测试执行服务
处理所有测试执行相关的业务逻辑
"""

import logging
from django.core.exceptions import ValidationError
from django.utils import timezone
from testmanager_app.utils.log_formatter import ExecutionLogger
from testmanager_app.utils.async_helper import get_event_loop
from testmanager_app.async_utils import execute_single_request_async
import asyncio
logger = logging.getLogger(__name__)


class TestExecutionService:
    """
    测试执行服务类

    处理测试执行的核心逻辑，包括验证、执行、结果处理等
    """

    @staticmethod
    def execute_api_test(execution, user):
        """
        执行API测试

        Args:
            execution: TestExecution实例
            user: 当前用户

        Returns:
            dict: 执行结果，包含execution_id, status, logs, response_data

        Raises:
            ValidationError: 验证失败时抛出
            Exception: 执行过程中发生错误时抛出
        """

        # 1. 验证执行类型
        if execution.test_type != 'api' or not execution.api_request:
            raise ValidationError("该执行记录不是API测试类型")

        # 2. 创建日志管理器
        log_formatter = ExecutionLogger()
        log_formatter.add_start(execution.id, execution.api_request)

        # 3. 获取API请求对象
        api_request = execution.api_request

        # 4. 执行请求（使用全局事件循环）
        try:
            log_formatter.add_request_sent()

            # 使用全局事件循环执行异步请求
            loop = get_event_loop()
            result = loop.run_until_complete(
                execute_single_request_async(api_request)
            )

            log_formatter.add_request_completed()
        except Exception as e:
            logger.error(f"执行httpx请求异常: {str(e)}", exc_info=True)
            raise

        # 5. 处理结果
        is_passed, status, actual_result = TestExecutionService._process_result(result)

        # 6. 添加结果日志
        log_formatter.add_response(result)

        if result.get('assertions'):
            log_formatter.add_assertions(result['assertions'])

        passed_count = result.get('passed_count', 0)
        total_count = result.get('total_assertions', 0)
        log_formatter.add_assertion_summary(passed_count, total_count)
        log_formatter.add_test_result(is_passed, passed_count, total_count)
        log_formatter.add_completion()

        # 使用格式化工具生成易读的输出
        from testmanager_app.utils.collection_output_formatter import format_request_summary
        formatted_summary = format_request_summary(result)
        log_formatter.add_formatted_summary(formatted_summary)

        # 7. 更新执行记录
        execution.status = status
        execution.actual_result = actual_result
        execution.api_response_data = {
            'status_code': result.get('status_code'),
            'response_time': result.get('response_time'),
            'response_body': result.get('response_body'),
            'assertion_results': result.get('assertions'),
            'passed_count': passed_count,
            'total_assertions': total_count
        }
        execution.api_logs = log_formatter.get_logs_string()
        execution.executed_at = timezone.now()

        # 8. 保存
        execution.save()

        # 清除项目统计缓存（执行记录变化会影响统计）
        if execution.testcase and execution.testcase.project:
            from testmanager_app.utils.cache_helper import invalidate_project_statistics
            invalidate_project_statistics(execution.testcase.project.id)
        elif execution.api_request and execution.api_request.project:
            from testmanager_app.utils.cache_helper import invalidate_project_statistics
            invalidate_project_statistics(execution.api_request.project.id)

        logger.info(f"执行完成, 日志已保存, 共 {log_formatter.get_logs_count()} 条")

        # 9. 返回结果
        execution_duration_ms = None
        if execution.execution_duration:
            execution_duration_ms = execution.execution_duration.total_seconds() * 1000

        return {
            'execution_id': execution.id,
            'status': execution.status,
            'logs': log_formatter.get_logs_list(),
            'response_data': execution.api_response_data,
            'execution_duration_ms': execution_duration_ms
        }

    @staticmethod
    def _process_result(result):
        """
        处理执行结果

        Args:
            result: API执行结果

        Returns:
            tuple: (is_passed, status, actual_result)
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
    def execute_single_api_request(api_request, user):
        """
        执行单个API请求（提取自ApiRequestViewSet.execute的核心逻辑）

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
        from testmanager_app.models import TestExecution
        from testmanager_app.utils.async_helper import get_event_loop

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

            # 处理事件循环冲突 - 在测试环境中避免使用已运行的事件循环
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 如果已经有运行中的循环，创建新任务
                if loop.is_running():
                    # 创建新的事件循环用于执行
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(
                            execute_single_request_async(api_request)
                        )
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(loop)
                else:
                    result = loop.run_until_complete(
                        execute_single_request_async(api_request)
                    )
            except RuntimeError:
                # 没有运行中的事件循环，使用全局事件循环
                loop = get_event_loop()
                result = loop.run_until_complete(
                    execute_single_request_async(api_request)
                )

            logger.info(f"[Backend Info] httpx请求完成, response_status: {result.get('response_status')}")
            logs.append(f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 请求发送完成")

            # 计算执行时间
            end_time = timezone.now()

            # 更新日志
            if result.get('error_message'):
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 请求失败")
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 错误信息: {result['error_message']}")
                logger.warning(f"[Backend Warning] API请求失败: {result['error_message']}")
            else:
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ 收到响应")
                logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP状态码: {result['response_status']}")
                # 检查 response_time 是否为 None
                if result['response_time'] is not None:
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应时间: {result['response_time']:.4f} 秒")
                    logger.info(f"[Backend Info] 收到响应, status_code: {result['response_status']}, response_time: {result['response_time']:.4f}s")
                else:
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应时间: N/A")
                    logger.info(f"[Backend Info] 收到响应, status_code: {result['response_status']}, response_time: N/A")

                # 解析响应体
                try:
                    response_body = json.loads(result['response_body'])
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应体格式: JSON")
                    # 美化打印JSON格式
                    formatted_json = json.dumps(response_body, indent=2, ensure_ascii=False)
                    logs.append(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 响应体内容:\n{formatted_json}")
                except:
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
            actual_result = f"请求失败: {result['error_message']}"
            if not result.get('error_message'):
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
                executor=user,
                status=execution_status,
                actual_result=actual_result,
                executed_at=timezone.now(),
                execution_duration=end_time - start_time,
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
        from testmanager_app.models import ApiRequest, TestExecution
        from testmanager_app.async_utils import execute_single_request_async
        from django.utils import timezone
        import asyncio

        # 参数验证
        if not request_ids:
            raise ValidationError("request_ids is required")

        if len(request_ids) > 1000:
            raise ValidationError("Cannot execute more than 1000 requests in a batch")

        logger.info(f"Starting batch execution of {len(request_ids)} API requests (optimized concurrent mode with sync_to_async)")

        # 优化1: 批量预加载所有ApiRequest对象（使用 sync_to_async 包装同步ORM查询）
        from asgiref.sync import sync_to_async
        
        def _get_api_requests_sync(ids):
            """同步函数：批量获取ApiRequest对象"""
            return list(ApiRequest.objects.filter(id__in=ids).select_related('project').prefetch_related('assertions'))
        
        get_api_requests_async = sync_to_async(_get_api_requests_sync, thread_sensitive=True)
        api_requests_list = await get_api_requests_async(request_ids)
        
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
                actual_result = f"请求失败: {result.get('error_message', 'Unknown error')}"
                
                if not result.get('error_message'):
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
                
                if result.get('error_message'):
                    logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 请求失败: {result['error_message']}")
                else:
                    logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ✅ 收到响应")
                    logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] HTTP状态码: {result.get('response_status')}")
                    if result.get('response_time') is not None:
                        logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 响应时间: {result['response_time']:.4f} 秒")
                    
                    if result.get('assertions'):
                        passed_count = result.get('passed_count', 0)
                        total_count = result.get('total_assertions', 0)
                        logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 📊 断言统计: {passed_count}/{total_count} 通过")
                
                logs.append(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ======== 执行完成 ========")
                
                # 优化3: 使用 sync_to_async 包装同步ORM创建TestExecution记录
                from asgiref.sync import sync_to_async
                
                def _create_execution_sync(api_req, exec_user, status, result_text, exec_time, response_data, log_text):
                    """同步函数：创建TestExecution记录"""
                    return TestExecution.objects.create(
                        test_type='api',
                        api_request=api_req,
                        executor=exec_user,
                        status=status,
                        actual_result=result_text,
                        executed_at=exec_time,
                        api_response_data=response_data,
                        api_logs=log_text
                    )
                
                create_execution_async = sync_to_async(_create_execution_sync, thread_sensitive=True)
                await create_execution_async(
                    api_request, user, execution_status, actual_result, now, result, "\n".join(logs)
                )
                
                # 返回结果（添加request_id以便后续处理）
                result['request_id'] = req_id
                return result
                
            except Exception as e:
                logger.error(f"Failed to execute request {req_id}: {str(e)}", exc_info=True)
                # 使用 sync_to_async 包装同步ORM创建失败的执行记录
                try:
                    from asgiref.sync import sync_to_async
                    
                    def _create_failed_execution_sync(api_req, exec_user, error_msg):
                        """同步函数：创建失败的TestExecution记录"""
                        return TestExecution.objects.create(
                            test_type='api',
                            api_request=api_req,
                            executor=exec_user,
                            status='failed',
                            actual_result=f'执行失败: {error_msg}',
                            executed_at=timezone.now(),
                            api_logs=f"执行失败: {error_msg}"
                        )
                    
                    create_failed_execution_async = sync_to_async(_create_failed_execution_sync, thread_sensitive=True)
                    await create_failed_execution_async(api_request, user, str(e))
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
        final_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
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


