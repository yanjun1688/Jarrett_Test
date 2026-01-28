"""
ASGI config for testmanager project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import sys
import asyncio

if sys.platform == 'win32':
    # 显式设置 ProactorEventLoopPolicy，确保 Playwright 在 Daphne 下能正常工作
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("显式设置 WindowsProactorEventLoopPolicy (from asgi.py)")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testmanager.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

# 初始化Django应用（必须在导入路由和中间件之前完成）
# 这是关键：必须在导入任何Django模型之前初始化Django应用
django_asgi_app = get_asgi_application()

# 在Django应用初始化后再导入路由配置和中间件（这些模块可能导入Django模型）
from channels.auth import AuthMiddlewareStack
from test_ui_app.middleware import TokenAuthMiddlewareStack
import test_ui_app.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # WebSocket 路由目前为空，录制器已切换为同步 REST 模式
    "websocket": TokenAuthMiddlewareStack(
        URLRouter(
            test_ui_app.routing.websocket_urlpatterns
        )
    ),
})
