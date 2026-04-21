"""
Django Signal Handlers

- Knowledge Base: document sync to ChromaDB on save/delete.
- Unified Models: auto-sync bridge models on source model save/delete.
"""
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models.knowledge import KnowledgeDocument
from core.models.unified import ScriptType, UnifiedExecution, UnifiedScript, UnifiedStatus
from testmanager_app.models import (
    AdvancedPressureTestConfig,
    AdvancedPressureTestExecution,
    PressureTestConfig,
    PressureTestExecution,
    ScriptExecution,
    TestScript,
)
from test_ui_app.models import UITestExecution, UITestScript

logger = logging.getLogger(__name__)


@receiver(post_save, sender=KnowledgeDocument)
def on_document_save(sender: Type[Any], instance: Any, created: bool, **kwargs: Any) -> None:
    """
    Trigger async sync after document save via Celery.
    """
    if created and instance.sync_status == 'pending':
        from core.tasks import sync_document_to_chroma
        sync_document_to_chroma.delay(instance.id)


@receiver(post_delete, sender=KnowledgeDocument)
def on_document_delete(sender: Type[Any], instance: Any, **kwargs: Any) -> None:
    """
    Clean up ChromaDB after document deletion via Celery.
    """
    if instance.chroma_id_prefix and instance.knowledge_base_id:
        from core.tasks import delete_document_chunks_from_chroma
        delete_document_chunks_from_chroma.delay(
            instance.chroma_id_prefix,
            instance.knowledge_base_id
        )


# ---------------------------------------------------------------------------
# Unified Models — Status mapping & sender config
# ---------------------------------------------------------------------------

STATUS_MAP: Dict[str, Dict[str, str]] = {
    'ScriptExecution': {
        'pending': UnifiedStatus.PENDING,
        'running': UnifiedStatus.RUNNING,
        'success': UnifiedStatus.PASSED,
        'failed': UnifiedStatus.FAILED,
    },
    'UITestExecution': {
        'pending': UnifiedStatus.PENDING,
        'running': UnifiedStatus.RUNNING,
        'passed': UnifiedStatus.PASSED,
        'failed': UnifiedStatus.FAILED,
        'skipped': UnifiedStatus.STOPPED,
    },
    'PressureTestExecution': {
        'pending': UnifiedStatus.PENDING,
        'running': UnifiedStatus.RUNNING,
        'completed': UnifiedStatus.PASSED,
        'stopped': UnifiedStatus.STOPPED,
        'failed': UnifiedStatus.FAILED,
    },
    'AdvancedPressureTestExecution': {
        'pending': UnifiedStatus.PENDING,
        'running': UnifiedStatus.RUNNING,
        'completed': UnifiedStatus.PASSED,
        'stopped': UnifiedStatus.STOPPED,
        'failed': UnifiedStatus.FAILED,
    },
}

SCRIPT_SENDER_CONFIG: Dict[Type[Any], str] = {
    TestScript: ScriptType.API,
    UITestScript: ScriptType.UI,
    PressureTestConfig: ScriptType.PRESSURE,
    AdvancedPressureTestConfig: ScriptType.ADVANCED_PRESSURE,
}

EXECUTION_SENDER_CONFIG: Dict[Type[Any], tuple[str, Type[Any]]] = {
    ScriptExecution: ('script', TestScript),
    UITestExecution: ('script', UITestScript),
    PressureTestExecution: ('config', PressureTestConfig),
    AdvancedPressureTestExecution: ('config', AdvancedPressureTestConfig),
}


# ---------------------------------------------------------------------------
# Unified Models — Script sync signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender=TestScript)
@receiver(post_save, sender=UITestScript)
@receiver(post_save, sender=PressureTestConfig)
@receiver(post_save, sender=AdvancedPressureTestConfig)
def sync_unified_script(
    sender: Type[Any],
    instance: Any,
    created: bool,
    **kwargs: Any,
) -> None:
    """Sync source script model to UnifiedScript on create/update."""
    try:
        ct = ContentType.objects.get_for_model(sender)
        script_type = SCRIPT_SENDER_CONFIG[sender]
        UnifiedScript.objects.update_or_create(
            content_type=ct,
            object_id=instance.pk,
            defaults={
                'name': instance.name,
                'description': instance.description,
                'script_type': script_type,
                'project': instance.project,
                'created_by': instance.created_by,
                'is_active': getattr(instance, 'is_active', True),
            },
        )
    except Exception:
        logger.exception(
            'Failed to sync UnifiedScript for %s id=%s',
            sender.__name__,
            instance.pk,
        )


