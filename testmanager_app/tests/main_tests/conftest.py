"""
主应用测试的共享配置和夹具

提供主应用测试所需的共享夹具、mock对象和测试工具
"""

import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from testmanager_app.models import (
    Project, Module, TestCase, TestExecution, TestReport,
    Role, UserRole, ApiRequest, ApiAssertion, RequestCollection
)


@pytest.fixture
def api_request_factory():
    """创建API请求工厂"""
    return APIRequestFactory()


@pytest.fixture
def request_factory():
    """创建标准Django请求工厂"""
    return RequestFactory()


@pytest.fixture
def mock_user():
    """创建mock用户"""
    user = Mock(spec=User)
    user.id = 1
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.is_authenticated = True
    user.is_superuser = False
    user.is_active = True
    return user


@pytest.fixture
def mock_superuser():
    """创建mock超级用户"""
    user = Mock(spec=User)
    user.id = 1
    user.username = 'admin'
    user.email = 'admin@example.com'
    user.is_authenticated = True
    user.is_superuser = True
    user.is_active = True
    return user


@pytest.fixture
def mock_anonymous_user():
    """创建mock匿名用户"""
    user = Mock(spec=User)
    user.is_authenticated = False
    user.is_superuser = False
    return user


@pytest.fixture
def mock_project():
    """创建mock项目"""
    project = Mock(spec=Project)
    project.id = 1
    project.name = 'Test Project'
    project.description = 'Test project description'
    project.is_active = True
    project.created_at = '2024-01-01T00:00:00Z'
    return project


@pytest.fixture
def mock_module(mock_project):
    """创建mock模块"""
    module = Mock(spec=Module)
    module.id = 1
    module.name = 'Test Module'
    module.description = 'Test module description'
    module.project = mock_project
    module.created_at = '2024-01-01T00:00:00Z'
    return module


@pytest.fixture
def mock_test_case(mock_project, mock_module):
    """创建mock测试用例"""
    test_case = Mock(spec=TestCase)
    test_case.id = 1
    test_case.title = 'Test Case Title'
    test_case.description = 'Test case description'
    test_case.steps = 'Step 1: Do something'
    test_case.expected_result = 'Expected result'
    test_case.priority = 'high'
    test_case.project = mock_project
    test_case.module = mock_module
    test_case.created_by = mock_user
    test_case.created_at = '2024-01-01T00:00:00Z'
    return test_case


@pytest.fixture
def mock_test_execution(mock_test_case, mock_user):
    """创建mock测试执行"""
    execution = Mock(spec=TestExecution)
    execution.id = 1
    execution.testcase = mock_test_case
    execution.executor = mock_user
    execution.status = 'passed'
    execution.actual_result = 'Actual test result'
    execution.comments = 'Test execution comments'
    execution.executed_at = '2024-01-01T00:00:00Z'
    return execution


@pytest.fixture
def mock_test_report():
    """创建mock测试报告"""
    report = Mock(spec=TestReport)
    report.id = 1
    report.title = 'Test Report'
    report.content = 'Test report content'
    report.created_at = '2024-01-01T00:00:00Z'
    return report


@pytest.fixture
def mock_role():
    """创建mock角色"""
    role = Mock(spec=Role)
    role.id = 1
    role.name = 'Test Role'
    role.permission = 'crud'
    role.description = 'Test role description'
    return role


@pytest.fixture
def mock_user_role(mock_user, mock_role):
    """创建mock用户角色关系"""
    user_role = Mock(spec=UserRole)
    user_role.id = 1
    user_role.user = mock_user
    user_role.role = mock_role
    user_role.created_at = '2024-01-01T00:00:00Z'
    return user_role


@pytest.fixture
def mock_api_request(mock_project):
    """创建mock API请求"""
    api_request = Mock(spec=ApiRequest)
    api_request.id = 1
    api_request.name = 'Test API'
    api_request.url = 'https://api.example.com/test'
    api_request.method = 'GET'
    api_request.headers = '{"Content-Type": "application/json"}'
    api_request.body = '{"key": "value"}'
    api_request.project = mock_project
    api_request.created_at = '2024-01-01T00:00:00Z'
    return api_request


@pytest.fixture
def mock_api_assertion(mock_api_request):
    """创建mock API断言"""
    assertion = Mock(spec=ApiAssertion)
    assertion.id = 1
    assertion.api_request = mock_api_request
    assertion.assertion_type = 'status_code'
    assertion.expected_value = '200'
    assertion.created_at = '2024-01-01T00:00:00Z'
    return assertion


