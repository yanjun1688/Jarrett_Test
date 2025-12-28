"""
Unit tests for log_formatter.py

Tests execution logging functionality and log formatting.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from django.utils import timezone

from testmanager_app.utils.log_formatter import ExecutionLogger


class TestExecutionLogger:
    """Test the ExecutionLogger class from log_formatter module."""

    def test_execution_logger_init(self):
        """Test ExecutionLogger initialization."""
        logger = ExecutionLogger()

        assert logger.logs == []
        assert logger.start_time is not None
        assert isinstance(logger.start_time, datetime)

    def test_execution_logger_init_with_custom_time(self):
        """Test ExecutionLogger initialization with custom start time."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        logger = ExecutionLogger(custom_time)

        assert logger.start_time == custom_time

    def test_add_log_entry(self):
        """Test adding a basic log entry."""
        logger = ExecutionLogger()
        custom_time = datetime(2024, 1, 1, 12, 0, 0)

        logger.add("Test message", "INFO", custom_time)

        assert len(logger.logs) == 1
        assert "[2024-01-01 12:00:00] Test message" in logger.logs[0]

    def test_add_log_entry_without_timestamp(self):
        """Test adding a log entry without explicit timestamp."""
        logger = ExecutionLogger()

        logger.add("Test message without timestamp")

        assert len(logger.logs) == 1
        assert "Test message without timestamp" in logger.logs[0]
        # Should include current timestamp format
        assert "[2024-" in logger.logs[0] or "[2025-" in logger.logs[0]  # Allow for current year

    def test_add_log_entry_with_different_levels(self):
        """Test adding log entries with different levels."""
        logger = ExecutionLogger()

        logger.add("Info message", "INFO")
        logger.add("Warning message", "WARNING")
        logger.add("Error message", "ERROR")

        assert len(logger.logs) == 3
        assert "Info message" in logger.logs[0]
        assert "Warning message" in logger.logs[1]
        assert "Error message" in logger.logs[2]

    def test_add_start_logs(self, mock_api_request):
        """Test adding start execution logs."""
        logger = ExecutionLogger()

        logger.add_start(123, mock_api_request)

        logs_string = logger.get_logs_string()

        assert "======== 开始执行API测试 ========" in logs_string
        assert "执行记录ID: 123" in logs_string
        assert f"API名称: {mock_api_request.name}" in logs_string
        assert f"请求URL: {mock_api_request.url}" in logs_string
        assert f"请求方法: {mock_api_request.method}" in logs_string
        assert "代理配置:" in logs_string

    def test_add_start_logs_with_proxy(self):
        """Test adding start logs with proxy configuration."""
        logger = ExecutionLogger()
        mock_api_request = Mock()
        mock_api_request.name = "Test API"
        mock_api_request.url = "https://api.example.com/test"
        mock_api_request.method = "GET"

        # Mock environment variable
        with patch.dict(os.environ, {'HTTP_PROXY': 'http://proxy.example.com:8080'}):
            logger.add_start(456, mock_api_request)

        logs_string = logger.get_logs_string()
        assert "代理配置: http://proxy.example.com:8080" in logs_string

    def test_add_start_logs_without_proxy(self):
        """Test adding start logs without proxy configuration."""
        logger = ExecutionLogger()
        mock_api_request = Mock()
        mock_api_request.name = "Test API"
        mock_api_request.url = "https://api.example.com/test"
        mock_api_request.method = "GET"

        # Ensure no proxy is set
        with patch.dict(os.environ, {}, clear=True):
            logger.add_start(789, mock_api_request)

        logs_string = logger.get_logs_string()
        assert "代理配置: 无代理" in logs_string

    def test_add_request_sent_logs(self):
        """Test adding request sent logs."""
        logger = ExecutionLogger()

        logger.add_request_sent()

        logs_string = logger.get_logs_string()
        assert "正在发送请求..." in logs_string

    def test_add_request_completed_logs(self):
        """Test adding request completed logs."""
        logger = ExecutionLogger()

        logger.add_request_completed()

        logs_string = logger.get_logs_string()
        assert "请求发送完成" in logs_string

    def test_add_response_logs_success(self, execution_result):
        """Test adding successful response logs."""
        logger = ExecutionLogger()

        logger.add_response(execution_result)

        logs_string = logger.get_logs_string()

        assert "✅ 收到响应" in logs_string
        assert "HTTP状态码: 200" in logs_string
        assert "响应时间: 0.1230 秒" in logs_string
        assert "响应体格式: JSON" in logs_string
        assert '"message": "success"' in logs_string

    def test_add_response_logs_with_error(self, execution_result_with_error):
        """Test adding response logs with error."""
        logger = ExecutionLogger()

        logger.add_response(execution_result_with_error)

        logs_string = logger.get_logs_string()

        assert "❌ 请求失败" in logs_string
        assert "错误信息: Connection timeout" in logs_string
        # Should not include response details when there's an error
        assert "HTTP状态码" not in logs_string

    def test_add_response_logs_non_json_response(self):
        """Test adding response logs with non-JSON response."""
        logger = ExecutionLogger()
        result = {
            'status_code': 200,
            'response_time': 0.1,
            'response_body': 'Plain text response',
            'error': None
        }

        logger.add_response(result)

        logs_string = logger.get_logs_string()

        assert "✅ 收到响应" in logs_string
        assert "响应体格式: 文本" in logs_string
        assert "响应体内容:\nPlain text response" in logs_string

    def test_add_assertions_logs(self, assertion_results):
        """Test adding assertions logs."""
        logger = ExecutionLogger()

        logger.add_assertions(assertion_results)

        logs_string = logger.get_logs_string()

        assert "开始验证断言..." in logs_string
        assert "✅ 通过" in logs_string
        assert "❌ 失败" in logs_string
        assert "断言类型: status_code" in logs_string
        assert "断言类型: response_time" in logs_string
        assert "断言类型: body_contains" in logs_string

    def test_add_assertions_logs_empty_list(self):
        """Test adding assertions logs with empty list."""
        logger = ExecutionLogger()

        logger.add_assertions([])

        logs_string = logger.get_logs_string()
        assert logs_string == ""  # Should add nothing for empty list

    def test_add_assertion_summary_logs(self):
        """Test adding assertion summary logs."""
        logger = ExecutionLogger()

        logger.add_assertion_summary(2, 3)

        logs_string = logger.get_logs_string()
        assert "📊 断言统计: 2/3 通过" in logs_string

    def test_add_assertion_summary_logs_zero_total(self):
        """Test adding assertion summary logs with zero total count."""
        logger = ExecutionLogger()

        logger.add_assertion_summary(0, 0)

        logs_string = logger.get_logs_string()
        assert logs_string == ""  # Should add nothing for zero total

    def test_add_test_result_logs_passed(self):
        """Test adding test result logs for passed test."""
        logger = ExecutionLogger()

        logger.add_test_result(True, 3, 3)

        logs_string = logger.get_logs_string()
        assert "✅ 测试通过" in logs_string

    def test_add_test_result_logs_failed(self):
        """Test adding test result logs for failed test."""
        logger = ExecutionLogger()

        logger.add_test_result(False, 2, 3)

        logs_string = logger.get_logs_string()
        assert "❌ 测试失败" in logs_string

    def test_add_completion_logs(self):
        """Test adding completion logs."""
        logger = ExecutionLogger()

        logger.add_completion()

        logs_string = logger.get_logs_string()
        assert "======== 执行完成 ========" in logs_string

    def test_get_logs_list(self):
        """Test getting logs as list."""
        logger = ExecutionLogger()

        logger.add("Log entry 1")
        logger.add("Log entry 2")
        logger.add("Log entry 3")

        logs_list = logger.get_logs_list()

        assert isinstance(logs_list, list)
        assert len(logs_list) == 3
        assert "Log entry 1" in logs_list[0]
        assert "Log entry 2" in logs_list[1]
        assert "Log entry 3" in logs_list[2]

    def test_get_logs_string(self):
        """Test getting logs as concatenated string."""
        logger = ExecutionLogger()

        logger.add("First log entry")
        logger.add("Second log entry")
        logger.add("Third log entry")

        logs_string = logger.get_logs_string()

        assert isinstance(logs_string, str)
        assert "First log entry" in logs_string
        assert "Second log entry" in logs_string
        assert "Third log entry" in logs_string
        assert logs_string.count("\n") == 2  # Should have newlines between entries

    def test_get_logs_count(self):
        """Test getting the count of log entries."""
        logger = ExecutionLogger()

        assert logger.get_logs_count() == 0

        logger.add("First entry")
        assert logger.get_logs_count() == 1

        logger.add("Second entry")
        logger.add("Third entry")
        assert logger.get_logs_count() == 3

    def test_complete_execution_workflow(self, mock_api_request, execution_result, assertion_results):
        """Test a complete execution workflow."""
        logger = ExecutionLogger()

        # Simulate a complete API test execution
        logger.add_start(123, mock_api_request)
        logger.add_request_sent()
        logger.add_request_completed()
        logger.add_response(execution_result)
        logger.add_assertions(assertion_results)
        logger.add_assertion_summary(2, 3)
        logger.add_test_result(False, 2, 3)
        logger.add_completion()

        logs_string = logger.get_logs_string()

        # Verify all stages are logged
        assert "======== 开始执行API测试 ========" in logs_string
        assert "======== 执行完成 ========" in logs_string
        assert "正在发送请求..." in logs_string
        assert "请求发送完成" in logs_string
        assert "✅ 收到响应" in logs_string
        assert "开始验证断言..." in logs_string
        assert "📊 断言统计: 2/3 通过" in logs_string
        assert "❌ 测试失败" in logs_string

    def test_empty_logger_state(self):
        """Test behavior of empty logger."""
        logger = ExecutionLogger()

        assert logger.get_logs_count() == 0
        assert logger.get_logs_list() == []
        assert logger.get_logs_string() == ""

    @patch('django.utils.timezone.now')
    def test_timestamp_consistency(self, mock_now):
        """Test that timestamps are consistent when mocked."""
        fixed_time = datetime(2024, 6, 15, 14, 30, 45)
        mock_now.return_value = fixed_time

        logger = ExecutionLogger()
        logger.add("Test message")

        logs_string = logger.get_logs_string()
        assert "[2024-06-15 14:30:45] Test message" in logs_string

    def test_large_log_content_handling(self):
        """Test handling of large log content."""
        logger = ExecutionLogger()

        # Add many log entries
        for i in range(100):
            logger.add(f"Log entry number {i}")

        logs_list = logger.get_logs_list()
        logs_string = logger.get_logs_string()
        logs_count = logger.get_logs_count()

        assert logs_count == 100
        assert len(logs_list) == 100
        assert logs_string.count("Log entry number") == 100

    def test_special_characters_in_logs(self):
        """Test handling of special characters in log messages."""
        logger = ExecutionLogger()

        special_messages = [
            "Message with unicode: 你好世界 🌍",
            "Message with quotes: \"test\" and 'test'",
            "Message with newlines: line1\nline2\nline3",
            "Message with tabs: col1\tcol2\tcol3",
            "Message with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        ]

        for message in special_messages:
            logger.add(message)

        logs_string = logger.get_logs_string()

        for message in special_messages:
            assert message in logs_string

    def test_nested_json_response_formatting(self):
        """Test formatting of nested JSON responses."""
        logger = ExecutionLogger()

        nested_result = {
            'status_code': 200,
            'response_time': 0.234,
            'response_body': json.dumps({
                'user': {
                    'id': 123,
                    'name': 'John Doe',
                    'preferences': {
                        'theme': 'dark',
                        'notifications': True
                    }
                },
                'meta': {
                    'total': 100,
                    'page': 1
                }
            }),
            'error': None
        }

        logger.add_response(nested_result)

        logs_string = logger.get_logs_string()

        assert "✅ 收到响应" in logs_string
        assert "响应体格式: JSON" in logs_string
        # Should contain formatted JSON with indentation
        assert '"user": {' in logs_string
        assert '"preferences": {' in logs_string
        assert '"theme": "dark"' in logs_string

    def test_invalid_json_response_handling(self):
        """Test handling of invalid JSON in responses."""
        logger = ExecutionLogger()

        invalid_json_result = {
            'status_code': 200,
            'response_time': 0.1,
            'response_body': '{"invalid": json, missing closing brace',
            'error': None
        }

        logger.add_response(invalid_json_result)

        logs_string = logger.get_logs_string()

        assert "✅ 收到响应" in logs_string
        assert "响应体格式: 文本" in logs_string  # Should fall back to text format
        assert "响应体内容:\n{\"invalid\": json, missing closing brace" in logs_string

    def test_assertion_results_edge_cases(self):
        """Test assertion logging with edge cases."""
        logger = ExecutionLogger()

        # Test with None assertion results
        logger.add_assertions(None)
        assert logger.get_logs_count() == 0

        # Test with empty list
        logger.add_assertions([])
        assert logger.get_logs_count() == 0

        # Test with single assertion
        single_assertion = [{'passed': True, 'assertion_type': 'single_test'}]
        logger.add_assertions(single_assertion)
        logs_string = logger.get_logs_string()
        assert "✅ 通过" in logs_string
        assert "断言类型: single_test" in logs_string

    def test_timestamp_formatting(self):
        """Test timestamp formatting in log entries."""
        logger = ExecutionLogger()

        # Test with specific timestamp
        test_time = datetime(2024, 12, 31, 23, 59, 59)
        logger.add("Test message", timestamp=test_time)

        logs_string = logger.get_logs_string()
        assert "[2024-12-31 23:59:59] Test message" in logs_string