@receiver(post_delete, sender=TestScript)
@receiver(post_delete, sender=UITestScript)
@receiver(post_delete, sender=PressureTestConfig)
@receiver(post_delete, sender=AdvancedPressureTestConfig)
def delete_unified_script(
    sender: Type[Any],
    instance: Any,
    **kwargs: Any,
) -> None:
    """Delete corresponding UnifiedScript when source script is deleted."""
    try:
        ct = ContentType.objects.get_for_model(sender)
        UnifiedScript.objects.filter(content_type=ct, object_id=instance.pk).delete()
    except Exception:
        logger.exception(
            'Failed to delete UnifiedScript for %s id=%s',
            sender.__name__,
            instance.pk,
        )


# ---------------------------------------------------------------------------
# Unified Models — Execution sync signals
# ---------------------------------------------------------------------------

def _get_duration_seconds(sender: Type[Any], instance: Any) -> Optional[float]:
    """Extract duration in seconds from source execution instance."""
    if sender is ScriptExecution:
        # DurationField — timedelta or None
        return instance.duration.total_seconds() if instance.duration else None
    if sender is UITestExecution:
        # FloatField (already seconds)
        duration: Optional[float] = instance.duration
        return duration
    # PressureTestExecution / AdvancedPressureTestExecution — FloatField
    result: Optional[float] = instance.duration_seconds
    return result


def _get_executor(sender: Type[Any], instance: Any) -> Any:
    """Extract executor user from source execution instance."""
    if sender is UITestExecution:
        return instance.executed_by
    return instance.executor


def _get_completed_at(sender: Type[Any], instance: Any) -> Any:
    """Extract completion time from source execution instance."""
    if sender is UITestExecution:
        return instance.completed_at
    return instance.finished_at


def _get_error_message(sender: Type[Any], instance: Any) -> str:
    """Extract error message from source execution instance."""
    if sender is AdvancedPressureTestExecution:
        return instance.error_log or ''
    if sender is PressureTestExecution:
        return ''
    return getattr(instance, 'error_message', '') or ''


@receiver(post_save, sender=ScriptExecution)
@receiver(post_save, sender=UITestExecution)
@receiver(post_save, sender=PressureTestExecution)
@receiver(post_save, sender=AdvancedPressureTestExecution)
def sync_unified_execution(
    sender: Type[Any],
    instance: Any,
    created: bool,
    **kwargs: Any,
) -> None:
    """Sync source execution record to UnifiedExecution on create/update."""
    try:
        # Look up the corresponding UnifiedScript via the source's script/config FK
        fk_attr, script_model = EXECUTION_SENDER_CONFIG[sender]
        source_script = getattr(instance, fk_attr)
        script_ct = ContentType.objects.get_for_model(script_model)
        unified_script = UnifiedScript.objects.get(
            content_type=script_ct,
            object_id=source_script.pk,
        )

        # Map status
        status_map = STATUS_MAP.get(sender.__name__, {})
        unified_status = status_map.get(instance.status, UnifiedStatus.PENDING)

        exec_ct = ContentType.objects.get_for_model(sender)
        UnifiedExecution.objects.update_or_create(
            content_type=exec_ct,
            object_id=instance.pk,
            defaults={
                'unified_script': unified_script,
                'status': unified_status,
                'executed_by': _get_executor(sender, instance),
                'started_at': instance.started_at,
                'completed_at': _get_completed_at(sender, instance),
                'duration_seconds': _get_duration_seconds(sender, instance),
                'error_message': _get_error_message(sender, instance),
            },
        )
    except Exception:
        logger.exception(
            'Failed to sync UnifiedExecution for %s id=%s',
            sender.__name__,
            instance.pk,
        )


@receiver(post_delete, sender=ScriptExecution)
@receiver(post_delete, sender=UITestExecution)
@receiver(post_delete, sender=PressureTestExecution)
@receiver(post_delete, sender=AdvancedPressureTestExecution)
def delete_unified_execution(
    sender: Type[Any],
    instance: Any,
    **kwargs: Any,
) -> None:
    """Delete corresponding UnifiedExecution when source execution is deleted."""
    try:
        ct = ContentType.objects.get_for_model(sender)
        UnifiedExecution.objects.filter(content_type=ct, object_id=instance.pk).delete()
    except Exception:
        logger.exception(
            'Failed to delete UnifiedExecution for %s id=%s',
            sender.__name__,
            instance.pk,
        )
