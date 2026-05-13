"""
Query Project Tool
查询用户有权限的项目列表
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.tools.base_tool import BaseTool, ToolResult


class QueryProjectTool(BaseTool):
    """查询用户有权限的项目列表"""

    def __init__(self) -> None:
        super().__init__(
            name="query_projects",
            description="获取当前用户有权限的项目列表，用于保存测试用例时选择目标项目。\n\n参数：\n- user_id（必需）：用户ID\n\n返回：\n- 项目选项列表，包含 id、label、description",
            version="1.0.0",
        )

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "user_id": {
                "type": "integer",
                "description": "用户ID",
            }
        }

    def _get_required_parameters(self) -> List[str]:
        return ["user_id"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        err = self.validate_required(kwargs, "user_id")
        if err:
            return err

        user_id = self.get_param(kwargs, "user_id")
        self.logger.info(f"[QueryProject] user_id={user_id}")

        from core.models.project import Project

        projects = await self.run_query(
            lambda: list(
                Project.objects.filter(is_active=True)
                .values('id', 'name', 'description')
                .order_by('-created_at')
            ),
            "查询项目失败",
        )

        if not projects:
            return ToolResult(
                success=True,
                data={
                    "options": [],
                    "message": "您还没有创建项目，请先创建项目后再保存测试用例。",
                },
            )

        options = [
            {"id": p['id'], "label": p['name'], "description": p['description'] or ""}
            for p in projects
        ]
        return ToolResult(
            success=True,
            data={"options": options, "message": "请选择要保存到的项目："},
        )
