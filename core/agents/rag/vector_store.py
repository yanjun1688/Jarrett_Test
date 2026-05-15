"""
ChromaDB Vector Store - Thread-safe global vector storage

Uses ChromaDB PersistentClient for persistent storage.
Single global collection: kb_knowledge (configured in settings)
"""
from __future__ import annotations

import logging
import os
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import chromadb
from chromadb.config import Settings

from core.config import settings

if TYPE_CHECKING:
    from chromadb import PersistentClient

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client_instance: Any = None


def _get_absolute_chromadb_path() -> str:
    """Get absolute path for ChromaDB storage"""
    path = settings.chromadb_path
    if not os.path.isabs(path):
        project_root = Path(__file__).parent.parent.parent.parent
        path = str(project_root / path)
    return path


def _get_global_client() -> Any:
    """Get or create the global ChromaDB PersistentClient singleton.

    Uses module-level singleton with double-checked locking.
    ChromaDB PersistentClient is thread-safe for reads; single client
    avoids SQLite lock contention from multiple connections.
    """
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                abs_path = _get_absolute_chromadb_path()
                logger.info(f'[ChromaDB] Initializing client with path: {abs_path}')
                logger.info(f'[ChromaDB] Path exists: {os.path.exists(abs_path)}')

                _client_instance = chromadb.PersistentClient(
                    path=abs_path,
                    settings=Settings(anonymized_telemetry=False),
                )

                collections = _client_instance.list_collections()
                logger.info(f'[ChromaDB] Available collections: {[c.name for c in collections]}')

    return _client_instance


class ChromaVectorStore:
    """
    ChromaDB Vector Store Wrapper

    Uses a global singleton PersistentClient with per-thread collection
    caching via threading.local().

    Supports multiple collections — each instance can target a different
    collection name.  The per-thread cache keys by collection_name so
    different instances in the same thread don't collide.
    """

    _local = threading.local()

    def __init__(self, collection_name: Optional[str] = None) -> None:
        self.collection_name = collection_name or settings.chromadb_collection_name

    @classmethod
    def get_client(cls) -> Any:
        """Get global ChromaDB PersistentClient singleton (thread-safe)."""
        return _get_global_client()

    @property
    def collection(self):
        """
        Get or create collection (thread-safe, cached per thread per name).

        Uses a dict keyed by collection_name to avoid cross-instance
        collisions when the same thread creates stores for different
        collections (e.g. kb_knowledge vs conversation_memory).
        """
        if not hasattr(self._local, '_collections'):
            self._local._collections = {}
        if self.collection_name not in self._local._collections:
            client = self.get_client()
            logger.info(f'[ChromaDB] Getting/creating collection: {self.collection_name}')
            try:
                self._local._collections[self.collection_name] = client.get_or_create_collection(
                    name=self.collection_name,
                )
                logger.info(f'[ChromaDB] Collection count: {self._local._collections[self.collection_name].count()}')
            except Exception as e:
                logger.warning(
                    f'[ChromaDB] get_or_create_collection failed: {e}, trying create_collection',
                )
                try:
                    self._local._collections[self.collection_name] = client.create_collection(
                        name=self.collection_name,
                    )
                    logger.info('[ChromaDB] Collection created successfully')
                except Exception as e2:
                    logger.error(f'[ChromaDB] create_collection also failed: {e2}')
                    raise
        return self._local._collections[self.collection_name]

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """Add documents to collection"""
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query similar documents"""
        try:
            logger.info(f'[ChromaDB] Query: n_results={n_results}, where={where}')
            logger.info(f'[ChromaDB] Embedding len: {len(query_embedding)}')

            col = self.collection
            logger.info(f'[ChromaDB] Collection obtained, count={col.count()}')

            result = col.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=['documents', 'metadatas', 'distances'],
            )
            logger.info(f"[ChromaDB] Query success, results: {len(result['ids'][0])}")
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f'[ChromaDB] Query failed: {e}')
            logger.error(f'[ChromaDB] Traceback: {traceback.format_exc()}')
            raise

    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        self.collection.delete(ids=ids)

    def delete_by_prefix(self, id_prefix: str) -> int:
        """
        Delete documents by chroma_id_prefix metadata field.

        Uses ChromaDB where filter on the ``chroma_id_prefix`` metadata key
        instead of pulling all documents, avoiding OOM on large datasets.

        Returns:
            Number of deleted documents
        """
        result = self.collection.get(where={'chroma_id_prefix': id_prefix})
        ids_to_delete = result['ids']
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def delete_by_metadata(self, where: Dict[str, Any]) -> int:
        """
        Delete documents by metadata filter.

        Args:
            where: Filter conditions, e.g. {"session_id": "abc-123", "user_id": "42"}

        Returns:
            Number of deleted documents
        """
        result = self.collection.get(where=where)
        ids_to_delete = result["ids"]
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def delete_collection(self) -> None:
        """Delete the entire collection"""
        self.get_client().delete_collection(name=self.collection_name)
        if hasattr(self._local, '_collections'):
            self._local._collections.pop(self.collection_name, None)

    def count(self) -> int:
        """Get document count"""
        return self.collection.count()  # type: ignore[no-any-return]
