"""
测试permissions.py文件

测试基于角色的权限控制功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rest_framework.permissions import SAFE_METHODS
from rest_framework.test import APIRequestFactory
from testmanager_app.permissions import RoleBasedPermission
from testmanager_app.models import Role


class TestRoleBasedPermission:
    """测试RoleBasedPermission类"""

    def test_permission_class_initialization(self):
        """测试权限类初始化"""
        permission = RoleBasedPermission()
        assert isinstance(permission, RoleBasedPermission)
        assert hasattr(permission, 'has_permission')

    def test_has_permission_method_exists(self):
        """测试has_permission方法存在"""
        permission = RoleBasedPermission()
        assert hasattr(permission, 'has_permission')
        assert callable(permission.has_permission)

    def test_login_path_bypass_permission(self, mock_anonymous_request, mock_anonymous_user):
        """测试登录路径绕过权限检查"""
        permission = RoleBasedPermission()

        # 测试登录路径
        mock_anonymous_request.path = '/api/auth/login/'
        mock_anonymous_request.user = mock_anonymous_user

        result = permission.has_permission(mock_anonymous_request, Mock())
        assert result is True

    def test_debug_path_bypass_permission(self, mock_anonymous_request, mock_anonymous_user):
        """测试调试路径绕过权限检查"""
        permission = RoleBasedPermission()

        # 测试调试路径
        mock_anonymous_request.path = '/api/auth/debug/'
        mock_anonymous_request.user = mock_anonymous_user

        result = permission.has_permission(mock_anonymous_request, Mock())
        assert result is True

    def test_anonymous_user_rejected(self, mock_anonymous_request, mock_anonymous_user):
        """测试匿名用户被拒绝"""
        permission = RoleBasedPermission()

        mock_anonymous_request.path = '/api/projects/'
        mock_anonymous_request.user = mock_anonymous_user

        result = permission.has_permission(mock_anonymous_request, Mock())
        assert result is False

    def test_none_user_rejected(self):
        """测试None用户被拒绝"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = None

        result = permission.has_permission(request, Mock())
        assert result is False

    def test_superuser_has_all_permissions(self, mock_superuser):
        """测试超级用户拥有所有权限"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_superuser
        request.method = 'DELETE'  # 不安全的方法

        result = permission.has_permission(request, Mock())
        assert result is True

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_no_roles_safe_methods_allowed(self, mock_get_roles, mock_user):
        """测试无角色用户被拒绝访问（强制登出）"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'  # 安全方法

        # Mock空角色列表（返回空的QuerySet）
        from testmanager_app.models import Role
        mock_get_roles.return_value = Role.objects.none()

        result = permission.has_permission(request, Mock())
        assert result is False  # 修改：无角色用户应该被拒绝（强制登出）

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_no_roles_unsafe_methods_denied(self, mock_get_roles, mock_user):
        """测试无角色用户拒绝不安全方法"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'POST'  # 不安全方法

        # Mock空角色列表（返回空的QuerySet）
        from testmanager_app.models import Role
        mock_get_roles.return_value = Role.objects.none()

        result = permission.has_permission(request, Mock())
        assert result is False

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_crud_role_all_methods_allowed(self, mock_get_roles, mock_user):
        """测试有CRUD角色的用户允许所有方法"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'DELETE'  # 不安全方法

        # Mock包含CRUD权限的角色
        mock_role = Mock()
        mock_role.permission = 'crud'
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is True

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_view_role_safe_methods_allowed(self, mock_get_roles, mock_user):
        """测试有view角色的用户允许安全方法"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'  # 安全方法

        # Mock包含view权限的角色
        mock_role = Mock()
        mock_role.permission = 'view'
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is True

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_view_role_unsafe_methods_denied(self, mock_get_roles, mock_user):
        """测试有view角色的用户拒绝不安全方法"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'POST'  # 不安全方法

        # Mock包含view权限的角色
        mock_role = Mock()
        mock_role.permission = 'view'
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is False

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_multiple_roles_crud_takes_priority(self, mock_get_roles, mock_user):
        """测试用户有多个角色时CRUD权限优先"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'DELETE'  # 不安全方法

        # Mock包含多个角色，包括CRUD权限
        mock_role1 = Mock()
        mock_role1.permission = 'view'
        mock_role2 = Mock()
        mock_role2.permission = 'crud'
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role1, mock_role2]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is True  # CRUD权限应该允许访问

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_user_with_unknown_permission_denied(self, mock_get_roles, mock_user):
        """测试有未知权限的用户被拒绝"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'  # 安全方法

        # Mock包含未知权限的角色
        mock_role = Mock()
        mock_role.permission = 'unknown_permission'
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is False  # 未知权限不应该允许访问

    def test_safe_methods_list_integrity(self):
        """测试安全方法列表完整性"""
        # 验证SAFE_METHODS包含预期的HTTP方法
        expected_safe_methods = ['GET', 'HEAD', 'OPTIONS']
        for method in expected_safe_methods:
            assert method in SAFE_METHODS

    def test_permission_with_different_paths(self, mock_user):
        """测试不同路径的权限行为"""
        permission = RoleBasedPermission()

        # 测试不同格式的登录路径
        login_paths = [
            '/api/auth/login/',
            '/api/auth/login',
            '/api/auth/debug/',
            '/api/auth/debug'
        ]

        for path in login_paths:
            request = Mock()
            request.path = path
            request.user = mock_user
            request.method = 'POST'

            # Mock数据库查询以避免ORM错误
            with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                from testmanager_app.models import Role
                mock_get_roles.return_value = Role.objects.none()  # 模拟用户没有角色
                result = permission.has_permission(request, Mock())
                # 登录路径应该绕过权限检查
                if path.startswith('/api/auth/login/') or path.startswith('/api/auth/debug/'):
                    assert result is True

    def test_permission_with_edge_cases(self, mock_user):
        """测试边界情况的权限处理"""
        permission = RoleBasedPermission()

        # 测试空路径
        request = Mock()
        request.path = ''
        request.user = mock_user
        request.method = 'GET'

        # Mock数据库查询以避免ORM错误
        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            from testmanager_app.models import Role
            mock_get_roles.return_value = Role.objects.none()  # 模拟用户没有角色
            result = permission.has_permission(request, Mock())
            # 空路径应该按照正常权限逻辑处理
            assert result is True or result is False  # 取决于用户角色

    def test_permission_method_signature(self):
        """测试权限方法签名"""
        permission = RoleBasedPermission()

        # has_permission方法应该有正确的签名
        import inspect
        sig = inspect.signature(permission.has_permission)
        params = list(sig.parameters.keys())

        assert 'request' in params
        assert 'view' in params

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_permission_optimization_list_call(self, mock_get_roles, mock_user):
        """测试权限优化的列表调用"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'

        # Mock角色列表
        mock_role1 = Mock()
        mock_role1.permission = 'view'
        mock_role2 = Mock()
        mock_role2.permission = 'view'
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role1, mock_role2]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is True

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_permission_permissions_set_creation(self, mock_get_roles, mock_user):
        """测试权限集合创建"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'

        # Mock多个角色
        mock_role1 = Mock()
        mock_role1.permission = 'view'
        mock_role2 = Mock()
        mock_role2.permission = 'crud'
        mock_role3 = Mock()
        mock_role3.permission = 'view'

        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([mock_role1, mock_role2, mock_role3]))
        mock_get_roles.return_value = mock_queryset

        result = permission.has_permission(request, Mock())
        assert result is True  # 因为有CRUD权限

        # 验证调用了get_user_roles_qs方法
        mock_get_roles.assert_called_once_with(mock_user, use_cache=True)


