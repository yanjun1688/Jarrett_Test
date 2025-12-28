"""
异步执行工具单元测试
测试异步API请求执行和批量执行功能
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from testmanager_app.async_utils import (
    execute_single_request_async,
    _validate_assertion_async,
    execute_batch_async,
)


class TestExecuteSingleRequestAsync:
    """测试异步执行单个API请求"""

    @pytest.fixture
    def mock_api_request_model(self):
        """创建模拟的API请求模型实例"""
        api_request = Mock()
        api_request.id = 1
        api_request.method = 'GET'
        api_request.url = 'https://api.example.com/test'
        api_request.headers = '{"Content-Type": "application/json"}'
        api_request.body = ''
        return api_request

    @pytest.fixture
    def mock_api_request_dict(self):
        """创建模拟的API请求字典"""
        return {
            'id': 2,
            'method': 'POST',
            'url': 'https://api.example.com/users',
            'headers': '{"Content-Type": "application/json"}',
            'body': '{"name": "test"}'
        }

    @pytest.fixture
    def mock_httpx_response(self):
        """创建模拟的HTTP响应"""
        response = Mock()
        response.status_code = 200
        response.headers = {'Content-Type': 'application/json'}
        response.text = '{"success": true}'
        response.elapsed = timedelta(seconds=0.123)
        response.json = Mock(return_value={"success": True})
        return response

    @pytest.mark.asyncio
    async def test_execute_get_request_with_model_instance(self, mock_api_request_model, mock_httpx_response):
        """测试使用模型实例执行GET请求"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_httpx_response)
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(mock_api_request_model)

            assert result['api_request_id'] == 1
            assert result['request_method'] == 'GET'
            assert result['request_url'] == 'https://api.example.com/test'
            assert result['response_status'] == 200
            assert result['response_body'] == '{"success": true}'
            assert result['response_time'] == 0.123
            assert result['error_message'] is None
            assert result['success'] is True
            assert 'execution_time' in result

    @pytest.mark.asyncio
    async def test_execute_post_request_with_json_body(self, mock_api_request_dict, mock_httpx_response):
        """测试执行带JSON请求体的POST请求"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_httpx_response)
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(mock_api_request_dict)

            assert result['api_request_id'] == 2
            assert result['request_method'] == 'POST'
            assert result['response_status'] == 200
            assert result['success'] is True

            # 验证请求被正确调用
            mock_client.request.assert_called_once_with(
                method='POST',
                url='https://api.example.com/users',
                headers={'Content-Type': 'application/json'},
                json={'name': 'test'},
                timeout=60.0
            )

    @pytest.mark.asyncio
    async def test_execute_request_with_text_body(self, mock_api_request_dict, mock_httpx_response):
        """测试执行带文本请求体的请求"""
        # 修改请求体为非JSON格式
        mock_api_request_dict['body'] = 'raw text data'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_httpx_response)
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(mock_api_request_dict)

            assert result['response_status'] == 200
            assert result['success'] is True

            # 验证文本请求体被正确处理
            mock_client.request.assert_called_once_with(
                method='POST',
                url='https://api.example.com/users',
                headers={'Content-Type': 'application/json'},
                content=b'raw text data',
                timeout=60.0
            )

    @pytest.mark.asyncio
    async def test_execute_request_with_multiline_headers(self, mock_api_request_dict, mock_httpx_response):
        """测试执行带多行头部的请求"""
        mock_api_request_dict['headers'] = 'Content-Type: application/json\nAuthorization: Bearer token123'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_httpx_response)
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(mock_api_request_dict)

            expected_headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer token123'
            }

            # 验证多行头部被正确解析
            call_args = mock_client.request.call_args
            assert call_args.kwargs['headers'] == expected_headers

    @pytest.mark.asyncio
    async def test_execute_request_with_invalid_json_headers(self, mock_api_request_dict, mock_httpx_response):
        """测试执行带无效JSON头部的请求"""
        mock_api_request_dict['headers'] = 'invalid json {'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_httpx_response)
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(mock_api_request_dict)

            # 当JSON解析失败时,应该使用原始字符串解析
            call_args = mock_client.request.call_args
            # 应该没有头部,因为无效格式无法解析
            assert call_args.kwargs['headers'] == {}

    @pytest.mark.asyncio
    async def test_execute_request_with_proxy(self, mock_api_request_model, mock_httpx_response):
        """测试通过代理执行请求"""
        with patch.dict('os.environ', {'HTTP_PROXY': 'http://proxy.example.com:8080'}):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.request = AsyncMock(return_value=mock_httpx_response)
                mock_client_class.return_value = mock_client

                result = await execute_single_request_async(mock_api_request_model)

                # 验证代理设置
                mock_client_class.assert_called_once_with(proxy='http://proxy.example.com:8080')
                assert result['response_status'] == 200

    @pytest.mark.asyncio
    async def test_execute_request_with_exception(self, mock_api_request_model):
        """测试执行请求时发生异常"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(side_effect=Exception("Network error"))
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(mock_api_request_model)

            assert result['response_status'] is None
            assert result['error_message'] == "Network error"
            assert result['response_body'] is None
            assert result['success'] is False

    @pytest.mark.asyncio
    async def test_execute_request_with_awaitable_input(self, mock_api_request_model, mock_httpx_response):
        """测试输入为可等待对象的情况"""
        # 创建可等待对象
        async def get_api_request():
            return mock_api_request_model

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_httpx_response)
            mock_client_class.return_value = mock_client

            result = await execute_single_request_async(get_api_request())

            assert result['api_request_id'] == 1
            assert result['response_status'] == 200

    @pytest.mark.asyncio
    async def test_execute_request_with_assertions(self, mock_api_request_model, mock_httpx_response):
        """测试执行请求并验证断言 - 修复版"""
        # 创建模拟断言
        mock_assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        mock_assertion.id = 1
        mock_assertion.name = 'Status Code Check'
        mock_assertion.assertion_type = 'status_code'
        mock_assertion.target_value = '200'

        # 使用 sync_to_async 包装数据库查询
        with patch('testmanager_app.async_utils.sync_to_async') as mock_sync_to_async:
            # 模拟 sync_to_async 返回一个异步函数
            async def mock_get_assertions():
                return [mock_assertion]
            
            mock_sync_to_async.return_value = mock_get_assertions

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.request = AsyncMock(return_value=mock_httpx_response)
                mock_client_class.return_value = mock_client

                result = await execute_single_request_async(mock_api_request_model)

                assert 'assertions' in result
                assert 'all_assertions_passed' in result
                assert result['all_assertions_passed'] is True
                assert len(result['assertions']) == 1
                assert result['assertions'][0]['passed'] is True

    @pytest.mark.asyncio
    async def test_execute_request_with_assertion_error(self, mock_api_request_model, mock_httpx_response):
        """测试断言验证过程中发生错误 - 修复版"""
        with patch('testmanager_app.async_utils.sync_to_async') as mock_sync_to_async:
            # 模拟数据库错误
            async def mock_get_assertions_error():
                raise Exception("Database error")
            
            mock_sync_to_async.return_value = mock_get_assertions_error

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.request = AsyncMock(return_value=mock_httpx_response)
                mock_client_class.return_value = mock_client

                result = await execute_single_request_async(mock_api_request_model)

                assert 'assertion_error' in result
                assert 'Database error' in result['assertion_error']


