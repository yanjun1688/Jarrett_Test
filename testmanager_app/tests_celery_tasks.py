"""
Celery 异步执行任务测试

测试请求集合的后台执行功能，包括：
- execute_collection_task Celery 任务
- execute_async API 端点
- task_status API 端点
- execution_status API 端点
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from testmanager_app.models import (
    Project, ApiRequest, RequestCollection, CollectionRequest,
    CollectionExecution, Role, UserRole
)


@pytest.mark.django_db
class TestCeleryTasks(TestCase):
    """Celery 任务单元测试"""
    
    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = Project.objects.create(name="测试项目")
        
        # 创建请求集合
        self.collection = RequestCollection.objects.create(
            name="测试集合",
            project=self.project,
            execution_mode='concurrent',
            created_by=self.user
        )
        
        # 创建 API 请求
        self.api_request1 = ApiRequest.objects.create(
            name="请求1",
            project=self.project,
            url="https://api.example.com/test1",
            method="GET"
        )
        self.api_request2 = ApiRequest.objects.create(
            name="请求2",
            project=self.project,
            url="https://api.example.com/test2",
            method="GET"
        )
        
        # 添加请求到集合
        CollectionRequest.objects.create(
            collection=self.collection,
            api_request=self.api_request1,
            order_index=0
        )
        CollectionRequest.objects.create(
            collection=self.collection,
            api_request=self.api_request2,
            order_index=1
        )
        
        # 创建执行记录
        self.collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.user,
            status='pending',
            total_requests=2
        )

    @patch('testmanager_app.collection_execution_strategies.CollectionExecutionStrategyFactory')
    def test_execute_collection_task_success(self, mock_factory):
        """测试 execute_collection_task 成功执行"""
        from testmanager_app.tasks import execute_collection_task
        
        # 修改集合为链式模式（使用同步执行）
        self.collection.execution_mode = 'chain'
        self.collection.save()
        
        # Mock 策略执行返回成功的执行记录
        mock_strategy = MagicMock()
        mock_execution = MagicMock()
        mock_execution.status = 'passed'
        mock_strategy._execute_sync.return_value = [mock_execution, mock_execution]
        mock_factory.get_strategy.return_value = mock_strategy
        
        # 执行任务（直接调用，不通过 Celery）
        result = execute_collection_task(
            collection_id=self.collection.id,
            execution_id=self.collection_exec.id,
            user_id=self.user.id
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['collection_id'], self.collection.id)
        self.assertEqual(result['execution_id'], self.collection_exec.id)
        
        # 验证执行记录已更新
        self.collection_exec.refresh_from_db()
        self.assertIn(self.collection_exec.status, ['success', 'failed'])

    def test_execute_collection_task_collection_not_found(self):
        """测试集合不存在时的错误处理"""
        from testmanager_app.tasks import execute_collection_task
        
        result = execute_collection_task(
            collection_id=99999,  # 不存在的ID
            execution_id=self.collection_exec.id,
            user_id=self.user.id
        )
        
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])

    def test_execute_collection_task_execution_not_found(self):
        """测试执行记录不存在时的错误处理"""
        from testmanager_app.tasks import execute_collection_task
        
        result = execute_collection_task(
            collection_id=self.collection.id,
            execution_id=99999,  # 不存在的ID
            user_id=self.user.id
        )
        
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])

    def test_get_task_status(self):
        """测试获取任务状态"""
        from testmanager_app.tasks import get_task_status
        
        # 使用一个假的 task_id
        status_info = get_task_status('fake-task-id-12345')
        
        self.assertIn('task_id', status_info)
        self.assertIn('status', status_info)
        self.assertEqual(status_info['task_id'], 'fake-task-id-12345')


@pytest.mark.django_db
class TestExecuteAsyncAPI(APITestCase):
    """execute_async API 端点测试"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建用户和权限
        self.admin = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        self.crud_role = Role.objects.create(name="管理员", permission="crud")
        UserRole.objects.create(user=self.admin, role=self.crud_role)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        
        self.project = Project.objects.create(name="测试项目")
        
        # 创建请求集合
        self.collection = RequestCollection.objects.create(
            name="异步测试集合",
            project=self.project,
            execution_mode='concurrent',
            created_by=self.admin
        )
        
        # 创建 API 请求并添加到集合
        self.api_request = ApiRequest.objects.create(
            name="测试请求",
            project=self.project,
            url="https://api.example.com/test",
            method="GET"
        )
        CollectionRequest.objects.create(
            collection=self.collection,
            api_request=self.api_request,
            order_index=0
        )

    @patch('testmanager_app.tasks.execute_collection_task')
    def test_execute_async_success(self, mock_task):
        """测试异步执行端点成功提交任务"""
        # Mock Celery 任务
        mock_task.delay.return_value = MagicMock(id='mock-task-id-123')
        
        url = f'/api/request-collections/{self.collection.id}/execute_async/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        self.assertIn('execution_id', response.data)
        self.assertEqual(response.data['task_id'], 'mock-task-id-123')
        self.assertEqual(response.data['collection_name'], '异步测试集合')
        
        # 验证 CollectionExecution 记录已创建
        execution_id = response.data['execution_id']
        exec_record = CollectionExecution.objects.get(pk=execution_id)
        self.assertEqual(exec_record.status, 'pending')
        self.assertEqual(exec_record.total_requests, 1)

    def test_execute_async_collection_not_found(self):
        """测试集合不存在时返回 404"""
        url = '/api/request-collections/99999/execute_async/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_execute_async_empty_collection(self):
        """测试空集合执行返回错误"""
        # 创建空集合
        empty_collection = RequestCollection.objects.create(
            name="空集合",
            project=self.project,
            execution_mode='concurrent'
        )
        
        url = f'/api/request-collections/{empty_collection.id}/execute_async/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_execute_async_unauthenticated(self):
        """测试未认证用户访问"""
        self.client.logout()
        
        url = f'/api/request-collections/{self.collection.id}/execute_async/'
        response = self.client.post(url)
        
        # 应该返回 401 或 403
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


