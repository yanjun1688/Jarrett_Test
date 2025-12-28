"""
主测试文件 - 单元测试与集成测试

测试范围：
1. TestExecution 模型 - collection_execution 外键关联
2. 集合执行策略 - ConcurrentExecutionStrategy, SequentialExecutionStrategy, ChainExecutionStrategy
3. RequestCollectionViewSet - execute 方法
4. TestExecutionService - execute_single_api_request 方法
5. 集成测试 - 完整执行流程

测试类型：
- 单元测试：测试单个组件的独立功能
- 集成测试：测试多个组件协同工作的流程
"""

import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework import status


from testmanager_app.models import (
    Project,
    Module,
    TestCase,
    TestExecution,
    ApiRequest,
    CollectionExecution,
    RequestCollection,
    CollectionRequest
)
from testmanager_app.collection_execution_strategies import (
    CollectionExecutionStrategyFactory,
    ConcurrentExecutionStrategy,
    SequentialExecutionStrategy,
    ChainExecutionStrategy
)
from testmanager_app.services.execution_service import TestExecutionService
from testmanager_app.views import RequestCollectionViewSet
from testmanager_app.async_utils import execute_single_request_async


# =============================================================================
# 单元测试 - TestExecution 模型
# =============================================================================

class TestExecutionTests(TestCase):
    """TestExecution 模型单元测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')
        self.module = Module.objects.create(
            project=self.project,
            name='Test Module'
        )
        self.testcase = TestCase.objects.create(
            project=self.project,
            module=self.module,
            title='Test Case',
            steps='Test steps',
            expected_result='Expected result'
        )
        self.api_request = ApiRequest.objects.create(
            project=self.project,
            name='API Test',
            method='GET',
            url='https://api.example.com/test'
        )

    def test_test_execution_creation_without_collection(self):
        """测试创建不带 collection_execution 的 TestExecution"""
        execution = TestExecution.objects.create(
            test_type='api',
            api_request=self.api_request,
            executor=self.user,
            status='passed',
            actual_result='Test passed'
        )

        self.assertIsNotNone(execution.id)
        self.assertIsNone(execution.collection_execution)
        self.assertEqual(execution.test_type, 'api')
        self.assertEqual(execution.status, 'passed')

    def test_test_execution_creation_with_collection(self):
        """测试创建带 collection_execution 的 TestExecution"""
        collection = RequestCollection.objects.create(
            project=self.project,
            name='Test Collection',
            execution_mode='concurrent'
        )
        collection_exec = CollectionExecution.objects.create(
            collection=collection,
            executor=self.user,
            status='success'
        )

        execution = TestExecution.objects.create(
            test_type='api',
            api_request=self.api_request,
            collection_execution=collection_exec,
            executor=self.user,
            status='passed',
            actual_result='Test passed'
        )

        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.collection_execution, collection_exec)
        self.assertIn(execution, collection_exec.api_executions.all())

    def test_collection_execution_reverse_relation(self):
        """测试 CollectionExecution 反向查询关联的 TestExecution"""
        collection = RequestCollection.objects.create(
            project=self.project,
            name='Test Collection',
            execution_mode='concurrent'
        )
        collection_exec = CollectionExecution.objects.create(
            collection=collection,
            executor=self.user,
            status='success'
        )

        # 创建多个 TestExecution
        for i in range(3):
            api_req = ApiRequest.objects.create(
                project=self.project,
                name=f'API {i}',
                method='GET',
                url='https://api.example.com/test'
            )
            TestExecution.objects.create(
                test_type='api',
                api_request=api_req,
                collection_execution=collection_exec,
                executor=self.user,
                status='passed'
            )

        # 验证反向查询
        self.assertEqual(collection_exec.api_executions.count(), 3)
        self.assertEqual(collection_exec.passed_requests, 0)  # 字段需要手动更新

    def test_test_execution_filter_by_collection(self):
        """测试通过 collection_execution 过滤 TestExecution"""
        collection1 = RequestCollection.objects.create(
            project=self.project,
            name='Collection 1',
            execution_mode='concurrent'
        )
        collection2 = RequestCollection.objects.create(
            project=self.project,
            name='Collection 2',
            execution_mode='sequential'
        )

        exec1 = CollectionExecution.objects.create(
            collection=collection1,
            executor=self.user,
            status='success'
        )
        exec2 = CollectionExecution.objects.create(
            collection=collection2,
            executor=self.user,
            status='success'
        )

        # 为每个集合创建 TestExecution
        TestExecution.objects.create(
            test_type='api',
            api_request=self.api_request,
            collection_execution=exec1,
            executor=self.user,
            status='passed'
        )

        api_req2 = ApiRequest.objects.create(
            project=self.project,
            name='API 2',
            method='POST',
            url='https://api.example.com/test2'
        )
        TestExecution.objects.create(
            test_type='api',
            api_request=api_req2,
            collection_execution=exec2,
            executor=self.user,
            status='failed'
        )

        # 验证过滤
        self.assertEqual(
            TestExecution.objects.filter(collection_execution=exec1).count(),
            1
        )
        self.assertEqual(
            TestExecution.objects.filter(collection_execution=exec2).count(),
            1
        )


# =============================================================================
# 单元测试 - 集合执行策略
# =============================================================================

class CollectionExecutionStrategyFactoryTest(TestCase):
    """集合执行策略工厂单元测试"""

    def test_get_concurrent_strategy(self):
        """测试获取并发策略"""
        strategy = CollectionExecutionStrategyFactory.get_strategy('concurrent')
        self.assertIsInstance(strategy, ConcurrentExecutionStrategy)

    def test_get_sequential_strategy(self):
        """测试获取顺序策略"""
        strategy = CollectionExecutionStrategyFactory.get_strategy('sequential')
        self.assertIsInstance(strategy, SequentialExecutionStrategy)

    def test_get_chain_strategy(self):
        """测试获取链式策略"""
        strategy = CollectionExecutionStrategyFactory.get_strategy('chain')
        self.assertIsInstance(strategy, ChainExecutionStrategy)

    def test_unsupported_strategy(self):
        """测试不支持的模式"""
        with self.assertRaises(ValueError):
            CollectionExecutionStrategyFactory.get_strategy('invalid_mode')


class ConcurrentExecutionStrategyTest(TestCase):
    """并发执行策略单元测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')

        # 创建 API 请求
        self.api_requests = []
        for i in range(3):
            api_req = ApiRequest.objects.create(
                project=self.project,
                name=f'API {i}',
                method='GET',
                url=f'https://api.example.com/test{i}'
            )
            self.api_requests.append(api_req)

        # 创建集合
        self.collection = RequestCollection.objects.create(
            project=self.project,
            name='Test Collection',
            execution_mode='concurrent'
        )

        # 创建 CollectionRequest
        self.collection_requests = []
        for i, api_req in enumerate(self.api_requests):
            coll_req = CollectionRequest.objects.create(
                collection=self.collection,
                api_request=api_req,
                order_index=i
            )
            self.collection_requests.append(coll_req)

        # 创建 CollectionExecution
        self.collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.user,
            status='pending'
        )

    @patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request')
    def test_execute_concurrent_creates_test_executions(self, mock_execute):
        """测试并发执行创建 TestExecution 记录"""
        # 预创建 TestExecution 对象
        pre_created_executions = []
        for api_req in self.api_requests:
            execution = TestExecution.objects.create(
                test_type='api',
                api_request=api_req,
                executor=self.user,
                status='passed',
                actual_result='Test passed'
            )
            pre_created_executions.append(execution)

        # Mock execute_single_api_request 返回预创建的对象
        mock_execute.side_effect = pre_created_executions

        strategy = ConcurrentExecutionStrategy()

        # 执行（使用 async_to_sync 包装）
        from asgiref.sync import async_to_sync
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            self.collection_exec
        )

        # 验证
        self.assertEqual(len(executions), 3)
        self.assertEqual(mock_execute.call_count, 3)

        # 验证所有 TestExecution 都关联了 collection_execution
        for execution in executions:
            self.assertEqual(execution.collection_execution, self.collection_exec)
            self.assertEqual(execution.status, 'passed')

        # 验证数据库中记录数
        self.assertEqual(
            TestExecution.objects.filter(collection_execution=self.collection_exec).count(),
            3
        )

    @patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request')
    def test_execute_concurrent_with_failures(self, mock_execute):
        """测试并发执行包含失败情况"""
        # 预创建 TestExecution 对象（第二个失败）
        pre_created_executions = []
        for idx, api_req in enumerate(self.api_requests):
            status = 'failed' if idx == 1 else 'passed'
            result = 'Test failed' if idx == 1 else 'Test passed'
            execution = TestExecution.objects.create(
                test_type='api',
                api_request=api_req,
                executor=self.user,
                status=status,
                actual_result=result
            )
            pre_created_executions.append(execution)

        # Mock 返回预创建的对象
        mock_execute.side_effect = pre_created_executions

        strategy = ConcurrentExecutionStrategy()

        from asgiref.sync import async_to_sync
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            self.collection_exec
        )

        # 验证结果
        self.assertEqual(len(executions), 3)
        passed_count = sum(1 for e in executions if e.status == 'passed')
        failed_count = sum(1 for e in executions if e.status == 'failed')
        self.assertEqual(passed_count, 2)
        self.assertEqual(failed_count, 1)


