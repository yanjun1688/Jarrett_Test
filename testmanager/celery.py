"""
Celery配置文件
"""
from __future__ import annotations

import os
import asyncio
import sys
from typing import Any

from celery import Celery
from celery.signals import worker_init

if sys.platform == 'win32':
    print(f"[Celery] Windows平台检测，强制设置事件循环策略...")
    print(f"[Celery] 当前策略: {asyncio.get_event_loop_policy().__class__.__name__}")
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print(f"[Celery] [OK] 已设置为: {asyncio.get_event_loop_policy().__class__.__name__}")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')

app = Celery('testmanager')

app.config_from_object('django.conf:settings', namespace='CELERY')

@worker_init.connect  # type: ignore[untyped-decorator]
def on_worker_init_handler(sender: Any | None = None, **kwargs: Any) -> None:
    """Worker进程初始化时的信号处理"""
    import asyncio
    import sys
    if sys.platform == 'win32':
        print(f"[Celery-Worker] Worker进程初始化，设置事件循环策略...")
        print(f"[Celery-Worker] 当前策略: {asyncio.get_event_loop_policy().__class__.__name__}")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print(f"[Celery-Worker] [OK] 已设置为: {asyncio.get_event_loop_policy().__class__.__name__}")

app.autodiscover_tasks(lambda: __import__('django.conf', fromlist=['settings']).settings.INSTALLED_APPS)

@app.task(bind=True, ignore_result=True)  # type: ignore[untyped-decorator]
def debug_task(self: Any) -> None:
    print(f'Request: {self.request!r}')

