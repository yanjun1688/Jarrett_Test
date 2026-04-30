"""
BM25 Index - Whoosh-based full-text search index.

Provides add/search/delete operations aligned with ChromaDB chunk IDs.
Chinese tokenizer using jieba.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import jieba
from whoosh.analysis import Tokenizer, Token
from whoosh.fields import ID, KEYWORD, NUMERIC, TEXT, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser

from core.config import settings


class ChineseTokenizer(Tokenizer):
    """Whoosh tokenizer using jieba for Chinese text segmentation."""

    def __call__(self, text: str, **kwargs: Any) -> Any:
        for word in jieba.cut(text):
            if word.strip():
                yield Token(original=text, text=word, pos=0, startchar=0, endchar=0)
            else:
                # Preserve single English characters for API keywords
                if any(c.isascii() for c in word):
                    yield Token(original=text, text=word, pos=0, startchar=0, endchar=0)


def create_chinese_analyzer() -> ChineseTokenizer:
    """Create a Chinese tokenizer for Whoosh."""
    return ChineseTokenizer()


class BM25Index:
    """
    Whoosh-based BM25 index for full-text search.

    Thread-safe singleton per process. Index files stored on disk.
    Aligned with ChromaDB chunk IDs for RRF fusion.
    """

    _instance: Optional[BM25Index] = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls) -> BM25Index:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, '_initialized') and self._initialized:
            return
        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return
            self._index_path = self._resolve_path()
            self._schema = Schema(
                chunk_id=ID(unique=True, stored=True),
                content=TEXT(stored=True, analyzer=create_chinese_analyzer()),
                doc_type=KEYWORD(stored=True),
                title=TEXT(stored=True, analyzer=create_chinese_analyzer()),
                knowledge_base_id=NUMERIC(stored=True),
                project_id=NUMERIC(stored=True),
            )
            self._ensure_index()
            self._initialized = True

    @staticmethod
    def _resolve_path() -> str:
        path = getattr(settings, 'bm25_index_path', './data/bm25_index')
        if not os.path.isabs(path):
            project_root = Path(__file__).parent.parent.parent.parent
            path = str(project_root / path)
        return path

    def _ensure_index(self) -> None:
        os.makedirs(self._index_path, exist_ok=True)
        seg_file = os.path.join(self._index_path, 'SEGMENTS')
        if not os.path.exists(seg_file):
            create_in(self._index_path, self._schema)
            logger.info(f'[BM25] Index created at {self._index_path}')

    @property
    def _ix(self) -> Any:
        if not hasattr(self._local, 'ix') or self._local.ix is None:
            self._local.ix = open_dir(self._index_path, schema=self._schema)
        return self._local.ix

    def add_document(
        self,
        chunk_id: str,
        content: str,
        doc_type: str = '',
        title: str = '',
        knowledge_base_id: int = 0,
        project_id: int = 0,
    ) -> None:
        """Add or update a single chunk document."""
        writer = self._ix.writer()
        writer.update_document(
            chunk_id=chunk_id,
            content=content,
            doc_type=doc_type,
            title=title,
            knowledge_base_id=knowledge_base_id,
            project_id=project_id,
        )
        writer.commit()
        logger.debug(f'[BM25] Added/updated: {chunk_id}')

    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> None:
        """Batch add multiple chunk documents."""
        writer = self._ix.writer()
        for doc in documents:
            writer.update_document(
                chunk_id=doc['chunk_id'],
                content=doc['content'],
                doc_type=doc.get('doc_type', ''),
                title=doc.get('title', ''),
                knowledge_base_id=doc.get('knowledge_base_id', 0),
                project_id=doc.get('project_id', 0),
            )
        writer.commit()
        logger.debug(f'[BM25] Batch added {len(documents)} documents')

    def search(
        self,
        query: str,
        top_k: int = 50,
        doc_type: Optional[str] = None,
        doc_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        BM25 full-text search.

        Args:
            query: Search query
            top_k: Max results
            doc_type: Single doc type filter (legacy)
            doc_types: Multiple doc types filter

        Returns:
            List of {chunk_id, score, content, doc_type, title}
        """
        with self._ix.searcher() as searcher:
            parser = MultifieldParser(['content', 'title'], schema=self._schema)
            parsed = parser.parse(query)

            results = searcher.search(parsed, limit=top_k)

            if doc_type:
                results = [r for r in results if r['doc_type'] == doc_type]
            elif doc_types:
                results = [r for r in results if r['doc_type'] in doc_types]

            return [
                {
                    'chunk_id': r['chunk_id'],
                    'score': r.score,
                    'content': r['content'],
                    'doc_type': r['doc_type'],
                    'title': r['title'],
                }
                for r in results
            ]

    def delete_by_prefix(self, prefix: str) -> int:
        """
        Delete all chunks with chunk_id starting with prefix.

        Args:
            prefix: e.g. 'source_123_'

        Returns:
            Number of deleted documents
        """
        from whoosh.query import Prefix

        writer = self._ix.writer()
        count = writer.delete_by_query(Prefix('chunk_id', prefix))
        writer.commit()
        logger.info(f'[BM25] Deleted {count} docs with prefix {prefix}')
        return count

    def delete_by_id(self, chunk_id: str) -> None:
        """Delete a single chunk by exact chunk_id."""
        writer = self._ix.writer()
        writer.delete_by_term('chunk_id', chunk_id)
        writer.commit()

    def count(self) -> int:
        """Total documents in index."""
        with self._ix.searcher() as searcher:
            return searcher.doc_count()

    def rebuild_from_scratch(self) -> None:
        """Delete and recreate the entire index."""
        import shutil

        shutil.rmtree(self._index_path, ignore_errors=True)
        self._ensure_index()
        logger.info('[BM25] Index rebuilt from scratch')
