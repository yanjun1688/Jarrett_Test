from django.urls import path, include
from rest_framework.routers import DefaultRouter
from testmanager_app import views

router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet)
router.register(r'modules', views.ModuleViewSet)
router.register(r'testcases', views.TestCaseViewSet)
router.register(r'executions', views.TestExecutionViewSet)
router.register(r'reports', views.TestReportViewSet)
router.register(r'test-scripts', views.TestScriptViewSet)
router.register(r'script-executions', views.ScriptExecutionViewSet)
router.register(r'api-requests', views.ApiRequestViewSet)
router.register(r'api-assertions', views.ApiAssertionViewSet)
router.register(r'request-collections', views.RequestCollectionViewSet)
router.register(r'collection-executions', views.CollectionExecutionViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'user-roles', views.UserRoleViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'feature-tests', views.FeatureTestCaseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('report-data/', views.TestReportDataView.as_view(), name='report-data'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh-token/', views.RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/debug/', views.DebugAuthView.as_view(), name='auth-debug'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    # YAML配置工具相关API
    path('projects/<int:project_id>/yaml-to-collection/', views.yaml_to_collection, name='yaml-to-collection'),
    path('projects/<int:project_id>/yaml/validate/', views.validate_yaml_config, name='validate-yaml'),
    # 注意：下面的路由已弃用，使用ViewSet的execute action代替
    # path('api-requests-async/<int:api_request_id>/execute/', views.execute_api_request_async, name='execute-api-request-async'),
]