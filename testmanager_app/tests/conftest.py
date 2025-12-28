"""
Pytest configuration and fixtures for testmanager_app tests.

This file contains shared fixtures, configurations, and utilities
used across multiple test files in the testmanager_app tests directory.
"""

import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from testmanager_app.models import Role, UserRole, ApiRequest


@pytest.fixture
def api_request_factory():
    """Create an API request factory for testing."""
    return APIRequestFactory()


@pytest.fixture
def request_factory():
    """Create a standard Django request factory."""
    return RequestFactory()


@pytest.fixture
def mock_request():
    """Create a mock request object with common attributes."""
    request = Mock()
    request.method = 'GET'
    request.path = '/api/test/'
    request.user = Mock()
    request.user.is_authenticated = True
    request.user.id = 1
    request.user.username = 'testuser'
    request.query_params = {}
    request.data = {}
    return request


@pytest.fixture
def mock_anonymous_request():
    """Create a mock anonymous request."""
    request = Mock()
    request.method = 'GET'
    request.path = '/api/test/'
    request.user = Mock()
    request.user.is_authenticated = False
    request.user.id = None
    request.user.username = 'anonymous'
    request.query_params = {}
    request.data = {}
    return request


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = 1
    user.username = 'testuser'
    user.is_authenticated = True
    user.is_superuser = False
    return user


@pytest.fixture
def mock_superuser():
    """Create a mock superuser for testing."""
    user = Mock(spec=User)
    user.id = 1
    user.username = 'admin'
    user.is_authenticated = True
    user.is_superuser = True
    return user


@pytest.fixture
def mock_api_request():
    """Create a mock API request model instance."""
    api_request = Mock(spec=ApiRequest)
    api_request.name = 'Test API'
    api_request.url = 'https://api.example.com/test'
    api_request.method = 'GET'
    return api_request


@pytest.fixture
def execution_result():
    """Create a sample execution result dictionary."""
    return {
        'status_code': 200,
        'response_time': 0.123,
        'response_body': '{"message": "success"}',
        'error': None
    }


@pytest.fixture
def execution_result_with_error():
    """Create a sample execution result with error."""
    return {
        'status_code': 500,
        'response_time': 0.234,
        'response_body': '{"error": "Internal Server Error"}',
        'error': 'Connection timeout'
    }


@pytest.fixture
def assertion_results():
    """Create sample assertion results."""
    return [
        {'passed': True, 'assertion_type': 'status_code'},
        {'passed': False, 'assertion_type': 'response_time'},
        {'passed': True, 'assertion_type': 'body_contains'}
    ]


@pytest.fixture
def template_context():
    """Create a sample template context dictionary."""
    return {
        'user': {
            'name': 'John Doe',
            'email': 'john@example.com',
            'role': 'admin'
        },
        'data': [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'}
        ],
        'config': {
            'timeout': 30,
            'retries': 3
        }
    }


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing logging functionality."""
    return Mock()


@pytest.fixture
def mock_timezone_now():
    """Mock timezone.now() for consistent timestamp testing."""
    from django.utils import timezone
    from datetime import datetime

    mock_time = datetime(2024, 1, 1, 12, 0, 0)
    with pytest.mock.patch.object(timezone, 'now', return_value=mock_time):
        yield mock_time


@pytest.fixture
def sample_template_strings():
    """Sample template strings for testing template rendering."""
    return {
        'simple': 'Hello {{user.name}}!',
        'nested': 'User: {{user.name}}, Role: {{user.role}}',
        'with_default': 'Welcome {{user.name|default:"Guest"}}',
        'list_access': 'First item: {{data.0.name}}',
        'multiple_vars': '{{user.name}} has {{config.timeout}}s timeout',
        'complex': 'API call for {{user.name}} with timeout {{config.timeout|default:"30"}}s'
    }


@pytest.fixture
def mock_role():
    """Create a mock role for testing."""
    role = Mock(spec=Role)
    role.id = 1
    role.name = 'Test Role'
    role.permission = 'crud'
    return role


@pytest.fixture
def mock_user_role():
    """Create a mock user-role relationship."""
    user_role = Mock(spec=UserRole)
    user_role.user_id = 1
    user_role.role_id = 1
    return user_role