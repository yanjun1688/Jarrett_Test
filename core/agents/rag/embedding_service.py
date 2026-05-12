import functools
import threading
from typing import List, Optional

from sentence_transformers import SentenceTransformer

from core.config import settings


class EmbeddingService:
    """
    进程级单例 + 线程安全初始化 + 可控 batch
    Celery 每个 worker 进程一份，Django 主进程一份
    """
    
    _instance: Optional["EmbeddingService"] = None
    _init_lock = threading.Lock()
    
    def __new__(cls):
        # 双重检查锁定，但只保证 __new__ 安全
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False  # 标记未初始化
        return cls._instance
    
    def __init__(self):
        # 真正的初始化锁 + 标记检查
        if getattr(self, "_initialized", False):
            return
        
        with self._init_lock:
            if getattr(self, "_initialized", False):
                return
            
            self._model = SentenceTransformer(settings.embedding_model)
            self._dimension = self._model.get_sentence_embedding_dimension()
            self._batch_size = getattr(settings, "embedding_batch_size", 32)
            self._initialized = True
    
    def embed_texts(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        if not texts:
            return []
        
        bs = batch_size or self._batch_size
        # encode 内部有 batch 处理，但显式控制更稳
        embeddings = self._model.encode(
            texts,
            batch_size=bs,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()  # type: ignore[no-any-return]
    
    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]
    
    @property
    def dimension(self):
        return self._dimension
    
    @classmethod
    def reset_instance(cls):
        """测试专用：真正释放内存"""
        with cls._init_lock:
            inst = cls._instance
            if inst is not None:
                del inst._model
                cls._instance = None
                import gc
                gc.collect()
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass


# 全局入口，避免到处 new
@functools.lru_cache(maxsize=1)
def get_embedder() -> EmbeddingService:
    return EmbeddingService()