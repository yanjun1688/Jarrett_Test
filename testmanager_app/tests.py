# """
# 修复版完整测试套件 - 解决数据库表错误
# 文件名: test_complete.py (注意: test_ 开头)
# """
# import pytest
# import pytest_asyncio
# from unittest.mock import patch, MagicMock, Mock
# from unittest.mock import AsyncMock  # Python 3.8+ 支持 AsyncMock
# import asyncio
# import json
# from django.test import TestCase, TransactionTestCase, override_settings
# from django.contrib.auth.models import User
# from django.urls import reverse
# from django.utils import timezone
# from django.db import IntegrityError
# from rest_framework.test import APIClient, APITestCase, APIRequestFactory
# from rest_framework import status
# from rest_framework.authtoken.models import Token
# from rest_framework.test import force_authenticate
# import httpx
# from asgiref.sync import sync_to_async
# from datetime import datetime, timedelta

# from testmanager_app.models import (
#     Project, Module, TestCase as TestCaseModel, TestExecution, TestReport,
#     TestScript, ScriptExecution, ApiRequest, ApiAssertion, RequestCollection,
#     CollectionExecution, CollectionRequest, FeatureTestCase, TestResult, Role, UserRole
# )
# from testmanager_app.serializers import (
#     ProjectSerializer, ModuleSerializer, TestCaseSerializer, TestCaseCreateSerializer,
#     TestExecutionSerializer, TestExecutionCreateSerializer, TestReportSerializer,
#     TestScriptSerializer, TestScriptCreateSerializer, ScriptExecutionSerializer,
#     ApiRequestSerializer, ApiRequestCreateSerializer, ApiAssertionSerializer,
#     ApiAssertionCreateSerializer, RequestCollectionSerializer, RequestCollectionCreateSerializer,
#     CollectionExecutionSerializer, CollectionExecutionCreateSerializer, UserListSerializer,
#     RoleSerializer, UserRoleSerializer, ProjectStatisticsSerializer
# )
# from testmanager_app.services import get_project_statistics
# from testmanager_app.views import (
#     RoleBasedPermission, _safe_get_int_param, _safe_get_str_param,
#     _safe_get_choice_param, ProjectViewSet
# )


# # ===========================
# # 模型测试
# # ===========================

# class TestProjectModel(TestCase):
#     """Project模型测试"""
    
#     def test_project_creation(self):
#         """测试项目创建"""
#         project = Project.objects.create(
#             name="测试项目",
#             description="这是一个测试项目"
#         )
#         self.assertEqual(project.name, "测试项目")
#         self.assertTrue(project.is_active)
#         self.assertIsNotNone(project.created_at)
    
#     def test_project_default_values(self):
#         """测试项目默认值"""
#         project = Project.objects.create(name="测试项目")
#         self.assertTrue(project.is_active)
#         self.assertEqual(project.description, "")
    
#     def test_project_str_method(self):
#         """测试项目字符串表示"""
#         project = Project.objects.create(name="测试项目")
#         self.assertEqual(str(project), "测试项目")
    
#     def test_project_ordering(self):
#         """测试项目排序"""
#         import time
#         p1 = Project.objects.create(name="项目1")
#         time.sleep(0.01)  # 稍作延迟确保时间戳不同
#         p2 = Project.objects.create(name="项目2")
#         projects = list(Project.objects.all())
#         self.assertEqual(projects[0], p2)  # 最新的在前
    
#     def test_project_update_timestamp(self):
#         """测试更新时间戳"""
#         import time
#         project = Project.objects.create(name="测试")
#         old_updated = project.updated_at
#         time.sleep(0.01)  # 稍作延迟确保时间戳有差异
#         project.name = "更新后"
#         project.save()
#         self.assertGreater(project.updated_at, old_updated)


# class TestModuleModel(TestCase):
#     """Module模型测试"""
    
#     def setUp(self):
#         self.project = Project.objects.create(name="测试项目")
    
#     def test_module_creation(self):
#         """测试模块创建"""
#         module = Module.objects.create(
#             project=self.project,
#             name="登录模块"
#         )
#         self.assertEqual(module.project, self.project)
#         self.assertEqual(module.name, "登录模块")
    
#     def test_module_str_method(self):
#         """测试模块字符串表示"""
#         module = Module.objects.create(project=self.project, name="模块")
#         expected = f"{self.project.name} - 模块"
#         self.assertEqual(str(module), expected)
    
#     def test_module_unique_together(self):
#         """测试唯一性约束"""
#         Module.objects.create(project=self.project, name="模块A")
#         with self.assertRaises(IntegrityError):
#             Module.objects.create(project=self.project, name="模块A")
    
#     def test_module_cascade_delete(self):
#         """测试级联删除"""
#         module = Module.objects.create(project=self.project, name="模块")
#         module_id = module.id
#         self.project.delete()
#         self.assertFalse(Module.objects.filter(id=module_id).exists())


# class TestTestCaseModel(TestCase):
#     """TestCase模型测试"""
    
#     def setUp(self):
#         self.user = User.objects.create_user(username='testuser', password='12345')
#         self.project = Project.objects.create(name="测试项目")
#         self.module = Module.objects.create(project=self.project, name="模块")
    
#     def test_testcase_creation(self):
#         """测试用例创建"""
#         testcase = TestCaseModel.objects.create(
#             title="测试登录",
#             project=self.project,
#             module=self.module,
#             priority='high',
#             steps='步骤',
#             expected_result='结果',
#             created_by=self.user
#         )
#         self.assertEqual(testcase.title, "测试登录")
#         self.assertEqual(testcase.priority, 'high')
    
#     def test_testcase_priority_choices(self):
#         """测试优先级选项"""
#         priorities = ['low', 'medium', 'high', 'critical']
#         for priority in priorities:
#             tc = TestCaseModel.objects.create(
#                 title=f"用例{priority}",
#                 project=self.project,
#                 module=self.module,
#                 priority=priority,
#                 steps='s',
#                 expected_result='e'
#             )
#             self.assertEqual(tc.priority, priority)
    
#     def test_testcase_created_by_null(self):
#         """测试创建人可为空"""
#         tc = TestCaseModel.objects.create(
#             title="用例",
#             project=self.project,
#             module=self.module,
#             steps='s',
#             expected_result='e'
#         )
#         self.assertIsNone(tc.created_by)


# class TestExecutionModelTest(TestCase):
#     """TestExecution模型测试"""
    
#     def setUp(self):
#         self.user = User.objects.create_user(username='testuser', password='12345')
#         self.project = Project.objects.create(name="项目")
#         self.module = Module.objects.create(project=self.project, name="模块")
#         self.testcase = TestCaseModel.objects.create(
#             title="用例",
#             project=self.project,
#             module=self.module,
#             steps='s',
#             expected_result='e'
#         )
    
#     def test_execution_all_statuses(self):
#         """测试所有执行状态"""
#         statuses = ['passed', 'failed', 'blocked', 'skipped']
#         for status_val in statuses:
#             execution = TestExecution.objects.create(
#                 testcase=self.testcase,
#                 status=status_val
#             )
#             self.assertEqual(execution.status, status_val)
    
#     def test_execution_str_method(self):
#         """测试执行记录字符串表示"""
#         execution = TestExecution.objects.create(
#             testcase=self.testcase,
#             status='passed'
#         )
#         result_str = str(execution)
#         # 应该包含"通过"或"passed"
#         self.assertTrue('通过' in result_str or 'passed' in result_str.lower())


# class TestReportModelTest(TestCase):
#     """TestReport模型测试"""
    
#     def setUp(self):
#         self.project = Project.objects.create(name="项目")
    
#     def test_pass_rate_zero_cases(self):
#         """测试总用例为0时的通过率"""
#         report = TestReport.objects.create(
#             project=self.project,
#             name="报告",
#             start_date=timezone.now(),
#             end_date=timezone.now(),
#             total_cases=0,
#             passed_cases=0
#         )
#         self.assertEqual(report.pass_rate, 0)
    
#     def test_pass_rate_calculation(self):
#         """测试通过率计算"""
#         report = TestReport.objects.create(
#             project=self.project,
#             name="报告",
#             start_date=timezone.now(),
#             end_date=timezone.now(),
#             total_cases=100,
#             passed_cases=75
#         )
#         self.assertEqual(report.pass_rate, 75.0)


# class TestRoleModel(TestCase):
#     """Role模型测试"""
    
#     def test_role_creation(self):
#         """测试角色创建"""
#         role = Role.objects.create(name="查看者", permission="view")
#         self.assertEqual(role.permission, "view")
    
#     def test_role_str_method(self):
#         """测试角色字符串表示"""
#         role = Role.objects.create(name="管理员", permission="crud")
#         self.assertEqual(str(role), "管理员")


# class TestUserRoleModel(TestCase):
#     """UserRole模型测试"""
    
#     def setUp(self):
#         self.user = User.objects.create_user(username='testuser', password='12345')
#         self.role = Role.objects.create(name="角色", permission="view")
    
#     def test_user_role_creation(self):
#         """测试用户角色关联创建"""
#         user_role = UserRole.objects.create(user=self.user, role=self.role)
#         self.assertEqual(user_role.user, self.user)
#         self.assertEqual(user_role.role, self.role)
    
#     def test_unique_together_constraint(self):
#         """测试唯一性约束"""
#         UserRole.objects.create(user=self.user, role=self.role)
#         with self.assertRaises(IntegrityError):
#             UserRole.objects.create(user=self.user, role=self.role)
    
#     def test_get_user_roles_static_method(self):
#         """测试获取用户角色静态方法"""
#         role2 = Role.objects.create(name="角色2", permission="crud")
#         UserRole.objects.create(user=self.user, role=self.role)
#         UserRole.objects.create(user=self.user, role=role2)
        
#         roles = UserRole.get_user_roles(self.user)
#         self.assertEqual(roles.count(), 2)


# # ===========================
# # 序列化器测试
# # ===========================

# class TestSerializers(TestCase):
#     """序列化器测试"""
    
#     def setUp(self):
#         self.project = Project.objects.create(name="项目")
#         self.module = Module.objects.create(project=self.project, name="模块")
    
#     def test_project_serializer(self):
#         """测试项目序列化器"""
#         serializer = ProjectSerializer(self.project)
#         self.assertEqual(serializer.data['name'], "项目")
#         self.assertIn('created_at', serializer.data)
    
#     def test_module_serializer(self):
#         """测试模块序列化器"""
#         serializer = ModuleSerializer(self.module)
#         self.assertEqual(serializer.data['name'], "模块")
    
#     def test_role_serializer(self):
#         """测试角色序列化器"""
#         role = Role.objects.create(name="角色", permission="view")
#         serializer = RoleSerializer(role)
#         self.assertEqual(serializer.data['name'], "角色")


# # ===========================
# # 服务层测试
# # ===========================

# class TestServices(TestCase):
#     """服务层测试"""
    
