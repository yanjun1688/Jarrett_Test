"""
Celery Tasks for Knowledge Base

Handles async sync of documents to ChromaDB.
"""
import logging
import re
from typing import Any, List
from celery import shared_task
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from core.models.knowledge import KnowledgeDocument, KnowledgeBase

logger = logging.getLogger(__name__)


def _extract_keywords(doc: Any) -> List[str]:
    keywords = []
    
    title = doc.metadata.get('title', '')
    if title:
        keywords.append(title)
    
    existing_keywords = doc.metadata.get('keywords', [])
    if existing_keywords:
        keywords.extend(existing_keywords)
    
    tags = doc.metadata.get('tags', [])
    if tags:
        keywords.extend(tags)
    
    name = doc.metadata.get('name', '')
    if name:
        keywords.append(name)
    
    content_sample = doc.content[:500] if doc.content else ''
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
    Sync document to ChromaDB
    
    Uses database-level optimistic lock for re-entry prevention:
    UPDATE ... SET sync_status='syncing' WHERE id=? AND sync_status='pending'
    Only successful update will proceed with sync.
    """
    from core.agents.rag.knowledge_retriever import KnowledgeRetriever
    
    try:
        updated = KnowledgeDocument.objects.filter(
            id=document_id,
            sync_status='pending'
        ).update(sync_status='syncing')
        
        if updated == 0:
            logger.info(f"Document {document_id} already being processed or synced")
            return
        
        doc = KnowledgeDocument.objects.select_related(
            'knowledge_base__project'
        ).get(id=document_id)
        
        project_id = doc.knowledge_base.project_id
        
        retriever = KnowledgeRetriever()
        
        chroma_id = doc.chroma_id
        chroma_id_prefix = f"doc_{doc.id}_"
        
        metadata = doc.metadata.copy()
        keywords = _extract_keywords(doc)
        metadata.update({
            'doc_type': doc.document_type,
            'knowledge_base_id': doc.knowledge_base.id,
            'knowledge_base_name': doc.knowledge_base.name,
            'project_id': project_id,
            'keywords': ','.join(keywords),
            'chroma_id_prefix': chroma_id_prefix,
        })
        
        retriever.add_document(
            content=doc.content,
            metadata=metadata,
            doc_id=chroma_id
        )
        
        doc.chroma_id_prefix = chroma_id_prefix
        doc.sync_status = 'synced'
        doc.synced_at = timezone.now()
        doc.sync_error = ''
        doc.save(update_fields=['chroma_id_prefix', 'sync_status', 'synced_at', 'sync_error'])
        
        logger.info(f"Document {document_id} synced to ChromaDB: {chroma_id}")
        
    except KnowledgeDocument.DoesNotExist:
        logger.error(f"Document {document_id} not found")
    except Exception as e:
        logger.error(f"Failed to sync document {document_id}: {e}")
        KnowledgeDocument.objects.filter(id=document_id).update(
            sync_status='failed',
            sync_error=str(e)
        )
        raise self.retry(exc=e)


@shared_task
def delete_document_chunks_from_chroma(chroma_id_prefix: str, knowledge_base_id: int) -> None:
    """
    Delete all chunks of a document from ChromaDB

    Args:
        chroma_id_prefix: Document ID prefix, e.g., "doc_123_"
        knowledge_base_id: Knowledge base ID (for project_id lookup)
    """
    from core.agents.rag.knowledge_retriever import KnowledgeRetriever
    try:
        kb = KnowledgeBase.objects.select_related('project').get(id=knowledge_base_id)
        project_id = kb.project_id
        
        retriever = KnowledgeRetriever()
        deleted_count = retriever.delete_document_chunks(chroma_id_prefix)
        logger.info(f"Deleted {deleted_count} chunks with prefix {chroma_id_prefix}")
    except ObjectDoesNotExist:
        logger.error(f"KnowledgeBase {knowledge_base_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete chunks {chroma_id_prefix}: {e}")


@shared_task
def sync_test_case_to_knowledge(test_case_id: int, knowledge_base_id: int) -> None:
    """Sync feature test case to knowledge base"""
    from django.apps import apps
    from core.services.document_converter import DocumentConverter
    from core.agents.rag.knowledge_retriever import KnowledgeRetriever
    
    try:
        FeatureTestCase = apps.get_model('testmanager_app', 'FeatureTestCase')
        test_case = FeatureTestCase.objects.select_related('project').get(id=test_case_id)
        converted = DocumentConverter.feature_test_to_markdown(test_case)
        
        doc = KnowledgeDocument.objects.create(
            knowledge_base_id=knowledge_base_id,
            document_type='test_pattern',
            content=converted['content'],
            metadata=converted['metadata'],
            sync_status='pending'
        )
        
        sync_document_to_chroma(doc.id)
        
    except Exception as e:
        logger.error(f"Failed to sync test case {test_case_id}: {e}")


@shared_task
def batch_sync_project_documents(project_id: int) -> str:
    """
    Batch sync all pending documents for a project

    Optimization: Cache results with list() to avoid N+1 queries
    """
    from core.agents.rag.knowledge_retriever import KnowledgeRetriever
    
    pending_docs = list(
        KnowledgeDocument.objects.filter(
            knowledge_base__project_id=project_id,
            sync_status='pending'
        ).values_list('id', flat=True)
    )
    
    for doc_id in pending_docs:
        sync_document_to_chroma(doc_id)
    
    count = len(pending_docs)
    logger.info(f"Synced {count} documents in project {project_id}")
    return f"Synced {count} documents"