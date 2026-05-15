"""
Celery Tasks for Knowledge Base

Handles async sync of documents to ChromaDB with chunking support.
"""
from __future__ import annotations

import logging
import re
from typing import Any, List, cast

from celery import shared_task
from django.utils import timezone

from core.models.knowledge import KnowledgeDocument
from core.task_events import publish

logger = logging.getLogger(__name__)


def _resolve_user_id_from_knowledge_base(knowledge_base_id: int) -> int | None:
    from core.models.knowledge import KnowledgeBase
    try:
        kb = KnowledgeBase.objects.select_related('project').only(
            'project__created_by'
        ).get(id=knowledge_base_id)
        return cast(int | None, kb.project.created_by_id)
    except KnowledgeBase.DoesNotExist:
        return None


def _resolve_user_id_from_project(project_id: int) -> int | None:
    from core.models.project import Project
    try:
        return cast(int | None, Project.objects.only('created_by_id').get(id=project_id).created_by_id)
    except Project.DoesNotExist:
        return None


def _extract_keywords(content: str, metadata: dict) -> List[str]:
    keywords = []
    title = metadata.get('title', '')
    if title:
        keywords.append(title)
    existing_keywords = metadata.get('keywords', [])
    if existing_keywords:
        keywords.extend(existing_keywords)
    tags = metadata.get('tags', [])
    if tags:
        keywords.extend(tags)
    content_sample = content[:500] if content else ''
    api_patterns = re.findall(r'API[_\-\w]*', content_sample)
    keywords.extend(api_patterns[:3])
    unique_keywords = []
    seen = set()
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen and kw:
            seen.add(kw_lower)
            unique_keywords.append(kw)
    return unique_keywords[:10]


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_document_to_chroma(self: Any, document_id: int) -> None:
    """
    Sync document to ChromaDB with chunking.

    Flow:
    1. Find the root document (chunk_index=-1)
    2. Run Chunker to split content into chunks
    3. Delete existing chunks from ChromaDB (if re-syncing)
    4. Batch embed + write chunks directly to ChromaDB
    5. Update root doc status (no chunk records in MySQL)
    """
    from core.agents.rag.knowledge_retriever import KnowledgeRetriever
    from core.agents.rag.chunker import Chunker

    user_id: int | None = None
    try:
        root_doc = KnowledgeDocument.objects.select_related(
            'knowledge_base__project',
        ).get(id=document_id)
        user_id = root_doc.knowledge_base.project.created_by_id

        if root_doc.sync_status == 'syncing':
            logger.info(f'Document {document_id} already being synced')
            return

        # Mark as syncing
        KnowledgeDocument.objects.filter(id=document_id).update(
            sync_status='syncing',
        )
        root_doc.refresh_from_db()

        project_id = root_doc.knowledge_base.project_id
        doc_type = root_doc.document_type
        content = root_doc.content
        chroma_id_prefix = f'source_{root_doc.id}_'

        # Delete existing chunks from ChromaDB (for re-sync)
        retriever = KnowledgeRetriever()
        retriever.delete_document_chunks(chroma_id_prefix)

        # Run chunker
        chunker = Chunker()
        chunks = chunker.chunk(doc_type, content)
        if not chunks:
            raise ValueError('Chunking returned empty result')

        # Build metadata base
        base_metadata = root_doc.metadata.copy()
        keywords = _extract_keywords(content, root_doc.metadata)
        base_metadata.update({
            'doc_type': doc_type,
            'knowledge_base_id': root_doc.knowledge_base.id,
            'knowledge_base_name': root_doc.knowledge_base.name,
            'project_id': project_id,
            'keywords': ','.join(keywords),
            'chroma_id_prefix': chroma_id_prefix,
            'root_document_id': root_doc.id,
        })

        # Batch embed and write to ChromaDB
        chunk_contents = [chunk.content for chunk in chunks]
        chunk_metadatas = [{
            **base_metadata,
            'chunk_index': chunk.chunk_index,
            'title': f"{root_doc.metadata.get('title', '')} (part {chunk.chunk_index + 1})",
        } for chunk in chunks]
        chunk_ids = [
            f'{chroma_id_prefix}chunk_{chunk.chunk_index}'
            for chunk in chunks
        ]

        embeddings = retriever.embedding_service.embed_texts(chunk_contents)
        retriever.vector_store.add_documents(
            documents=chunk_contents,
            embeddings=embeddings,
            metadatas=chunk_metadatas,
            ids=chunk_ids,
        )

        # Write to BM25 index
        from core.agents.rag.bm25_index import BM25Index
        bm25 = BM25Index()
        bm25_docs = [
            {
                'chunk_id': chunk_ids[i],
                'content': chunk_contents[i],
                'doc_type': doc_type,
                'title': root_doc.metadata.get('title', ''),
                'knowledge_base_id': root_doc.knowledge_base.id,
                'project_id': project_id,
            }
            for i in range(len(chunks))
        ]
        bm25.add_documents_batch(bm25_docs)

        # Update root document (no chunk records in MySQL)
        root_doc.chroma_id_prefix = chroma_id_prefix
        root_doc.sync_status = 'synced'
        root_doc.synced_at = timezone.now()
        root_doc.sync_error = ''
        root_doc.save(update_fields=[
            'chroma_id_prefix', 'sync_status', 'synced_at', 'sync_error',
        ])

        logger.info(
            f'Document {document_id} synced: {len(chunks)} chunks '
            f'(prefix={chroma_id_prefix})',
        )
        publish(
            self.request.id,
            'core.tasks.sync_document_to_chroma',
            'success',
            user_id=str(user_id) if user_id else None,
        )

    except KnowledgeDocument.DoesNotExist:
        logger.error(f'Document {document_id} not found')
        publish(
            self.request.id,
            'core.tasks.sync_document_to_chroma',
            'failed',
            error=f'Document {document_id} not found',
        )
    except Exception as e:
        logger.error(f'Failed to sync document {document_id}: {e}')
        KnowledgeDocument.objects.filter(id=document_id).update(
            sync_status='failed',
            sync_error=str(e)[:500],
        )
        publish(
            self.request.id,
            'core.tasks.sync_document_to_chroma',
            'failed',
            user_id=str(user_id) if user_id else None,
            error=str(e)[:500],
        )
        raise self.retry(exc=e)


