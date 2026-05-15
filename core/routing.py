"""
WebSocket 路由配置 for core
Celery 任务状态推送
"""
from __future__ import annotations

from typing import List

from django.urls import re_path

from core.consumers import CeleryTaskConsumer

websocket_urlpatterns: List = [
    re_path(r'ws/celery/tasks/?$', CeleryTaskConsumer.as_asgi()),
]
