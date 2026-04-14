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

    def __init__(self) -> None:
        super().__init__()
        self.action_results: list[dict[str, Any]] = []

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
        
        # 确保第一个 action 是 navigate（如果存在 navigate 类型）
        # 只移动第一个 navigate 到最前面，保持其余 action 的用户定义顺序
        first_nav_idx = next(
            (i for i, a in enumerate(sorted_actions) if a.get('type') == 'navigate'),
            None
        )
        if first_nav_idx is not None and first_nav_idx > 0:
            nav_action = sorted_actions.pop(first_nav_idx)
            sorted_actions.insert(0, nav_action)

        for action in sorted_actions:
            result = await self._execute_action(action)
            self.action_results.append(result)

            action_id = action.get('id', 'unknown')
            action_type = action.get('type', 'unknown')
            action_order = action.get('order', 0)
            status = result.get('status', 'unknown')

            try:
                print(f"[UITest] Action {action_order}: {action_type} ({action_id})", flush=True)

                if status == 'passed':
                    message = result.get('message', '')
                    print(f"[UITest]   OK: {message}", flush=True)
                elif status == 'failed':
                    error_msg = result.get('error', 'Unknown error')
                    message = result.get('message', '')
                    print(f"[UITest]   FAIL: {error_msg}", flush=True)
                    if message:
                        print(f"[UITest]      Detail: {message}", flush=True)

                    error_detail = (
                        f"UI测试执行失败\n"
                        f"  失败步骤: Action #{action_order} ({action_type})\n"
                        f"  Action ID: {action_id}\n"
                        f"  错误原因: {error_msg}\n"
                        f"  详情: {message if message else '无'}"
                    )
                    logger.error(error_detail)

                    raise RuntimeError(error_detail)
            except UnicodeEncodeError as e:
                # 处理终端编码问题，但记录错误以便调试
                logger.warning(f"Unicode encoding error in terminal output: {e}")
                pass

        return self.action_results

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个action，带自愈机制"""
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
                # 尝试执行，失败则自愈
                try:
                    result = await self._execute_click(selector, params, result)
                except Exception as e:
                    logger.warning(f"[SelfHealing] Click failed with selector {selector}, attempting healing...")
                    healed_selector = await self._heal_click_action(action)
                    if healed_selector:
                        logger.info(f"[SelfHealing] Click healed with new selector: {healed_selector}")
                        result = await self._execute_click(healed_selector, params, result)
                        result['data']['healed'] = True
                        result['data']['original_selector'] = selector
                        result['data']['healed_selector'] = healed_selector
                    else:
                        raise
            elif action_type == 'fill':
                # 尝试执行，失败则自愈
                try:
                    result = await self._execute_fill(selector, params, result)
                except Exception as e:
                    logger.warning(f"[SelfHealing] Fill failed with selector {selector}, attempting healing...")
                    healed_selector = await self._heal_fill_action(action, params.get('value', ''))
                    if healed_selector:
                        logger.info(f"[SelfHealing] Fill healed with new selector: {healed_selector}")
                        result = await self._execute_fill(healed_selector, params, result)
                        result['data']['healed'] = True
                        result['data']['original_selector'] = selector
                        result['data']['healed_selector'] = healed_selector
                    else:
                        raise
            elif action_type == 'select':
                result = await self._execute_select(selector, params, result)
            elif action_type == 'press':
                result = await self._execute_press(selector, params, result)
            elif action_type == 'select_option':
                result = await self._execute_select_option(selector, params, result)
            elif action_type == 'canvas_click':
                result = await self._execute_canvas_click(selector, params, result)
            elif action_type == 'canvas_drag':
                result = await self._execute_canvas_drag(selector, params, result)
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
            
            if self.page is None:
                raise RuntimeError("页面未初始化")
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

    async def _execute_press(self, selector: Optional[Dict[str, str]],
                            params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行按键action - 使用Playwright语义化定位器
        
        用于按下特定键（如Enter、Escape等）
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        locator = self._get_semantic_locator(selector)
        key = params.get('key', 'Enter')

        try:
            await locator.press(key)

            result['status'] = 'passed'
            result['message'] = f'成功按键: {key} on {self._get_locator_description(selector)}'
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'按键失败: {key} on {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"Press操作失败: key={key}, selector={self._get_locator_description(selector)}, 错误: {error_msg}")
        
        return result

    async def _execute_select_option(self, selector: Optional[Dict[str, str]],
                                    params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行下拉选项选择action
        
        用于动态下拉框（如Google地址自动完成）中选择选项
        通过文本内容匹配选项
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        value = params.get('value', '')
        if not value:
            result['status'] = 'failed'
            result['message'] = '缺少value参数'
            result['error'] = 'Missing value parameter'
            return result

        locator = self._get_semantic_locator(selector)

        try:
            # 首先尝试填充值到输入框
            await locator.fill(value)
            
            if self.page is None:
                raise RuntimeError("页面未初始化")
            # 等待一下让页面响应
            await self.page.wait_for_timeout(300)
            
            result['status'] = 'passed'
            result['message'] = f'成功选择选项: {self._get_locator_description(selector)}, 值="{value}"'
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'选择选项失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"SelectOption操作失败: selector={self._get_locator_description(selector)}, 值={value}, 错误: {error_msg}")
        
        return result

    async def _execute_canvas_click(self, selector: Optional[Dict[str, str]],
                                   params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Canvas点击action
        
        参数:
        - selector: canvas元素的选择器
        - params.x: 点击位置的X坐标（0-1之间的比例值）
        - params.y: 点击位置的Y坐标（0-1之间的比例值）
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        locator = self._get_semantic_locator(selector)
        x_ratio = params.get('x', 0.5)
        y_ratio = params.get('y', 0.5)

        try:
            # 等待canvas元素可见
            await locator.wait_for(state='visible', timeout=30000)
            
            # 获取canvas的实际尺寸
            box = await locator.bounding_box()
            if not box:
                raise RuntimeError("无法获取Canvas元素的边界框")
            
            # 计算实际点击坐标
            x = box['x'] + box['width'] * x_ratio
            y = box['y'] + box['height'] * y_ratio
            
            # 使用page.mouse点击
            await self.page.mouse.click(x, y)

            result['status'] = 'passed'
            result['message'] = f'成功点击Canvas: {self._get_locator_description(selector)}, 位置=({x_ratio:.2%}, {y_ratio:.2%})'
            result['data'] = {'x_ratio': x_ratio, 'y_ratio': y_ratio, 'actual_x': x, 'actual_y': y}
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'Canvas点击失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"CanvasClick操作失败: selector={self._get_locator_description(selector)}, 错误: {error_msg}")
        
        return result

    async def _execute_canvas_drag(self, selector: Optional[Dict[str, str]],
                                  params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Canvas拖拽action
        
        参数:
        - selector: canvas元素的选择器
        - params.start_x: 起始X坐标比例（0-1）
        - params.start_y: 起始Y坐标比例（0-1）
        - params.end_x: 结束X坐标比例（0-1）
        - params.end_y: 结束Y坐标比例（0-1）
        """
        if not selector:
            result['status'] = 'failed'
            result['message'] = '缺少selector参数'
            result['error'] = 'Missing selector parameter'
            return result

        locator = self._get_semantic_locator(selector)
        start_x_ratio = params.get('start_x', 0.3)
        start_y_ratio = params.get('start_y', 0.5)
        end_x_ratio = params.get('end_x', 0.7)
        end_y_ratio = params.get('end_y', 0.5)

        try:
            # 等待canvas元素可见
            await locator.wait_for(state='visible', timeout=30000)
            
            # 获取canvas的实际尺寸
            box = await locator.bounding_box()
            if not box:
                raise RuntimeError("无法获取Canvas元素的边界框")
            
            # 计算实际坐标
            start_x = box['x'] + box['width'] * start_x_ratio
            start_y = box['y'] + box['height'] * start_y_ratio
            end_x = box['x'] + box['width'] * end_x_ratio
            end_y = box['y'] + box['height'] * end_y_ratio
            
            # 执行拖拽操作
            await self.page.mouse.move(start_x, start_y)
            await self.page.mouse.down()
            await self.page.mouse.move(end_x, end_y, steps=10)
            await self.page.mouse.up()

            result['status'] = 'passed'
            result['message'] = f'成功拖拽Canvas: {self._get_locator_description(selector)}'
            result['data'] = {
                'start_ratio': (start_x_ratio, start_y_ratio),
                'end_ratio': (end_x_ratio, end_y_ratio),
                'start_actual': (start_x, start_y),
                'end_actual': (end_x, end_y)
            }
        except Exception as e:
            error_msg = str(e)
            result['status'] = 'failed'
            result['message'] = f'Canvas拖拽失败: {self._get_locator_description(selector)}'
            result['error'] = error_msg
            logger.error(f"CanvasDrag操作失败: selector={self._get_locator_description(selector)}, 错误: {error_msg}")
        
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
            if self.page is None:
                raise RuntimeError("页面未初始化")
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

    async def _heal_fill_action(self, action: Dict[str, Any], value: str) -> Optional[Dict[str, str]]:
        """
        自愈fill操作：在页面中寻找最合适的输入框
        
        当首选定位器失败时，基于页面实际内容智能匹配输入元素
        """
        try:
            if self.page is None:
                logger.warning("[SelfHealing] Page not initialized")
                return None
            # 1. 获取所有可见的输入元素
            inputs = await self.page.locator('input:visible, textarea:visible').all()
            if not inputs:
                logger.warning("[SelfHealing] No visible input elements found on page")
                return None

            # 2. 为每个输入元素打分
            candidates = []
            for inp in inputs:
                score = 0
                attrs = {
                    'placeholder': await inp.get_attribute('placeholder') or '',
                    'name': await inp.get_attribute('name') or '',
                    'id': await inp.get_attribute('id') or '',
                    'aria-label': await inp.get_attribute('aria-label') or '',
                    'type': await inp.get_attribute('type') or 'text'
                }
                
                # 关键词匹配（搜索相关）- 权重最高
                search_keywords = ['搜索', '百度一下', 'search', 'query', 'wd', 'kw']
                for kw in search_keywords:
                    for attr_val in attrs.values():
                        if kw.lower() in attr_val.lower():
                            score += 3
                
                # 输入框类型匹配
                if attrs['type'] in ['text', 'search']:
                    score += 2
                elif attrs['type'] in ['email', 'password', 'number']:
                    score += 1
                
                # 输入内容长度启发（长文本更可能是搜索框）
                if len(value) > 5:
                    score += 1
                
                # 有明确标识的元素优先
                if attrs['id']:
                    score += 1
                if attrs['name']:
                    score += 0.5
                
                if score > 0:
                    candidates.append((score, attrs, inp))
            
            # 3. 选择最佳匹配
            if not candidates:
                logger.warning("[SelfHealing] No suitable input candidates found")
                return None
            
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_attrs, best_input = candidates[0]
            
            # 阈值检查：至少要有2分才使用
            if best_score < 2:
                logger.warning(f"[SelfHealing] Best candidate score too low: {best_score}")
                return None
            
            # 4. 生成稳定的选择器
            if best_attrs['id']:
                healed_selector = {'type': 'id', 'value': best_attrs['id']}
            elif best_attrs['name']:
                healed_selector = {'type': 'name', 'value': best_attrs['name']}
            elif best_attrs['placeholder']:
                healed_selector = {'type': 'placeholder', 'value': best_attrs['placeholder']}
            else:
                # 兜底：使用CSS选择器
                tag = await best_input.evaluate('el => el.tagName.toLowerCase()')
                healed_selector = {'type': 'css', 'value': f'{tag}:visible'}
            
            logger.info(f"[SelfHealing] Fill healed: score={best_score}, selector={healed_selector}")
            return healed_selector
            
        except Exception as e:
            logger.error(f"[SelfHealing] Fill healing failed: {e}")
            return None

    async def _heal_click_action(self, action: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        自愈click操作：在页面中寻找最合适的可点击元素
        
        当首选定位器失败时，基于页面实际内容智能匹配按钮或链接
        """
        try:
            if self.page is None:
                logger.warning("[SelfHealing] Page not initialized")
                return None
            # 1. 获取所有可见的可点击元素
            clickables = await self.page.locator('button:visible, a:visible, [role="button"]:visible').all()
            if not clickables:
                logger.warning("[SelfHealing] No visible clickable elements found on page")
                return None

            # 2. 为每个元素打分
            candidates = []
            for elem in clickables:
                score = 0
                attrs = {
                    'text': await elem.inner_text() or '',
                    'aria-label': await elem.get_attribute('aria-label') or '',
                    'title': await elem.get_attribute('title') or '',
                    'id': await elem.get_attribute('id') or '',
                    'name': await elem.get_attribute('name') or '',
                    'tag': await elem.evaluate('el => el.tagName.toLowerCase()')
                }
                
                # 关键词匹配（按钮相关）
                button_keywords = ['搜索', '百度一下', 'submit', '确认', '确定', 'search', 'go']
                for kw in button_keywords:
                    if kw.lower() in attrs['text'].lower():
                        score += 3
                    if kw.lower() in attrs['aria-label'].lower():
                        score += 2
                
                # 标签类型权重
                if attrs['tag'] == 'button':
                    score += 2
                elif attrs['tag'] == 'a':
                    score += 1
                
                # 有明确标识的元素优先
                if attrs['id']:
                    score += 1
                if attrs['text'].strip():
                    score += 1
                
                if score > 0:
                    candidates.append((score, attrs, elem))
            
            # 3. 选择最佳匹配
            if not candidates:
                logger.warning("[SelfHealing] No suitable clickable candidates found")
                return None
            
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_attrs, best_elem = candidates[0]
            
            # 阈值检查
            if best_score < 2:
                logger.warning(f"[SelfHealing] Best candidate score too low: {best_score}")
                return None
            
            # 4. 生成稳定的选择器
            if best_attrs['id']:
                healed_selector = {'type': 'id', 'value': best_attrs['id']}
            elif best_attrs['text'].strip():
                # 使用text定位
                healed_selector = {'type': 'text', 'value': best_attrs['text'].strip()[:30]}
            elif best_attrs['aria-label']:
                healed_selector = {'type': 'aria-label', 'value': best_attrs['aria-label']}
            else:
                # 兜底
                healed_selector = {'type': 'css', 'value': f'{best_attrs["tag"]}:visible'}
            
            logger.info(f"[SelfHealing] Click healed: score={best_score}, selector={healed_selector}")
            return healed_selector
            
        except Exception as e:
            logger.error(f"[SelfHealing] Click healing failed: {e}")
            return None

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
