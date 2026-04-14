"""
Agent集成API视图
提供Agent辅助生成UI测试的API端点
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging

from .agent_integration import AgentIntegrationService

logger = logging.getLogger(__name__)


class GenerateScriptWithAgentView(APIView):
    """
    使用Agent生成UI测试脚本
    POST /api/ui-test/agent/generate
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """使用Agent生成UI测试脚本"""
        try:
            from .agent_integration import AgentIntegrationService
            
            data = request.data
            description = data.get('description')
            project_id = data.get('project_id')
            url = data.get('url')
            use_rag = data.get('use_knowledge_base', True)
            user_id = request.user.id if request.user.is_authenticated else None
            
            if not description or not project_id:
                return Response(
                    {'error': '缺少必要参数: description, project_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 创建Agent集成服务
            agent_service = AgentIntegrationService()
            
            # 同步执行（在生产环境应改为异步任务）
            result = agent_service.generate_script_with_agent_sync(
                description=description,
                project_id=project_id,
                url=url,
                use_rag=use_rag,
                user_id=user_id
            )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"使用Agent生成脚本失败: {e}", exc_info=True)
            return Response(
                {'error': '服务器内部错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
