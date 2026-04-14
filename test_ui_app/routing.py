"""
WebSocket路由配置 for test_ui_app
定义所有WebSocket连接的URL模式
"""

from __future__ import annotations

from typing import List

from django.urls import re_path
from channels.routing import URLRouter

from test_ui_app.consumers import ChatBotConsumer

websocket_urlpatterns: List = [
    re_path(r'ws/chatbot/?$', ChatBotConsumer.as_asgi()),
]

application = URLRouter(websocket_urlpatterns)
