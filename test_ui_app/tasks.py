"""
Celery任务定义
"""
import logging
import asyncio
import sys
import json, time
from celery import shared_task

from .execution.execution_manager import ExecutionManager

logger = logging.getLogger(__name__)

# 【关键修复】在Windows上确保使用ProactorEventLoopPolicy
# 必须在模块加载时就设置，因为Celery worker可能使用系统Python启动
if sys.platform == 'win32':
    current_policy = asyncio.get_event_loop_policy().__class__.__name__
    if 'Selector' in current_policy:
        logger.warning(f"检测到错误的事件循环策略: {current_policy}，正在修复为ProactorEventLoopPolicy")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info(f"已设置事件循环策略为: {asyncio.get_event_loop_policy().__class__.__name__}")

# #region agent log
# 在模块加载时立即记录事件循环策略
try:
    log_path = r'd:\Project\JTest\.cursor\debug.log'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'id': 'log_000',
            'timestamp': time.time() * 1000,
            'location': 'tasks.py:15',
            'message': '模块加载时的事件循环策略',
            'data': {
                'policy': asyncio.get_event_loop_policy().__class__.__name__,
                'sys_platform': sys.platform
            },
            'sessionId': 'debug-session',
                    'runId': 'post-fix',
            'hypothesisId': 'A'
        }) + '\n')
except:
    pass
# #endregion

# Windows上使用默认的ProactorEventLoopPolicy
# Playwright需要Proactor才能创建子进程，不要设置Selector！


@shared_task(bind=True, name='test_ui_app.execute_ui_test_task')
def execute_ui_test_task(self, script_id, user_id=None):
    """
    异步执行UI测试任务（自动创建执行记录）
    
    Args:
        self: Celery任务实例（bind=True时自动传入）
        script_id: 脚本ID
        user_id: 用户ID（可选）
        
    Returns:
        Dict: 执行结果
    """
    # 确保script_id是整数类型
    script_id = int(script_id)
    if user_id is not None:
        user_id = int(user_id)
    
    try:
        # 创建事件循环（使用默认策略）
        # Windows上默认是ProactorEventLoopPolicy，Playwright需要
        if sys.platform == 'win32':
            current_policy = asyncio.get_event_loop_policy().__class__.__name__
            if 'Selector' in current_policy:
                logger.warning(f"任务执行前检测到错误的事件循环策略: {current_policy}")
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            manager = ExecutionManager()
            
            # 直接调用ExecutionManager.execute（它会统一创建执行记录）
            result = loop.run_until_complete(
                manager.execute(script_id=script_id, user_id=user_id)
            )
            
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Celery任务执行失败: script_id={script_id}, 错误: {str(e)}")
        raise


@shared_task(bind=True, name='test_ui_app.execute_ui_test_with_execution_task')
def execute_ui_test_with_execution_task(self, script_id, execution_id, user_id=None):
    """
    异步执行UI测试任务（使用已创建的执行记录）
    
    Args:
        self: Celery任务实例（bind=True时自动传入）
        script_id: 脚本ID
        execution_id: 已创建的执行记录ID
        user_id: 用户ID（可选）
        
    Returns:
        Dict: 执行结果
    """
    script_id = int(script_id)
    execution_id = int(execution_id)
    if user_id is not None:
        user_id = int(user_id)
    
    try:
        # Windows 上确保使用 ProactorEventLoopPolicy
        if sys.platform == 'win32':
            current_policy = asyncio.get_event_loop_policy().__class__.__name__
            if 'Selector' in current_policy:
                logger.warning(f"任务执行前检测到错误的事件循环策略: {current_policy}")
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            manager = ExecutionManager()
            
            # 调用 execute_with_execution，使用已创建的执行记录
            result = loop.run_until_complete(
                manager.execute_with_execution(
                    script_id=script_id,
                    execution_id=execution_id,
                    user_id=user_id
                )
            )
            
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Celery任务执行失败: script_id={script_id}, execution_id={execution_id}, 错误: {str(e)}")
        # 更新执行记录为失败状态
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

