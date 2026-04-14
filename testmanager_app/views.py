"""
JTest API Views - 主导入文件

注意：此文件已拆分为多个模块文件，请导入具体的视图模块
路由已统一到 api/urls.py (/api/v1/)
"""
from __future__ import annotations
from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response

from .project_views import ProjectViewSet, ModuleViewSet
from .testcase_views import TestCaseViewSet, TestExecutionViewSet
from .controllers.api_views import (
    ApiRequestViewSet, ApiAssertionViewSet,
    RequestCollectionViewSet, CollectionExecutionViewSet
)
from .controllers.report_views import (
    TestReportViewSet, TestReportDataView
)
from .auth_views import (
    UserViewSet, FeatureTestCaseViewSet,
    LoginView, MeView, LogoutView, RefreshTokenView
)
from .controllers.script_views import TestScriptViewSet, ScriptExecutionViewSet
from .chatbots.chatbot_views import (
    EnhancedChatBotView, GetModelListView, ClearConversationView,
    GetAvailableToolsView, TestToolExecutionView,
    ConversationListView, ConversationDetailView, CacheStatsView
)
from .controllers.skill_api_views import (
    SkillRemoteSearchView, SkillLocalListView, SkillExecuteView
)

__all__ = [
    'yaml_to_collection',
    'validate_yaml_config',
    
    'ProjectViewSet',
    'ModuleViewSet',
    
    'TestCaseViewSet',
    'TestExecutionViewSet',
    
    'ApiRequestViewSet',
    'ApiAssertionViewSet',
    'RequestCollectionViewSet',
    'CollectionExecutionViewSet',
    
    'TestReportViewSet',
    'TestReportDataView',
    
    'LoginView',
    'MeView',
    'LogoutView',
    'RefreshTokenView',
    
    'UserViewSet',
    'FeatureTestCaseViewSet',
    
    'TestScriptViewSet',
    'ScriptExecutionViewSet',
    
    'EnhancedChatBotView',
    'GetModelListView',
    'ClearConversationView',
    'GetAvailableToolsView',
    'TestToolExecutionView',
    'ConversationListView',
    'ConversationDetailView',
    'CacheStatsView',
    
    'SkillRemoteSearchView',
    'SkillLocalListView',
    'SkillExecuteView',
]

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from testmanager_app.services.yaml_converter import YamlToCollectionConverter
from testmanager_app.services.yaml_validator import YamlValidator
import base64
import logging

logger = logging.getLogger(__name__)


def _decode_yaml_content(yaml_content: str) -> str:
    """尝试解码base64编码的YAML内容"""
    try:
        decoded = base64.b64decode(yaml_content.encode('utf-8')).decode('utf-8')
        if decoded.strip().startswith(('name:', 'steps:', '-')):
            return decoded
    except Exception:
        pass
    return yaml_content


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yaml_to_collection(request: Request, project_id: int) -> Response:
    """
    将YAML配置转换为RequestCollection
    
    Args:
        request: HTTP请求
        project_id: 项目ID
    
    Returns:
        Response: 转换结果
    """
    try:
        yaml_content = request.data.get('yaml_content', '')
        yaml_content = _decode_yaml_content(yaml_content)
        name = request.data.get('name', '')
        description = request.data.get('description', '')
        execution_mode = request.data.get('execution_mode', 'chain')
        validate_only = request.data.get('validate_only', False)
        
        if not yaml_content:
            return Response(
                {'code': 400, 'message': 'YAML内容不能为空', 'data': {}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not name:
            return Response(
                {'code': 400, 'message': '集合名称不能为空', 'data': {}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        converter = YamlToCollectionConverter(
            project_id=project_id,
            created_by_id=request.user.id
        )
        
        success, result = converter.convert(
            yaml_content=yaml_content,
            name=name,
            description=description,
            execution_mode=execution_mode,
            validate_only=validate_only
        )
        
        logger.info(f"YAML转换结果: success={success}, result={result}")
        
        if success:
            if validate_only:
                return Response({
                    'code': 200,
                    'message': '验证成功',
                    'data': result
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'code': 201,
                    'message': '转换成功',
                    'data': result
                }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'code': 400,
                'message': result.get('error', '转换失败'),
                'data': result
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"YAML转换失败: {str(e)}", exc_info=True)
        return Response(
            {'error': f'转换失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_yaml_config(request: Request, project_id: int) -> Response:
    """
    验证YAML配置
    
    Args:
        request: HTTP请求
        project_id: 项目ID
    
    Returns:
        Response: 验证结果
    """
    try:
        yaml_content = request.data.get('yaml_content', '')
        yaml_content = _decode_yaml_content(yaml_content)
        
        if not yaml_content:
            return Response(
                {'code': 400, 'message': 'YAML内容不能为空', 'data': {}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validator = YamlValidator()
        
        check_variables = request.data.get('check_variables', True)
        check_jsonpath = request.data.get('check_jsonpath', True)
        
        is_valid, errors, warnings = validator.validate(yaml_content, check_variables, check_jsonpath)
        
        import yaml
        try:
            config = yaml.safe_load(yaml_content)
            total_steps = len(config.get('steps', [])) if isinstance(config, dict) else 0
        except Exception:
            total_steps = 0
        
        if is_valid:
            return Response({
                'code': 200,
                'message': 'YAML配置验证通过',
                'data': {
                    'valid': True,
                    'stats': {
                        'total_steps': total_steps
                    }
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'code': 400,
                'message': 'YAML配置验证失败',
                'data': {
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"YAML验证失败: {str(e)}", exc_info=True)
        return Response(
            {'error': f'验证失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )