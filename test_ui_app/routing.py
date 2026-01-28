"""
WebSocket路由配置 for test_ui_app
定义所有WebSocket连接的URL模式
"""

from django.urls import re_path
from channels.routing import URLRouter

# WebSocket URL模式列表
# 目前为空，录制器已切换为同步REST模式
# 如需添加WebSocket消费者，请按以下格式添加：
# websocket_urlpatterns = [
#     re_path(r'ws/test/$', consumer_class.as_asgi()),
# ]

websocket_urlpatterns = []

# WebSocket路由器实例（备用）
application = URLRouter(websocket_urlpatterns)
