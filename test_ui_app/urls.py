"""
UI测试应用的URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UITestScriptViewSet,
    UITestExecutionViewSet,
)

router = DefaultRouter()
router.register(r'ui-scripts', UITestScriptViewSet, basename='ui-script')
router.register(r'ui-executions', UITestExecutionViewSet, basename='ui-execution')

urlpatterns = [
    path('', include(router.urls)),
]

