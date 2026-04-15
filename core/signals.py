"""
Django Signal Handlers for Knowledge Base

Handles document sync to ChromaDB on save/delete.

Uses Celery .delay() for async execution to avoid blocking Django requests.
"""
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models.knowledge import KnowledgeDocument


@receiver(post_save, sender=KnowledgeDocument)
def on_document_save(sender, instance, created, **kwargs):
    """
    Trigger async sync after document save via Celery.
    """
    if created and instance.sync_status == 'pending':
        from core.tasks import sync_document_to_chroma
        sync_document_to_chroma.delay(instance.id)


@receiver(post_delete, sender=KnowledgeDocument)
def on_document_delete(sender, instance, **kwargs):
    """
    Clean up ChromaDB after document deletion via Celery.
    """
    if instance.chroma_id_prefix and instance.knowledge_base_id:
        from core.tasks import delete_document_chunks_from_chroma
        delete_document_chunks_from_chroma.delay(
            instance.chroma_id_prefix,
            instance.knowledge_base_id
        )