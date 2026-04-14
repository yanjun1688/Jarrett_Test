"""
同步浏览器录制器 - 完全同步阻塞实现


用户运行 start_recording() 后，程序将阻塞，直到浏览器关闭。
"""
from __future__ import annotations
import json
import logging
import time
from typing import Any, Callable
from playwright.sync_api import Playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class SyncBrowserRecorder:
    """
    同步浏览器录制器 - 阻塞式实现
    """
    
    def __init__(self) -> None:
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.is_recording = False
        self.recorded_actions: list[dict[str, Any]] = []
        self.action_counter = 0
        self._action_callback: Callable[[dict[str, Any]], None] | None = None
    
    def _get_recording_script(self) -> str:
        """
        获取录制脚本 - 简化版，仅录制核心事件
        
        支持的事件：
        1. click - 点击（自动向上查找交互元素）
        2. fill - 输入（blur或Enter触发）
        3. press - Enter键
        4. navigate - 导航（由Python端处理）
        5. select_option - 下拉框选项选择
        6. canvas_click - Canvas元素点击
        7. canvas_drag - Canvas元素拖拽
        """
        return """
        (() => {
            if (window.__webPilotRecorder) return;
            window.__webPilotRecorder = true;
            
            // 输入内容缓存，用于blur和Enter触发时获取最终值
            const inputCache = new WeakMap();
            // 防抖定时器
            let fillDebounceTimer = null;
            // Canvas拖拽状态
            let canvasDragState = null;
            
            const setupRecorder = () => {
                /**
                 * 获取真正的交互元素
                 * 当点击的是 span/div 等非交互元素时，向上查找 button/a 等
                 */
                const getInteractionElement = (el) => {
                    if (!el) return null;
                    
                    const interactiveTags = ['button', 'a', 'input', 'select', 'textarea'];
                    const tag = el.tagName.toLowerCase();
                    
                    // 本身就是交互元素
                    if (interactiveTags.includes(tag)) {
                        return el;
                    }
                    
                    // 有 role="button" 等属性
                    const role = el.getAttribute('role');
                    if (role === 'button' || el.getAttribute('role') === 'link') {
                        return el;
                    }
                    
                    // 向上查找最近的交互元素（最多3层）
                    let parent = el.parentElement;
                    let depth = 0;
                    while (parent && depth < 3) {
                        const parentTag = parent.tagName.toLowerCase();
                        if (interactiveTags.includes(parentTag) || parent.getAttribute('role') === 'button') {
                            return parent;
                        }
                        parent = parent.parentElement;
                        depth++;
                    }
                    
                    return el; // 找不到就返回原元素
                };
                
                /**
                 * 生成遵循Playwright最佳实践的selector
                 * 优先级顺序: id > testid > aria-label > name > text > css
                 */
                const getSelector = (el) => {
                    if (!el) return null;
                    
                    const tag = el.tagName.toLowerCase();
                    
                    // 1. id（排除动态ID）
                    if (el.id) {
                        const id = el.id.trim();
                        const dynamicIdPatterns = [
                            /^(react|vue|ember|ng|angular)/i,
                            /^(pv_id_|mui-|headlessui-|radix-)/i,
                            /^(v-|_)\d+/,
                            /^[0-9a-f]{8}-[0-9a-f]{4}/i,
                            /^\d+$/,
                            /^[a-z0-9]{20,}$/i
                        ];
                        
                        const isDynamic = dynamicIdPatterns.some(pattern => pattern.test(id));
                        if (!isDynamic) {
                            return { type: 'id', value: id };
                        }
                    }
                    
                    // 2. data-testid
                    if (el.dataset && el.dataset.testid) {
                        return { type: 'testid', value: el.dataset.testid.trim() };
                    }
                    
                    // 3. aria-label（按钮优先）
                    if (el.getAttribute('aria-label')) {
                        return { type: 'aria-label', value: el.getAttribute('aria-label').trim() };
                    }
                    
                    // 4. name属性
                    if (el.name) {
                        return { type: 'name', value: el.name.trim() };
                    }
                    
                    // 5. 按钮文本（button/a 优先使用文本定位）
                    if (['button', 'a'].includes(tag)) {
                        const text = el.textContent?.trim();
                        if (text && text.length <= 30) {
                            return { type: 'text', value: text };
                        }
                    }
                    
                    // 6. type="submit" 按钮
                    if (tag === 'button' && el.getAttribute('type') === 'submit') {
                        const text = el.textContent?.trim();
                        if (text) {
                            return { type: 'text', value: text };
                        }
                    }
                    
                    // 7. CSS选择器
                    const cssResult = generateStableCssSelector(el);
                    if (cssResult) {
                        if (typeof cssResult === 'string') {
                            return { type: 'css', value: cssResult };
                        } else if (cssResult.selector !== undefined) {
                            return { type: 'css', value: cssResult.selector, index: cssResult.index };
                        }
                    }
                    
                    console.warn('[JTest] 无法生成稳定的selector，跳过元素:', tag);
                    return null;
                };
                
                /**
                 * 生成稳定的CSS选择器
                 * 返回: 字符串 或 { selector: string, index: number }
                 */
                const generateStableCssSelector = (el) => {
                    if (!el) return null;
                    
                    const tag = el.tagName.toLowerCase();
                    if (tag === 'body') return 'body';
                    
                    const buildSelectors = () => {
                        const selectors = [];
                        
                        // 稳定的class名称
                        if (el.className && typeof el.className === 'string') {
                            const classes = el.className.trim().split(/\\s+/);
                            const stableClasses = classes.filter(c => {
                                return c && 
                                       !c.includes(':') && 
                                       !/^[a-z0-9]{7,}$/i.test(c) &&
                                       !/^(css|module|scoped)/i.test(c);
                            });
                            
                            if (stableClasses.length > 0) {
                                // 组合多个class增加精确度
                                if (stableClasses.length >= 2) {
                                    selectors.push(`${tag}.${stableClasses.slice(0, 2).join('.')}`);
                                } else {
                                    selectors.push(`${tag}.${stableClasses[0]}`);
                                }
                            }
                        }
                        
                        // aria属性
                        if (el.getAttribute('aria-label')) {
                            selectors.push(`${tag}[aria-label="${el.getAttribute('aria-label')}"]`);
                        }
                        if (el.getAttribute('role')) {
                            selectors.push(`${tag}[role="${el.getAttribute('role')}"]`);
                        }
                        
                        // type属性
                        if (el.getAttribute('type')) {
                            selectors.push(`${tag}[type="${el.getAttribute('type')}"]`);
                        }
                        
                        // placeholder
                        if (el.getAttribute('placeholder')) {
                            selectors.push(`${tag}[placeholder="${el.getAttribute('placeholder')}"]`);
                        }
                        
                        return selectors;
                    };
                    
                    const selectors = buildSelectors();
                    
                    if (selectors.length > 0) {
                        const firstSelector = selectors[0];
                        
                        const matches = document.querySelectorAll(firstSelector);
                        
                        if (matches.length === 1) {
                            return firstSelector;
                        }
                        
                        // 多个匹配时，记录索引
                        if (matches.length > 1) {
                            const index = Array.from(matches).indexOf(el);
                            if (index !== -1) {
                                return { selector: firstSelector, index: index };
                            }
                        }
                        
                        return firstSelector;
                    }
                    
                    return null;
                };

                const sendAction = (action) => {
                    if (typeof window.reportAction === 'function') {
                        try { 
                            window.reportAction(JSON.stringify(action)); 
                        } catch(e) { 
                            console.error('[JTest] Report error:', e); 
                        }
                    }
                };
                
                const getElementText = (el) => {
                    if (!el) return '';
                    const text = el.textContent?.trim() || '';
                    return text.length > 30 ? text.substring(0, 30) + '...' : text;
                };
                
                /**
                 * 记录输入框内容
                 */
                const trackInputChange = (el) => {
                    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                        inputCache.set(el, el.value);
                    }
                };
                
                /**
                 * 发送fill动作（带防抖）
                 */
                const sendFillAction = (el, immediate = false) => {
                    const selector = getSelector(el);
                    if (!selector) return;
                    
                    const value = inputCache.get(el) || el.value;
                    if (!value) return;
                    
                    const doSend = () => {
                        sendAction({
                            type: 'fill',
                            selector: selector,
                            value: value,
                            timestamp: Date.now()
                        });
                        console.log('[JTest] Recorded fill:', selector, `value="${value}"`);
                        inputCache.delete(el);
                    };
                    
                    if (immediate) {
                        doSend();
                    } else {
                        // 防抖：等待300ms确保用户输入完成
                        clearTimeout(fillDebounceTimer);
                        fillDebounceTimer = setTimeout(doSend, 300);
                    }
                };

                // ========== 事件监听 ==========
                
                // 1. 实时跟踪输入内容
                document.addEventListener('input', (e) => {
                    trackInputChange(e.target);
                }, true);
                
                // 2. blur时记录fill
                document.addEventListener('blur', (e) => {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                        sendFillAction(e.target, true);
                    }
                }, true);
                
                // 3. Enter键
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                            sendFillAction(e.target, true);
                        }
                        
                        const selector = getSelector(e.target);
                        if (selector) {
                            sendAction({
                                type: 'press',
                                selector: selector,
                                key: 'Enter',
                                timestamp: Date.now()
                            });
                            console.log('[JTest] Recorded press Enter:', selector);
                        }
                    }
                }, true);
                
                // 4. click - 关键：向上查找交互元素
                document.addEventListener('click', (e) => {
                    // 先记录输入框内容
                    const activeEl = document.activeElement;
                    if (activeEl && activeEl !== e.target) {
                        if (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA') {
                            sendFillAction(activeEl, true);
                        }
                    }
                    
                    // 获取真正的交互元素
                    const targetEl = getInteractionElement(e.target);
                    const selector = getSelector(targetEl);
                    
                    if (selector) {
                        const action = {
                            type: 'click',
                            selector: selector,
                            timestamp: Date.now()
                        };
                        
                        const text = getElementText(targetEl);
                        if (text) action.text = text;
                        
                        sendAction(action);
                        console.log('[JTest] Recorded click:', selector, text ? `(${text})` : '');
                    }
                }, true);
                
                // ========== Canvas录制 ==========
                
                /**
                 * 获取Canvas相对坐标（0-1比例）
                 */
                const getCanvasRelativeCoords = (canvas, event) => {
                    const rect = canvas.getBoundingClientRect();
                    const x = (event.clientX - rect.left) / rect.width;
                    const y = (event.clientY - rect.top) / rect.height;
                    return { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) };
                };
                
                /**
                 * 获取Canvas选择器
                 */
                const getCanvasSelector = (canvas) => {
                    if (canvas.id) {
                        const id = canvas.id.trim();
                        const dynamicIdPatterns = [
                            /^(react|vue|ember|ng|angular)/i,
                            /^(pv_id_|mui-|headlessui-|radix-)/i,
                            /^(v-|_)\d+/,
                            /^[0-9a-f]{8}-[0-9a-f]{4}/i,
                            /^\d+$/
                        ];
                        const isDynamic = dynamicIdPatterns.some(pattern => pattern.test(id));
                        if (!isDynamic) {
                            return { type: 'id', value: id };
                        }
                    }
                    
                    if (canvas.dataset && canvas.dataset.testid) {
                        return { type: 'testid', value: canvas.dataset.testid.trim() };
                    }
                    
                    if (canvas.getAttribute('aria-label')) {
                        return { type: 'aria-label', value: canvas.getAttribute('aria-label').trim() };
                    }
                    
                    // 尝试使用class
                    if (canvas.className && typeof canvas.className === 'string') {
                        const classes = canvas.className.trim().split(/\\s+/);
                        const stableClasses = classes.filter(c => c && !/^[a-z0-9]{7,}$/i.test(c));
                        if (stableClasses.length > 0) {
                            return { type: 'css', value: `canvas.${stableClasses[0]}` };
                        }
                    }
                    
                    return { type: 'css', value: 'canvas' };
                };
                
                // Canvas mousedown - 开始拖拽或点击
                document.addEventListener('mousedown', (e) => {
                    const canvas = e.target.closest('canvas');
                    if (canvas) {
                        const coords = getCanvasRelativeCoords(canvas, e);
                        canvasDragState = {
                            canvas: canvas,
                            selector: getCanvasSelector(canvas),
                            startX: coords.x,
                            startY: coords.y,
                            startTime: Date.now()
                        };
                    }
                }, true);
                
                // Canvas mousemove - 跟踪拖拽
                document.addEventListener('mousemove', (e) => {
                    if (canvasDragState && canvasDragState.canvas) {
                        const coords = getCanvasRelativeCoords(canvasDragState.canvas, e);
                        canvasDragState.currentX = coords.x;
                        canvasDragState.currentY = coords.y;
                    }
                }, true);
                
                // Canvas mouseup - 完成点击或拖拽
                document.addEventListener('mouseup', (e) => {
                    if (canvasDragState && canvasDragState.canvas) {
                        const canvas = canvasDragState.canvas;
                        const coords = getCanvasRelativeCoords(canvas, e);
                        
                        const dx = Math.abs(coords.x - canvasDragState.startX);
                        const dy = Math.abs(coords.y - canvasDragState.startY);
                        const duration = Date.now() - canvasDragState.startTime;
                        
                        // 判断是点击还是拖拽（移动超过5%或持续超过300ms视为拖拽）
                        const isDrag = (dx > 0.05 || dy > 0.05) || duration > 300;
                        
                        if (isDrag) {
                            // 发送拖拽事件
                            sendAction({
                                type: 'canvas_drag',
                                selector: canvasDragState.selector,
                                params: {
                                    start_x: canvasDragState.startX,
                                    start_y: canvasDragState.startY,
                                    end_x: coords.x,
                                    end_y: coords.y
                                },
                                timestamp: Date.now()
                            });
                            console.log('[JTest] Recorded canvas_drag:', 
                                `(${(canvasDragState.startX*100).toFixed(1)}%, ${(canvasDragState.startY*100).toFixed(1)}%) ->`,
                                `(${(coords.x*100).toFixed(1)}%, ${(coords.y*100).toFixed(1)}%)`);
                        } else {
                            // 发送点击事件
                            sendAction({
                                type: 'canvas_click',
                                selector: canvasDragState.selector,
                                params: {
                                    x: coords.x,
                                    y: coords.y
                                },
                                timestamp: Date.now()
                            });
                            console.log('[JTest] Recorded canvas_click:', 
                                `(${(coords.x*100).toFixed(1)}%, ${(coords.y*100).toFixed(1)}%)`);
                        }
                    }
                    canvasDragState = null;
                }, true);
                
                // 5. 监听下拉框选项点击（地址自动完成等）
                // 使用 MutationObserver 监听动态下拉框
                const dropdownObserver = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === 1) {
                                // 检查是否是下拉列表容器
                                const isDropdown = 
                                    node.getAttribute && (
                                        node.getAttribute('role') === 'listbox' ||
                                        node.classList.contains('pac-container') ||  // Google 地址
                                        node.classList.contains('dropdown') ||
                                        node.tagName === 'UL' || node.tagName === 'OL'
                                    );
                                
                                if (isDropdown) {
                                    console.log('[JTest] 检测到下拉框容器');
                                    
                                    // 为选项添加点击监听
                                    node.addEventListener('click', (e) => {
                                        e.stopPropagation();
                                        
                                        // 获取选项文本
                                        const optionText = e.target.textContent?.trim();
                                        const parentInput = document.activeElement;
                                        
                                        if (optionText && parentInput && 
                                            (parentInput.tagName === 'INPUT' || parentInput.tagName === 'TEXTAREA')) {
                                            
                                            // 记录选中的文本
                                            sendAction({
                                                type: 'select_option',
                                                selector: getSelector(parentInput),
                                                value: optionText,
                                                timestamp: Date.now()
                                            });
                                            console.log('[JTest] Recorded select_option:', optionText);
                                        }
                                    }, true);
                                }
                            }
                        });
                    });
                });
                
                dropdownObserver.observe(document.body, {
                    childList: true,
                    subtree: true
                });
                
                console.log('[JTest] Recorder ready (click, fill, press Enter, select_option, canvas)');
            };
            
            setupRecorder();
        })();
        """

    def _handle_action_report(self, source: Any, action_json: str) -> None:
        """处理来自页面的动作报告"""
        try:
            action_data = json.loads(action_json)
            self._add_action_from_page(action_data)
        except Exception as e:
            logger.error(f"[SyncRecorder] 处理动作报告出错: {str(e)}")

    def _add_action_from_page(self, action_data: dict[str, Any]) -> None:
        """
        将页面动作添加到列表，并进行智能去重
        
        处理两种selector格式：
        1. 旧格式: 字符串 (向后兼容)
        2. 新格式: {type: 'xxx', value: 'xxx'} 对象 (Playwright标准)
        """
        action_type = action_data.get('type')
        selector = action_data.get('selector')
        
        if not action_type:
            logger.warning(f"[SyncRecorder] 忽略无效动作（缺少type）: {action_data}")
            return
        
        # 冗余click去重逻辑
        if action_type == 'fill' and len(self.recorded_actions) > 0:
            last_action = self.recorded_actions[-1]
            
            # 如果上一个动作是click，且目标相同，移除冗余click
            if last_action['type'] == 'click':
                # 比较选择器
                if self._is_same_selector(last_action['selector'], selector):
                    logger.info(f"[SyncRecorder] 跳过冗余click，后续有fill操作")
                    self.recorded_actions.pop()  # 移除最后一个click
                    self.action_counter -= 1
        
        # 转换selector格式（如果需要）
        # 如果selector已经是对象格式（{type, value}），直接使用
        # 如果selector是字符串格式，保持向后兼容（校验器支持）
        # 这样既支持新的最佳实践，也兼容旧的录制数据
        processed_selector = selector
        
        # 构建参数
        params = {}
        if 'value' in action_data: params['value'] = action_data['value']
        if 'key' in action_data: params['key'] = action_data['key']
        
        # Canvas事件参数
        if action_type in ('canvas_click', 'canvas_drag') and 'params' in action_data:
            params = action_data['params']
        
        # 生成描述
        description = f"{action_type} 操作"
        if 'text' in action_data:
            description = f"{action_type} ({action_data['text']})"
        elif action_type == 'canvas_click':
            x_pct = params.get('x', 0) * 100
            y_pct = params.get('y', 0) * 100
            description = f"Canvas点击 ({x_pct:.1f}%, {y_pct:.1f}%)"
        elif action_type == 'canvas_drag':
            start_x = params.get('start_x', 0) * 100
            start_y = params.get('start_y', 0) * 100
            end_x = params.get('end_x', 0) * 100
            end_y = params.get('end_y', 0) * 100
            description = f"Canvas拖拽 ({start_x:.1f}%,{start_y:.1f}%)->({end_x:.1f}%,{end_y:.1f}%)"
        
        action = self._add_action(
            action_type=action_type,
            selector=processed_selector,
            params=params,
            description=description
        )
        
        if action and self._action_callback:
            try:
                self._action_callback(action)
            except Exception:
                pass

    def _is_same_selector(self, sel1: Any, sel2: Any) -> bool:
        """比较两个选择器是否指向同一元素"""
        if isinstance(sel1, dict) and isinstance(sel2, dict):
            return sel1.get('type') == sel2.get('type') and sel1.get('value') == sel2.get('value')
        return sel1 == sel2

    def _add_action(
        self,
        action_type: str,
        selector: Any = None,
        params: Any = None,
        description: str = '',
    ) -> dict[str, Any]:
        """记录动作"""
        self.action_counter += 1
        action = {
            'id': f'action_{self.action_counter}',
            'order': self.action_counter,
            'type': action_type,
            'selector': selector,
            'params': params if isinstance(params, dict) else {},
            'description': description
        }
        self.recorded_actions.append(action)
        return action

    def start_recording(
        self,
        start_url: str,
        browser_type: str = 'chromium',
    ) -> list[dict[str, Any]]:
        """
        启动录制（阻塞式）
        
        调用后会打开浏览器并阻塞，直到浏览器窗口关闭。
        """
        from playwright.sync_api import sync_playwright
        
        logger.info(f"[SyncRecorder] 启动同步录音: {start_url}")
        self.recorded_actions = []
        self.action_counter = 0
        
        try:
            self.playwright = sync_playwright().start()
            browser_launchers = {
                'chromium': self.playwright.chromium,
                'firefox': self.playwright.firefox,
                'webkit': self.playwright.webkit,
            }
            launcher = browser_launchers.get(browser_type, self.playwright.chromium)
            
            self.browser = launcher.launch(headless=False)
            self.context = self.browser.new_context(viewport={'width': 1280, 'height': 720})
            
            # 注入脚本和绑定方法
            self.context.expose_binding('reportAction', self._handle_action_report)
            self.context.add_init_script(self._get_recording_script())
            
            self.page = self.context.new_page()
            
            # 监听页面关闭事件 - 这是退出循环的最可靠信号
            is_closed = [False]
            def on_page_close():
                logger.info("[SyncRecorder] 录制页面已关闭")
                is_closed[0] = True
            
            self.page.on("close", lambda _: on_page_close())
            
            if start_url and start_url != 'about:blank':
                self.page.goto(start_url)
                self._add_action('navigate', params={'url': start_url}, description=f'打开 {start_url}')

            self.is_recording = True
            
            # 阻塞循环：等待页面或浏览器关闭
            logger.info("[SyncRecorder] 进入阻塞等待状态...")
            while not is_closed[0]:
                # 使用 page.wait_for_timeout 是为了让 Playwright 有机会处理内部事件
                try:
                    if self.page is not None:
                        self.page.wait_for_timeout(500)
                except Exception:
                    # 如果页面已经关闭，wait_for_timeout 可能会抛异常
                    break
                
                # 双重检查浏览器连接
                if self.browser is not None and not self.browser.is_connected():
                    break
            
            return self.recorded_actions.copy()
            
        except Exception as e:
            logger.error(f"[SyncRecorder] 录制过程异常: {str(e)}")
            return self.recorded_actions.copy()
        finally:
            self.cleanup()

    def set_action_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """设置动作实时回调（用于控制台输出等）"""
        self._action_callback = callback

    def cleanup(self) -> None:
        """清理资源"""
        logger.info("[SyncRecorder] 清理资源")
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
        except Exception:
            pass
        self.page = self.context = self.browser = self.playwright = None
        self.is_recording = False
