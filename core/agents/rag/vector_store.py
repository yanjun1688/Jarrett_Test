"""
ChromaDB Vector Store - Thread-safe global vector storage

Uses ChromaDB PersistentClient for persistent storage.
Single global collection: kb_knowledge (configured in settings)
"""
# pyright: reportAttributeAccessIssue=false
import os
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings

from core.config import settings


def _get_absolute_chromadb_path() -> str:
    """Get absolute path for ChromaDB storage"""
    path = settings.chromadb_path
    if not os.path.isabs(path):
        project_root = Path(__file__).parent.parent.parent.parent
        path = str(project_root / path)
    return path


class ChromaVectorStore:
    """
    ChromaDB Vector Store Wrapper
    
    Uses PersistentClient for persistent storage.
    Single global collection for all projects.
    
    Thread safety: Uses threading.local() to isolate both client and collection 
    instances per thread. Each thread has its own client and collection objects,
    but they all point to the same underlying database.
    """
    
    _local = threading.local()
    
    def __init__(self):
        self.collection_name = settings.chromadb_collection_name
    
    @classmethod
    def get_client(cls) -> chromadb.PersistentClient:
        """
        Get ChromaDB client (thread-safe)
        
        threading.local() ensures each thread has its own client instance,
        different threads don't interfere with each other, no race conditions,
        no locks needed.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not hasattr(cls._local, 'client') or cls._local.client is None:
            abs_path = _get_absolute_chromadb_path()
            logger.info(f"[ChromaDB] Initializing client with path: {abs_path}")
            logger.info(f"[ChromaDB] Path exists: {os.path.exists(abs_path)}")
            
            cls._local.client = chromadb.PersistentClient(
                path=abs_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            collections = cls._local.client.list_collections()
            logger.info(f"[ChromaDB] Available collections: {[c.name for c in collections]}")
        
        return cls._local.client
    
    @property
    def collection(self):
        """Get or create global collection (thread-safe)"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not hasattr(self._local, 'collection') or self._local.collection is None:
            client = self.get_client()
            logger.info(f"[ChromaDB] Getting/creating collection: {self.collection_name}")
            try:
                self._local.collection = client.get_or_create_collection(
                    name=self.collection_name
                )
                logger.info(f"[ChromaDB] Collection count: {self._local.collection.count()}")
            except Exception as e:
                logger.warning(f"[ChromaDB] Failed to get/create collection: {e}, trying to recreate")
                try:
                    client.delete_collection(name=self.collection_name)
                except Exception:
                    pass
                self._local.collection = client.create_collection(
                    name=self.collection_name
                )
                logger.info(f"[ChromaDB] Collection recreated successfully")
        return self._local.collection
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Add documents to collection"""
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query similar documents"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[ChromaDB] Query: n_results={n_results}, where={where}")
            logger.info(f"[ChromaDB] Embedding len: {len(query_embedding)}")
            
            col = self.collection
            logger.info(f"[ChromaDB] Collection obtained, count={col.count()}")
            
            result = col.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            logger.info(f"[ChromaDB] Query success, results: {len(result['ids'][0])}")
            return result
        except Exception as e:
            logger.error(f"[ChromaDB] Query failed: {e}")
            logger.error(f"[ChromaDB] Traceback: {traceback.format_exc()}")
            return {
                'ids': [[]],
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }
    
    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        self.collection.delete(ids=ids)
    
    def delete_by_prefix(self, id_prefix: str) -> int:
        """
        Delete documents by ID prefix
        
        Used for deleting all chunks of a document
        
        Returns:
            Number of deleted documents
        """
        all_docs = self.collection.get()
        if not all_docs['ids']:
            return 0
        
        ids_to_delete = [
            doc_id for doc_id in all_docs['ids']
            if doc_id.startswith(id_prefix)
        ]
        
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        
        return len(ids_to_delete)
    
    def delete_collection(self) -> None:
        """Delete the entire collection"""
        self.get_client().delete_collection(name=self.collection_name)
        if hasattr(self._local, 'collection'):
            self._local.collection = None
    
    def count(self) -> int:
        """Get document count"""
        return self.collection.count()