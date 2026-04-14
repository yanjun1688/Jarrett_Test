"""
UI测试模块 - 页面元素提取、知识存储、脚本生成和执行

提供完整的UI测试生成流程：
1. PageElementExtractor - 提取页面元素
2. UIElementKnowledgeStore - 元素知识存储
3. UITestScriptGenerator - 测试脚本生成
4. UITestExecutor - 测试执行
"""
from typing import Dict, Any, List, Optional
import logging
import json
import asyncio

from core.agents.rag import KnowledgeRAGAgent
from core.agents.planning.test_planning_agent import TestPlanningAgent
from core.flow.flow_ir import FlowIR, FlowNodeIR
from shared.constants import TestType

logger = logging.getLogger(__name__)


class PageElementExtractor:
    """
    页面元素提取器
    
    使用Playwright访问页面并提取可交互元素
    """
    
    def __init__(self, timeout: int = 30000, headless: bool = True):
        """
        初始化元素提取器
        
        Args:
            timeout: 超时时间（毫秒）
            headless: 是否无头模式
        """
        self.timeout = timeout
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None
    
    async def extract(self, url: str) -> Dict[str, Any]:
        """
        提取页面元素
        
        Args:
            url: 页面URL
            
        Returns:
            提取结果
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                
                # 访问页面
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
                
                # 获取标题
                title = await page.title()
                
                # 提取元素
                elements = await self._extract_elements(page)
                
                await browser.close()
                
                return {
                    "success": True,
                    "url": url,
                    "title": title,
                    "elements": elements,
                    "element_count": len(elements)
                }
                
        except Exception as e:
            logger.error(f"提取页面元素失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def _extract_elements(self, page) -> List[Dict[str, Any]]:
        """通过JavaScript提取页面元素"""
        js_code = """
        () => {
            const elements = [];
            const selectors = ['button', 'a', 'input', 'select', 'textarea'];
            
            selectors.forEach(tag => {
                document.querySelectorAll(tag).forEach((el, index) => {
                    try {
                        // 生成唯一选择器
                        let selector = el.tagName.toLowerCase();
                        if (el.id) {
                            selector = '#' + el.id;
                        } else if (el.className && typeof el.className === 'string') {
                            selector = el.className.split(' ')[0] 
                                ? '.' + el.className.split(' ')[0].trim() 
                                : selector;
                        }
                        
                        // 检查是否可见和可交互
                        const rect = el.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0;
                        const isInteractive = ['button', 'a', 'input', 'select'].includes(el.tagName.toLowerCase());
                        
                        if (isVisible) {
                            elements.push({
                                id: 'elem_' + tag + '_' + index,
                                tag: el.tagName.toLowerCase(),
                                selector: selector,
                                text: el.textContent ? el.textContent.trim().substring(0, 100) : '',
                                type: el.getAttribute('type') || '',
                                name: el.getAttribute('name') || '',
                                placeholder: el.getAttribute('placeholder') || '',
                                href: el.getAttribute('href') || '',
                                is_interactive: isInteractive,
                                position: { x: rect.x, y: rect.y }
                            });
                        }
                    } catch (e) {
                        // 忽略单个元素错误
                    }
                });
            });
            
            return elements;
        }
        """
        
        return await page.evaluate(js_code)
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._browser:
            await self._browser.close()  # type: ignore[union-attr]


class UIElementKnowledgeStore:
    """
    UI元素知识存储
    
    将提取的页面元素存储到知识库，供后续测试生成使用
    """
    
    def __init__(self, rag_agent: Optional[KnowledgeRAGAgent] = None):
        """
        初始化知识存储
        
        Args:
            rag_agent: 知识RAG代理
        """
        self.rag_agent = rag_agent
    
    async def store(
        self,
        page_url: str,
        elements: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        存储页面元素到知识库
        
        Args:
            page_url: 页面URL
            elements: 页面元素列表
            metadata: 额外元数据
            
        Returns:
            存储结果
        """
        if not self.rag_agent:
            return {
                "success": False,
                "error": "RAG agent not configured"
            }
        
        try:
            result = await self.rag_agent.store_ui_elements(
                page_url=page_url,
                elements=elements,
                metadata=metadata
            )
            
            return {
                "success": True,
                "stored_count": result.get("stored_count", 0),
                "page_url": page_url
            }
            
        except Exception as e:
            logger.error(f"存储UI元素失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def query(
        self,
        page_url: Optional[str] = None,
        element_type: Optional[str] = None,
        top_k: int = 20
    ) -> Dict[str, Any]:
        """
        查询UI元素
        
        Args:
            page_url: 页面URL过滤
            element_type: 元素类型过滤
            top_k: 返回数量
            
        Returns:
            查询结果
        """
        if not self.rag_agent:
            return {
                "success": False,
                "elements": [],
                "error": "RAG agent not configured"
            }
        
        try:
            result = await self.rag_agent.query_ui_elements(
                page_url=page_url,
                element_type=element_type,
                top_k=top_k
            )
            
            return {
                "success": True,
                "elements": result.get("elements", []),
                "count": result.get("count", 0)
            }
            
        except Exception as e:
            logger.error(f"查询UI元素失败: {e}")
            return {
                "success": False,
                "elements": [],
                "error": str(e)
            }


