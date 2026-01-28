"""
同步浏览器录制器 - 完全同步阻塞实现


用户运行 start_recording() 后，程序将阻塞，直到浏览器关闭。
"""
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

class SyncBrowserRecorder:
    """
    同步浏览器录制器 - 阻塞式实现
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_recording = False
        self.recorded_actions: List[Dict[str, Any]] = []
        self.action_counter = 0
        self._action_callback: Optional[Callable] = None
    
    def _get_recording_script(self) -> str:
        """
        获取录制脚本 - 遵循Playwright最佳实践

        生成与执行引擎一致的selector格式：
        1. 优先级顺序: id > testid > name > css
        2. 生成标准化的selector对象格式: {type: 'xxx', value: 'xxx'}
        3. 避免使用动态class名称
        4. 支持文本内容作为备选方案
        """
        return """
        (() => {
            if (window.__webPilotRecorder) return;
            window.__webPilotRecorder = true;
            
            const setupRecorder = () => {
                /**
                 * 生成遵循Playwright最佳实践的selector
                 * 优先级顺序: id > testid > name > css
                 * 
                 * @param {Element} el - 目标元素
                 * @returns {Object} selector对象 {type: string, value: string}
                 */
                const getSelector = (el) => {
                    if (!el) return null;
                    
                    const tag = el.tagName.toLowerCase();
                    
                    // 1. 最高优先级: id (唯一标识符)
                    // 跳过动态生成的id (如: react-, vue-, pv_id_, mui-, UUID等)
                    if (el.id) {
                        const id = el.id.trim();
                        // 扩展的动态ID检测规则
                        const dynamicIdPatterns = [
                            /^(react|vue|ember|ng|angular)/i,        // 框架前缀
                            /^(pv_id_|mui-|headlessui-|radix-)/i,    // UI库动态ID
                            /^(v-|_)\d+/,                            // v-123, _456
                            /^[0-9a-f]{8}-[0-9a-f]{4}/i,             // UUID格式
                            /^\d+$/,                                 // 纯数字ID
                            /^[a-z0-9]{20,}$/i                       // 长hash ID
                        ];
                        
                        const isDynamic = dynamicIdPatterns.some(pattern => pattern.test(id));
                        if (!isDynamic) {
                            return { type: 'id', value: id };
                        }
                        console.log('[JTest] Skipped dynamic ID:', id);
                    }
                    
                    // 2. 次高优先级: data-testid (专门用于测试)
                    if (el.dataset && el.dataset.testid) {
                        return { type: 'testid', value: el.dataset.testid.trim() };
                    }
                    
                    // 3. 第三优先级: name属性 (表单元素)
                    if (el.name) {
                        return { type: 'name', value: el.name.trim() };
                    }
                    
                    // 4. 第四优先级: CSS选择器
                    // 生成稳定且可读的CSS选择器
                    const cssSelector = generateStableCssSelector(el);
                    if (cssSelector) {
                        return { type: 'css', value: cssSelector };
                    }
                    
                    // 5. 最后备选: 不再使用纯标签，直接放弃该元素
                    // 避免生成诸如 css=span / css=div 这种质量极差的选择器
                    console.warn('[JTest] 无法生成稳定的selector，跳过元素:', tag);
                    return null;
                };
                
                /**
                 * 生成稳定的CSS选择器
                 * 避免动态class，优先使用静态class和属性
                 * 
                 * @param {Element} el - 目标元素
                 * @returns {string} 稳定的CSS选择器
                 */
                const generateStableCssSelector = (el) => {
                    if (!el) return null;
                    
                    const tag = el.tagName.toLowerCase();
                    
                    // 特殊处理body
                    if (tag === 'body') return 'body';
                    
                    // 尝试多个策略构建选择器的工具函数
                    const buildSelectors = () => {
                        const selectors = [];
                        
                        // 策略0: 使用文本内容（最稳定）
                        const text = el.textContent?.trim();
                        if (text && text.length > 0 && text.length <= 50) {
                            // 对于button、a、label等交互元素，优先使用文本定位
                            if (['button', 'a', 'label', 'span'].includes(tag)) {
                                // 检查文本是否唯一
                                const allSameTags = document.querySelectorAll(tag);
                                const textMatches = Array.from(allSameTags).filter(m => 
                                    m.textContent?.trim() === text
                                );
                                
                                if (textMatches.length === 1) {
                                    // 使用Playwright的:has-text()伪类
                                    selectors.push(`${tag}:has-text("${text}")`);
                                    console.log('[JTest] Using text-based selector:', `${tag}:has-text("${text}")`);
                                }
                            }
                        }
                        
                        // 策略1: 使用稳定的class名称
                        if (el.className && typeof el.className === 'string') {
                            const classes = el.className.trim().split(/\\s+/);
                            // 过滤掉动态class (包含: 或看起来像hash)
                            const stableClasses = classes.filter(c => {
                                return c && 
                                       !c.includes(':') && 
                                       !/^[a-z0-9]{7,}$/i.test(c) &&  // 避免hash-like class
                                       !/^(css|module|scoped)/i.test(c);
                            });
                            
                            if (stableClasses.length > 0) {
                                // 使用第一个稳定的class
                                selectors.push(`${tag}.${stableClasses[0]}`);
                            }
                        }
                        
                        // 策略2: 使用aria属性 (无障碍访问，通常稳定)
                        if (el.getAttribute('aria-label')) {
                            selectors.push(`${tag}[aria-label="${el.getAttribute('aria-label')}"]`);
                        }
                        if (el.getAttribute('aria-labelledby')) {
                            selectors.push(`${tag}[aria-labelledby="${el.getAttribute('aria-labelledby')}"]`);
                        }
                        if (el.getAttribute('role')) {
                            selectors.push(`${tag}[role="${el.getAttribute('role')}"]`);
                        }
                        
                        // 策略3: 使用type属性 (input/button)
                        if (el.getAttribute('type')) {
                            selectors.push(`${tag}[type="${el.getAttribute('type')}"]`);
                        }
                        
                        // 策略4: 使用href属性 (a标签)
                        if (tag === 'a' && el.getAttribute('href')) {
                            const href = el.getAttribute('href');
                            // 避免过于复杂的URL
                            if (href && href.length < 100) {
                                selectors.push(`${tag}[href="${href}"]`);
                            }
                        }
                        
                        return selectors;
                    };
                    
                    // 选择器质量检查函数
                    const validateSelectorQuality = (selector) => {
                        if (!selector) return false;
                        
                        // 拒绝纯标签选择器
                        const pureTags = ['div', 'span', 'p', 'section', 'article', 'button', 'a', 'input', 'label'];
                        if (pureTags.includes(selector)) {
                            console.warn('[JTest] 拒绝纯标签选择器:', selector);
                            return false;
                        }
                        
                        // 检查是否包含语义属性
                        const hasSemanticInfo = 
                            selector.includes('[placeholder=') ||
                            selector.includes('[name=') ||
                            selector.includes('[aria-label=') ||
                            selector.includes('[title=') ||
                            selector.includes(':has-text(') ||
                            selector.includes('.') ||  // 有class
                            selector.includes('#');    // 有id
                        
                        if (!hasSemanticInfo) {
                            console.warn('[JTest] 选择器缺乏语义属性:', selector);
                            return false;
                        }
                        
                        return true;
                    };
                    
                    // 获取候选选择器
                    const selectors = buildSelectors();
                    
                    // 尝试通过父元素增强选择器的唯一性
                    if (selectors.length > 0) {
                        // 如果当前选择器在页面中是唯一的，直接返回
                        const firstSelector = selectors[0];
                        
                        // 验证选择器质量
                        if (!validateSelectorQuality(firstSelector)) {
                            console.warn('[JTest] 无法生成高质量选择器，跳过录制');
                            return null;  // 返回null会导致该动作不被记录
                        }
                        
                        const matches = document.querySelectorAll(firstSelector);
                        
                        if (matches.length === 1) {
                            return firstSelector;
                        }
                        
                        // 如果有多个匹配，尝试通过父元素限定
                        // 但最多只向上查找2层，避免选择器过长
                        let parent = el.parentElement;
                        let depth = 0;
                        while (parent && parent.tagName && depth < 2) {
                            const parentSelector = generateStableCssSelector(parent);
                            if (parentSelector && parentSelector !== 'body') {
                                const enhancedSelector = `${parentSelector} > ${firstSelector}`;
                                const enhancedMatches = document.querySelectorAll(enhancedSelector);
                                
                                if (enhancedMatches.length === 1) {
                                    return enhancedSelector;
                                }
                            }
                            parent = parent.parentElement;
                            depth++;
                        }
                        
                        // 如果还是不唯一，尝试nth-child
                        if (matches.length > 1) {
                            const index = Array.from(matches).indexOf(el);
                            if (index !== -1) {
                                return `${firstSelector}:nth-child(${index + 1})`;
                            }
                        }
                        
                        // 返回第一个候选选择器（即使不唯一）
                        return firstSelector;
                    }
                    
                    // 如果没有生成任何选择器，记录警告并返回null
                    console.warn('[JTest] 无法生成稳定的selector，跳过录制:', tag);
                    return null;
                };

                /**
                 * 发送动作到后端
                 * 
                 * @param {Object} action - 动作对象
                 */
                const sendAction = (action) => {
                    if (typeof window.reportAction === 'function') {
                        try { 
                            window.reportAction(JSON.stringify(action)); 
                        } catch(e) { 
                            console.error('[JTest] Report error:', e); 
                        }
                    }
                };
                
                /**
                 * 获取元素的文本内容（用于调试）
                 */
                const getElementText = (el) => {
                    if (!el) return '';
                    const text = el.textContent?.trim() || '';
                    return text.length > 30 ? text.substring(0, 30) + '...' : text;
                };

                // 监听点击事件
                document.addEventListener('click', (e) => {
                    const selector = getSelector(e.target);
                    if (selector) {
                        const action = {
                            type: 'click',
                            selector: selector,
                            timestamp: Date.now()
                        };
                        
                        // 添加文本信息用于调试
                        const text = getElementText(e.target);
                        if (text) action.text = text;
                        
                        sendAction(action);
                        console.log('[JTest] Recorded click:', selector, text ? `(${text})` : '');
                    }
                }, true);
                
                // 监听blur事件 - 只在失去焦点时记录最终值
                document.addEventListener('blur', (e) => {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                        const selector = getSelector(e.target);
                        if (!selector) return;
                        
                        // 只记录有内容的输入
                        const value = e.target.value;
                        if (value) {
                            sendAction({
                                type: 'fill',
                                selector: selector,
                                value: value,
                                timestamp: Date.now()
                            });
                            console.log('[JTest] Recorded fill (on blur):', selector, `value="${value}"`);
                        }
                    }
                }, true);
                
                // 监听选择变化事件 (下拉框)
                document.addEventListener('change', (e) => {
                    if (e.target.tagName === 'SELECT') {
                        const selector = getSelector(e.target);
                        if (!selector) return;
                        
                        sendAction({
                            type: 'select',
                            selector: selector,
                            value: e.target.value,
                            timestamp: Date.now()
                        });
                        console.log('[JTest] Recorded select:', selector, `value="${e.target.value}"`);
                    }
                }, true);
                
                console.log('[JTest] Playwright-compatible recorder injected');
            };
            
            setupRecorder();
        })();
        """

    def _handle_action_report(self, source, action_json: str):
        """处理来自页面的动作报告"""
        try:
            action_data = json.loads(action_json)
            self._add_action_from_page(action_data)
        except Exception as e:
            logger.error(f"[SyncRecorder] 处理动作报告出错: {str(e)}")

    def _add_action_from_page(self, action_data: Dict[str, Any]):
        """
        将页面动作添加到列表，并进行智能去重
        
        处理两种selector格式：
        1. 旧格式: 字符串 (向后兼容)
        2. 新格式: {type: 'xxx', value: 'xxx'} 对象 (Playwright标准)
        """
        action_type = action_data.get('type')
        selector = action_data.get('selector')
        
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
        
        # 生成描述
        description = f"{action_type} 操作"
        if 'text' in action_data:
            description = f"{action_type} ({action_data['text']})"
        
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

    def _add_action(self, action_type: str, selector: Any = None,
                    params: Any = None, description: str = '') -> Dict[str, Any]:
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

    def start_recording(self, start_url: str, browser_type: str = 'chromium') -> List[Dict[str, Any]]:
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
                    self.page.wait_for_timeout(500)
                except:
                    # 如果页面已经关闭，wait_for_timeout 可能会抛异常
                    break
                
                # 双重检查浏览器连接
                if not self.browser.is_connected():
                    break
            
            return self.recorded_actions.copy()
            
        except Exception as e:
            logger.error(f"[SyncRecorder] 录制过程异常: {str(e)}")
            return self.recorded_actions.copy()
        finally:
            self.cleanup()

    def set_action_callback(self, callback: Callable):
        """设置动作实时回调（用于控制台输出等）"""
        self._action_callback = callback

    def cleanup(self):
        """清理资源"""
        logger.info("[SyncRecorder] 清理资源")
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
        except:
            pass
        self.page = self.context = self.browser = self.playwright = None
        self.is_recording = False
