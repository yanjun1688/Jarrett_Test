"""
知识检索Agent
专门用于查询和检索测试知识库
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..llm.base_llm import BaseLLMService, create_llm_service
from ..rag.rag_retriever_service import RAGRetriever

logger = logging.getLogger(__name__)

# How many chunks to send to LLM (acts as implicit reranking via RRF)
RAG_CONTEXT_LIMIT = 10


class KnowledgeRAGAgent:
    """知识检索Agent"""

    def __init__(
        self,
        llm_service: Optional[BaseLLMService] = None,
        rag_retriever: Optional[RAGRetriever] = None,
    ):
        if llm_service is None:
            llm_service = create_llm_service(provider='openai')

        self.llm_service = llm_service
        self.rag_retriever = rag_retriever

    async def initialize(self) -> None:
        logger.info('Initializing KnowledgeRAGAgent')
        if self.llm_service and hasattr(self.llm_service, 'initialize'):
            await self.llm_service.initialize()
        if self.rag_retriever and hasattr(self.rag_retriever, 'initialize'):
            await self.rag_retriever.initialize()
        logger.info('KnowledgeRAGAgent initialization complete')

    async def cleanup(self) -> None:
        logger.info('Cleaning up KnowledgeRAGAgent')
        if self.rag_retriever and hasattr(self.rag_retriever, 'cleanup'):
            await self.rag_retriever.cleanup()
        if self.llm_service and hasattr(self.llm_service, 'cleanup'):
            await self.llm_service.cleanup()
        logger.info('KnowledgeRAGAgent cleanup complete')

    async def query(
        self,
        query: str,
        top_k: int = RAG_CONTEXT_LIMIT,
        document_type: Optional[str] = None,
        use_llm: bool = True,
        knowledge_base_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        查询知识库

        Args:
            query: 查询文本
            top_k: 返回结果数量
            document_type: 文档类型过滤
            use_llm: 是否使用LLM生成回答
            knowledge_base_id: 知识库ID过滤

        Returns:
            查询结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": "Knowledge retriever not available"
            }

        try:
            # 检索文档
            doc_types_list = [document_type] if document_type else None
            documents = await self.rag_retriever.retrieve(
                query, 
                top_k, 
                knowledge_base_id=knowledge_base_id,
                doc_types=doc_types_list
            )

            if not documents:
                return {
                    "success": True,
                    "answer": "未找到相关文档",
                    "documents": [],
                    "metadata": {"retrieved_count": 0}
                }

            # 如果不需要LLM，直接返回文档
            if not use_llm:
                return {
                    "success": True,
                    "answer": "",
                    "documents": documents,
                    "metadata": {"retrieved_count": len(documents)}
                }

            # 使用LLM生成答案
            answer = await self._generate_answer(query, documents)

            _log_rag_query(query, documents, answer)

            return {
                'success': True,
                'answer': answer,
                'documents': documents,
                'metadata': {
                    'retrieved_count': len(documents),
                    'query_length': len(query),
                    'sources': [
                        {
                            'title': d.get('metadata', {}).get('title', ''),
                            'doc_type': d.get('metadata', {}).get('doc_type', ''),
                            'score': d.get('combined_score', d.get('distance', 0.0)),
                        }
                        for d in documents
                    ],
                },
            }

        except Exception as e:
            logger.error(f"Failed to query knowledge base: {e}")
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": str(e)
            }
    
    async def _generate_answer(
        self,
        query: str,
        documents: List[Dict[str, Any]],
    ) -> str:
        """
        Build context from RAG results and generate answer via LLM.

        Context injection structure:
        - Each chunk: [标题] 内容片段
        - Truncate by RRF score if over limit
        - Source citations appended at end
        """
        context_parts: List[str] = []
        sources: List[str] = []

        for i, doc in enumerate(documents[:RAG_CONTEXT_LIMIT], 1):
            content = doc.get('document', '')
            metadata = doc.get('metadata', {})
            title = metadata.get('title', '未命名文档')
            doc_type = metadata.get('doc_type', '')
            rrf_score = doc.get('combined_score', doc.get('distance', 0.0))

            label = f'{title} ({doc_type})'
            context_parts.append(f'【{i}】{label}')
            context_parts.append(content)
            context_parts.append('')

            sources.append(f'[{i}] {label}')

        source_text = '\n'.join(sources)
        context_text = '\n'.join(context_parts)

        prompt = f"""请基于以下参考文档回答用户问题。

参考文档（按相关性排序，越靠前越相关）：
{context_text}

用户问题：{query}

要求：
- 优先引用靠前的文档内容
- 如果文档中没有相关信息，请直接说明，不要编造
- 回答末尾标注引用来源"""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_message='你是一个测试领域知识助手，基于提供的文档回答。请准确、客观。',
            )

            return response
        except Exception as e:
            logger.error(f'Failed to generate answer: {e}')
            return '生成答案时出错，请查看检索到的文档。'
    
    async def get_best_practices(
        self,
        topic: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        获取测试最佳实践

        Args:
            topic: 主题（如 "API testing", "UI testing"）
            top_k: 返回结果数量

        Returns:
            最佳实践结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": "Knowledge retriever not available"
            }
        query = f"best practices for {topic} testing"
        return await self.query(
            query=query,
            top_k=top_k,
            document_type="best_practice"
        )
    
    async def get_code_examples(
        self,
        description: str,
        language: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        获取代码示例

        Args:
            description: 代码描述
            language: 编程语言
            top_k: 返回结果数量

        Returns:
            代码示例结果
        """
        query = f"code example for {description}"

        if not self.rag_retriever:
            return {
                "success": False,
                "examples": [],
                "error": "Knowledge retriever not available"
            }

        try:
            documents = await self.rag_retriever.retrieve_code_examples(query, language, top_k)

            return {
                "success": True,
                "examples": documents,
                "metadata": {"retrieved_count": len(documents)}
            }

        except Exception as e:
            logger.error(f"Failed to get code examples: {e}")
            return {
                "success": False,
                "examples": [],
                "error": str(e)
            }
    
    async def get_test_patterns(
        self,
        scenario: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        获取测试模式

        Args:
            scenario: 测试场景
            top_k: 返回结果数量

        Returns:
            测试模式结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": "Knowledge retriever not available"
            }
        query = f"test patterns for {scenario}"
        return await self.query(
            query=query,
            top_k=top_k,
            document_type="test_pattern"
        )


def _log_rag_query(
    query: str,
    documents: List[Dict[str, Any]],
    answer: str,
) -> None:
    """
    Log every RAG query → context → answer for traceability.

    This is the only place we can track exactly what was sent to the LLM.
    """
    chunks_log = []
    for i, doc in enumerate(documents[:RAG_CONTEXT_LIMIT], 1):
        metadata = doc.get('metadata', {})
        chunks_log.append({
            'rank': i,
            'title': metadata.get('title', ''),
            'doc_type': metadata.get('doc_type', ''),
            'score': doc.get('combined_score', doc.get('distance', 0.0)),
            'content_preview': (doc.get('document', '') or '')[:120],
        })

    log_entry = {
        'event': 'rag_query',
        'timestamp': datetime.utcnow().isoformat(),
        'query': query,
        'chunk_count': len(chunks_log),
        'chunks': chunks_log,
        'answer_preview': answer[:300] if answer else '',
    }

    logger.info(json.dumps(log_entry, ensure_ascii=False))


