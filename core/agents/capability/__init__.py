"""
Capability Module

MCP 连接管理（保留），其他能力系统已移除。
"""
from .mcp_lifespan import (
    global_mcp_manager,
    load_servers_from_settings,
)

__all__ = [
    "global_mcp_manager",
    "load_servers_from_settings",
]