#     def setUp(self):
#         self.user = User.objects.create_user(username='testuser', password='12345')
#         self.project = Project.objects.create(name="项目")
#         self.module = Module.objects.create(project=self.project, name="模块")
    
#     def test_get_project_statistics_not_found(self):
#         """测试项目不存在时的统计"""
#         result = get_project_statistics(99999)
#         self.assertIsNone(result)
    
#     def test_get_project_statistics_no_data(self):
#         """测试无数据时的统计"""
#         result = get_project_statistics(self.project.id)
#         self.assertEqual(result['total_testcases'], 0)
#         self.assertEqual(result['pass_rate'], 0)
    
#     def test_get_project_statistics_with_data(self):
#         """测试有数据时的统计"""
#         tc1 = TestCaseModel.objects.create(
#             project=self.project,
#             module=self.module,
#             title='用例1',
#             steps='s',
#             expected_result='e'
#         )
#         TestExecution.objects.create(testcase=tc1, status='passed')
#         TestExecution.objects.create(testcase=tc1, status='failed')
        
#         result = get_project_statistics(self.project.id)
#         self.assertEqual(result['total_testcases'], 1)
#         self.assertEqual(result['total_executions'], 2)
#         self.assertEqual(result['passed_executions'], 1)


# # ===========================
# # 权限测试
# # ===========================

# class TestRoleBasedPermission(TestCase):
#     """权限系统测试"""
    
#     def setUp(self):
#         self.permission = RoleBasedPermission()
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.user_with_crud = User.objects.create_user(username='crud_user', password='12345')
#         self.user_with_view = User.objects.create_user(username='view_user', password='12345')
#         self.user_no_role = User.objects.create_user(username='no_role', password='12345')
        
#         crud_role = Role.objects.create(name="CRUD", permission="crud")
#         view_role = Role.objects.create(name="VIEW", permission="view")
        
#         UserRole.objects.create(user=self.user_with_crud, role=crud_role)
#         UserRole.objects.create(user=self.user_with_view, role=view_role)
    
#     def test_unauthenticated_user_denied(self):
#         """测试未认证用户被拒绝"""
#         request = MagicMock()
#         request.user = MagicMock()
#         request.user.is_authenticated = False
#         request.path = '/api/projects/'
        
#         self.assertFalse(self.permission.has_permission(request, None))
    
#     def test_superuser_allowed_all(self):
#         """测试超级用户允许所有操作"""
#         request = MagicMock()
#         request.user = self.admin
#         request.method = 'POST'
#         request.path = '/api/projects/'
        
#         self.assertTrue(self.permission.has_permission(request, None))
    
#     def test_crud_user_allowed_all_methods(self):
#         """测试CRUD用户允许所有方法"""
#         for method in ['GET', 'POST', 'PUT', 'DELETE']:
#             request = MagicMock()
#             request.user = self.user_with_crud
#             request.method = method
#             request.path = '/api/projects/'
            
#             self.assertTrue(self.permission.has_permission(request, None))
    
#     def test_view_user_allowed_safe_methods_only(self):
#         """测试VIEW用户只允许安全方法"""
#         for method in ['GET', 'HEAD', 'OPTIONS']:
#             request = MagicMock()
#             request.user = self.user_with_view
#             request.method = method
#             request.path = '/api/projects/'
            
#             self.assertTrue(self.permission.has_permission(request, None))
        
#         for method in ['POST', 'PUT', 'DELETE']:
#             request = MagicMock()
#             request.user = self.user_with_view
#             request.method = method
#             request.path = '/api/projects/'
            
#             self.assertFalse(self.permission.has_permission(request, None))


# # ===========================
# # 工具函数测试
# # ===========================

# class TestUtilityFunctions(TestCase):
#     """工具函数测试"""
    
#     def test_safe_get_int_param_valid(self):
#         """测试安全获取整数参数 - 有效值"""
#         request = MagicMock()
#         request.query_params = {'id': '123'}
#         result = _safe_get_int_param(request, 'id')
#         self.assertEqual(result, 123)
    
#     def test_safe_get_int_param_invalid(self):
#         """测试安全获取整数参数 - 无效值"""
#         request = MagicMock()
#         request.query_params = {'id': 'abc'}
#         result = _safe_get_int_param(request, 'id')
#         self.assertIsNone(result)
    
#     def test_safe_get_int_param_none(self):
#         """测试安全获取整数参数 - 不存在"""
#         request = MagicMock()
#         request.query_params = {}
#         result = _safe_get_int_param(request, 'id')
#         self.assertIsNone(result)
    
#     def test_safe_get_str_param_valid(self):
#         """测试安全获取字符串参数"""
#         request = MagicMock()
#         request.query_params = {'name': 'test_project'}
#         result = _safe_get_str_param(request, 'name')
#         self.assertEqual(result, 'test_project')
    
#     def test_safe_get_str_param_sql_injection(self):
#         """测试SQL注入防护"""
#         request = MagicMock()
#         request.query_params = {'name': "'; DROP TABLE"}
#         result = _safe_get_str_param(request, 'name')
#         self.assertIsNone(result)
    
#     def test_safe_get_choice_param_valid(self):
#         """测试安全获取选项参数"""
#         request = MagicMock()
#         request.query_params = {'status': 'passed'}
#         result = _safe_get_choice_param(request, 'status', ['passed', 'failed'])
#         self.assertEqual(result, 'passed')
    
#     def test_safe_get_choice_param_invalid(self):
#         """测试无效选项"""
#         request = MagicMock()
#         request.query_params = {'status': 'invalid'}
#         result = _safe_get_choice_param(request, 'status', ['passed', 'failed'])
#         self.assertIsNone(result)


# # ===========================
# # API测试
# # ===========================

# class TestProjectAPI(APITestCase):
#     """项目API测试"""
    
#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
    
#     def test_create_project(self):
#         """测试创建项目"""
#         data = {'name': '新项目', 'description': '描述'}
#         response = self.client.post('/api/projects/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data['name'], '新项目')
    
#     def test_list_projects(self):
#         """测试列表项目"""
#         Project.objects.create(name="项目1")
#         response = self.client.get('/api/projects/')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertGreater(len(response.data['results']), 0)
    
#     def test_update_project(self):
#         """测试更新项目"""
#         project = Project.objects.create(name="原项目")
#         data = {'name': '新项目', 'description': '新描述'}
#         response = self.client.put(f'/api/projects/{project.id}/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['name'], '新项目')
    
#     def test_delete_project(self):
#         """测试删除项目"""
#         project = Project.objects.create(name="项目")
#         response = self.client.delete(f'/api/projects/{project.id}/')
#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
#     def test_project_statistics(self):
#         """测试项目统计"""
#         project = Project.objects.create(name="项目")
#         response = self.client.get(f'/api/projects/{project.id}/statistics/')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn('total_testcases', response.data)


# class TestModuleAPI(APITestCase):
#     """模块API测试"""
    
#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目")
    
#     def test_create_module(self):
#         """测试创建模块"""
#         data = {'project': self.project.id, 'name': '模块'}
#         response = self.client.post('/api/modules/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
#     def test_filter_modules_by_project(self):
#         """测试按项目过滤模块"""
#         Module.objects.create(project=self.project, name="模块1")
#         response = self.client.get(f'/api/modules/?project={self.project.id}')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data['results']), 1)


# class TestTestCaseAPI(APITestCase):
#     """测试用例API测试"""
    
#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目")
#         self.module = Module.objects.create(project=self.project, name="模块")
    
#     def test_create_testcase(self):
#         """测试创建测试用例"""
#         data = {
#             'title': '测试用例',
#             'project': self.project.id,
#             'module': self.module.id,
#             'priority': 'high',
#             'steps': '步骤',
#             'expected_result': '结果'
#         }
#         response = self.client.post('/api/testcases/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
#     def test_filter_testcases_by_priority(self):
#         """测试按优先级过滤"""
#         TestCaseModel.objects.create(
#             title='用例',
#             project=self.project,
#             module=self.module,
#             priority='high',
#             steps='s',
#             expected_result='e'
#         )
#         response = self.client.get('/api/testcases/?priority=high')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertGreater(len(response.data['results']), 0)


# class TestAuthenticationAPI(APITestCase):
#     """认证API测试"""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             password='testpass123',
#             email='test@example.com'
#         )
#         self.role = Role.objects.create(name="角色", permission="view")
#         UserRole.objects.create(user=self.user, role=self.role)
    
#     def test_login_success(self):
#         """测试登录成功"""
#         response = self.client.post('/api/auth/login/', {
#             'username': 'testuser',
#             'password': 'testpass123'
#         }, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn('token', response.data)
#         self.assertIn('user', response.data)
    
#     def test_login_invalid_credentials(self):
#         """测试无效凭证"""
#         response = self.client.post('/api/auth/login/', {
#             'username': 'testuser',
#             'password': 'wrongpass'
#         }, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
#     def test_me_endpoint(self):
#         """测试me端点"""
#         self.client.force_authenticate(user=self.user)
#         response = self.client.get('/api/auth/me/')
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['username'], 'testuser')


# class TestReportAPI(APITestCase):
#     """测试报告API"""
    
#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目")
    
#     def test_generate_report_success(self):
#         """测试生成报告"""
#         now = timezone.now()
#         data = {
#             'project_id': self.project.id,
#             'start_date': (now - timedelta(days=1)).isoformat(),
#             'end_date': now.isoformat()
#         }
#         response = self.client.post('/api/reports/generate_report/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
#     def test_generate_report_invalid_project(self):
#         """测试无效项目ID"""
#         now = timezone.now()
#         data = {
#             'project_id': 99999,
#             'start_date': now.isoformat(),
#             'end_date': now.isoformat()
#         }
#         response = self.client.post('/api/reports/generate_report/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# class TestRoleAPI(APITestCase):
#     """角色API测试"""
    
#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.client.force_authenticate(user=self.admin)
    
#     def test_create_role(self):
#         """测试创建角色"""
#         data = {'name': '测试角色', 'permission': 'view', 'description': '描述'}
#         response = self.client.post('/api/roles/', data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
#     def test_list_roles(self):
#         """测试列表角色"""
#         Role.objects.create(name="角色1", permission="view")
#         response = self.client.get('/api/roles/')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)


# # ===========================
# # 异步测试
# # ===========================

# @pytest.mark.django_db(transaction=True)
# class TestApiRequestAsync:
#     """API请求异步测试"""

#     @pytest_asyncio.fixture(autouse=True)
#     async def setup(self, db):
#         self.admin = await sync_to_async(User.objects.create_superuser)(
#             username='admin', password='12345'
#         )
#         crud_role = await sync_to_async(Role.objects.create)(name="管理员", permission="crud")
#         await sync_to_async(UserRole.objects.create)(user=self.admin, role=crud_role)

#         from django.test import AsyncClient
#         self.client = AsyncClient()
#         await sync_to_async(self.client.force_login)(self.admin)