class UITestScriptGenerator:
    """
    UI测试脚本生成器
    
    基于页面元素和用户描述生成UI测试FlowIR
    """
    
    def __init__(
        self,
        llm_service: Any = None,
        knowledge_rag_agent: Optional[KnowledgeRAGAgent] = None
    ):
        """
        初始化脚本生成器
        
        Args:
            llm_service: LLM服务
            knowledge_rag_agent: 知识RAG代理
        """
        self.llm_service = llm_service
        self.knowledge_rag_agent = knowledge_rag_agent
    
    async def generate(
        self,
        description: str,
        url: str,
        elements: List[Dict[str, Any]],
        use_knowledge: bool = True
    ) -> Dict[str, Any]:
        """
        生成UI测试脚本
        
        Args:
            description: 用户描述
            url: 页面URL
            elements: 页面元素
            use_knowledge: 是否使用知识库
            
        Returns:
            生成结果，包含FlowIR
        """
        try:
            # 检索知识库上下文
            context = {}
            if use_knowledge and self.knowledge_rag_agent:
                rag_result = await self.knowledge_rag_agent.query(
                    query=f"UI test for {description}",
                    top_k=3,
                    document_type="ui_test",
                    use_llm=False
                )
                context["documents"] = rag_result.get("documents", [])
            
            # 如果有LLM，使用LLM生成
            if self.llm_service:
                return await self._generate_with_llm(description, url, elements, context)
            
            # 否则使用模板生成
            return await self._generate_with_template(description, url, elements)
            
        except Exception as e:
            logger.error(f"生成UI测试脚本失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_with_llm(
        self,
        description: str,
        url: str,
        elements: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用LLM生成测试脚本"""
        # 构建提示
        elements_desc = json.dumps(elements, indent=2, ensure_ascii=False)
        
        prompt = f"""请根据以下信息生成UI测试流程：

用户需求：{description}
目标页面：{url}

页面元素：
{elements_desc}

请生成符合以下格式的FlowIR JSON：
{{
    "nodes": {{
        "node_1": {{
            "id": "node_1",
            "node_type": "ui_navigate",
            "parameters": {{"url": "..."}},
            "metadata": {{"name": "..."}}
        }}
    }},
    "start_node": "node_1",
    "metadata": {{"name": "...", "test_type": "ui"}}
}}

注意：只生成有效的JSON，不要有其他内容。"""
        
        response = await self.llm_service.generate(
            prompt=prompt,
            system_message="你是一个UI测试工程师，负责生成自动化测试脚本。"
        )
        
        # 解析响应
        try:
            flow_dict = json.loads(response)
            flow_ir = FlowIR(
                metadata=flow_dict.get("metadata", {
                    "name": description[:50],
                    "test_type": TestType.UI
                })
            )
            
            for node_id, node_data in flow_dict.get("nodes", {}).items():
                node = FlowNodeIR(
                    id=node_id,
                    node_type=node_data.get("node_type", "unknown"),
                    parameters=node_data.get("parameters", {}),
                    metadata=node_data.get("metadata", {})
                )
                flow_ir.add_node(node)
            
            if flow_dict.get("start_node"):
                flow_ir.start_node = flow_dict["start_node"]
            
            return {
                "success": True,
                "flow_ir": flow_ir.to_dict()
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}")
            # 回退到模板
            return await self._generate_with_template(description, url, elements)
    
    async def _generate_with_template(
        self,
        description: str,
        url: str,
        elements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用模板生成测试脚本"""
        flow_ir = FlowIR(
            metadata={
                "name": f"UI测试: {description[:50]}",
                "description": description,
                "test_type": TestType.UI,
                "url": url
            }
        )
        
        # 导航节点
        nav_node = FlowNodeIR(
            id="node_navigate",
            node_type="ui_navigate",
            parameters={"url": url},
            metadata={"name": "打开页面", "description": f"导航到{url}"}
        )
        flow_ir.add_node(nav_node)
        
        # 根据元素生成操作节点
        current_node = nav_node
        
        # 查找可交互元素
        interactive_elements = [e for e in elements if e.get("is_interactive", False)]
        
        for i, element in enumerate(interactive_elements[:5]):  # 最多5个操作
            action_type = self._get_action_type(element)
            action_node = FlowNodeIR(
                id=f"node_action_{i}",
                node_type=action_type,
                parameters={
                    "selector": element.get("selector", ""),
                    "value": element.get("value", ""),
                    "wait_time": 2
                },
                depends_on=[current_node.id],
                metadata={
                    "name": f"操作: {element.get('text', element.get('tag', 'element'))}",
                    "description": element.get("text", ""),
                    "element_id": element.get("id")
                }
            )
            flow_ir.add_node(action_node)
            current_node.on_success = action_node.id
            current_node = action_node
        
        # 添加断言节点
        assert_node = FlowNodeIR(
            id="node_assert",
            node_type="ui_assert",
            parameters={
                "selector": "body",
                "expected": "visible"
            },
            depends_on=[current_node.id],
            metadata={"name": "验证页面加载完成"}
        )
        flow_ir.add_node(assert_node)
        current_node.on_success = "node_assert"
        
        flow_ir.start_node = "node_navigate"
        
        return {
            "success": True,
            "flow_ir": flow_ir.to_dict()
        }
    
    def _get_action_type(self, element: Dict[str, Any]) -> str:
        """根据元素类型确定操作类型"""
        tag = element.get("tag", "").lower()
        el_type = element.get("type", "").lower()
        
        if tag == "a":
            return "ui_click"
        elif tag == "input":
            if el_type in ["text", "password", "email", "search"]:
                return "ui_input"
            elif el_type in ["checkbox", "radio"]:
                return "ui_click"
            return "ui_input"
        elif tag == "button" or tag == "select":
            return "ui_click"
        elif tag == "textarea":
            return "ui_input"
        
        return "ui_click"


class UITestExecutor:
    """
    UI测试执行器
    
    执行UI测试FlowIR
    """
    
    def __init__(self, playwright_engine: Any = None):
        """
        初始化执行器
        
        Args:
            playwright_engine: Playwright引擎
        """
        self.playwright_engine = playwright_engine
    
    async def execute(
        self,
        flow_ir: FlowIR,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行UI测试
        
        Args:
            flow_ir: 测试流程IR
            context: 执行上下文
            
        Returns:
            执行结果
        """
        context = context or {}
        results = []
        
        try:
            # 初始化Playwright
            if not self.playwright_engine:
                from test_ui_app.playwright_engine import PlaywrightEngine
                self.playwright_engine = PlaywrightEngine()
                await self.playwright_engine.initialize()
            
            # 获取执行顺序
            execution_order = self._get_execution_order(flow_ir)
            
            # 执行每个节点
            for node_id in execution_order:
                node = flow_ir.nodes.get(node_id)
                if not node:
                    continue
                
                result = await self._execute_node(node, context)
                results.append({
                    "node_id": node_id,
                    "success": result.get("success", False),
                    "data": result
                })
                
                # 检查是否失败
                if not result.get("success", False):
                    return {
                        "success": False,
                        "error": f"节点 {node_id} 执行失败",
                        "results": results
                    }
            
            return {
                "success": True,
                "results": results,
                "total_nodes": len(execution_order),
                "executed_nodes": len(results)
            }
            
        except Exception as e:
            logger.error(f"UI测试执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": results
            }
        
        finally:
            if self.playwright_engine:
                try:
                    cleanup = getattr(self.playwright_engine, 'cleanup', None)
                    if cleanup:
                        if asyncio.iscoroutinefunction(cleanup):
                            await cleanup()
                        else:
                            cleanup()
                except Exception:
                    pass
    
    def _get_execution_order(self, flow_ir: FlowIR) -> List[str]:
        """获取节点执行顺序"""
        order = []
        visited = set()
        
        def visit(node_id: str):
            if node_id in visited or node_id not in flow_ir.nodes:
                return
            visited.add(node_id)
            order.append(node_id)
            
            node = flow_ir.nodes.get(node_id)
            if node and node.on_success:
                visit(node.on_success)
        
        if flow_ir.start_node:
            visit(flow_ir.start_node)
        
        return order
    
    async def _execute_node(
        self,
        node: FlowNodeIR,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行单个节点"""
        node_type = node.node_type
        
        # 检查是否使用mock引擎
        is_mock = getattr(self.playwright_engine, '_is_mock', False)
        
        try:
            if is_mock:
                # Mock引擎，返回成功
                return {"success": True, "action": f"mock_{node_type}", "node_id": node.id}
            
            assert self.playwright_engine.page is not None, "playwright_engine.page should not be None"
            
            if node_type == "ui_navigate":
                url = node.parameters.get("url", "")
                await self.playwright_engine.page.goto(url, wait_until="domcontentloaded")  # type: ignore[union-attr]
                return {"success": True, "action": "navigate", "url": url}
            
            elif node_type == "ui_click":
                selector = node.parameters.get("selector", "")
                await self.playwright_engine.page.click(selector)  # type: ignore[union-attr]
                return {"success": True, "action": "click", "selector": selector}
            
            elif node_type == "ui_input":
                selector = node.parameters.get("selector", "")
                value = node.parameters.get("value", "")
                await self.playwright_engine.page.fill(selector, value)  # type: ignore[union-attr]
                return {"success": True, "action": "input", "selector": selector, "value": value}
            
            elif node_type == "ui_assert":
                selector = node.parameters.get("selector", "body")
                expected = node.parameters.get("expected", "visible")
                
                if expected == "visible":
                    await self.playwright_engine.page.wait_for_selector(selector, state="visible")
                    return {"success": True, "action": "assert", "selector": selector}
                
                return {"success": True, "action": "assert", "selector": selector}
            
            else:
                logger.warning(f"未知节点类型: {node_type}")
                return {"success": True, "action": "skip", "node_type": node_type}
                
        except Exception as e:
            logger.error(f"节点执行失败: {e}")
            return {"success": False, "error": str(e)}


class UITestWorkflow:
    """
    UI测试完整工作流
    
    整合元素提取、存储、生成和执行
    """
    
    def __init__(
        self,
        llm_service: Any = None,
        knowledge_rag_agent: Optional[KnowledgeRAGAgent] = None,
        playwright_engine: Any = None
    ):
        self.extractor = PageElementExtractor()
        self.knowledge_store = UIElementKnowledgeStore(rag_agent=knowledge_rag_agent)
        self.generator = UITestScriptGenerator(
            llm_service=llm_service,
            knowledge_rag_agent=knowledge_rag_agent
        )
        self.executor = UITestExecutor(playwright_engine=playwright_engine)
    
    async def run(
        self,
        description: str,
        url: str,
        store_elements: bool = True,
        execute_test: bool = True
    ) -> Dict[str, Any]:
        """
        运行完整的UI测试工作流
        
        Args:
            description: 用户描述
            url: 页面URL
            store_elements: 是否存储元素到知识库
            execute_test: 是否执行测试
            
        Returns:
            完整工作流结果
        """
        result = {
            "description": description,
            "url": url,
            "steps": {}
        }
        
        # 1. 提取元素
        extract_result = await self.extractor.extract(url)
        result["steps"]["extraction"] = extract_result
        
        if not extract_result.get("success"):
            result["success"] = False
            result["error"] = extract_result.get("error")
            return result
        
        elements = extract_result.get("elements", [])
        
        # 2. 存储到知识库
        if store_elements:
            store_result = await self.knowledge_store.store(url, elements)
            result["steps"]["storage"] = store_result
        
        # 3. 生成测试脚本
        generate_result = await self.generator.generate(
            description=description,
            url=url,
            elements=elements
        )
        result["steps"]["generation"] = generate_result
        
        if not generate_result.get("success"):
            result["success"] = False
            result["error"] = generate_result.get("error") or "Generation failed with unknown error"
            return result
        
        # 4. 执行测试
        if execute_test:
            flow_ir_dict = generate_result.get("flow_ir", {})
            flow_ir = FlowIR.from_dict(flow_ir_dict)
            
            exec_result = await self.executor.execute(flow_ir)
            result["steps"]["execution"] = exec_result
            result["success"] = exec_result.get("success", False)
        else:
            result["success"] = True
        
        return result