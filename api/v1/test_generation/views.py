"""
Test generation API views
统一的测试生成 API：UI 测试、API 测试、PRD 处理

@deprecated: 2026-04-24 - 此API模块已废弃，所有端点返回 deprecated 响应
原因：应使用ChatbotAgent统一对话入口，不再通过REST API直接生成测试
替代方案：使用 /api/v1/chatbot/message/ 端点通过对话生成测试

注意：此模块已被物理废弃，所有API返回 410 Gone 状态
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


DEPRECATED_RESPONSE: Dict[str, Any] = {
    'success': False,
    'error': 'API_DEPRECATED',
    'message': '此API已废弃，请使用 Chatbot 对话接口生成测试',
    'alternative': '/api/v1/chatbot/message/',
    'documentation': 'https://docs.example.com/api/chatbot',
    'deprecated_at': '2026-04-24',
    'removed_at': '2026-05-24'
}


class GenerateUITestView(APIView):
    """
    生成 UI 测试脚本 (已废弃)
    
    POST /api/v1/test-generation/ui-test/
    
    @deprecated: 请使用 /api/v1/chatbot/message/ 发送对话消息生成UI测试
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        """返回废弃响应"""
        logger.warning(
            f"[DEPRECATED] GenerateUITestView called by user {request.user.id if request.user.is_authenticated else 'anonymous'}"
        )
        return Response(
            DEPRECATED_RESPONSE,
            status=status.HTTP_410_GONE
        )


class GenerateAPITestView(APIView):
    """
    生成 API 测试用例 (已废弃)
    
    POST /api/v1/test-generation/api-test/
    
    @deprecated: 请使用 /api/v1/chatbot/message/ 发送对话消息生成API测试
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        """返回废弃响应"""
        logger.warning(
            f"[DEPRECATED] GenerateAPITestView called by user {request.user.id if request.user.is_authenticated else 'anonymous'}"
        )
        return Response(
            DEPRECATED_RESPONSE,
            status=status.HTTP_410_GONE
        )


class GenerateFromPRDView(APIView):
    """
    从 PRD 文档生成测试用例 (已废弃)
    
    POST /api/v1/test-generation/from-prd/
    
    @deprecated: 请使用 /api/v1/chatbot/message/ 上传PRD文档到知识库后生成测试
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        """返回废弃响应"""
        logger.warning(
            f"[DEPRECATED] GenerateFromPRDView called by user {request.user.id if request.user.is_authenticated else 'anonymous'}"
        )
        return Response(
            DEPRECATED_RESPONSE,
            status=status.HTTP_410_GONE
        )