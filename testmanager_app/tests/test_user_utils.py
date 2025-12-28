"""
Unit tests for user_utils.py

Tests user role and permission functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.permissions import SAFE_METHODS

from testmanager_app.utils.user_utils import (
    get_user_roles_qs,
    get_user_roles_data,
    get_user_role_ids,
    check_user_permissions
)


class TestGetUserRolesQs:
    """Test the get_user_roles_qs function."""

    def test_get_user_roles_qs_with_authenticated_user(self, mock_user):
        """Test getting roles query set for authenticated user."""
        with patch('testmanager_app.utils.user_utils.Role') as mock_role_model:
            mock_queryset = Mock()
            mock_role_model.objects.filter.return_value = mock_queryset

            result = get_user_roles_qs(mock_user)

            mock_role_model.objects.filter.assert_called_once_with(user_links__user=mock_user)
            assert result is mock_queryset

    def test_get_user_roles_qs_with_anonymous_user(self, mock_anonymous_request):
        """Test getting roles query set for anonymous user."""
        user = mock_anonymous_request.user

        with patch('testmanager_app.utils.user_utils.Role') as mock_role_model:
            mock_empty_queryset = Mock()
            mock_role_model.objects.none.return_value = mock_empty_queryset

            result = get_user_roles_qs(user)

            mock_role_model.objects.none.assert_called_once()
            assert result is mock_empty_queryset

    def test_get_user_roles_qs_with_none_user(self):
        """Test getting roles query set for None user."""
        with patch('testmanager_app.utils.user_utils.Role') as mock_role_model:
            mock_empty_queryset = Mock()
            mock_role_model.objects.none.return_value = mock_empty_queryset

            result = get_user_roles_qs(None)

            mock_role_model.objects.none.assert_called_once()
            assert result is mock_empty_queryset

    def test_get_user_roles_qs_with_unauthenticated_user(self):
        """Test getting roles query set for unauthenticated user."""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False

        with patch('testmanager_app.utils.user_utils.Role') as mock_role_model:
            mock_empty_queryset = Mock()
            mock_role_model.objects.none.return_value = mock_empty_queryset

            result = get_user_roles_qs(unauthenticated_user)

            mock_role_model.objects.none.assert_called_once()
            assert result is mock_empty_queryset


class TestGetUserRolesData:
    """Test the get_user_roles_data function."""

    def test_get_user_roles_data_with_roles(self, mock_user):
        """Test getting user roles data when user has roles."""
        mock_roles = [Mock(), Mock()]  # Mock role objects
        mock_serialized_data = [{"id": 1, "name": "Admin"}, {"id": 2, "name": "User"}]

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs, \
             patch('testmanager_app.utils.user_utils.RoleSerializer') as mock_serializer:

            mock_get_roles_qs.return_value = mock_roles
            mock_serializer.return_value.data = mock_serialized_data

            result = get_user_roles_data(mock_user)

            mock_get_roles_qs.assert_called_once_with(mock_user)
            mock_serializer.assert_called_once_with(mock_roles, many=True, context=None)
            assert result is mock_serialized_data

    def test_get_user_roles_data_with_serializer_context(self, mock_user):
        """Test getting user roles data with custom serializer context."""
        mock_roles = [Mock()]
        context = {"request": Mock()}
        mock_serialized_data = [{"id": 1, "name": "Admin"}]

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs, \
             patch('testmanager_app.utils.user_utils.RoleSerializer') as mock_serializer:

            mock_get_roles_qs.return_value = mock_roles
            mock_serializer.return_value.data = mock_serialized_data

            result = get_user_roles_data(mock_user, context)

            mock_get_roles_qs.assert_called_once_with(mock_user)
            mock_serializer.assert_called_once_with(mock_roles, many=True, context=context)
            assert result is mock_serialized_data

    def test_get_user_roles_data_with_no_roles(self, mock_user):
        """Test getting user roles data when user has no roles."""
        mock_empty_roles = []

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs, \
             patch('testmanager_app.utils.user_utils.RoleSerializer') as mock_serializer:

            mock_get_roles_qs.return_value = mock_empty_roles
            mock_serializer.return_value.data = []

            result = get_user_roles_data(mock_user)

            mock_get_roles_qs.assert_called_once_with(mock_user)
            mock_serializer.assert_called_once_with(mock_empty_roles, many=True, context=None)
            assert result == []


class TestGetUserRoleIds:
    """Test the get_user_role_ids function."""

    def test_get_user_role_ids_with_roles(self, mock_user):
        """Test getting user role IDs when user has roles."""
        mock_roles_qs = Mock()
        mock_roles_qs.values_list.return_value = [1, 2, 3]

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = get_user_role_ids(mock_user)

            mock_get_roles_qs.assert_called_once_with(mock_user)
            mock_roles_qs.values_list.assert_called_once_with('id', flat=True)
            assert result == [1, 2, 3]

    def test_get_user_role_ids_with_no_roles(self, mock_user):
        """Test getting user role IDs when user has no roles."""
        mock_roles_qs = Mock()
        mock_roles_qs.values_list.return_value = []

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = get_user_role_ids(mock_user)

            mock_get_roles_qs.assert_called_once_with(mock_user)
            mock_roles_qs.values_list.assert_called_once_with('id', flat=True)
            assert result == []

    def test_get_user_role_ids_casts_to_list(self, mock_user):
        """Test that get_user_role_ids properly casts result to list."""
        # Simulate values_list returning a queryset-like object
        mock_values_list = Mock()
        mock_values_list.__iter__ = Mock(return_value=iter([1, 2, 3]))
        mock_values_list.__len__ = Mock(return_value=3)

        mock_roles_qs = Mock()
        mock_roles_qs.values_list.return_value = mock_values_list

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = get_user_role_ids(mock_user)

            assert isinstance(result, list)
            assert result == [1, 2, 3]


class TestCheckUserPermissions:
    """Test the check_user_permissions function."""

    def test_check_user_permissions_superuser(self, mock_superuser):
        """Test permission check for superuser."""
        result = check_user_permissions(mock_superuser, "GET")

        expected = {
            'role_count': 0,
            'has_crud': False,
            'has_view': False,
            'can_access': True
        }
        assert result == expected

    def test_check_user_permissions_with_crud_role(self, mock_user):
        """Test permission check for user with CRUD role."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 2
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'crud')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Test with any HTTP method
            for method in ['GET', 'POST', 'PUT', 'DELETE']:
                result = check_user_permissions(mock_user, method)

                expected = {
                    'role_count': 2,
                    'has_crud': True,
                    'has_view': False,
                    'can_access': True
                }
                assert result == expected

    def test_check_user_permissions_with_view_role_safe_methods(self, mock_user):
        """Test permission check for user with view role using safe methods."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 1
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'view')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Test with safe methods (GET, HEAD, OPTIONS)
            for method in SAFE_METHODS:
                result = check_user_permissions(mock_user, method)

                expected = {
                    'role_count': 1,
                    'has_crud': False,
                    'has_view': True,
                    'can_access': True
                }
                assert result == expected

    def test_check_user_permissions_with_view_role_unsafe_methods(self, mock_user):
        """Test permission check for user with view role using unsafe methods."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 1
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'view')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Test with unsafe methods (POST, PUT, DELETE)
            unsafe_methods = ['POST', 'PUT', 'DELETE', 'PATCH']
            for method in unsafe_methods:
                result = check_user_permissions(mock_user, method)

                expected = {
                    'role_count': 1,
                    'has_crud': False,
                    'has_view': True,
                    'can_access': False
                }
                assert result == expected

    def test_check_user_permissions_no_roles(self, mock_user):
        """Test permission check for user with no roles."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 0
        mock_roles_qs.filter.return_value = Mock(exists=lambda: False)

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = check_user_permissions(mock_user, "GET")

            expected = {
                'role_count': 0,
                'has_crud': False,
                'has_view': False,
                'can_access': False
            }
            assert result == expected

    def test_check_user_permissions_with_anonymous_user(self, mock_anonymous_request):
        """Test permission check for anonymous user."""
        user = mock_anonymous_request.user

        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 0
        mock_roles_qs.filter.return_value = Mock(exists=lambda: False)

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = check_user_permissions(user, "GET")

            expected = {
                'role_count': 0,
                'has_crud': False,
                'has_view': False,
                'can_access': False
            }
            assert result == expected

    def test_check_user_permissions_with_none_user(self):
        """Test permission check for None user."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 0
        mock_roles_qs.filter.return_value = Mock(exists=lambda: False)

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = check_user_permissions(None, "GET")

            expected = {
                'role_count': 0,
                'has_crud': False,
                'has_view': False,
                'can_access': False
            }
            assert result == expected


