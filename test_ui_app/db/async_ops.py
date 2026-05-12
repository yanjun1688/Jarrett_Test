from __future__ import annotations
from typing import Optional
from django.utils import timezone
from ..models import UITestScript, UITestExecution

async def get_script_async(script_id: int) -> UITestScript:
    return await UITestScript.objects.aget(id=script_id)

async def create_execution_async(script: UITestScript, user_id: Optional[int] = None) -> UITestExecution:
    return await UITestExecution.objects.acreate(
        script=script,
        executed_by_id=user_id,
        status='running',
        started_at=timezone.now(),
    )

async def get_execution_async(execution_id: int) -> UITestExecution:
    return await UITestExecution.objects.aget(id=execution_id)

async def save_execution_async(execution: UITestExecution) -> None:
    await execution.asave()

async def mark_execution_failed_async(execution: UITestExecution, error_msg: str) -> None:
    execution.status = 'failed'
    completed_at = timezone.now()
    execution.completed_at = completed_at
    execution.error_message = error_msg
    started_at = execution.started_at
    if started_at:
        execution.duration = (completed_at - started_at).total_seconds()
    await execution.asave()