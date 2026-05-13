"""
通用 Generate 工具
根据 scenario 配置调用 LLM 生成内容，不包含任何领域知识。
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

from core.tools.base_tool import BaseTool, ToolResult
from core.agents.llm import create_llm_service
from core.schemas.scenarios import SCENARIOS

logger = logging.getLogger(__name__)


class GenerateTool(BaseTool):
    """根据 scenario 类型调用 LLM 生成 JSON 格式的内容"""

    def __init__(self, llm_service: Optional[Any] = None) -> None:
        super().__init__(
            name="generate",
            description="生成测试内容（测试用例、API 测试脚本等），根据 scenario 参数决定生成类型。返回 JSON 格式的输出。",
            version="2.0.0",
        )
        self._llm_service = llm_service

    def _build_parameters_schema(self) -> Dict[str, Any]:
        scenario_descs = "\n".join(
            f'  - "{k}": {v["description"]}' for k, v in SCENARIOS.items()
        )
        return {
            "scenario": {
                "type": "string",
                "description": f"生成场景。可选值：\n{scenario_descs}",
                "enum": list(SCENARIOS.keys()),
            },
            "content": {
                "type": "string",
                "description": "输入内容（PRD 文档内容或 API 定义等）",
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ["scenario", "content"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        scenario = kwargs.get("scenario")
        content = kwargs.get("content")

        if not scenario or not content:
            return ToolResult(
                success=False,
                data={},
                error="缺少必填参数: scenario 和 content",
            )

        config = SCENARIOS.get(scenario)
        if not config:
            return ToolResult(
                success=False,
                data={},
                error=f"未知场景: {scenario}。可用场景: {', '.join(SCENARIOS.keys())}",
            )

        try:
            if not self._llm_service:
                provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
                self._llm_service = create_llm_service(provider=provider)

            prompt = config["prompt_template"].format(
                content=content,
                schema_example=config["schema_example"],
            )

            response = await self._llm_service.generate(
                prompt=prompt,
                system_message=config.get("system_message", ""),
                temperature=0.3,
                max_tokens=4000,
            )

            json_str = self._extract_json(response)

            return ToolResult(
                success=True,
                data={
                    "output": json_str,
                    "scenario": scenario,
                },
                metadata={
                    "scenario": scenario,
                    "content_length": len(response),
                },
            )

        except Exception as e:
            logger.error(f"Generate failed for scenario '{scenario}': {e}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"生成失败: {str(e)}",
            )

    def _extract_json(self, response: str) -> str:
        match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        brace_match = re.search(r"(\{.*\}|\[.*\])", response, re.DOTALL)
        if brace_match:
            return brace_match.group(1).strip()
        return response.strip()
