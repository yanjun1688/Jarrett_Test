"""
Celery 任务定义 - 请求集合后台执行

提供请求集合的异步执行能力，避免 HTTP 请求超时，
支持任务状态查询和进度跟踪。
"""
import logging
import sys
import asyncio

from celery import shared_task
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='testmanager_app.execute_collection')
def execute_collection_task(self, collection_id: int, execution_id: int, user_id: int = None):
    """
    后台执行请求集合任务
    
    Args:
        self: Celery 任务实例（bind=True 时自动传入）
        collection_id: 请求集合 ID
        execution_id: CollectionExecution 记录 ID（预先创建）
        user_id: 执行用户 ID（可选）
    
    Returns:
        dict: 执行结果摘要
    """
    from testmanager_app.models import (
        RequestCollection, CollectionExecution, CollectionRequest
    )
    from testmanager_app.collection_execution_strategies import (
        CollectionExecutionStrategyFactory
    )
    from django.contrib.auth.models import User
    
    logger.info(f"[Celery Task] Starting collection execution: "
                f"collection_id={collection_id}, execution_id={execution_id}, task_id={self.request.id}")
    
    try:
        # 获取集合和执行记录
        collection = RequestCollection.objects.prefetch_related(
            'collection_requests__api_request'
        ).get(pk=collection_id)
        
        collection_exec = CollectionExecution.objects.get(pk=execution_id)
        
        # 获取用户对象
        user = None
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found, executing as anonymous")
        
        # 更新状态为运行中
        collection_exec.status = 'running'
        collection_exec.save(update_fields=['status'])
        
        # 获取请求列表
        collection_requests = list(
            collection.collection_requests.select_related('api_request')
            .order_by('order_index')
        )
        
        execution_mode = collection.execution_mode
        started_at = timezone.now()
        
        # 获取执行策略
        strategy = CollectionExecutionStrategyFactory.get_strategy(execution_mode)
        
        # 执行请求
        if execution_mode == 'chain':
            context = {}
            # 链式执行直接调用同步方法
            executions = strategy._execute_sync(
                collection_requests,
                user,
                collection_exec,
                context
            )
        else:
            # 并发和顺序执行使用异步方式
            context = None
            executions = async_to_sync(strategy.execute)(
                collection_requests,
                user,
                collection_exec,
                context
            )
        
        # 更新统计信息
        finished_at = timezone.now()
        duration = finished_at - started_at
        
        passed_count = sum(1 for e in executions if e.status == 'passed')
        failed_count = len(executions) - passed_count
        
        collection_exec.status = 'success' if failed_count == 0 else 'failed'
        collection_exec.finished_at = finished_at
        collection_exec.duration = duration
        collection_exec.passed_requests = passed_count
        collection_exec.failed_requests = failed_count
        collection_exec.output = (
            f"Mode: {execution_mode}, Total: {len(executions)}, "
            f"Passed: {passed_count}, Failed: {failed_count}"
        )
        collection_exec.save()
        
        logger.info(
            f"[Celery Task] Collection execution completed: "
            f"task_id={self.request.id}, mode={execution_mode}, "
            f"total={len(executions)}, passed={passed_count}, failed={failed_count}"
        )
        
        return {
            'success': True,
            'execution_id': execution_id,
            'collection_id': collection_id,
            'status': collection_exec.status,
            'total_requests': len(executions),
            'passed_requests': passed_count,
            'failed_requests': failed_count,
            'duration_seconds': duration.total_seconds() if duration else None,
        }
        
    except RequestCollection.DoesNotExist:
        logger.error(f"[Celery Task] Collection {collection_id} not found")
        _update_execution_error(execution_id, f"Collection {collection_id} not found")
        return {
            'success': False,
            'error': f"Collection {collection_id} not found",
            'execution_id': execution_id,
        }
        
    except CollectionExecution.DoesNotExist:
        logger.error(f"[Celery Task] Execution record {execution_id} not found")
        return {
            'success': False,
            'error': f"Execution record {execution_id} not found",
        }
        
    except Exception as e:
        logger.error(f"[Celery Task] Execution failed: {str(e)}", exc_info=True)
        _update_execution_error(execution_id, str(e))
        return {
            'success': False,
            'error': str(e),
            'execution_id': execution_id,
        }


def _update_execution_error(execution_id: int, error_message: str):
    """更新执行记录为错误状态"""
    try:
        from testmanager_app.models import CollectionExecution
        collection_exec = CollectionExecution.objects.get(pk=execution_id)
        collection_exec.status = 'failed'
        collection_exec.output = f"执行失败: {error_message}"
        collection_exec.finished_at = timezone.now()
        collection_exec.save()
    except Exception as e:
        logger.error(f"Failed to update execution error status: {e}")


def get_task_status(task_id: str) -> dict:
    """
    获取 Celery 任务状态
    
    Args:
        task_id: Celery 任务 ID
    
    Returns:
        dict: 任务状态信息
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    
    response = {
        'task_id': task_id,
        'status': result.status,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
    }
    
    if result.ready():
        if result.successful():
            response['result'] = result.result
        else:
            response['error'] = str(result.result) if result.result else 'Unknown error'
    
    return response
