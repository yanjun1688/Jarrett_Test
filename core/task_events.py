"""
Celery 任务事件发布

通过 Channel Layer 广播任务状态到指定用户的 WebSocket。
复用已有基础设施，不需要新 Redis 连接。
"""
from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

CELERY_TASKS_GROUP_PREFIX = "celery_tasks"


def _group_name(user_id: str | None) -> str:
    """构建按用户隔离的群名"""
    return f"{CELERY_TASKS_GROUP_PREFIX}_{user_id}" if user_id else CELERY_TASKS_GROUP_PREFIX


def publish(
    task_id: str,
    task_name: str,
    status: str,
    user_id: str | None = None,
    **extra: Any,
) -> None:
    """
    发布任务状态事件到 Channel Layer。

    Args:
        task_id: Celery 任务 ID (self.request.id)
        task_name: 任务全限定名 (如 "core.tasks.sync_document_to_chroma")
        status: 状态 ("success" | "failed" | 自定义)
        user_id: 用户 ID，用于隔离（未传入时广播到公共组）
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("[TaskEvents] Channel layer not available")
            return
        async_to_sync(channel_layer.group_send)(
            _group_name(user_id),
            {
                "type": "task.status",
                "task_id": task_id,
                "task_name": task_name,
                "status": status,
                **extra,
            },
        )
    except Exception as e:
        logger.warning(f"[TaskEvents] Publish failed: {e}")
