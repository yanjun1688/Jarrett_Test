from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .import_export import import_testcases, export_testcases, get_import_template

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

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/import-testcases/', import_testcases, name='import_testcases'),
    path('api/export-testcases/', export_testcases, name='export_testcases'),
    path('api/import-template/', get_import_template, name='import_template'),
]