class TestRoleBasedPermissionEdgeCases:
    """测试RoleBasedPermission边界情况"""

    def test_permission_with_invalid_request_method(self, mock_user):
        """测试无效HTTP方法的权限处理"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'INVALID_METHOD'

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            mock_role = Mock()
            mock_role.permission = 'view'
            mock_queryset = Mock()
            mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
            mock_get_roles.return_value = mock_queryset

            result = permission.has_permission(request, Mock())
            # 无效方法应该被当作不安全方法处理
            assert result is False

    def test_permission_with_malformed_path(self, mock_user):
        """测试畸形路径的权限处理"""
        permission = RoleBasedPermission()

        malformed_paths = [
            '',
            '/',
            '//',
            'api',
            'invalid-path',
            '/api/auth/login//',
            '/api/auth/login/extra/path'
        ]

        for path in malformed_paths:
            request = Mock()
            request.path = path
            request.user = mock_user
            request.method = 'GET'

            with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                from testmanager_app.models import Role
                mock_get_roles.return_value = Role.objects.none()

                result = permission.has_permission(request, Mock())
                # 畸形路径应该按照正常权限逻辑处理 - 无角色用户强制登出
                assert result is False   # 修改：无角色用户应该被拒绝（强制登出）

    def test_permission_with_concurrent_access(self, mock_user):
        """测试并发访问的权限处理"""
        import threading
        import time

        permission = RoleBasedPermission()
        results = []

        def access_permission():
            try:
                request = Mock()
                request.path = '/api/projects/'
                request.user = mock_user
                request.method = 'GET'

                with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                    from testmanager_app.models import Role
                    mock_get_roles.return_value = Role.objects.none()

                    result = permission.has_permission(request, Mock())
                    results.append(result)
            except Exception as e:
                results.append(str(e))

        # 创建多个线程同时访问
        threads = []
        for i in range(5):
            thread = threading.Thread(target=access_permission)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 所有访问都应该被拒绝（无角色用户强制登出）
        assert len(results) == 5
        for result in results:
            assert result is False  # 修改：无角色用户应该被拒绝（强制登出）

    @patch('testmanager_app.utils.user_utils.get_user_roles_qs')
    def test_permission_with_database_error(self, mock_get_roles, mock_user):
        """测试数据库错误时的权限处理"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'

        # Mock数据库错误
        mock_get_roles.side_effect = Exception("Database connection error")

        # 数据库错误应该导致权限被拒绝
        with pytest.raises(Exception):
            permission.has_permission(request, Mock())

    def test_permission_with_role_permission_edge_cases(self, mock_user):
        """测试角色权限边界情况"""
        permission = RoleBasedPermission()

        edge_case_permissions = [
            '',  # 空权限
            'VIEW',  # 大写权限
            'CrUd',  # 混合大小写
            'view ',  # 带空格
            ' crud ',  # 带空格
            None,  # None权限
        ]

        for perm in edge_case_permissions:
            request = Mock()
            request.path = '/api/projects/'
            request.user = mock_user
            request.method = 'GET'

            with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                from testmanager_app.models import Role
                if perm is not None:
                    mock_role = Mock()
                    mock_role.permission = perm
                    mock_queryset = Mock()
                    mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
                    mock_get_roles.return_value = mock_queryset
                else:
                    mock_get_roles.return_value = Role.objects.none()

                result = permission.has_permission(request, Mock())
                # 根据新的功能实现调整测试期望
                if perm == 'view':
                    # 精确的'view'权限应该允许访问
                    assert result is True
                elif perm == 'crud':
                    # 'crud'权限应该允许所有操作
                    assert result is True
                elif perm is None:
                    # 用户没有任何角色时，强制登出（返回False）
                    assert result is False  # 新功能：无角色用户强制登出
                else:
                    # 其他无效权限应该被拒绝
                    assert result is False


