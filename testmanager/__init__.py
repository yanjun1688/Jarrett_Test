from __future__ import annotations

import sys
import asyncio
from typing import Any, Tuple

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("显式设置 WindowsProactorEventLoopPolicy (from __init__.py)")

import pymysql
pymysql.install_as_MySQLdb()

__all__: Tuple[str, ...]

try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except Exception as e:
    print(f"警告: Celery初始化失败: {e}")
    print("Django将继续启动，但Celery功能可能不可用")
    celery_app = None
    __all__ = tuple()
