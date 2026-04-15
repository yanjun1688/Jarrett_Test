from __future__ import annotations

from typing import Dict, List, Optional, Any, TYPE_CHECKING
import logging
from threading import Lock
from datetime import datetime

from .base import (
    CapabilityManifest,
    SkillCapability,
    ToolCapability,
    MCPServerCapability
)
from .events import (
    CapabilityEvent,
    CapabilityEventType,
    global_capability_event_bus
)

if TYPE_CHECKING:
    from skills.base import SkillSpec

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    能力注册中心
    
    统一管理所有可感知的能力：
    - Skills (技能)
    - Tools (工具)
    - MCP Servers (MCP 服务器)
    
    线程安全，支持并发访问
    """
    
    def __init__(self) -> None:
        self._skills: Dict[str, SkillCapability] = {}
        self._tools: Dict[str, ToolCapability] = {}
        self._mcp_servers: Dict[str, MCPServerCapability] = {}
        self._lock = Lock()
        self._event_bus = global_capability_event_bus
        
        logger.info("CapabilityRegistry initialized")
    
    def register_skill(self, skill: Any) -> None:
        with self._lock:
            spec: SkillSpec = skill.spec
            
            capability = SkillCapability(
                name=spec.name,
                description=spec.description,
                allowed_tools=spec.extra_config.get("allowed_tools", []),
                category=spec.category,
                tags=spec.tags,
                version=spec.version,
                author=spec.author,
                mode=spec.extra_config.get("mode", "execute")
            )
            
            self._skills[spec.name] = capability
            logger.info(f"Registered skill capability: {spec.name}")
        
        self._event_bus.publish_sync(CapabilityEvent(
            event_type=CapabilityEventType.SKILL_REGISTERED,
            capability_name=spec.name,
            capability_data=capability.to_dict()
        ))
    
    def register_skill_from_dict(self, skill_data: Dict[str, Any]) -> None:
        with self._lock:
            capability = SkillCapability(
                name=skill_data.get("name", ""),
                description=skill_data.get("description", ""),
                allowed_tools=skill_data.get("allowed_tools", []),
                category=skill_data.get("category", "general"),
                tags=skill_data.get("tags", []),
                version=skill_data.get("version", "1.0.0"),
                author=skill_data.get("author", ""),
                mode=skill_data.get("mode", "execute")
            )
            
            self._skills[capability.name] = capability
            logger.info(f"Registered skill capability from dict: {capability.name}")
        
        self._event_bus.publish_sync(CapabilityEvent(
            event_type=CapabilityEventType.SKILL_REGISTERED,
            capability_name=capability.name,
            capability_data=capability.to_dict()
        ))
    
    def unregister_skill(self, skill_name: str) -> bool:
        with self._lock:
            if skill_name in self._skills:
                del self._skills[skill_name]
                logger.info(f"Unregistered skill capability: {skill_name}")
                
                self._event_bus.publish_sync(CapabilityEvent(
                    event_type=CapabilityEventType.SKILL_UNREGISTERED,
                    capability_name=skill_name
                ))
                return True
            return False
    
    def get_skill(self, name: str) -> Optional[SkillCapability]:
        return self._skills.get(name)
    
    def get_all_skills(self) -> List[SkillCapability]:
        return list(self._skills.values())
    
    def register_tool(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        with self._lock:
            capability = ToolCapability(
                name=name,
                description=description,
                version=version,
                parameters=parameters or {}
            )
            
            self._tools[name] = capability
            logger.info(f"Registered tool capability: {name}")
        
        self._event_bus.publish_sync(CapabilityEvent(
            event_type=CapabilityEventType.TOOL_REGISTERED,
            capability_name=name,
            capability_data=capability.to_dict()
        ))
    
    def unregister_tool(self, tool_name: str) -> bool:
        with self._lock:
            if tool_name in self._tools:
                del self._tools[tool_name]
                
                self._event_bus.publish_sync(CapabilityEvent(
                    event_type=CapabilityEventType.TOOL_UNREGISTERED,
                    capability_name=tool_name
                ))
                return True
            return False
    
    def get_all_tools(self) -> List[ToolCapability]:
        return list(self._tools.values())
    
    def register_mcp_server(
        self,
        name: str,
        instructions: str = "",
        tools: Optional[List[str]] = None
    ) -> None:
        with self._lock:
            capability = MCPServerCapability(
                name=name,
                instructions=instructions,
                tools=tools or [],
                connected_at=datetime.now()
            )
            
            self._mcp_servers[name] = capability
            logger.info(f"Registered MCP server: {name}")
        
        self._event_bus.publish_sync(CapabilityEvent(
            event_type=CapabilityEventType.MCP_SERVER_CONNECTED,
            capability_name=name,
            capability_data=capability.to_dict()
        ))
    
    def unregister_mcp_server(self, server_name: str) -> bool:
        with self._lock:
            if server_name in self._mcp_servers:
                del self._mcp_servers[server_name]
                
                self._event_bus.publish_sync(CapabilityEvent(
                    event_type=CapabilityEventType.MCP_SERVER_DISCONNECTED,
                    capability_name=server_name
                ))
                return True
            return False
    
    def get_manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            skills=list(self._skills.values()),
            tools=list(self._tools.values()),
            mcp_servers=list(self._mcp_servers.values()),
            last_updated=datetime.now()
        )
    
    def clear_all(self) -> None:
        with self._lock:
            self._skills.clear()
            self._tools.clear()
            self._mcp_servers.clear()
            
            self._event_bus.publish_sync(CapabilityEvent(
                event_type=CapabilityEventType.CAPABILITIES_CLEARED,
                capability_name="all"
            ))
        
        logger.info("Cleared all capabilities")


global_capability_registry: CapabilityRegistry = CapabilityRegistry()