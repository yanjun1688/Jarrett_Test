"""
Embedding Service - Thread-safe singleton for text embedding

Uses sentence-transformers model for generating embeddings.
"""
import threading
from typing import List, Optional, cast

from sentence_transformers import SentenceTransformer

from core.config import settings


class EmbeddingService:
    """
    Embedding Service (process-level singleton)
    
    Note:
    1. In Django main process, model is loaded only once
    2. In Celery workers, each worker process holds its own model instance
    3. If using multiple workers, memory usage will multiply by worker count
    4. Recommend evaluating worker count vs memory resources, or use dedicated inference service
    
    Thread safety: Uses threading.Lock to ensure single initialization in multi-threaded environment
    """
    
    _instance: Optional['EmbeddingService'] = None
    _model: Optional[SentenceTransformer] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        with self._lock:
            if self._model is None:
                self._model = SentenceTransformer(settings.embedding_model)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        if self._model is None:
            raise RuntimeError("Embedding model not initialized")
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()
        return [list(e) if hasattr(e, 'tolist') else e for e in embeddings]
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        if self._model is None:
            raise RuntimeError("Embedding model not initialized")
        embedding = self._model.encode(query, convert_to_numpy=True)
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        return list(embedding)
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension"""
        if self._model is None:
            raise RuntimeError("Embedding model not initialized")
        return cast(int, self._model.get_sentence_embedding_dimension())
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing only)"""
        with cls._lock:
            cls._instance = None
            cls._model = None