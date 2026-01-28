from asgiref.sync import sync_to_async
from django.utils import timezone
from ..models import UITestScript, UITestExecution

async def get_script_async(script_id: int) -> UITestScript:
    def _get():
        return UITestScript.objects.select_related("project", "created_by").get(id=script_id)
    return await sync_to_async(_get, thread_sensitive=True)()

async def create_execution_async(script: UITestScript, user_id: int = None) -> UITestExecution:
    def _create():
        return UITestExecution.objects.create(
            script=script,
            executed_by_id=user_id,
            status='running',
            started_at=timezone.now(),
        )
    return await sync_to_async(_create, thread_sensitive=True)()

async def get_execution_async(execution_id: int) -> UITestExecution:
    def _get():
        return UITestExecution.objects.get(id=execution_id)
    return await sync_to_async(_get, thread_sensitive=True)()

async def save_execution_async(execution: UITestExecution):
    def _save():
        execution.save()
    await sync_to_async(_save, thread_sensitive=True)()

async def mark_execution_failed_async(execution: UITestExecution, error_msg: str):
    def _update():
        execution.status = 'failed'
        execution.completed_at = timezone.now()
        execution.error_message = error_msg
        if execution.started_at:
            execution.duration = (execution.completed_at - execution.started_at).total_seconds()
        execution.save()
    await sync_to_async(_update, thread_sensitive=True)()
