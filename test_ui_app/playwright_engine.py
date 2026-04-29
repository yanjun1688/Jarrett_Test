"""
Playwright执行引擎
"""
# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Windows 上 Playwright 创建浏览器子进程依赖 create_subprocess_exec，
# 只有 ProactorEventLoopPolicy（基于 IOCP）支持，SelectorEventLoopPolicy 会 raise NotImplementedError。
# 因此不做策略切换，保持项目入口点（manage.py/__init__/asgi/celery）已统一设置的 ProactorEventLoopPolicy。


def create_windows_compatible_event_loop() -> asyncio.AbstractEventLoop:
    """
    创建与Windows兼容的事件循环（用于Playwright）

    Windows 上使用 ProactorEventLoopPolicy（基于 IOCP）以支持 Playwright 浏览器子进程创建。
    SelectorEventLoopPolicy 在 Windows 上不支持 create_subprocess_exec，会导致 NotImplementedError。

    Returns:
        asyncio.AbstractEventLoop: 配置正确的事件循环
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


class PlaywrightEngine:
    """
    Playwright执行引擎
    
    核心职责：
    1. 浏览器初始化和清理
    2. URL验证和修复
    3. Selector格式转换
    4. 截图功能
    
    注意：
    - execute_step() 方法已废弃，请使用 ActionRunner.execute_actions()
    - PlaywrightRecorder 类已废弃，请使用 SyncBrowserRecorder
    """
    
    def __init__(self) -> None:
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright: Any = None
        self.screenshots_dir = Path(settings.BASE_DIR) / 'media' / 'ui_test_screenshots'
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_and_fix_url(self, url: str) -> str:
        """
        验证并修复URL格式
        
        Args:
            url: 原始URL
            
        Returns:
            str: 验证和修复后的URL
            
        Raises:
            ValueError: URL格式无效
        """
        if not url or not isinstance(url, str):
            raise ValueError("URL不能为空")
        
        url = url.strip()
        
        # 移除多余的引号
        if url.startswith('"') and url.endswith('"'):
            url = url[1:-1]
        if url.startswith("'") and url.endswith("'"):
            url = url[1:-1]
        
        url = url.strip()
        
        # 如果没有协议，自动添加https://
        parsed = urlparse(url)
        if not parsed.scheme:
            # 检查是否是本地文件路径
            if url.startswith('/') or url.startswith('./') or url.startswith('../'):
                url = f"file://{url}"
            else:
                # 默认使用https
                url = f"https://{url}"
            logger.info(f"URL缺少协议，已自动添加: {url}")
        
        # 验证URL格式（允许about:blank等特殊URL）
        parsed = urlparse(url)
        if not parsed.netloc and parsed.scheme not in ['file', 'data', 'about']:
            raise ValueError(f"无效的URL格式: {url}")
        
        return url
    
    async def initialize(self, browser_type: str = 'chromium', headless: bool = True,
                        viewport_width: int = 1280, viewport_height: int = 720,
                        timeout: int = 30000) -> bool:
        """
        初始化浏览器
        
        Args:
            browser_type: 浏览器类型 ('chromium', 'firefox', 'webkit')
            headless: 是否无头模式
            viewport_width: 视口宽度
            viewport_height: 视口高度
            timeout: 超时时间（毫秒）
            
        Returns:
            bool: 初始化成功返回True
            
        Raises:
            Exception: 初始化失败
        """
        try:
            # Windows上Playwright需要ProactorEventLoopPolicy（默认）
            # 不要设置SelectorEventLoopPolicy，会导致NotImplementedError
            
            # 添加超时保护防止卡死
            try:
                self.playwright = await asyncio.wait_for(
                    async_playwright().start(),
                    timeout=15.0
                )
            except asyncio.TimeoutError:
                raise Exception("Playwright初始化超时（15秒），请检查安装：playwright install")
            
            browser_map = {
                'chromium': self.playwright.chromium if self.playwright else None,
                'firefox': self.playwright.firefox if self.playwright else None,
                'webkit': self.playwright.webkit if self.playwright else None,
            }
            
            browser_launcher = browser_map.get(browser_type, self.playwright.chromium if self.playwright else None)
            if browser_launcher is None:
                raise Exception("Playwright浏览器启动器未初始化")
            self.browser = await browser_launcher.launch(headless=headless)
            
            self.context = await self.browser.new_context(
                viewport={'width': viewport_width, 'height': viewport_height},
            )
            self.context.set_default_timeout(timeout)
            self.page = await self.context.new_page()
            
            logger.info(f"Playwright引擎初始化成功: {browser_type}, headless={headless}")
            return True
        except Exception as e:
            logger.error(f"Playwright引擎初始化失败: {str(e)}")
            raise
    
    def _get_selector_string(self, selector: Optional[Dict[str, Any]]) -> str:
        """
        统一的选择器转换方法
        
        支持两种格式：
        1. 旧格式: {'locator_type': 'id', 'locator_value': 'xxx'}
        2. 新格式: {'type': 'id', 'value': 'xxx'}
        
        Args:
            selector: 选择器对象或字典
            
        Returns:
            str: Playwright选择器字符串
            
        Raises:
            ValueError: selector格式错误
        """
        if not selector:
            logger.warning("selector为空，使用body作为默认选择器")
            return 'body'
        
        # 支持两种格式：旧格式(locator_type/locator_value)和新格式(type/value)
        selector_type = selector.get('type') or selector.get('locator_type')
        selector_value = selector.get('value') or selector.get('locator_value')
        
        if not selector_type or not selector_value:
            raise ValueError(f"selector格式错误: {selector}")
        
        # 转换为Playwright选择器格式
        if selector_type == 'id':
            return f"#{selector_value}"
        elif selector_type == 'name':
            return f"[name='{selector_value}']"
        elif selector_type == 'css':
            return selector_value
        elif selector_type == 'testid':
            return f"[data-testid='{selector_value}']"
        else:
            # 未知类型，尝试作为CSS选择器
            logger.warning(f"未知的选择器类型: {selector_type}，将作为CSS选择器使用")
            return selector_value
    
    def _get_semantic_locator(self, selector: Optional[Dict[str, Any]]) -> Any:
        """
        获取语义化定位器 - 遵循Playwright最佳实践

        优先级顺序：
        1. testid: get_by_test_id() - 专门用于测试的标识
        2. role: get_by_role() - 基于ARIA角色的语义化定位
        3. label: get_by_label() - 基于标签文本的表单元素定位
        4. text: get_by_text() - 基于文本内容定位
        5. placeholder: get_by_placeholder() - 基于占位符定位
        6. id/name/css: locator() - 传统CSS选择器

        支持index字段：当选择器有index时，使用.nth(index)选择第几个匹配元素

        Args:
            selector: 选择器对象，格式为 {'type': 'xxx', 'value': 'xxx', 'index': 0}

        Returns:
            Locator: Playwright Locator对象

        Raises:
            ValueError: selector格式错误或page未初始化
        """
        if not self.page:
            raise RuntimeError("页面未初始化")

        if not selector:
            raise ValueError("selector不能为空")

        selector_type = selector.get('type') or selector.get('locator_type')
        selector_value = selector.get('value') or selector.get('locator_value')
        element_index = selector.get('index')

        if not selector_type or not selector_value:
            raise ValueError(f"selector格式错误: {selector}")

        if selector_type == 'testid':
            locator = self.page.get_by_test_id(selector_value)
        elif selector_type == 'role':
            role_name = selector.get('name')
            if role_name:
                locator = self.page.get_by_role(selector_value, name=role_name)
            else:
                locator = self.page.get_by_role(selector_value)
        elif selector_type == 'label':
            locator = self.page.get_by_label(selector_value)
        elif selector_type == 'text':
            locator = self.page.get_by_text(selector_value, exact=False)
        elif selector_type == 'placeholder':
            locator = self.page.get_by_placeholder(selector_value)
        elif selector_type == 'aria-label':
            locator = self.page.locator(f"[aria-label='{selector_value}']")
        elif selector_type == 'id':
            locator = self.page.locator(f"#{selector_value}")
        elif selector_type == 'name':
            locator = self.page.locator(f"[name='{selector_value}']")
        elif selector_type == 'css':
            locator = self.page.locator(selector_value)
        else:
            logger.warning(f"未知的选择器类型: {selector_type}，将作为CSS选择器使用")
            locator = self.page.locator(selector_value)
        
        if element_index is not None:
            locator = locator.nth(element_index)
            logger.debug(f"[Locator] 使用 .nth({element_index}) 选择第 {element_index + 1} 个匹配元素")
        
        return locator
    
    def _get_locator_description(self, selector: Optional[Dict[str, Any]]) -> str:
        """
        获取定位器的友好描述
        
        Args:
            selector: 选择器对象
            
        Returns:
            str: 友好的描述文本
        """
        if not selector:
            return "未知元素"
        
        selector_type = selector.get('type') or selector.get('locator_type')
        selector_value = selector.get('value') or selector.get('locator_value')
        
        if not selector_type or not selector_value:
            return "未知元素"
        
        # 生成友好描述
        type_labels = {
            'testid': 'data-testid',
            'role': 'role',
            'label': 'label',
            'text': 'text',
            'placeholder': 'placeholder',
            'aria-label': 'aria-label',
            'id': 'id',
            'name': 'name',
            'css': 'css'
        }
        
        label = type_labels.get(selector_type, selector_type)
        
        # 截断过长的值
        display_value = selector_value if len(selector_value) <= 50 else selector_value[:47] + '...'
        
        return f"{label}={display_value}"
    
    async def _take_screenshot(self, name: str) -> str:
        """
        截图
        
        Args:
            name: 截图名称
            
        Returns:
            str: 截图文件相对路径
        """
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        if self.page is None:
            raise RuntimeError("页面未初始化")
        await self.page.screenshot(path=str(filepath))
        return str(filepath.relative_to(settings.BASE_DIR))
    
    async def cleanup(self) -> None:
        """
        清理资源（带超时保护）
        
        关键改进：
        1. 每个清理步骤独立超时（3秒），防止卡死
        2. 即使前面步骤失败，后续步骤仍然执行
        3. 确保playwright.stop()一定会被调用
        """
        cleanup_timeout = 3.0  # 每个步骤的超时时间
        
        try:
            # 步骤1: 关闭页面（带超时）
            if self.page:
                try:
                    await asyncio.wait_for(self.page.close(), timeout=cleanup_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"关闭page超时（{cleanup_timeout}秒）")
                except Exception as e:
                    logger.error(f"关闭page失败: {str(e)}")
                finally:
                    self.page = None
            
            # 步骤2: 关闭上下文（带超时）
            if self.context:
                try:
                    await asyncio.wait_for(self.context.close(), timeout=cleanup_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"关闭context超时（{cleanup_timeout}秒）")
                except Exception as e:
                    logger.error(f"关闭context失败: {str(e)}")
                finally:
                    self.context = None
            
            # 步骤3: 关闭浏览器（带超时）
            if self.browser:
                try:
                    await asyncio.wait_for(self.browser.close(), timeout=cleanup_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"关闭browser超时（{cleanup_timeout}秒）")
                except Exception as e:
                    logger.error(f"关闭browser失败: {str(e)}")
                finally:
                    self.browser = None
            
            # 步骤4: 停止Playwright驱动（带超时）
            # 关键：即使browser.close()失败，这里也会执行
            if self.playwright:
                try:
                    await asyncio.wait_for(self.playwright.stop(), timeout=cleanup_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"停止playwright超时（{cleanup_timeout}秒）")
                    # 超时后仍然置None，防止后续访问
                except Exception as e:
                    logger.error(f"停止playwright失败: {str(e)}")
                finally:
                    self.playwright = None
            
            logger.info("Playwright引擎资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
            # 即使出错，也要确保所有引用置为None
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
