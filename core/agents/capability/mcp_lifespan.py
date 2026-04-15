"""
MCP 连接生命周期管理器 - 应用级管理（基座）

设计原则：
- MCP 连接在应用启动时初始化，关闭时清理
- 支持健康检查和自动重连
- 单例模式，全局复用连接
- 可扩展：支持动态注册多个 MCP Server

配置方式（推荐从 settings.py 或 .env 加载）：
    MCP_SERVERS = {
        "playwright": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest"],
            "auto_reconnect": True,
        },
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-server-filesystem", "/path/to/dir"],
        },
    }

使用方式：
    from core.agents.capability.mcp_lifespan import global_mcp_manager
    
    # 动态注册（可选）
    global_mcp_manager.register_server(MCPServerConfig(...))
    
    # 获取连接状态
    is_connected = global_mcp_manager.is_connected("playwright")
    
    # 获取工具列表（自动重连）
    tools = await global_mcp_manager.get_tools("playwright")
    
    # 调用工具（自动重连）
    result = await global_mcp_manager.call_tool("playwright", "browser_navigate", {...})
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str
    transport: str = "stdio"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    
    # 连接选项
    auto_reconnect: bool = True
    health_check_interval: int = 60  # 秒
    max_reconnect_attempts: int = 3
    reconnect_delay: int = 5  # 秒


@dataclass
class ConnectionState:
    """连接状态"""
    server_name: str
    connected: bool = False
    connection: Any = None
    last_health_check: Optional[datetime] = None
    reconnect_attempts: int = 0
    last_error: Optional[str] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)


class MCPConnectionManager:
    """
    MCP 连接管理器 - 应用级生命周期
    
    功能：
    1. 应用启动时初始化所有 MCP Server 连接
    2. 健康检查 + 自动重连
    3. 工具调用代理（失败时自动重连）
    """
    
    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerConfig] = {}
        self._states: Dict[str, ConnectionState] = {}
        self._initialized: bool = False
        self._health_check_task: Optional[asyncio.Task[None]] = None
        self._lock: asyncio.Lock = asyncio.Lock()
        
        logger.info("[MCPManager] 初始化")
    
    def register_server(self, config: MCPServerConfig) -> None:
        """注册 MCP Server 配置"""
        self._servers[config.name] = config
        self._states[config.name] = ConnectionState(server_name=config.name)
        logger.info(f"[MCPManager] 注册 Server: {config.name}")
    
    async def initialize(self) -> None:
        """初始化所有已注册的 MCP Server"""
        if self._initialized:
            logger.info("[MCPManager] 已初始化，跳过")
            return
        
        logger.info("[MCPManager] 开始初始化所有 MCP Server...")
        
        for name, config in self._servers.items():
            await self._connect_server(name, config)
        
        self._initialized = True
        
        if any(s.auto_reconnect for s in self._servers.values()):
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"[MCPManager] 初始化完成，连接数: {sum(1 for s in self._states.values() if s.connected)}")
    
    async def _connect_server(self, name: str, config: MCPServerConfig) -> bool:
        """连接单个 MCP Server"""
        state = self._states[name]
        
        try:
            import sys
            import os
            skills_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                "skills", "mcp-builder", "scripts"
            )
            if skills_path not in sys.path:
                sys.path.insert(0, skills_path)
            
            from connections import create_connection
            
            logger.info(f"[MCPManager] 连接 {name}...")
            start_time = time.time()
            
            connection = create_connection(
                transport=config.transport,
                command=config.command,
                args=config.args,
                url=config.url,
                env=config.env
            )
            
            await connection.__aenter__()
            
            state.connection = connection
            state.connected = True
            state.last_error = None
            state.reconnect_attempts = 0
            
            tools = await connection.list_tools()
            state.tools = tools
            
            elapsed = time.time() - start_time
            logger.info(f"[MCPManager] {name} 连接成功，提供 {len(tools)} 个工具，耗时 {elapsed:.2f}s")
            
            return True
            
        except Exception as e:
            state.connected = False
            state.last_error = str(e)
            logger.error(f"[MCPManager] {name} 连接失败: {e}", exc_info=True)
            return False
    
    async def _disconnect_server(self, name: str) -> None:
        """断开单个 MCP Server"""
        state = self._states.get(name)
        if state and state.connection:
            try:
                await state.connection.__aexit__(None, None, None)
                logger.info(f"[MCPManager] {name} 断开成功")
            except Exception as e:
                logger.warning(f"[MCPManager] {name} 断开失败: {e}")
            
            state.connected = False
            state.connection = None
            state.tools = []
    
    async def shutdown(self) -> None:
        """关闭所有 MCP Server 连接"""
        logger.info("[MCPManager] 开始关闭所有连接...")
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        for name in self._servers.keys():
            await self._disconnect_server(name)
        
        self._initialized = False
        logger.info("[MCPManager] 关闭完成")
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(60)
                
                for name, config in self._servers.items():
                    if not config.auto_reconnect:
                        continue
                    
                    state = self._states[name]
                    
                    if state.connected:
                        state.last_health_check = datetime.now()
                        logger.debug(f"[MCPManager] {name} 健康检查: 已连接")
                    else:
                        logger.warning(f"[MCPManager] {name} 健康检查: 断开，尝试重连...")
                        await self._reconnect(name, config)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MCPManager] 健康检查循环异常: {e}")
    
    async def _reconnect(self, name: str, config: MCPServerConfig) -> bool:
        """尝试重连"""
        state = self._states[name]
        
        if state.reconnect_attempts >= config.max_reconnect_attempts:
            logger.error(f"[MCPManager] {name} 重连次数已达上限 ({config.max_reconnect_attempts})")
            return False
        
        state.reconnect_attempts += 1
        logger.info(f"[MCPManager] {name} 重连尝试 #{state.reconnect_attempts}")
        
        await asyncio.sleep(config.reconnect_delay)
        
        success = await self._connect_server(name, config)
        
        if success:
            state.reconnect_attempts = 0
            logger.info(f"[MCPManager] {name} 重连成功")
        
        return success
    
    def is_connected(self, server_name: str) -> bool:
        """检查连接状态"""
        state = self._states.get(server_name)
        return state.connected if state else False
    
    def get_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """获取工具列表（不自动重连，仅返回缓存）"""
        state = self._states.get(server_name)
        return state.tools if state else []
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用 MCP 工具
        
        特性：连接断开时自动重连
        """
        async with self._lock:
            state = self._states.get(server_name)
            config = self._servers.get(server_name)
            
            if not state or not config:
                raise ValueError(f"未知 MCP Server: {server_name}")
            
            if not state.connected and config.auto_reconnect:
                logger.warning(f"[MCPManager] {server_name} 未连接，尝试重连...")
                await self._reconnect(server_name, config)
            
            if not state.connected:
                raise ValueError(f"MCP Server {server_name} 未连接")
            
            try:
                logger.info(f"[MCPManager] 调用工具: {server_name}/{tool_name}")
                result = await state.connection.call_tool(tool_name, arguments)
                logger.info(f"[MCPManager] 工具返回: {tool_name}")
                return result
                
            except Exception as e:
                logger.error(f"[MCPManager] 工具调用失败: {e}")
                
                if config.auto_reconnect:
                    state.connected = False
                    logger.info(f"[MCPManager] 尝试重连后重新调用...")
                    
                    if await self._reconnect(server_name, config):
                        try:
                            result = await state.connection.call_tool(tool_name, arguments)
                            logger.info(f"[MCPManager] 重连后调用成功: {tool_name}")
                            return result
                        except Exception as e2:
                            logger.error(f"[MCPManager] 重连后调用仍失败: {e2}")
                            raise
                
                raise
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有连接状态"""
        return {
            name: {
                "connected": state.connected,
                "tools_count": len(state.tools),
                "last_health_check": state.last_health_check.isoformat() if state.last_health_check else None,
                "reconnect_attempts": state.reconnect_attempts,
                "last_error": state.last_error
            }
            for name, state in self._states.items()
        }


global_mcp_manager: MCPConnectionManager = MCPConnectionManager()


__all__ = [
    "MCPServerConfig",
    "ConnectionState",
    "MCPConnectionManager",
    "global_mcp_manager",
    "load_servers_from_config",
    "load_servers_from_settings",
    "load_default_servers",
]


def configure_default_servers() -> None:
    """配置默认 MCP Servers"""
    global_mcp_manager.register_server(MCPServerConfig(
        name="playwright",
        transport="stdio",
        command="npx",
        args=["-y", "@playwright/mcp@latest"],
        auto_reconnect=True,
        health_check_interval=60,
        max_reconnect_attempts=3,
        reconnect_delay=5
    ))
    logger.info("[MCPManager] 默认 Servers 已配置")


def load_servers_from_settings() -> None:
    """从 Django settings 加载 MCP Servers"""
    try:
        from django.conf import settings
        mcp_servers = getattr(settings, 'MCP_SERVERS', {})
        if not mcp_servers:
            logger.info("[MCPManager] settings 中无 MCP_SERVERS 配置，使用默认")
            load_default_servers()
            return
        for name, config in mcp_servers.items():
            global_mcp_manager.register_server(MCPServerConfig(
                name=name,
                transport=config.get('transport', 'stdio'),
                command=config.get('command'),
                args=config.get('args', []),
                url=config.get('url'),
                env=config.get('env', {}),
                auto_reconnect=config.get('auto_reconnect', True),
                health_check_interval=config.get('health_check_interval', 60),
                max_reconnect_attempts=config.get('max_reconnect_attempts', 3),
                reconnect_delay=config.get('reconnect_delay', 5),
            ))
            logger.info(f"[MCPManager] 从 settings 加载: {name}")
    except Exception as e:
        logger.warning(f"[MCPManager] settings 加载失败: {e}")
        load_default_servers()


def load_servers_from_config(config: Dict[str, Any]) -> None:
    """从配置字典加载 MCP Servers"""
    for name, cfg in config.items():
        global_mcp_manager.register_server(MCPServerConfig(
            name=name,
            transport=cfg.get('transport', 'stdio'),
            command=cfg.get('command'),
            args=cfg.get('args', []),
            url=cfg.get('url'),
            env=cfg.get('env', {}),
            auto_reconnect=cfg.get('auto_reconnect', True),
        ))


def load_default_servers() -> None:
    """加载默认 MCP Servers"""
    configure_default_servers()