"""
WebSocket路由配置 for test_ui_app
ChatBot 对话 WebSocket 路由
"""
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

from typing import List

from django.urls import re_path
from channels.routing import URLRouter

from test_ui_app.consumers import ChatBotConsumer

websocket_urlpatterns: List = [
    re_path(r'ws/chatbot/?$', ChatBotConsumer.as_asgi()),
]

application = URLRouter(websocket_urlpatterns)
