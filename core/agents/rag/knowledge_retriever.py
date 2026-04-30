"""
Knowledge Retriever - Core retrieval component

Combines EmbeddingService + ChromaVectorStore + BM25Index for hybrid search.
Implements RRF fusion for combining vector and BM25 results.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from core.agents.rag.embedding_service import EmbeddingService
from core.agents.rag.vector_store import ChromaVectorStore
from core.config import settings


class KnowledgeRetriever:
    """
    Knowledge Retriever with hybrid search (Vector + BM25 + RRF).
    """

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.vector_store = ChromaVectorStore()
        self._bm25: Any = None

    @property
    def bm25(self) -> Any:
        if self._bm25 is None:
            from core.agents.rag.bm25_index import BM25Index
            self._bm25 = BM25Index()
        return self._bm25

    def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        doc_id: str,
    ) -> None:
        """Add a single document"""
        if 'chroma_id_prefix' not in metadata:
            metadata['chroma_id_prefix'] = doc_id.rsplit('_chunk_', 1)[0] + '_' if '_chunk_' in doc_id else doc_id
        embedding = self.embedding_service.embed_query(content)
        self.vector_store.add_documents(
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )

    def add_documents_batch(
        self,
        contents: List[str],
        metadatas: List[Dict[str, Any]],
        doc_ids: List[str],
    ) -> None:
        """Add multiple documents in batch"""
        for i, (doc_id, m) in enumerate(zip(doc_ids, metadatas)):
            if 'chroma_id_prefix' not in m:
                m['chroma_id_prefix'] = doc_id.rsplit('_chunk_', 1)[0] + '_' if '_chunk_' in doc_id else doc_id
        embeddings = self.embedding_service.embed_texts(contents)
        self.vector_store.add_documents(
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=doc_ids,
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_types: Optional[List[str]] = None,
        project_id: Optional[int] = None,
        knowledge_base_id: Optional[int] = None,
        boost_project: bool = False,
        hybrid_search: bool = True,
        where_extra: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: Vector + BM25 + RRF fusion.

        Args:
            query: Search query
            top_k: Number of results to return
            doc_types: Filter by document types
            project_id: Filter by project
            knowledge_base_id: Filter by knowledge base
            boost_project: Prioritize results from specified project
            hybrid_search: If True, use BM25 + Vector + RRF
            where_extra: Additional ChromaDB where filters
        """
        if not hybrid_search or not settings.bm25_enabled:
            return self._vector_only_search(
                query, top_k, doc_types, project_id,
                knowledge_base_id, boost_project, where_extra,
            )

        # 1. Vector search
        query_embedding = self.embedding_service.embed_query(query)
        where = self._build_where_clause(doc_types, project_id, knowledge_base_id)
        if where_extra:
            where = {'$and': [where, where_extra]} if where else where_extra

        vector_n = settings.bm25_top_k
        vector_raw = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=vector_n,
            where=where if where else None,
        )

        # 2. BM25 search
        try:
            bm25_raw = self.bm25.search(query, top_k=settings.bm25_top_k, doc_types=doc_types)
        except Exception:
            bm25_raw = []

        # 3. RRF fusion
        k = settings.rrf_k
        rrf_scores: Dict[str, float] = defaultdict(float)

        # Vector results by rank
        for rank, chunk_id in enumerate(vector_raw.get('ids', [[]])[0]):
            rrf_scores[chunk_id] += 1.0 / (k + rank)

        # BM25 results by rank
        for rank, item in enumerate(bm25_raw):
            rrf_scores[item['chunk_id']] += 1.0 / (k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: -x[1])

        # 4. Build final results
        vector_docs = {
            doc_id: {
                'content': vector_raw['documents'][0][i] if vector_raw.get('documents') else None,
                'metadata': vector_raw['metadatas'][0][i] if vector_raw.get('metadatas') else {},
                'distance': vector_raw['distances'][0][i] if vector_raw.get('distances') else None,
            }
            for i, doc_id in enumerate(vector_raw.get('ids', [[]])[0])
        }

        bm25_docs = {
            item['chunk_id']: {
                'content': item.get('content', ''),
                'metadata': {
                    'doc_type': item.get('doc_type', ''),
                    'title': item.get('title', ''),
                },
            }
            for item in bm25_raw
        }

        formatted: List[Dict[str, Any]] = []
        for chunk_id, score in ranked[:top_k]:
            entry = vector_docs.get(chunk_id) or bm25_docs.get(chunk_id)
            if entry:
                formatted.append({
                    'id': chunk_id,
                    'content': entry.get('content', ''),
                    'metadata': entry.get('metadata', {}),
                    'distance': entry.get('distance'),
                    'rrf_score': score,
                })

        if boost_project and project_id:
            formatted = self._boost_project_results(formatted, project_id, top_k)

        return formatted[:top_k]

    def _vector_only_search(
        self,
        query: str,
        top_k: int,
        doc_types: Optional[List[str]],
        project_id: Optional[int],
        knowledge_base_id: Optional[int],
        boost_project: bool,
        where_extra: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Fallback: vector-only search with keyword boost."""
        query_embedding = self.embedding_service.embed_query(query)

        where = self._build_where_clause(doc_types, project_id, knowledge_base_id)
        if where_extra:
            where = {'$and': [where, where_extra]} if where else where_extra

        n_results = top_k * 3
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where if where else None,
        )

        formatted = self._format_results(results)
        formatted = self._apply_keyword_boost(formatted, query, top_k * 2)

        if boost_project and project_id:
            formatted = self._boost_project_results(formatted, project_id, top_k)

        return formatted[:top_k]

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Pure semantic search (backward compatibility)."""
        return self.search(query, top_k=top_k)

    def search_tests(
        self,
        query: str,
        source_types: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Test case search (backward compatibility)."""
        return self.search(query, top_k=top_k, doc_types=source_types)

    def search_documents(
        self,
        query: str,
        document_types: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Document search (backward compatibility)."""
        return self.search(query, top_k=top_k, doc_types=document_types)

    def delete_document(self, doc_id: str) -> None:
        """Delete a single document."""
        self.vector_store.delete(ids=[doc_id])

    def delete_document_chunks(self, id_prefix: str) -> int:
        """
        Delete all chunks of a document.

        Args:
            id_prefix: Document ID prefix, e.g. "source_123_"

        Returns:
            Number of deleted chunks
        """
        # Delete from BM25
        try:
            self.bm25.delete_by_prefix(id_prefix)
        except Exception:
            pass
        # Delete from ChromaDB
        return self.vector_store.delete_by_prefix(id_prefix)

    def _build_where_clause(
        self,
        doc_types: Optional[List[str]],
        project_id: Optional[int],
        knowledge_base_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build ChromaDB where clause from filters."""
        conditions: List[Dict[str, Any]] = []

        if doc_types and len(doc_types) == 1:
            conditions.append({'doc_type': doc_types[0]})
        elif doc_types and len(doc_types) > 1:
            conditions.append({'doc_type': {'$in': doc_types}})

        if project_id is not None:
            conditions.append({'project_id': project_id})

        if knowledge_base_id is not None:
            conditions.append({'knowledge_base_id': knowledge_base_id})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {'$and': conditions}

    # ── legacy keyword boost (fallback when BM25 disabled) ──

    DOC_TYPE_KEYWORDS: Dict[str, List[str]] = {
        'prd': ['PRD', '需求', '产品需求', '功能需求', '产品文档', '需求文档'],
        'api_doc': ['API', '接口', '接口文档', 'yaml', 'swagger', 'openapi', 'API文档'],
        'best_practice': ['最佳实践', '最佳', '实践', '规范', '指南'],
        'code_example': ['代码示例', '示例代码', '代码', '示例', 'example', 'code'],
        'test_pattern': ['测试模式', '模式', 'pattern', '测试策略'],
    }

    def _extract_query_keywords(self, query: str) -> List[str]:
        keywords = []
        api_patterns = re.findall(r'API[_\-\w]*', query, re.IGNORECASE)
        keywords.extend(api_patterns)
        words = re.findall(r'\b[A-Z_]{2,}\b', query)
        keywords.extend(words)
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', query)
        keywords.extend(chinese_chars)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
        keywords.extend(words[:5])
        unique = []
        seen = set()
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and len(kw) >= 2:
                seen.add(kw_lower)
                unique.append(kw)
        return unique

    def _apply_keyword_boost(
        self,
        results: List[Dict[str, Any]],
        query: str,
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """Legacy keyword boost (used only when BM25 is disabled)."""
        query_keywords = self._extract_query_keywords(query)
        if not query_keywords:
            return results

        query_lower = query.lower().strip()

        scored_results = []
        for r in results:
            metadata = r.get('metadata', {})
            doc_keywords_str = metadata.get('keywords', '')
            doc_keywords = doc_keywords_str.split(',') if doc_keywords_str else []
            title = metadata.get('title', '')
            title_lower = title.lower().strip()
            content = r.get('content', '') or ''
            doc_type = metadata.get('doc_type', '')

            keyword_score = 0.0

            if query_lower == title_lower or query_lower in title_lower:
                keyword_score += 5.0

            for kw in query_keywords:
                kw_lower = kw.lower()
                for doc_kw in doc_keywords:
                    if kw_lower in doc_kw.lower():
                        keyword_score += 1.0
                if kw_lower in title.lower():
                    keyword_score += 0.5
                if kw_lower in content.lower():
                    keyword_score += 0.5
                if doc_type in self.DOC_TYPE_KEYWORDS:
                    type_keywords = self.DOC_TYPE_KEYWORDS[doc_type]
                    type_keywords_lower = [tk.lower() for tk in type_keywords]
                    if kw_lower in type_keywords_lower:
                        keyword_score += 2.0

            distance = r.get('distance') or 1.0
            vector_score = 1.0 / (1.0 + distance)
            combined_score = vector_score + (keyword_score * 0.3)

            if combined_score > 0:
                scored_results.append({
                    **r,
                    'keyword_score': keyword_score,
                    'combined_score': combined_score,
                })

        scored_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        return scored_results[:target_count]

    def _boost_project_results(
        self,
        results: List[Dict[str, Any]],
        project_id: int,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Sort results so that documents from the specified project appear first."""
        project_results = []
        other_results = []
        for r in results:
            if r.get('metadata', {}).get('project_id') == project_id:
                project_results.append(r)
            else:
                other_results.append(r)
        return (project_results + other_results)[:top_k]

    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format query results, fallback to MySQL for missing metadata."""
        formatted: List[Dict[str, Any]] = []
        if not results['ids'] or not results['ids'][0]:
            return formatted

        kb_ids_to_fetch: List[int] = []
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            kb_name = metadata.get('knowledge_base_name')
            kb_id = metadata.get('knowledge_base_id')
            if (not kb_name or kb_name == 'None') and kb_id:
                kb_ids_to_fetch.append(kb_id)

        kb_names_cache: Dict[int, str] = {}
        if kb_ids_to_fetch:
            try:
                from core.models.knowledge import KnowledgeBase
                kb_objects = KnowledgeBase.objects.filter(id__in=kb_ids_to_fetch)
                kb_names_cache = {kb.id: kb.name for kb in kb_objects}
            except Exception:
                pass

        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            kb_name = metadata.get('knowledge_base_name')
            kb_id = metadata.get('knowledge_base_id')
            if (not kb_name or kb_name == 'None') and kb_id and kb_id in kb_names_cache:
                metadata['knowledge_base_name'] = kb_names_cache[kb_id]

            formatted.append({
                'id': doc_id,
                'content': results['documents'][0][i] if results['documents'] else None,
                'metadata': metadata,
                'distance': results['distances'][0][i] if results['distances'] else None,
            })
        return formatted
