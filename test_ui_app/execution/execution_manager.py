"""
执行管理器 - 协调整个执行生命周期
"""
import logging
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.conf import settings

from ..models import UITestScript, UITestExecution
from ..validators.script_validator import ScriptValidator, ValidationError
from .action_runner import ActionRunner
from .log_collector import LogCollector

logger = logging.getLogger(__name__)


class ExecutionManager:
    """执行管理器"""

    def __init__(self):
        self.validator = ScriptValidator()
        self.runner = ActionRunner()

    async def execute(self, script_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        执行脚本（完整生命周期，自动创建执行记录）

        Args:
            script_id: 脚本ID
            user_id: 用户ID

        Returns:
            Dict: 执行结果，包含execution_id, status等
        """
        execution = None
        work_dir = None

        try:
            # 1. 获取脚本
            print(f"[UITest] 正在加载脚本 ID: {script_id}", flush=True)
            script = await self._get_script(script_id)
            print(f"[UITest] 脚本加载成功: {script.name}", flush=True)

            # 2. 校验脚本
            actions = script.actions or []
            if not actions:
                raise ValidationError("脚本actions列表为空")

            print(f"[UITest] 开始校验脚本，共 {len(actions)} 个actions", flush=True)
            is_valid, error_msg = self.validator.validate(
                actions=actions,
                browser_type=script.browser_type,
                viewport_width=script.viewport_width,
                viewport_height=script.viewport_height,
                timeout=script.timeout
            )

            if not is_valid:
                raise ValidationError(f"脚本校验失败: {error_msg}")

            print(f"[UITest] 脚本校验通过", flush=True)

            # 3. 创建工作目录
            work_dir = self._create_work_directory()

            # 4. 创建执行记录
            execution = await self._create_execution(script, user_id)
            print(f"[UITest] 执行记录创建成功，ID: {execution.id}", flush=True)

            # 5. 执行核心流程
            return await self._execute_core(script, execution, actions, work_dir)

        except ValidationError as e:
            print(f"[UITest] [ERROR] 脚本校验失败: {str(e)}", flush=True)
            logger.error(f"脚本校验失败: {str(e)}")
            if execution:
                await self._mark_execution_failed(execution, str(e))
            return {
                'success': False,
                'execution_id': execution.id if execution else None,
                'status': 'failed',
                'error': str(e)
            }

        except Exception as e:
            print(f"[UITest] [ERROR] 执行过程中发生错误: {str(e)}", flush=True)
            logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
            if execution:
                await self._mark_execution_failed(execution, str(e))
            return {
                'success': False,
                'execution_id': execution.id if execution else None,
                'status': 'failed',
                'error': str(e)
            }

        finally:
            await self._cleanup_resources(work_dir)

    async def execute_with_execution(
        self, script_id: int, execution_id: int, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行脚本（使用已创建的执行记录）

        Args:
            script_id: 脚本ID
            execution_id: 已创建的执行记录ID
            user_id: 用户ID

        Returns:
            Dict: 执行结果
        """
        execution = None
        work_dir = None

        try:
            # 1. 获取脚本
            print(f"[UITest] 正在加载脚本 ID: {script_id}", flush=True)
            script = await self._get_script(script_id)
            print(f"[UITest] 脚本加载成功: {script.name}", flush=True)

            # 2. 获取已存在的执行记录并更新状态为 running
            execution = await self._get_execution(execution_id)
            await self._update_execution_status(execution, 'running')
            print(f"[UITest] 执行记录状态已更新为 running，ID: {execution.id}", flush=True)

            # 3. 校验脚本
            actions = script.actions or []
            if not actions:
                raise ValidationError("脚本actions列表为空")

            print(f"[UITest] 开始校验脚本，共 {len(actions)} 个actions", flush=True)
            is_valid, error_msg = self.validator.validate(
                actions=actions,
                browser_type=script.browser_type,
                viewport_width=script.viewport_width,
                viewport_height=script.viewport_height,
                timeout=script.timeout
            )

            if not is_valid:
                raise ValidationError(f"脚本校验失败: {error_msg}")

            print(f"[UITest] 脚本校验通过", flush=True)

            # 4. 创建工作目录
            work_dir = self._create_work_directory()

            # 5. 执行核心流程
            return await self._execute_core(script, execution, actions, work_dir)

        except ValidationError as e:
            print(f"[UITest] [ERROR] 脚本校验失败: {str(e)}", flush=True)
            logger.error(f"脚本校验失败: {str(e)}")
            if execution:
                await self._mark_execution_failed(execution, str(e))
            return {
                'success': False,
                'execution_id': execution_id,
                'status': 'failed',
                'error': str(e)
            }

        except Exception as e:
            print(f"[UITest] [ERROR] 执行过程中发生错误: {str(e)}", flush=True)
            logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
            if execution:
                await self._mark_execution_failed(execution, str(e))
            return {
                'success': False,
                'execution_id': execution_id,
                'status': 'failed',
                'error': str(e)
            }

        finally:
            await self._cleanup_resources(work_dir)

    async def _execute_core(
        self, script: UITestScript, execution: UITestExecution,
        actions: list, work_dir: Path
    ) -> Dict[str, Any]:
        """
        执行核心流程（公共逻辑提取）

        Args:
            script: 脚本对象
            execution: 执行记录
            actions: 动作列表
            work_dir: 工作目录

        Returns:
            Dict: 执行结果
        """
        # 1. 初始化日志采集器并记录执行开始
        log_collector = LogCollector(execution)
        await log_collector.log_execution_start(script, len(actions))

        # 2. 初始化浏览器
        print(f"[UITest] 正在初始化浏览器...", flush=True)
        await self.runner.initialize(
            browser_type=script.browser_type,
            headless=script.headless,
            viewport_width=script.viewport_width,
            viewport_height=script.viewport_height,
            timeout=script.timeout
        )
        log_collector._add_log_line("浏览器初始化成功")

        # 3. 执行actions
        print(f"[UITest] 开始执行 {len(actions)} 个actions...", flush=True)
        action_results = await self.runner.execute_actions(actions)
        print(f"[UITest] Actions执行完成", flush=True)

        # 4. 采集日志
        for action, result in zip(actions, action_results):
            await log_collector.collect_action_result(action, result)

        await log_collector.update_execution(action_results)

        # 5. 返回结果
        execution = await self._get_execution(execution.id)
        print(f"[UITest] 执行完成，最终状态: {execution.status}", flush=True)
        return {
            'success': execution.status == 'passed',
            'execution_id': execution.id,
            'status': execution.status,
            'message': '执行完成'
        }

    async def _cleanup_resources(self, work_dir: Optional[Path]):
        """清理资源"""
        try:
            print(f"[UITest] 清理资源...", flush=True)
            # 清理工作目录
            if work_dir:
                await self._cleanup_work_directory(work_dir)
                print(f"[UITest] 工作目录已清理", flush=True)

            # 清理浏览器资源
            await self.runner.cleanup()
            print(f"[UITest] 浏览器资源已清理", flush=True)
            print(f"[UITest] 资源清理完成", flush=True)
        except Exception as e:
            print(f"[UITest] [ERROR] 资源清理失败: {str(e)}", flush=True)
            logger.error(f"资源清理失败: {str(e)}")

    async def _update_execution_status(self, execution: UITestExecution, status: str):
        """更新执行记录状态"""
        def _update():
            execution.status = status
            if status == 'running' and not execution.started_at:
                execution.started_at = timezone.now()
            execution.save()

        await sync_to_async(_update, thread_sensitive=True)()

    async def _get_script(self, script_id: int) -> UITestScript:
        """获取脚本对象"""
        def _get():
            return UITestScript.objects.get(id=script_id)

        return await sync_to_async(_get, thread_sensitive=True)()

    async def _create_execution(self, script: UITestScript, user_id: Optional[int]) -> UITestExecution:
        """创建执行记录"""
        def _create():
            from django.contrib.auth.models import User
            executed_by = None
            if user_id:
                try:
                    executed_by = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass

            return UITestExecution.objects.create(
                script=script,
                executed_by=executed_by,
                status='running',
                started_at=timezone.now()
            )

        return await sync_to_async(_create, thread_sensitive=True)()

    async def _get_execution(self, execution_id: int) -> UITestExecution:
        """获取执行记录"""
        def _get():
            return UITestExecution.objects.get(id=execution_id)

        return await sync_to_async(_get, thread_sensitive=True)()

    async def _mark_execution_failed(self, execution: UITestExecution, error_msg: str):
        """标记执行失败"""
        def _mark():
            execution.status = 'failed'
            execution.error_message = error_msg
            execution.completed_at = timezone.now()
            if execution.started_at:
                execution.duration = (
                    timezone.now() - execution.started_at
                ).total_seconds()
            execution.save()

        await sync_to_async(_mark, thread_sensitive=True)()

    def _create_work_directory(self) -> Path:
        """创建工作目录"""
        base_dir = Path(settings.MEDIA_ROOT) / "ui_test_work" if hasattr(settings, 'MEDIA_ROOT') else Path(tempfile.gettempdir()) / "ui_test_work"
        base_dir.mkdir(parents=True, exist_ok=True)
        work_dir = tempfile.mkdtemp(prefix="execution_", dir=str(base_dir))
        return Path(work_dir)

    async def _cleanup_work_directory(self, work_dir: Path):
        """清理工作目录"""
        def _cleanup():
            if work_dir and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

        await sync_to_async(_cleanup, thread_sensitive=True)()