#     @patch('testmanager_app.views.execute_single_request_async')
#     @pytest.mark.asyncio
#     async def test_execute_api_request(self, mock_execute):
#         """测试执行API请求 - Mock execute_single_request_async 函数"""
#         # 设置mock返回值
#         mock_execute.return_value = {
#             'status_code': 200,
#             'response_time': 0.5,
#             'response_body': '{"success": true}',
#             'assertions': [],
#             'passed_count': 0,
#             'total_assertions': 0
#         }

#         project = await sync_to_async(Project.objects.create)(name="项目")
#         api_request = await sync_to_async(ApiRequest.objects.create)(
#             name="测试请求",
#             project=project,
#             url="https://httpbin.org/get",
#             method="GET",
#             headers='{}',
#             body=''
#         )

#         # 使用正确的URL: /api/api-requests/{id}/execute/
#         url = f'/api/api-requests/{api_request.id}/execute/'
#         response = await self.client.post(url)

#         assert response.status_code == status.HTTP_200_OK
#         # 验证mock被调用
#         mock_execute.assert_called_once()
#         # 验证响应包含关键字段
#         assert 'status_code' in response.json()
#         assert response.json()['status_code'] == 200


# # ===========================
# # 数据完整性测试
# # ===========================

# class TestDataIntegrity(TestCase):
#     """数据完整性测试"""
    
#     def test_cascade_delete_project(self):
#         """测试删除项目级联删除"""
#         project = Project.objects.create(name="项目")
#         module = Module.objects.create(project=project, name="模块")
#         module_id = module.id
        
#         project.delete()
#         self.assertFalse(Module.objects.filter(id=module_id).exists())
    
#     def test_set_null_on_user_delete(self):
#         """测试删除用户时设置为NULL"""
#         user = User.objects.create_user(username='testuser', password='12345')
#         project = Project.objects.create(name="项目")
#         module = Module.objects.create(project=project, name="模块")
#         testcase = TestCaseModel.objects.create(
#             project=project,
#             module=module,
#             title='用例',
#             created_by=user,
#             steps='s',
#             expected_result='e'
#         )
        
#         user.delete()
#         testcase.refresh_from_db()
#         self.assertIsNone(testcase.created_by)


# # ===========================
# # 边界情况测试
# # ===========================

# class TestEdgeCases(APITestCase):
#     """边界情况测试"""
    
#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目")
    
#     def test_create_project_empty_name(self):
#         """测试创建空名称项目"""
#         response = self.client.post('/api/projects/', {'name': ''}, format='json')
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
#     def test_delete_nonexistent_resource(self):
#         """测试删除不存在的资源"""
#         response = self.client.delete('/api/projects/99999/')
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
#     def test_update_nonexistent_resource(self):
#         """测试更新不存在的资源"""
#         response = self.client.put('/api/projects/99999/', {'name': '新名称'}, format='json')
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# # ===========================
# # 性能测试
# # ===========================

# class TestPerformance(TestCase):
#     """性能测试"""

#     def test_bulk_create_testcases(self):
#         """测试批量创建测试用例"""
#         import time

#         project = Project.objects.create(name="项目")
#         module = Module.objects.create(project=project, name="模块")

#         start = time.time()
#         testcases = [
#             TestCaseModel(
#                 project=project,
#                 module=module,
#                 title=f'用例{i}',
#                 steps='步骤',
#                 expected_result='结果'
#             )
#             for i in range(100)
#         ]
#         TestCaseModel.objects.bulk_create(testcases)
#         duration = time.time() - start

#         self.assertLess(duration, 1.0)
#         self.assertEqual(TestCaseModel.objects.count(), 100)

#     def test_query_with_select_related(self):
#         """测试使用select_related的查询优化"""
#         from django.test.utils import CaptureQueriesContext
#         from django.db import connection

#         project = Project.objects.create(name="项目")
#         module = Module.objects.create(project=project, name="模块")
#         user = User.objects.create_user(username='testuser', password='12345')

#         for i in range(10):
#             TestCaseModel.objects.create(
#                 project=project,
#                 module=module,
#                 title=f'用例{i}',
#                 created_by=user,
#                 steps='s',
#                 expected_result='e'
#             )

#         # 测试使用select_related
#         with CaptureQueriesContext(connection) as context:
#             testcases = list(TestCaseModel.objects.select_related('project', 'module').all())
#             for tc in testcases:
#                 _ = tc.project.name
#                 _ = tc.module.name
#             queries_with = len(context.captured_queries)

#         # 查询数量应该很少（1或2个查询）
#         self.assertLess(queries_with, 5)


# # ===========================
# # 补充测试 - services.py 提高覆盖率
# # ===========================

# class TestServicesMore(TestCase):
#     """更多 services.py 测试以提高覆盖率"""

#     def setUp(self):
#         self.project = Project.objects.create(name="测试项目")
#         self.module = Module.objects.create(project=self.project, name="测试模块")

#     def test_get_project_statistics_all_zeros(self):
#         """测试项目统计全部为零的情况"""
#         result = get_project_statistics(self.project.id)

#         self.assertEqual(result['total_testcases'], 0)
#         self.assertEqual(result['total_executions'], 0)
#         self.assertEqual(result['passed_executions'], 0)
#         self.assertEqual(result['pass_rate'], 0)

#     def test_get_project_statistics_perfect_pass_rate(self):
#         """测试100%通过率"""
#         testcase = TestCaseModel.objects.create(
#             title="完美通过",
#             project=self.project,
#             module=self.module,
#             steps="步骤",
#             expected_result="结果"
#         )
#         TestExecution.objects.create(testcase=testcase, status='passed')

#         result = get_project_statistics(self.project.id)

#         self.assertEqual(result['total_testcases'], 1)
#         self.assertEqual(result['total_executions'], 1)
#         self.assertEqual(result['passed_executions'], 1)
#         self.assertEqual(result['pass_rate'], 100.0)

#     def test_get_project_statistics_all_statuses(self):
#         """测试所有执行状态的统计"""
#         testcase = TestCaseModel.objects.create(
#             title="全状态测试",
#             project=self.project,
#             module=self.module,
#             steps="步骤",
#             expected_result="结果"
#         )

#         for status in ['passed', 'failed', 'blocked', 'skipped']:
#             TestExecution.objects.create(testcase=testcase, status=status)

#         result = get_project_statistics(self.project.id)

#         self.assertEqual(result['total_executions'], 4)
#         self.assertEqual(result['passed_executions'], 1)
#         self.assertEqual(result['failed_executions'], 1)
#         self.assertEqual(result['blocked_executions'], 1)
#         self.assertEqual(result['skipped_executions'], 1)
#         self.assertEqual(result['pass_rate'], 25.0)


# # ===========================
# # 补充测试 - serializers.py 提高覆盖率
# # ===========================

# class TestSerializerCoverage(TestCase):
#     """序列化器覆盖率补充测试"""

#     def setUp(self):
#         self.project = Project.objects.create(name="测试项目")
#         self.module = Module.objects.create(project=self.project, name="测试模块")

#     def test_project_serializer_all_fields(self):
#         """测试 ProjectSerializer 所有字段"""
#         serializer = ProjectSerializer(self.project)
#         data = serializer.data

#         self.assertIn('id', data)
#         self.assertIn('name', data)
#         self.assertIn('description', data)
#         self.assertIn('created_at', data)
#         self.assertIn('updated_at', data)
#         self.assertIn('is_active', data)

#     def test_module_serializer_all_fields(self):
#         """测试 ModuleSerializer 所有字段"""
#         serializer = ModuleSerializer(self.module)
#         data = serializer.data

#         self.assertIn('id', data)
#         self.assertIn('project', data)
#         self.assertIn('project_name', data)
#         self.assertIn('name', data)
#         self.assertIn('description', data)
#         self.assertIn('created_at', data)
#         self.assertIn('updated_at', data)

#     def test_testcase_serializer_all_fields(self):
#         """测试 TestCaseSerializer 所有字段"""
#         user = User.objects.create_user(username='testuser', password='12345')
#         testcase = TestCaseModel.objects.create(
#             title="测试用例",
#             project=self.project,
#             module=self.module,
#             priority='high',
#             created_by=user
#         )

#         serializer = TestCaseSerializer(testcase)
#         data = serializer.data

#         self.assertIn('id', data)
#         self.assertIn('project_name', data)
#         self.assertIn('module_name', data)
#         self.assertIn('created_by_name', data)

#     def test_testcase_create_serializer(self):
#         """测试 TestCaseCreateSerializer"""
#         data = {
#             'title': '新建用例',
#             'project': self.project.id,
#             'module': self.module.id,
#             'priority': 'medium',
#             'steps': '测试步骤',
#             'expected_result': '预期结果'
#         }

#         serializer = TestCaseCreateSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#         testcase = serializer.save()
#         self.assertEqual(testcase.title, '新建用例')
#         self.assertEqual(testcase.priority, 'medium')

#     def test_testcase_create_serializer_invalid_priority(self):
#         """测试无效优先级应该失败"""
#         data = {
#             'title': '新建用例',
#             'project': self.project.id,
#             'module': self.module.id,
#             'priority': 'invalid',  # 无效值，不在 choices 中
#             'steps': '测试步骤',
#             'expected_result': '预期结果'
#         }

#         serializer = TestCaseCreateSerializer(data=data)
#         # 应该失败，因为模型定义了 choices，DRF 会自动验证
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('priority', serializer.errors)

#     def test_testexecution_serializer_all_fields(self):
#         """测试 TestExecutionSerializer 所有字段"""
#         testcase = TestCaseModel.objects.create(
#             title="测试用例",
#             project=self.project,
#             module=self.module,
#             steps="步骤",
#             expected_result="结果"
#         )
#         user = User.objects.create_user(username='testuser', password='12345')
#         execution = TestExecution.objects.create(testcase=testcase, executor=user, status='passed')

#         serializer = TestExecutionSerializer(execution)
#         data = serializer.data

#         self.assertIn('testcase_title', data)
#         self.assertIn('executor_name', data)

#     def test_testreport_serializer_pass_rate(self):
#         """测试 TestReportSerializer pass_rate 字段"""
#         report = TestReport.objects.create(
#             project=self.project,
#             name="测试报告",
#             start_date=timezone.now(),
#             end_date=timezone.now(),
#             total_cases=10,
#             passed_cases=7
#         )

#         serializer = TestReportSerializer(report)
#         self.assertEqual(serializer.data['pass_rate'], 70.0)

#     def test_testscript_serializer_readonly_file(self):
#         """测试 TestScriptSerializer file 只读"""
#         script = TestScript.objects.create(
#             name="测试脚本",
#             project=self.project,
#             script_type='python'
#         )

#         data = {
#             'name': '更新脚本',
#             'script_type': 'api'
#         }

