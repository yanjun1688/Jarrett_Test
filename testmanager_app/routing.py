"""
WebSocket 路由配置 for testmanager_app
压力测试相关的 WebSocket 连接路由
"""

from __future__ import annotations

from typing import List

from django.urls import re_path

from testmanager_app.consumers import PressureTestConsumer, AdvancedPressureTestConsumer

websocket_urlpatterns: List = [
    re_path(r'ws/pressure-test/(?P<execution_id>\d+)/?$', PressureTestConsumer.as_asgi()),
    re_path(r'ws/advanced-pressure-test/(?P<execution_id>\d+)/?$', AdvancedPressureTestConsumer.as_asgi()),
]