class TestUserUtilsIntegration:
    """Integration tests for user utility functions."""

    def test_user_role_workflow(self, mock_user):
        """Test complete user role workflow."""
        # Mock role data
        mock_roles = [Mock(id=1), Mock(id=2)]
        mock_serialized_data = [{"id": 1, "name": "Admin"}, {"id": 2, "name": "User"}]
        mock_role_ids = [1, 2]

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs, \
             patch('testmanager_app.utils.user_utils.RoleSerializer') as mock_serializer:

            # Setup mocks
            mock_get_roles_qs.return_value = mock_roles
            mock_serializer.return_value.data = mock_serialized_data
            mock_roles.values_list.return_value = mock_role_ids

            # Test all functions work together
            roles_qs = get_user_roles_qs(mock_user)
            roles_data = get_user_roles_data(mock_user)
            role_ids = get_user_role_ids(mock_user)

            assert roles_qs is mock_roles
            assert roles_data is mock_serialized_data
            assert role_ids == mock_role_ids

    def test_permission_check_integration_with_roles(self, mock_user):
        """Test permission check integration when user has roles."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 2
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'crud')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            permissions = check_user_permissions(mock_user, "POST")

            assert permissions['can_access'] is True
            assert permissions['has_crud'] is True
            assert permissions['role_count'] == 2

    def test_permission_check_integration_without_roles(self, mock_user):
        """Test permission check integration when user has no roles."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 0
        mock_roles_qs.filter.return_value = Mock(exists=lambda: False)

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            permissions = check_user_permissions(mock_user, "GET")

            assert permissions['can_access'] is False
            assert permissions['has_crud'] is False
            assert permissions['has_view'] is False
            assert permissions['role_count'] == 0

    def test_superuser_bypasses_role_checks(self, mock_superuser):
        """Test that superuser bypasses all role-based permission checks."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 0
        mock_roles_qs.filter.return_value = Mock(exists=lambda: False)

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Superuser should have access regardless of roles
            permissions = check_user_permissions(mock_superuser, "DELETE")

            assert permissions['can_access'] is True
            # But role information should still be accurate
            assert permissions['role_count'] == 0
            assert permissions['has_crud'] is False
            assert permissions['has_view'] is False


class TestUserUtilsErrorHandling:
    """Test error handling in user utility functions."""

    def test_get_user_roles_qs_with_invalid_user(self):
        """Test get_user_roles_qs with invalid user object."""
        invalid_user = "not_a_user_object"

        with patch('testmanager_app.utils.user_utils.Role') as mock_role_model:
            mock_empty_queryset = Mock()
            mock_role_model.objects.none.return_value = mock_empty_queryset

            result = get_user_roles_qs(invalid_user)

            mock_role_model.objects.none.assert_called_once()
            assert result is mock_empty_queryset

    def test_check_user_permissions_with_invalid_method(self, mock_user):
        """Test check_user_permissions with invalid HTTP method."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 1
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'view')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Test with non-standard HTTP method
            result = check_user_permissions(mock_user, "INVALID")

            # Should treat as unsafe method
            expected = {
                'role_count': 1,
                'has_crud': False,
                'has_view': True,
                'can_access': False
            }
            assert result == expected

    def test_functions_handle_database_errors_gracefully(self, mock_user):
        """Test that functions handle database errors gracefully."""
        # Simulate database error
        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.side_effect = Exception("Database error")

            # Functions should not crash, but return safe defaults
            with pytest.raises(Exception):
                get_user_roles_qs(mock_user)