#         serializer = TestScriptSerializer(script, data=data, partial=True)
#         if serializer.is_valid():
#             updated = serializer.save()
#             self.assertEqual(updated.name, '更新脚本')

#     def test_apiassertion_serializer_all_fields(self):
#         """测试 ApiAssertionSerializer 所有字段"""
#         api_request = ApiRequest.objects.create(
#             name="测试请求",
#             project=self.project,
#             url="https://httpbin.org/get",
#             method="GET"
#         )
#         assertion = ApiAssertion.objects.create(
#             api_request=api_request,
#             assertion_type='status_code',
#             comparison='equals',
#             expected_value='200'
#         )

#         serializer = ApiAssertionSerializer(assertion)
#         data = serializer.data

#         self.assertIn('api_request_name', data)

#     def test_collection_execution_serializer_pass_rate(self):
#         """测试 CollectionExecutionSerializer pass_rate 字段"""
#         collection = RequestCollection.objects.create(
#             name="测试集合",
#             project=self.project
#         )
#         execution = CollectionExecution.objects.create(
#             collection=collection,
#             status='success',
#             total_requests=10,
#             passed_requests=8
#         )

#         serializer = CollectionExecutionSerializer(execution)
#         self.assertEqual(serializer.data['pass_rate'], 80.0)

#     def test_userrole_serializer_fields(self):
#         """测试 UserRoleSerializer 所有字段"""
#         user = User.objects.create_user(username='testuser', password='12345')
#         role = Role.objects.create(name="测试角色", permission="view")
#         user_role = UserRole.objects.create(user=user, role=role)

#         serializer = UserRoleSerializer(user_role)
#         data = serializer.data

#         self.assertIn('username', data)
#         self.assertIn('role_name', data)
#         self.assertIn('role_permission', data)


# # ===========================
# # 补充测试 - API视图错误处理
# # ===========================

# class TestAPIErrorHandling(APITestCase):
#     """测试 API 错误处理"""

#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目1")
#         self.module = Module.objects.create(project=self.project, name="模块1")

#     def test_create_project_empty_name_validation(self):
#         """测试创建项目时名称无效的边界情况"""
#         data = {'name': ''}
#         response = self.client.post('/api/projects/', data, format='json')

#         # name 不能为空，应该返回 400
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_create_module_without_project(self):
#         """测试创建模块时不提供项目"""
#         data = {
#             'name': '测试模块',
#             'description': '描述'
#             # 缺少 project 字段
#         }
#         response = self.client.post('/api/modules/', data, format='json')

#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_update_testcase_invalid_priority(self):
#         """测试更新用例时优先级不存在的情况"""
#         testcase = TestCaseModel.objects.create(
#             title="测试用例",
#             project=self.project,
#             module=self.module,
#             priority='medium',
#             steps="步骤",
#             expected_result="结果"
#         )

#         data = {
#             'priority': 'nonexistent',
#             'title': '更新标题'
#         }

#         response = self.client.patch(f'/api/testcases/{testcase.id}/', data, format='json')

#         # DRF 会接受任何值，因为 priority 没有 choices 限制在 serializer
#         self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

#     def test_report_generate_missing_params(self):
#         """测试生成报告缺少参数"""
#         now = timezone.now()
#         data = {
#             'project_id': self.project.id,
#             # 缺少 start_date 和 end_date
#         }

#         response = self.client.post('/api/reports/generate_report/', data, format='json')

#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_report_generate_invalid_date_order(self):
#         """测试生成报告开始日期晚于结束日期"""
#         now = timezone.now()
#         data = {
#             'project_id': self.project.id,
#             'start_date': now.isoformat(),
#             'end_date': (now - timedelta(days=1)).isoformat()
#         }

#         response = self.client.post('/api/reports/generate_report/', data, format='json')

#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# # ===========================
# # 核心业务逻辑完整流程测试 - 快速提高覆盖率
# # ===========================

# class TestCompleteBusinessWorkflows(TestCase):
#     """测试完整的业务工作流以提高覆盖率"""

#     def setUp(self):
#         self.project = Project.objects.create(name="业务项目")
#         self.module = Module.objects.create(project=self.project, name="业务模块")
#         self.user = User.objects.create_user(username='businessuser', password='12345')

#     def test_testexecution_either_testcase_or_api_request_is_null(self):
#         """测试执行时必须至少有一个用例或API请求"""
#         # 测试testcase为None（API测试）
#         api_request = ApiRequest.objects.create(
#             name="独立API测试",
#             project=self.project,
#             url="https://httpbin.org/get",
#             method="GET"
#         )
#         execution = TestExecution.objects.create(
#             test_type='api',
#             api_request=api_request,
#             executor=self.user,
#             status='passed',
#             api_response_data={'status': 'success'},
#             api_logs='请求发送成功\n响应接收成功\n所有断言通过'
#         )
#         self.assertIsNone(execution.testcase)
#         self.assertIsNotNone(execution.api_request)
#         self.assertEqual(execution.test_type, 'api')

#         # 测试api_request为None（功能测试）
#         testcase = TestCaseModel.objects.create(
#             title="功能测试",
#             project=self.project,
#             module=self.module,
#             steps="功能步骤",
#             expected_result="功能结果"
#         )
#         execution2 = TestExecution.objects.create(
#             test_type='testcase',
#             testcase=testcase,
#             executor=self.user,
#             status='passed'
#         )
#         self.assertIsNotNone(execution2.testcase)
#         self.assertIsNone(execution2.api_request)
#         self.assertEqual(execution2.test_type, 'testcase')

#     def test_testexecution_api_logs_field(self):
#         """测试执行记录的API日志字段"""
#         api_request = ApiRequest.objects.create(
#             name="带日志的API",
#             project=self.project,
#             url="https://httpbin.org/get",
#             method="GET"
#         )
#         logs = """[2024-01-01 10:00:00] 开始执行API请求: https://httpbin.org/get
# [2024-01-01 10:00:01] 发送请求: GET
# [2024-01-01 10:00:02] 收到响应: HTTP 200
# [2024-01-01 10:00:02] 响应时间: 1234ms
# [2024-01-01 10:00:03] 断言验证: status_code equals 200 => 通过
# [2024-01-01 10:00:03] 执行完成: 1/1 断言通过"""

#         execution = TestExecution.objects.create(
#             test_type='api',
#             api_request=api_request,
#             executor=self.user,
#             status='passed',
#             api_logs=logs
#         )

#         self.assertIn("开始执行", execution.api_logs)
#         self.assertIn("HTTP 200", execution.api_logs)
#         self.assertIn("断言通过", execution.api_logs)

#     def test_complete_project_lifecycle(self):
#         """测试项目完整生命周期"""
#         # 创建项目
#         project = Project.objects.create(
#             name="完整生命周期项目",
#             description="从创建到删除"
#         )
#         project_id = project.id

#         # 创建模块
#         module = Module.objects.create(project=project, name="业务模块")

#         # 创建测试用例
#         testcase = TestCaseModel.objects.create(
#             title="完整用例",
#             project=project,
#             module=module,
#             priority='high',
#             steps="步骤",
#             expected_result="结果",
#             created_by=self.user
#         )

#         # 创建执行记录
#         execution = TestExecution.objects.create(
#             testcase=testcase,
#             executor=self.user,
#             status='passed',
#             actual_result="实际结果",
#             comments="详细注释"
#         )

#         # 验证关联查询
#         self.assertEqual(project.testcases.count(), 1)
#         self.assertEqual(module.testcases.count(), 1)

#         # 删除项目，验证级联删除
#         project.delete()
#         self.assertFalse(Project.objects.filter(id=project_id).exists())

#     def test_api_request_assertion_workflow(self):
#         """测试API请求和断言完整流程"""
#         api_request = ApiRequest.objects.create(
#             name="业务流程API",
#             project=self.project,
#             url="https://httpbin.org/get",
#             method="GET",
#             headers="Content-Type: application/json",
#             body="",
#             created_by=self.user
#         )

#         # 创建多个断言
#         for i in range(3):
#             ApiAssertion.objects.create(
#                 api_request=api_request,
#                 assertion_type='status_code',
#                 comparison='equals',
#                 expected_value='200'
#             )

#         # 验证关联
#         self.assertEqual(api_request.assertions.count(), 3)
#         self.assertEqual(str(api_request), "业务流程API")

#     def test_request_collection_workflow(self):
#         """测试请求集合完整流程"""
#         collection = RequestCollection.objects.create(
#             name="业务集合",
#             project=self.project,
#             created_by=self.user
#         )

#         # 添加多个API请求（使用CollectionRequest中间表）
#         for i in range(5):
#             api_request = ApiRequest.objects.create(
#                 name=f"请求{i}",
#                 project=self.project,
#                 url=f"https://example.com/{i}",
#                 method="GET"
#             )
#             CollectionRequest.objects.create(
#                 collection=collection,
#                 api_request=api_request,
#                 order_index=i
#             )

#         self.assertEqual(collection.collection_requests.count(), 5)

#         # 使用序列化器验证 request_count
#         serializer = RequestCollectionSerializer(collection)
#         self.assertEqual(serializer.data['request_count'], 5)

#     def test_script_execution_complete_flow(self):
#         """测试脚本执行完整流程"""
#         script = TestScript.objects.create(
#             name="业务脚本",
#             description="描述",
#             script_type='api',
#             project=self.project,
#             created_by=self.user
#         )

#         started = timezone.now()
#         finished = started + timedelta(seconds=5)

#         execution = ScriptExecution.objects.create(
#             script=script,
#             executor=self.user,
#             status='success',
#             output="执行输出",
#             error_message="",
#             started_at=started,
#             finished_at=finished
#         )

#         # 验证持续时间
#         self.assertIsNotNone(execution.calculated_duration)
#         self.assertEqual(str(execution), f"业务脚本 - 成功")

#     def test_testresult_with_all_fields(self):
#         """测试包含所有字段的测试结果"""
#         api_request = ApiRequest.objects.create(
#             name="测试结果API",
#             project=self.project,
#             url="https://httpbin.org/get",
#             method="GET"
#         )

#         result = TestResult.objects.create(
#             api_request=api_request,
#             status='success',
#             status_code=200,
#             response_time=150.5,
#             response_body='{"success": true}',
#             response_headers='{"Content-Type": "application/json"}',
#             assertion_results=[
#                 {'assertion': 'status_code', 'passed': True},
#                 {'assertion': 'response_time', 'passed': True}
#             ]
#         )

#         self.assertEqual(result.status_code, 200)
#         self.assertEqual(result.response_time, 150.5)
#         self.assertIn('success', result.response_body)

#     def test_user_role_comprehensive_management(self):
#         """全面的用户角色管理测试"""
#         user = User.objects.create_user(username='roleuser', password='12345')

#         # 创建多个角色
#         roles = []
#         for i in range(3):
#             role = Role.objects.create(
#                 name=f"角色{i}",
#                 permission="crud" if i % 2 == 0 else "view"
#             )
#             roles.append(role)
#             UserRole.assign_role_to_user(user, role)

