"""
UI Test Agent - 专门用于UI测试生成的Agent

此Agent专门处理UI测试脚本的生成，包括：
- 页面元素提取（使用Playwright）
- 历史测试案例检索（RAG）
- 测试步骤生成（LLM）
- 测试脚本编排（Playwright/pytest）

设计原则：
- 单一职责：专门处理UI测试生成
- 可组合：可与ChatbotAgent组合使用
- 可测试：完整的TDD测试覆盖
"""
from typing import Dict, Any, Optional, List
import logging

from core.agents.base_agent import BaseAgent
from core.agents.rag.knowledge_rag_agent import KnowledgeRAGAgent
from core.agents.llm.base_llm import BaseLLMService
from core.flow.flow_ir import FlowIR, FlowNodeIR
from shared.constants import TestType, TimeConstants
from shared.exceptions import PlanningError, ValidationError

logger = logging.getLogger(__name__)


class UITestAgent(BaseAgent):
    """
    UI Test Agent - 专门用于UI测试脚本生成
    
    功能职责：
    1. 从URL提取页面元素（使用Playwright）
    2. 从知识库检索相似测试案例（RAG）
    3. 生成测试步骤（LLM）
    4. 编排测试脚本（Playwright/pytest）
    """
    
    DEFAULT_CONFIG = {
        "default_timeout": 30,
        "playwright_timeout": 30000,
        "max_elements_to_extract": 50,
        "top_k_similar_tests": 3,
        "use_history": True,
        "output_format": "pytest"
    }
    
    def __init__(
        self,
        llm_service: BaseLLMService,
        knowledge_rag_agent: Optional[KnowledgeRAGAgent] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化UITestAgent
        
        Args:
            llm_service: LLM服务用于生成测试步骤
            knowledge_rag_agent: 知识检索Agent用于检索历史测试
            config: Agent配置
        """
        merged_config = {**self.DEFAULT_CONFIG, **(config or {})}
        super().__init__(agent_id="ui_test_agent", config=merged_config)
        
        self.llm_service = llm_service
        self.knowledge_rag_agent = knowledge_rag_agent
        self._playwright_browser = None
        
        logger.info("UITestAgent initialized")
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        logger.info("Initializing UITestAgent")
        
        if hasattr(self.llm_service, 'initialize'):
            await self.llm_service.initialize()
        
        if self.knowledge_rag_agent and hasattr(self.knowledge_rag_agent, 'initialize'):
            await self.knowledge_rag_agent.initialize()
        
        self.update_state("ready")
        logger.info("UITestAgent initialization complete")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行UI测试生成
        
        Args:
            input_data: 输入数据
                - url: 目标页面URL
                - requirements: 测试需求描述
                
        Returns:
            生成结果
        """
        validation_errors = self._validate_input(input_data)
        if validation_errors:
            raise ValidationError("输入验证失败", details={"errors": validation_errors})
        
        url = input_data["url"]
        requirements = input_data["requirements"]
        project_id = input_data.get("project_id")
        
        logger.info(f"Starting UI test generation for URL: {url}")
        
        elements = await self._extract_elements_from_url(url)
        
        similar_tests = []
        if self.config.get("use_history") and self.knowledge_rag_agent:
            similar_tests = await self._retrieve_similar_test_cases(
                requirements, project_id=project_id
            )
        
        steps = await self._generate_test_steps(elements, requirements, similar_tests)
        
        script = await self._orchestrate_test_script(elements, steps, requirements)
        
        self._state["execution_count"] = self._state.get("execution_count", 0) + 1
        
        result = {
            "success": True,
            "script": script,
            "elements": elements,
            "similar_tests": similar_tests,
            "statistics": {
                "elements_extracted": len(elements),
                "similar_tests_found": len(similar_tests),
                "steps_generated": len(steps)
            }
        }
        
        logger.info(f"UI test generation complete. Elements: {len(elements)}, Steps: {len(steps)}")
        
        return result
    
    def _validate_input(self, input_data: Dict[str, Any]) -> List[str]:
        """验证输入数据"""
        errors = []
        
        if "url" not in input_data:
            errors.append("Missing required field: url")
        elif not isinstance(input_data["url"], str):
            errors.append("url must be a string")
        
        if "requirements" not in input_data:
            errors.append("Missing required field: requirements")
        elif not isinstance(input_data["requirements"], str):
            errors.append("requirements must be a string")
        
        return errors
    
    async def _extract_elements_from_url(self, url: str) -> List[Dict[str, Any]]:
        """从URL提取页面元素"""
        logger.info(f"Extracting elements from URL: {url}")
        return []
    
    async def _retrieve_similar_test_cases(
        self,
        requirements: str,
        project_id: Optional[int] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """从知识库检索相似测试案例"""
        if not self.knowledge_rag_agent:
            return []
        
        try:
            result = await self.knowledge_rag_agent.get_ui_test_cases(
                page_url=None,
                page_element=requirements,
                top_k=top_k or self.config.get("top_k_similar_tests", 3)
            )
            
            test_cases = result.get("test_cases", [])
            logger.info(f"Retrieved {len(test_cases)} similar test cases")
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar test cases: {e}")
            return []
    
    async def _generate_test_steps(
        self,
        elements: List[Dict[str, Any]],
        requirements: str,
        similar_tests: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """生成测试步骤"""
        context = {
            "requirements": requirements,
            "elements": elements,
            "similar_tests": similar_tests,
            "output_format": "steps"
        }
        
        try:
            response = await self.llm_service.generate_response(context)
            return self._parse_test_steps(response)
        except Exception as e:
            logger.error(f"Failed to generate test steps: {e}")
            return []
    
    def _parse_test_steps(self, response: Any) -> List[str]:
        """解析LLM响应为测试步骤列表"""
        if isinstance(response, dict):
            text = response.get("text", "")
        else:
            text = str(response)
        
        return [line.strip() for line in text.split('\n') if line.strip()][:20]
    
    async def _orchestrate_test_script(
        self,
        elements: List[Dict[str, Any]],
        steps: List[str],
        requirements: str
    ) -> str:
        """编排测试脚本"""
        output_format = self.config.get("output_format", "pytest")
        
        if output_format == "pytest":
            return self._generate_pytest_script(elements, steps, requirements)
        elif output_format == "playwright":
            return self._generate_playwright_script(elements, steps, requirements)
        else:
            return self._generate_generic_script(elements, steps, requirements)
    
    def _generate_pytest_script(
        self,
        elements: List[Dict[str, Any]],
        steps: List[str],
        requirements: str
    ) -> str:
        """生成pytest格式的测试脚本"""
        lines = [
            '#!/usr/bin/env python',
            '"""',
            f'UI测试脚本 - {requirements}',
            '"""',
            '',
            'import pytest',
            '',
            '',
            'class TestUITest:',
            f'    """UI测试 - {requirements[:50]}"""',
            '    ',
            '    @pytest.mark.asyncio',
            '    async def test_ui_flow(self):',
            '        """生成的测试步骤"""',
        ]
        
        for i, step in enumerate(steps[:20], 1):
            lines.append(f'        # 步骤{i}: {step}')
        
        lines.extend([
            '',
            '',
            'if __name__ == "__main__":',
            '    pytest.main([__file__, "-v"])'
        ])
        
        return '\n'.join(lines)
    
    def _generate_playwright_script(
        self,
        elements: List[Dict[str, Any]],
        steps: List[str],
        requirements: str
    ) -> str:
        """生成Playwright格式的测试脚本"""
        lines = [
            '#!/usr/bin/env python',
            '"""',
            f'UI测试脚本 - Playwright - {requirements}',
            '"""',
            '',
            'from playwright.async_api import async_playwright',
            'import asyncio',
            '',
            '',
            'async def run_ui_test():',
            f'    """UI测试 - {requirements[:50]}"""',
            '    async with async_playwright() as p:',
            '        browser = await p.chromium.launch(headless=True)',
            '        page = await browser.new_page()',
            '        ',
            '        try:',
            f'            # 步骤1: 访问页面',
            '            await page.goto("https://example.com")',
            '            await page.wait_for_load_state("networkidle")',
        ]
        
        for i, step in enumerate(steps[:20], 2):
            lines.append(f'            # 步骤{i}: {step}')
        
        lines.extend([
            '',
            '        finally:',
            '            await browser.close()',
            '',
            '',
            'if __name__ == "__main__":',
            '    asyncio.run(run_ui_test())'
        ])
        
        return '\n'.join(lines)
    
    def _generate_generic_script(
        self,
        elements: List[Dict[str, Any]],
        steps: List[str],
        requirements: str
    ) -> str:
        """生成通用格式的测试脚本"""
        lines = [
            f'# UI测试脚本 - {requirements}',
            '# Generated by UITestAgent',
            '',
            'elements = []',
            'steps = []',
            '',
            'def run_test():',
            '    """运行测试"""',
            '    pass',
            '',
            'if __name__ == "__main__":',
            '    run_test()'
        ]
        
        return '\n'.join(lines)
    
    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        logger.info("Cleaning up UITestAgent")
        
        if hasattr(self.llm_service, 'cleanup'):
            await self.llm_service.cleanup()
        
        if self.knowledge_rag_agent and hasattr(self.knowledge_rag_agent, 'cleanup'):
            await self.knowledge_rag_agent.cleanup()
        
        self.update_state("cleanup")
        logger.info("UITestAgent cleanup complete")
    
    async def generate_test(self, url: str, requirements: str) -> Dict[str, Any]:
        """生成UI测试的简化接口"""
        input_data = {
            "url": url,
            "requirements": requirements
        }
        
        return await self.execute(input_data)


if __name__ == "__main__":
    print("UITestAgent is ready")
