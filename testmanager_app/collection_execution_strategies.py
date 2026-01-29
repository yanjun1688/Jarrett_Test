"""
集合执行策略模块
提供请求集合的三种执行策略，统一接口和行为

设计原则：
- 策略模式：不同执行模式使用不同策略类
- 接口统一：所有策略实现相同的接口，返回统一格式的结果
- 错误处理：策略内部统一处理错误，返回标准化的错误结果
- 开闭原则：新增执行模式只需添加新策略类，无需修改核心代码
"""

import asyncio
import json  # 修复：添加json解析支持
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional

from jsonpath_ng import parse as jsonpath_parse
from asgiref.sync import sync_to_async

from testmanager_app.async_utils import execute_single_request_async
from testmanager_app.utils.template_renderer import TemplateRenderer  # 修复：添加模板渲染器
from django.utils import timezone

logger = logging.getLogger(__name__)


# 辅助函数：异步创建TestExecution记录
async def _create_test_execution_async(
    api_request,
    user,
    collection_exec,
    status,
    actual_result,
    executed_at=None
):
    """
    异步创建TestExecution记录
    
    Args:
        api_request: API请求对象
        user: 执行用户
        collection_exec: 集合执行记录
        status: 执行状态
        actual_result: 实际结果
        executed_at: 执行时间（可选）
    
    Returns:
        TestExecution: 创建的TestExecution对象
    """
    from testmanager_app.models import TestExecution
    
    def _create_execution_sync(api_req, exec_user, coll_exec, exec_status, result_text, exec_time):
        """同步函数：创建TestExecution记录"""
        return TestExecution.objects.create(
            test_type='api',
            api_request=api_req,
            collection_execution=coll_exec,
            executor=exec_user,
            status=exec_status,
            actual_result=result_text,
            executed_at=exec_time or timezone.now()
        )
    
    create_execution_async = sync_to_async(_create_execution_sync, thread_sensitive=True)
    return await create_execution_async(api_request, user, collection_exec, status, actual_result, executed_at)


# 辅助函数：统一处理 TestExecutionService.execute_single_api_request 的返回值
async def _process_execution_result(
    result,
    api_request,
    user,
    collection_exec,
    metadata=None
):
    """
    统一处理执行结果，将字典结果转换为TestExecution对象
    
    Args:
        result: TestExecutionService.execute_single_api_request 的返回值（字典或TestExecution对象）
        api_request: API请求对象
        user: 执行用户
        collection_exec: 集合执行记录
        metadata: 可选的元数据（用于日志）
    
    Returns:
        TestExecution: TestExecution对象
    """
    if isinstance(result, Exception):
        logger.error(f"Request execution failed with exception: {result}")
        return await _create_test_execution_async(
            api_request,
            user,
            collection_exec,
            'failed',
            f'执行失败: {str(result)}',
            timezone.now()
        )
    elif isinstance(result, dict):
        # TestExecutionService.execute_single_api_request 返回字典结果
        status = 'failed'
        actual_result = result.get('error_message', '执行完成')
        
        if not result.get('error_message'):
            passed_count = result.get('passed_count', 0)
            total_count = result.get('total_assertions', 0)
            if total_count > 0:
                status = 'passed' if passed_count == total_count else 'failed'
                actual_result = f"测试{'通过' if status == 'passed' else '失败'}: {passed_count}/{total_count} 断言通过"
            else:
                # 无断言，根据HTTP状态码判断
                status_code = result.get('response_status')
                if status_code and 200 <= status_code < 400:
                    status = 'passed'
                    actual_result = '请求成功'
        
        # 创建 TestExecution 记录
        execution = await _create_test_execution_async(
            api_request,
            user,
            collection_exec,
            status,
            actual_result,
            timezone.now()
        )
        
        # 更新执行记录的详细数据
        def _update_execution_data_sync(exec, result_data):
            """同步函数：更新执行记录的详细数据"""
            exec.api_response_data = {
                'status_code': result_data.get('response_status'),
                'response_time': result_data.get('response_time'),
                'response_body': result_data.get('response_body'),
                'assertion_results': result_data.get('assertions', []),
                'passed_count': result_data.get('passed_count', 0),
                'total_assertions': result_data.get('total_assertions', 0)
            }
            # 如果有日志，也保存
            if 'logs' in result_data:
                exec.api_logs = result_data['logs'] if isinstance(result_data['logs'], str) else '\n'.join(result_data['logs'])
            exec.save()
            return exec
        
        update_execution_async = sync_to_async(_update_execution_data_sync, thread_sensitive=True)
        return await update_execution_async(execution, result)
    elif hasattr(result, 'id'):
        # 如果返回的是 TestExecution 对象（向后兼容）
        execution = result
        # 使用 sync_to_async 包装 save 操作
        def _save_execution_sync(exec, coll_exec):
            exec.collection_execution = coll_exec
            exec.save()
            return exec
        
        save_execution_async = sync_to_async(_save_execution_sync, thread_sensitive=True)
        return await save_execution_async(execution, collection_exec)
    else:
        logger.error(f"Unexpected result format: {type(result)}")
        return await _create_test_execution_async(
            api_request,
            user,
            collection_exec,
            'failed',
            '结果格式错误',
            timezone.now()
        )


