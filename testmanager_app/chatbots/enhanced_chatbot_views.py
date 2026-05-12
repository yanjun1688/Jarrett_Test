"""
hatBot视图
支持自然语言+API文档的智能接口测试


"""
import logging
from typing import Any
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def enhanced_chatbot_query(request):
    """
    增强版ChatBot查询接口
    支持自然语言+API文档的智能接口测试
    
    注意：test_agent_framework 已删除，服务暂时不可用
    """
    return Response({
        "success": False,
        "message": "Enhanced ChatBot service temporarily unavailable",
        "reason": "test_agent_framework has been removed, migration in progress",
        "data": None
    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def api_test_orchestration(request):
    """
    API测试编排接口
    """
    return Response({
        "success": False,
        "message": "API test orchestration service temporarily unavailable",
        "reason": "test_agent_framework has been removed, migration in progress"
    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def generate_test_cases_from_docs(request):
    """
    从API文档生成测试用例
    """
    return Response({
        "success": False,
        "message": "Test case generation service temporarily unavailable",
        "reason": "test_agent_framework has been removed, migration in progress"
    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def execute_test_plan(request):
    """
    执行测试计划
    """
    return Response({
        "success": False,
        "message": "Test plan execution service temporarily unavailable",
        "reason": "test_agent_framework has been removed, migration in progress"
    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
