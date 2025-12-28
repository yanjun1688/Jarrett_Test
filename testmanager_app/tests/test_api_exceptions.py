"""
Unit tests for api_exceptions.py

Tests all custom exceptions and exception handling decorators.
"""

import pytest
from unittest.mock import Mock, patch
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.db import IntegrityError

from testmanager_app.utils.api_exceptions import (
    BusinessException,
    ResourceNotFoundException,
    ValidationFailedException,
    DuplicateResourceException,
    PermissionDeniedException,
    api_exception_handler,
    async_api_exception_handler
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_business_exception(self):
        """Test BusinessException base class."""
        exc = BusinessException("Test error message", "TEST_CODE", status.HTTP_400_BAD_REQUEST)

        assert str(exc) == "Test error message"
        assert exc.message == "Test error message"
        assert exc.code == "TEST_CODE"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_resource_not_found_exception(self):
        """Test ResourceNotFoundException."""
        exc = ResourceNotFoundException("User", 123)

        assert "User (ID: 123) 未找到" in str(exc)
        assert exc.code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_validation_failed_exception(self):
        """Test ValidationFailedException."""
        exc = ValidationFailedException("Invalid email format")

        assert str(exc) == "Invalid email format"
        assert exc.code == "VALIDATION_FAILED"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_resource_exception(self):
        """Test DuplicateResourceException."""
        exc = DuplicateResourceException("User", "email", "test@example.com")

        assert "User 已存在: email=test@example.com" in str(exc)
        assert exc.code == "DUPLICATE_RESOURCE"
        assert exc.status_code == status.HTTP_409_CONFLICT

    def test_permission_denied_exception(self):
        """Test PermissionDeniedException."""
        exc = PermissionDeniedException()

        assert str(exc) == "权限不足"
        assert exc.code == "PERMISSION_DENIED"
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_permission_denied_exception_custom_message(self):
        """Test PermissionDeniedException with custom message."""
        exc = PermissionDeniedException("Custom permission error")

        assert str(exc) == "Custom permission error"
        assert exc.code == "PERMISSION_DENIED"
        assert exc.status_code == status.HTTP_403_FORBIDDEN


class TestApiExceptionHandler:
    """Test the api_exception_handler decorator."""

    def test_successful_execution(self, mock_request):
        """Test successful function execution."""
        @api_exception_handler
        def successful_function(request):
            return Response({"message": "success"})

        result = successful_function(mock_request)

        assert result.status_code == status.HTTP_200_OK
        assert result.data == {"message": "success"}

    def test_business_exception_handling(self, mock_request):
        """Test BusinessException handling."""
        @api_exception_handler
        def business_exception_function(request):
            raise BusinessException("Business error", "BUSINESS_ERROR", status.HTTP_400_BAD_REQUEST)

        result = business_exception_function(mock_request)

        assert result.status_code == status.HTTP_400_BAD_REQUEST
        assert result.data["error"] == "Business error"
        assert result.data["code"] == "BUSINESS_ERROR"
        assert "request_id" in result.data

    def test_validation_error_handling(self, mock_request):
        """Test ValidationError handling."""
        @api_exception_handler
        def validation_error_function(request):
            raise ValidationError("Invalid input")

        result = validation_error_function(mock_request)

        assert result.status_code == status.HTTP_400_BAD_REQUEST
        assert result.data["error"] == "参数验证失败"
        assert result.data["code"] == "VALIDATION_ERROR"
        assert "request_id" in result.data

    def test_http404_handling(self, mock_request):
        """Test Http404 handling."""
        @api_exception_handler
        def http404_function(request):
            raise Http404()

        result = http404_function(mock_request)

        assert result.status_code == status.HTTP_404_NOT_FOUND
        assert result.data["error"] == "请求的资源不存在"
        assert result.data["code"] == "NOT_FOUND"
        assert "request_id" in result.data

    def test_object_does_not_exist_handling(self, mock_request):
        """Test ObjectDoesNotExist handling."""
        @api_exception_handler
        def does_not_exist_function(request):
            raise ObjectDoesNotExist("Resource not found")

        result = does_not_exist_function(mock_request)

        assert result.status_code == status.HTTP_404_NOT_FOUND
        assert result.data["error"] == "请求的资源不存在"
        assert result.data["code"] == "NOT_FOUND"
        assert "request_id" in result.data

    def test_integrity_error_handling(self, mock_request):
        """Test IntegrityError handling."""
        @api_exception_handler
        def integrity_error_function(request):
            raise IntegrityError("Duplicate entry")

        result = integrity_error_function(mock_request)

        assert result.status_code == status.HTTP_409_CONFLICT
        assert result.data["error"] == "数据冲突，可能已存在相同记录"
        assert result.data["code"] == "INTEGRITY_ERROR"
        assert "request_id" in result.data

    def test_generic_exception_handling(self, mock_request):
        """Test generic exception handling."""
        @api_exception_handler
        def generic_exception_function(request):
            raise ValueError("Something went wrong")

        result = generic_exception_function(mock_request)

        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert result.data["error"] == "服务器内部错误"
        assert result.data["code"] == "INTERNAL_ERROR"
        assert "request_id" in result.data

    def test_function_without_request(self):
        """Test decorator with function that doesn't have request parameter."""
        @api_exception_handler
        def function_without_request():
            return Response({"message": "success"})

        result = function_without_request()

        assert result.status_code == status.HTTP_200_OK
        assert result.data == {"message": "success"}

    def test_exception_with_function_without_request(self):
        """Test exception handling with function that doesn't have request parameter."""
        @api_exception_handler
        def exception_function():
            raise BusinessException("Error", "CODE", status.HTTP_400_BAD_REQUEST)

        result = exception_function()

        assert result.status_code == status.HTTP_400_BAD_REQUEST
        assert result.data["error"] == "Error"
        assert "request_id" in result.data


class TestAsyncApiExceptionHandler:
    """Test the async_api_exception_handler decorator."""

    @pytest.mark.asyncio
    async def test_successful_async_execution(self, mock_request):
        """Test successful async function execution."""
        @async_api_exception_handler
        async def successful_async_function(request):
            from django.http import JsonResponse
            return JsonResponse({"message": "async success"})

        result = await successful_async_function(mock_request)

        assert result.status_code == status.HTTP_200_OK
        # Note: JsonResponse content would need to be parsed for full assertion

    @pytest.mark.asyncio
    async def test_async_business_exception_handling(self, mock_request):
        """Test BusinessException handling in async function."""
        @async_api_exception_handler
        async def async_business_exception_function(request):
            raise BusinessException("Async business error", "ASYNC_ERROR", status.HTTP_400_BAD_REQUEST)

        result = await async_business_exception_function(mock_request)

        assert result.status_code == status.HTTP_400_BAD_REQUEST
        # Note: JsonResponse content would need to be parsed for full assertion

    @pytest.mark.asyncio
    async def test_async_validation_error_handling(self, mock_request):
        """Test ValidationError handling in async function."""
        @async_api_exception_handler
        async def async_validation_error_function(request):
            raise ValidationError("Async validation error")

        result = await async_validation_error_function(mock_request)

        assert result.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_async_generic_exception_handling(self, mock_request):
        """Test generic exception handling in async function."""
        @async_api_exception_handler
        async def async_generic_exception_function(request):
            raise RuntimeError("Async runtime error")

        result = await async_generic_exception_function(mock_request)

        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_async_function_without_request(self):
        """Test async decorator with function that doesn't have request parameter."""
        @async_api_exception_handler
        async def async_function_without_request():
            from django.http import JsonResponse
            return JsonResponse({"message": "async success"})

        result = await async_function_without_request()

        assert result.status_code == status.HTTP_200_OK


class TestExceptionHandlerLogging:
    """Test logging behavior of exception handlers."""

    @patch('testmanager_app.utils.api_exceptions.logger')
    def test_logging_on_success(self, mock_logger, mock_request):
        """Test logging behavior on successful execution."""
        @api_exception_handler
        def successful_function(request):
            return Response({"message": "success"})

        result = successful_function(mock_request)

        # Verify debug logs were called
        assert mock_logger.debug.called
        assert "开始执行" in str(mock_logger.debug.call_args_list[0])
        assert "执行完成" in str(mock_logger.debug.call_args_list[1])

    @patch('testmanager_app.utils.api_exceptions.logger')
    def test_logging_on_business_exception(self, mock_logger, mock_request):
        """Test logging behavior on business exception."""
        @api_exception_handler
        def business_exception_function(request):
            raise BusinessException("Business error", "BUSINESS_ERROR", status.HTTP_400_BAD_REQUEST)

        result = business_exception_function(mock_request)

        # Verify warning log was called
        assert mock_logger.warning.called
        assert "Business" in str(mock_logger.warning.call_args)

    @patch('testmanager_app.utils.api_exceptions.logger')
    def test_logging_on_internal_exception(self, mock_logger, mock_request):
        """Test logging behavior on internal exception."""
        @api_exception_handler
        def internal_exception_function(request):
            raise ValueError("Internal error")

        result = internal_exception_function(mock_request)

        # Verify error log was called with exc_info
        assert mock_logger.error.called
        assert "Internal" in str(mock_logger.error.call_args)
        # Check that exc_info=True was passed
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs.get('exc_info') is True