from __future__ import annotations

import sys
import asyncio
from typing import Any

if sys.platform == 'win32':
    # 显式设置 ProactorEventLoopPolicy，确保 Playwright 在所有 Windows 进程中可用
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("显式设置 WindowsProactorEventLoopPolicy (from __init__.py)")

# Configure pymysql to work with Django
import pymysql
pymysql.install_as_MySQLdb()

# 延迟导入Celery，避免在Django启动时阻塞
# Celery会在worker进程中使用，不需要在web进程中立即初始化
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except Exception as e:
    # 如果Celery导入失败（例如Redis连接问题），不应该阻塞Django启动
    print(f"警告: Celery初始化失败: {e}")
    print("Django将继续启动，但Celery功能可能不可用")
    celery_app = None
    __all__ = tuple()
