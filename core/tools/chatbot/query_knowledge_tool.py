"""
Query Knowledge Tool
查询知识库。支持三种模式：list（列出文档）、search（语义搜索）、get（查看全文）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

from core.tools.base_tool import BaseTool, ToolResult


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
        err = self.validate_required(kwargs, "mode")
        if err:
            return err

        mode = self.get_param(kwargs, "mode")
        knowledge_base_id = self.get_param(kwargs, "knowledge_base_id")
        query = self.get_param(kwargs, "query")
        document_id = self.get_param(kwargs, "document_id")
        doc_type = self.get_param(kwargs, "doc_type")
        project_id = self.get_param(kwargs, "project_id")

        self.logger.info(
            f'[QueryKnowledge] mode={mode}, kb_id={knowledge_base_id}, '
            f'query={query!r}, doc_id={document_id}'
        )

        if mode in ('list', 'search') and not knowledge_base_id and query:
            extracted = self._extract_knowledge_base_from_query(query)
            if extracted:
                knowledge_base_id = extracted

        if mode == 'list':
            return await self._handle_list(knowledge_base_id)
        elif mode == 'search':
            return await self._handle_search(query, knowledge_base_id, doc_type, project_id)
        elif mode == 'get':
            return await self._handle_get(document_id)
        else:
            return ToolResult(success=False, data={}, error=f'无效的 mode: {mode}')

    async def _handle_list(self, knowledge_base_id: Optional[int]) -> ToolResult:
        if not knowledge_base_id:
            return ToolResult(success=False, data={}, error='list 模式需要 knowledge_base_id')

        from core.models.knowledge import KnowledgeDocument

        docs = await self.run_query(
            lambda: list(
                KnowledgeDocument.objects.filter(
                    knowledge_base_id=knowledge_base_id,
                    chunk_index=-1,
                ).values('id', 'document_type', 'content', 'file_path', 'metadata')
                .order_by('-created_at')
            ),
            "查询文档列表失败",
        )

        if not docs:
            return ToolResult(
                success=True,
                data={'documents': [], 'message': f'知识库 (ID={knowledge_base_id}) 中没有文档'},
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

        return ToolResult(success=True, data={'documents': documents, 'message': answer, 'answer': answer})

    async def _handle_search(
        self,
        query: Optional[str],
        knowledge_base_id: Optional[int],
        doc_type: Optional[str],
        project_id: Optional[int] = None,
    ) -> ToolResult:
        if not query:
            return ToolResult(success=False, data={}, error='search 模式需要 query 参数')

        from core.agents.rag.knowledge_retriever import KnowledgeRetriever

        retriever = KnowledgeRetriever()
        doc_types_list = [doc_type] if doc_type else None

        results = await self.run_query(
            lambda: retriever.search(
                query, top_k=5, doc_types=doc_types_list,
                knowledge_base_id=knowledge_base_id, project_id=project_id, hybrid_search=True,
            ),
            "搜索失败",
        )

        if not results:
            return ToolResult(success=True, data={'documents': [], 'message': '未找到匹配的文档', 'answer': '未找到匹配的文档'})

        documents = []
        for r in results:
            metadata = r.get('metadata', {})
            content = r.get('content', '')
            documents.append({
                'id': metadata.get('knowledge_document_id'),
                'title': metadata.get('title', '未命名文档'),
                'doc_type': metadata.get('doc_type'),
                'knowledge_base_name': metadata.get('knowledge_base_name'),
                'score': r.get('combined_score', r.get('score', 0.0)),
                'snippet': (content or '')[:500],
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

        return ToolResult(success=True, data={'documents': documents, 'message': answer, 'answer': answer})

    async def _handle_get(self, document_id: Optional[int]) -> ToolResult:
        if not document_id:
            return ToolResult(success=False, data={}, error='get 模式需要 document_id')

        from core.models.knowledge import KnowledgeDocument

        def _get() -> Optional[Dict[str, Any]]:
            try:
                doc: Any = KnowledgeDocument.objects.get(id=document_id)
                content = doc.content or ''
                if not content and doc.file_path:
                    try:
                        with open(doc.file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except Exception as e:
                        self.logger.warning(f'[QueryKnowledge] 读取文件失败: {e}')
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

        doc = await self.run_query(_get, "获取文档失败")

        if not doc:
            return ToolResult(success=True, data={'document': None, 'message': f'文档 (ID={document_id}) 不存在'})

        answer = f'**{doc["title"]}**\n- 类型: {doc["doc_type"]}\n- 文档ID: {doc["id"]}\n\n{doc["content"]}'

        return ToolResult(success=True, data={'document': doc, 'message': answer, 'answer': answer})

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
                self.logger.info(f'[QueryKnowledge] 识别知识库: {kb_name!r} -> kb_id={kb.id}')
                return kb.id  # type: ignore[no-any-return]
        except Exception as e:
            self.logger.warning(f'[QueryKnowledge] 查询知识库失败: {e}')

        return None
