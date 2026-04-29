"""
Unified API Routing Configuration (v1)

All API endpoints are consolidated under /api/v1/ for consistency.
Structure:
    /api/v1/
    ├── auth/                      # Authentication
    ├── chatbot/                   # Chatbot AI
    ├── knowledge/                 # Knowledge base
    ├── planning/                  # Test planning
    ├── test-generation/           # Test generation (UI/API/PRD)
    ├── projects/                  # Project management (ViewSet)
    ├── modules/                   # Module management (ViewSet)
    ├── testcases/                 # Test cases (ViewSet)
    ├── executions/                # Execution records (ViewSet)
    ├── reports/                   # Reports (ViewSet)
    ├── api-requests/              # API requests (ViewSet)
    ├── api-assertions/            # API assertions (ViewSet)
    ├── request-collections/       # Request collections (ViewSet)
    ├── collection-executions/     # Collection executions (ViewSet)
    ├── test-scripts/              # Test scripts (ViewSet)
    ├── script-executions/         # Script executions (ViewSet)
    ├── users/                     # Users (ViewSet)
    ├── feature-tests/             # Feature tests (ViewSet)
    ├── ui-test/                   # UI test module
    ├── skills/                    # Skills/workflows
    └── projects/<id>/...          # Project-level operations
"""
from __future__ import annotations

from typing import Any

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.urlpatterns import format_suffix_patterns

from api.v1.knowledge import views as knowledge_views
from api.v1.planning import views as planning_views
from api.v1.execution import views as execution_views
from api.v1.test_generation import views as test_generation_views

from testmanager_app.chatbots import chatbot_views
from testmanager_app.controllers import skill_api_views
from testmanager_app import auth_views
from testmanager_app import views as tm_views
from test_ui_app import views as ui_views
from api.v1.unified import views as unified_views

app_name = 'api'

router = DefaultRouter()

router.register(r'projects', tm_views.ProjectViewSet, basename='project')
router.register(r'modules', tm_views.ModuleViewSet, basename='module')
router.register(r'testcases', tm_views.TestCaseViewSet, basename='testcase')
router.register(r'executions', tm_views.TestExecutionViewSet, basename='execution')
router.register(r'reports', tm_views.TestReportViewSet, basename='report')
router.register(r'test-scripts', tm_views.TestScriptViewSet, basename='test-script')
router.register(r'script-executions', tm_views.ScriptExecutionViewSet, basename='script-execution')
router.register(r'api-requests', tm_views.ApiRequestViewSet, basename='api-request')
router.register(r'api-assertions', tm_views.ApiAssertionViewSet, basename='api-assertion')
router.register(r'request-collections', tm_views.RequestCollectionViewSet, basename='request-collection')
router.register(r'collection-executions', tm_views.CollectionExecutionViewSet, basename='collection-execution')
router.register(r'pressure-test-configs', tm_views.PressureTestConfigViewSet, basename='pressure-test-config')
router.register(r'pressure-test-executions', tm_views.PressureTestExecutionViewSet, basename='pressure-test-execution')
router.register(r'advanced-pressure-configs', tm_views.AdvancedPressureTestConfigViewSet, basename='advanced-pressure-config')
router.register(r'advanced-pressure-executions', tm_views.AdvancedPressureTestExecutionViewSet, basename='advanced-pressure-execution')
router.register(r'users', tm_views.UserViewSet, basename='user')
router.register(r'feature-tests', tm_views.FeatureTestCaseViewSet, basename='feature-test')

router.register(r'ui-scripts', ui_views.UITestScriptViewSet, basename='ui-script')
router.register(r'ui-executions', ui_views.UITestExecutionViewSet, basename='ui-execution')

router.register(r'unified/scripts', unified_views.UnifiedScriptViewSet, basename='unified-script')
router.register(r'unified/executions', unified_views.UnifiedExecutionViewSet, basename='unified-execution')

auth_patterns = [
    path('login/', auth_views.LoginView.as_view(), name='auth-login'),
    path('logout/', auth_views.LogoutView.as_view(), name='auth-logout'),
    path('me/', auth_views.MeView.as_view(), name='auth-me'),
    path('refresh/', auth_views.RefreshTokenView.as_view(), name='auth-refresh'),
]

