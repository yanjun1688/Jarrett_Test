"""
GenerateAPI Test Tool
根据用户描述生成 API 测试配置（JSON 格式）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.tools.base_tool import BaseTool, ToolResult
from core.agents.llm import create_llm_service
from core.schemas.script_config import SCRIPT_CONFIG_EXAMPLE

logger = logging.getLogger(__name__)


class GenerateAPITestTool(BaseTool):
    """根据用户描述生成 API 测试用例"""

    def __init__(self, llm_service: Optional[Any] = None) -> None:
        super().__init__(
            name='generate_api_test',
            description='生成 API/接口测试脚本。当用户需要测试 REST API、HTTP 接口时调用。',
            version='2.0.0'
        )
        self._llm_service = llm_service

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            'project_id': {
                'type': 'integer',
                'description': '项目 ID（必填）。如果用户未提供，请先询问用户选择项目。'
            },
            'endpoint': {
                'type': 'string',
                'description': 'API 端点路径，如 /api/login'
            },
            'method': {
                'type': 'string',
                'enum': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
                'description': 'HTTP 方法'
            },
            'description': {
                'type': 'string',
                'description': '测试场景描述'
            },
            'module_id': {
                'type': 'integer',
                'description': '模块 ID（可选）'
            }
        }

    def _get_required_parameters(self) -> List[str]:
        return ['project_id', 'endpoint', 'method']

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        生成 API 测试用例，直接调用 LLM

        Args:
            project_id: 项目 ID（必填）
            endpoint: API 端点路径
            method: HTTP 方法
            description: 测试场景描述
            module_id: 模块 ID

        Returns:
            包含测试用例的 ToolResult
        """
        project_id = kwargs.get('project_id')
        endpoint = kwargs.get('endpoint')
        method = kwargs.get('method', 'GET').upper()
        description = kwargs.get('description', '')
        module_id = kwargs.get('module_id')

        if not project_id:
            return ToolResult(
                success=False,
                data={},
                error='缺少项目 ID。请先询问用户选择一个项目。'
            )

        if not endpoint:
            return ToolResult(
                success=False,
                data={},
                error='缺少必填参数: endpoint'
            )

        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if method not in valid_methods:
            return ToolResult(
                success=False,
                data={},
                error=f'无效的 HTTP 方法: {method}。有效方法: {", ".join(valid_methods)}'
            )

        try:
            # 初始化 LLM 服务（如果未提供）
            if not self._llm_service:
                self._llm_service = create_llm_service(provider='zhipu')

            example = json.dumps(SCRIPT_CONFIG_EXAMPLE, indent=2, ensure_ascii=False)

            prompt = f"""请根据以下 API 信息生成 API 测试配置（JSON 格式）。

API 端点: {endpoint}
HTTP 方法: {method}
描述: {description}

请生成一个 JSON 对象，包含 variables、setup、steps 等字段。参考格式如下：

{example}

要求：
1. variables 中定义需要的变量，如 base_url、token 等
2. setup 中完成前置操作（如登录获取 token）
3. steps 中完成主要的测试请求
4. 每个步骤包含 name、request（含 method、url、headers、json）、extract（需要提取变量时）和 assertions
5. 断言规则：
   - 验证业务状态码时使用 jsonpath 断言：{{"type": "jsonpath", "expression": "$.code", "expected": 200}}
   - 除非明确需要验证 HTTP 响应码（如 401 未授权），否则不要使用 status_code 断言
   - 注意：很多 API 无论成功失败都返回 HTTP 200，业务状态在 response body 的 code 字段中
6. 使用 {{{{variable}}}} 模板语法引用变量
7. 输出格式化的 JSON（带缩进），不要输出压缩成一行

注意：只输出 JSON 本身，不要用 markdown 包裹。"""

            response = await self._llm_service.generate(
                prompt=prompt,
                system_message='你是 API 测试专家，擅长生成 JSON 格式的 API 测试配置。',
                temperature=0.3,
                max_tokens=3000
            )

            code = self._extract_json(response)

            user_options = self._generate_user_options()

            return ToolResult(
                success=True,
                data={
                    'script': {
                        'format': 'json_config',
                        'code': code,
                    },
                    'user_options': user_options,
                },
                metadata={
                    'endpoint': endpoint,
                    'method': method,
                    'project_id': project_id,
                    'module_id': module_id,
                },
            )

        except Exception as e:
            logger.error(f'Failed to generate API test: {e}')
            return ToolResult(
                success=False,
                data={},
                error=f'Generation error: {str(e)}'
            )

    def _extract_json(self, response: str) -> str:
        """从 LLM 响应中提取 JSON"""
        import re

        # 尝试提取 markdown json 代码块
        match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 尝试直接提取 {} 或 [] 包裹的内容
        brace_match = re.search(r'(\{.*\}|\[.*\])', response, re.DOTALL)
        if brace_match:
            return brace_match.group(1).strip()

        return response.strip()

    def _generate_user_options(self) -> Dict[str, Any]:
        return {
            'can_save': True,
            'can_execute': True,
            'save_options': [
                {'label': '保存为测试脚本', 'action': 'save_new'},
            ],
            'execute_options': [
                {'label': '立即执行', 'action': 'execute_now'},
                {'label': '稍后执行', 'action': 'execute_later'},
            ],
            'suggested_action': '您想要保存还是执行这个测试脚本？',
        }
