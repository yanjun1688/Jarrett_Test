"""
Agent集成API视图 - 提供Agent辅助生成API测试的API端点
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging

from .agent_integration import APIAgentIntegrationService

logger = logging.getLogger(__name__)


class GenerateTestCaseWithAgentView(APIView):
    """
    使用Agent生成API测试用例
    POST /api/api-test/agent/generate
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """使用Agent生成API测试用例"""
        try:
            data = request.data
            api_definition = data.get('api_definition')
            project_id = data.get('project_id')
            module_id = data.get('module_id')
            use_rag = data.get('use_knowledge_base', True)
            user_id = request.user.id if request.user.is_authenticated else None
            
            if not api_definition or not project_id:
                return Response(
                    {'error': '缺少必要参数: api_definition, project_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            agent_service = APIAgentIntegrationService()
            
            result = agent_service.generate_test_case_with_agent_sync(
                api_definition=api_definition,
                project_id=project_id,
                module_id=module_id,
                use_rag=use_rag,
                user_id=user_id
            )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"使用Agent生成测试用例失败: {e}", exc_info=True)
            return Response(
                {'error': '服务器内部错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QueryKnowledgeBaseView(APIView):
    """
    查询知识库
    POST /api/agent/knowledge/query
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request):
        """查询知识库获取最佳实践和示例"""
        try:
            from core.agents.rag.knowledge_rag_agent import KnowledgeRAGAgent
            from core.agents.rag.rag_retriever_service import DjangoORMRAGRetriever
            
            data = request.data
            query = data.get('query')
            project_id = data.get('project_id')
            top_k = data.get('top_k', 5)
            use_llm = data.get('use_llm', True)
            
            if not query or not project_id:
                return Response(
                    {'error': '缺少必要参数: query, project_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            rag_retriever = DjangoORMRAGRetriever(project_id=project_id)
            agent = KnowledgeRAGAgent(rag_retriever=rag_retriever)
            
            result = await agent.query(
                query=query,
                top_k=top_k,
                use_llm=use_llm
            )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"查询知识库失败: {e}", exc_info=True)
            return Response(
                {'error': '服务器内部错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BuildKnowledgeBaseView(APIView):
    """
    构建知识库
    POST /api/agent/knowledge/build
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """构建项目知识库"""
        return Response({
            'success': False,
            'message': 'Knowledge builder service temporarily unavailable',
            'reason': 'test_agent_framework has been removed, migration in progress'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ListKnowledgeBasesView(APIView):
    """
    列出知识库
    GET /api/agent/knowledge/list
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """列出知识库"""
        try:
            from core.models.knowledge import KnowledgeBase
            from testmanager_app.serializers import KnowledgeBaseSerializer
            
            # 获取知识库列表
            knowledge_bases = KnowledgeBase.objects.all().order_by('-created_at')
            
            # 序列化
            serializer = KnowledgeBaseSerializer(knowledge_bases, many=True)
            
            return Response({
                'success': True,
                'knowledge_bases': serializer.data,
                'total': knowledge_bases.count()
            })
            
        except Exception as e:
            logger.error(f"列出知识库失败: {e}", exc_info=True)
            return Response(
                {'error': '服务器内部错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetBestPracticesView(APIView):
    """
    获取最佳实践建议
    POST /api/agent/best-practices
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """获取测试最佳实践建议"""
        return Response({
            'success': False,
            'message': 'Best practices service temporarily unavailable',
            'reason': 'test_agent_framework has been removed, migration in progress'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