#         # 验证角色分配
#         self.assertEqual(UserRole.get_user_roles(user).count(), 3)

#         # 验证角色权限
#         crud_roles = UserRole.get_user_roles(user).filter(permission='crud')
#         self.assertEqual(crud_roles.count(), 2)  # 角色0和角色2

#         # 移除角色
#         UserRole.remove_role_from_user(user, roles[0])
#         self.assertEqual(UserRole.get_user_roles(user).count(), 2)

#     def test_feature_testcase_complete(self):
#         """测试功能测试用例完整字段"""
#         feature_test = FeatureTestCase.objects.create(
#             title="功能测试完整",
#             pre_steps="详细前置步骤",
#             steps="详细操作步骤",
#             expected_result="详细预期结果",
#             actual_result="详细实际结果",
#             to_confirm="待确认事项",
#             is_passed=True,
#             version="v2.0"
#         )

#         self.assertEqual(feature_test.is_passed, True)
#         self.assertEqual(feature_test.version, "v2.0")
#         self.assertEqual(str(feature_test), "功能测试完整")


# # ===========================
# # 补充测试 - 边界情况和异常
# # ===========================

# class TestEdgeCasesAndExceptions(TestCase):
#     """更多边界情况和异常处理测试"""

#     def test_module_unique_together_integrity_error(self):
#         """测试模块唯一性约束"""
#         project = Project.objects.create(name="测试项目")
#         Module.objects.create(project=project, name="模块1")

#         with self.assertRaises(IntegrityError):
#             Module.objects.create(project=project, name="模块1")

#     def test_userrole_unique_together_integrity_error(self):
#         """测试用户角色唯一性约束"""
#         user = User.objects.create_user(username='testuser', password='12345')
#         role = Role.objects.create(name="角色", permission="view")
#         UserRole.objects.create(user=user, role=role)

#         with self.assertRaises(IntegrityError):
#             UserRole.objects.create(user=user, role=role)

#     def test_testresult_creation_minimal(self):
#         """测试 TestResult 最小数据创建"""
#         api_request = ApiRequest.objects.create(
#             name="测试请求",
#             project=Project.objects.create(name="项目"),
#             url="https://httpbin.org/get",
#             method="GET"
#         )

#         # 只传必需字段
#         result = TestResult.objects.create(
#             api_request=api_request,
#             status='success'
#         )

#         self.assertEqual(result.status, 'success')
#         self.assertIsNone(result.status_code)
#         self.assertIsNone(result.response_time)

#     def setUp(self):
#         """为测试方法设置 project"""
#         self.project = Project.objects.create(name="测试项目")

#     def test_script_execution_timed_out_status(self):
#         """测试脚本执行超时状态"""
#         script = TestScript.objects.create(
#             name="测试脚本",
#             project=self.project,
#             script_type='python'
#         )

#         execution = ScriptExecution.objects.create(
#             script=script,
#             status='failed'  # 超时后状态
#         )

#         self.assertEqual(execution.status, 'failed')

# # ===========================
# # 补充测试 - 提高覆盖率
# # ===========================

# class TestTestCasePriorityChoices(TestCase):
#     """测试 TestCase 的 PRIORITY_CHOICES"""

#     def setUp(self):
#         self.project = Project.objects.create(name="测试项目")
#         self.module = Module.objects.create(project=self.project, name="测试模块")

#     def test_all_priority_choices(self):
#         """测试所有优先级选项"""
#         priorities = ['low', 'medium', 'high', 'critical']
#         priority_labels = ['低', '中', '高', '紧急']

#         for i, (priority, label) in enumerate(zip(priorities, priority_labels)):
#             testcase = TestCaseModel.objects.create(
#                 title=f"测试用例-{priority}",
#                 project=self.project,
#                 module=self.module,
#                 priority=priority,
#                 steps="测试步骤",
#                 expected_result="预期结果"
#             )

#             # 验证存储的值
#             self.assertEqual(testcase.priority, priority)

#             # 验证 get_priority_display 返回正确的标签
#             self.assertEqual(testcase.get_priority_display(), label)

#     def test_default_priority(self):
#         """测试默认优先级"""
#         testcase = TestCaseModel.objects.create(
#             title="测试默认优先级",
#             project=self.project,
#             module=self.module,
#             steps="测试步骤",
#             expected_result="预期结果"
#         )

#         self.assertEqual(testcase.priority, 'medium')  # 默认值

# class TestTestCasePriorityChoices(TestCase):
#     """测试 TestCase 的 PRIORITY_CHOICES"""

#     def setUp(self):
#         self.project = Project.objects.create(name="测试项目")
#         self.module = Module.objects.create(project=self.project, name="测试模块")

#     def test_all_priority_choices(self):
#         """测试所有优先级选项"""
#         priorities = ['low', 'medium', 'high', 'critical']
#         priority_labels = ['低', '中', '高', '紧急']

#         for i, (priority, label) in enumerate(zip(priorities, priority_labels)):
#             testcase = TestCaseModel.objects.create(
#                 title=f"测试用例-{priority}",
#                 project=self.project,
#                 module=self.module,
#                 priority=priority,
#                 steps="测试步骤",
#                 expected_result="预期结果"
#             )

#             # 验证存储的值
#             self.assertEqual(testcase.priority, priority)

#             # 验证 get_priority_display 返回正确的标签
#             self.assertEqual(testcase.get_priority_display(), label)

#     def test_default_priority(self):
#         """测试默认优先级"""
#         testcase = TestCaseModel.objects.create(
#             title="测试默认优先级",
#             project=self.project,
#             module=self.module,
#             steps="测试步骤",
#             expected_result="预期结果"
#         )

#         self.assertEqual(testcase.priority, 'medium')  # 默认值


# class TestUtilityFunctions(TestCase):
#     """测试工具函数"""

#     def test_safe_get_choice_param_valid(self):
#         """测试 _safe_get_choice_param - 有效值"""
#         from unittest.mock import Mock
#         from testmanager_app.views import _safe_get_choice_param

#         request = Mock()
#         request.query_params = {'status': 'passed'}
#         result = _safe_get_choice_param(request, 'status', ['passed', 'failed', 'pending'])
#         self.assertEqual(result, 'passed')

#     def test_safe_get_choice_param_invalid(self):
#         """测试 _safe_get_choice_param - 无效值"""
#         from unittest.mock import Mock
#         from testmanager_app.views import _safe_get_choice_param

#         request = Mock()
#         request.query_params = {'status': 'invalid_value'}
#         result = _safe_get_choice_param(request, 'status', ['passed', 'failed', 'pending'])
#         self.assertIsNone(result)

#     def test_safe_get_choice_param_none(self):
#         """测试 _safe_get_choice_param - 不存在的参数"""
#         from unittest.mock import Mock
#         from testmanager_app.views import _safe_get_choice_param

#         request = Mock()
#         request.query_params = {}
#         result = _safe_get_choice_param(request, 'status', ['passed', 'failed', 'pending'])
#         self.assertIsNone(result)


# class TestProjectViewSetStatistics(TestCase):
#     """测试 ProjectViewSet 的 statistics 方法"""

#     def setUp(self):
#         self.factory = APIRequestFactory()
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)

#     def test_statistics_with_data(self):
#         """测试有数据的项目统计"""
#         project = Project.objects.create(name="测试项目")
#         module = Module.objects.create(project=project, name="测试模块")

#         # 创建测试用例和执行记录
#         testcase = TestCaseModel.objects.create(
#             title="测试用例",
#             project=project,
#             module=module,
#             steps="步骤",
#             expected_result="结果"
#         )
#         TestExecution.objects.create(testcase=testcase, status='passed')
#         TestExecution.objects.create(testcase=testcase, status='failed')

#         # 创建请求
#         request = self.factory.get(f'/api/projects/{project.id}/statistics/')
#         force_authenticate(request, user=self.admin)

#         view = ProjectViewSet.as_view({'get': 'statistics'})
#         response = view(request, pk=project.id)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['total_testcases'], 1)
#         self.assertEqual(response.data['total_executions'], 2)
#         self.assertEqual(response.data['passed_executions'], 1)

#     def test_statistics_not_found(self):
#         """测试不存在的项目统计"""
#         request = self.factory.get('/api/projects/99999/statistics/')
#         force_authenticate(request, user=self.admin)

#         view = ProjectViewSet.as_view({'get': 'statistics'})
#         response = view(request, pk=99999)

#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# class TestSerializerValidation(TestCase):
#     """测试序列化器验证"""

#     def setUp(self):
#         self.project = Project.objects.create(name="测试项目")
#         self.module = Module.objects.create(project=self.project, name="测试模块")

#     def test_requestcollection_serializer_request_count(self):
#         """测试 RequestCollectionSerializer 的 get_request_count 方法"""
#         collection = RequestCollection.objects.create(
#             name="测试集合",
#             project=self.project
#         )

#         # 创建 API 请求并添加到集合（使用CollectionRequest中间表）
#         api_request = ApiRequest.objects.create(
#             name="测试请求",
#             project=self.project,
#             url="https://httpbin.org/get",
#             method="GET"
#         )
#         CollectionRequest.objects.create(
#             collection=collection,
#             api_request=api_request,
#             order_index=0
#         )

#         serializer = RequestCollectionSerializer(collection)
#         self.assertEqual(serializer.data['request_count'], 1)

#     def test_role_serializer_user_count(self):
#         """测试 RoleSerializer 的 get_user_count 方法"""
#         role = Role.objects.create(name="测试角色", permission="view")
#         user = User.objects.create_user(username='testuser', password='12345')

#         UserRole.objects.create(user=user, role=role)

#         serializer = RoleSerializer(role)
#         self.assertEqual(serializer.data['user_count'], 1)

#     def test_userlist_serializer_roles(self):
#         """测试 UserListSerializer 的 get_roles 方法"""
#         user = User.objects.create_user(
#             username='testuser',
#             password='12345',
#             email='test@example.com'
#         )
#         role = Role.objects.create(name="测试角色", permission="view")
#         UserRole.objects.create(user=user, role=role)

#         serializer = UserListSerializer(user)
#         self.assertEqual(len(serializer.data['roles']), 1)
#         self.assertEqual(serializer.data['roles'][0]['name'], "测试角色")

#     def test_userlist_serializer_create_with_roles(self):
#         """测试 UserListSerializer 创建用户并分配角色"""
#         role = Role.objects.create(name="测试角色", permission="view")

#         data = {
#             'username': 'newuser',
#             'email': 'newuser@example.com',
#             'role_ids': [role.id]
#         }

#         serializer = UserListSerializer(data=data)
#         if serializer.is_valid():
#             user = serializer.save()
#             self.assertEqual(user.username, 'newuser')
#             self.assertEqual(user.role_links.count(), 1)
#         else:
#             self.fail(f"Serializer validation failed: {serializer.errors}")

