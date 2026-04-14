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

# 【关键修复】在Windows上强制设置ProactorEventLoopPolicy
# 这必须在导入任何使用asyncio的模块之前设置
if sys.platform == 'win32':
    print(f"[Celery] Windows平台检测，强制设置事件循环策略...")
    print(f"[Celery] 当前策略: {asyncio.get_event_loop_policy().__class__.__name__}")
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print(f"[Celery] [OK] 已设置为: {asyncio.get_event_loop_policy().__class__.__name__}")

# 设置默认Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')

app = Celery('testmanager')

# 从Django settings中读取配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 【关键修复】在worker初始化时设置事件循环策略（使用 Celery 5.x 的信号系统）
from celery.signals import worker_init

@worker_init.connect
def on_worker_init_handler(sender: Any | None = None, **kwargs: Any) -> None:
    """Worker进程初始化时的信号处理"""
    import asyncio
    import sys
    if sys.platform == 'win32':
        print(f"[Celery-Worker] Worker进程初始化，设置事件循环策略...")
        print(f"[Celery-Worker] 当前策略: {asyncio.get_event_loop_policy().__class__.__name__}")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print(f"[Celery-Worker] [OK] 已设置为: {asyncio.get_event_loop_policy().__class__.__name__}")

# 自动发现任务 - 使用延迟加载，避免避免在Django web进程启动时阻塞
# autodiscover_tasks()会在需要时才真正导入任务模块
# 传递lambda延迟获取INSTALLED_APPS，避免过早初始化Django
app.autodiscover_tasks(lambda: __import__('django.conf', fromlist=['settings']).settings.INSTALLED_APPS)

@app.task(bind=True, ignore_result=True)
def debug_task(self: Any) -> None:
    print(f'Request: {self.request!r}')