@pytest.fixture
def mock_request_collection(mock_project):
    """创建mock请求集合"""
    collection = Mock(spec=RequestCollection)
    collection.id = 1
    collection.name = 'Test Collection'
    collection.description = 'Test collection description'
    collection.project = mock_project
    collection.created_at = '2024-01-01T00:00:00Z'
    return collection


@pytest.fixture
def mock_request(mock_user):
    """创建mock请求对象"""
    request = Mock()
    request.method = 'GET'
    request.path = '/api/test/'
    request.user = mock_user
    request.META = {'REMOTE_ADDR': '127.0.0.1'}
    request.GET = {}
    request.POST = {}
    request.FILES = {}
    request.COOKIES = {}
    request.session = {}
    return request


@pytest.fixture
def mock_anonymous_request(mock_anonymous_user):
    """创建mock匿名请求"""
    request = Mock()
    request.method = 'GET'
    request.path = '/api/test/'
    request.user = mock_anonymous_user
    request.META = {'REMOTE_ADDR': '127.0.0.1'}
    request.GET = {}
    request.POST = {}
    request.FILES = {}
    request.COOKIES = {}
    request.session = {}
    return request


@pytest.fixture
def sample_project_data():
    """示例项目数据"""
    return {
        'name': 'Sample Project',
        'description': 'Sample project description',
        'is_active': True
    }


@pytest.fixture
def sample_test_case_data(mock_project, mock_module):
    """示例测试用例数据"""
    return {
        'title': 'Sample Test Case',
        'description': 'Sample test case description',
        'steps': 'Step 1: Do something\nStep 2: Verify result',
        'expected_result': 'Expected outcome',
        'priority': 'medium',
        'project': mock_project,
        'module': mock_module
    }


@pytest.fixture
def sample_api_request_data(mock_project):
    """示例API请求数据"""
    return {
        'name': 'Sample API',
        'url': 'https://api.example.com/sample',
        'method': 'POST',
        'headers': '{"Content-Type": "application/json", "Authorization": "Bearer token"}',
        'body': '{"param1": "value1", "param2": "value2"}',
        'project': mock_project
    }


@pytest.fixture
def sample_role_data():
    """示例角色数据"""
    return {
        'name': 'Test Manager',
        'permission': 'crud',
        'description': 'Can create, read, update and delete'
    }

    """示例导入数据"""
    return [
        {
            'name': 'Test Project 1',
            'description': 'Description 1',
            'is_active': True
        },
        {
            'name': 'Test Project 2',
            'description': 'Description 2',
            'is_active': False
        }
    ]


@pytest.fixture
def mock_queryset():
    """创建mock查询集"""
    queryset = Mock()
    queryset.count.return_value = 5
    queryset.filter.return_value = queryset
    queryset.exclude.return_value = queryset
    queryset.order_by.return_value = queryset
    queryset.values_list.return_value = [1, 2, 3, 4, 5]
    queryset.first.return_value = Mock()
    queryset.last.return_value = Mock()
    queryset.exists.return_value = True
    return queryset


@pytest.fixture
def mock_admin_site():
    """创建mock admin站点"""
    site = Mock()
    site.register = Mock()
    site.unregister = Mock()
    return site


@pytest.fixture
def mock_admin_model():
    """创建mock admin模型"""
    model_admin = Mock()
    model_admin.list_display = []
    model_admin.list_filter = []
    model_admin.search_fields = []
    model_admin.ordering = []
    model_admin.get_queryset = Mock(return_value=mock_queryset())
    return model_admin


@pytest.fixture
def execution_result():
    """执行结果示例"""
    return {
        'status_code': 200,
        'response_time': 0.123,
        'response_body': '{"success": true, "data": {"id": 1}}',
        'error': None
    }


@pytest.fixture
def execution_result_with_error():
    """包含错误的执行结果示例"""
    return {
        'status_code': 500,
        'response_time': 0.234,
        'response_body': '{"error": "Internal Server Error"}',
        'error': 'Connection timeout'
    }


@pytest.fixture
def sample_script():
    """示例测试脚本"""
    return """
# 测试脚本示例
def test_api():
    response = requests.get('https://api.example.com/test')
    assert response.status_code == 200
    return response.json()

if __name__ == '__main__':
    result = test_api()
    print(result)
"""


@pytest.fixture
def sample_template_context():
    """示例模板上下文"""
    return {
        'user': {
            'name': 'John Doe',
            'email': 'john@example.com',
            'role': 'admin'
        },
        'config': {
            'timeout': 30,
            'retries': 3,
            'base_url': 'https://api.example.com'
        },
        'data': [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'}
        ]
    }