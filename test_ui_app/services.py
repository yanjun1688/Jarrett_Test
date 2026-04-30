"""
UI测试服务层

注意：Django 5+ 中禁止在 async 函数里直接使用同步 ORM，
这里按照 testmanager_app 里现有模式，统一用 sync_to_async 包装 ORM 操作。
"""
from __future__ import annotations

import asyncio
import sys
import base64
from typing import Dict, List, Optional, Any, Union, cast, Callable, Literal

from asgiref.sync import sync_to_async, async_to_sync
from django.utils import timezone
from django.db import transaction
from django.db.models import QuerySet, Model

from .models import (
    UITestScript,
    UITestExecution,
)
from .playwright_engine import PlaywrightEngine
from .execution.execution_manager import ExecutionManager
from .converters.action_converter import convert_to_actions
import logging

logger = logging.getLogger(__name__)


def get_python_executable() -> str:
    """
    获取当前虚拟环境的Python可执行文件路径
    
    使用 sys.executable 确保始终使用当前Django应用运行的Python解释器，
    这样可以保证子脚本能够访问虚拟环境中安装的所有包（如playwright）。
    
    Returns:
        str: Python可执行文件的完整路径
    """
    return sys.executable


class UITestService:
    """UI测试服务"""

    def __init__(self) -> None:
        self.engine: PlaywrightEngine = PlaywrightEngine()

    async def _get_script(self, script_id: int) -> UITestScript:
        """异步获取脚本对象（包装同步 ORM）"""
        def _get() -> UITestScript:
            # 预加载关联，避免在异步上下文中再次触发数据库查询
            return (
                UITestScript.objects.select_related("project", "created_by")
                .get(id=script_id)
            )

        return await sync_to_async(_get, thread_sensitive=True)()

    async def _create_execution(self, script: UITestScript, user_id: int | None) -> UITestExecution:
        """异步创建执行记录"""
        def _create() -> UITestExecution:
            return UITestExecution.objects.create(
                script=script,
                executed_by_id=user_id,
                status="running",
                started_at=timezone.now(),
            )

        return await sync_to_async(_create, thread_sensitive=True)()

    async def _save_execution(self, execution: UITestExecution) -> None:
        """异步保存执行记录"""
        def _save() -> None:
            execution.save()

        await sync_to_async(_save, thread_sensitive=True)()

    def execute_script_sync(self, script_id: int, user_id: int | None = None) -> Dict[str, Any]:
        """
        提交Celery任务执行测试脚本（用于 Django 视图）
        
        注意：
        - 此方法只负责提交Celery任务，不创建执行记录
        - 执行记录由ExecutionManager在执行时统一创建
        - 立即返回task_id，实际执行在后台进行
        """
        from .tasks import execute_ui_test_task
        task_func: Any = execute_ui_test_task
        
        try:
            # 提交Celery任务异步执行
            # 如果user_id为None，不传递该参数，让任务函数使用默认值
            if user_id is not None:
                task = task_func.delay(script_id, user_id=user_id)
            else:
                task = task_func.delay(script_id)
            # Removed verbose logging
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '任务已提交，正在执行中'
            }
            
        except Exception as e:
            logger.error(f"[ExecuteScriptSync] 提交任务失败 ID={script_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def execute_script_with_execution(
        self, script_id: int, execution_id: int, user_id: int | None = None
    ) -> Dict[str, Any]:
        """
        提交Celery任务执行测试脚本（使用已创建的执行记录）
        
        Args:
            script_id: 脚本ID
            execution_id: 已创建的执行记录ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 包含 task_id 的结果
        """
        from .tasks import execute_ui_test_with_execution_task
        task_func: Any = execute_ui_test_with_execution_task
        
        try:
            task = task_func.delay(
                script_id, execution_id, user_id=user_id
            )
            
            return {
                'success': True,
                'task_id': task.id,
                'execution_id': execution_id,
                'message': '任务已提交，正在执行中'
            }
            
        except Exception as e:
            logger.error(f"[ExecuteScriptWithExecution] 提交任务失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }
    

class ScriptBuilder:
    """脚本构建器（用于录制和手动构建脚本）"""
    
    @staticmethod
    def create_script_from_steps(
        name: str,
        steps_data: List[Dict[str, Any]],
        project_id: int | None = None,
        user_id: int | None = None,
        **kwargs: Any
    ) -> UITestScript:
        """
        从步骤数据创建脚本（转换为actions格式）
        
        注意：steps_data可以是steps格式或actions格式
        """
        # 检查是否已经是actions格式（包含id、order、type等字段）
        is_actions_format = len(steps_data) > 0 and all(
            'type' in step or 'id' in step
            for step in steps_data
        )
        
        if is_actions_format:
            # 已经是actions格式，直接使用
            logger.info(f"[ScriptBuilder] 检测到actions格式，直接使用，数量: {len(steps_data)}")
            actions = steps_data
        else:
            # steps格式，需要转换
            logger.info(f"[ScriptBuilder] 检测到steps格式，进行转换，数量: {len(steps_data)}")
            actions = convert_to_actions(steps_data, 'actions')  # 传递'actions'类型，让转换器智能处理
        
        with transaction.atomic():
            script = UITestScript.objects.create(
                name=name,
                project_id=project_id if project_id is not None else None,  # type: ignore[misc]
                created_by_id=user_id,
                actions=actions,
                **kwargs
            )
            script_id: int = getattr(script, 'id', 0)
            
            logger.info(f"[ScriptBuilder] 脚本创建成功: id={script_id}, actions数量={len(actions)}")
            return script

class ElementExtractor(PlaywrightEngine):
    """
    页面元素提取器
    
    使用 Playwright 渲染页面并提取交互元素，
    输出格式兼容现有 PageStructureView 的存储格式。
    """
    
    async def extract_page_elements_async(
        self,
        url: str,
        wait_for_network: bool = True,
        wait_selector: str | None = None,
        wait_timeout: int = 5000,
        headless: bool = True,
        browser_type: str = 'chromium'
    ) -> Dict[str, Any]:
        """
        提取页面交互元素（异步版本）
        
        Args:
            url: 页面URL
            wait_for_network: 是否等待网络空闲
            wait_selector: 等待特定选择器出现
            wait_timeout: 等待超时(毫秒)
            headless: 是否无头模式
            browser_type: 浏览器类型
            
        Returns:
            Dict[str, Any]: 包含 url, title, elements 的字典
        """
        url = self._validate_and_fix_url(url)
        
        try:
            await self.initialize(
                browser_type=browser_type,
                headless=headless,
                viewport_width=1280,
                viewport_height=720,
                timeout=30000
            )
            
            await self._navigate_and_wait(url, wait_for_network, wait_selector, wait_timeout)
            
            if self.page is None:
                raise RuntimeError("页面未初始化")
            title = await self.page.title()
            elements = await self._extract_elements_via_js()
            
            logger.info(f"Extracted {len(elements)} elements from {url}")
            
            return {
                'url': url,
                'title': title,
                'elements': elements
            }
            
        finally:
            await self.cleanup()
    
    extract_page_elements = async_to_sync(extract_page_elements_async)
    
    async def _navigate_and_wait(
        self,
        url: str,
        wait_for_network: bool,
        wait_selector: str | None,
        wait_timeout: int
    ) -> None:
        if self.page is None:
            raise RuntimeError("页面未初始化")
        wait_until: Literal['networkidle', 'domcontentloaded'] = 'networkidle' if wait_for_network else 'domcontentloaded'
        await self.page.goto(url, wait_until=wait_until, timeout=30000)
        
        if wait_selector:
            try:
                await self.page.wait_for_selector(wait_selector, timeout=wait_timeout)
            except Exception as e:
                logger.warning(f"Wait selector timeout: {wait_selector}, {e}")
    
    async def _extract_elements_via_js(self) -> List[Dict[str, Any]]:
        """通过 JavaScript 提取页面交互元素"""
        if self.page is None:
            raise RuntimeError("页面未初始化")
        page = self.page
        js_code = """
        () => {
            const elements = [];
            
            document.querySelectorAll('input, textarea').forEach(el => {
                if (el.offsetParent === null) return;
                
                const type = el.type || 'text';
                if (type === 'hidden' || type === 'submit' || type === 'button' || type === 'image' || type === 'file') {
                    return;
                }
                
                const elem = {
                    type: 'input',
                    tag: el.tagName.toLowerCase(),
                    attributes: {},
                    text: null,
                    selector_hints: []
                };
                
                if (el.placeholder) {
                    elem.attributes.placeholder = el.placeholder;
                    elem.selector_hints.push(`placeholder=${el.placeholder}`);
                }
                if (el.id) {
                    elem.attributes.id = el.id;
                    elem.selector_hints.push(`#${el.id}`);
                }
                if (el.name) {
                    elem.attributes.name = el.name;
                    elem.selector_hints.push(`name=${el.name}`);
                }
                if (el.type) {
                    elem.attributes.type = el.type;
                }
                
                if (!elem.selector_hints.length && el.className) {
                    const cls = el.className.split(' ')[0];
                    if (cls) {
                        elem.selector_hints.push(`.${cls}`);
                        elem.attributes.class = cls;
                    }
                }
                
                if (elem.selector_hints.length > 0) {
                    elements.push(elem);
                }
            });
            
            document.querySelectorAll('button, input[type="submit"], input[type="button"]').forEach(el => {
                if (el.offsetParent === null) return;
                
                const elem = {
                    type: 'button',
                    tag: el.tagName.toLowerCase(),
                    attributes: {},
                    text: null,
                    selector_hints: []
                };
                
                if (el.tagName.toLowerCase() === 'button') {
                    elem.text = el.textContent.trim();
                } else {
                    elem.text = el.value || '';
                }
                
                if (el.id) {
                    elem.attributes.id = el.id;
                    elem.selector_hints.push(`#${el.id}`);
                }
                if (el.name) {
                    elem.attributes.name = el.name;
                }
                if (el.type) {
                    elem.attributes.type = el.type;
                }
                
                if (elem.text) {
                    elem.selector_hints.push(`text=${elem.text}`);
                    elem.selector_hints.push(`value=${elem.text}`);
                }
                
                if (elem.selector_hints.length > 0) {
                    elements.push(elem);
                }
            });
            
            document.querySelectorAll('a').forEach(el => {
                if (el.offsetParent === null) return;
                
                const text = el.textContent.trim();
                if (!text) return;
                
                const elem = {
                    type: 'link',
                    tag: 'a',
                    attributes: {},
                    text: text,
                    selector_hints: [`text=${text}`]
                };
                
                if (el.id) {
                    elem.attributes.id = el.id;
                    elem.selector_hints.push(`#${el.id}`);
                }
                if (el.href) {
                    elem.attributes.href = el.href;
                }
                if (el.className) {
                    const cls = el.className.split(' ')[0];
                    if (cls) {
                        elem.attributes.class = cls;
                        elem.selector_hints.push(`.${cls}`);
                    }
                }
                
                elements.push(elem);
            });
            
            document.querySelectorAll('select').forEach(el => {
                if (el.offsetParent === null) return;
                
                const elem = {
                    type: 'select',
                    tag: 'select',
                    attributes: {},
                    text: null,
                    selector_hints: []
                };
                
                if (el.id) {
                    elem.attributes.id = el.id;
                    elem.selector_hints.push(`#${el.id}`);
                }
                if (el.name) {
                    elem.attributes.name = el.name;
                    elem.selector_hints.push(`name=${el.name}`);
                }
                
                elements.push(elem);
            });
            
            document.querySelectorAll('[role="button"], [onclick]').forEach(el => {
                if (el.offsetParent === null) return;
                if (el.tagName.toLowerCase() in ['button', 'a', 'input']) return;
                
                const text = el.textContent.trim();
                if (!text || text.length > 50) return;
                
                const elem = {
                    type: 'button',
                    tag: el.tagName.toLowerCase(),
                    attributes: {},
                    text: text,
                    selector_hints: [`text=${text}`]
                };
                
                if (el.id) {
                    elem.attributes.id = el.id;
                    elem.selector_hints.push(`#${el.id}`);
                }
                if (el.className) {
                    const cls = el.className.split(' ')[0];
                    if (cls) {
                        elem.attributes.class = cls;
                        elem.selector_hints.push(`.${cls}`);
                    }
                }
                if (el.getAttribute('role')) {
                    elem.attributes.role = el.getAttribute('role');
                }
                
                elements.push(elem);
            });
            
            return elements;
        }
        """
        
        result: List[Dict[str, Any]] = cast(List[Dict[str, Any]], await page.evaluate(js_code))
        return result
