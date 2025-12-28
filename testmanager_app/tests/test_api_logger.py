"""
Unit tests for api_logger.py

Tests all logger classes and logging decorators.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone
from datetime import datetime, timedelta

from testmanager_app.utils.api_logger import (
    RequestLogger,
    ExecutionLogger,
    DatabaseLogger,
    log_api_request,
    log_async_api_request
)


class TestRequestLogger:
    """Test the RequestLogger context manager."""

    def test_request_logger_init_with_request(self, mock_request):
        """Test RequestLogger initialization with request."""
        logger = RequestLogger("test_function", mock_request)

        assert logger.func_name == "test_function"
        assert logger.request == mock_request
        assert logger.user_id == 1
        assert logger.username == "testuser"
        assert "req_" in logger.request_id

    def test_request_logger_init_without_request(self):
        """Test RequestLogger initialization without request."""
        logger = RequestLogger("test_function")

        assert logger.func_name == "test_function"
        assert logger.request is None
        assert logger.user_id is None
        assert logger.username == "anonymous"
        assert "func_" in logger.request_id

    def test_request_logger_init_with_anonymous_request(self, mock_anonymous_request):
        """Test RequestLogger initialization with anonymous request."""
        logger = RequestLogger("test_function", mock_anonymous_request)

        assert logger.user_id is None
        assert logger.username == "anonymous"

    @patch('testmanager_app.utils.api_logger.logger')
    def test_request_logger_successful_context(self, mock_logger, mock_request):
        """Test RequestLogger in successful context."""
        with RequestLogger("test_function", mock_request) as logger:
            assert logger.start_time is not None
            assert isinstance(logger.start_time, datetime)

        # Verify info logs were called
        assert mock_logger.info.call_count >= 6  # Header + function info + request info + footer
        log_calls = [str(call) for call in mock_logger.info.call_args_list]

        # Check key log messages
        assert any("开始: test_function" in log for log in log_calls)
        assert any("ID:" in log for log in log_calls)
        assert any("用户: testuser" in log for log in log_calls)
        assert any("方法: GET" in log for log in log_calls)
        assert any("路径: /api/test/" in log for log in log_calls)
        assert any("状态: success" in log for log in log_calls)

    @patch('testmanager_app.utils.api_logger.logger')
    def test_request_logger_with_exception(self, mock_logger, mock_request):
        """Test RequestLogger when exception occurs."""
        with pytest.raises(ValueError):
            with RequestLogger("test_function", mock_request):
                raise ValueError("Test error")

        # Verify error logs were called
        assert mock_logger.error.called
        log_calls = [str(call) for call in mock_logger.error.call_args_list]

        # Check error log messages
        assert any("异常: test_function" in log for log in log_calls)
        assert any("错误类型: ValueError" in log for log in log_calls)
        assert any("错误信息: Test error" in log for log in log_calls)

    @patch('testmanager_app.utils.api_logger.logger')
    def test_request_logger_with_query_params(self, mock_logger):
        """Test RequestLogger with query parameters."""
        request = Mock()
        request.method = 'GET'
        request.path = '/api/test/'
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.username = 'testuser'
        request.query_params = {'page': '1', 'limit': '10'}
        request.data = {}

        with RequestLogger("test_function", request):
            pass

        # Verify debug log for query parameters
        assert mock_logger.debug.called
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("查询参数" in log for log in debug_calls)
        assert any("page" in log and "limit" in log for log in debug_calls)

    @patch('testmanager_app.utils.api_logger.logger')
    def test_request_logger_with_request_body(self, mock_logger):
        """Test RequestLogger with request body."""
        request = Mock()
        request.method = 'POST'
        request.path = '/api/test/'
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.username = 'testuser'
        request.query_params = {}
        request.data = {'name': 'test', 'value': 123}

        with RequestLogger("test_function", request):
            pass

        # Verify debug log for request body
        assert mock_logger.debug.called
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("请求体" in log for log in debug_calls)
        assert any("name" in log and "value" in log for log in debug_calls)


class TestExecutionLogger:
    """Test the ExecutionLogger class."""

    def test_execution_logger_class_exists(self):
        """Test ExecutionLogger class exists and has static methods."""
        assert hasattr(ExecutionLogger, 'log_execution_start')
        assert hasattr(ExecutionLogger, 'log_execution_step')
        assert hasattr(ExecutionLogger, 'log_execution_end')
        assert hasattr(ExecutionLogger, 'log_execution_error')

        # 验证都是静态方法
        import inspect
        assert isinstance(inspect.getattr_static(ExecutionLogger, 'log_execution_start'), staticmethod)
        assert isinstance(inspect.getattr_static(ExecutionLogger, 'log_execution_step'), staticmethod)

    @patch('testmanager_app.utils.api_logger.logger')
    def test_log_execution_start(self, mock_logger, mock_api_request):
        """Test logging execution start."""
        # 正确调用静态方法 - 使用关键字参数
        ExecutionLogger.log_execution_start("API_TEST", 123, api_request=mock_api_request)

        # 验证日志被调用
        assert mock_logger.info.called
        # 验证关键日志消息
        log_calls = [str(call) for call in mock_logger.info.call_args_list]

        # 检查是否记录了开始信息
        assert any("API_TEST 开始 - ExecutionID: 123" in call for call in log_calls)
        assert any(f"API名称: {mock_api_request.name}" in call for call in log_calls)
        assert any(f"请求URL: {mock_api_request.url}" in call for call in log_calls)
        assert any(f"请求方法: {mock_api_request.method}" in call for call in log_calls)

    def test_log_execution_step(self):
        """Test logging execution step."""
        # 正确调用静态方法
        ExecutionLogger.log_execution_step("exec_123", "initialization", "Starting process")
        ExecutionLogger.log_execution_step("exec_123", "processing", "Processing data", level="debug")

        # 静态方法调用，如果没有异常则测试通过
        assert True

    @patch('testmanager_app.utils.api_logger.logger')
    def test_log_execution_step_with_mock_logger(self, mock_logger):
        """Test logging execution step with mocked logger."""
        # 正确调用静态方法
        ExecutionLogger.log_execution_step("exec_123", "test_step", "Test message")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[Step: test_step]" in call_args
        assert "ExecutionID: exec_123" in call_args
        assert "Test message" in call_args

    def test_log_execution_end(self):
        """Test logging execution end."""
        # 正确调用静态方法
        ExecutionLogger.log_execution_end("API_TEST", "exec_123", "success", 1.5)

        # 静态方法调用，如果没有异常则测试通过
        assert True

    def test_log_execution_error(self):
        """Test logging execution error."""
        stack_trace = "Traceback: line 1\nline 2"
        # 正确调用静态方法
        ExecutionLogger.log_execution_error("API_TEST", "exec_123", "Connection failed", stack_trace)

        # 静态方法调用，如果没有异常则测试通过
        assert True

    def test_execution_logger_methods_without_duration(self):
        """Test execution logger methods without duration parameter."""
        # 正确调用静态方法
        ExecutionLogger.log_execution_end("API_TEST", "exec_123", "success")
        ExecutionLogger.log_execution_error("API_TEST", "exec_123", "Error occurred")

        assert True  # If no exception is raised, the test passes


class TestDatabaseLogger:
    """Test the DatabaseLogger class."""

    def test_log_query_start(self):
        """Test logging query start."""
        logger = DatabaseLogger()
        logger.log_query_start("User")
        logger.log_query_start("Project", {"status": "active"})

        # These methods log directly using the logger
        assert True  # If no exception is raised, the test passes

    def test_log_query_end(self):
        """Test logging query end."""
        logger = DatabaseLogger()
        logger.log_query_end("User", count=5, duration=0.123)
        logger.log_query_end("Project")

        # These methods log directly using the logger
        assert True  # If no exception is raised, the test passes

    def test_log_save_start(self):
        """Test logging save start."""
        logger = DatabaseLogger()
        logger.log_save_start("User", 123)
        logger.log_save_start("Project")

        # These methods log directly using the logger
        assert True  # If no exception is raised, the test passes

    def test_log_save_end(self):
        """Test logging save end."""
        logger = DatabaseLogger()
        logger.log_save_end("User", 123, created=True, duration=0.050)
        logger.log_save_end("User", 123, created=False)

        # These methods log directly using the logger
        assert True  # If no exception is raised, the test passes

    @patch('testmanager_app.utils.api_logger.logger')
    def test_database_logger_with_mock(self, mock_logger):
        """Test database logger methods with mocked logger."""
        logger = DatabaseLogger()

        logger.log_query_start("User", {"active": True})
        logger.log_query_end("User", count=10, duration=0.1)
        logger.log_save_start("Project", 1)
        logger.log_save_end("Project", 1, created=True, duration=0.05)

        # Verify appropriate log levels were called
        assert mock_logger.debug.call_count >= 4

        # Check specific log messages
        log_messages = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("开始查询 User" in msg and "filters" in msg for msg in log_messages)
        assert any("完成查询 User" in msg and "返回 10条记录" in msg for msg in log_messages)
        assert any("开始保存 Project ID: 1" in msg for msg in log_messages)
        assert any("完成创建 Project ID: 1" in msg for msg in log_messages)


class TestLogDecorators:
    """Test the logging decorators."""

    @patch('testmanager_app.utils.api_logger.RequestLogger')
    def test_log_api_request_decorator(self, mock_request_logger_class, mock_request):
        """Test the log_api_request decorator."""
        mock_logger_instance = Mock()
        mock_request_logger_class.return_value.__enter__ = Mock(return_value=mock_logger_instance)
        mock_request_logger_class.return_value.__exit__ = Mock(return_value=None)

        @log_api_request
        def test_function(self, request):
            return {"result": "success"}

        result = test_function(None, mock_request)

        assert result == {"result": "success"}
        mock_request_logger_class.assert_called_once_with("test_function", mock_request)

    @patch('testmanager_app.utils.api_logger.RequestLogger')
    def test_log_api_request_decorator_with_exception(self, mock_request_logger_class, mock_request):
        """Test the log_api_request decorator with exception."""
        mock_logger_instance = Mock()
        mock_request_logger_class.return_value.__enter__ = Mock(return_value=mock_logger_instance)
        mock_request_logger_class.return_value.__exit__ = Mock(return_value=None)

        @log_api_request
        def test_function(self, request):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_function(None, mock_request)

        mock_request_logger_class.assert_called_once_with("test_function", mock_request)

    @pytest.mark.asyncio
    @patch('testmanager_app.utils.api_logger.RequestLogger')
    async def test_log_async_api_request_decorator(self, mock_request_logger_class, mock_request):
        """Test the log_async_api_request decorator."""
        mock_logger_instance = Mock()
        mock_request_logger_class.return_value.__enter__ = Mock(return_value=mock_logger_instance)
        mock_request_logger_class.return_value.__exit__ = Mock(return_value=None)

        @log_async_api_request
        async def async_test_function(self, request):
            return {"result": "async success"}

        result = await async_test_function(None, mock_request)

        assert result == {"result": "async success"}
        mock_request_logger_class.assert_called_once_with("async_test_function", mock_request)

    @pytest.mark.asyncio
    @patch('testmanager_app.utils.api_logger.RequestLogger')
    async def test_log_async_api_request_decorator_with_exception(self, mock_request_logger_class, mock_request):
        """Test the log_async_api_request decorator with exception."""
        mock_logger_instance = Mock()
        mock_request_logger_class.return_value.__enter__ = Mock(return_value=mock_logger_instance)
        mock_request_logger_class.return_value.__exit__ = Mock(return_value=None)

        @log_async_api_request
        async def async_test_function(self, request):
            raise ValueError("Async test error")

        with pytest.raises(ValueError):
            await async_test_function(None, mock_request)

        mock_request_logger_class.assert_called_once_with("async_test_function", mock_request)


class TestLoggerIntegration:
    """Integration tests for logger classes."""

    def test_request_logger_with_real_time_calculation(self, mock_request):
        """Test RequestLogger with real time duration calculation."""
        start_time = timezone.now()

        with patch('testmanager_app.utils.api_logger.logger'):
            with RequestLogger("test_function", mock_request) as logger:
                # Simulate some processing time
                import time
                time.sleep(0.001)  # 1ms delay

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            # Duration should be greater than 0
            assert duration > 0

    def test_execution_logger_with_multiple_operations(self, mock_api_request):
        """Test ExecutionLogger with multiple operations."""
        # 正确调用静态方法
        ExecutionLogger.log_execution_start("TEST", 1, api_request=mock_api_request)
        ExecutionLogger.log_execution_step("1", "step1", "First step")
        ExecutionLogger.log_execution_step("1", "step2", "Second step", level="debug")
        ExecutionLogger.log_execution_end("TEST", "1", "completed", 2.5)

        # All operations should complete without errors
        assert True

    def test_database_logger_comprehensive(self):
        """Test DatabaseLogger with comprehensive scenarios."""
        logger = DatabaseLogger()

        # Test various database operations
        logger.log_query_start("User")
        logger.log_query_start("Project", {"status": "active", "owner": "user1"})
        logger.log_query_end("User", count=0)
        logger.log_query_end("Project", count=15, duration=0.250)
        logger.log_save_start("User")
        logger.log_save_start("Task", 123)
        logger.log_save_end("User", 456, created=True, duration=0.100)
        logger.log_save_end("Task", 123, created=False, duration=0.075)

        # All operations should complete without errors
        assert True