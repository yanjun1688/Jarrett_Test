"""
集合执行策略集成测试
测试集合执行策略模式、工厂模式和各种执行策略的实现 - 使用真实调用链路
"""

import pytest
import asyncio
import json
from django.core.files import File
from asgiref.sync import sync_to_async
from django.utils import timezone

from testmanager_app.models import ApiRequest, RequestCollection, CollectionRequest
from testmanager_app.collection_execution_strategies import (
    CollectionExecutionStatus,
    CollectionExecutionStrategyInterface,
    ConcurrentExecutionStrategy,
    SequentialExecutionStrategy,
    ChainExecutionStrategy,
    RequestRenderer,
    CollectionExecutionStrategyFactory
)


class TestCollectionExecutionStatus:
    """测试集合执行状态枚举"""

    def test_status_values(self):
        """测试状态枚举值"""
        assert CollectionExecutionStatus.SUCCESS.value == "success"
        assert CollectionExecutionStatus.FAILED.value == "failed"
        assert CollectionExecutionStatus.ERROR.value == "error"

    def test_status_equality(self):
        """测试状态枚举比较"""
        assert CollectionExecutionStatus.SUCCESS == CollectionExecutionStatus.SUCCESS
        assert CollectionExecutionStatus.FAILED != CollectionExecutionStatus.SUCCESS


class TestCollectionExecutionStrategyInterface:
    """测试集合执行策略接口"""

    def test_interface_is_abstract(self):
        """测试接口是抽象类"""
        with pytest.raises(TypeError):
            CollectionExecutionStrategyInterface()

    def test_concrete_strategy_must_implement_methods(self):
        """测试具体策略必须实现所有抽象方法"""
        class IncompleteStrategy(CollectionExecutionStrategyInterface):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()

    def test_concrete_strategy_must_implement_can_execute(self):
        """测试具体策略必须实现can_execute方法"""
        class StrategyWithoutCanExecute(CollectionExecutionStrategyInterface):
            async def execute(self, collection_requests, context=None):
                return []

        with pytest.raises(TypeError):
            StrategyWithoutCanExecute()

    def test_concrete_strategy_must_implement_execute(self):
        """测试具体策略必须实现execute方法"""
        class StrategyWithoutExecute(CollectionExecutionStrategyInterface):
            def can_execute(self, execution_mode):
                return True

        with pytest.raises(TypeError):
            StrategyWithoutExecute()


