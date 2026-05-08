"""
MCP Tool Adapter — 将 global_mcp_manager 的工具包装为 BaseTool

使 MCP 工具可以与内置工具统一注册到 ToolRegistry，由 ReActEngine 通过
registry.get(name) → execute_with_validation() 调用。
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.tools.base_tool import BaseTool, ToolResult

import logging

logger = logging.getLogger(__name__)


class MCPToolAdapter(BaseTool):
    """将 global_mcp_manager 的工具包装为 BaseTool"""

    def __init__(self, server_name: str, tool_def: Dict[str, Any]):
        name = f"mcp__{server_name}__{tool_def['name']}"
        super().__init__(name=name, description=tool_def.get("description", ""))
        self._server = server_name
        self._tool_name = tool_def["name"]
        self._input_schema = tool_def.get("input_schema", {})

    def _build_parameters_schema(self) -> Dict[str, Any]:
        props: Any = self._input_schema.get("properties", {})
        return props if isinstance(props, dict) else {}

    def _get_required_parameters(self) -> List[str]:
        req: Any = self._input_schema.get("required", [])
        return req if isinstance(req, list) else []

    async def execute(self, **kwargs: Any) -> ToolResult:
        from core.agents.capability.mcp_lifespan import global_mcp_manager
        try:
            result = await global_mcp_manager.call_tool(
                self._server, self._tool_name, kwargs
            )
            return ToolResult(success=True, data={"result": result})
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
