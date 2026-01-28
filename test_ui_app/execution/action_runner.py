"""
动作执行器 - 基于PlaywrightEngine，只处理actions格式
"""
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from playwright.async_api import Page, Browser, BrowserContext
from django.conf import settings
from django.utils import timezone
from pathlib import Path

from ..playwright_engine import PlaywrightEngine

logger = logging.getLogger(__name__)


class ActionRunner(PlaywrightEngine):
    """动作执行器，继承PlaywrightEngine，专门处理actions格式"""

    def __init__(self):
        super().__init__()
        self.action_results = []

    async def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行actions列表
        
        Args:
            actions: actions列表，格式为 [{"id": "...", "order": 1, "type": "...", ...}, ...]
            
        Returns:
            List[Dict]: 执行结果列表，每个action对应一个结果
            
        Raises:
            RuntimeError: 当任何action执行失败时，抛出异常并包含失败信息
        """
        if not self.page:
            raise RuntimeError("页面未初始化，请先调用initialize()")
        
        self.action_results = []
        
        # 按order排序
        sorted_actions = sorted(actions, key=lambda x: x.get('order', 0))
        
        # 【FIX】优先执行navigate actions
        # 将navigate类型的action移到最前面，确保页面导航先完成
        # 这样可以避免在页面加载前就尝试操作元素导致失败
        navigate_actions = [a for a in sorted_actions if a.get('type') == 'navigate']
        other_actions = [a for a in sorted_actions if a.get('type') != 'navigate']
        sorted_actions = navigate_actions + other_actions
        
        for action in sorted_actions:
            result = await self._execute_action(action)
            self.action_results.append(result)

            # 立即输出 action 执行结果到控制台
            action_id = action.get('id', 'unknown')
            action_type = action.get('type', 'unknown')
            action_order = action.get('order', 0)
            status = result.get('status', 'unknown')

            # 输出 action 执行结果
            print(f"[UITest] Action {action_order}: {action_type} ({action_id})", flush=True)

            if status == 'passed':
                message = result.get('message', '')
                print(f"[UITest]   ✅ 执行成功: {message}", flush=True)
            elif status == 'failed':
                error_msg = result.get('error', 'Unknown error')
                message = result.get('message', '')
                print(f"[UITest]   ❌ 执行失败: {error_msg}", flush=True)
                if message:
                    print(f"[UITest]      错误详情: {message}", flush=True)
                
                # 构建详细的错误信息
                error_detail = (
                    f"UI测试执行失败\n"
                    f"  失败步骤: Action #{action_order} ({action_type})\n"
                    f"  Action ID: {action_id}\n"
                    f"  错误原因: {error_msg}\n"
                    f"  详情: {message if message else '无'}"
                )
                logger.error(error_detail)
                
                # 立即抛出异常，中断执行流程
                # 注意：资源清理由调用方（ExecutionManager）负责
                raise RuntimeError(error_detail)

        return self.action_results

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个action"""
        action_id = action.get('id', 'unknown')
        action_type = action.get('type')
        action_order = action.get('order', 0)
        params = action.get('params', {})
        selector = action.get('selector')
        description = action.get('description', '')

        result = {
            'action_id': action_id,
            'order': action_order,
            'status': 'pending',
            'message': '',
            'data': {},
            'error': None,
        }

        try:
            if action_type == 'navigate':
                result = await self._execute_navigate(params, result)
            elif action_type == 'click':
                result = await self._execute_click(selector, params, result)
            elif action_type == 'fill':
                result = await self._execute_fill(selector, params, result)
            elif action_type == 'select':
                result = await self._execute_select(selector, params, result)
            elif action_type == 'hover':
                result = await self._execute_hover(selector, params, result)
            elif action_type == 'wait':
                result = await self._execute_wait(params, result)
            elif action_type == 'screenshot':
                result = await self._execute_screenshot(params, result)
            else:
                result['status'] = 'failed'
                result['message'] = f'不支持的操作类型: {action_type}'
                result['error'] = f'Unsupported action type: {action_type}'
                
        except Exception as e:
            result['status'] = 'failed'
            result['message'] = f'执行失败: {str(e)}'
            result['error'] = str(e)
            logger.error(f"Action执行失败: {action_id}, 类型: {action_type}, 错误: {str(e)}")
        
        # Removed verbose logging
        return result

    async def _execute_navigate(self, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行导航action
        
        导航到指定URL，等待页面网络空闲
        """
        url = params.get('url', '')
        if not url:
            result['status'] = 'failed'
            result['message'] = '缺少url参数'
            result['error'] = 'Missing url parameter'
            return result

        try:
            # 验证和修复URL格式
            url = self._validate_and_fix_url(url)
            
            # 导航到URL，等待网络空闲
            await self.page.goto(url, wait_until='networkidle', timeout=30000)

            result['status'] = 'passed'
            result['message'] = f'成功导航到: {url}'
            result['data'] = {'url': self.page.url}
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'导航失败: {url}'
            result['error'] = error_msg
            logger.error(f"Navigate操作失败: url={url}, 错误: {error_msg}")
        
        return result

    async def _execute_click(self, selector: Optional[Dict[str, str]],
                            params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行点击action - 使用Playwright语义化定位器
        
        遵循Playwright最佳实践：
        1. 优先使用语义化定位器（get_by_role、get_by_text等）
        2. 自动等待元素可见和可交互
        3. 失败时立即报错，不跳过
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        # 使用Playwright语义化定位器
        locator = self._get_semantic_locator(selector)

        try:
            # 等待元素可见（Playwright会自动等待元素可交互）
            await locator.wait_for(state='visible', timeout=30000)

            # 点击元素（Playwright会自动滚动到元素位置）
            await locator.click(timeout=30000)

            result['status'] = 'passed'
            result['message'] = f'成功点击元素: {self._get_locator_description(selector)}'
        except Exception as e:
            # 任何错误都视为失败，不跳过
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'点击失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"Click操作失败: {self._get_locator_description(selector)}, 错误: {error_msg}")

        return result

    async def _execute_fill(self, selector: Optional[Dict[str, str]],
                           params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行填写action - 使用Playwright语义化定位器
        
        遵循Playwright最佳实践：
        1. 优先使用语义化定位器
        2. 自动等待元素可编辑
        3. 填充前自动清空输入框
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        # 使用Playwright语义化定位器
        locator = self._get_semantic_locator(selector)
        value = params.get('value', '')

        try:
            # Playwright的fill()方法会自动：
            # 1. 等待元素可见和可编辑
            # 2. 清空现有内容
            # 3. 填充新值
            await locator.fill(value)

            result['status'] = 'passed'
            result['message'] = f'成功填写元素: {self._get_locator_description(selector)}, 值="{value}"'
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'填写失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"Fill操作失败: {self._get_locator_description(selector)}, 错误: {error_msg}")
        
        return result

    async def _execute_select(self, selector: Optional[Dict[str, str]],
                             params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行选择action - 使用Playwright语义化定位器
        
        用于 <select> 下拉框选择
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        # 使用Playwright语义化定位器
        locator = self._get_semantic_locator(selector)
        value = params.get('value', '')

        try:
            # Playwright会自动等待select元素可见和可交互
            await locator.select_option(value)

            result['status'] = 'passed'
            result['message'] = f'成功选择选项: {self._get_locator_description(selector)}, 值="{value}"'
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'选择失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"Select操作失败: {self._get_locator_description(selector)}, 错误: {error_msg}")
        
        return result

    async def _execute_hover(self, selector: Optional[Dict[str, str]],
                           params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行悬停action - 使用Playwright语义化定位器
        
        用于触发hover效果（如下拉菜单、工具提示等）
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        # 使用Playwright语义化定位器
        locator = self._get_semantic_locator(selector)

        try:
            # Playwright会自动滚动到元素位置并悬停
            await locator.hover()

            result['status'] = 'passed'
            result['message'] = f'成功悬停元素: {self._get_locator_description(selector)}'
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'悬停失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"Hover操作失败: {self._get_locator_description(selector)}, 错误: {error_msg}")
        
        return result

    async def _execute_wait(self, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行等待action
        
        支持三种等待类型：
        1. timeout: 等待固定时间（毫秒）
        2. selector: 等待元素出现（使用语义化定位器）
        3. navigation: 等待页面加载完成
        """
        wait_type = params.get('type', 'timeout')

        try:
            if wait_type == 'timeout':
                timeout = params.get('timeout', 5000)
                await self.page.wait_for_timeout(timeout)
                result['status'] = 'passed'
                result['message'] = f'等待完成: {timeout}ms'
            elif wait_type == 'selector':
                selector = params.get('selector')
                if not selector:
                    result['status'] = 'failed'
                    result['message'] = '等待selector类型需要提供selector参数'
                    result['error'] = 'Missing selector for wait type "selector"'
                    return result
                
                # 使用Playwright语义化定位器
                locator = self._get_semantic_locator(selector)
                await locator.wait_for(state='visible', timeout=30000)
                
                result['status'] = 'passed'
                result['message'] = f'等待元素出现: {self._get_locator_description(selector)}'
            elif wait_type == 'navigation':
                await self.page.wait_for_load_state('networkidle', timeout=30000)
                result['status'] = 'passed'
                result['message'] = '等待页面加载完成'
            else:
                result['status'] = 'failed'
                result['message'] = f'不支持的等待类型: {wait_type}'
                result['error'] = f'Unsupported wait type: {wait_type}'
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'等待失败: {wait_type}'
            result['error'] = error_msg
            logger.error(f"Wait操作失败: type={wait_type}, 错误: {error_msg}")

        return result

    async def _execute_screenshot(self, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行截图action
        
        保存当前页面截图到指定路径
        """
        try:
            screenshot_path = await self._take_screenshot(
                params.get('name', f'screenshot_{timezone.now().timestamp()}')
            )

            result['status'] = 'passed'
            result['message'] = f'截图成功: {screenshot_path}'
            result['data'] = {'screenshot_path': screenshot_path}
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = '截图失败'
            result['error'] = error_msg
            logger.error(f"Screenshot操作失败: 错误: {error_msg}")
        
        return result
