"""
GenerateUI Test Tool
根据用户描述生成 UI 自动化测试脚本（Playwright）
"""
from typing import Dict, Any, List, Optional
import logging
import re

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GenerateUITestTool(BaseTool):
    """根据用户描述生成 UI 自动化测试脚本（Playwright）"""
    
    def __init__(self, llm_service=None):
        super().__init__(
            name="generate_ui_test",
            description="生成 UI/Web 自动化测试脚本。当用户需要测试网页功能、表单、按钮点击等UI交互时调用。",
            version="1.0.0"
        )
        self._llm_service = llm_service
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "url": {
                "type": "string",
                "description": "要测试的网页 URL"
            },
            "description": {
                "type": "string",
                "description": "测试场景描述，如'测试登录功能'"
            },
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要执行的操作列表，如 ['点击登录按钮', '输入用户名']"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["description"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        生成 UI 测试脚本
        
        Args:
            url: 要测试的网页 URL
            description: 测试场景描述
            actions: 要执行的操作列表
            
        Returns:
            包含测试脚本的 ToolResult
        """
        if not self._llm_service:
            return ToolResult(
                success=False,
                data={},
                error="LLM service is required but not provided"
            )
        
        url = kwargs.get("url", "")
        description = kwargs.get("description")
        actions = kwargs.get("actions", [])
        
        if not description:
            return ToolResult(
                success=False,
                data={},
                error="Missing required parameter: description"
            )
        
        try:
            if not actions:
                actions = self._get_default_actions(description)
            
            prompt = self._build_prompt(url, description, actions)
            llm_response = await self._llm_service.generate(prompt=prompt)
            
            script_data = self._parse_script_response(llm_response)
            user_options = self._generate_user_options(script_data)
            
            result_data = {
                "script": script_data,
                "user_options": user_options
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "url": url,
                    "description": description
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to generate UI test: {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"LLM generation error: {str(e)}"
            )
    
    def _build_prompt(self, url: str, description: str, actions: List[str]) -> str:
        """构建 LLM Prompt"""
        actions_str = "\n".join(f"- {action}" for action in actions) if actions else "- 根据描述自动推断操作"
        url_context = f"目标 URL: {url}\n" if url else "URL: 由用户提供\n"
        
        prompt = f"""你是一个 UI 自动化测试专家，精通 Playwright 和 Python。

{url_context}测试场景: {description}

需要执行的操作:
{actions_str}

请生成一个完整的 Playwright 测试脚本，要求：
1. 使用 Python 和 playwright.sync_api
2. 包含完整的测试函数定义
3. 添加适当的断言来验证测试结果
4. 添加必要的注释说明测试步骤
5. 处理可能的异常情况

请直接返回 Python 代码，不要包含额外的解释文字。代码应该可以直接运行。"""
        return prompt
    
    def _parse_script_response(self, response: str) -> Dict[str, Any]:
        """解析脚本响应"""
        code = response
        
        if "```python" in response:
            code_match = re.search(r'```python\s*([\s\S]*?)\s*```', response)
            if code_match:
                code = code_match.group(1).strip()
        elif "```" in response:
            code_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
            if code_match:
                code = code_match.group(1).strip()
        
        actions = self._extract_actions_from_code(code)
        
        return {
            "language": "python",
            "framework": "playwright",
            "code": code,
            "actions": actions
        }
    
    def _extract_actions_from_code(self, code: str) -> List[Dict[str, Any]]:
        """从代码中提取操作"""
        actions = []
        
        goto_pattern = r"page\.goto\(['\"]([^'\"]+)['\"]"
        for match in re.finditer(goto_pattern, code):
            actions.append({
                "type": "navigate",
                "selector": None,
                "value": match.group(1)
            })
        
        fill_pattern = r"page\.fill\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]*)['\"]"
        for match in re.finditer(fill_pattern, code):
            actions.append({
                "type": "fill",
                "selector": match.group(1),
                "value": match.group(2)
            })
        
        click_pattern = r"page\.click\(['\"]([^'\"]+)['\"]"
        for match in re.finditer(click_pattern, code):
            actions.append({
                "type": "click",
                "selector": match.group(1),
                "value": None
            })
        
        return actions
    
    def _get_default_actions(self, description: str) -> List[str]:
        """根据描述获取默认操作"""
        desc_lower = description.lower()
        
        if "登录" in description or "login" in desc_lower:
            return [
                "打开登录页面",
                "输入用户名",
                "输入密码",
                "点击登录按钮",
                "验证登录成功"
            ]
        elif "注册" in description or "register" in desc_lower or "signup" in desc_lower:
            return [
                "打开注册页面",
                "填写注册表单",
                "点击注册按钮",
                "验证注册成功"
            ]
        elif "表单" in description or "form" in desc_lower:
            return [
                "打开表单页面",
                "填写表单字段",
                "提交表单",
                "验证提交结果"
            ]
        elif "搜索" in description or "search" in desc_lower:
            return [
                "打开搜索页面",
                "输入搜索关键词",
                "执行搜索",
                "验证搜索结果"
            ]
        else:
            return [
                "打开页面",
                "执行主要操作",
                "验证结果"
            ]
    
    def _generate_user_options(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """生成用户选项"""
        return {
            "can_save": True,
            "can_execute": True,
            "save_options": [
                {"label": "保存为测试脚本", "action": "save_script"},
                {"label": "保存到测试套件", "action": "save_to_suite"}
            ],
            "execute_options": [
                {"label": "立即执行", "action": "execute_now"},
                {"label": "稍后执行", "action": "execute_later"}
            ],
            "suggested_action": "是否保存或执行这个测试脚本？"
        }