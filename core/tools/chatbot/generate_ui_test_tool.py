"""
GenerateUI Test Tool
根据用户描述生成 UI 自动化测试脚本（Playwright）
直接调用 LLM 生成代码，不再走 TestGenerationService
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.tools.base_tool import BaseTool, ToolResult
from core.agents.llm import create_llm_service

logger = logging.getLogger(__name__)


class GenerateUITestTool(BaseTool):
    """根据用户描述生成 UI 自动化测试脚本（Playwright）"""

    def __init__(self, llm_service: Optional[Any] = None) -> None:
        super().__init__(
            name='generate_ui_test',
            description='生成 UI/Web 自动化测试脚本。当用户需要测试网页功能、表单、按钮点击等UI交互时调用。',
            version='2.0.0'
        )
        self._llm_service = llm_service

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            'project_id': {
                'type': 'integer',
                'description': '[DEPRECATED] 项目 ID（已弃用，后续版本移除）。保存脚本时需要通过 save_test_script 传入。'
            },
            'description': {
                'type': 'string',
                'description': '测试场景描述，如\'测试登录功能\''
            },
            'url': {
                'type': 'string',
                'description': '要测试的网页 URL（可选）'
            },
            'actions': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': '要执行的操作列表（可选），如 [\'点击登录按钮\', \'输入用户名\']'
            }
        }

    def _get_required_parameters(self) -> List[str]:
        return ['description']

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        生成 UI 测试脚本，直接调用 LLM

        Args:
            description: 测试场景描述
            url: 要测试的网页 URL
            actions: 要执行的操作列表

        Returns:
            包含测试脚本的 ToolResult
        """
        project_id = kwargs.get('project_id')
        description = kwargs.get('description')
        url = kwargs.get('url')
        actions = kwargs.get('actions', [])

        if not description:
            return ToolResult(
                success=False,
                data={},
                error='缺少必填参数: description'
            )

        try:
            # 初始化 LLM 服务（如果未提供）
            if not self._llm_service:
                self._llm_service = create_llm_service(provider='zhipu')

            # 构建 prompt
            url_context = f'目标URL: {url}\n' if url else ''
            actions_context = ''
            if actions:
                actions_context = '操作步骤:\n' + '\n'.join([f'{i+1}. {action}' for i, action in enumerate(actions)])

            prompt = f"""请根据以下描述生成 Playwright UI 自动化测试代码。

测试场景: {description}
{url_context}{actions_context}

要求：
1. 使用 Python + Playwright + pytest
2. 包含必要的 import 语句
3. 使用异步方式 (async/await)
4. 包含适当的注释说明每个步骤
5. 使用合适的定位器 (role, text, test-id 优先于 CSS selector)
6. 包含错误处理
7. 代码应完整可执行

请自我检查：
- 代码是否完整可运行？
- 是否包含所有必要的 import？
- 是否有适当的注释？
- 是否符合 Playwright 最佳实践？

直接输出 Python 代码，使用 markdown 代码块格式。"""

            # 调用 LLM 生成代码
            response = await self._llm_service.generate(
                prompt=prompt,
                system_message='你是 Playwright 测试专家，擅长生成高质量的 UI 自动化测试代码。',
                temperature=0.3,
                max_tokens=2000
            )

            # 提取代码
            code = self._extract_code(response)

            # 简单的质量评分
            quality_score = self._calculate_quality_score(code)

            script_data = {
                'language': 'python',
                'framework': 'playwright',
                'code': code
            }

            user_options = self._generate_user_options()

            return ToolResult(
                success=True,
                data={
                    'script': script_data,
                    'user_options': user_options,
                    'quality_score': quality_score
                },
                metadata={
                    'url': url,
                    'description': description,
                    'actions': actions
                }
            )

        except Exception as e:
            logger.error(f'Failed to generate UI test: {e}')
            return ToolResult(
                success=False,
                data={},
                error=f'Generation error: {str(e)}'
            )

    def _extract_code(self, response: str) -> str:
        """从 LLM 响应中提取代码"""
        import re

        # 尝试提取 markdown 代码块
        code_block_pattern = r'```python\s*(.*?)```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        if matches:
            return str(matches[0].strip())

        # 如果没有找到代码块，尝试提取整个响应中的代码行
        lines = response.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            if line.strip().startswith(('import ', 'from ', 'async def', 'def ', 'class ', '@pytest', 'async with', 'await ')):
                in_code = True
            if in_code:
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines).strip()

        # 如果都没找到，返回原始响应
        return response.strip()

    def _calculate_quality_score(self, code: str) -> int:
        """计算代码质量评分（启发式）"""
        score = 0

        # 检查代码长度
        if len(code) >= 200:
            score += 20

        # 检查是否有 import
        if 'import' in code:
            score += 20

        # 检查是否有 async/await
        if 'async def' in code or 'await ' in code:
            score += 20

        # 检查是否有注释
        if '#' in code or '"""' in code:
            score += 20

        # 检查是否有断言或验证
        if 'expect(' in code or 'assert' in code:
            score += 20

        return min(score, 100)

    def _generate_user_options(self, script: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成用户选项"""
        return {
            'can_save': True,
            'can_execute': True,
            'save_options': [
                {'label': '保存为测试脚本', 'action': 'save_script'},
                {'label': '保存到测试套件', 'action': 'save_to_suite'}
            ],
            'execute_options': [
                {'label': '立即执行', 'action': 'execute_now'},
                {'label': '稍后执行', 'action': 'execute_later'}
            ],
            'suggested_action': '是否保存或执行这个测试脚本？'
        }
