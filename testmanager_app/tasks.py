"""
Celery 任务定义 - 请求集合后台执行

DEPRECATED: 2026-04-15
该模块已废弃，压测功能已迁移到 WebSocket 实时推送
保留原因：兼容现有代码，观察期后删除

提供请求集合的异步执行能力，避免 HTTP 请求超时，
支持任务状态查询和进度跟踪。
"""
# pyright: reportAttributeAccessIssue=false
from __future__ import annotations
import warnings
import logging
import sys
import asyncio
from typing import Any

from celery import shared_task
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)

# 模块级废弃警告
warnings.warn(
    "tasks module is deprecated. Pressure test functionality has been moved to WebSocket.",
    DeprecationWarning,
    stacklevel=2
)


@shared_task(bind=True, name='testmanager_app.execute_collection')
def execute_collection_task(
    self: Any,
    collection_id: int,
    execution_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    后台执行请求集合任务
    
    DEPRECATED: 2026-04-15
    请使用 WebSocket 压测功能替代
    保留原因：兼容现有代码，观察期后删除
    
    Args:
        self: Celery 任务实例（bind=True 时自动传入）
        collection_id: 请求集合 ID
        execution_id: CollectionExecution 记录 ID（预先创建）
        user_id: 执行用户 ID（可选）
    
    Returns:
        dict[str, Any]: 执行结果摘要
    """
    warnings.warn(
        "execute_collection_task is deprecated. Use WebSocket pressure test instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from testmanager_app.models import (
        RequestCollection, CollectionExecution, CollectionRequest
    )
    from testmanager_app.services.strategy.collection_execution_strategies import (
        CollectionExecutionStrategyFactory
    )
    from django.contrib.auth.models import User
    
    logger.info(f"[Celery Task] Starting collection execution: "
                f"collection_id={collection_id}, execution_id={execution_id}, task_id={self.request.id}")
    
    try:
        collection = RequestCollection.objects.prefetch_related(
            'collection_requests__api_request'
        ).get(pk=collection_id)
        
        collection_exec = CollectionExecution.objects.get(pk=execution_id)
        
        user = None
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found, executing as anonymous")
        
        collection_exec.status = 'running'
        collection_exec.save(update_fields=['status'])
        
        collection_requests = list(
            collection.collection_requests.select_related('api_request')
            .order_by('order_index')
        )
        
        execution_mode = collection.execution_mode
        started_at = timezone.now()
        
        strategy = CollectionExecutionStrategyFactory.get_strategy(execution_mode)
        
        # 在 Celery worker 中执行请求
        # 三种模式都使用统一的 execute_in_worker 方法
        # - 并发：asyncio.run() + asyncio.gather() 同时发起
        # - 顺序：asyncio.run() + 循环顺序执行，支持失败即停
        # - 链式：纯同步执行（httpx.Client），支持变量传递
        context: dict[str, Any] | None = {} if execution_mode == 'chain' else None
        executions = strategy.execute_in_worker(
            collection_requests,
            user,
            collection_exec,
            context
        )
        
        # 更新统计信息
        finished_at = timezone.now()
        duration = finished_at - started_at
        
        passed_count = sum(1 for e in executions if getattr(e, 'status', None) == 'passed' or (isinstance(e, dict) and e.get('success', False)))
        failed_count = len(executions) - passed_count
        
        # 构建详细执行日志
        detail_logs = []
        detail_logs.append(f"========== 请求集合执行报告 ==========")
        detail_logs.append(f"集合名称: {collection.name}")
        detail_logs.append(f"执行模式: {execution_mode}")
        detail_logs.append(f"开始时间: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        detail_logs.append(f"结束时间: {finished_at.strftime('%Y-%m-%d %H:%M:%S')}")
        detail_logs.append(f"执行时长: {duration.total_seconds():.2f} 秒")
        detail_logs.append(f"")
        detail_logs.append(f"========== 执行统计 ==========")
        detail_logs.append(f"总请求数: {len(executions)}")
        detail_logs.append(f"通过: {passed_count}")
        detail_logs.append(f"失败: {failed_count}")
        detail_logs.append(f"")
        detail_logs.append(f"========== 请求详情 ==========")
        
        for idx, execution in enumerate(executions, 1):
            is_dict = isinstance(execution, dict)
            status = getattr(execution, 'status', None) if not is_dict else ('passed' if execution.get('success', False) else 'failed')
            status_icon = "✅" if status == 'passed' else "❌"
            
            if is_dict:
                detail_logs.append(f"")
                detail_logs.append(f"--- 请求 {idx}/{len(executions)} {status_icon} ---")
                detail_logs.append(f"状态: {status}")
                detail_logs.append(f"结果: {execution.get('error', '执行完成')}")
            else:
                api_request = getattr(execution, 'api_request', None)
                detail_logs.append(f"")
                detail_logs.append(f"--- 请求 {idx}/{len(executions)} {status_icon} ---")
                detail_logs.append(f"名称: {api_request.name if api_request else 'N/A'}")
                detail_logs.append(f"URL: {api_request.url if api_request else 'N/A'}")
                detail_logs.append(f"方法: {api_request.method if api_request else 'N/A'}")
                detail_logs.append(f"状态: {status}")
                detail_logs.append(f"结果: {getattr(execution, 'actual_result', None) or 'N/A'}")
                
                response_data = getattr(execution, 'api_response_data', None)
                if response_data:
                    if isinstance(response_data, dict):
                        if response_data.get('response_status'):
                            detail_logs.append(f"HTTP状态码: {response_data['response_status']}")
                        if response_data.get('response_time'):
                            detail_logs.append(f"响应时间: {response_data['response_time']:.3f}s")
                        if response_data.get('error_message'):
                            detail_logs.append(f"错误信息: {response_data['error_message']}")
                        if response_data.get('assertions'):
                            detail_logs.append(f"断言结果:")
                            for assertion in response_data['assertions']:
                                a_status = "✅" if assertion.get('passed') else "❌"
                                detail_logs.append(f"  {a_status} {assertion.get('assertion_type', 'unknown')}: "
                                                 f"期望={assertion.get('expected_value')}, 实际={assertion.get('actual_value')}")
        
        detail_logs.append(f"")
        detail_logs.append(f"========== 执行结束 ==========")
        
        collection_exec.status = 'success' if failed_count == 0 else 'failed'
        collection_exec.finished_at = finished_at
        collection_exec.duration = duration
        collection_exec.passed_requests = passed_count
        collection_exec.failed_requests = failed_count
        collection_exec.output = "\n".join(detail_logs)
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


def _update_execution_error(execution_id: int, error_message: str) -> None:
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


