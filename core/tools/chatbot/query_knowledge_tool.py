"""
Query Knowledge Tool
查询知识库获取测试最佳实践、示例代码等
"""
from typing import Dict, Any, List, Optional
import logging

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class QueryKnowledgeTool(BaseTool):
    """查询知识库获取测试最佳实践、示例代码等"""
    
    def __init__(self, knowledge_rag_agent=None):
        super().__init__(
            name="query_knowledge",
            description="查询项目内部知识库。检索用户上传的项目文档、规范、示例代码等。\n\n参数：\n- query（必需）：搜索查询内容\n- topic（可选）：查询主题类型（best_practice/code_example/test_pattern/general）\n\n知识库范围：\n- 仅包含用户上传的项目内部文档\n\n返回：\n- 匹配的文档内容和来源",
            version="1.0.0"
        )
        self._knowledge_rag_agent = knowledge_rag_agent
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "搜索查询内容"
            },
            "topic": {
                "type": "string",
                "enum": ["best_practice", "code_example", "test_pattern", "general"],
                "description": "查询主题类型"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["query"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        查询知识库
        
        Args:
            query: 搜索查询内容
            topic: 查询主题类型
            
        Returns:
            知识库查询结果
        """
        query = kwargs.get("query")
        topic = kwargs.get("topic", "general")
        
        if not query:
            return ToolResult(
                success=False,
                data={},
                error="Missing required parameter: query"
            )
        
        # 检查 agent 是否可用（对象存在 + rag_retriever 不为 None）
        if not self._knowledge_rag_agent or not getattr(self._knowledge_rag_agent, 'rag_retriever', None):
            # 降级：直接用 KnowledgeRetriever 做向量检索
            logger.info("KnowledgeRAGAgent not available, using fallback retriever")
            try:
                from core.agents.rag.knowledge_retriever import KnowledgeRetriever
                
                retriever = KnowledgeRetriever()
                results = await sync_to_async(retriever.search)(
                    query, top_k=5, boost_project=True
                )
                
                if not results:
                    return ToolResult(
                        success=True,
                        data={"success": True, "answer": "知识库中暂无相关内容。", "documents": []},
                    )
                
                formatted_docs = []
                for r in results:
                    formatted_docs.append({
                        "content": r.get("content", ""),
                        "source": r.get("metadata", {}).get("source", "未知来源"),
                        "score": r.get("combined_score", r.get("score", 0.0))
                    })
                
                answer = "\n\n".join(
                    f"**[{i+1}] {d['source']}**\n{d['content'][:500]}"
                    for i, d in enumerate(formatted_docs[:5])
                )
                
                return ToolResult(
                    success=True,
                    data={"success": True, "answer": answer, "documents": formatted_docs},
                    metadata={"query": query, "topic": topic, "documents_found": len(formatted_docs)}
                )
            except Exception as e:
                logger.error(f"Knowledge retriever fallback failed: {e}")
                return ToolResult(
                    success=False,
                    data={},
                    error=f"知识库查询失败: {str(e)}"
                )
        
        try:
            document_type = self._map_topic_to_document_type(topic)
            
            result = await self._knowledge_rag_agent.query(
                query=query,
                top_k=5,
                document_type=document_type,
                use_llm=True
            )
            
            formatted_result = self._format_knowledge_response(result)
            
            return ToolResult(
                success=result.get("success", False),
                data=formatted_result,
                metadata={
                    "query": query,
                    "topic": topic,
                    "documents_found": len(result.get("documents", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Knowledge query failed: {e}")
            return ToolResult(
                success=False,
                data={
                    "success": False,
                    "message": "知识库查询出错",
                    "suggestions": self._generate_suggestions_for_empty()
                },
                error=f"Knowledge query error: {str(e)}"
            )
    
    def _map_topic_to_document_type(self, topic: str) -> Optional[str]:
        """将主题映射到文档类型"""
        topic_mapping = {
            "best_practice": "best_practice",
            "code_example": "code_example",
            "test_pattern": "test_pattern",
            "general": None
        }
        return topic_mapping.get(topic)
    
    def _format_knowledge_response(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """格式化知识库响应"""
        success = raw_response.get("success", False)
        answer = raw_response.get("answer", "")
        documents = raw_response.get("documents", [])
        
        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                "content": doc.get("content", doc.get("document", "")),
                "source": doc.get("metadata", {}).get("source", doc.get("source", "Unknown")),
                "score": doc.get("combined_score", doc.get("score", 0.0))
            })
        
        suggestions = self._generate_suggestions(answer, documents)
        
        return {
            "success": success,
            "answer": answer,
            "documents": formatted_docs,
            "suggestions": suggestions
        }
    
    def _generate_suggestions(
        self,
        answer: str,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """生成建议"""
        suggestions = []
        
        if not documents:
            suggestions.append("知识库中暂无相关内容")
            suggestions.append("您可以让我帮您生成测试用例")
            suggestions.append("或者查询其他相关主题")
        else:
            suggestions.append("查看更多相关文档")
            if len(documents) > 1:
                suggestions.append("了解代码实现示例")
            suggestions.append("查看测试最佳实践")
        
        return suggestions
    
    def _generate_suggestions_for_empty(self) -> List[str]:
        """为空知识库生成建议"""
        return [
            "您可以先问我关于测试的一般问题",
            "或者让我帮您生成测试用例",
            "也可以生成 UI 或 API 测试脚本"
        ]
    
    def _build_friendly_empty_message(self) -> str:
        """构建友好的空知识库提示"""
        return "知识库暂无内容，请先添加测试文档或最佳实践。"