from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端 - 管理 MCP server 连接"""
    
    def __init__(self, capability_registry=None):
        self.registry = capability_registry
        self._connections: Dict[str, Any] = {}
    
    async def connect(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """连接 MCP server"""
        try:
            # MCP 连接器在项目根目录的 skills/mcp-builder/scripts 下
            import sys
            import os
            skills_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "skills", "mcp-builder", "scripts")
            sys.path.insert(0, skills_path)
            
            from connections import create_connection
            
            logger.info(f"[MCPClient] 连接服务器: {server_name}")
            
            connection = create_connection(
                transport=server_config.get("transport", "stdio"),
                command=server_config.get("command"),
                args=server_config.get("args", []),
                url=server_config.get("url"),
                env=server_config.get("env")
            )
            
            await connection.__aenter__()
            self._connections[server_name] = connection
            
            logger.info(f"[MCPClient] 连接成功: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"[MCPClient] 连接失败: {e}", exc_info=True)
            return False
    
    async def disconnect(self, server_name: str) -> bool:
        """断开 MCP server"""
        if server_name in self._connections:
            await self._connections[server_name].__aexit__(None, None, None)
            del self._connections[server_name]
            logger.info(f"[MCPClient] 断开成功: {server_name}")
            return True
        return False
    
    async def get_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """获取 server 提供的工具列表"""
        if server_name not in self._connections:
            logger.error(f"[MCPClient] 服务器未连接: {server_name}")
            return []
        
        tools = await self._connections[server_name].list_tools()
        logger.info(f"[MCPClient] {server_name} 提供 {len(tools)} 个工具")
        return tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用 MCP 工具"""
        if server_name not in self._connections:
            raise ValueError(f"服务器未连接: {server_name}")
        
        logger.info(f"[MCPClient] 调用工具: {server_name}/{tool_name}, 参数: {arguments}")
        result = await self._connections[server_name].call_tool(tool_name, arguments)
        logger.info(f"[MCPClient] 工具返回: {result}")
        return result