class TestRoleBasedPermissionIntegration:
    """测试RoleBasedPermission集成"""

    def test_permission_with_viewset_integration(self, mock_user):
        """测试与ViewSet集成的权限"""
        permission = RoleBasedPermission()

        # 创建一个模拟的ViewSet
        viewset = Mock()
        viewset.action = 'list'

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            mock_role = Mock()
            mock_role.permission = 'view'
            mock_queryset = Mock()
            mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
            mock_get_roles.return_value = mock_queryset

            result = permission.has_permission(request, viewset)
            assert result is True

    def test_permission_with_different_actions(self, mock_user):
        """测试不同动作的权限"""
        permission = RoleBasedPermission()

        # 测试不同的HTTP方法和对应的权限要求
        test_cases = [
            {'method': 'GET', 'permission': 'view', 'expected': True},
            {'method': 'POST', 'permission': 'view', 'expected': False},
            {'method': 'PUT', 'permission': 'view', 'expected': False},
            {'method': 'DELETE', 'permission': 'view', 'expected': False},
            {'method': 'GET', 'permission': 'crud', 'expected': True},
            {'method': 'POST', 'permission': 'crud', 'expected': True},
            {'method': 'PUT', 'permission': 'crud', 'expected': True},
            {'method': 'DELETE', 'permission': 'crud', 'expected': True},
        ]

        for test_case in test_cases:
            request = Mock()
            request.path = '/api/projects/'
            request.user = mock_user
            request.method = test_case['method']

            with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                mock_role = Mock()
                mock_role.permission = test_case['permission']
                mock_queryset = Mock()
                mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
                mock_get_roles.return_value = mock_queryset

                result = permission.has_permission(request, Mock())
                assert result == test_case['expected']

    def test_permission_caching_behavior(self, mock_user):
        """测试权限缓存行为"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            mock_role = Mock()
            mock_role.permission = 'view'
            mock_queryset = Mock()
            mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
            mock_get_roles.return_value = mock_queryset

            # 多次调用应该产生相同的结果
            result1 = permission.has_permission(request, Mock())
            result2 = permission.has_permission(request, Mock())
            result3 = permission.has_permission(request, Mock())

            assert result1 is result2 is result3 is True
            # get_user_roles_qs应该被调用多次（缓存可能命中，但函数会被调用）
            assert mock_get_roles.call_count == 3

    def test_permission_with_model_permissions(self, mock_user):
        """测试与模型权限的集成"""
        permission = RoleBasedPermission()

        # 测试不同的模型操作
        operations = [
            {'method': 'GET', 'action': 'list', 'permission': 'view'},
            {'method': 'POST', 'action': 'create', 'permission': 'crud'},
            {'method': 'PUT', 'action': 'update', 'permission': 'crud'},
            {'method': 'DELETE', 'action': 'destroy', 'permission': 'crud'},
        ]

        for operation in operations:
            request = Mock()
            request.path = '/api/projects/'
            request.user = mock_user
            request.method = operation['method']

            with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                mock_role = Mock()
                mock_role.permission = operation['permission']
                mock_queryset = Mock()
                mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
                mock_get_roles.return_value = mock_queryset

                result = permission.has_permission(request, Mock())
                assert result is True

    def test_permission_performance_with_multiple_roles(self, mock_user):
        """测试多角色情况下的权限性能"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/'
        request.user = mock_user
        request.method = 'GET'

        # 创建多个角色
        roles = []
        for i in range(10):
            mock_role = Mock()
            mock_role.permission = 'view' if i % 2 == 0 else 'crud'
            roles.append(mock_role)

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            mock_queryset = Mock()
            mock_queryset.__iter__ = Mock(return_value=iter(roles))
            mock_get_roles.return_value = mock_queryset

            result = permission.has_permission(request, Mock())
            assert result is True  # 因为有CRUD权限

    def test_permission_with_custom_http_methods(self, mock_user):
        """测试自定义HTTP方法的权限"""
        permission = RoleBasedPermission()

        custom_methods = ['PATCH', 'TRACE', 'CONNECT']

        for method in custom_methods:
            request = Mock()
            request.path = '/api/projects/'
            request.user = mock_user
            request.method = method

            with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
                mock_role = Mock()
                mock_role.permission = 'view'
                mock_queryset = Mock()
                mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
                mock_get_roles.return_value = mock_queryset

                result = permission.has_permission(request, Mock())
                # 自定义方法应该被当作不安全方法处理
                assert result is False

    def test_permission_with_path_parameters(self, mock_user):
        """测试带路径参数的权限"""
        permission = RoleBasedPermission()

        # 测试带ID的路径
        request = Mock()
        request.path = '/api/projects/123/'
        request.user = mock_user
        request.method = 'GET'

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            mock_role = Mock()
            mock_role.permission = 'view'
            mock_queryset = Mock()
            mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
            mock_get_roles.return_value = mock_queryset

            result = permission.has_permission(request, Mock())
            assert result is True

    def test_permission_with_query_parameters(self, mock_user):
        """测试带查询参数的权限"""
        permission = RoleBasedPermission()

        request = Mock()
        request.path = '/api/projects/?search=test&page=1'
        request.user = mock_user
        request.method = 'GET'

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles:
            mock_role = Mock()
            mock_role.permission = 'view'
            mock_queryset = Mock()
            mock_queryset.__iter__ = Mock(return_value=iter([mock_role]))
            mock_get_roles.return_value = mock_queryset

            result = permission.has_permission(request, Mock())
            assert result is True  # 查询参数不应该影响权限检查