@shared_task(bind=True)
def delete_document_chunks_from_chroma(self: Any, chroma_id_prefix: str, knowledge_base_id: int) -> None:
    """Delete all chunks from ChromaDB by prefix."""
    from core.agents.rag.knowledge_retriever import KnowledgeRetriever
    user_id = _resolve_user_id_from_knowledge_base(knowledge_base_id)
    try:
        retriever = KnowledgeRetriever()
        deleted_count = retriever.delete_document_chunks(chroma_id_prefix)
        logger.info(f'Deleted {deleted_count} chunks with prefix {chroma_id_prefix}')
        publish(
            self.request.id,
            'core.tasks.delete_document_chunks_from_chroma',
            'success',
            user_id=str(user_id) if user_id else None,
        )
    except Exception as e:
        logger.error(f'Failed to delete chunks {chroma_id_prefix}: {e}')
        publish(
            self.request.id,
            'core.tasks.delete_document_chunks_from_chroma',
            'failed',
            user_id=str(user_id) if user_id else None,
            error=str(e)[:500],
        )


@shared_task(bind=True)
def batch_sync_project_documents(self: Any, project_id: int) -> str:
    """Batch sync all pending root documents for a project."""
    user_id = _resolve_user_id_from_project(project_id)
    pending_docs = list(
        KnowledgeDocument.objects.filter(
            knowledge_base__project_id=project_id,
            sync_status='pending',
            chunk_index=-1,
        ).values_list('id', flat=True)
    )
    for doc_id in pending_docs:
        sync_document_to_chroma(doc_id)
    count = len(pending_docs)
    logger.info(f'Synced {count} documents in project {project_id}')
    publish(
        self.request.id,
        'core.tasks.batch_sync_project_documents',
        'success',
        user_id=str(user_id) if user_id else None,
    )
    return f'Synced {count} documents'


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def index_conversation_memory(
    self: Any,
    session_id: str,
    user_id: str,
    role: str,
    content: str,
) -> None:
    """
    Celery 任务：将消息 embedding 后存入对话记忆 ChromaDB。

    异步执行，不阻塞用户响应。
    """
    from uuid import uuid4
    message_id = str(uuid4())
    logger.info(f"[Task] index_conversation_memory started: msg_id={message_id}, session={session_id}, role={role}, content_len={len(content)}")
    try:
        from core.agents.rag.conversation_memory import ConversationMemoryIndexer
        indexer = ConversationMemoryIndexer()
        indexer.index_message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            message_id=message_id,
        )
        logger.info(f"[Task] index_conversation_memory completed: msg_id={message_id}")
        publish(
            self.request.id,
            'core.tasks.index_conversation_memory',
            'success',
            user_id=str(user_id) if user_id else None,
        )
    except Exception as e:
        logger.error(f"[Task] index_conversation_memory failed: msg_id={message_id}, error={e}")
        publish(
            self.request.id,
            'core.tasks.index_conversation_memory',
            'failed',
            user_id=str(user_id) if user_id else None,
            error=str(e)[:500],
        )
        raise self.retry(exc=e)
