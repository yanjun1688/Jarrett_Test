"""
WebSocket路由配置 for test_ui_app
定义所有WebSocket连接的URL模式
"""
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

from typing import List

from django.urls import re_path
from channels.routing import URLRouter

from test_ui_app.consumers import ChatBotConsumer, PressureTestConsumer
from test_ui_app.advanced_pressure_consumers import AdvancedPressureTestConsumer

websocket_urlpatterns: List = [
    re_path(r'ws/chatbot/?$', ChatBotConsumer.as_asgi()),
    re_path(r'ws/pressure-test/(?P<execution_id>\d+)/?$', PressureTestConsumer.as_asgi()),
    re_path(r'ws/advanced-pressure-test/(?P<execution_id>\d+)/?$', AdvancedPressureTestConsumer.as_asgi()),
]

application = URLRouter(websocket_urlpatterns)