@pytest.mark.django_db
class TestConcurrentExecutionStrategy:
    """测试并发执行策略 - 使用真实数据"""

    @pytest.fixture
    def strategy(self):
        return ConcurrentExecutionStrategy()

    @pytest.fixture
    def api_request(self, db):
        """创建真实的API请求"""
        return ApiRequest.objects.create(
            name='Test API Request',
            method='GET',
            url='https://httpbin.org/get',
            headers='{"Accept": "application/json"}',
            body=''
        )

    @pytest.fixture
    def collection_request(self, db, api_request):
        """创建真实的集合请求"""
        collection = RequestCollection.objects.create(
            name='Test Collection',
            description='Test Collection for Concurrent Execution'
        )
        return CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

    def test_can_execute_concurrent_mode(self, strategy):
        """测试支持并发模式"""
        assert strategy.can_execute('concurrent') is True

    def test_cannot_execute_non_concurrent_modes(self, strategy):
        """测试不支持非并发模式"""
        assert strategy.can_execute('sequential') is False
        assert strategy.can_execute('chain') is False
        assert strategy.can_execute('unknown') is False

    @pytest.mark.asyncio
    async def test_execute_single_successful_request(self, strategy, collection_request):
        """测试执行单个成功的请求 - 使用真实数据"""
        # 使用真实的集合请求对象
        results = await strategy.execute([collection_request])

        # 验证结果格式
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result
        assert ' error_message' in result
        assert 'status_code' in result
        assert 'response_time' in result
        assert 'response_body' in result
        assert 'assertions' in result
        assert 'passed_count' in result
        assert 'total_assertions' in result
        assert 'execution_index' in result
        assert 'request_count' in result

        # 验证请求ID匹配
        assert result['api_request_id'] == collection_request.api_request.id

    @pytest.mark.asyncio
    async def test_execute_multiple_concurrent_requests(self, strategy, api_request):
        """测试并发执行多个请求 - 使用真实数据"""
        # 创建多个真实的集合请求
        collection = RequestCollection.objects.create(name='Multi-Request Collection')
        requests = []

        for i in range(3):
            # 创建多个API请求
            api_req = ApiRequest.objects.create(
                name=f'Test API Request {i}',
                method='GET',
                url='https://httpbin.org/get',
                headers='{"Accept": "application/json"}',
                body=''
            )
            coll_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req,
                order_index=i,
                stop_on_failure=False
            )
            requests.append(coll_req)

        results = await strategy.execute(requests)

        # 验证执行了所有请求
        assert len(results) == 3
        # 验证每个结果都有正确的格式
        for result in results:
            assert 'api_request_id' in result
            assert 'success' in result
            assert 'execution_index' in result
            assert result['execution_index'] == 0  # 每个请求只执行一次
            assert result['request_count'] == 1

    @pytest.mark.asyncio
    async def test_execute_with_invalid_url(self, strategy, api_request):
        """测试URL无效的情况 - 使用真实数据"""
        # 创建一个URL无效的API请求
        api_request.url = 'invalid://bad-url'
        api_request.save()

        collection = RequestCollection.objects.create(name='Invalid URL Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

        results = await strategy.execute([coll_req])

        # 验证错误处理
        assert len(results) == 1
        result = results[0]
        assert result['api_request_id'] == api_request.id
        assert result['success'] is False
        assert result['error'] is not None
        assert result['status_code'] is None
        assert result['response_time'] == 0

    @pytest.mark.asyncio
    async def test_execute_with_network_timeout(self, strategy, api_request):
        """测试网络超时情况 - 使用真实数据"""
        # 创建一个超时时间很短的请求
        api_request.url = 'https://httpbin.org/delay/10'  # 10秒延迟
        api_request.timeout = 1  # 1秒超时
        api_request.save()

        collection = RequestCollection.objects.create(name='Timeout Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

        results = await strategy.execute([coll_req])

        # 验证超时处理
        assert len(results) == 1
        result = results[0]
        assert result['api_request_id'] == api_request.id
        assert result['success'] is False
        assert 'timeout' in result['error'].lower() or 'time' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_execute_with_multiple_request_counts(self, strategy, api_request):
        """测试执行多个请求计数 - 使用真实数据"""
        # 使用sync_to_async来处理数据库操作
        collection = await sync_to_async(RequestCollection.objects.create)(name='Multi-Count Collection')
        coll_req = await sync_to_async(CollectionRequest.objects.create)(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False,
            request_count=3  # 执行3次
        )

        results = await strategy.execute([coll_req])

        # 验证执行了3次
        assert len(results) == 3
        # 验证每次执行都有正确的索引
        for i, result in enumerate(results):
            assert result['execution_index'] == i
            assert result['request_count'] == 3

    def test_create_error_result_format(self, strategy):
        """测试错误结果格式"""
        error_result = strategy._create_error_result(999, "Test error message")

        assert error_result['api_request_id'] == 999
        assert error_result['success'] is False
        assert error_result['error'] == "Test error message"
        assert error_result['status_code'] is None
        assert error_result['response_time'] == 0
        assert error_result['response_body'] == ''
        assert error_result['assertions'] == []
        assert error_result['passed_count'] == 0
        assert error_result['total_assertions'] == 0


@pytest.mark.django_db
class TestSequentialExecutionStrategy:
    """测试顺序执行策略 - 使用真实数据"""

    @pytest.fixture
    def strategy(self):
        return SequentialExecutionStrategy()

    @pytest.fixture
    def api_request(self, db):
        """创建真实的API请求"""
        return ApiRequest.objects.create(
            name='Test API Request',
            method='GET',
            url='https://httpbin.org/get',
            headers='{"Accept": "application/json"}',
            body=''
        )

    @pytest.fixture
    def collection_request(self, db, api_request):
        """创建真实的集合请求"""
        collection = RequestCollection.objects.create(
            name='Sequential Test Collection',
            description='Test Collection for Sequential Execution'
        )
        return CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

    def test_can_execute_sequential_mode(self, strategy):
        """测试支持顺序模式"""
        assert strategy.can_execute('sequential') is True

    def test_cannot_execute_non_sequential_modes(self, strategy):
        """测试不支持非顺序模式"""
        assert strategy.can_execute('concurrent') is False
        assert strategy.can_execute('chain') is False
        assert strategy.can_execute('unknown') is False

    @pytest.mark.asyncio
    async def test_execute_single_successful_request(self, strategy, collection_request):
        """测试执行单个成功的请求 - 使用真实数据"""
        results = await strategy.execute([collection_request])

        # 验证结果格式
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result
        assert 'error' in result
        assert 'status_code' in result
        assert 'response_time' in result
        assert 'response_body' in result
        assert 'assertions' in result
        assert 'passed_count' in result
        assert 'total_assertions' in result

        # 验证请求ID匹配
        assert result['api_request_id'] == collection_request.api_request.id

    @pytest.mark.asyncio
    async def test_execute_multiple_sequential_requests(self, strategy, api_request):
        """测试顺序执行多个请求 - 使用真实数据"""
        # 创建多个真实的集合请求
        collection = RequestCollection.objects.create(name='Sequential Multi-Request Collection')
        requests = []

        for i in range(3):
            # 创建多个API请求
            api_req = ApiRequest.objects.create(
                name=f'Sequential Test API Request {i}',
                method='GET',
                url='https://httpbin.org/get',
                headers='{"Accept": "application/json"}',
                body='',
                            )
            coll_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req,
                order_index=i,
                stop_on_failure=False
            )
            requests.append(coll_req)

        results = await strategy.execute(requests)

        # 验证执行了所有请求
        assert len(results) == 3
        # 验证每个结果都有正确的格式
        for result in results:
            assert 'api_request_id' in result
            assert 'success' in result
            assert 'execution_index' in result
            assert result['execution_index'] == 0  # 每个请求只执行一次
            assert result['request_count'] == 1

    @pytest.mark.asyncio
    async def test_stop_on_failure_when_enabled(self, strategy, api_request):
        """测试启用失败停止功能 - 使用真实数据"""
        # 创建两个请求，第一个失败
        collection = RequestCollection.objects.create(name='Stop on Failure Collection')

        # 第一个请求：创建一个会失败的请求
        api_req1 = ApiRequest.objects.create(
            name='Failed API Request',
            method='GET',
            url='invalid://bad-url',
            headers='{}',
            body=''
        )
        first_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_req1,
            order_index=1,
            stop_on_failure=True  # 启用失败停止
        )

        # 第二个请求：正常请求（不应该执行）
        api_req2 = ApiRequest.objects.create(
            name='Should Not Execute',
            method='GET',
            url='https://httpbin.org/get',
            headers='{"Accept": "application/json"}',
            body=''
        )
        second_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_req2,
            order_index=2,
            stop_on_failure=True
        )

        results = await strategy.execute([first_req, second_req])

        # 应该只执行第一个请求
        assert len(results) == 1
        assert results[0]['success'] is False

    @pytest.mark.asyncio
    async def test_continue_on_failure_when_disabled(self, strategy, api_request):
        """测试禁用失败停止功能 - 使用真实数据"""
        # 创建两个请求，第一个失败但继续执行
        collection = RequestCollection.objects.create(name='Continue on Failure Collection')

        # 第一个请求：创建一个会失败的请求
        api_req1 = ApiRequest.objects.create(
            name='Failed API Request',
            method='GET',
            url='invalid://bad-url',
            headers='{}',
            body=''
        )
        first_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_req1,
            order_index=1,
            stop_on_failure=False  # 禁用失败停止
        )

        # 第二个请求：正常请求（应该执行）
        api_req2 = ApiRequest.objects.create(
            name='Should Execute',
            method='GET',
            url='https://httpbin.org/get',
            headers='{"Accept": "application/json"}',
            body=''
        )
        second_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_req2,
            order_index=2,
            stop_on_failure=False
        )

        results = await strategy.execute([first_req, second_req])

        # 应该执行两个请求
        assert len(results) == 2
        assert results[0]['success'] is False
        assert results[1]['success'] is True

    @pytest.mark.asyncio
    async def test_execute_with_exception(self, strategy, api_request):
        """测试执行过程中出现异常 - 使用真实数据"""
        # 创建一个会触发异常的请求
        api_request.url = 'invalid://bad-url'
        api_request.save()

        collection = RequestCollection.objects.create(name='Exception Test Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

        results = await strategy.execute([coll_req])

        # 验证错误处理
        assert len(results) == 1
        result = results[0]
        assert result['api_request_id'] == api_request.id
        assert result['success'] is False
        assert result['error'] is not None
        assert result['status_code'] is None
        assert result['response_time'] == 0


@pytest.mark.django_db
class TestChainExecutionStrategy:
    """测试链式执行策略 - 使用真实数据"""

    @pytest.fixture
    def strategy(self):
        return ChainExecutionStrategy()

    @pytest.fixture
    def api_request(self, db):
        """创建真实的API请求"""
        return ApiRequest.objects.create(
            name='Test API Request',
            method='GET',
            url='https://httpbin.org/get',
            headers='{"Accept": "application/json"}',
            body=''
        )

    @pytest.fixture
    def collection_request(self, db, api_request):
        """创建真实的集合请求"""
        collection = RequestCollection.objects.create(
            name='Chain Test Collection',
            description='Test Collection for Chain Execution'
        )
        return CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

    def test_can_execute_chain_mode(self, strategy):
        """测试支持链式模式"""
        assert strategy.can_execute('chain') is True

    def test_cannot_execute_non_chain_modes(self, strategy):
        """测试不支持非链式模式"""
        assert strategy.can_execute('concurrent') is False
        assert strategy.can_execute('sequential') is False
        assert strategy.can_execute('unknown') is False

    @pytest.mark.asyncio
    async def test_execute_single_request_without_context(self, strategy, collection_request):
        """测试无上下文执行单个请求 - 使用真实数据"""
        results = await strategy.execute([collection_request])

        # 验证结果格式
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result
        assert 'error' in result
        assert 'status_code' in result
        assert 'response_time' in result
        assert 'response_body' in result
        assert 'assertions' in result
        assert 'passed_count' in result
        assert 'total_assertions' in result

        # 验证请求ID匹配
        assert result['api_request_id'] == collection_request.api_request.id

    @pytest.mark.asyncio
    async def test_execute_with_context(self, strategy, collection_request):
        """测试使用上下文执行请求 - 使用真实数据"""
        context = {'user_id': '123', 'token': 'existing_token'}

        results = await strategy.execute([collection_request], context)

        # 验证结果格式
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result

    @pytest.mark.asyncio
    async def test_variable_extraction_on_success(self, strategy, api_request):
        """测试成功时提取变量 - 使用真实数据"""
        # 设置提取规则
        collection = RequestCollection.objects.create(name='Extraction Test Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )
        # 设置提取规则
        coll_req.extract_rules = [
            {'name': 'extracted_url', 'jsonpath': '$.url'},
            {'name': 'extracted_origin', 'jsonpath': '$.origin'}
        ]

        results = await strategy.execute([coll_req])

        # 验证执行成功
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result

    @pytest.mark.asyncio
    async def test_request_rendering_with_template(self, strategy, api_request):
        """测试请求模板渲染 - 使用真实数据"""
        # 创建带模板变量的请求
        api_request.url = 'https://httpbin.org/get?user_id={{user_id}}'
        api_request.headers = '{"Authorization": "Bearer {{token}}"}'
        api_request.save()

        collection = RequestCollection.objects.create(name='Template Test Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

        context = {'user_id': '123', 'token': 'abc123'}

        results = await strategy.execute([coll_req], context)

        # 验证执行成功
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result

    def test_extract_variables_with_valid_jsonpath(self, strategy):
        """测试使用有效的JSONPath提取变量 - 使用真实数据"""
        result = {
            'response_body': '{"user_id": 123, "token": "abc123"}',
            'success': True
        }
        extract_rules = [
            {'name': 'user_id', 'jsonpath': '$.user_id'},
            {'name': 'auth_token', 'jsonpath': '$.token'}
        ]
        context = {}

        new_context = strategy._extract_variables(result, extract_rules, context)

        assert new_context['user_id'] == 123
        assert new_context['auth_token'] == 'abc123'

    def test_extract_variables_with_invalid_jsonpath(self, strategy):
        """测试使用无效的JSONPath提取变量 - 使用真实数据"""
        result = {
            'response_body': '{"valid_field": "value"}',
            'success': True
        }
        extract_rules = [
            {'name': 'missing_field', 'jsonpath': '$.nonexistent.field'}
        ]
        context = {'existing': 'data'}

        new_context = strategy._extract_variables(result, extract_rules, context)

        # 应该返回原始上下文
        assert new_context == context

    def test_extract_variables_with_invalid_json(self, strategy):
        """测试响应体不是有效JSON时的变量提取 - 使用真实数据"""
        result = {
            'response_body': 'invalid json {',
            'success': True
        }
        extract_rules = [{'name': 'test', 'jsonpath': '$.test'}]
        context = {'existing': 'value'}

        new_context = strategy._extract_variables(result, extract_rules, context)

        # 应该返回原始上下文
        assert new_context == context

    def test_extract_variables_with_missing_rule_fields(self, strategy):
        """测试提取规则缺少必要字段 - 使用真实数据"""
        result = {
            'response_body': '{"field1": "value1", "field2": "value2"}',
            'success': True
        }
        extract_rules = [
            {'name': 'valid_rule', 'jsonpath': '$.field1'},  # 有效规则
            {'jsonpath': '$.field2'},  # 缺少name字段
            {'name': 'missing_jsonpath'},  # 缺少jsonpath字段
            {}  # 完全空的规则
        ]
        context = {}

        new_context = strategy._extract_variables(result, extract_rules, context)

        # 应该只提取有效的规则
        assert 'valid_rule' in new_context
        assert new_context['valid_rule'] == 'value1'
        assert len(new_context) == 1

    def test_extract_variables_from_failed_response(self, strategy):
        """测试从失败的响应中提取变量 - 使用真实数据"""
        result = {
            'response_body': '{"error": "Request failed"}',
            'success': False
        }
        extract_rules = [
            {'name': 'error_message', 'jsonpath': '$.error'}
        ]
        context = {}

        new_context = strategy._extract_variables(result, extract_rules, context)

        # 即使响应失败，也应该能提取变量
        assert new_context['error_message'] == 'Request failed'

    def test_extract_variables_with_complex_jsonpath(self, strategy):
        """测试复杂JSONPath表达式 - 使用真实数据"""
        result = {
            'response_body': json.dumps({
                'store': {
                    'book': [
                        {'category': 'reference', 'author': 'Nigel Rees', 'title': 'Sayings of the Century', 'price': 8.95},
                        {'category': 'fiction', 'author': 'Evelyn Waugh', 'title': 'Sword of Honour', 'price': 12.99},
                        {'category': 'fiction', 'author': 'Herman Melville', 'title': 'Moby Dick', 'isbn': '0-553-21311-3', 'price': 8.99},
                        {'category': 'fiction', 'author': 'J. R. R. Tolkien', 'title': 'The Lord of the Rings', 'isbn': '0-395-19395-8', 'price': 22.99}
                    ],
                    'bicycle': {'color': 'red', 'price': 19.95}
                }
            }),
            'success': True
        }
        extract_rules = [
            {'name': 'first_book_title', 'jsonpath': '$.store.book[0].title'},
            {'name': 'bicycle_price', 'jsonpath': '$.store.bicycle.price'}
        ]
        context = {}

        new_context = strategy._extract_variables(result, extract_rules, context)

        assert new_context['first_book_title'] == 'Sayings of the Century'
        assert new_context['bicycle_price'] == 19.95


@pytest.mark.django_db
class TestRequestRenderer:
    """测试请求渲染器 - 使用真实数据"""

    @pytest.fixture
    def renderer(self):
        return RequestRenderer()

    @pytest.fixture
    def api_request_model(self, db):
        """创建真实的API请求模型实例"""
        return ApiRequest.objects.create(
            name='Template Test Request',
            method='GET',
            url='https://api.example.com/users/{{user_id}}',
            headers='{"Authorization": "Bearer {{token}}"}',
            body='{"user": "{{user_name}}"}'
        )

    def test_render_with_model_instance(self, renderer, api_request_model):
        """测试渲染模型实例 - 使用真实数据"""
        context = {'user_id': '123', 'token': 'abc123', 'user_name': 'john'}

        result = renderer.render(api_request_model, context)

        assert result['id'] == api_request_model.id
        assert result['method'] == 'GET'
        assert result['url'] == 'https://api.example.com/users/123'
        assert result['headers'] == '{"Authorization": "Bearer abc123"}'
        assert result['body'] == '{"user": "john"}'

    def test_render_with_dict(self, renderer):
        """测试渲染字典 - 使用真实数据"""
        api_request = {
            'id': 102,
            'method': 'POST',
            'url': 'https://api.example.com/posts/{{post_id}}',
            'headers': '{"Content-Type": "application/json"}',
            'body': '{"title": "{{title}}", "content": "{{content}}"}'
        }
        context = {'post_id': '456', 'title': 'Test Post', 'content': 'Test content'}

        result = renderer.render(api_request, context)

        assert result['id'] == 102
        assert result['method'] == 'POST'
        assert result['url'] == 'https://api.example.com/posts/456'
        assert result['headers'] == '{"Content-Type": "application/json"}'
        assert result['body'] == '{"title": "Test Post", "content": "Test content"}'

    def test_render_with_nested_dict(self, renderer):
        """测试渲染嵌套字典 - 使用真实数据"""
        api_request = {
            'id': 103,
            'method': 'PUT',
            'url': 'https://api.example.com/items/{{item.id}}',
            'headers': '{"Authorization": "{{auth.type}} {{auth.token}}"}',
            'body': '{"config": {"timeout": {{config.timeout}}, "retries": {{config.retries}}}}'
        }
        context = {
            'item': {'id': '789'},
            'auth': {'type': 'Bearer', 'token': 'xyz789'},
            'config': {'timeout': 30, 'retries': 3}
        }

        result = renderer.render(api_request, context)

        assert result['url'] == 'https://api.example.com/items/789'
        assert result['headers'] == '{"Authorization": "Bearer xyz789"}'
        assert result['body'] == '{"config": {"timeout": 30, "retries": 3}}'

    def test_render_with_missing_variables(self, renderer, api_request_model):
        """测试上下文缺少变量时的渲染 - 使用真实数据"""
        context = {'user_id': '123'}  # 缺少token和user_name

        result = renderer.render(api_request_model, context)

        assert result['url'] == 'https://api.example.com/users/123'
        # 缺少的变量应该保持原样
        assert result['headers'] == '{"Authorization": "Bearer {{token}}"}'
        assert result['body'] == '{"user": "{{user_name}}"}'

    def test_render_with_non_string_values(self, renderer):
        """测试渲染非字符串值 - 使用真实数据"""
        api_request = {
            'id': 104,
            'method': 'POST',
            'url': 'https://api.example.com/data/{{data_id}}',
            'headers': '{}',
            'body': ''
        }
        context = {'data_id': 12345}  # 整数

        result = renderer.render(api_request, context)

        assert result['url'] == 'https://api.example.com/data/12345'

    def test_render_with_empty_context(self, renderer, api_request_model):
        """测试空上下文 - 使用真实数据"""
        result = renderer.render(api_request_model, {})

        # 所有模板变量应该保持原样
        assert result['url'] == 'https://api.example.com/users/{{user_id}}'
        assert result['headers'] == '{"Authorization": "Bearer {{token}}"}'
        assert result['body'] == '{"user": "{{user_name}}"}'

    def test_render_with_empty_template_values(self, renderer):
        """测试渲染空值 - 使用真实数据"""
        api_request = {
            'id': 105,
            'method': 'GET',
            'url': 'https://api.example.com/empty/{{empty_value}}',
            'headers': '{}',
            'body': ''
        }
        context = {'empty_value': ''}

        result = renderer.render(api_request, context)

        assert result['url'] == 'https://api.example.com/empty/'

    def test_render_preserves_request_structure(self, renderer):
        """测试渲染保持请求结构 - 使用真实数据"""
        api_request = {
            'id': 106,
            'method': 'DELETE',
            'url': 'https://api.example.com/items/{{item_id}}',
            'headers': '{}',
            'body': ''
        }
        context = {'item_id': '999'}

        result = renderer.render(api_request, context)

        # 验证所有必要字段都存在
        assert 'id' in result
        assert 'method' in result
        assert 'url' in result
        assert 'headers' in result
        assert 'body' in result


@pytest.mark.django_db
class TestCollectionExecutionStrategyFactory:
    """测试集合执行策略工厂 - 使用真实数据"""

    @pytest.fixture
    def factory(self):
        # 清除工厂状态，确保测试独立
        CollectionExecutionStrategyFactory._strategies = None
        return CollectionExecutionStrategyFactory

    def test_factory_initialization(self, factory):
        """测试工厂初始化"""
        assert factory._strategies is None
        factory._initialize_strategies()
        assert factory._strategies is not None
        assert len(factory._strategies) == 3

    def test_get_strategy_for_concurrent_mode(self, factory):
        """测试获取并发模式的策略"""
        strategy = factory.get_strategy('concurrent')
        assert isinstance(strategy, ConcurrentExecutionStrategy)

    def test_get_strategy_for_sequential_mode(self, factory):
        """测试获取顺序模式的策略"""
        strategy = factory.get_strategy('sequential')
        assert isinstance(strategy, SequentialExecutionStrategy)

    def test_get_strategy_for_chain_mode(self, factory):
        """测试获取链式模式的策略"""
        strategy = factory.get_strategy('chain')
        assert isinstance(strategy, ChainExecutionStrategy)

    def test_get_strategy_for_unsupported_mode(self, factory):
        """测试获取不支持的模式"""
        with pytest.raises(ValueError) as exc_info:
            factory.get_strategy('unsupported_mode')

        assert "Unsupported execution mode: unsupported_mode" in str(exc_info.value)

    def test_register_new_strategy(self, factory):
        """测试注册新策略"""
        class CustomStrategy(CollectionExecutionStrategyInterface):
            def can_execute(self, execution_mode):
                return execution_mode == 'custom'

            async def execute(self, collection_requests, context=None):
                return []

        custom_strategy = CustomStrategy()
        factory.register_strategy(custom_strategy)

        # 验证策略已注册并可用
        strategy = factory.get_strategy('custom')
        assert strategy is custom_strategy

        # 验证策略在列表中
        strategies = factory.get_registered_strategies()
        assert custom_strategy in strategies

    def test_strategy_priority_ordering(self, factory):
        """测试策略优先级排序"""
        factory._initialize_strategies()
        strategies = factory._strategies

        # 验证所有策略类型都存在
        strategy_types = [type(strategy) for strategy in strategies]
        assert ConcurrentExecutionStrategy in strategy_types
        assert SequentialExecutionStrategy in strategy_types
        assert ChainExecutionStrategy in strategy_types

    def test_get_registered_strategies(self, factory):
        """测试获取所有已注册的策略"""
        strategies = factory.get_registered_strategies()
        assert len(strategies) == 3
        assert any(isinstance(s, ConcurrentExecutionStrategy) for s in strategies)
        assert any(isinstance(s, SequentialExecutionStrategy) for s in strategies)
        assert any(isinstance(s, ChainExecutionStrategy) for s in strategies)

    def test_get_registered_strategies_returns_copy(self, factory):
        """测试获取已注册策略返回的是副本"""
        strategies1 = factory.get_registered_strategies()
        strategies2 = factory.get_registered_strategies()

        assert strategies1 is not strategies2
        assert len(strategies1) == len(strategies2)

    def test_multiple_initializations(self, factory):
        """测试多次初始化不会重复创建策略"""
        factory._initialize_strategies()
        first_strategies = factory._strategies.copy()

        factory._initialize_strategies()
        second_strategies = factory._strategies.copy()

        # 应该是同一个列表对象
        assert first_strategies is second_strategies

    def test_factory_singleton_behavior(self, factory):
        """测试工厂单例行为"""
        strategy1 = factory.get_strategy('concurrent')
        strategy2 = factory.get_strategy('concurrent')

        # 应该返回同一个策略实例
        assert strategy1 is strategy2


@pytest.mark.django_db
class TestStrategyIntegration:
    """测试策略集成场景 - 使用真实数据"""

    @pytest.fixture
    def factory(self):
        CollectionExecutionStrategyFactory._strategies = None
        return CollectionExecutionStrategyFactory

    @pytest.fixture
    def api_request(self, db):
        """创建真实的API请求"""
        return ApiRequest.objects.create(
            name='Integration Test API Request',
            method='GET',
            url='https://httpbin.org/get',
            headers='{"Accept": "application/json"}',
            body=''
        )

    @pytest.fixture
    def collection_request(self, db, api_request):
        """创建真实的集合请求"""
        collection = RequestCollection.objects.create(
            name='Integration Test Collection',
            description='Integration Test Collection'
        )
        return CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

    @pytest.mark.asyncio
    async def test_end_to_end_concurrent_execution(self, factory, collection_request):
        """测试并发执行的端到端场景 - 使用真实数据"""
        strategy = factory.get_strategy('concurrent')

        results = await strategy.execute([collection_request])

        # 验证结果格式
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result
        assert 'status_code' in result
        assert 'response_time' in result
        assert 'response_body' in result
        assert result['api_request_id'] == collection_request.api_request.id

    @pytest.mark.asyncio
    async def test_end_to_end_sequential_execution(self, factory, api_request):
        """测试顺序执行的端到端场景 - 使用真实数据"""
        strategy = factory.get_strategy('sequential')

        # 创建多个真实的集合请求
        collection = RequestCollection.objects.create(name='Sequential Integration Collection')
        requests = []

        for i in range(2):
            api_req = ApiRequest.objects.create(
                name=f'Integration Test API Request {i}',
                method='GET',
                url='https://httpbin.org/get',
                headers='{"Accept": "application/json"}',
                body='',
                            )
            coll_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req,
                order_index=i,
                stop_on_failure=False
            )
            requests.append(coll_req)

        results = await strategy.execute(requests)

        # 验证执行了所有请求
        assert len(results) == 2
        # 验证每个结果都有正确的格式
        for result in results:
            assert 'api_request_id' in result
            assert 'success' in result
            assert 'status_code' in result
            assert 'response_time' in result
            assert 'response_body' in result

    @pytest.mark.asyncio
    async def test_end_to_end_chain_execution(self, factory, api_request):
        """测试链式执行的端到端场景 - 使用真实数据"""
        strategy = factory.get_strategy('chain')

        # 创建带提取规则的集合请求
        collection = RequestCollection.objects.create(name='Chain Integration Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )
        # 设置提取规则
        coll_req.extract_rules = [
            {'name': 'origin', 'jsonpath': '$.origin'},
            {'name': 'url', 'jsonpath': '$.url'}
        ]

        results = await strategy.execute([coll_req], {})

        # 验证结果格式
        assert len(results) == 1
        result = results[0]
        assert 'api_request_id' in result
        assert 'success' in result
        assert 'status_code' in result
        assert 'response_time' in result
        assert 'response_body' in result

    def test_strategy_selection_based_on_mode(self, factory):
        """测试基于模式选择策略"""
        # 验证每种模式都能正确选择对应的策略
        concurrent_strategy = factory.get_strategy('concurrent')
        assert isinstance(concurrent_strategy, ConcurrentExecutionStrategy)

        sequential_strategy = factory.get_strategy('sequential')
        assert isinstance(sequential_strategy, SequentialExecutionStrategy)

        chain_strategy = factory.get_strategy('chain')
        assert isinstance(chain_strategy, ChainExecutionStrategy)

    @pytest.mark.asyncio
    async def test_error_handling_across_strategies(self, factory, api_request):
        """测试所有策略的错误处理 - 使用真实数据"""
        # 创建一个无效的API请求来触发错误
        api_request.url = 'invalid://bad-url'
        api_request.save()

        # 测试并发策略错误处理
        concurrent_strategy = factory.get_strategy('concurrent')
        collection = RequestCollection.objects.create(name='Error Test Collection')
        coll_req = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

        results = await concurrent_strategy.execute([coll_req])
        assert len(results) == 1
        assert results[0]['success'] is False
        assert results[0]['error'] is not None

        # 测试顺序策略错误处理
        sequential_strategy = factory.get_strategy('sequential')
        results = await sequential_strategy.execute([coll_req])
        assert len(results) == 1
        assert results[0]['success'] is False
        assert results[0]['error'] is not None

        # 测试链式策略错误处理
        chain_strategy = factory.get_strategy('chain')
        coll_req.extract_rules = []
        results = await chain_strategy.execute([coll_req])
        assert len(results) == 1
        assert results[0]['success'] is False
        assert results[0]['error'] is not None


if __name__ == '__main__':
    pytest.main([__file__])