class TestValidateAssertionAsync:
    """测试异步断言验证"""

    @pytest.fixture
    def mock_response(self):
        """创建模拟响应对象"""
        response = Mock()
        response.status_code = 200
        response.text = '{"user": "test", "count": 42}'
        response.headers = {
            'Content-Type': 'application/json',
            'X-Custom-Header': 'custom-value'
        }
        response.json = Mock(return_value={"user": "test", "count": 42})
        return response

    @pytest.fixture
    def mock_request_result(self):
        """创建模拟请求结果"""
        return {
            'response_time': 0.123
        }

    @pytest.mark.asyncio
    async def test_validate_status_code_assertion_success(self, mock_response, mock_request_result):
        """测试状态码断言验证成功"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Status Code Test'
        assertion.assertion_type = 'status_code'
        assertion.target_value = '200'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is True
        assert result['actual_value'] == '200'
        assert result['target_value'] == '200'
        assert result['type'] == 'status_code'

    @pytest.mark.asyncio
    async def test_validate_status_code_assertion_failure(self, mock_response, mock_request_result):
        """测试状态码断言验证失败"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Status Code Test'
        assertion.assertion_type = 'status_code'
        assertion.target_value = '404'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert result['actual_value'] == '200'
        assert result['target_value'] == '404'

    @pytest.mark.asyncio
    async def test_validate_contains_assertion_success(self, mock_response, mock_request_result):
        """测试包含断言验证成功"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Contains Test'
        assertion.assertion_type = 'contains'
        assertion.target_value = 'user'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is True
        assert 'user' in result['actual_value']
        assert result['target_value'] == 'user'

    @pytest.mark.asyncio
    async def test_validate_contains_assertion_failure(self, mock_response, mock_request_result):
        """测试包含断言验证失败"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Contains Test'
        assertion.assertion_type = 'contains'
        assertion.target_value = 'nonexistent'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert result['actual_value'] == '{"user": "test", "count": 42}'

    @pytest.mark.asyncio
    async def test_validate_json_equals_assertion_success(self, mock_response, mock_request_result):
        """测试JSON相等断言验证成功"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'JSON Equals Test'
        assertion.assertion_type = 'json_equals'
        assertion.target_value = '{"user": "test", "count": 42}'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is True
        # 注意：actual_value 应该是 JSON 字符串
        actual_json = json.loads(result['actual_value'])
        assert actual_json == {"user": "test", "count": 42}

    @pytest.mark.asyncio
    async def test_validate_json_equals_assertion_invalid_json(self, mock_response, mock_request_result):
        """测试JSON相等断言验证时JSON解析失败"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'JSON Equals Test'
        assertion.assertion_type = 'json_equals'
        assertion.target_value = 'invalid json {'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert 'JSON解析失败' in result['actual_value']

    @pytest.mark.asyncio
    async def test_validate_response_time_assertion_success(self, mock_response, mock_request_result):
        """测试响应时间断言验证成功"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Response Time Test'
        assertion.assertion_type = 'response_time'
        assertion.target_value = '0.5'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is True
        assert result['actual_value'] == '0.123'
        assert float(result['actual_value']) <= float(result['target_value'])

    @pytest.mark.asyncio
    async def test_validate_response_time_assertion_failure(self, mock_response, mock_request_result):
        """测试响应时间断言验证失败"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Response Time Test'
        assertion.assertion_type = 'response_time'
        assertion.target_value = '0.1'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert float(result['actual_value']) > float(result['target_value'])

    @pytest.mark.asyncio
    async def test_validate_header_exists_assertion_success(self, mock_response, mock_request_result):
        """测试头部存在断言验证成功"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Header Exists Test'
        assertion.assertion_type = 'header_exists'
        assertion.target_value = 'Content-Type'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is True
        assert result['actual_value'] == 'application/json'

    @pytest.mark.asyncio
    async def test_validate_header_exists_assertion_failure(self, mock_response, mock_request_result):
        """测试头部存在断言验证失败"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Header Exists Test'
        assertion.assertion_type = 'header_exists'
        assertion.target_value = 'Non-Existent-Header'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert result['actual_value'] == ''

    @pytest.mark.asyncio
    async def test_validate_header_equals_assertion_success(self, mock_response, mock_request_result):
        """测试头部相等断言验证成功"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Header Equals Test'
        assertion.assertion_type = 'header_equals'
        assertion.target_value = 'Content-Type: application/json'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is True
        assert result['actual_value'] == 'application/json'

    @pytest.mark.asyncio
    async def test_validate_header_equals_assertion_invalid_format(self, mock_response, mock_request_result):
        """测试头部相等断言格式错误"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Header Equals Test'
        assertion.assertion_type = 'header_equals'
        assertion.target_value = 'InvalidFormat'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert '格式错误' in result['actual_value']

    @pytest.mark.asyncio
    async def test_validate_unknown_assertion_type(self, mock_response, mock_request_result):
        """测试未知的断言类型"""
        assertion = Mock(spec=['id', 'name', 'assertion_type', 'target_value'])
        assertion.id = 1
        assertion.name = 'Unknown Test'
        assertion.assertion_type = 'unknown_type'
        assertion.target_value = 'test'

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert '未知的断言类型' in result['actual_value']

    @pytest.mark.asyncio
    async def test_validate_assertion_with_exception(self, mock_response, mock_request_result):
        """测试断言验证过程中发生异常"""
        assertion = Mock()
        assertion.id = 1
        # 模拟访问 assertion_type 时抛出异常
        type(assertion).assertion_type = property(lambda self: (_ for _ in ()).throw(Exception("Test error")))

        result = await _validate_assertion_async(assertion, mock_response, mock_request_result)

        assert result['passed'] is False
        assert '验证失败' in result['actual_value']


