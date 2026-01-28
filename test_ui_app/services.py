"""
UI测试服务层

注意：Django 5+ 中禁止在 async 函数里直接使用同步 ORM，
这里按照 testmanager_app 里现有模式，统一用 sync_to_async 包装 ORM 操作。
"""
import asyncio
import sys
import base64
from typing import Dict, List, Optional, Any

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import transaction

from .models import (
    UITestScript,
    UITestExecution,
)
from .playwright_engine import PlaywrightEngine, create_windows_compatible_event_loop
from .execution.execution_manager import ExecutionManager
from .converters.action_converter import convert_to_actions
import logging

logger = logging.getLogger(__name__)


def get_python_executable():
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

    def __init__(self):
        self.engine = PlaywrightEngine()

    async def _get_script(self, script_id: int) -> UITestScript:
        """异步获取脚本对象（包装同步 ORM）"""
        def _get():
            # 预加载关联，避免在异步上下文中再次触发数据库查询
            return (
                UITestScript.objects.select_related("project", "created_by")
                .get(id=script_id)
            )

        return await sync_to_async(_get, thread_sensitive=True)()

    async def _create_execution(self, script: UITestScript, user_id: Optional[int]) -> UITestExecution:
        """异步创建执行记录"""
        def _create():
            return UITestExecution.objects.create(
                script=script,
                executed_by_id=user_id,
                status="running",
                started_at=timezone.now(),
            )

        return await sync_to_async(_create, thread_sensitive=True)()

    async def _save_execution(self, execution: UITestExecution):
        """异步保存执行记录"""
        def _save():
            execution.save()

        await sync_to_async(_save, thread_sensitive=True)()

    def execute_script_sync(self, script_id: int, user_id: Optional[int] = None) -> Dict:
        """
        提交Celery任务执行测试脚本（用于 Django 视图）
        
        注意：
        - 此方法只负责提交Celery任务，不创建执行记录
        - 执行记录由ExecutionManager在执行时统一创建
        - 立即返回task_id，实际执行在后台进行
        """
        from .tasks import execute_ui_test_task
        
        try:
            # 提交Celery任务异步执行
            # 如果user_id为None，不传递该参数，让任务函数使用默认值
            if user_id is not None:
                task = execute_ui_test_task.delay(script_id, user_id=user_id)
            else:
                task = execute_ui_test_task.delay(script_id)
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
        self, script_id: int, execution_id: int, user_id: Optional[int] = None
    ) -> Dict:
        """
        提交Celery任务执行测试脚本（使用已创建的执行记录）
        
        Args:
            script_id: 脚本ID
            execution_id: 已创建的执行记录ID
            user_id: 用户ID
            
        Returns:
            Dict: 包含 task_id 的结果
        """
        from .tasks import execute_ui_test_with_execution_task
        
        try:
            task = execute_ui_test_with_execution_task.delay(
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
        steps_data: List[Dict],
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **kwargs
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
                project_id=project_id,
                created_by_id=user_id,
                actions=actions,
                **kwargs
            )
            
            logger.info(f"[ScriptBuilder] 脚本创建成功: id={script.id}, actions数量={len(actions)}")
            return script