@pytest.mark.django_db
class TestTaskStatusAPI(APITestCase):
    """task_status API 端点测试"""
    
    def setUp(self):
        """设置测试数据"""
        self.admin = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        self.crud_role = Role.objects.create(name="管理员", permission="crud")
        UserRole.objects.create(user=self.admin, role=self.crud_role)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_task_status_pending(self):
        """测试查询 pending 状态的任务"""
        url = '/api/request-collections/task-status/fake-pending-task/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('task_id', response.data)
        self.assertIn('status', response.data)

    @patch('celery.result.AsyncResult')
    def test_task_status_completed(self, mock_async_result):
        """测试查询已完成的任务状态"""
        # Mock AsyncResult
        mock_result = MagicMock()
        mock_result.status = 'SUCCESS'
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {
            'success': True,
            'execution_id': 1,
            'passed_requests': 2,
            'failed_requests': 0
        }
        mock_async_result.return_value = mock_result
        
        url = '/api/request-collections/task-status/completed-task-id/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['ready'])


@pytest.mark.django_db
class TestExecutionStatusAPI(APITestCase):
    """execution_status API 端点测试"""
    
    def setUp(self):
        """设置测试数据"""
        self.admin = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        self.crud_role = Role.objects.create(name="管理员", permission="crud")
        UserRole.objects.create(user=self.admin, role=self.crud_role)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        
        self.project = Project.objects.create(name="测试项目")
        
        self.collection = RequestCollection.objects.create(
            name="状态测试集合",
            project=self.project,
            execution_mode='sequential'
        )
        
        self.collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            executor=self.admin,
            status='running',
            total_requests=5,
            passed_requests=2,
            failed_requests=0
        )

    def test_execution_status_success(self):
        """测试查询执行状态成功"""
        url = f'/api/request-collections/{self.collection.id}/execution-status/{self.collection_exec.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'running')
        self.assertEqual(response.data['total_requests'], 5)
        self.assertEqual(response.data['passed_requests'], 2)

    def test_execution_status_not_found(self):
        """测试执行记录不存在时返回 404"""
        url = f'/api/request-collections/{self.collection.id}/execution-status/99999/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_execution_status_wrong_collection(self):
        """测试执行记录与集合不匹配时返回 404"""
        # 创建另一个集合
        other_collection = RequestCollection.objects.create(
            name="其他集合",
            project=self.project,
            execution_mode='concurrent'
        )
        
        # 使用错误的集合 ID 查询
        url = f'/api/request-collections/{other_collection.id}/execution-status/{self.collection_exec.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class TestUpdateExecutionError(TestCase):
    """_update_execution_error 辅助函数测试"""
    
    def setUp(self):
        """设置测试数据"""
        self.project = Project.objects.create(name="测试项目")
        self.collection = RequestCollection.objects.create(
            name="测试集合",
            project=self.project
        )
        self.collection_exec = CollectionExecution.objects.create(
            collection=self.collection,
            status='running'
        )

    def test_update_execution_error(self):
        """测试更新执行记录为错误状态"""
        from testmanager_app.tasks import _update_execution_error
        
        _update_execution_error(self.collection_exec.id, "测试错误信息")
        
        self.collection_exec.refresh_from_db()
        self.assertEqual(self.collection_exec.status, 'failed')
        self.assertIn("测试错误信息", self.collection_exec.output)
        self.assertIsNotNone(self.collection_exec.finished_at)

    def test_update_execution_error_not_found(self):
        """测试更新不存在的执行记录（应该不抛出异常）"""
        from testmanager_app.tasks import _update_execution_error
        
        # 不应该抛出异常
        _update_execution_error(99999, "测试错误")


# 集成测试 - 可选，需要 Celery worker 运行
# @pytest.mark.skipif(not celery_running(), reason="Celery worker not running")
# class TestCeleryIntegration(TestCase):
#     """Celery 集成测试（需要 Redis 和 Celery worker）"""
#     pass