class SequentialExecutionStrategyTest(TestCase):
    """顺序执行策略单元测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')

        self.api_requests = []
        for i in range(3):
            api_req = ApiRequest.objects.create(
                project=self.project,
                name=f'API {i}',
                method='GET',
                url=f'https://api.example.com/test{i}'
            )
            self.api_requests.append(api_req)

        self.collection = RequestCollection.objects.create(
            project=self.project,
            name='Test Collection',
            execution_mode='sequential'
        )

        self.collection_requests = []
        for i, api_req in enumerate(self.api_requests):
            coll_req = CollectionRequest.objects.create(
                collection=self.collection,
                api_request=api_req,
                order_index=i,
                stop_on_failure=True  # 第一次失败就停止
            )
            self.collection_requests.append(coll_req)

        self.collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.user,
            status='pending'
        )

    @patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request')
    def test_execute_sequential_with_stop_on_failure(self, mock_execute):
        """测试顺序执行并在失败时停止"""
        # 预创建 TestExecution 对象（第二个失败）
        pre_created_executions = []
        for idx, api_req in enumerate(self.api_requests):
            status = 'failed' if idx == 1 else 'passed'
            result = 'Test failed' if idx == 1 else 'Test passed'
            execution = TestExecution.objects.create(
                test_type='api',
                api_request=api_req,
                executor=self.user,
                status=status,
                actual_result=result
            )
            pre_created_executions.append(execution)

        # Mock 返回预创建的对象
        mock_execute.side_effect = pre_created_executions

        strategy = SequentialExecutionStrategy()

        from asgiref.sync import async_to_sync
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            self.collection_exec
        )

        # 验证只有前两个请求被执行（第二个失败后停止）
        self.assertEqual(len(executions), 2)
        self.assertEqual(mock_execute.call_count, 2)

    @patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request')
    def test_execute_sequential_without_stop_on_failure(self, mock_execute):
        """测试顺序执行不停止"""
        # 修改 stop_on_failure
        for cr in self.collection_requests:
            cr.stop_on_failure = False
            cr.save()

        # 预创建 TestExecution 对象（第二个失败）
        pre_created_executions = []
        for idx, api_req in enumerate(self.api_requests):
            status = 'failed' if idx == 1 else 'passed'
            result = 'Test failed' if idx == 1 else 'Test passed'
            execution = TestExecution.objects.create(
                test_type='api',
                api_request=api_req,
                executor=self.user,
                status=status,
                actual_result=result
            )
            pre_created_executions.append(execution)

        # Mock 返回预创建的对象
        mock_execute.side_effect = pre_created_executions

        strategy = SequentialExecutionStrategy()

        from asgiref.sync import async_to_sync
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            self.collection_exec
        )

        # 验证所有请求都执行了
        self.assertEqual(len(executions), 3)
        self.assertEqual(mock_execute.call_count, 3)


class ChainExecutionStrategyTest(TestCase):
    """链式执行策略单元测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')

        self.api_requests = []
        for i in range(3):
            api_req = ApiRequest.objects.create(
                project=self.project,
                name=f'API {i}',
                method='GET',
                url=f'https://api.example.com/test{i}'
            )
            self.api_requests.append(api_req)

        self.collection = RequestCollection.objects.create(
            project=self.project,
            name='Test Collection',
            execution_mode='chain'
        )

        self.collection_requests = []
        for i, api_req in enumerate(self.api_requests):
            coll_req = CollectionRequest.objects.create(
                collection=self.collection,
                api_request=api_req,
                order_index=i
            )
            self.collection_requests.append(coll_req)

        self.collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.user,
            status='pending'
        )

    @patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request')
    def test_execute_chain_with_variable_extraction(self, mock_execute):
        """测试链式执行带变量提取"""
        # 预创建 TestExecution 对象
        pre_created_executions = []
        for i, api_req in enumerate(self.api_requests):
            # 第一个请求有变量数据
            if i == 0:
                execution = TestExecution.objects.create(
                    test_type='api',
                    api_request=api_req,
                    executor=self.user,
                    status='passed',
                    actual_result='Test passed'
                )
                execution.api_response_data = {
                    'response_body': json.dumps({'token': f'token_{api_req.id}', 'user_id': 123})
                }
                execution.save()
            else:
                execution = TestExecution.objects.create(
                    test_type='api',
                    api_request=api_req,
                    executor=self.user,
                    status='passed',
                    actual_result='Test passed'
                )
            pre_created_executions.append(execution)

        # Mock 返回预创建的对象
        mock_execute.side_effect = pre_created_executions

        # 为第一个请求添加提取规则
        self.collection_requests[0].extract_rules = [
            {'name': 'token', 'jsonpath': '$.token'},
            {'name': 'user_id', 'jsonpath': '$.user_id'}
        ]
        self.collection_requests[0].save()

        strategy = ChainExecutionStrategy()

        from asgiref.sync import async_to_sync
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            self.collection_exec
        )

        # 验证所有请求都执行了
        self.assertEqual(len(executions), 3)

        # 验证所有 TestExecution 都关联了 collection_execution
        for execution in executions:
            self.assertEqual(execution.collection_execution, self.collection_exec)