class TestUserUtilsEdgeCases:
    """Test edge cases for user utility functions."""

    def test_get_user_roles_data_with_complex_serializer_context(self, mock_user):
        """Test get_user_roles_data with complex serializer context."""
        mock_roles = [Mock()]
        complex_context = {
            "request": Mock(),
            "view": Mock(),
            "format": "json"
        }

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs, \
             patch('testmanager_app.utils.user_utils.RoleSerializer') as mock_serializer:

            mock_get_roles_qs.return_value = mock_roles
            mock_serializer.return_value.data = [{"id": 1, "name": "Admin"}]

            result = get_user_roles_data(mock_user, complex_context)

            mock_serializer.assert_called_once_with(mock_roles, many=True, context=complex_context)

    def test_get_user_role_ids_with_generator_like_values_list(self, mock_user):
        """Test get_user_role_ids when values_list returns a generator-like object."""
        def mock_generator():
            yield 1
            yield 2
            yield 3

        mock_roles_qs = Mock()
        mock_roles_qs.values_list.return_value = mock_generator()

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = get_user_role_ids(mock_user)

            assert result == [1, 2, 3]

    def test_check_user_permissions_boundary_conditions(self, mock_user):
        """Test check_user_permissions with boundary conditions."""
        # Test with exactly one role
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 1
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'view')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            result = check_user_permissions(mock_user, "GET")

            assert result['role_count'] == 1
            assert result['can_access'] is True

    def test_all_safe_methods_treated_equally(self, mock_user):
        """Test that all safe methods are treated equally."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 1
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'view')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Test all safe methods give same result
            safe_method_results = []
            for method in SAFE_METHODS:
                result = check_user_permissions(mock_user, method)
                safe_method_results.append(result)

            # All results should be identical
            first_result = safe_method_results[0]
            for result in safe_method_results[1:]:
                assert result == first_result

    def test_all_unsafe_methods_treated_equally(self, mock_user):
        """Test that all unsafe methods are treated equally for view-only users."""
        mock_roles_qs = Mock()
        mock_roles_qs.count.return_value = 1
        mock_roles_qs.filter.side_effect = lambda permission: Mock(exists=lambda: permission == 'view')

        with patch('testmanager_app.utils.user_utils.get_user_roles_qs') as mock_get_roles_qs:
            mock_get_roles_qs.return_value = mock_roles_qs

            # Test unsafe methods for view-only user
            unsafe_methods = ['POST', 'PUT', 'DELETE', 'PATCH']
            unsafe_method_results = []
            for method in unsafe_methods:
                result = check_user_permissions(mock_user, method)
                unsafe_method_results.append(result)

            # All results should be identical (no access)
            first_result = unsafe_method_results[0]
            for result in unsafe_method_results[1:]:
                assert result == first_result
                assert result['can_access'] is False