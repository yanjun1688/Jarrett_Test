from __future__ import annotations

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class TestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testmanager_app"
    
    def ready(self) -> None:
        """应用准备就绪，预加载 Embedding 模型"""
        try:
            from core.agents.rag.embedding_service import EmbeddingService
            EmbeddingService()
            logger.info("Embedding model preloaded at startup")
        except Exception as e:
            logger.warning(f"Failed to preload Embedding model: {e}")