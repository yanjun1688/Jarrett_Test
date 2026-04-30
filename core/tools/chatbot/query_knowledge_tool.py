"""
Query Knowledge Tool
查询知识库。支持三种模式：list（列出文档）、search（语义搜索）、get（查看全文）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import re

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class QueryKnowledgeTool(BaseTool):
    """查询知识库"""

    def __init__(self, knowledge_rag_agent: Any = None) -> None:
        super().__init__(
            name='query_knowledge',
            description='查询知识库。支持三种模式：\n\n'
                       '1. list — 列出知识库中的文档标题和ID\n'
                       '2. search — 语义搜索文档内容，返回标题+摘要片段\n'
                       '3. get — 按文档ID查看全文\n\n'
                       '规则：\n'
                       '- 用户说"xx知识库有哪些文档" → 调 list(knowledge_base_id=X, query="xx知识库")\n'
                       '  系统会自动从 query 中解析知识库名称并匹配 ID\n'
                       '- 用户说"搜索xxx内容" → 调 search(query="xxx")\n'
                       '- 用户说"看某个文档的全文/具体内容" → 调 get(document_id=X)\n'
                       '- list 和 search 的返回内容中会包含文档列表，LLM 直接呈现给用户选择',
            version='2.0.0',
        )
        self._knowledge_rag_agent = knowledge_rag_agent

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            'mode': {
                'type': 'string',
                'enum': ['list', 'search', 'get'],
                'description': '操作模式：list-列出文档标题, search-语义搜索内容, get-查看全文',
            },
            'knowledge_base_id': {
                'type': 'integer',
                'description': '知识库ID（list 模式必填，search 模式可选过滤）',
            },
            'query': {
                'type': 'string',
                'description': '搜索关键词（search 模式必填）',
            },
            'document_id': {
                'type': 'integer',
                'description': '文档ID（get 模式必填，从 list 结果中获取）',
            },
            'doc_type': {
                'type': 'string',
                'enum': ['prd', 'api_doc', 'best_practice', 'code_example', 'test_pattern'],
                'description': '文档类型过滤（仅 search 模式可用）',
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ['mode']

    async def execute(self, **kwargs: Any) -> ToolResult:
        mode = kwargs.get('mode')
        knowledge_base_id = kwargs.get('knowledge_base_id')
        query = kwargs.get('query')
        document_id = kwargs.get('document_id')
        doc_type = kwargs.get('doc_type')

        logger.info(f'[QueryKnowledge] mode={mode}, kb_id={knowledge_base_id}, '
                     f'query={query!r}, doc_id={document_id}, doc_type={doc_type}')

        # list 和 search 模式：从 query 中自动识别知识库名称
        if mode in ('list', 'search') and not knowledge_base_id and query:
            extracted_kb_id = self._extract_knowledge_base_from_query(query)
            if extracted_kb_id:
                knowledge_base_id = extracted_kb_id
                logger.info(f'[QueryKnowledge] 从 query 识别知识库: kb_id={extracted_kb_id}')

        if mode == 'list':
            return await self._handle_list(knowledge_base_id)
        elif mode == 'search':
            return await self._handle_search(query, knowledge_base_id, doc_type)
        elif mode == 'get':
            return await self._handle_get(document_id)
        else:
            return ToolResult(
                success=False,
                data={},
                error=f'无效的 mode: {mode}，可选值: list, search, get',
            )

    async def _handle_list(self, knowledge_base_id: Optional[int]) -> ToolResult:
        if not knowledge_base_id:
            return ToolResult(
                success=False,
                data={},
                error='list 模式需要 knowledge_base_id 参数',
            )

        try:
            from core.models.knowledge import KnowledgeDocument

            def _query() -> List[Dict[str, Any]]:
                return list(
                    KnowledgeDocument.objects.filter(  # type: ignore[arg-type]
                        knowledge_base_id=knowledge_base_id,
                        chunk_index=-1,  # root documents only
                    ).values('id', 'document_type', 'content', 'file_path', 'metadata').order_by('-created_at')
                )

            docs = await sync_to_async(_query)()
            logger.info(f'[QueryKnowledge] list mode: 查到 {len(docs)} 个文档')

            if not docs:
                return ToolResult(
                    success=True,
                    data={
                        'documents': [],
                        'message': f'知识库 (ID={knowledge_base_id}) 中没有文档',
                    },
                )

            documents = [
                {
                    'id': d['id'],
                    'title': (d.get('metadata') or {}).get('title', d['file_path'].split('/')[-1] if d['file_path'] else f'文档_{d["id"]}'),
                    'doc_type': d['document_type'],
                    'description': ((d.get('metadata') or {}).get('description', ''))[:200],
                }
                for d in docs
            ]

            titles = '\n'.join(f'  {d["id"]}. [{d["doc_type"]}] {d["title"]}' for d in documents)
            answer = f'知识库 (ID={knowledge_base_id}) 中有 {len(documents)} 个文档：\n{titles}\n\n如需查看详情，请使用 get(document_id=xxx) 获取全文。'

            return ToolResult(
                success=True,
                data={
                    'documents': documents,
                    'message': answer,
                    'answer': answer,
                },
                metadata={
                    'mode': 'list',
                    'knowledge_base_id': knowledge_base_id,
                    'documents_found': len(documents),
                },
            )

        except Exception as e:
            logger.error(f'[QueryKnowledge] list 失败: {e}')
            return ToolResult(
                success=False,
                data={},
                error=f'查询文档列表失败: {e}',
            )

    async def _handle_search(
        self,
        query: Optional[str],
        knowledge_base_id: Optional[int],
        doc_type: Optional[str],
    ) -> ToolResult:
        if not query:
            return ToolResult(
                success=False,
                data={},
                error='search 模式需要 query 参数',
            )

        try:
            from core.agents.rag.knowledge_retriever import KnowledgeRetriever

            retriever = KnowledgeRetriever()
            doc_types_list = [doc_type] if doc_type else None

            results = await sync_to_async(retriever.search)(
                query,
                top_k=5,
                doc_types=doc_types_list,
                knowledge_base_id=knowledge_base_id,
                hybrid_search=True,
            )
            logger.info(f'[QueryKnowledge] search 结果: {len(results)} 条')

            if not results:
                return ToolResult(
                    success=True,
                    data={
                        'documents': [],
                        'message': '未找到匹配的文档',
                        'answer': '未找到匹配的文档',
                    },
                )

            documents = []
            for r in results:
                metadata = r.get('metadata', {})
                content = r.get('content', '')
                content_snippet = (content or '')[:500]
                documents.append({
                    'id': metadata.get('knowledge_document_id'),
                    'title': metadata.get('title', '未命名文档'),
                    'doc_type': metadata.get('doc_type'),
                    'knowledge_base_name': metadata.get('knowledge_base_name'),
                    'score': r.get('combined_score', r.get('score', 0.0)),
                    'snippet': content_snippet,
                })

            answer_parts = []
            for i, doc in enumerate(documents, 1):
                kb = doc.get('knowledge_base_name', '')
                kb_str = f' [{kb}]' if kb else ''
                answer_parts.append(
                    f'**[{i}] {doc["title"]}**{kb_str}\n'
                    f'- 相关度: {doc["score"]:.2f}\n'
                    f'- 文档ID: {doc["id"]}\n'
                    f'- 摘要:\n{doc["snippet"]}'
                )
            answer = '\n\n---\n\n'.join(answer_parts)

            return ToolResult(
                success=True,
                data={
                    'documents': documents,
                    'message': answer,
                    'answer': answer,
                },
                metadata={
                    'mode': 'search',
                    'query': query,
                    'documents_found': len(documents),
                },
            )

        except Exception as e:
            logger.error(f'[QueryKnowledge] search 失败: {e}')
            return ToolResult(
                success=False,
                data={},
                error=f'搜索失败: {e}',
            )

    async def _handle_get(self, document_id: Optional[int]) -> ToolResult:
        if not document_id:
            return ToolResult(
                success=False,
                data={},
                error='get 模式需要 document_id 参数',
            )

        try:
            from core.models.knowledge import KnowledgeDocument

            def _get() -> Optional[Dict[str, Any]]:
                try:
                    doc = KnowledgeDocument.objects.get(id=document_id)
                    content = doc.content or ''
                    if not content and doc.file_path:
                        try:
                            with open(doc.file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except Exception as e:
                            logger.warning(f'[QueryKnowledge] 读取文件失败: {e}')
                    metadata = doc.metadata or {}
                    return {
                        'id': doc.id,
                        'title': metadata.get('title', doc.file_path.split('/')[-1] if doc.file_path else f'文档_{doc.id}'),
                        'doc_type': doc.document_type,
                        'content': content,
                        'description': metadata.get('description', ''),
                        'knowledge_base_id': doc.knowledge_base_id,
                    }
                except KnowledgeDocument.DoesNotExist:
                    return None

            doc = await sync_to_async(_get)()

            if not doc:
                return ToolResult(
                    success=True,
                    data={
                        'document': None,
                        'message': f'文档 (ID={document_id}) 不存在',
                    },
                )

            logger.info(f'[QueryKnowledge] get mode: 文档 {doc["title"]}, 内容长度 {len(doc["content"])}')

            answer = (
                f'**{doc["title"]}**\n'
                f'- 类型: {doc["doc_type"]}\n'
                f'- 文档ID: {doc["id"]}\n\n'
                f'{doc["content"]}'
            )

            return ToolResult(
                success=True,
                data={
                    'document': doc,
                    'message': answer,
                    'answer': answer,
                },
                metadata={
                    'mode': 'get',
                    'document_id': document_id,
                    'document_title': doc['title'],
                    'content_length': len(doc['content']),
                },
            )

        except Exception as e:
            logger.error(f'[QueryKnowledge] get 失败: {e}')
            return ToolResult(
                success=False,
                data={},
                error=f'获取文档失败: {e}',
            )

    def _extract_knowledge_base_from_query(self, query: str) -> Optional[int]:
        """从 query 中识别知识库名称并返回 ID"""
        from core.models.knowledge import KnowledgeBase

        patterns = [
            r'(.+?)知识库(?:的|里|中)',
            r'在(.+?)知识库(?:中|里)',
            r'查询(.+?)知识库',
        ]

        kb_name = None
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                kb_name = match.group(1).strip()
                break

        if not kb_name:
            return None

        try:
            kb = KnowledgeBase.objects.filter(name__icontains=kb_name).first()
            if kb:
                logger.info(f'[QueryKnowledge] 识别知识库: {kb_name!r} -> kb_id={kb.id}')
                return kb.id
        except Exception as e:
            logger.warning(f'[QueryKnowledge] 查询知识库失败: {e}')

        return None
