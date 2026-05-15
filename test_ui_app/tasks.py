"""
Celery任务定义
"""
from __future__ import annotations
import logging
import asyncio
import sys
from typing import Any, cast
from celery import shared_task

from core.task_events import publish
from .execution.execution_manager import ExecutionManager

logger = logging.getLogger(__name__)

logger.debug(
    "模块加载时的事件循环策略: policy=%s, sys_platform=%s",
    asyncio.get_event_loop_policy().__class__.__name__,
    sys.platform,
)


@shared_task(bind=True, name='test_ui_app.execute_ui_test_task')
def execute_ui_test_task(
    self: Any,
    script_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    异步执行UI测试任务（自动创建执行记录）
    
    Args:
        self: Celery任务实例（bind=True时自动传入）
        script_id: 脚本ID
        user_id: 用户ID（可选）
        
    Returns:
        dict[str, Any]: 执行结果
    """
    script_id = int(script_id)
    if user_id is not None:
        user_id = int(user_id)
    
    try:
        manager = ExecutionManager()
        result = cast(dict[str, Any], asyncio.run(manager.execute(script_id=script_id, user_id=user_id)))
        publish(
            self.request.id,
            'test_ui_app.execute_ui_test_task',
            'success',
            user_id=str(user_id) if user_id else None,
        )
        return result
    except Exception as e:
        logger.error(f"Celery任务执行失败: script_id={script_id}, 错误: {str(e)}")
        publish(
            self.request.id,
            'test_ui_app.execute_ui_test_task',
            'failed',
            user_id=str(user_id) if user_id else None,
            error=str(e)[:500],
        )
        raise


@shared_task(bind=True, name='test_ui_app.execute_ui_test_with_execution_task')
def execute_ui_test_with_execution_task(
    self: Any,
    script_id: int,
    execution_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    异步执行UI测试任务（使用已创建的执行记录）
    
    Args:
        self: Celery任务实例（bind=True时自动传入）
        script_id: 脚本ID
        execution_id: 已创建的执行记录ID
        user_id: 用户ID（可选）
        
    Returns:
        dict[str, Any]: 执行结果
    """
    script_id = int(script_id)
    execution_id = int(execution_id)
    if user_id is not None:
        user_id = int(user_id)
    
    try:
        manager = ExecutionManager()
        result = cast(dict[str, Any], asyncio.run(
            manager.execute_with_execution(
                script_id=script_id,
                execution_id=execution_id,
                user_id=user_id
            )
        ))
        publish(
            self.request.id,
            'test_ui_app.execute_ui_test_with_execution_task',
            'success',
            user_id=str(user_id) if user_id else None,
        )
        return result
    except Exception as e:
        logger.error(f"Celery任务执行失败: script_id={script_id}, execution_id={execution_id}, 错误: {str(e)}")
        publish(
            self.request.id,
            'test_ui_app.execute_ui_test_with_execution_task',
            'failed',
            user_id=str(user_id) if user_id else None,
            error=str(e)[:500],
        )
        try:
            from .models import UITestExecution
            from django.utils import timezone
            execution = UITestExecution.objects.get(id=execution_id)
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            if execution.started_at:
                execution.duration = (timezone.now() - execution.started_at).total_seconds()
            execution.save()
        except Exception as update_error:
            logger.error(f"更新执行记录失败: {str(update_error)}")
        raise

