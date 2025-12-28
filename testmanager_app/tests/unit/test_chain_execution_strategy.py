"""
链式执行策略单元测试
专门针对 ChainExecutionStrategy 的测试，使用 mock 模拟 HTTP 请求

测试覆盖：
1. 基本链式执行流程（同步实现）
2. 变量提取和传递
3. 变量提取后的断言验证
4. 变量提取失败时立即停止
5. 模板渲染
6. 错误处理
7. stop_on_failure 逻辑
8. 多请求链式执行
9. 完整链路日志记录
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth.models import User
from django.utils import timezone

from testmanager_app.models import (
    ApiRequest, RequestCollection, CollectionRequest, CollectionExecution, TestExecution
)
from testmanager_app.collection_execution_strategies import (
    ChainExecutionStrategy,
    RequestRenderer
)


@pytest.mark.django_db
class TestChainExecutionStrategy:
    """链式执行策略测试类"""

    @pytest.fixture
    def strategy(self):
        """创建链式执行策略实例"""
        return ChainExecutionStrategy()

    @pytest.fixture
    def user(self, db):
        """创建测试用户"""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @pytest.fixture
    def api_request_1(self, db):
        """创建第一个API请求（用于提取变量）"""
        return ApiRequest.objects.create(
            name='Login API',
            method='POST',
            url='https://api.example.com/login',
            headers='{"Content-Type": "application/json"}',
            body='{"username": "test", "password": "test123"}'
        )

    @pytest.fixture
    def api_request_2(self, db):
        """创建第二个API请求（使用提取的变量）"""
        return ApiRequest.objects.create(
            name='Get User Info',
            method='GET',
            url='https://api.example.com/users/{{user_id}}',
            headers='{"Authorization": "Bearer {{token}}"}',
            body=''
        )

    @pytest.fixture
    def api_request_3(self, db):
        """创建第三个API请求（继续使用变量）"""
        return ApiRequest.objects.create(
            name='Update User',
            method='PUT',
            url='https://api.example.com/users/{{user_id}}',
            headers='{"Authorization": "Bearer {{token}}", "Content-Type": "application/json"}',
            body='{"name": "{{user_name}}"}'
        )

    @pytest.fixture
    def collection(self, db):
        """创建请求集合"""
        return RequestCollection.objects.create(
            name='Chain Execution Test Collection',
            description='Test collection for chain execution',
            execution_mode='chain'
        )

    @pytest.fixture
    def collection_exec(self, db, collection, user):
        """创建集合执行记录"""
        return CollectionExecution.objects.create(
            collection=collection,
            executor=user,
            status='pending',
            started_at=timezone.now()
        )

    def test_can_execute_chain_mode(self, strategy):
        """测试支持链式模式"""
        assert strategy.can_execute('chain') is True
        assert strategy.can_execute('concurrent') is False
        assert strategy.can_execute('sequential') is False

    def test_single_request_execution(self, strategy, api_request_1, user, collection_exec):
        """测试单个请求的链式执行（同步实现）"""
        collection = RequestCollection.objects.create(name='Single Request Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False
        )

        # Mock TestExecutionService.execute_single_api_request（同步方法）
        mock_result = {
            'api_request_id': api_request_1.id,
            'request_method': 'POST',
            'request_url': 'https://api.example.com/login',
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"token": "abc123", "user_id": 456}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            # execute_single_api_request 会创建 TestExecution 记录
            # 我们需要创建一个真实的 TestExecution 记录来模拟
            execution = TestExecution.objects.create(
                test_type='api',
                api_request=api_request_1,
                executor=user,
                status='passed',
                actual_result='测试通过',
                executed_at=timezone.now(),
                api_response_data=mock_result,
                api_logs='\n'.join(mock_result['logs'])
            )
            
            mock_execute.return_value = mock_result

            # 直接调用同步方法
            executions = strategy._execute_sync(
                [coll_req],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行结果
            assert len(executions) == 1
            assert isinstance(executions[0], TestExecution)
            assert executions[0].status == 'passed'
            assert executions[0].api_request == api_request_1
            assert executions[0].collection_execution == collection_exec

            # 验证 mock 被调用
            mock_execute.assert_called_once()

    def test_variable_extraction_and_passing(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试变量提取和传递（包含断言验证）"""
        collection = RequestCollection.objects.create(name='Variable Passing Collection')
        
        # 第一个请求：提取变量
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            extract_rules=[
                {'name': 'token', 'jsonpath': '$.token'},
                {'name': 'user_id', 'jsonpath': '$.user_id'}
            ]
        )

        # 第二个请求：使用提取的变量
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        # Mock 第一个请求的响应
        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"token": "abc123xyz", "user_id": 789}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        # Mock 第二个请求的响应（应该使用提取的变量）
        mock_result_2 = {
            'api_request_id': api_request_2.id,
            'response_status': 200,
            'response_time': 0.3,
            'response_body': '{"id": 789, "name": "Test User"}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:01] 开始执行', '[2024-01-01 10:00:01] 执行完成']
        }

        # 用于捕获调用时的实际参数值
        captured_calls = []
        
        def capture_and_return(api_request, user):
            """捕获调用时的实际参数值"""
            # 在执行策略中，api_request 对象在调用时已经被临时修改为渲染后的值
            # 我们需要立即捕获这些值，因为 finally 块会恢复原始值
            captured_calls.append({
                'url': api_request.url,
                'headers': api_request.headers,
                'body': api_request.body
            })
            # 返回对应的 mock 结果
            if len(captured_calls) == 1:
                return mock_result_1
            else:
                return mock_result_2
        
        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request', side_effect=capture_and_return):
            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行了两个请求
            assert len(executions) == 2
            assert executions[0].status == 'passed'
            assert executions[1].status == 'passed'

            # 验证第二个请求使用了提取的变量
            # 检查捕获的调用参数（第二个请求应该使用渲染后的 URL 和 headers）
            assert len(captured_calls) == 2
            
            # 获取第二个请求的调用参数（已捕获的值）
            second_call_data = captured_calls[1]
            assert '789' in second_call_data['url']  # URL 中应该包含提取的 user_id
            assert 'abc123xyz' in second_call_data['headers']  # headers 中应该包含提取的 token

    def test_variable_extraction_assertion_failure(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试变量提取断言失败时立即停止"""
        collection = RequestCollection.objects.create(name='Variable Assertion Failure Collection')
        
        # 第一个请求：提取变量（但变量值为 None 或空）
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            extract_rules=[
                {'name': 'token', 'jsonpath': '$.token'}  # 这个会提取到 None
            ]
        )

        # 第二个请求：不应该被执行（因为变量提取失败）
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        # Mock 第一个请求的响应（token 为 None）
        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"token": null, "user_id": 789}',  # token 为 null
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.return_value = mock_result_1

            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证只执行了第一个请求，第二个请求因为变量提取失败而停止
            assert len(executions) == 1
            assert executions[0].status == 'failed'  # 因为变量提取失败，状态变为 failed
            assert '变量提取或断言失败' in executions[0].actual_result

            # 验证第二个请求没有被执行
            assert mock_execute.call_count == 1

    def test_variable_extraction_jsonpath_not_found(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试变量提取 JSONPath 未找到匹配值时立即停止"""
        collection = RequestCollection.objects.create(name='JSONPath Not Found Collection')
        
        # 第一个请求：提取变量（但 JSONPath 找不到匹配值）
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            extract_rules=[
                {'name': 'token', 'jsonpath': '$.nonexistent_token'}  # 这个路径不存在
            ]
        )

        # 第二个请求：不应该被执行
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        # Mock 第一个请求的响应
        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"user_id": 789}',  # 没有 token 字段
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.return_value = mock_result_1

            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证只执行了第一个请求，第二个请求因为变量提取失败而停止
            assert len(executions) == 1
            assert executions[0].status == 'failed'
            assert '变量提取或断言失败' in executions[0].actual_result

            # 验证第二个请求没有被执行
            assert mock_execute.call_count == 1

    def test_multi_request_chain_execution(self, strategy, api_request_1, api_request_2, api_request_3, user, collection_exec):
        """测试多请求链式执行"""
        collection = RequestCollection.objects.create(name='Multi Request Chain Collection')
        
        # 第一个请求：登录并提取 token 和 user_id
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            extract_rules=[
                {'name': 'token', 'jsonpath': '$.token'},
                {'name': 'user_id', 'jsonpath': '$.user_id'},
                {'name': 'user_name', 'jsonpath': '$.user_name'}
            ]
        )

        # 第二个请求：获取用户信息
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        # 第三个请求：更新用户信息
        coll_req_3 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_3,
            order_index=3,
            stop_on_failure=False
        )

        # Mock 响应
        mock_results = [
            {
                'api_request_id': api_request_1.id,
                'response_status': 200,
                'response_time': 0.5,
                'response_body': json.dumps({
                    'token': 'secret_token_123',
                    'user_id': 999,
                    'user_name': 'John Doe'
                }),
                'error_message': None,
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
            },
            {
                'api_request_id': api_request_2.id,
                'response_status': 200,
                'response_time': 0.3,
                'response_body': '{"id": 999, "name": "John Doe"}',
                'error_message': None,
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'logs': ['[2024-01-01 10:00:01] 开始执行', '[2024-01-01 10:00:01] 执行完成']
            },
            {
                'api_request_id': api_request_3.id,
                'response_status': 200,
                'response_time': 0.4,
                'response_body': '{"id": 999, "name": "John Doe", "updated": true}',
                'error_message': None,
                'assertions': [],
                'passed_count': 0,
                'total_assertions': 0,
                'logs': ['[2024-01-01 10:00:02] 开始执行', '[2024-01-01 10:00:02] 执行完成']
            }
        ]

        # 用于捕获调用时的实际参数值
        captured_calls = []
        
        def capture_and_return(api_request, user):
            """捕获调用时的实际参数值"""
            captured_calls.append({
                'url': api_request.url,
                'headers': api_request.headers,
                'body': api_request.body
            })
            # 返回对应的 mock 结果
            return mock_results[len(captured_calls) - 1]
        
        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request', side_effect=capture_and_return):
            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2, coll_req_3],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行了三个请求
            assert len(executions) == 3
            assert all(e.status == 'passed' for e in executions)

            # 验证变量传递
            assert len(captured_calls) == 3
            
            # 验证第二个请求使用了第一个请求提取的变量
            second_call_data = captured_calls[1]
            assert '999' in second_call_data['url']
            assert 'secret_token_123' in second_call_data['headers']

            # 验证第三个请求使用了第一个请求提取的变量
            third_call_data = captured_calls[2]
            assert '999' in third_call_data['url']
            assert 'secret_token_123' in third_call_data['headers']
            assert 'John Doe' in third_call_data['body']

    def test_stop_on_failure_enabled(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试启用 stop_on_failure 时的行为"""
        collection = RequestCollection.objects.create(name='Stop On Failure Collection')
        
        # 第一个请求：成功
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=True,
            extract_rules=[{'name': 'token', 'jsonpath': '$.token'}]
        )

        # 第二个请求：失败（不应该执行）
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=True
        )

        # Mock 第一个请求成功，第二个请求失败
        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"token": "abc123"}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        mock_result_2 = {
            'api_request_id': api_request_2.id,
            'response_status': 500,
            'response_time': 0.2,
            'response_body': '{"error": "Internal Server Error"}',
            'error_message': 'HTTP 500',
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:01] 开始执行', '[2024-01-01 10:00:01] 执行失败']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.side_effect = [mock_result_1, mock_result_2]

            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行了两个请求（第二个虽然失败但已经执行了）
            assert len(executions) == 2
            assert executions[0].status == 'passed'
            assert executions[1].status == 'failed'

            # 验证两个请求都被执行了（stop_on_failure 是在执行后检查的）
            assert mock_execute.call_count == 2

    def test_stop_on_failure_disabled(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试禁用 stop_on_failure 时的行为（但链式执行在请求失败时仍会停止）"""
        collection = RequestCollection.objects.create(name='Continue On Failure Collection')
        
        # 第一个请求：失败
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False  # 禁用失败停止
        )

        # 第二个请求：成功（但不会执行，因为链式执行在第一个请求失败时会停止）
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        # Mock 第一个请求失败，第二个请求成功
        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 500,
            'response_time': 0.2,
            'response_body': '{"error": "Internal Server Error"}',
            'error_message': 'HTTP 500',
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行失败']
        }

        mock_result_2 = {
            'api_request_id': api_request_2.id,
            'response_status': 200,
            'response_time': 0.3,
            'response_body': '{"id": 123}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:01] 开始执行', '[2024-01-01 10:00:01] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.side_effect = [mock_result_1, mock_result_2]

            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证只执行了第一个请求（链式执行在请求失败时会停止）
            assert len(executions) == 1
            assert executions[0].status == 'failed'

            # 验证第二个请求没有被执行（链式执行在第一个请求失败时停止）
            assert mock_execute.call_count == 1

    def test_variable_extraction_from_execution(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试从 TestExecution 对象中提取变量"""
        collection = RequestCollection.objects.create(name='Extract From Execution Collection')
        
        # 第一个请求：提取变量
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            extract_rules=[
                {'name': 'token', 'jsonpath': '$.token'},
                {'name': 'user_id', 'jsonpath': '$.user_id'}
            ]
        )

        # 第二个请求：使用提取的变量
        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        # Mock 第一个请求的响应
        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': json.dumps({
                'token': 'extracted_token_456',
                'user_id': 888
            }),
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        # Mock 第二个请求的响应
        mock_result_2 = {
            'api_request_id': api_request_2.id,
            'response_status': 200,
            'response_time': 0.3,
            'response_body': '{"id": 888}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:01] 开始执行', '[2024-01-01 10:00:01] 执行完成']
        }

        # 用于捕获调用时的实际参数值
        captured_calls = []
        
        def capture_and_return(api_request, user):
            """捕获调用时的实际参数值"""
            captured_calls.append({
                'url': api_request.url,
                'headers': api_request.headers,
                'body': api_request.body
            })
            # 返回对应的 mock 结果
            if len(captured_calls) == 1:
                return mock_result_1
            else:
                return mock_result_2
        
        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request', side_effect=capture_and_return):
            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行结果
            assert len(executions) == 2
            assert executions[0].status == 'passed'
            assert executions[1].status == 'passed'

            # 验证第一个执行记录的 api_response_data 包含响应体
            assert executions[0].api_response_data is not None
            assert 'response_body' in executions[0].api_response_data

            # 验证第二个请求使用了提取的变量
            # 检查捕获的调用参数（第二个请求应该使用渲染后的 URL 和 headers）
            assert len(captured_calls) == 2
            second_call_data = captured_calls[1]
            assert '888' in second_call_data['url']
            assert 'extracted_token_456' in second_call_data['headers']

    def test_execution_with_exception(self, strategy, api_request_1, user, collection_exec):
        """测试执行过程中出现异常"""
        collection = RequestCollection.objects.create(name='Exception Test Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False
        )

        # Mock 抛出异常
        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.side_effect = Exception('Network error')

            executions = strategy._execute_sync(
                [coll_req],
                user=user,
                collection_exec=collection_exec
            )

            # 验证错误处理
            assert len(executions) == 1
            assert executions[0].status == 'failed'
            assert '执行失败' in executions[0].actual_result
            assert 'Network error' in executions[0].actual_result

    def test_empty_collection_requests(self, strategy, user, collection_exec):
        """测试空请求列表"""
        executions = strategy._execute_sync(
            [],
            user=user,
            collection_exec=collection_exec
        )

        assert len(executions) == 0

    def test_request_count_multiple_executions(self, strategy, api_request_1, user, collection_exec):
        """测试 request_count > 1 的情况"""
        collection = RequestCollection.objects.create(name='Multiple Executions Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            request_count=3  # 执行3次
        )

        # Mock 响应
        mock_result = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"result": "success"}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.return_value = mock_result

            executions = strategy._execute_sync(
                [coll_req],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行了3次
            assert len(executions) == 3
            assert all(e.status == 'passed' for e in executions)
            assert mock_execute.call_count == 3

    def test_context_initialization(self, strategy, api_request_1, user, collection_exec):
        """测试上下文初始化"""
        collection = RequestCollection.objects.create(name='Context Init Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False
        )

        # 提供初始上下文
        initial_context = {'predefined_var': 'predefined_value'}

        mock_result = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"result": "success"}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.return_value = mock_result

            executions = strategy._execute_sync(
                [coll_req],
                user=user,
                collection_exec=collection_exec,
                context=initial_context
            )

            # 验证执行成功
            assert len(executions) == 1
            assert executions[0].status == 'passed'

            # 验证初始上下文被使用（如果请求中有模板变量）
            # 这里主要验证不会因为初始上下文而出错
            assert mock_execute.call_count == 1

    def test_chain_logs_recorded(self, strategy, api_request_1, api_request_2, user, collection_exec):
        """测试完整链路日志记录"""
        collection = RequestCollection.objects.create(name='Chain Logs Collection')
        
        coll_req_1 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_1,
            order_index=1,
            stop_on_failure=False,
            extract_rules=[{'name': 'token', 'jsonpath': '$.token'}]
        )

        coll_req_2 = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request_2,
            order_index=2,
            stop_on_failure=False
        )

        mock_result_1 = {
            'api_request_id': api_request_1.id,
            'response_status': 200,
            'response_time': 0.5,
            'response_body': '{"token": "test_token"}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:00] 开始执行', '[2024-01-01 10:00:00] 执行完成']
        }

        mock_result_2 = {
            'api_request_id': api_request_2.id,
            'response_status': 200,
            'response_time': 0.3,
            'response_body': '{"id": 123}',
            'error_message': None,
            'assertions': [],
            'passed_count': 0,
            'total_assertions': 0,
            'logs': ['[2024-01-01 10:00:01] 开始执行', '[2024-01-01 10:00:01] 执行完成']
        }

        with patch('testmanager_app.services.execution_service.TestExecutionService.execute_single_api_request') as mock_execute:
            mock_execute.side_effect = [mock_result_1, mock_result_2]

            executions = strategy._execute_sync(
                [coll_req_1, coll_req_2],
                user=user,
                collection_exec=collection_exec
            )

            # 验证执行成功
            assert len(executions) == 2

            # 验证链路日志被记录到 CollectionExecution.output
            collection_exec.refresh_from_db()
            assert collection_exec.output is not None
            assert '[链式执行]' in collection_exec.output
            assert '开始执行链式请求集合' in collection_exec.output
            assert '链式执行完成' in collection_exec.output
            assert '变量提取成功' in collection_exec.output or '变量断言通过' in collection_exec.output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

