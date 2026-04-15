"""
UI Test App URL Configuration

Routes are now unified under api/urls.py (/api/v1/)
This file is kept for backward compatibility and exports.
"""
# pyright: reportAssignmentType=false

from __future__ import annotations

from typing import List

from django.urls import path, include
from django.urls.resolvers import URLPattern
from rest_framework.routers import DefaultRouter
from .views import (
    UITestScriptViewSet,
    UITestExecutionViewSet,
    ExtractElementsView,
)
from .agent_views import GenerateScriptWithAgentView

router: DefaultRouter = DefaultRouter()
router.register(r'ui-scripts', UITestScriptViewSet, basename='ui-script')
router.register(r'ui-executions', UITestExecutionViewSet, basename='ui-execution')

urlpatterns: List[URLPattern] = [
    path('', include(router.urls)),
    path('ui-test/agent/generate/', GenerateScriptWithAgentView.as_view(), name='generate-ui-test-with-agent'),
    path('extract-elements/', ExtractElementsView.as_view(), name='extract-elements'),
]