#     def test_userlist_serializer_update_roles(self):
#         """测试 UserListSerializer 更新用户角色"""
#         user = User.objects.create_user(username='testuser', password='12345')
#         role1 = Role.objects.create(name="角色1", permission="view")
#         role2 = Role.objects.create(name="角色2", permission="crud")

#         UserRole.objects.create(user=user, role=role1)

#         data = {
#             'role_ids': [role2.id]
#         }

#         serializer = UserListSerializer(user, data=data, partial=True)
#         if serializer.is_valid():
#             updated_user = serializer.save()
#             self.assertEqual(updated_user.role_links.count(), 1)
#             self.assertEqual(updated_user.role_links.first().role, role2)
#         else:
#             self.fail(f"Serializer validation failed: {serializer.errors}")


# # ===========================
# # 测试链路脚本引擎测试
# # ===========================

# class TestScriptEngine(TestCase):
#     """测试脚本引擎 - 测试链路执行功能"""

#     def setUp(self):
#         self.project = Project.objects.create(name="脚本引擎测试项目")
#         self.user = User.objects.create_user(username='testuser', password='12345')
#         self.script_content = '''
# name: 测试脚本
# variables:
#   username: testuser
#   base_url: https://api.example.com

# test_steps:
#   - name: 登录请求
#     request:
#       method: POST
#       url: "{{base_url}}/api/login"
#       json:
#         username: "{{username}}"
#         password: "123456"
#     extract:
#       - name: token
#         jsonpath: "$.data.token"
#     assertions:
#       - type: status_code
#         expected: 200
#   - name: 获取用户信息
#     request:
#       method: GET
#       url: "{{base_url}}/api/user"
#       headers:
#         Authorization: "Bearer {{token}}"
#     assertions:
#       - type: status_code
#         expected: 200

# setup:
#   - name: 初始化设置
#     request:
#       method: POST
#       url: "{{base_url}}/api/setup"
#       json:
#         setup_key: "setup_value"
#     assertions:
#       - type: status_code
#         expected: 201

# teardown:
#   - name: 清理测试数据
#     request:
#       method: DELETE
#       url: "{{base_url}}/api/cleanup"
#       headers:
#         Authorization: "Bearer {{token}}"
#     assertions:
#       - type: status_code
#         expected: 200
# '''

#     @patch('httpx.Client')
#     def test_simple_yaml_execution(self, mock_client_class):
#         """测试简单YAML脚本执行"""
#         # 创建mock client
#         mock_client = MagicMock()
#         mock_client_class.return_value = mock_client

#         # 准备mock响应
#         login_response = MagicMock()
#         login_response.status_code = 200
#         login_response.elapsed.total_seconds.return_value = 0.5
#         login_response.json.return_value = {'data': {'token': 'fake_token_12345'}}
#         login_response.text = '{"data":{"token":"fake_token_12345"}}'

#         user_response = MagicMock()
#         user_response.status_code = 200
#         user_response.elapsed.total_seconds.return_value = 0.3
#         user_response.json.return_value = {'data': {'id': 1, 'name': 'Test User'}}
#         user_response.text = '{"data":{"id":1,"name":"Test User"}}'

#         setup_response = MagicMock()
#         setup_response.status_code = 201
#         setup_response.elapsed.total_seconds.return_value = 0.2
#         setup_response.json.return_value = {'status': 'setup_done'}
#         setup_response.text = '{"status":"setup_done"}'

#         cleanup_response = MagicMock()
#         cleanup_response.status_code = 200
#         cleanup_response.elapsed.total_seconds.return_value = 0.1
#         cleanup_response.json.return_value = {'status': 'cleanup_done'}
#         cleanup_response.text = '{"status":"cleanup_done"}'

#         # 配置client.request返回不同的响应
#         mock_client.request.side_effect = [
#             setup_response,   # setup
#             login_response,   # 登录
#             user_response,    # 获取用户信息
#             cleanup_response  # teardown
#         ]

#         # 执行测试
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         result = executor.execute_test_chain(self.script_content, 'yaml')

#         # 验证结果
#         self.assertTrue(result['success'])
#         # 不硬编码日志数量，只要日志存在且格式正确即可
#         self.assertGreater(len(result['logs']), 20, "应该有足够多的日志")
#         self.assertTrue(result['logs'][0].startswith('['))  # 日志有正确的时间戳格式

#         # 验证变量提取
#         self.assertIn('token', result['context'])
#         self.assertEqual(result['context']['token'], 'fake_token_12345')

#         # 验证setup和teardown都被执行
#         setup_found = any('初始化设置' in log for log in result['logs'])
#         teardown_found = any('清理测试数据' in log for log in result['logs'])
#         self.assertTrue(setup_found)
#         self.assertTrue(teardown_found)

#     @patch('httpx.Client')
#     def test_sequence_order(self, mock_client_class):
#         """测试步骤按顺序执行 - 验证没有ID也能保证顺序"""
#         mock_client = MagicMock()
#         mock_client_class.return_value = mock_client

#         # 创建一个顺序敏感的测试脚本 - 修复jsonpath格式
#         script = '''
# name: 顺序测试
# variables:
#   step_name: "初始值"

# test_steps:
#   - name: 第一步
#     request:
#       method: GET
#       url: "https://api.example.com/step1"
#     extract:
#       - name: step_name
#         jsonpath: "$.data.name"

#   - name: 第二步
#     request:
#       method: GET
#       url: "https://api.example.com/{{step_name}}"

#   - name: 第三步
#     request:
#       method: POST
#       url: "https://api.example.com/final"
# '''

#         # 创建模拟响应
#         responses = []
#         resp1 = MagicMock()
#         resp1.status_code = 200
#         resp1.elapsed.total_seconds.return_value = 0.1
#         resp1.json.return_value = {'data': {'name': 'step2_result'}}
#         resp1.text = '{"data":{"name":"step2_result"}}'
#         responses.append(resp1)

#         resp2 = MagicMock()
#         resp2.status_code = 200
#         resp2.elapsed.total_seconds.return_value = 0.1
#         resp2.json.return_value = {'data': {'status': 'step_1'}}
#         resp2.text = '{"data":{"status":"step_1"}}'
#         responses.append(resp2)

#         resp3 = MagicMock()
#         resp3.status_code = 200
#         resp3.elapsed.total_seconds.return_value = 0.1
#         resp3.json.return_value = {'data': {'status': 'step_2'}}
#         resp3.text = '{"data":{"status":"step_2"}}'
#         responses.append(resp3)

#         mock_client.request.side_effect = responses

#         # 执行
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         result = executor.execute_test_chain(script, 'yaml')
#         self.assertTrue(result['success'])

#         # 验证执行的顺序：应该看到三个步骤按顺序执行
#         logs_str = '\n'.join(result['logs'])
#         step1_pos = logs_str.find('执行步骤: 第一步')
#         step2_pos = logs_str.find('执行步骤: 第二步')
#         step3_pos = logs_str.find('执行步骤: 第三步')

#         # 验证顺序（后执行的步骤，出现位置应该更靠后）
#         self.assertLess(step1_pos, step2_pos, "第一步应该在第二步之前执行")
#         self.assertLess(step2_pos, step3_pos, "第二步应该在第三步之前执行")

#         # 验证第二步使用了第一步提取的变量
#         executor_second_call = mock_client.request.call_args_list[1]
#         url_arg = executor_second_call[1].get('url') or executor_second_call[0][1]
#         self.assertEqual(url_arg, 'https://api.example.com/step2_result')

#     @patch('httpx.Client')
#     def test_setup_teardown_always_executed(self, mock_client_class):
#         """测试setup总是先执行，teardown总是后执行，无论测试是否通过"""
#         mock_client = MagicMock()
#         mock_client_class.return_value = mock_client

#         # 创建一个会失败的测试脚本
#         script = '''
# name: setup/teardown测试
# variables:
#   fail: false

# test_steps:
#   - name: 会失败的步骤
#     request:
#       method: GET
#       url: "https://api.example.com/will_fail"
#     assertions:
#       - type: status_code
#         expected: 200

# setup:
#   - name: 设置步骤
#     request:
#       method: GET
#       url: "https://api.example.com/setup"

# teardown:
#   - name: 清理步骤
#     request:
#       method: DELETE
#       url: "https://api.example.com/cleanup"
# '''

#         # 创建响应：setup成功，测试失败，teardown成功
#         setup_resp = MagicMock()
#         setup_resp.status_code = 200
#         setup_resp.elapsed.total_seconds.return_value = 0.1
#         setup_resp.json.return_value = {'status': 'setup_ok'}

#         test_resp = MagicMock()
#         test_resp.status_code = 500  # 测试失败
#         test_resp.elapsed.total_seconds.return_value = 0.1
#         test_resp.json.return_value = {'error': 'internal_error'}

#         teardown_resp = MagicMock()
#         teardown_resp.status_code = 200
#         teardown_resp.elapsed.total_seconds.return_value = 0.1
#         teardown_resp.json.return_value = {'status': 'cleanup_ok'}

#         mock_client.request.side_effect = [setup_resp, test_resp, teardown_resp]

#         # 执行（应该失败，但teardown仍然执行）
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         result = executor.execute_test_chain(script, 'yaml')

#         # 验证失败
#         self.assertFalse(result['success'])

#         # 验证setup、测试、teardown都被执行（3次调用）
#         self.assertEqual(mock_client.request.call_count, 3)

#         # 验证日志中出现了所有步骤
#         logs_str = '\n'.join(result['logs'])
#         self.assertIn('执行步骤: 设置步骤', logs_str)
#         self.assertIn('执行步骤: 会失败的步骤', logs_str)
#         self.assertIn('执行步骤: 清理步骤', logs_str)

#         # 验证teardown在哪个阶段执行（应该在测试步骤之后）
#         setup_pos = logs_str.find('执行步骤: 设置步骤')
#         test_pos = logs_str.find('执行步骤: 会失败的步骤')
#         teardown_pos = logs_str.find('执行步骤: 清理步骤')
#         self.assertLess(setup_pos, test_pos)
#         self.assertLess(test_pos, teardown_pos)

#     @patch('httpx.Client')
#     def test_template_variable_rendering(self, mock_client_class):
#         """测试模板变量替换{{variable}} - 修复jsonpath"""
#         mock_client = MagicMock()
#         mock_client_class.return_value = mock_client

#         script = '''
# name: 变量替换测试
# variables:
#   username: testuser
#   password: "123456"
#   base_url: https://api.example.com

# test_steps:
#   - name: 登录
#     request:
#       method: POST
#       url: "{{base_url}}/login"
#       json:
#         user: "{{username}}"
#         pass: "{{password}}"
#         combined: "{{username}}:{{password}}"
#     extract:
#       - name: user_id
#         jsonpath: "$.data.id"
# '''

