"""
Load Skill Tool
按需加载已安装 skill 的完整指令内容
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.tools.base_tool import BaseTool, ToolResult

import logging

logger = logging.getLogger(__name__)


class LoadSkillTool(BaseTool):
    """按名称加载已安装 skill 的完整 SKILL.md 内容"""

    def __init__(self, skill_loader: Any):
        super().__init__(
            name="load_skill",
            description="加载已安装技能的完整指令内容。当 system prompt 中列出了某技能但你未收到其完整指令时调用此工具。参数 name 是技能名称。",
            version="1.0.0",
            timeout=30,
        )
        self.skill_loader = skill_loader

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "name": {
                "type": "string",
                "description": "要加载的技能名称（与 system prompt 中列出的名称完全一致）",
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ["name"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        name: str = kwargs["name"].strip()

        if not name:
            return ToolResult(success=False, data={}, error="缺少参数: name")

        skills = self.skill_loader.discover()
        for s in skills:
            if s.name == name:
                logger.info(f"[LoadSkill] 加载 skill: {name}, content_len={len(s.content)}")
                return ToolResult(
                    success=True,
                    data={
                        "name": s.name,
                        "description": s.description,
                        "content": s.content,
                        "allowed_tools": s.allowed_tools,
                        "message": f"Skill '{s.name}' 已加载，请按指令执行。",
                    },
                )

        available = [s.name for s in skills]
        logger.warning(f"[LoadSkill] skill 不存在: {name}, 可用: {available}")
        return ToolResult(
            success=False,
            error=f"Skill '{name}' 未安装。可用技能: {', '.join(available) if available else '无'}",
        )