class CollectionExecutionStatus(Enum):
    """集合执行状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class CollectionExecutionStrategyInterface(ABC):
    """
    集合执行策略接口

    所有执行策略必须实现此接口，确保：
    - 统一的返回值格式
    - 统一的错误处理方式
    - 统一的日志记录
    """

    @abstractmethod
    def can_execute(self, execution_mode: str) -> bool:
        """
        检查策略是否支持给定的执行模式

        Args:
            execution_mode: 执行模式（concurrent、sequential、chain）

        Returns:
            bool: 是否支持该模式
        """
        pass

    @abstractmethod
    async def execute(
        self,
        collection_requests: List,
        user: Any = None,
        collection_exec: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行请求集合（统一接口）

        Args:
            collection_requests: 集合请求对象列表
            user: 执行用户（可选，用于创建TestExecution记录）
            collection_exec: 集合执行记录（可选）
            context: 上下文变量（仅 chain 模式使用）

        Returns:
            List[Dict[str, Any]]: 标准化的执行结果列表
            每个结果包含：
            - request_id: 请求ID
            - success: 是否成功
            - error: 错误信息（如果有）
            - response_status: HTTP状态码
            - response_time: 响应时间
            - response_body: 响应体
            - assertions: 断言结果列表
            - passed_count: 通过的断言数量
            - total_assertions: 断言总数
        """
        pass

    def _create_error_result(self, api_request_id: int, error_message: str) -> Dict[str, Any]:
        """
        创建标准化的错误结果（所有策略类必须实现）

        Args:
            request_id: 请求ID
            error_message: 错误信息

        Returns:
            Dict[str, Any]: 错误结果字典
        """
        return {
            'request_id': api_request_id,
            'success': False,
            'error': error_message,
            'status_code': None,
            'response_time': 0,
            'response_body': '',
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'execution_index': 0,
            'request_count': 1,
        }

    def execute_in_worker(
        self,
        collection_requests: List,
        user: Any = None,
        collection_exec: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List:
        """
        在 Celery worker 中执行（子类需要覆盖此方法）
        
        默认实现使用 asyncio.run() 调用异步 execute 方法。
        链式执行策略会覆盖此方法使用纯同步实现。
        """
        return asyncio.run(self.execute(collection_requests, user, collection_exec, context))


class ConcurrentExecutionStrategy(CollectionExecutionStrategyInterface):
    """并发执行策略（同时发起所有请求）"""

    def can_execute(self, execution_mode: str) -> bool:
        """支持 concurrent 模式"""
        return execution_mode == 'concurrent'

    async def execute(
        self,
        collection_requests: List,
        user: Any = None,
        collection_exec: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        并发执行所有请求（支持两种模式：简化测试模式和完整业务模式）

        Args:
            collection_requests: 集合请求列表
            user: 执行用户（可选，None时使用简化模式）
            collection_exec: 集合执行记录（可选）
            context: 不使用（为统一接口保留）

        Returns:
            List[Dict[str, Any]]: 如果user为None返回字典结果，否则返回TestExecution对象列表
        """
        total_requests = sum(getattr(req, 'request_count', 1) for req in collection_requests)
        logger.info(f"Concurrent execution: {len(collection_requests)} collection requests, {total_requests} total individual requests")

        # 简化测试模式（不创建TestExecution记录）
        if user is None:
            return await self._execute_simplified(collection_requests)

        # 完整业务模式（创建TestExecution记录）
        return await self._execute_full(collection_requests, user, collection_exec)

    async def _execute_simplified(self, collection_requests: List) -> List[Dict[str, Any]]:
        """简化测试模式 - 直接返回结果字典"""
        from testmanager_app.async_utils import execute_single_request_async

        tasks = []
        for coll_req in collection_requests:
            request_count = getattr(coll_req, 'request_count', 1)
            for i in range(request_count):
                # 渲染请求
                rendered_request = RequestRenderer().render(coll_req.api_request, {})
                # 执行请求
                task = execute_single_request_async(rendered_request)
                tasks.append(task)

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 格式化结果
        formatted_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append(self._create_error_result(
                    getattr(collection_requests[idx // request_count].api_request, 'id', 0),
                    str(result)
                ))
            else:
                formatted_results.append(result)

        return formatted_results

    async def _execute_full(self, collection_requests: List, user: Any, collection_exec: Any) -> List[Dict[str, Any]]:
        """完整业务模式 - 创建TestExecution记录
        
        修复：
        1. 直接使用 execute_single_request_async（纯异步函数），避免 sync_to_async 嵌套导致的 CurrentThreadExecutor 错误
        2. 实现真正的并发执行，而不是阻塞式执行
        3. 在结果处理时创建 TestExecution 记录
        """
        from testmanager_app.async_utils import execute_single_request_async

        tasks = []
        task_metadata = []

        for coll_req in collection_requests:
            request_count = getattr(coll_req, 'request_count', 1)
            for i in range(request_count):
                try:
                    # 渲染请求（处理模板变量）
                    rendered_request = RequestRenderer().render(coll_req.api_request, {})
                    # 直接使用纯异步函数，实现真正的并发
                    task = execute_single_request_async(rendered_request)
                    tasks.append(task)
                    task_metadata.append({
                        'request_id': coll_req.api_request.id,
                        'coll_req': coll_req,
                        'execution_index': i
                    })
                except Exception as e:
                    logger.error(f"Failed to prepare request {coll_req.id}: {e}")
                    error_execution = await _create_test_execution_async(
                        coll_req.api_request,
                        user,
                        collection_exec,
                        'failed',
                        f'准备失败: {str(e)}',
                        timezone.now()
                    )
                    task_metadata.append({
                        'request_id': coll_req.api_request.id,
                        'coll_req': coll_req,
                        'execution_index': i,
                        'execution': error_execution
                    })

        # 真正的并发执行（所有任务同时执行，不阻塞）
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        executions = []
        for idx, result in enumerate(raw_results):
            metadata = task_metadata[idx]
            # 使用统一的处理函数，将字典结果转换为 TestExecution 对象
            execution = await _process_execution_result(
                result,
                metadata['coll_req'].api_request,
                user,
                collection_exec,
                metadata
            )
            executions.append(execution)

        return executions


class ChainExecutionStrategy(CollectionExecutionStrategyInterface):
    """链式执行策略（顺序执行，支持变量传递）"""

    def can_execute(self, execution_mode: str) -> bool:
        """支持 chain 模式"""
        return execution_mode == 'chain'

    def execute_in_worker(
        self,
        collection_requests: List,
        user: Any = None,
        collection_exec: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List:
        """
        在 Celery worker 中执行（覆盖基类方法）
        
        链式执行使用纯同步实现，完全不涉及事件循环：
        - 使用 httpx.Client 同步发送请求
        - 支持变量提取和模板渲染
        - 支持失败即停
        """
        return self._execute_sync(collection_requests, user, collection_exec, context)

    async def execute(
        self,
        collection_requests: List,
        user: Any = None,
        collection_exec: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        链式执行请求（异步接口，内部使用同步实现）
        
        链式执行本质就是顺序执行，只是支持变量提取和模板渲染。
        使用同步实现可以避免 Django ORM 的异步保护异常。

        Args:
            collection_requests: 集合请求列表
            user: 执行用户（可选，None时使用简化模式）
            collection_exec: 集合执行记录（可选）
            context: 上下文变量（从上一个请求提取的变量）

        Returns:
            List[Dict[str, Any]]: 如果user为None返回字典结果，否则返回TestExecution对象列表
        """
        # 链式执行使用同步实现，通过 asyncio.to_thread 包装以避免阻塞
        return await asyncio.to_thread(
            self._execute_sync,
            collection_requests,
            user,
            collection_exec,
            context
        )
    
    def _execute_sync(
        self,
        collection_requests: List,
        user: Any = None,
        collection_exec: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        链式执行的同步实现（核心逻辑）
        
        使用同步方法执行，避免 Django ORM 的异步保护异常。
        链式执行本质就是顺序执行 + 变量提取。
        """
        total_requests = sum(getattr(req, 'request_count', 1) for req in collection_requests)
        logger.info(f"Chain execution: {len(collection_requests)} collection requests, {total_requests} total individual requests")

        # 简化测试模式（不创建TestExecution记录）
        if user is None:
            return self._execute_simplified_sync(collection_requests, context)

        # 完整业务模式（创建TestExecution记录）
        return self._execute_full_sync(collection_requests, user, collection_exec, context)

    def _execute_simplified_sync(self, collection_requests: List, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """简化测试模式 - 直接返回结果字典（纯同步实现，支持setup/teardown）"""
        from testmanager_app.async_utils import execute_single_request_sync

        if context is None:
            context = {}

        # 分离 setup、normal、teardown 请求
        setup_requests = [req for req in collection_requests if getattr(req, 'request_type', 'normal') == 'setup']
        normal_requests = [req for req in collection_requests if getattr(req, 'request_type', 'normal') == 'normal']
        teardown_requests = [req for req in collection_requests if getattr(req, 'request_type', 'normal') == 'teardown']

        executions = []
        request_renderer = RequestRenderer()

        # 1. 执行 Setup 请求
        if setup_requests:
            for coll_req in setup_requests:
                result = self._execute_single_request_simplified(coll_req, context, request_renderer)
                executions.append(result)
                if not result.get('success', False):
                    # Setup 失败，执行 teardown 后返回
                    if teardown_requests:
                        for teardown_req in teardown_requests:
                            self._execute_single_request_simplified(teardown_req, context, request_renderer)
                    return executions

        # 2. 执行正常请求
        for coll_req in normal_requests:
            request_count = getattr(coll_req, 'request_count', 1)

            # 渲染请求（替换模板变量）
            rendered_request = request_renderer.render(coll_req.api_request, context)

            last_successful_result = None

            for i in range(request_count):
                try:
                    # 使用同步 httpx 执行请求（完全不涉及事件循环）
                    result = execute_single_request_sync(rendered_request)
                    executions.append(result)

                    if result.get('success', False):
                        last_successful_result = result

                        if coll_req.stop_on_failure and i == 0:
                            break
                    else:
                        if coll_req.stop_on_failure:
                            break

                except Exception as e:
                    logger.error(f"Failed to execute request {coll_req.id}: {e}")
                    error_result = self._create_error_result(
                        getattr(coll_req.api_request, 'id', 0),
                        str(e)
                    )
                    executions.append(error_result)

                    if coll_req.stop_on_failure:
                        break

            # 提取变量并更新上下文
            result_to_extract = last_successful_result or (executions[-1] if executions else None)
            if result_to_extract and coll_req.extract_rules:
                new_context = self._extract_variables(result_to_extract, coll_req.extract_rules, context.copy())
                context.update(new_context)

            if coll_req.stop_on_failure and executions and not executions[-1].get('success', False):
                break

        return executions

    def _execute_single_request_simplified(self, coll_req, context: Dict[str, Any], request_renderer) -> Dict[str, Any]:
        """执行单个请求（简化模式，使用同步 httpx）"""
        from testmanager_app.async_utils import execute_single_request_sync
        
        try:
            # 渲染请求（替换模板变量）
            rendered_request = request_renderer.render(coll_req.api_request, context)
            # 使用同步 httpx 执行请求
            result = execute_single_request_sync(rendered_request)
            
            # 提取变量并更新上下文
            if result.get('success', False) and coll_req.extract_rules:
                new_context = self._extract_variables(result, coll_req.extract_rules, context.copy())
                context.update(new_context)
            
            return result
        except Exception as e:
            logger.error(f"Failed to execute request {coll_req.id}: {e}")
            return self._create_error_result(
                getattr(coll_req.api_request, 'id', 0),
                str(e)
            )

    def _execute_full_sync(self, collection_requests: List, user: Any, collection_exec: Any, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """完整业务模式 - 创建TestExecution记录（同步实现）
        
        链式执行使用同步实现：
        1. 使用 TestExecutionService.execute_single_api_request（同步方法）
        2. 直接使用 Django ORM，避免异步保护异常
        3. 顺序执行，支持变量提取和模板渲染
        4. 变量提取后自动断言验证，失败立即停止
        5. 完整链路日志记录
        6. 支持 setup/teardown 请求
        """
        from testmanager_app.services.execution_service import TestExecutionService

        if context is None:
            context = {}

        executions = []
        request_renderer = RequestRenderer()
        chain_logs = []  # 完整链路日志
        
        # 分离 setup、normal、teardown 请求
        setup_requests = [req for req in collection_requests if getattr(req, 'request_type', 'normal') == 'setup']
        normal_requests = [req for req in collection_requests if getattr(req, 'request_type', 'normal') == 'normal']
        teardown_requests = [req for req in collection_requests if getattr(req, 'request_type', 'normal') == 'teardown']
        
        # 记录链式执行开始
        chain_logs.append(f"[链式执行] ======== 开始执行链式请求集合 ========")
        chain_logs.append(f"[链式执行] Setup请求数: {len(setup_requests)}")
        chain_logs.append(f"[链式执行] 正常请求数: {len(normal_requests)}")
        chain_logs.append(f"[链式执行] Teardown请求数: {len(teardown_requests)}")
        chain_logs.append(f"[链式执行] 执行时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[Chain Execution] Starting chain execution: setup={len(setup_requests)}, normal={len(normal_requests)}, teardown={len(teardown_requests)}")

        # 1. 执行 Setup 请求
        if setup_requests:
            chain_logs.append(f"\n[链式执行] ======== 执行 Setup 请求 ========")
            setup_executions = self._execute_requests_sync(setup_requests, user, collection_exec, context, request_renderer, chain_logs, is_setup=True)
            executions.extend(setup_executions)
            
            # 检查 setup 是否失败
            if setup_executions and any(exec.status != 'passed' for exec in setup_executions if hasattr(exec, 'status')):
                chain_logs.append(f"[链式执行] ❌ Setup 失败，中止执行")
                logger.warning(f"[Chain Execution] Setup failed, aborting execution")
                # 即使 setup 失败，也执行 teardown
                if teardown_requests:
                    chain_logs.append(f"\n[链式执行] ======== 执行 Teardown 请求（Setup失败后） ========")
                    teardown_executions = self._execute_requests_sync(teardown_requests, user, collection_exec, context, request_renderer, chain_logs, is_teardown=True)
                    executions.extend(teardown_executions)
                return executions

        # 2. 执行正常请求
        chain_logs.append(f"\n[链式执行] ======== 执行正常请求 ========")
        normal_executions = self._execute_requests_sync(normal_requests, user, collection_exec, context, request_renderer, chain_logs, is_setup=False)
        executions.extend(normal_executions)
        all_passed = all(exec.status == 'passed' for exec in normal_executions if hasattr(exec, 'status'))

        # 3. 执行 Teardown 请求（无论正常请求成功或失败都会执行）
        if teardown_requests:
            chain_logs.append(f"\n[链式执行] ======== 执行 Teardown 请求 ========")
            teardown_executions = self._execute_requests_sync(teardown_requests, user, collection_exec, context, request_renderer, chain_logs, is_teardown=True)
            executions.extend(teardown_executions)

        chain_logs.append(f"\n[链式执行] ======== 链式执行完成 ========")
        chain_logs.append(f"[链式执行] 执行结果: {'✅ 通过' if all_passed else '❌ 失败'}")
        
        return executions

    def _execute_requests_sync(self, collection_requests: List, user: Any, collection_exec: Any, context: Dict[str, Any], 
                                request_renderer: Any, chain_logs: List[str], is_setup: bool = False, is_teardown: bool = False) -> List[Any]:
        """执行请求列表的通用方法（支持 setup/normal/teardown）"""
        from testmanager_app.services.execution_service import TestExecutionService
        from testmanager_app.models import TestExecution
        
        executions = []
        
        for req_idx, coll_req in enumerate(collection_requests, 1):
            request_count = getattr(coll_req, 'request_count', 1)
            
            # 记录当前请求信息
            chain_logs.append(f"\n[链式执行] ======== 执行第 {req_idx}/{len(collection_requests)} 个请求 ========")
            chain_logs.append(f"[链式执行] 请求名称: {coll_req.api_request.name}")
            chain_logs.append(f"[链式执行] 请求URL: {coll_req.api_request.url}")
            chain_logs.append(f"[链式执行] 请求方法: {coll_req.api_request.method}")
            if coll_req.extract_rules:
                chain_logs.append(f"[链式执行] 变量提取规则: {len(coll_req.extract_rules)} 条")
                for rule in coll_req.extract_rules:
                    chain_logs.append(f"[链式执行]   - {rule.get('name')}: {rule.get('jsonpath')}")
            logger.info(f"[Chain Execution] Executing request {req_idx}/{len(collection_requests)}: {coll_req.api_request.name}")

            last_successful_execution = None

            for i in range(request_count):
                # 每次执行前都重新渲染请求（使用最新的 context，支持变量传递）
                rendered_request_dict = request_renderer.render(coll_req.api_request, context)
                if context:
                    chain_logs.append(f"[链式执行] 当前上下文变量: {list(context.keys())}")
                try:
                    # 创建临时 ApiRequest 对象，使用渲染后的值
                    # 临时保存原始值
                    original_url = coll_req.api_request.url
                    original_headers = coll_req.api_request.headers
                    original_body = coll_req.api_request.body
                    
                    try:
                        # 临时更新模型对象的属性（使用渲染后的值）
                        coll_req.api_request.url = rendered_request_dict.get('url', original_url)
                        coll_req.api_request.headers = rendered_request_dict.get('headers', original_headers)
                        coll_req.api_request.body = rendered_request_dict.get('body', original_body)
                        
                        chain_logs.append(f"[链式执行] 执行请求 #{i+1}/{request_count}...")
                        
                        # 使用同步方法执行（直接调用，避免异步问题）
                        result = TestExecutionService.execute_single_api_request(
                            coll_req.api_request,
                            user
                        )
                    finally:
                        # 恢复原始值
                        coll_req.api_request.url = original_url
                        coll_req.api_request.headers = original_headers
                        coll_req.api_request.body = original_body

                    # execute_single_api_request 已经创建了 TestExecution 记录
                    # 我们需要找到它并更新 collection_execution 字段
                    from testmanager_app.models import TestExecution
                    
                    # 获取最新创建的 TestExecution 记录（按执行时间倒序，取第一个）
                    execution = TestExecution.objects.filter(
                        api_request=coll_req.api_request,
                        executor=user,
                        collection_execution__isnull=True  # 还没有设置 collection_execution 的记录
                    ).order_by('-executed_at').first()
                    
                    if execution:
                        # 更新 collection_execution 字段
                        execution.collection_execution = collection_exec
                        execution.save()
                    else:
                        # 如果找不到（理论上不应该发生），创建一个新的
                        status = 'failed'
                        actual_result = result.get('error_message', '执行完成')
                        
                        if not result.get('error_message'):
                            passed_count = result.get('passed_count', 0)
                            total_count = result.get('total_assertions', 0)
                            if total_count > 0:
                                status = 'passed' if passed_count == total_count else 'failed'
                                actual_result = f"测试{'通过' if status == 'passed' else '失败'}: {passed_count}/{total_count} 断言通过"
                            else:
                                status_code = result.get('response_status')
                                if status_code and 200 <= status_code < 400:
                                    status = 'passed'
                                    actual_result = '请求成功'
                        
                        # 注意：TestExecutionService.execute_single_api_request 会将整个 result 存储在 api_response_data 中
                        # 所以这里也应该使用 result 本身，而不是嵌套结构
                        execution = TestExecution.objects.create(
                            test_type='api',
                            api_request=coll_req.api_request,
                            collection_execution=collection_exec,
                            executor=user,
                            status=status,
                            actual_result=actual_result,
                            executed_at=timezone.now(),
                            api_response_data=result,  # 直接使用 result，与 TestExecutionService.execute_single_api_request 保持一致
                            api_logs=result.get('logs', '') if isinstance(result.get('logs'), str) else '\n'.join(result.get('logs', []))
                        )
                    
                    # 记录执行结果
                    chain_logs.append(f"[链式执行] 请求执行完成: status={execution.status}, response_status={result.get('response_status')}")
                    logger.info(f"[Chain Execution] Request {coll_req.id} execution #{i+1} completed, status={execution.status}")
                    executions.append(execution)

                    # 检查请求执行是否成功
                    # Setup 和 Teardown 请求失败时，根据 stop_on_failure 决定是否停止
                    # 正常请求失败时，总是停止（因为后续请求可能依赖这个请求的变量）
                    if execution.status != 'passed':
                        if is_setup:
                            chain_logs.append(f"[链式执行] ❌ Setup 请求执行失败")
                            logger.warning(f"[Chain Execution] Setup request {coll_req.id} failed")
                            if coll_req.stop_on_failure:
                                break
                        elif is_teardown:
                            chain_logs.append(f"[链式执行] ⚠️ Teardown 请求执行失败（继续执行其他 teardown）")
                            logger.warning(f"[Chain Execution] Teardown request {coll_req.id} failed")
                            # Teardown 失败不影响其他 teardown 的执行
                        else:
                            chain_logs.append(f"[链式执行] ❌ 请求执行失败，停止链式执行")
                            logger.warning(f"[Chain Execution] Request {coll_req.id} failed, stopping chain execution")
                            if coll_req.stop_on_failure:
                                break
                            # 即使 stop_on_failure=False，链式执行也应该在请求失败时停止（因为后续请求可能依赖这个请求的变量）
                            break

                    # 如果成功，记录为最后一次成功的执行
                    last_successful_execution = execution

                    # 提取变量并验证断言（链式执行必须验证变量提取）
                    if coll_req.extract_rules:
                        chain_logs.append(f"[链式执行] 开始提取变量（共 {len(coll_req.extract_rules)} 条规则）...")
                        # 从 execution.api_response_data 或 result 中获取响应数据
                        # execute_single_api_request 返回的 result 直接包含 response_body
                        # TestExecutionService.execute_single_api_request 会将整个 result 存储在 api_response_data 中
                        # 所以 execution.api_response_data 的结构就是 result 的结构
                        if execution.api_response_data and isinstance(execution.api_response_data, dict):
                            response_data = execution.api_response_data
                        else:
                            # 如果 api_response_data 不存在或格式不对，使用 result（这种情况不应该发生，但为了健壮性）
                            response_data = result
                        
                        logger.debug(f"[Chain Execution] Extracting variables from response_data: {response_data}")
                        logger.debug(f"[Chain Execution] Current context before extraction: {context}")
                        logger.debug(f"[Chain Execution] Response body: {response_data.get('response_body')}")
                        
                        # 重要：传入当前的 context（不是 copy），这样提取的变量会基于当前上下文
                        # 但为了安全性，我们在方法内部会创建副本
                        new_context, extraction_failed, extraction_logs = self._extract_and_assert_variables(
                            response_data,
                            coll_req.extract_rules,
                            context  # 传入原始 context，方法内部会创建副本
                        )
                        
                        logger.debug(f"[Chain Execution] New context after extraction: {new_context}")
                        logger.debug(f"[Chain Execution] Extraction failed: {extraction_failed}")
                        
                        # 添加提取日志
                        chain_logs.extend(extraction_logs)
                        
                        # 如果变量提取失败或断言失败，立即停止整个链式执行
                        if extraction_failed:
                            chain_logs.append(f"[链式执行] ❌ 变量提取或断言失败，立即停止链式执行")
                            logger.error(f"[Chain Execution] Variable extraction/assertion failed for request {coll_req.id}, stopping chain execution")
                            
                            # 更新执行记录状态为失败
                            execution.status = 'failed'
                            current_result = execution.actual_result or '执行完成'
                            execution.actual_result = f"{current_result}；变量提取或断言失败"
                            execution.save()
                            
                            # 立即停止整个链式执行（跳出所有循环）
                            break
                        
                        # 更新上下文：new_context 已经包含了所有变量（旧变量+新变量）
                        # 计算新提取的变量（用于日志）- 在更新 context 之前计算
                        old_context_keys = set(context.keys())
                        new_context_keys = set(new_context.keys())
                        new_vars = {k: new_context[k] for k in new_context_keys if k not in old_context_keys or context.get(k) != new_context[k]}
                        
                        # 直接使用 new_context 更新 context（确保所有变量都被更新）
                        # 重要：使用 clear() 和 update() 确保完全替换，而不是 merge
                        context.clear()
                        context.update(new_context)
                        
                        logger.debug(f"[Chain Execution] Context after update: {context}")
                        logger.info(f"[Chain Execution] Context keys: {list(context.keys())}, values: {list(context.values())}")
                        
                        if new_vars:
                            chain_logs.append(f"[链式执行] ✅ 变量提取成功，已提取变量: {list(new_vars.keys())}")
                            logger.info(f"[Chain Execution] Variables extracted successfully: {list(new_vars.keys())}")
                        else:
                            chain_logs.append(f"[链式执行] ✅ 变量提取成功（无新变量）")
                            logger.info(f"[Chain Execution] Variables extracted successfully (no new variables)")

                    if coll_req.stop_on_failure and i == 0:
                        break

                except Exception as e:
                    logger.error(f"Failed to execute request {coll_req.id}: {e}")
                    chain_logs.append(f"[链式执行] ❌ 执行异常: {str(e)}")

                    # 创建失败的 TestExecution 记录
                    from testmanager_app.models import TestExecution
                    execution = TestExecution.objects.create(
                        test_type='api',
                        api_request=coll_req.api_request,
                        collection_execution=collection_exec,
                        executor=user,
                        status='failed',
                        actual_result=f'执行失败: {str(e)}',
                        executed_at=timezone.now()
                    )
                    executions.append(execution)
                    chain_logs.append(f"[链式执行] ❌ 请求执行失败，停止链式执行")

                    # 链式执行中，任何异常都应该停止
                    break

            # 检查是否需要停止（基于最后一个执行结果）
            # 注意：变量提取发生在 coll_req 的 request_count 循环内部
            # 所以当第一个 coll_req 执行完成并提取变量后，context 已经更新
            # 第二个 coll_req 的渲染会使用更新后的 context
            if executions and executions[-1].status != 'passed':
                chain_logs.append(f"[链式执行] ======== 链式执行已停止（请求失败） ========")
                logger.warning(f"[Chain Execution] Chain execution stopped due to request failure")
                break
            
            # 记录当前 context 状态（用于调试）- 在 coll_req 循环结束后
            if context:
                chain_logs.append(f"[链式执行] 请求 {req_idx} 执行完成后的上下文: {context}")
                logger.info(f"[Chain Execution] Context after request {req_idx}: {context}")

        # 记录链式执行完成
        passed_count = sum(1 for e in executions if e.status == 'passed')
        failed_count = len(executions) - passed_count
        chain_logs.append(f"\n[链式执行] ======== 链式执行完成 ========")
        chain_logs.append(f"[链式执行] 总执行数: {len(executions)}")
        chain_logs.append(f"[链式执行] 通过: {passed_count}, 失败: {failed_count}")
        chain_logs.append(f"[链式执行] 完成时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[Chain Execution] Chain execution completed: {passed_count} passed, {failed_count} failed")

        # 将完整链路日志保存到 CollectionExecution
        if collection_exec:
            existing_output = collection_exec.output or ""
            chain_logs_text = "\n".join(chain_logs)
            collection_exec.output = f"{existing_output}\n\n{chain_logs_text}" if existing_output else chain_logs_text
            collection_exec.save()

        return executions

    def _extract_and_assert_variables(
        self,
        response_data: Dict[str, Any],
        extract_rules: List[Dict[str, str]],
        context: Dict[str, Any]
    ) -> tuple[Dict[str, Any], bool, List[str]]:
        """
        从 TestExecution 的 api_response_data 中提取变量并断言验证
        
        链式执行专用：提取变量后自动断言变量是否存在，失败则停止执行。

        Args:
            response_data: TestExecution 的 api_response_data
            extract_rules: 提取规则列表（包含 name、jsonpath）
            context: 当前上下文

        Returns:
            tuple: (提取的变量字典, 是否失败, 日志列表)
            - 如果变量提取失败或断言失败，返回 (context, True, logs)
            - 如果成功，返回 (new_context, False, logs)
        """
        logs = []
        
        if not extract_rules:
            return context, False, logs

        # 从 response_data 中获取响应体
        response_body = response_data.get('response_body', '{}')

        try:
            # 先解析 JSON 字符串，再使用 jsonpath
            response_json = json.loads(response_body)
        except Exception as e:
            logs.append(f"[链式执行] ❌ 响应体JSON解析失败: {str(e)}")
            logger.warning(f"Failed to parse response body for variable extraction: {e}")
            return context, True, logs  # 解析失败，返回失败标志

        new_context = context.copy()  # 在原始上下文中添加新变量
        all_extracted = True  # 是否所有变量都成功提取
        extracted_vars = {}  # 成功提取的变量

        for rule in extract_rules:
            try:
                name = rule.get('name')
                jsonpath_expr = rule.get('jsonpath')

                if not name or not jsonpath_expr:
                    logs.append(f"[链式执行] ⚠️ 提取规则缺少必要字段: name={name}, jsonpath={jsonpath_expr}")
                    all_extracted = False
                    continue

                expr = jsonpath_parse(jsonpath_expr)
                matches = [match.value for match in expr.find(response_json)]

                if matches:
                    extracted_value = matches[0]
                    logs.append(f"[链式执行] 📥 变量提取: {name} = {extracted_value}")
                    logger.info(f"Extracted variable: {name} = {extracted_value}")
                    
                    # 断言验证：检查变量值是否有效（不为 None、空字符串等）
                    if extracted_value is None:
                        logs.append(f"[链式执行] ❌ 变量断言失败: {name} 的值为 None")
                        logger.error(f"Variable assertion failed: {name} is None")
                        all_extracted = False
                    elif isinstance(extracted_value, str) and not extracted_value.strip():
                        logs.append(f"[链式执行] ❌ 变量断言失败: {name} 的值为空字符串")
                        logger.error(f"Variable assertion failed: {name} is empty string")
                        all_extracted = False
                    else:
                        # 断言通过，添加到成功提取的变量中
                        extracted_vars[name] = extracted_value
                        new_context[name] = extracted_value
                        logs.append(f"[链式执行] ✅ 变量断言通过: {name} 存在且有效")
                        logger.info(f"Variable assertion passed: {name} exists and is valid")
                else:
                    logs.append(f"[链式执行] ❌ 变量提取失败: {name} (JSONPath '{jsonpath_expr}' 未找到匹配值)")
                    logger.warning(f"jsonpath '{jsonpath_expr}' found no matches for variable {name}")
                    all_extracted = False

            except Exception as e:
                rule_name = rule.get('name', 'unknown') if isinstance(rule, dict) else 'unknown'
                logs.append(f"[链式执行] ❌ 变量提取异常: {rule_name} - {str(e)}")
                logger.error(f"Failed to extract variable {rule}: {e}")
                all_extracted = False

        # 如果所有变量都成功提取，返回成功；否则返回失败（不更新上下文）
        if all_extracted:
            logs.append(f"[链式执行] ✅ 所有变量提取和断言验证通过: {list(extracted_vars.keys())}")
            return new_context, False, logs
        else:
            logs.append(f"[链式执行] ❌ 变量提取或断言失败，不更新上下文")
            return context, True, logs  # 失败时返回原始上下文，不更新

    def _extract_variables_from_execution(
        self,
        response_data: Dict[str, Any],
        extract_rules: List[Dict[str, str]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从 TestExecution 的 api_response_data 中提取变量到上下文 - 修复版本
        
        注意：此方法不进行断言验证，仅用于向后兼容。
        链式执行应使用 _extract_and_assert_variables 方法。

        Args:
            response_data: TestExecution 的 api_response_data
            extract_rules: 提取规则列表（包含 name、jsonpath）
            context: 当前上下文

        Returns:
            Dict[str, Any]: 更新后的上下文（与旧上下文合并）
        """
        if not extract_rules:
            return context

        # 从 response_data 中获取响应体
        response_body = response_data.get('response_body', '{}')

        try:
            # 修复：先解析 JSON 字符串，再使用 jsonpath
            response_json = json.loads(response_body)
        except Exception as e:
            logger.warning(f"Failed to parse response body for variable extraction: {e}")
            return context

        new_context = context.copy()  # 在原始上下文中添加新变量

        for rule in extract_rules:
            try:
                name = rule.get('name')
                jsonpath_expr = rule.get('jsonpath')

                if not name or not jsonpath_expr:
                    continue

                expr = jsonpath_parse(jsonpath_expr)
                matches = [match.value for match in expr.find(response_json)]

                if matches:
                    new_context[name] = matches[0]
                    logger.info(f"Extracted variable: {name} = {matches[0]}")
                else:
                    logger.warning(f"jsonpath '{jsonpath_expr}' found no matches")

            except Exception as e:
                logger.error(f"Failed to extract variable {rule}: {e}")

        return new_context

    def _extract_variables(
        self,
        result: Dict[str, Any],
        extract_rules: List[Dict[str, str]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从响应中提取变量到上下文 - 修复版本

        Args:
            result: 请求执行结果（包含 response_body）
            extract_rules: 提取规则列表（包含 name、jsonpath）
            context: 当前上下文

        Returns:
            Dict[str, Any]: 更新后的上下文（与旧上下文合并）
        """
        if not extract_rules:
            return context

        # 从 result 中获取响应体
        response_body = result.get('response_body', '{}')

        try:
            # 修复：先解析 JSON 字符串，再使用 jsonpath
            response_json = json.loads(response_body)
        except Exception as e:
            logger.warning(f"Failed to parse response body for variable extraction: {e}")
            # 修复：返回原始上下文而不是抛出或返回空
            return context

        new_context = context.copy()  # 在原始上下文中添加新变量

        for rule in extract_rules:
            try:
                name = rule.get('name')
                jsonpath_expr = rule.get('jsonpath')

                if not name or not jsonpath_expr:
                    continue

                expr = jsonpath_parse(jsonpath_expr)
                matches = [match.value for match in expr.find(response_json)]

                if matches:
                    new_context[name] = matches[0]
                    logger.info(f"Extracted variable: {name} = {matches[0]}")
                else:
                    logger.warning(f"jsonpath '{jsonpath_expr}' found no matches")

            except Exception as e:
                logger.error(f"Failed to extract variable from rule {rule}: {e}")

        return new_context


class RequestRenderer:
    """请求渲染器（处理模板变量）"""

    def render(self, api_request, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染请求中的模板变量 - 修复版本，支持嵌套变量

        Args:
            api_request: API请求对象或字典
            context: 上下文变量

        Returns:
            Dict[str, Any]: 渲染后的请求字典
        """
        # 修复：使用 TemplateRenderer 支持嵌套变量
        if hasattr(api_request, 'id'):
            # 模型实例
            return {
                'id': api_request.id,
                'method': api_request.method,
                'url': TemplateRenderer.render(api_request.url, context),
                'headers': TemplateRenderer.render(api_request.headers, context),
                'body': TemplateRenderer.render(api_request.body, context),
            }
        else:
            # 已经是字典
            return {
                'id': api_request.get('id'),
                'method': api_request.get('method'),
                'url': TemplateRenderer.render(api_request.get('url', ''), context),
                'headers': TemplateRenderer.render(api_request.get('headers', '{}'), context),
                'body': TemplateRenderer.render(api_request.get('body', ''), context),
            }


class CollectionExecutionStrategyFactory:
    """
    集合执行策略工厂

    负责创建和管理集合执行策略实例，实现策略的注册和获取
    """

    _strategies = None  # 策略缓存

    @classmethod
    def _initialize_strategies(cls):
        """初始化所有策略实例"""
        if cls._strategies is None:
            cls._strategies = [
                ConcurrentExecutionStrategy(),
                ChainExecutionStrategy(),
            ]
            logger.info(f"初始化集合执行策略工厂，注册 {len(cls._strategies)} 个策略")

    @classmethod
    def get_strategy(cls, execution_mode: str) -> CollectionExecutionStrategyInterface:
        """
        获取适合指定执行模式的策略

        Args:
            execution_mode: 执行模式（concurrent、sequential、chain）

        Returns:
            CollectionExecutionStrategyInterface: 策略实例

        Raises:
            ValueError: 如果找不到支持该模式的策略
        """
        cls._initialize_strategies()

        for strategy in cls._strategies:
            if strategy.can_execute(execution_mode):
                logger.debug(f"找到策略: {strategy.__class__.__name__} 用于模式 {execution_mode}")
                return strategy

        raise ValueError(f"Unsupported execution mode: {execution_mode}")

    @classmethod
    def register_strategy(cls, strategy: CollectionExecutionStrategyInterface):
        """注册新的策略"""
        cls._initialize_strategies()
        cls._strategies.insert(0, strategy)
        logger.info(f"注册新策略: {strategy.__class__.__name__}")

    @classmethod
    def get_registered_strategies(cls) -> list:
        """获取所有已注册的策略"""
        cls._initialize_strategies()
        return cls._strategies.copy()