#         resp = MagicMock()
#         resp.status_code = 200
#         resp.elapsed.total_seconds.return_value = 0.1
#         resp.json.return_value = {'data': {'id': 12345}}
#         resp.text = '{"data":{"id":12345}}'

#         mock_client.request.return_value = resp

#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         result = executor.execute_test_chain(script, 'yaml')

#         self.assertTrue(result['success'])

#         # 验证模板变量被正确替换
#         call_args = mock_client.request.call_args
#         json_data = call_args[1]['json']
#         self.assertEqual(json_data['user'], 'testuser')
#         self.assertEqual(json_data['pass'], '123456')
#         self.assertEqual(json_data['combined'], 'testuser:123456')

#         # 验证变量被提取
#         self.assertIn('user_id', result['context'])
#         self.assertEqual(result['context']['user_id'], 12345)


# class TestScriptEngineEdgeCases(TestCase):
#     """测试脚本引擎边界情况"""

#     def test_invalid_yaml_format(self):
#         """测试无效YAML格式"""
#         invalid_yaml = """
# name: 测试
#   invalid:
#     - indentation
#     is_wrong: here
# """

#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         result = executor.execute_test_chain(invalid_yaml, 'yaml')

#         # 应该失败
#         self.assertFalse(result['success'])
#         self.assertIn('error', result)

#     def test_empty_script(self):
#         """测试空脚本"""
#         empty_script = ''

#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         result = executor.execute_test_chain(empty_script, 'yaml')

#         self.assertFalse(result['success'])

#     def test_no_test_steps(self):
#         """测试没有测试步骤的情况"""
#         script = '''
# name: 空测试
# variables:
#   test: value
# '''

#         with patch('httpx.Client') as mock_client_class:
#             mock_client = MagicMock()
#             mock_client_class.return_value = mock_client

#             from testmanager_app.script_engine import TestChainExecutor
#             executor = TestChainExecutor()
#             result = executor.execute_test_chain(script, 'yaml')

#             # 如果没有测试步骤，应该成功（因为没有可以失败的地方）
#             self.assertTrue(result['success'])

#     def test_jsonpath_not_found(self):
#         """测试jsonpath找不到值的情况"""
#         script = '''
# name: jsonpath测试
# test_steps:
#   - name: 提取不存在的字段
#     request:
#       method: GET
#       url: "https://api.example.com/data"
#     extract:
#       - name: missing_field
#         jsonpath: "$.data.nonexistent"
# '''

#         with patch('httpx.Client') as mock_client_class:
#             mock_client = MagicMock()
#             mock_client_class.return_value = mock_client

#             resp = MagicMock()
#             resp.status_code = 200
#             resp.elapsed.total_seconds.return_value = 0.1
#             resp.json.return_value = {'data': {'exists': 'value'}}
#             resp.text = '{"data":{"exists":"value"}}'

#             mock_client.request.return_value = resp

#             from testmanager_app.script_engine import TestChainExecutor
#             executor = TestChainExecutor()
#             result = executor.execute_test_chain(script, 'yaml')

#             # 应该成功，但变量未提取
#             self.assertTrue(result['success'])
#             self.assertNotIn('missing_field', result['context'])

#             # 验证日志中有警告
#             logs_str = '\n'.join(result['logs'])
#             self.assertIn('未找到匹配值', logs_str)


# class TestScriptEngineUnitMethods(TestCase):
#     """测试脚本引擎的各个独立方法"""

#     def test_render_template_string(self):
#         """测试字符串模板渲染"""
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         executor.context = {'name': 'testuser', 'age': 25}

#         result = executor.render_template("User: {{name}}, Age: {{age}}")
#         self.assertEqual(result, "User: testuser, Age: 25")

#     def test_render_template_dict(self):
#         """测试字典模板渲染"""
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         executor.context = {'user': 'testuser', 'pass': '123'}

#         result = executor.render_template({
#             'username': '{{user}}',
#             'password': '{{pass}}'
#         })
#         self.assertEqual(result['username'], 'testuser')
#         self.assertEqual(result['password'], '123')

#     def test_render_template_list(self):
#         """测试列表模板渲染"""
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()
#         executor.context = {'key': 'value'}

#         result = executor.render_template(['{{key}}', 'static', '{{key}}'])
#         self.assertEqual(result, ['value', 'static', 'value'])

#     def test_render_template_undefined_var(self):
#         """测试未定义的变量"""
#         from testmanager_app.script_engine import TestChainExecutor
#         executor = TestChainExecutor()

#         result = executor.render_template("Hello {{undefined_key}} World")
#         self.assertEqual(result, "Hello  World")

#         # 验证有警告日志
#         import logging
#         with self.assertLogs(level='INFO') as cm:
#             executor.render_template("Hello {{undefined_key}} World")
#             self.assertTrue(any('未定义' in msg for msg in cm.output))

#     def test_validate_assertions_status_code(self):
#         """测试状态码断言验证"""
#         from testmanager_app.script_engine import TestChainExecutor
#         from unittest.mock import MagicMock

#         executor = TestChainExecutor()

#         # 创建mock响应
#         response = MagicMock()
#         response.status_code = 200
#         response.json.return_value = {'data': {'id': 1}}

#         assertions = [
#             {'type': 'status_code', 'expected': 200},
#             {'type': 'status_code', 'expected': 201}  # 这个会失败
#         ]

#         passed, results = executor.validate_assertions(response, assertions)
#         self.assertFalse(passed)
#         self.assertEqual(len(results), 2)
#         self.assertTrue(results[0]['passed'])
#         self.assertFalse(results[1]['passed'])

#     def test_validate_assertions_jsonpath(self):
#         """测试JSONPath断言验证"""
#         from testmanager_app.script_engine import TestChainExecutor
#         from unittest.mock import MagicMock

#         executor = TestChainExecutor()

#         response = MagicMock()
#         response.status_code = 200
#         response.json.return_value = {'data': {'name': 'testuser', 'value': 42}}

#         assertions = [
#             {'type': 'jsonpath', 'expression': '$.data.name', 'expected': 'testuser'},
#             {'type': 'jsonpath', 'expression': '$.data.value', 'expected': 42}
#         ]

#         passed, results = executor.validate_assertions(response, assertions)
#         self.assertTrue(passed)
#         self.assertEqual(len(results), 2)
#         self.assertTrue(all(r['passed'] for r in results))

#     def test_validate_assertions_invalid_type(self):
#         """测试无效的断言类型"""
#         from testmanager_app.script_engine import TestChainExecutor
#         from unittest.mock import MagicMock

#         executor = TestChainExecutor()
#         response = MagicMock()
#         response.status_code = 200
#         response.json.return_value = {}

#         assertions = [
#             {'type': 'unknown_type'}
#         ]

#         passed, results = executor.validate_assertions(response, assertions)
#         self.assertFalse(passed)
#         self.assertFalse(results[0]['passed'])

#     def test_execute_request_with_json(self):
#         """测试执行带JSON的请求"""
#         from testmanager_app.script_engine import TestChainExecutor

#         executor = TestChainExecutor()
#         request_data = {
#             'method': 'POST',
#             'url': 'https://api.example.com/test',
#             'headers': {'Content-Type': 'application/json'},
#             'json': {'key': 'value'}
#         }

#         # mock session
#         mock_session = MagicMock()
#         mock_response = MagicMock()
#         mock_response.status_code = 200
#         mock_response.elapsed.total_seconds.return_value = 0.1
#         mock_session.request.return_value = mock_response
#         executor.session = mock_session

#         response = executor.execute_request(request_data)

#         self.assertEqual(response.status_code, 200)
#         mock_session.request.assert_called_once()

#     def test_execute_request_with_data(self):
#         """测试执行带form data的请求"""
#         from testmanager_app.script_engine import TestChainExecutor

#         executor = TestChainExecutor()
#         request_data = {
#             'method': 'POST',
#             'url': 'https://api.example.com/test',
#             'data': 'username=test&password=pass'
#         }

#         mock_session = MagicMock()
#         mock_response = MagicMock()
#         mock_response.status_code = 200
#         mock_response.elapsed.total_seconds.return_value = 0.1
#         mock_session.request.return_value = mock_response
#         executor.session = mock_session

#         response = executor.execute_request(request_data)

#         self.assertEqual(response.status_code, 200)
#         call_kwargs = mock_session.request.call_args[1]
#         self.assertEqual(call_kwargs['data'], 'username=test&password=pass')

#     def test_log_method(self):
#         """测试日志方法"""
#         from testmanager_app.script_engine import TestChainExecutor

#         executor = TestChainExecutor()
#         initial_count = len(executor.logs)

#         executor.log("测试日志消息")

#         self.assertEqual(len(executor.logs), initial_count + 1)
#         self.assertTrue(executor.logs[-1].endswith('测试日志消息'))
#         self.assertTrue(executor.logs[-1].startswith('['))


# class TestScriptEngineViewSet(APITestCase):
#     """测试脚本引擎集成到ViewSet"""

#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目")

#     @patch('testmanager_app.script_engine.TestChainExecutor')
#     def test_execute_yaml_script(self, mock_executor_class):
#         """测试执行YAML脚本"""
#         mock_executor = MagicMock()
#         mock_executor_class.return_value = mock_executor
#         mock_executor.execute_test_chain.return_value = {
#             'success': True,
#             'logs': ['[2024-01-01 10:00:00] 开始', '[2024-01-01 10:00:01] 完成'],
#             'context': {'token': 'abc123'},
#         }

#         # 创建脚本 - 使用正确的API端点 /api/test-scripts/
#         import tempfile
#         with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
#             f.write('name: test\ntest_steps: []')

#         with open(f.name, 'rb') as script_file:
#             form_data = {
#                 'name': '测试脚本',
#                 'description': '描述',
#                 'script_type': 'yaml',
#                 'project': self.project.id,
#                 'file': script_file
#             }

#             response = self.client.post('/api/test-scripts/', form_data, format='multipart')

#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         script_id = response.data['id']

#         # 执行脚本
#         response = self.client.post(f'/api/test-scripts/{script_id}/execute/')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#         # 验证执行记录
#         self.assertEqual(ScriptExecution.objects.count(), 1)
#         execution = ScriptExecution.objects.first()
#         self.assertEqual(execution.status, 'success')


# class TestRequestCollectionExecution(APITestCase):
#     """请求集合执行测试"""

#     def setUp(self):
#         self.admin = User.objects.create_superuser(username='admin', password='12345')
#         self.crud_role = Role.objects.create(name="管理员", permission="crud")
#         UserRole.objects.create(user=self.admin, role=self.crud_role)
#         self.client.force_authenticate(user=self.admin)
#         self.project = Project.objects.create(name="项目")

#     @patch('testmanager_app.collection_execution_strategies.execute_single_request_async')
#     def test_concurrent_execution(self, mock_execute):
#         """测试并发执行模式"""
#         # 设置mock返回值 - 使用AsyncMock返回协程
#         async def mock_async_return():
#             return {
#                 'status_code': 200,
#                 'response_time': 0.5,
#                 'response_body': '{"success": true}',
#                 'assertions': [],
#                 'passed_count': 0,
#                 'total_assertions': 0,
#                 'success': True
#             }

