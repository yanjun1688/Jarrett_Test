"""
链式执行变量传递集成测试
测试链式执行模式中变量提取、模板渲染和上下文传递功能 - 使用真实调用链路
覆盖率目标：70%
"""

import pytest
import json
from testmanager_app.models import ApiRequest, RequestCollection, CollectionRequest
from testmanager_app.collection_execution_strategies import ChainExecutionStrategy


@pytest.mark.django_db
class TestChainExecutionVariablePassing:
    """测试链式执行中的变量传递功能 - 使用真实数据"""

    @pytest.fixture
    def strategy(self):
        """创建链式执行策略实例"""
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
            name='Chain Variable Test Collection',
            description='Test Collection for Chain Variable Passing'
        )
        return CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=1,
            stop_on_failure=False
        )

    class TestVariableExtraction:
        """测试变量提取功能 - 使用真实数据"""

        def test_extract_simple_variables(self, strategy):
            """测试提取简单变量 - 使用真实数据"""
            result = {
                'response_body': '{"user_id": 123, "token": "abc123xyz", "status": "active"}',
                'success': True
            }
            extract_rules = [
                {'name': 'user_id', 'jsonpath': '$.user_id'},
                {'name': 'auth_token', 'jsonpath': '$.token'},
                {'name': 'user_status', 'jsonpath': '$.status'}
            ]
            context = {}

            new_context = strategy._extract_variables(result, extract_rules, context)

            assert new_context['user_id'] == 123
            assert new_context['auth_token'] == 'abc123xyz'
            assert new_context['user_status'] == 'active'

        def test_extract_nested_variables(self, strategy):
            """测试提取嵌套变量 - 使用真实数据"""
            result = {
                'response_body': json.dumps({
                    'data': {
                        'user': {
                            'id': 456,
                            'profile': {
                                'name': 'John Doe',
                                'email': 'john@example.com'
                            }
                        },
                        'metadata': {
                            'version': '1.0',
                            'timestamp': '2024-01-01T00:00:00Z'
                        }
                    }
                }),
                'success': True
            }
            extract_rules = [
                {'name': 'user_id', 'jsonpath': '$.data.user.id'},
                {'name': 'user_name', 'jsonpath': '$.data.user.profile.name'},
                {'name': 'api_version', 'jsonpath': '$.data.metadata.version'}
            ]
            context = {}

            new_context = strategy._extract_variables(result, extract_rules, context)

            assert new_context['user_id'] == 456
            assert new_context['user_name'] == 'John Doe'
            assert new_context['api_version'] == '1.0'

        def test_extract_array_variables(self, strategy):
            """测试提取数组中的变量 - 使用真实数据"""
            result = {
                'response_body': json.dumps({
                    'items': [
                        {'id': 1, 'name': 'Item 1'},
                        {'id': 2, 'name': 'Item 2'},
                        {'id': 3, 'name': 'Item 3'}
                    ],
                    'first_item': {'id': 10, 'name': 'First'}
                }),
                'success': True
            }
            extract_rules = [
                {'name': 'first_item_id', 'jsonpath': '$.items[0].id'},
                {'name': 'first_item_name', 'jsonpath': '$.items[0].name'},
                {'name': 'first_item_direct', 'jsonpath': '$.first_item.id'}
            ]
            context = {}

            new_context = strategy._extract_variables(result, extract_rules, context)

            assert new_context['first_item_id'] == 1
            assert new_context['first_item_name'] == 'Item 1'
            assert new_context['first_item_direct'] == 10

        def test_extract_variables_preserves_existing_context(self, strategy):
            """测试提取变量时保留现有上下文 - 使用真实数据"""
            result = {
                'response_body': '{"new_token": "xyz789"}',
                'success': True
            }
            extract_rules = [
                {'name': 'token', 'jsonpath': '$.new_token'}
            ]
            context = {'existing_key': 'existing_value', 'user_id': 123}

            new_context = strategy._extract_variables(result, extract_rules, context)

            assert new_context['existing_key'] == 'existing_value'
            assert new_context['user_id'] == 123
            assert new_context['token'] == 'xyz789'

        def test_extract_variables_with_invalid_jsonpath(self, strategy):
            """测试使用无效JSONPath提取变量 - 使用真实数据"""
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
            extract_rules = [
                {'name': 'test', 'jsonpath': '$.test'}
            ]
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

    class TestTemplateRendering:
        """测试模板渲染功能 - 使用真实数据"""

        def test_render_simple_template(self, strategy):
            """测试渲染简单模板 - 使用真实数据"""
            api_request = ApiRequest.objects.create(
                name='Template Test Request',
                method='GET',
                url='https://api.example.com/users/{{user_id}}',
                headers='{"Authorization": "Bearer {{token}}"}',
                body=''
            )
            context = {'user_id': '123', 'token': 'abc123'}

            from testmanager_app.collection_execution_strategies import RequestRenderer
            renderer = RequestRenderer()
            result = renderer.render(api_request, context)

            assert result['url'] == 'https://api.example.com/users/123'
            assert result['headers'] == '{"Authorization": "Bearer abc123"}'

        def test_render_with_missing_variables(self, strategy):
            """测试上下文缺少变量时的渲染 - 使用真实数据"""
            api_request = ApiRequest.objects.create(
                name='Missing Vars Test Request',
                method='POST',
                url='https://api.example.com/data/{{required_id}}',
                headers='{"X-Token": "{{token}}"}',
                body='{"user": "{{user_name}}"}'
            )
            context = {'required_id': '456'}  # 缺少token和user_name

            from testmanager_app.collection_execution_strategies import RequestRenderer
            renderer = RequestRenderer()
            result = renderer.render(api_request, context)

            assert result['url'] == 'https://api.example.com/data/456'
            # 缺少的变量应该保持原样
            assert result['headers'] == '{"X-Token": "{{token}}"}'
            assert result['body'] == '{"user": "{{user_name}}"}'

        def test_render_with_nested_variables(self, strategy):
            """测试渲染嵌套变量 - 使用真实数据"""
            api_request = ApiRequest.objects.create(
                name='Nested Vars Test Request',
                method='GET',
                url='https://api.example.com/users/{{user.profile.id}}',
                headers='{"Authorization": "{{auth.type}} {{auth.token}}"}',
                body=''
            )
            context = {
                'user': {'profile': {'id': '789'}},
                'auth': {'type': 'Bearer', 'token': 'xyz789'}
            }

            from testmanager_app.collection_execution_strategies import RequestRenderer
            renderer = RequestRenderer()
            result = renderer.render(api_request, context)

            assert result['url'] == 'https://api.example.com/users/789'
            assert result['headers'] == '{"Authorization": "Bearer xyz789"}'

        def test_render_with_special_characters(self, strategy):
            """测试渲染包含特殊字符的变量 - 使用真实数据"""
            api_request = ApiRequest.objects.create(
                name='Special Chars Test Request',
                method='GET',
                url='https://api.example.com/search?q={{query}}',
                headers='{"User-Agent": "{{user_agent}}"}',
                body=''
            )
            context = {
                'query': 'test query with spaces & special chars!',
                'user_agent': 'TestApp/1.0 (Windows NT 10.0; Win64; x64)'
            }

            from testmanager_app.collection_execution_strategies import RequestRenderer
            renderer = RequestRenderer()
            result = renderer.render(api_request, context)

            assert 'test query with spaces & special chars!' in result['url']
            assert 'TestApp/1.0 (Windows NT 10.0; Win64; x64)' in result['headers']

    @pytest.mark.django_db
    class TestChainExecutionFlow:
        """测试链式执行流程 - 使用真实数据"""

        @pytest.mark.asyncio
        async def test_single_request_chain_execution(self, strategy, collection_request):
            """测试单个请求的链式执行 - 使用真实数据"""
            # 设置提取规则
            collection_request.extract_rules = [
                {'name': 'response_url', 'jsonpath': '$.url'},
                {'name': 'response_origin', 'jsonpath': '$.origin'}
            ]

            results = await strategy.execute([collection_request])

            # 验证执行成功
            assert len(results) == 1
            result = results[0]
            assert 'api_request_id' in result
            assert 'success' in result
            assert 'status_code' in result
            assert 'response_time' in result
            assert 'response_body' in result

        @pytest.mark.asyncio
        async def test_multiple_requests_with_variable_passing(self, strategy, api_request):
            """测试多个请求间的变量传递 - 使用真实数据"""
            # 创建第一个请求：提取变量
            api_req1 = ApiRequest.objects.create(
                name='First API Request',
                method='GET',
                url='https://httpbin.org/get',
                headers='{"Accept": "application/json"}',
                body='',
                            )
            collection = RequestCollection.objects.create(name='Variable Passing Collection')
            first_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req1,
                order_index=1,
                stop_on_failure=False
            )
            # 设置提取规则
            first_req.extract_rules = [
                {'name': 'user_agent', 'jsonpath': '$.headers.User-Agent'},
                {'name': 'origin', 'jsonpath': '$.origin'}
            ]

            # 创建第二个请求：使用提取的变量
            api_req2 = ApiRequest.objects.create(
                name='Second API Request',
                method='POST',
                url='https://httpbin.org/post',
                headers='{"User-Agent": "{{user_agent}}", "X-Origin": "{{origin}}"}',
                body='{"data": "test"}',
                            )
            second_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req2,
                order_index=2,
                stop_on_failure=False
            )

            # 执行链式请求
            results = await strategy.execute([first_req, second_req])

            # 验证执行了所有请求
            assert len(results) == 2
            assert all(result['success'] for result in results)

        @pytest.mark.asyncio
        async def test_chain_execution_with_failed_request(self, strategy, api_request):
            """测试链式执行中请求失败的情况 - 使用真实数据"""
            # 创建第一个请求成功
            collection = RequestCollection.objects.create(name='Failure Test Collection')
            first_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_request,
                order_index=1,
                stop_on_failure=False
            )
            first_req.extract_rules = [
                {'name': 'important_var', 'jsonpath': '$.url'}
            ]

            # 创建第二个请求失败（使用无效URL）
            api_req2 = ApiRequest.objects.create(
                name='Failed API Request',
                method='GET',
                url='invalid://bad-url',
                headers='{}',
                body='',
                            )
            second_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req2,
                order_index=2,
                stop_on_failure=True  # 启用失败停止
            )

            # 创建第三个请求（不应该执行）
            api_req3 = ApiRequest.objects.create(
                name='Third API Request',
                method='GET',
                url='https://httpbin.org/get',
                headers='{}',
                body='',
                            )
            third_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req3,
                order_index=3,
                stop_on_failure=False
            )

            results = await strategy.execute([first_req, second_req, third_req])

            # 应该只执行两个请求（第三个不应该执行）
            assert len(results) == 2
            assert results[0]['success'] is True
            assert results[1]['success'] is False

        @pytest.mark.asyncio
        async def test_chain_execution_with_stop_on_failure_disabled(self, strategy, api_request):
            """测试禁用失败停止时的链式执行 - 使用真实数据"""
            # 创建第一个请求失败
            api_req1 = ApiRequest.objects.create(
                name='Failed API Request',
                method='GET',
                url='invalid://bad-url',
                headers='{}',
                body='',
                            )
            collection = RequestCollection.objects.create(name='Continue On Failure Collection')
            first_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req1,
                order_index=1,
                stop_on_failure=False  # 禁用失败停止
            )

            # 创建第二个请求应该继续执行
            api_req2 = ApiRequest.objects.create(
                name='Success API Request',
                method='GET',
                url='https://httpbin.org/get',
                headers='{"Accept": "application/json"}',
                body='',
                            )
            second_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req2,
                order_index=2,
                stop_on_failure=False
            )

            results = await strategy.execute([first_req, second_req])

            assert len(results) == 2
            assert results[0]['success'] is False
            assert results[1]['success'] is True

        @pytest.mark.asyncio
        async def test_complex_variable_extraction_scenario(self, strategy, api_request):
            """测试复杂的变量提取场景 - 使用真实数据"""
            # 创建第一个请求：提取多个变量
            api_req1 = ApiRequest.objects.create(
                name='Multi-Var API Request',
                method='GET',
                url='https://httpbin.org/get',
                headers='{"Accept": "application/json"}',
                body='',
                            )
            collection = RequestCollection.objects.create(name='Complex Scenario Collection')
            first_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req1,
                order_index=1,
                stop_on_failure=False
            )
            # 设置多个提取规则
            first_req.extract_rules = [
                {'name': 'user_agent', 'jsonpath': '$.headers.User-Agent'},
                {'name': 'origin', 'jsonpath': '$.origin'},
                {'name': 'url', 'jsonpath': '$.url'}
            ]

            # 创建第二个请求：使用所有提取的变量
            api_req2 = ApiRequest.objects.create(
                name='Use All Vars API Request',
                method='POST',
                url='https://httpbin.org/post',
                headers='{"User-Agent": "{{user_agent}}", "X-Origin": "{{origin}}", "X-URL": "{{url}}"}',
                body='{"test": "data"}',
                            )
            second_req = CollectionRequest.objects.create(
                collection=collection,
                api_request=api_req2,
                order_index=2,
                stop_on_failure=False
            )

            results = await strategy.execute([first_req, second_req])

            assert len(results) == 2
            assert all(result['success'] for result in results)

    class TestErrorHandling:
        """测试错误处理 - 使用真实数据"""

        def test_extract_variables_with_jsonpath_error(self, strategy):
            """测试JSONPath解析错误处理 - 使用真实数据"""
            result = {
                'response_body': '{"data": "value"}',
                'success': True
            }
            extract_rules = [
                {'name': 'error_field', 'jsonpath': '$$$invalid$$$'}  # 无效语法
            ]
            context = {'existing': 'data'}

            new_context = strategy._extract_variables(result, extract_rules, context)

            # 应该返回原始上下文
            assert new_context == context

        @pytest.mark.asyncio
        async def test_chain_execution_with_rendering_error(self, strategy, collection_request):
            """测试模板渲染错误处理 - 使用真实数据"""
            # 创建一个会导致渲染错误的请求
            collection_request.api_request.url = None  # None值会导致渲染错误
            collection_request.api_request.save()

            results = await strategy.execute([collection_request])

            # 应该处理错误并返回错误结果
            assert len(results) == 1
            assert results[0]['success'] is False
            assert 'error' in results[0]

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
                {'name': 'fiction_books_count', 'jsonpath': '$.store.book[?(@.category == "fiction")].length()'},
                {'name': 'bicycle_price', 'jsonpath': '$.store.bicycle.price'},
                {'name': 'all_book_authors', 'jsonpath': '$.store.book[*].author'}
            ]
            context = {}

            new_context = strategy._extract_variables(result, extract_rules, context)

            assert new_context['first_book_title'] == 'Sayings of the Century'
            assert new_context['bicycle_price'] == 19.95
            assert 'all_book_authors' in new_context


if __name__ == '__main__':
    pytest.main([__file__])