"""
对话记忆 RAG 检索与索引

对话消息的语义检索和异步索引，使用单独的 ChromaDB collection
"conversation_memory" 存储，与知识库 RAG ("kb_knowledge") 隔离。

设计原则：
- 仅向量检索，不用 BM25（对话短句多，关键词匹配效果差）
- 按 user_id 做数据隔离
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

from core.agents.rag.vector_store import ChromaVectorStore
from core.config import settings

logger = logging.getLogger(__name__)


class ConversationMemoryRetriever:
    """
    对话记忆检索器

    只做向量检索（不过 BM25）。原因：
    - 对话消息短、口语化，BM25 关键词匹配效果差
    - 向量语义匹配更适合"意思相近但用词不同"的场景
    """

    COLLECTION_NAME = "conversation_memory"

    def __init__(self) -> None:
        from core.agents.rag.knowledge_retriever import EmbeddingService
        self.embedding_service = EmbeddingService()
        self.vector_store = ChromaVectorStore(collection_name=self.COLLECTION_NAME)

    def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索相关历史对话。

        Args:
            query: 用户当前问题
            user_id: 用户 ID（数据隔离必须）
            top_k: 返回条数
            session_id: 可选，限制只搜某个会话

        Returns:
            [{content, role, timestamp, session_id, score}, ...]
        """
        logger.info(f"[MemoryRetriever] Searching: query_len={len(query)}, user_id={user_id}, top_k={top_k}, session_id={session_id}")

        query_embedding = self.embedding_service.embed_query(query)

        if session_id:
            where: Dict[str, Any] = {
                "$and": [
                    {"user_id": {"$eq": str(user_id)}},
                    {"session_id": {"$eq": str(session_id)}},
                ]
            }
        else:
            where = {"user_id": {"$eq": str(user_id)}}

        result = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=where,
        )

        documents: List[Dict[str, Any]] = []
        if result and result.get("ids") and result["ids"][0]:
            for i in range(len(result["ids"][0])):
                documents.append({
                    "id": result["ids"][0][i],
                    "content": result["documents"][0][i],
                    "role": result["metadatas"][0][i].get("role", ""),
                    "timestamp": result["metadatas"][0][i].get("timestamp", ""),
                    "session_id": result["metadatas"][0][i].get("session_id", ""),
                    "score": 1 - result["distances"][0][i],
                })

        logger.info(f"[MemoryRetriever] Found {len(documents)} results for user_id={user_id}")
        return documents


class ConversationMemoryIndexer:
    """
    对话记忆索引器

    将消息 embedding 后存入 ChromaDB，走异步路径（Celery 任务）。
    """

    COLLECTION_NAME = "conversation_memory"

    def __init__(self) -> None:
        from core.agents.rag.knowledge_retriever import EmbeddingService
        self.embedding_service = EmbeddingService()
        self.vector_store = ChromaVectorStore(collection_name=self.COLLECTION_NAME)

    def index_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        message_id: str,
    ) -> None:
        """
        索引单条消息到 ChromaDB。

        Args:
            session_id: 会话 ID
            user_id: 用户 ID（用于数据隔离）
            role: 消息角色（user/assistant）
            content: 消息内容
            message_id: 唯一消息 ID（uuid4，由调用方生成）
        """
        if not content or len(content.strip()) < settings.memory_index_min_length:
            logger.debug(f"[MemoryIndexer] Skip short message: role={role}, len={len(content.strip())}")
            return

        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.debug(f"[MemoryIndexer] Indexing: role={role}, msg_id={message_id}, session={session_id}, user={user_id}, content_len={len(content)}")

        embedding = self.embedding_service.embed_query(content)

        self.vector_store.add_documents(
            documents=[content],
            embeddings=[embedding],
            metadatas=[{
                "user_id": str(user_id),
                "session_id": str(session_id),
                "role": role,
                "timestamp": timestamp,
            }],
            ids=[message_id],
        )

        logger.debug(f"[MemoryIndexer] Indexed {message_id} successfully")

    def delete_session(self, session_id: str) -> int:
        """删除该会话的所有记忆索引"""
        deleted = cast(int, self.vector_store.delete_by_metadata({"session_id": session_id}))
        logger.debug(f"[MemoryIndexer] Deleted {deleted} memory docs for session={session_id}")
        return deleted
