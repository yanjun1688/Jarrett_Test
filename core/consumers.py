"""
Celery 任务状态 WebSocket Consumer

根据认证用户的 ID 加入对应隔离组，只接收自己的任务事件。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

CELERY_TASKS_GROUP_PREFIX = "celery_tasks"


class CeleryTaskConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or not hasattr(user, "id") or not user.id:
            await self.close(code=4001)
            return
        self.group_name = f"{CELERY_TASKS_GROUP_PREFIX}_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"[CeleryWS] Connected: channel={self.channel_name}, group={self.group_name}")

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"[CeleryWS] Disconnected: channel={self.channel_name}, code={close_code}")

    async def task_status(self, event: dict[str, Any]) -> None:
        """
        接收 task.status 类型的事件。

        group_send 发的消息中 type="task.status"
        → Channels 自动将 "." 转换为 "_" → 调用 task_status()
        """
        await self.send(text_data=json.dumps({
            "type": "task.status",
            "task_id": event.get("task_id"),
            "task_name": event.get("task_name"),
            "status": event.get("status"),
            "error": event.get("error"),
        }))
