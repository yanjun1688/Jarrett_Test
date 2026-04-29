from __future__ import annotations

import sys
import asyncio
from typing import Any, Tuple

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("[__init__] 设置 WindowsProactorEventLoopPolicy (子进程支持)")
    # 强制 UTF-8 编码，解决 emoji 等 Unicode 字符输出问题
    stdout_reconfigure = getattr(sys.stdout, 'reconfigure', None)
    stderr_reconfigure = getattr(sys.stderr, 'reconfigure', None)
    if stdout_reconfigure:
        stdout_reconfigure(encoding='utf-8', errors='replace')
    if stderr_reconfigure:
        stderr_reconfigure(encoding='utf-8', errors='replace')

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