# =============================================================================
# 单元测试 - TestExecutionService
# =============================================================================

class TestExecutionServiceTest(TestCase):
    """TestExecutionService 单元测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')
        self.api_request = ApiRequest.objects.create(
            project=self.project,
            name='API Test',
            method='GET',
            url='https://api.example.com/test'
        )

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_execute_single_api_request_creates_test_execution(self, mock_execute_async):
        """测试执行单个API请求创建TestExecution记录"""
        # Mock 异步执行结果
        mock_execute_async.return_value = {
            'api_request_id': self.api_request.id,
            'request_method': 'GET',
            'request_url': 'https://api.example.com/test',
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"status": "success"}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'success': True
        }

        result = TestExecutionService.execute_single_api_request(
            self.api_request,
            self.user
        )

        # 验证返回结果
        self.assertIsNotNone(result)
        self.assertEqual(result['response_status'], 200)

        # 验证创建了 TestExecution 记录
        execution = TestExecution.objects.get(api_request=self.api_request)
        self.assertEqual(execution.executor, self.user)
        self.assertEqual(execution.status, 'passed')
        self.assertEqual(execution.test_type, 'api')
        self.assertIsNotNone(execution.api_logs)
        self.assertIsNotNone(execution.api_response_data)

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_execute_single_api_request_with_assertions(self, mock_execute_async):
        """测试执行API请求带断言验证"""
        mock_execute_async.return_value = {
            'api_request_id': self.api_request.id,
            'request_method': 'GET',
            'request_url': 'https://api.example.com/test',
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"status": "success", "data": {"user_id": 123}}',
            'error_message': None,
            'assertions': [
                {'id': 1, 'type': 'status_code', 'target_value': '200', 'actual_value': '200', 'passed': True},
                {'id': 2, 'type': 'contains', 'target_value': 'success', 'actual_value': '{"status": "success"...', 'passed': True}
            ],
            'passed_count': 2,
            'total_assertions': 2,
            'all_assertions_passed': True,
            'success': True
        }

        TestExecutionService.execute_single_api_request(self.api_request, self.user)

        execution = TestExecution.objects.get(api_request=self.api_request)
        self.assertEqual(execution.status, 'passed')
        self.assertIn('2/2 断言通过', execution.actual_result)

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_execute_single_api_request_failure(self, mock_execute_async):
        """测试API请求执行失败"""
        mock_execute_async.return_value = {
            'api_request_id': self.api_request.id,
            'request_method': 'GET',
            'request_url': 'https://api.example.com/test',
            'response_status': None,
            'response_time': None,
            'response_body': '',
            'error_message': 'Connection timeout',
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'success': False
        }

        TestExecutionService.execute_single_api_request(self.api_request, self.user)

        execution = TestExecution.objects.get(api_request=self.api_request)
        self.assertEqual(execution.status, 'failed')
        self.assertIn('请求失败', execution.actual_result)
        self.assertIn('Connection timeout', execution.api_logs)


# =============================================================================
# 集成测试 - 完整执行流程
# =============================================================================

class CollectionExecutionIntegrationTest(TransactionTestCase):
    """集合执行集成测试"""

    def setUp(self):
        """设置完整的测试环境"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')

        # 创建多个 API 请求
        self.api_requests = []
        for i in range(3):
            api_req = ApiRequest.objects.create(
                project=self.project,
                name=f'API {i}',
                method='GET',
                url=f'https://api.example.com/test{i}'
            )
            self.api_requests.append(api_req)

        # 创建请求集合
        self.collection = RequestCollection.objects.create(
            project=self.project,
            name='Integration Test Collection',
            execution_mode='concurrent'
        )

        # 添加请求到集合
        self.collection_requests = []
        for i, api_req in enumerate(self.api_requests):
            coll_req = CollectionRequest.objects.create(
                collection=self.collection,
                api_request=api_req,
                order_index=i
            )
            self.collection_requests.append(coll_req)

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_full_collection_execution_workflow(self, mock_execute_async):
        """测试完整的集合执行工作流"""
        # Mock HTTP 请求执行
        def mock_execute(api_request):
            return {
                'api_request_id': api_request.id,
                'request_method': api_request.method,
                'request_url': api_request.url,
                'response_status': 200,
                'response_time': 0.5,
                'response_body': '{"status": "success"}',
                'error_message': None,
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'success': True
            }

        mock_execute_async.side_effect = mock_execute

        # 执行集合（模拟视图调用）
        from asgiref.sync import async_to_sync
        from testmanager_app.collection_execution_strategies import (
            CollectionExecutionStrategyFactory
        )

        collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.user,
            status='pending'
        )

        strategy = CollectionExecutionStrategyFactory.get_strategy('concurrent')

        # 执行集合
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            collection_exec
        )

        # 验证集成结果
        self.assertEqual(len(executions), 3)

        # 更新 CollectionExecution 统计
        passed_count = sum(1 for e in executions if e.status == 'passed')
        collection_exec.passed_requests = passed_count
        collection_exec.failed_requests = len(executions) - passed_count
        collection_exec.status = 'success'
        collection_exec.save()

        # 验证数据库状态
        self.assertEqual(
            TestExecution.objects.filter(collection_execution=collection_exec).count(),
            3
        )
        self.assertEqual(
            collection_exec.passed_requests,
            3
        )

        # 验证每个 TestExecution 的数据完整性
        for execution in executions:
            self.assertEqual(execution.test_type, 'api')
            self.assertIsNotNone(execution.executor)
            self.assertIsNotNone(execution.executed_at)
            self.assertIsNotNone(execution.api_logs)
            self.assertIsNotNone(execution.api_response_data)

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_mixed_success_and_failure_workflow(self, mock_execute_async):
        """测试混合成功和失败的执行流程"""
        def mock_execute(api_request):
            # 第二个请求失败，其他成功
            if 'API 1' in api_request.name:
                return {
                    'api_request_id': api_request.id,
                    'request_method': api_request.method,
                    'request_url': api_request.url,
                    'response_status': 500,
                    'response_time': 0.5,
                    'response_body': '{"error": "Internal Server Error"}',
                    'error_message': None,
                    'assertions': [],
                    'passed_count': 0,
                    'total_assertions': 0,
                    'success': False
                }
            return {
                'api_request_id': api_request.id,
                'request_method': api_request.method,
                'request_url': api_request.url,
                'response_status': 200,
                'response_time': 0.5,
                'response_body': '{"status": "success"}',
                'error_message': None,
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'success': True
            }

        mock_execute_async.side_effect = mock_execute

        from asgiref.sync import async_to_sync
        from testmanager_app.collection_execution_strategies import (
            CollectionExecutionStrategyFactory
        )

        collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.user,
            status='pending'
        )

        # 并发执行
        strategy = CollectionExecutionStrategyFactory.get_strategy('concurrent')
        executions = async_to_sync(strategy.execute)(
            self.collection_requests,
            self.user,
            collection_exec
        )

        # 更新统计
        passed_count = sum(1 for e in executions if e.status == 'passed')
        collection_exec.passed_requests = passed_count
        collection_exec.failed_requests = len(executions) - passed_count
        collection_exec.status = 'failed' if passed_count < len(executions) else 'success'
        collection_exec.save()

        # 验证混合结果
        self.assertEqual(len(executions), 3)
        self.assertEqual(passed_count, 2)
        self.assertEqual(collection_exec.failed_requests, 1)
        self.assertEqual(collection_exec.status, 'failed')


