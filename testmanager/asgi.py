"""
ASGI config for testmanager project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/

MCP Lifespan 管理：
- 应用启动时初始化 MCP Server 连接
- 应用关闭时清理连接
"""

from __future__ import annotations

import os
import sys
import asyncio
from typing import Any

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("[ASGI] 设置 WindowsProactorEventLoopPolicy")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testmanager.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter


django_asgi_app: Any = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ChannelNameRouter
from test_ui_app.middleware import TokenAuthMiddlewareStack
import test_ui_app.routing as test_ui_routing
import testmanager_app.routing as testmanager_routing
import core.routing as core_routing


class MCPLifespanMiddleware:
    """
    MCP Lifespan 中间件
    
    处理 ASGI lifespan 事件，在应用启动/关闭时管理 MCP 连接
    """
    
    def __init__(self, app: Any) -> None:
        self.app = app
        self._mcp_initialized = False
    
    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            await self.app(scope, receive, send)
    
    async def _handle_lifespan(self, scope: Any, receive: Any, send: Any) -> None:
        message = await receive()
        
        if message["type"] == "lifespan.startup":
            try:
                from core.agents.capability.mcp_lifespan import (
                    global_mcp_manager,
                    load_servers_from_settings
                )
                
                load_servers_from_settings()
                await global_mcp_manager.initialize()
                self._mcp_initialized = True
                
                await send({"type": "lifespan.startup.complete"})
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"[ASGI] MCP startup failed: {e}", exc_info=True)
                await send({"type": "lifespan.startup.failed", "message": str(e)})
        
        elif message["type"] == "lifespan.shutdown":
            try:
                if self._mcp_initialized:
                    from core.agents.capability.mcp_lifespan import global_mcp_manager
                    await global_mcp_manager.shutdown()
                
                await send({"type": "lifespan.shutdown.complete"})
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"[ASGI] MCP shutdown failed: {e}", exc_info=True)
                await send({"type": "lifespan.shutdown.failed", "message": str(e)})


application = MCPLifespanMiddleware(
    ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": TokenAuthMiddlewareStack(
            URLRouter(
                test_ui_routing.websocket_urlpatterns + testmanager_routing.websocket_urlpatterns + core_routing.websocket_urlpatterns
            )
        ),
    })
)