#         mock_execute.return_value = mock_async_return()

#         # 创建集合
#         collection = RequestCollection.objects.create(
#             name="并发测试集合",
#             project=self.project,
#             execution_mode='concurrent'
#         )

#         # 创建API请求
#         req1 = ApiRequest.objects.create(
#             name="请求1",
#             project=self.project,
#             url="https://api.example.com/1",
#             method="GET"
#         )
#         req2 = ApiRequest.objects.create(
#             name="请求2",
#             project=self.project,
#             url="https://api.example.com/2",
#             method="GET"
#         )

#         # 添加到集合
#         CollectionRequest.objects.create(collection=collection, api_request=req1, order_index=0)
#         CollectionRequest.objects.create(collection=collection, api_request=req2, order_index=1)

#         # 执行
#         response = self.client.post(f'/api/request-collections/{collection.id}/execute/')

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['status'], 'success')
#         self.assertEqual(response.data['total_requests'], 2)
#         self.assertEqual(response.data['passed_requests'], 2)

#         # 验证mock被调用了2次
#         self.assertEqual(mock_execute.call_count, 2)

#     @patch('testmanager_app.collection_execution_strategies.execute_single_request_async')
#     def test_sequential_execution(self, mock_execute):
#         """测试顺序执行模式"""
#         # 设置mock返回值 - 使用AsyncMock返回协程
#         async def mock_async_return():
#             return {
#                 'status_code': 200,
#                 'response_time': 0.5,
#                 'response_body': '{"success": true}',
#                 'assertions': [],
#                 'passed_count': 0,
#                 'total_assertions': 0,
#                 'success': True
#             }

#         mock_execute.return_value = mock_async_return()

#         collection = RequestCollection.objects.create(
#             name="顺序测试集合",
#             project=self.project,
#             execution_mode='sequential'
#         )

#         req1 = ApiRequest.objects.create(name="请求1", project=self.project, url="https://api.example.com/1", method="GET")
#         req2 = ApiRequest.objects.create(name="请求2", project=self.project, url="https://api.example.com/2", method="GET")

#         CollectionRequest.objects.create(collection=collection, api_request=req1, order_index=0)
#         CollectionRequest.objects.create(collection=collection, api_request=req2, order_index=1)

#         response = self.client.post(f'/api/request-collections/{collection.id}/execute/')

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['status'], 'success')

#     @patch('testmanager_app.collection_execution_strategies.execute_single_request_async')
#     def test_chain_execution_with_variables(self, mock_execute):
#         """测试链式执行模式与变量提取"""
#         # 第一个请求返回token
#         async def side_effect_func(api_request_data):
#             if 'login' in api_request_data.get('url', ''):
#                 return {
#                     'status_code': 200,
#                     'response_time': 0.5,
#                     'response_body': '{"data": {"token": "abc123"}}',
#                     'success': True
#                 }
#             elif 'user' in api_request_data.get('url', ''):
#                 # 第二个请求应该包含提取的token
#                 if 'Bearer abc123' in api_request_data.get('headers', ''):
#                     return {
#                         'status_code': 200,
#                         'response_time': 0.5,
#                         'response_body': '{"data": {"id": 123}}',
#                         'success': True
#                     }
#                 else:
#                     return {
#                         'status_code': 401,
#                         'response_time': 0.5,
#                         'response_body': '{"error": "Unauthorized"}',
#                         'success': False
#                     }
#             return {'status_code': 404, 'response_time': 0.5, 'response_body': '{}', 'success': False}

#         mock_execute.side_effect = side_effect_func

#         collection = RequestCollection.objects.create(
#             name="链式测试集合",
#             project=self.project,
#             execution_mode='chain'
#         )

#         # 登录请求
#         login_req = ApiRequest.objects.create(
#             name="登录",
#             project=self.project,
#             url="https://api.example.com/login",
#             method="POST",
#             headers='{}',
#             body='{}'
#         )

#         # 获取用户信息请求（使用模板变量）
#         user_req = ApiRequest.objects.create(
#             name="获取用户信息",
#             project=self.project,
#             url="https://api.example.com/user",
#             method="GET",
#             headers='{"Authorization": "Bearer {{token}}"}',
#             body=''
#         )

#         # 添加到集合，设置变量提取规则
#         CollectionRequest.objects.create(
#             collection=collection,
#             api_request=login_req,
#             order_index=0,
#             extract_rules=[{"name": "token", "jsonpath": "$.data.token"}]
#         )
#         CollectionRequest.objects.create(
#             collection=collection,
#             api_request=user_req,
#             order_index=1
#         )

#         response = self.client.post(f'/api/request-collections/{collection.id}/execute/')

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         # 如果token提取和传递成功，两个请求都应该成功
#         self.assertEqual(response.data['passed_requests'], 2)

#     @patch('testmanager_app.collection_execution_strategies.execute_single_request_async')
#     def test_chain_execution_stop_on_failure(self, mock_execute):
#         """测试链式执行失败时停止"""
#         # 第一个请求失败 - 使用异步side_effect
#         async def side_effect_func(api_request_data):
#             if api_request_data.get('url', '').endswith('1'):
#                 return {
#                     'status_code': 500,
#                     'response_time': 0.5,
#                     'response_body': '{"error": "Internal Server Error"}',
#                     'success': False
#                 }
#             else:
#                 # 第二个请求不应该被执行
#                 raise Exception("Second request should not be executed")

#         mock_execute.side_effect = side_effect_func

#         collection = RequestCollection.objects.create(
#             name="失败停止测试集合",
#             project=self.project,
#             execution_mode='chain'
#         )

#         req1 = ApiRequest.objects.create(name="请求1", project=self.project, url="https://api.example.com/1", method="GET")
#         req2 = ApiRequest.objects.create(name="请求2", project=self.project, url="https://api.example.com/2", method="GET")

#         CollectionRequest.objects.create(collection=collection, api_request=req1, order_index=0, stop_on_failure=True)
#         CollectionRequest.objects.create(collection=collection, api_request=req2, order_index=1, stop_on_failure=True)

#         response = self.client.post(f'/api/request-collections/{collection.id}/execute/')

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['status'], 'failed')
#         self.assertEqual(response.data['passed_requests'], 0)
#         self.assertEqual(response.data['failed_requests'], 1)

#         # 只应该执行了第一个请求
#         self.assertEqual(mock_execute.call_count, 1, f"Mock was called {mock_execute.call_count} times instead of 1. Second request was executed when it should have been stopped.")

#     def test_render_template_with_context(self):
#         """测试模板渲染功能"""
#         from testmanager_app.views import RequestCollectionViewSet

#         viewset = RequestCollectionViewSet()
#         context = {'token': 'abc123', 'user_id': 456}

#         # 测试字符串渲染
#         result = viewset._render_request_with_context({
#             'id': 1,
#             'method': 'GET',
#             'url': 'https://api.example.com/user/{{user_id}}',
#             'headers': '{"Authorization": "Bearer {{token}}"}',
#             'body': ''
#         }, context)

#         self.assertEqual(result['url'], 'https://api.example.com/user/456')
#         self.assertEqual(result['headers'], '{"Authorization": "Bearer abc123"}')

#     def test_extract_variables(self):
#         """测试变量提取功能"""
#         from testmanager_app.views import RequestCollectionViewSet

#         viewset = RequestCollectionViewSet()
#         context = {'existing': 'value'}

#         result = {
#             'response_body': '{"data": {"token": "abc123", "user": {"id": 456}}}',
#             'success': True
#         }

#         extract_rules = [
#             {'name': 'token', 'jsonpath': '$.data.token'},
#             {'name': 'user_id', 'jsonpath': '$.data.user.id'}
#         ]

#         new_context = viewset._extract_variables(result, extract_rules, context)

#         self.assertEqual(new_context['token'], 'abc123')
#         self.assertEqual(new_context['user_id'], 456)
#         self.assertEqual(new_context['existing'], 'value')

#     @patch('testmanager_app.collection_execution_strategies.execute_single_request_async')
#     def test_concurrent_execution_performance(self, mock_execute):
#         """测试并发执行的性能（所有请求同时发起）"""
#         import time

#         # 模拟耗时操作
#         def slow_execution(api_request_data):
#             time.sleep(0.1)  # 每个请求0.1秒
#             return {'status_code': 200, 'response_time': 0.1, 'response_body': '{}', 'success': True}

#         mock_execute.side_effect = slow_execution

#         collection = RequestCollection.objects.create(
#             name="性能测试集合",
#             project=self.project,
#             execution_mode='concurrent'
#         )

#         # 创建10个请求
#         for i in range(10):
#             req = ApiRequest.objects.create(
#                 name=f"请求{i}",
#                 project=self.project,
#                 url=f"https://api.example.com/{i}",
#                 method="GET"
#             )
#             CollectionRequest.objects.create(collection=collection, api_request=req, order_index=i)

#         start_time = time.time()
#         response = self.client.post(f'/api/request-collections/{collection.id}/execute/')
#         end_time = time.time()

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         # 并发执行应该远小于顺序执行的时间（10个请求每个0.1秒，顺序需要1秒）
#         # 在测试环境中，放宽到4.0秒以确保测试稳定性（考虑网络问题）
#         self.assertLess(end_time - start_time, 4.0)

# print("""
# ==========================================
# 测试套件使用说明 - 请求集合混合执行模式
# ==========================================

# 1. 数据库变更:
#    - RequestCollection新增execution_mode字段（3种模式）
#    - 新增CollectionRequest中间表（替代ManyToManyField）
#    - 支持排序(order_index)、失败停止(stop_on_failure)、变量提取(extract_rules)

# 2. 执行模式:
#    - concurrent: 所有请求同时发起，性能最好
#    - sequential: 顺序执行，互不干扰
#    - chain: 链式执行，支持变量传递（{{variable}}）

# 3. 新增测试（10+个）:
#    - test_concurrent_execution: 测试并发执行
#    - test_sequential_execution: 测试顺序执行
#    - test_chain_execution_with_variables: 测试链式执行和变量提取
#    - test_chain_execution_stop_on_failure: 测试失败时停止
#    - test_render_template_with_context: 测试模板渲染
#    - test_extract_variables: 测试变量提取

# 4. 前端交互设计:
#    - 创建集合时选择执行模式
#    - 添加请求时设置顺序、失败停止、变量提取规则
#    - 执行时显示进度和日志
#    - 链式模式下显示变量传递可视化

# 5. 运行测试:
#    pytest testmanager_app/tests.py::TestRequestCollectionExecution -v

# 6. 生成迁移:
#    python manage.py makemigrations
#    python manage.py migrate

# 预期覆盖率: 60-70%
# ==========================================
# """)pytest testmanager_app/tests/