class ApiExecutionIntegrationTest(TransactionTestCase):
    """API 执行集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')
        self.api_request = ApiRequest.objects.create(
            project=self.project,
            name='API Test',
            method='POST',
            url='https://api.example.com/users',
            headers='{"Content-Type": "application/json"}',
            body='{"name": "John", "email": "john@example.com"}'
        )

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_single_api_execution_workflow(self, mock_execute_async):
        """测试单个 API 执行完整工作流"""
        mock_execute_async.return_value = {
            'api_request_id': self.api_request.id,
            'request_method': 'POST',
            'request_url': 'https://api.example.com/users',
            'response_status': 201,
            'response_time': 0.8,
            'response_body': '{"id": 123, "name": "John", "email": "john@example.com"}',
            'error_message': None,
            'assertions': [
                {'id': 1, 'type': 'status_code', 'target_value': '201', 'actual_value': '201', 'passed': True}
            ],
            'passed_count': 1,
            'total_assertions': 1,
            'all_assertions_passed': True,
            'success': True
        }

        # 执行 API 请求
        result = TestExecutionService.execute_single_api_request(
            self.api_request,
            self.user
        )

        # 验证执行结果
        self.assertEqual(result['response_status'], 201)

        # 验证 TestExecution 记录
        execution = TestExecution.objects.get(api_request=self.api_request)
        self.assertEqual(execution.executor, self.user)
        self.assertEqual(execution.status, 'passed')
        self.assertEqual(execution.test_type, 'api')
        self.assertIn('POST', execution.api_logs)
        self.assertIn('john@example.com', execution.api_logs)
        self.assertEqual(execution.api_response_data['response_status'], 201)

        # 验证没有关联集合执行
        self.assertIsNone(execution.collection_execution)


# =============================================================================
# 边界条件测试
# =============================================================================

class EdgeCaseTest(TestCase):
    """边界条件测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')
        self.api_request = ApiRequest.objects.create(
            project=self.project,
            name='API Test',
            method='GET',
            url='https://api.example.com/test'
        )

    def test_empty_collection_execution(self):
        """测试空集合执行"""
        collection = RequestCollection.objects.create(
            project=self.project,
            name='Empty Collection',
            execution_mode='concurrent'
        )

        collection_exec = CollectionExecution.objects.create(
            collection=collection,
            executor=self.user,
            status='success'
        )

        # 验证空集合没有关联的 TestExecution
        self.assertEqual(
            TestExecution.objects.filter(collection_execution=collection_exec).count(),
            0
        )

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_execute_with_network_error(self, mock_execute_async):
        """测试网络错误处理"""
        mock_execute_async.return_value = {
            'api_request_id': self.api_request.id,
            'request_method': 'GET',
            'request_url': 'https://api.example.com/test',
            'response_status': None,
            'response_time': None,
            'response_body': '',
            'error_message': 'Connection refused',
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'success': False
        }

        result = TestExecutionService.execute_single_api_request(
            self.api_request,
            self.user
        )

        # 验证错误处理
        execution = TestExecution.objects.get(api_request=self.api_request)
        self.assertEqual(execution.status, 'failed')
        self.assertIn('Connection refused', execution.api_logs)
        self.assertIn('请求失败', execution.actual_result)

    def test_test_execution_with_partial_data(self):
        """测试TestExecution部分数据的情况"""
        # 只设置必填字段
        execution = TestExecution.objects.create(
            test_type='api',
            status='pending'
        )

        self.assertIsNone(execution.api_request)
        self.assertIsNone(execution.executor)
        self.assertIsNone(execution.collection_execution)
        self.assertEqual(execution.status, 'pending')


