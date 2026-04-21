"""
Django Signal Handlers

- Knowledge Base: document sync to ChromaDB on save/delete.
- Unified Models: auto-sync bridge models on source model save/delete.
"""
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import json
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
    'TestExecution': {
        'pending': UnifiedStatus.PENDING,
        'passed': UnifiedStatus.PASSED,
        'failed': UnifiedStatus.FAILED,
        'blocked': UnifiedStatus.STOPPED,
        'skipped': UnifiedStatus.STOPPED,
    },
    'ChatBotExecutionLog': {
        'success': UnifiedStatus.PASSED,
        'error': UnifiedStatus.FAILED,
        'pending': UnifiedStatus.PENDING,
        'running': UnifiedStatus.RUNNING,
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
# Unified Models — Helper functions for extracting fields
# ---------------------------------------------------------------------------

def _get_duration_seconds(sender: Type[Any], instance: Any) -> Optional[float]:
    """Extract duration in seconds from source execution instance."""
    if sender is ScriptExecution:
        return instance.duration.total_seconds() if instance.duration else None
    if sender is UITestExecution:
        duration: Optional[float] = instance.duration
        return duration
    # PressureTestExecution / AdvancedPressureTestExecution — FloatField
    result: Optional[float] = getattr(instance, 'duration_seconds', None)
    return result


def _get_executor(sender: Type[Any], instance: Any) -> Any:
    """Extract executor user from source execution instance."""
    if sender is UITestExecution:
        return instance.executed_by
    return getattr(instance, 'executor', getattr(instance, 'executed_by', None))


def _get_completed_at(sender: Type[Any], instance: Any) -> Any:
    """Extract completion time from source execution instance."""
    if sender is UITestExecution:
        return instance.completed_at
    return getattr(instance, 'finished_at', getattr(instance, 'completed_at', None))


def _get_error_message(sender: Type[Any], instance: Any) -> str:
    """Extract error message from source execution instance."""
    if sender is AdvancedPressureTestExecution:
        return instance.error_log or ''
    if sender is PressureTestExecution:
        return ''
    return getattr(instance, 'error_message', '') or ''


def _get_logs(sender: Type[Any], instance: Any) -> str:
    """
    统一从各源模型获取执行日志。

    模型              取值逻辑
    ScriptExecution   instance.output
    TestExecution     instance.api_logs
    UITestExecution   instance.execution_log
    PressureTestExecution          instance.logs
    AdvancedPressureTestExecution  instance.logs
    ChatBotExecutionLog           instance.details.get('logs') 或 JSON stringify
    """
    from core.models.test_management import TestExecution
    from core.models.chatbot_execution_log import ChatBotExecutionLog

    if sender is ScriptExecution:
        return getattr(instance, 'output', '') or ''
    if sender is TestExecution:
        return getattr(instance, 'api_logs', '') or ''
    if sender is UITestExecution:
        return getattr(instance, 'execution_log', '') or ''
    if sender in (PressureTestExecution, AdvancedPressureTestExecution):
        return getattr(instance, 'logs', '') or ''
    if sender is ChatBotExecutionLog:
        details = getattr(instance, 'details', None)
        if details and isinstance(details, dict):
            logs_val = details.get('logs', '')
            if isinstance(logs_val, str):
                return logs_val
            return json.dumps(logs_val, ensure_ascii=False, default=str)
        return ''
    return ''


def _get_script_name_for_execution(sender: Type[Any], instance: Any) -> str:
    """Extract script/config name from execution instance."""
    from core.models.test_management import TestExecution
    from core.models.chatbot_execution_log import ChatBotExecutionLog

    if sender is TestExecution:
        if instance.test_script:
            return str(instance.test_script.name)
        if instance.api_request:
            return str(instance.api_request.name)
        if instance.test_case:
            return str(instance.test_case.title)
        return f'TestExecution #{instance.pk}'
    if sender is ChatBotExecutionLog:
        return str(instance.title) or f'ChatBot #{instance.pk}'
    # For standard execution senders (ScriptExecution, UITestExecution, etc.)
    fk_attr = EXECUTION_SENDER_CONFIG.get(sender, (None, None))[0]
    if fk_attr:
        source_script = getattr(instance, fk_attr, None)
        if source_script:
            return getattr(source_script, 'name', '')
    return ''


def _get_project_for_execution(sender: Type[Any], instance: Any) -> Any:
    """Extract project from execution instance."""
    from core.models.test_management import TestExecution
    from core.models.chatbot_execution_log import ChatBotExecutionLog

    if sender is TestExecution:
        if instance.test_script and instance.test_script.project:
            return instance.test_script.project
        if instance.api_request and instance.api_request.project:
            return instance.api_request.project
        if instance.test_case and instance.test_case.project:
            return instance.test_case.project
        return None
    if sender is ChatBotExecutionLog:
        # ChatBotExecutionLog 通过 execution FK 间接获取 project
        if instance.execution:
            return _get_project_for_execution(TestExecution, instance.execution)
        return None
    # Standard senders
    fk_attr = EXECUTION_SENDER_CONFIG.get(sender, (None, None))[0]
    if fk_attr:
        source_script = getattr(instance, fk_attr, None)
        if source_script:
            return getattr(source_script, 'project', None)
    return None


def _get_script_type_for_execution(sender: Type[Any], instance: Any) -> str:
    """Determine script_type for execution."""
    from core.models.test_management import TestExecution
    from core.models.chatbot_execution_log import ChatBotExecutionLog

    if sender is TestExecution:
        type_map: Dict[str, str] = {
            'api': ScriptType.API,
            'script': ScriptType.SCRIPT,
            'functional': ScriptType.API,
            'flow': ScriptType.API,
        }
        return type_map.get(instance.test_type, ScriptType.API)
    if sender is ChatBotExecutionLog:
        return ScriptType.CHATBOT
    if sender is ScriptExecution:
        return ScriptType.API
    if sender is UITestExecution:
        return ScriptType.UI
    if sender is PressureTestExecution:
        return ScriptType.PRESSURE
    if sender is AdvancedPressureTestExecution:
        return ScriptType.ADVANCED_PRESSURE
    return ScriptType.API


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
# Unified Models — Execution sync signals (standard senders with UnifiedScript)
# ---------------------------------------------------------------------------

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
                'script_name': _get_script_name_for_execution(sender, instance),
                'script_type': _get_script_type_for_execution(sender, instance),
                'project': _get_project_for_execution(sender, instance),
                'status': unified_status,
                'executed_by': _get_executor(sender, instance),
                'started_at': instance.started_at,
                'completed_at': _get_completed_at(sender, instance),
                'duration_seconds': _get_duration_seconds(sender, instance),
                'error_message': _get_error_message(sender, instance),
                'logs': _get_logs(sender, instance),
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


# ---------------------------------------------------------------------------
# Unified Models — TestExecution sync (no UnifiedScript FK)
# ---------------------------------------------------------------------------

def _sync_test_execution(sender: Type[Any], instance: Any, **kwargs: Any) -> None:
    """Sync TestExecution to UnifiedExecution (unified_script=None)."""
    try:
        status_map = STATUS_MAP.get('TestExecution', {})
        unified_status = status_map.get(instance.status, UnifiedStatus.PENDING)

        exec_ct = ContentType.objects.get_for_model(sender)
        UnifiedExecution.objects.update_or_create(
            content_type=exec_ct,
            object_id=instance.pk,
            defaults={
                'unified_script': None,
                'script_name': _get_script_name_for_execution(sender, instance),
                'script_type': _get_script_type_for_execution(sender, instance),
                'project': _get_project_for_execution(sender, instance),
                'status': unified_status,
                'executed_by': instance.executed_by,
                'started_at': instance.executed_at,
                'completed_at': None,
                'duration_seconds': instance.duration if instance.duration else None,
                'error_message': getattr(instance, 'error_message', '') or '',
                'logs': _get_logs(sender, instance),
            },
        )
    except Exception:
        logger.exception(
            'Failed to sync UnifiedExecution for TestExecution id=%s',
            instance.pk,
        )


def _delete_test_execution(sender: Type[Any], instance: Any, **kwargs: Any) -> None:
    """Delete UnifiedExecution when TestExecution is deleted."""
    try:
        ct = ContentType.objects.get_for_model(sender)
        UnifiedExecution.objects.filter(content_type=ct, object_id=instance.pk).delete()
    except Exception:
        logger.exception(
            'Failed to delete UnifiedExecution for TestExecution id=%s',
            instance.pk,
        )


# Lazy-connect to avoid circular import at module level
def _connect_test_execution_signals() -> None:
    """Connect TestExecution signals (called from AppConfig.ready)."""
    from core.models.test_management import TestExecution
    post_save.connect(_sync_test_execution, sender=TestExecution)
    post_delete.connect(_delete_test_execution, sender=TestExecution)


# ---------------------------------------------------------------------------
# Unified Models — ChatBotExecutionLog sync
# ---------------------------------------------------------------------------

def _sync_chatbot_execution_log(sender: Type[Any], instance: Any, **kwargs: Any) -> None:
    """Sync ChatBotExecutionLog to UnifiedExecution."""
    try:
        from core.models.chatbot_execution_log import ChatBotExecutionLog

        details = instance.details or {}
        raw_status = details.get('status', 'pending') if isinstance(details, dict) else 'pending'
        status_map = STATUS_MAP.get('ChatBotExecutionLog', {})
        unified_status = status_map.get(raw_status, UnifiedStatus.PENDING)

        exec_ct = ContentType.objects.get_for_model(sender)
        UnifiedExecution.objects.update_or_create(
            content_type=exec_ct,
            object_id=instance.pk,
            defaults={
                'unified_script': None,
                'script_name': _get_script_name_for_execution(sender, instance),
                'script_type': ScriptType.CHATBOT,
                'project': _get_project_for_execution(sender, instance),
                'status': unified_status,
                'executed_by': None,
                'started_at': instance.created_at,
                'completed_at': None,
                'duration_seconds': None,
                'error_message': details.get('error', '') if isinstance(details, dict) else '',
                'logs': _get_logs(sender, instance),
            },
        )
    except Exception:
        logger.exception(
            'Failed to sync UnifiedExecution for ChatBotExecutionLog id=%s',
            instance.pk,
        )


def _delete_chatbot_execution_log(sender: Type[Any], instance: Any, **kwargs: Any) -> None:
    """Delete UnifiedExecution when ChatBotExecutionLog is deleted."""
    try:
        ct = ContentType.objects.get_for_model(sender)
        UnifiedExecution.objects.filter(content_type=ct, object_id=instance.pk).delete()
    except Exception:
        logger.exception(
            'Failed to delete UnifiedExecution for ChatBotExecutionLog id=%s',
            instance.pk,
        )


def _connect_chatbot_execution_log_signals() -> None:
    """Connect ChatBotExecutionLog signals (called from AppConfig.ready)."""
    from core.models.chatbot_execution_log import ChatBotExecutionLog
    post_save.connect(_sync_chatbot_execution_log, sender=ChatBotExecutionLog)
    post_delete.connect(_delete_chatbot_execution_log, sender=ChatBotExecutionLog)