class PlaywrightService:
    """Playwright页面预览和元素选择服务"""
    
    def __init__(self):
        self.engine = PlaywrightEngine()
    
    async def preview_page(self, url: str, browser_type: str = 'chromium',
                          viewport_width: int = 1280, viewport_height: int = 720) -> Dict[str, Any]:
        """
        预览页面并返回截图
        
        Args:
            url: 要预览的URL
            browser_type: 浏览器类型
            viewport_width: 视口宽度
            viewport_height: 视口高度
            
        Returns:
            Dict: {success, screenshot (base64), url, ...}
        """
        try:
            # 验证并修复URL
            url = self.engine._validate_and_fix_url(url)
            
            # 初始化浏览器
            await self.engine.initialize(
                browser_type=browser_type,
                headless=True,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                timeout=30000
            )
            
            # 导航到URL
            await self.engine.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 截图
            screenshot_bytes = await self.engine.page.screenshot(type='png', full_page=False)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            current_url = self.engine.page.url
            page_title = await self.engine.page.title()
            
            return {
                'success': True,
                'screenshot': f'data:image/png;base64,{screenshot_base64}',
                'url': current_url,
                'title': page_title,
                'viewport_width': viewport_width,
                'viewport_height': viewport_height,
            }
        except Exception as e:
            logger.error(f"预览页面失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # 清理资源
            try:
                await self.engine.cleanup()
            except Exception as cleanup_error:
                logger.error(f"清理资源失败: {str(cleanup_error)}")
    
    def preview_page_sync(self, url: str, browser_type: str = 'chromium',
                         viewport_width: int = 1280, viewport_height: int = 720) -> Dict[str, Any]:
        """同步预览页面（用于Django视图）"""
        loop = create_windows_compatible_event_loop()
        try:
            return loop.run_until_complete(
                self.preview_page(url, browser_type, viewport_width, viewport_height)
            )
        finally:
            loop.close()
    
    async def select_element(self, url: str, x: Optional[int] = None, y: Optional[int] = None,
                            selector: Optional[str] = None, browser_type: str = 'chromium',
                            viewport_width: int = 1280, viewport_height: int = 720) -> Dict[str, Any]:
        """
        根据坐标或选择器获取元素定位信息
        
        Args:
            url: 页面URL
            x: 点击的X坐标
            y: 点击的Y坐标
            selector: 选择器
            browser_type: 浏览器类型
            viewport_width: 视口宽度
            viewport_height: 视口高度
            
        Returns:
            Dict: {success, element_info, locator, candidates: [...]}
        """
        try:
            # 验证并修复URL
            url = self.engine._validate_and_fix_url(url)
            
            # 初始化浏览器
            await self.engine.initialize(
                browser_type=browser_type,
                headless=True,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                timeout=30000
            )
            
            # 导航到URL
            await self.engine.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 根据坐标或选择器获取元素
            element_data = None
            if x is not None and y is not None:
                # 使用坐标获取元素
                element_data = await self.engine.page.evaluate("""
                    (x, y) => {
                        const element = document.elementFromPoint(x, y);
                        if (!element) return null;
                        
                        // 获取元素信息
                        const rect = element.getBoundingClientRect();
                        const tagName = element.tagName.toLowerCase();
                        const id = element.id || '';
                        const className = element.className || '';
                        const name = element.name || '';
                        const textContent = (element.textContent || '').trim().substring(0, 50);
                        const dataTestId = element.getAttribute('data-testid') || '';
                        const role = element.getAttribute('role') || '';
                        const ariaLabel = element.getAttribute('aria-label') || '';
                        const href = element.href || '';
                        const value = element.value || '';
                        
                        // 获取父元素信息
                        let parentInfo = null;
                        if (element.parentElement) {
                            parentInfo = {
                                tag: element.parentElement.tagName.toLowerCase(),
                                id: element.parentElement.id || '',
                                className: element.parentElement.className || ''
                            };
                        }
                        
                        return {
                            tag: tagName,
                            id: id,
                            className: className,
                            name: name,
                            textContent: textContent,
                            dataTestId: dataTestId,
                            role: role,
                            ariaLabel: ariaLabel,
                            href: href,
                            value: value,
                            rect: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            },
                            parent: parentInfo
                        };
                    }
                """, x, y)
            elif selector:
                # 使用选择器获取元素
                try:
                    element_data = await self.engine.page.evaluate("""
                        (selector) => {
                            const element = document.querySelector(selector);
                            if (!element) return null;
                            
                            const rect = element.getBoundingClientRect();
                            const tagName = element.tagName.toLowerCase();
                            const id = element.id || '';
                            const className = element.className || '';
                            const name = element.name || '';
                            const textContent = (element.textContent || '').trim().substring(0, 50);
                            const dataTestId = element.getAttribute('data-testid') || '';
                            const role = element.getAttribute('role') || '';
                            const ariaLabel = element.getAttribute('aria-label') || '';
                            const href = element.href || '';
                            const value = element.value || '';
                            
                            let parentInfo = null;
                            if (element.parentElement) {
                                parentInfo = {
                                    tag: element.parentElement.tagName.toLowerCase(),
                                    id: element.parentElement.id || '',
                                    className: element.parentElement.className || ''
                                };
                            }
                            
                            return {
                                tag: tagName,
                                id: id,
                                className: className,
                                name: name,
                                textContent: textContent,
                                dataTestId: dataTestId,
                                role: role,
                                ariaLabel: ariaLabel,
                                href: href,
                                value: value,
                                rect: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                },
                                parent: parentInfo
                            };
                        }
                    """, selector)
                except Exception as e:
                    logger.warning(f"使用选择器获取元素失败: {str(e)}")
                    element_data = None
            
            if not element_data:
                return {
                    'success': False,
                    'error': '无法找到元素'
                }
            
            # 生成定位器候选（MVP只支持：id, css, name, testid）
            candidates = []
            
            # 策略1: ID
            if element_data.get('id'):
                candidates.append({
                    'locator_type': 'id',
                    'locator_value': element_data['id'],
                    'selector': f"#{element_data['id']}",
                    'priority': 1,
                    'description': f"ID: {element_data['id']}"
                })
            
            # 策略2: data-testid
            if element_data.get('dataTestId'):
                candidates.append({
                    'locator_type': 'testid',
                    'locator_value': element_data['dataTestId'],
                    'selector': f"[data-testid='{element_data['dataTestId']}']",
                    'priority': 2,
                    'description': f"Test ID: {element_data['dataTestId']}"
                })
            
            # 策略3: name属性
            if element_data.get('name'):
                candidates.append({
                    'locator_type': 'name',
                    'locator_value': element_data['name'],
                    'selector': f"[name='{element_data['name']}']",
                    'priority': 3,
                    'description': f"Name: {element_data['name']}"
                })
            
            # 策略4: CSS选择器 (tag + class，作为后备)
            if element_data.get('className'):
                class_list = element_data['className'].split()[:3]  # 取前3个class
                css_selector = f"{element_data['tag']}.{'.'.join(class_list)}"
                candidates.append({
                    'locator_type': 'css',
                    'locator_value': css_selector,
                    'selector': css_selector,
                    'priority': 4,
                    'description': f"CSS: {css_selector}"
                })
            
            # 按优先级排序
            candidates.sort(key=lambda x: x['priority'])
            
            # 推荐定位器（优先级最高的）
            recommended_locator = candidates[0] if candidates else None
            
            return {
                'success': True,
                'element_info': element_data,
                'locator': {
                    'locator_type': recommended_locator['locator_type'] if recommended_locator else 'css',
                    'locator_value': recommended_locator['locator_value'] if recommended_locator else ''
                },
                'candidates': candidates
            }
            
        except Exception as e:
            logger.error(f"选择元素失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # 清理资源
            try:
                await self.engine.cleanup()
            except Exception as cleanup_error:
                logger.error(f"清理资源失败: {str(cleanup_error)}")
    
    def select_element_sync(self, url: str, x: Optional[int] = None, y: Optional[int] = None,
                           selector: Optional[str] = None, browser_type: str = 'chromium',
                           viewport_width: int = 1280, viewport_height: int = 720) -> Dict[str, Any]:
        """同步选择元素（用于Django视图）"""
        loop = create_windows_compatible_event_loop()
        try:
            return loop.run_until_complete(
                self.select_element(
                    url=url,
                    x=x,
                    y=y,
                    selector=selector,
                    browser_type=browser_type,
                    viewport_width=viewport_width,
                    viewport_height=viewport_height
                )
            )
        finally:
            loop.close()