chatbot_patterns = [
    path('chat/', chatbot_views.EnhancedChatBotView.as_view(), name='chatbot-chat'),
    path('models/', chatbot_views.GetModelListView.as_view(), name='chatbot-models'),
    path('clear/', chatbot_views.ClearConversationView.as_view(), name='chatbot-clear'),
    path('tools/', chatbot_views.GetAvailableToolsView.as_view(), name='chatbot-tools'),
    path('test-tool/', chatbot_views.TestToolExecutionView.as_view(), name='chatbot-test-tool'),
    path('conversations/', chatbot_views.ConversationListView.as_view(), name='chatbot-conversations'),
    path('conversations/<str:conversation_id>/', chatbot_views.ConversationDetailView.as_view(), name='chatbot-conversation-detail'),
    path('cache-stats/', chatbot_views.CacheStatsView.as_view(), name='chatbot-cache-stats'),
    path('mcp-status/', chatbot_views.MCPStatusView.as_view(), name='chatbot-mcp-status'),
    path('execution-logs/', chatbot_views.ChatBotExecutionLogListView.as_view(), name='chatbot-execution-logs'),
    path('execution-logs/<int:log_id>/', chatbot_views.ChatBotExecutionLogDetailView.as_view(), name='chatbot-execution-log-detail'),
]

knowledge_patterns = [
    path('query/', knowledge_views.QueryKnowledgeView.as_view(), name='query-knowledge'),
    path('build/', knowledge_views.BuildKnowledgeBaseView.as_view(), name='build-knowledge-base'),
    path('list/', knowledge_views.ListKnowledgeBasesView.as_view(), name='list-knowledge-bases'),
    path('upload/', knowledge_views.UploadDocumentView.as_view(), name='upload-document'),
    path('best-practices/', knowledge_views.GetBestPracticesView.as_view(), name='get-best-practices'),
    path('page-structure/', execution_views.PageStructureView.as_view(), name='page-structure'),
    path('documents/', knowledge_views.ListKnowledgeDocumentsView.as_view(), name='list-knowledge-documents'),
    path('documents/<int:pk>/', knowledge_views.DeleteKnowledgeDocumentView.as_view(), name='delete-knowledge-document'),
    path('documents/<int:pk>/sync/', knowledge_views.SyncDocumentView.as_view(), name='sync-document'),
]

planning_patterns = [
    path('plan/', planning_views.PlanTestView.as_view(), name='plan-test'),
    path('refine/', planning_views.RefinePlanView.as_view(), name='refine-plan'),
]

ui_test_patterns = [
    path('extract-elements/', ui_views.ExtractElementsView.as_view(), name='extract-elements'),
]

# [DEPRECATED 2026-04-24] test-generation 模块已废弃
# 所有端点返回 410 Gone，请使用 /api/v1/chatbot/message/ 替代
# 计划在 2026-05-24 物理删除这些路由
test_generation_patterns = [
    path('ui-test/', test_generation_views.GenerateUITestView.as_view(), name='generate-ui-test'),
    path('api-test/', test_generation_views.GenerateAPITestView.as_view(), name='generate-api-test'),
    path('from-prd/', test_generation_views.GenerateFromPRDView.as_view(), name='generate-from-prd'),
]

skills_patterns = [
    # [DEPRECATED] GET /skills/remote-search/ - 旧版直接调用 npx CLI
    path('remote-search/', skill_api_views.SkillRemoteSearchView.as_view(), name='skill-remote-search'),
    
    # [DEPRECATED] POST /skills/install/ - 旧版直接调用 npx CLI  
    path('install/', skill_api_views.SkillInstallView.as_view(), name='skill-install'),
    
    # [MCP] POST /skills/search/ - 新版 MCP Server 代理
    path('search/', skill_api_views.SkillSearchMCPView.as_view(), name='skill-search'),
    
    # GET /skills/local/ - 本地技能列表（保持兼容）
    path('local/', skill_api_views.SkillLocalListView.as_view(), name='skill-local'),
    
    # POST /skills/execute/ - 执行技能（保持兼容）
    path('execute/', skill_api_views.SkillExecuteView.as_view(), name='skill-execute'),
]

urlpatterns = [
    path('', include(router.urls)),
    
    path('auth/', include((auth_patterns, 'auth'), namespace='auth')),
    path('chatbot/', include((chatbot_patterns, 'chatbot'), namespace='chatbot')),
    path('knowledge/', include((knowledge_patterns, 'knowledge'), namespace='knowledge')),
    path('planning/', include((planning_patterns, 'planning'), namespace='planning')),
    path('test-generation/', include((test_generation_patterns, 'test-generation'), namespace='test-generation')),
    path('ui-test/', include((ui_test_patterns, 'ui-test'), namespace='ui-test')),
    path('skills/', include((skills_patterns, 'skills'), namespace='skills')),
    
    path('report-data/', tm_views.TestReportDataView.as_view(), name='report-data'),
    
    path('projects/<int:project_id>/yaml-to-collection/', tm_views.yaml_to_collection, name='yaml-to-collection'),
    path('projects/<int:project_id>/yaml/validate/', tm_views.validate_yaml_config, name='validate-yaml'),
]