"""
Query Project Tool
查询用户有权限的项目列表
"""
from __future__ import annotations

from typing import Any, Dict, List
import logging

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class QueryProjectTool(BaseTool):
    """查询用户有权限的项目列表"""
    
    def __init__(self) -> None:
        super().__init__(
            name="query_projects",
            description="获取当前用户有权限的项目列表，用于保存测试用例时选择目标项目。\n\n参数：\n- user_id（必需）：用户ID\n\n返回：\n- 项目选项列表，包含 id、label、description",
            version="1.0.0"
        )
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "user_id": {
                "type": "integer",
                "description": "用户ID"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["user_id"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        查询用户项目
        
        Args:
            user_id: 用户ID
            
        Returns:
            项目列表
        """
        user_id = kwargs.get("user_id")

        logger.info(f'[QueryProject] 参数: user_id={user_id}')

        if not user_id:
            logger.warning('[QueryProject] 缺少 user_id')
            return ToolResult(
                success=False,
                data={},
                error="Missing required parameter: user_id"
            )
        
        try:
            from core.models.project import Project
            
            def _get_projects() -> List[Dict[str, Any]]:
                return list(
                    Project.objects.filter(  # type: ignore[arg-type]
                        is_active=True
                    ).values('id', 'name', 'description').order_by('-created_at')
                )
            
            projects = await sync_to_async(_get_projects)()
            logger.info(f'[QueryProject] 查询到 {len(projects)} 个活跃项目')

            options = [
                {
                    "id": p['id'],
                    "label": p['name'],
                    "description": p['description'] or ""
                }
                for p in projects
            ]
            
            if not options:
                logger.info('[QueryProject] 无活跃项目')
                return ToolResult(
                    success=True,
                    data={
                        "options": [],
                        "message": "您还没有创建项目，请先创建项目后再保存测试用例。"
                    }
                )

            logger.info(f'[QueryProject] 返回 {len(options)} 个项目: {[o["label"] for o in options]}')
            return ToolResult(
                success=True,
                data={
                    "options": options,
                    "message": "请选择要保存到的项目："
                }
            )
            
        except Exception as e:
            logger.error(f'[QueryProject] 查询失败: {e}')
            return ToolResult(
                success=False,
                data={},
                error=f"查询项目失败: {str(e)}"
            )