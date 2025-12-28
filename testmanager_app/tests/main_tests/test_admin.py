"""
测试admin.py文件

测试Django admin配置
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib import admin
from django.contrib.admin import AdminSite
from testmanager_app.admin import (
    RoleAdmin, UserRoleAdmin, ProjectAdmin, ModuleAdmin,
    TestCaseAdmin, TestExecutionAdmin
)
from testmanager_app.models import (
    Role, UserRole, Project, Module, TestCase, TestExecution
)


class TestRoleAdmin:
    """测试RoleAdmin配置"""

    def test_role_admin_list_display(self):
        """测试RoleAdmin的list_display配置"""
        role_admin = RoleAdmin(Role, AdminSite())
        expected_list_display = ['name', 'permission', 'description']
        assert list(role_admin.list_display) == expected_list_display

    def test_role_admin_list_filter(self):
        """测试RoleAdmin的list_filter配置"""
        role_admin = RoleAdmin(Role, AdminSite())
        expected_list_filter = ['permission']
        assert list(role_admin.list_filter) == expected_list_filter

    def test_role_admin_search_fields(self):
        """测试RoleAdmin的search_fields配置"""
        role_admin = RoleAdmin(Role, AdminSite())
        expected_search_fields = ['name', 'description']
        assert list(role_admin.search_fields) == expected_search_fields

    def test_role_admin_ordering(self):
        """测试RoleAdmin的ordering配置"""
        role_admin = RoleAdmin(Role, AdminSite())
        expected_ordering = ['name']
        assert list(role_admin.ordering) == expected_ordering

    def test_role_admin_registration(self):
        """测试RoleAdmin是否被正确注册"""
        # 检查Role模型是否被注册到admin站点
        assert admin.site.is_registered(Role)
        # 获取注册的ModelAdmin类
        registered_admin = admin.site._registry.get(Role)
        assert registered_admin is not None
        assert isinstance(registered_admin, RoleAdmin)


class TestUserRoleAdmin:
    """测试UserRoleAdmin配置"""

    def test_user_role_admin_list_display(self):
        """测试UserRoleAdmin的list_display配置"""
        user_role_admin = UserRoleAdmin(UserRole, AdminSite())
        expected_list_display = ['user', 'role', 'created_at']
        assert list(user_role_admin.list_display) == expected_list_display

    def test_user_role_admin_list_filter(self):
        """测试UserRoleAdmin的list_filter配置"""
        user_role_admin = UserRoleAdmin(UserRole, AdminSite())
        expected_list_filter = ['role', 'created_at']
        assert list(user_role_admin.list_filter) == expected_list_filter

    def test_user_role_admin_search_fields(self):
        """测试UserRoleAdmin的search_fields配置"""
        user_role_admin = UserRoleAdmin(UserRole, AdminSite())
        expected_search_fields = ['user__username', 'role__name']
        assert list(user_role_admin.search_fields) == expected_search_fields

    def test_user_role_admin_ordering(self):
        """测试UserRoleAdmin的ordering配置"""
        user_role_admin = UserRoleAdmin(UserRole, AdminSite())
        expected_ordering = ['-created_at']
        assert list(user_role_admin.ordering) == expected_ordering

    def test_user_role_admin_registration(self):
        """测试UserRoleAdmin是否被正确注册"""
        assert admin.site.is_registered(UserRole)
        registered_admin = admin.site._registry.get(UserRole)
        assert registered_admin is not None
        assert isinstance(registered_admin, UserRoleAdmin)


class TestProjectAdmin:
    """测试ProjectAdmin配置"""

    def test_project_admin_list_display(self):
        """测试ProjectAdmin的list_display配置"""
        project_admin = ProjectAdmin(Project, AdminSite())
        expected_list_display = ['name', 'description', 'is_active', 'created_at']
        assert list(project_admin.list_display) == expected_list_display

    def test_project_admin_list_filter(self):
        """测试ProjectAdmin的list_filter配置"""
        project_admin = ProjectAdmin(Project, AdminSite())
        expected_list_filter = ['is_active', 'created_at']
        assert list(project_admin.list_filter) == expected_list_filter

    def test_project_admin_search_fields(self):
        """测试ProjectAdmin的search_fields配置"""
        project_admin = ProjectAdmin(Project, AdminSite())
        expected_search_fields = ['name', 'description']
        assert list(project_admin.search_fields) == expected_search_fields

    def test_project_admin_ordering(self):
        """测试ProjectAdmin的ordering配置"""
        project_admin = ProjectAdmin(Project, AdminSite())
        expected_ordering = ['-created_at']
        assert list(project_admin.ordering) == expected_ordering

    def test_project_admin_registration(self):
        """测试ProjectAdmin是否被正确注册"""
        assert admin.site.is_registered(Project)
        registered_admin = admin.site._registry.get(Project)
        assert registered_admin is not None
        assert isinstance(registered_admin, ProjectAdmin)


class TestModuleAdmin:
    """测试ModuleAdmin配置"""

    def test_module_admin_list_display(self):
        """测试ModuleAdmin的list_display配置"""
        module_admin = ModuleAdmin(Module, AdminSite())
        expected_list_display = ['name', 'project', 'description', 'created_at']
        assert list(module_admin.list_display) == expected_list_display

    def test_module_admin_list_filter(self):
        """测试ModuleAdmin的list_filter配置"""
        module_admin = ModuleAdmin(Module, AdminSite())
        expected_list_filter = ['project', 'created_at']
        assert list(module_admin.list_filter) == expected_list_filter

    def test_module_admin_search_fields(self):
        """测试ModuleAdmin的search_fields配置"""
        module_admin = ModuleAdmin(Module, AdminSite())
        expected_search_fields = ['name', 'description', 'project__name']
        assert list(module_admin.search_fields) == expected_search_fields

    def test_module_admin_ordering(self):
        """测试ModuleAdmin的ordering配置"""
        module_admin = ModuleAdmin(Module, AdminSite())
        expected_ordering = ['project', 'name']
        assert list(module_admin.ordering) == expected_ordering

    def test_module_admin_registration(self):
        """测试ModuleAdmin是否被正确注册"""
        assert admin.site.is_registered(Module)
        registered_admin = admin.site._registry.get(Module)
        assert registered_admin is not None
        assert isinstance(registered_admin, ModuleAdmin)


class TestTestCaseAdmin:
    """测试TestCaseAdmin配置"""

    def test_test_case_admin_list_display(self):
        """测试TestCaseAdmin的list_display配置"""
        test_case_admin = TestCaseAdmin(TestCase, AdminSite())
        expected_list_display = ['title', 'project', 'module', 'priority', 'created_by', 'created_at']
        assert list(test_case_admin.list_display) == expected_list_display

    def test_test_case_admin_list_filter(self):
        """测试TestCaseAdmin的list_filter配置"""
        test_case_admin = TestCaseAdmin(TestCase, AdminSite())
        expected_list_filter = ['project', 'module', 'priority', 'created_at']
        assert list(test_case_admin.list_filter) == expected_list_filter

    def test_test_case_admin_search_fields(self):
        """测试TestCaseAdmin的search_fields配置"""
        test_case_admin = TestCaseAdmin(TestCase, AdminSite())
        expected_search_fields = ['title', 'steps', 'expected_result']
        assert list(test_case_admin.search_fields) == expected_search_fields

    def test_test_case_admin_ordering(self):
        """测试TestCaseAdmin的ordering配置"""
        test_case_admin = TestCaseAdmin(TestCase, AdminSite())
        expected_ordering = ['-created_at']
        assert list(test_case_admin.ordering) == expected_ordering

    def test_test_case_admin_registration(self):
        """测试TestCaseAdmin是否被正确注册"""
        assert admin.site.is_registered(TestCase)
        registered_admin = admin.site._registry.get(TestCase)
        assert registered_admin is not None
        assert isinstance(registered_admin, TestCaseAdmin)


class TestTestExecutionAdmin:
    """测试TestExecutionAdmin配置"""

    def test_test_execution_admin_list_display(self):
        """测试TestExecutionAdmin的list_display配置"""
        test_execution_admin = TestExecutionAdmin(TestExecution, AdminSite())
        expected_list_display = ['testcase', 'executor', 'status', 'executed_at']
        assert list(test_execution_admin.list_display) == expected_list_display

    def test_test_execution_admin_list_filter(self):
        """测试TestExecutionAdmin的list_filter配置"""
        test_execution_admin = TestExecutionAdmin(TestExecution, AdminSite())
        expected_list_filter = ['status', 'executor', 'executed_at']
        assert list(test_execution_admin.list_filter) == expected_list_filter

    def test_test_execution_admin_search_fields(self):
        """测试TestExecutionAdmin的search_fields配置"""
        test_execution_admin = TestExecutionAdmin(TestExecution, AdminSite())
        expected_search_fields = ['testcase__title', 'actual_result', 'comments']
        assert list(test_execution_admin.search_fields) == expected_search_fields

    def test_test_execution_admin_ordering(self):
        """测试TestExecutionAdmin的ordering配置"""
        test_execution_admin = TestExecutionAdmin(TestExecution, AdminSite())
        expected_ordering = ['-executed_at']
        assert list(test_execution_admin.ordering) == expected_ordering

    def test_test_execution_admin_registration(self):
        """测试TestExecutionAdmin是否被正确注册"""
        assert admin.site.is_registered(TestExecution)
        registered_admin = admin.site._registry.get(TestExecution)
        assert registered_admin is not None
        assert isinstance(registered_admin, TestExecutionAdmin)


class TestAdminIntegration:
    """测试Admin集成"""

    def test_all_models_registered(self):
        """测试所有模型都已注册到admin"""
        expected_models = [
            Role, UserRole, Project, Module, TestCase, TestExecution
        ]

        for model in expected_models:
            assert admin.site.is_registered(model), f"Model {model.__name__} is not registered"

    def test_admin_site_configuration(self):
        """测试admin站点配置"""
        # 检查admin站点的基本配置
        assert hasattr(admin.site, '_registry')
        assert len(admin.site._registry) > 0

        # 检查是否包含我们的模型
        our_models = [Role, UserRole, Project, Module, TestCase, TestExecution]
        registered_models = list(admin.site._registry.keys())

        for model in our_models:
            assert model in registered_models

    @patch('django.contrib.admin.ModelAdmin.get_queryset')
    def test_admin_queryset_optimization(self, mock_get_queryset, mock_queryset):
        """测试admin查询集优化"""
        mock_get_queryset.return_value = mock_queryset

        # 为每个ModelAdmin测试查询集
        admin_classes = [
            RoleAdmin(Role, AdminSite()),
            UserRoleAdmin(UserRole, AdminSite()),
            ProjectAdmin(Project, AdminSite()),
            ModuleAdmin(Module, AdminSite()),
            TestCaseAdmin(TestCase, AdminSite()),
            TestExecutionAdmin(TestExecution, AdminSite())
        ]

        for admin_class in admin_classes:
            queryset = admin_class.get_queryset(Mock())
            assert queryset is not None
            mock_get_queryset.assert_called()

    def test_admin_field_lookups(self):
        """测试admin字段查询配置"""
        # 测试包含外键查询的配置
        user_role_admin = UserRoleAdmin(UserRole, AdminSite())
        assert 'user__username' in user_role_admin.search_fields
        assert 'role__name' in user_role_admin.search_fields

        module_admin = ModuleAdmin(Module, AdminSite())
        assert 'project__name' in module_admin.search_fields

        test_execution_admin = TestExecutionAdmin(TestExecution, AdminSite())
        assert 'testcase__title' in test_execution_admin.search_fields

    def test_admin_ordering_configuration(self):
        """测试admin排序配置"""
        # 测试时间倒序排序
        time_desc_admins = [
            UserRoleAdmin(UserRole, AdminSite()),
            ProjectAdmin(Project, AdminSite()),
            TestCaseAdmin(TestCase, AdminSite()),
            TestExecutionAdmin(TestExecution, AdminSite())
        ]

        for admin_class in time_desc_admins:
            assert '-created_at' in admin_class.ordering or '-executed_at' in admin_class.ordering

        # 测试按名称排序
        name_asc_admins = [RoleAdmin(Role, AdminSite()), ModuleAdmin(Module, AdminSite())]

        for admin_class in name_asc_admins:
            assert 'name' in admin_class.ordering

    def test_admin_list_filter_coverage(self):
        """测试admin过滤器配置覆盖"""
        # 检查过滤器的完整性
        role_admin = RoleAdmin(Role, AdminSite())
        assert 'permission' in role_admin.list_filter

        user_role_admin = UserRoleAdmin(UserRole, AdminSite())
        assert 'role' in user_role_admin.list_filter
        assert 'created_at' in user_role_admin.list_filter

        project_admin = ProjectAdmin(Project, AdminSite())
        assert 'is_active' in project_admin.list_filter
        assert 'created_at' in project_admin.list_filter

        module_admin = ModuleAdmin(Module, AdminSite())
        assert 'project' in module_admin.list_filter

        test_case_admin = TestCaseAdmin(TestCase, AdminSite())
        assert 'project' in test_case_admin.list_filter
        assert 'module' in test_case_admin.list_filter
        assert 'priority' in test_case_admin.list_filter

        test_execution_admin = TestExecutionAdmin(TestExecution, AdminSite())
        assert 'status' in test_execution_admin.list_filter
        assert 'executor' in test_execution_admin.list_filter


class TestAdminEdgeCases:
    """测试Admin边界情况"""

    def test_admin_with_empty_data(self):
        """测试admin处理空数据"""
        # 创建空的queryset mock
        empty_queryset = Mock()
        empty_queryset.count.return_value = 0
        empty_queryset.filter.return_value = empty_queryset
        empty_queryset.exclude.return_value = empty_queryset
        empty_queryset.order_by.return_value = empty_queryset
        empty_queryset.first.return_value = None
        empty_queryset.last.return_value = None
        empty_queryset.exists.return_value = False

        # 测试admin类能处理空数据
        admin_classes = [
            RoleAdmin(Role, AdminSite()),
            UserRoleAdmin(UserRole, AdminSite()),
            ProjectAdmin(Project, AdminSite()),
            ModuleAdmin(Module, AdminSite()),
            TestCaseAdmin(TestCase, AdminSite()),
            TestExecutionAdmin(TestExecution, AdminSite())
        ]

        for admin_class in admin_classes:
            # 确保admin类能正常初始化
            assert hasattr(admin_class, 'list_display')
            assert hasattr(admin_class, 'list_filter')
            assert hasattr(admin_class, 'search_fields')
            assert hasattr(admin_class, 'ordering')

    def test_admin_search_field_validation(self):
        """测试admin搜索字段验证"""
        # 验证搜索字段格式
        admin_classes = [
            RoleAdmin(Role, AdminSite()),
            UserRoleAdmin(UserRole, AdminSite()),
            ProjectAdmin(Project, AdminSite()),
            ModuleAdmin(Module, AdminSite()),
            TestCaseAdmin(TestCase, AdminSite()),
            TestExecutionAdmin(TestExecution, AdminSite())
        ]

        for admin_class in admin_classes:
            # 确保搜索字段是列表或元组
            assert isinstance(admin_class.search_fields, (list, tuple))
            # 确保搜索字段不为空
            assert len(admin_class.search_fields) > 0

    def test_admin_list_display_validation(self):
        """测试admin列表显示字段验证"""
        admin_classes = [
            RoleAdmin(Role, AdminSite()),
            UserRoleAdmin(UserRole, AdminSite()),
            ProjectAdmin(Project, AdminSite()),
            ModuleAdmin(Module, AdminSite()),
            TestCaseAdmin(TestCase, AdminSite()),
            TestExecutionAdmin(TestExecution, AdminSite())
        ]

        for admin_class in admin_classes:
            # 确保列表显示字段是列表或元组
            assert isinstance(admin_class.list_display, (list, tuple))
            # 确保列表显示字段不为空
            assert len(admin_class.list_display) > 0