class TestExecuteBatchAsync:
    """测试异步批量执行请求"""

    @pytest.fixture
    def mock_requests_data(self):
        """创建模拟的请求数据列表"""
        return [
            {
                'id': 1,
                'method': 'GET',
                'url': 'https://api.example.com/test1',
                'headers': '{}',
                'body': ''
            },
            {
                'id': 2,
                'method': 'POST',
                'url': 'https://api.example.com/test2',
                'headers': '{}',
                'body': ''
            },
            {
                'id': 3,
                'method': 'GET',
                'url': 'https://api.example.com/test3',
                'headers': '{}',
                'body': ''
            }
        ]

    @pytest.fixture
    def mock_success_result(self):
        """创建模拟的成功执行结果"""
        return {
            'api_request_id': 1,
            'request_method': 'GET',
            'request_url': 'https://api.example.com/test1',
            'response_status': 200,
            'error_message': None,
            'success': True
        }

    @pytest.mark.asyncio
    async def test_execute_concurrent_batch(self, mock_requests_data, mock_success_result):
        """测试并发批量执行"""
        with patch('testmanager_app.async_utils.execute_single_request_async',
                   return_value=mock_success_result) as mock_execute:

            results = await execute_batch_async(mock_requests_data, execution_mode='concurrent')

            assert len(results) == 3
            assert mock_execute.call_count == 3
            # 验证所有结果都成功
            assert all(not isinstance(r, Exception) for r in results)

    @pytest.mark.asyncio
    async def test_execute_sequential_batch(self, mock_requests_data, mock_success_result):
        """测试顺序批量执行"""
        with patch('testmanager_app.async_utils.execute_single_request_async',
                   return_value=mock_success_result) as mock_execute:

            results = await execute_batch_async(mock_requests_data, execution_mode='sequential')

            assert len(results) == 3
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_chain_batch(self, mock_requests_data):
        """测试链式批量执行"""
        mock_result = {
            'api_request_id': 1,
            'request_method': 'GET',
            'response_status': 200,
            'all_assertions_passed': True,
            'success': True
        }
        
        with patch('testmanager_app.async_utils.execute_single_request_async',
                   return_value=mock_result) as mock_execute:

            results = await execute_batch_async(mock_requests_data, execution_mode='chain')

            assert len(results) == 3
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_batch_with_invalid_mode(self, mock_requests_data):
        """测试使用无效的执行模式"""
        with pytest.raises(ValueError) as exc_info:
            await execute_batch_async(mock_requests_data, execution_mode='invalid')

        assert "不支持的执行模式" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_sequential_batch_with_exception(self, mock_requests_data):
        """测试顺序批量执行时发生异常"""
        with patch('testmanager_app.async_utils.execute_single_request_async',
                   side_effect=Exception("Execution error")) as mock_execute:

            results = await execute_batch_async(mock_requests_data, execution_mode='sequential')

            assert len(results) == 3
            assert all('error' in result for result in results)

    @pytest.mark.asyncio
    async def test_execute_chain_batch_with_exception(self, mock_requests_data):
        """测试链式批量执行时发生异常"""
        with patch('testmanager_app.async_utils.execute_single_request_async',
                   side_effect=Exception("Chain execution error")) as mock_execute:

            results = await execute_batch_async(mock_requests_data, execution_mode='chain')

            # 链式执行遇到异常应该停止
            assert len(results) == 1
            assert 'error' in results[0]

    @pytest.mark.asyncio
    async def test_execute_concurrent_batch_with_max_concurrent(self, mock_requests_data, mock_success_result):
        """测试并发批量执行时限制最大并发数"""
        with patch('testmanager_app.async_utils.execute_single_request_async',
                   return_value=mock_success_result) as mock_execute:

            results = await execute_batch_async(
                mock_requests_data, 
                execution_mode='concurrent', 
                max_concurrent=1
            )

            assert len(results) == 3
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_batch_with_empty_requests(self):
        """测试执行空请求列表"""
        results = await execute_batch_async([])

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_execute_batch_with_single_request(self, mock_success_result):
        """测试执行单个请求"""
        single_request = [{
            'id': 1,
            'method': 'GET',
            'url': 'https://api.example.com/test',
            'headers': '{}',
            'body': ''
        }]

        with patch('testmanager_app.async_utils.execute_single_request_async',
                   return_value=mock_success_result):

            results = await execute_batch_async(single_request)

            assert len(results) == 1
            assert results[0]['success'] is True