from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class CapabilityType(Enum):
    SKILL = "skill"
    TOOL = "tool"
    MCP_SERVER = "mcp_server"
    COMMAND = "command"


@dataclass
class SkillCapability:
    name: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    mode: str = "execute"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": CapabilityType.SKILL.value,
            "name": self.name,
            "description": self.description,
            "allowed_tools": self.allowed_tools,
            "category": self.category,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "mode": self.mode
        }


@dataclass
class ToolCapability:
    name: str
    description: str
    version: str = "1.0.0"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": CapabilityType.TOOL.value,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": self.parameters
        }


@dataclass
class MCPServerCapability:
    name: str
    instructions: str = ""
    tools: List[str] = field(default_factory=list)
    status: str = "connected"
    connected_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": CapabilityType.MCP_SERVER.value,
            "name": self.name,
            "instructions": self.instructions,
            "tools": self.tools,
            "status": self.status,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None
        }


@dataclass
class CapabilityManifest:
    skills: List[SkillCapability] = field(default_factory=list)
    tools: List[ToolCapability] = field(default_factory=list)
    mcp_servers: List[MCPServerCapability] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills": [s.to_dict() for s in self.skills],
            "tools": [t.to_dict() for t in self.tools],
            "mcp_servers": [m.to_dict() for m in self.mcp_servers],
            "total_count": len(self.skills) + len(self.tools) + len(self.mcp_servers),
            "last_updated": self.last_updated.isoformat()
        }