# =============================================================================
# 性能测试
# =============================================================================

class PerformanceIntegrationTest(TransactionTestCase):
    """性能集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project')

    @patch('testmanager_app.services.execution_service.execute_single_request_async')
    def test_concurrent_execution_performance(self, mock_execute_async):
        """测试并发执行性能（100个请求）"""
        # 创建100个API请求
        api_requests = []
        for i in range(100):
            api_req = ApiRequest.objects.create(
                project=self.project,
                name=f'API {i}',
                method='GET',
                url=f'https://api.example.com/test{i}'
            )
            api_requests.append(api_req)

        collection = RequestCollection.objects.create(
            project=self.project,
            name='Performance Test Collection',
            execution_mode='concurrent'
        )

        collection_requests = []
        for i, api_req in enumerate(api_requests):
            coll_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req,
                order_index=i
            )
            collection_requests.append(coll_req)

        collection_exec = CollectionExecution.objects.create(
            collection=collection,
            executor=self.user,
            status='pending'
        )

        # Mock 快速返回
        def mock_execute(api_request):
            return {
                'api_request_id': api_request.id,
                'request_method': api_request.method,
                'request_url': api_request.url,
                'response_status': 200,
                'response_time': 0.1,
                'response_body': '{"status": "success"}',
                'error_message': None,
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'success': True
            }

        mock_execute_async.side_effect = mock_execute

        # 执行并发测试
        from asgiref.sync import async_to_sync
        from testmanager_app.collection_execution_strategies import (
            CollectionExecutionStrategyFactory
        )

        strategy = CollectionExecutionStrategyFactory.get_strategy('concurrent')

        import time
        start_time = time.time()

        executions = async_to_sync(strategy.execute)(
            collection_requests,
            self.user,
            collection_exec
        )

        duration = time.time() - start_time

        # 验证所有请求都执行了
        self.assertEqual(len(executions), 100)

        # 验证并发性能（100个请求，每个0.1秒，应该远小于10秒）
        self.assertLess(duration, 5.0)  # 实际应该小于2秒，留有余地

        # 验证所有记录正确创建
        self.assertEqual(
            TestExecution.objects.filter(collection_execution=collection_exec).count(),
            100
        )
