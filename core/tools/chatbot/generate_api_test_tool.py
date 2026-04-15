"""
GenerateAPI Test Tool
根据用户描述生成 API 测试用例
"""
from typing import Dict, Any, List, Optional
import logging
import json
import re

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GenerateAPITestTool(BaseTool):
    """根据用户描述生成 API 测试用例"""
    
    def __init__(self, llm_service: Optional[Any] = None) -> None:
        super().__init__(
            name="generate_api_test",
            description="生成 API/接口测试脚本。当用户需要测试 REST API、HTTP 接口时调用。",
            version="1.0.0"
        )
        self._llm_service = llm_service
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "endpoint": {
                "type": "string",
                "description": "API 端点路径，如 /api/login"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP 方法"
            },
            "description": {
                "type": "string",
                "description": "测试场景描述"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["endpoint", "method"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        生成 API 测试用例
        
        Args:
            endpoint: API 端点路径
            method: HTTP 方法
            description: 测试场景描述
            
        Returns:
            包含测试用例的 ToolResult
        """
        if not self._llm_service:
            return ToolResult(
                success=False,
                data={},
                error="LLM service is required but not provided"
            )
        
        endpoint = kwargs.get("endpoint")
        method = kwargs.get("method", "GET").upper()
        description = kwargs.get("description", "")
        
        if not endpoint:
            return ToolResult(
                success=False,
                data={},
                error="Missing required parameter: endpoint"
            )
        
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        if method not in valid_methods:
            return ToolResult(
                success=False,
                data={},
                error=f"Invalid HTTP method: {method}. Valid methods are: {', '.join(valid_methods)}"
            )
        
        try:
            prompt = self._build_prompt(endpoint, method, description)
            llm_response = await self._llm_service.generate(prompt=prompt)
            
            parsed_response = self._parse_llm_response(llm_response)
            test_cases = parsed_response.get("test_cases", [])
            
            summary = self._generate_summary(test_cases)
            user_options = self._generate_user_options(test_cases)
            
            result_data = {
                "test_cases": test_cases,
                "summary": summary,
                "user_options": user_options
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "endpoint": endpoint,
                    "method": method,
                    "total_cases": len(test_cases)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to generate API test: {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"LLM generation error: {str(e)}"
            )
    
    def _build_prompt(self, endpoint: str, method: str, description: str) -> str:
        """构建 LLM Prompt"""
        prompt = f"""你是一个 API 测试专家。请根据以下信息生成测试用例：

API 端点: {endpoint}
HTTP 方法: {method}
描述: {description or '无具体描述'}

请生成包含以下内容的测试用例（JSON 格式）：
1. 正向测试用例（正常场景）
2. 负向测试用例（异常场景，如参数缺失、类型错误等）
3. 边界测试用例（如空值、超长字符串等）

返回格式（必须是有效的 JSON）：
{{
    "test_cases": [
        {{
            "name": "测试用例名称",
            "description": "测试用例描述",
            "endpoint": "{endpoint}",
            "method": "{method}",
            "headers": {{"Content-Type": "application/json"}},
            "body": {{}},
            "expected_status": 200,
            "test_type": "positive",
            "validation_rules": [
                {{"type": "status_code", "expected": 200}}
            ]
        }}
    ]
}}

请直接返回 JSON 格式的测试用例，不要包含其他文字说明。"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 返回的响应"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                parsed: Dict[str, Any] = json.loads(json_str)
                return parsed
            
            return {"test_cases": []}
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {response[:200]}")
            return {"test_cases": self._generate_fallback_test_cases()}
    
    def _generate_fallback_test_cases(self) -> List[Dict[str, Any]]:
        """生成后备测试用例"""
        return [
            {
                "name": "基本正向测试",
                "description": "基本正向测试用例",
                "endpoint": "/api/placeholder",
                "method": "GET",
                "headers": {"Content-Type": "application/json"},
                "body": {},
                "expected_status": 200,
                "test_type": "positive",
                "validation_rules": [{"type": "status_code", "expected": 200}]
            }
        ]
    
    def _generate_summary(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成测试用例摘要"""
        total = len(test_cases)
        positive = sum(1 for tc in test_cases if tc.get("test_type") == "positive")
        negative = sum(1 for tc in test_cases if tc.get("test_type") == "negative")
        boundary = sum(1 for tc in test_cases if tc.get("test_type") == "boundary")
        
        return {
            "total_cases": total,
            "positive_cases": positive,
            "negative_cases": negative,
            "boundary_cases": boundary
        }
    
    def _generate_user_options(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成用户选项"""
        return {
            "can_save": True,
            "can_execute": True,
            "save_options": [
                {"label": "保存为新测试用例", "action": "save_new"},
                {"label": "追加到现有集合", "action": "save_append"}
            ],
            "execute_options": [
                {"label": "立即执行", "action": "execute_now"},
                {"label": "稍后执行", "action": "execute_later"}
            ],
            "suggested_action": "您想要保存还是执行这些测试用例？"
        }