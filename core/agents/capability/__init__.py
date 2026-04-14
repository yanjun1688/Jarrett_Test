"""
Capability Aware System - 能力感知系统

提供模型感知扩展机制，让 AI Agent 知道：
- 有哪些可用技能
- 技能可用什么工具
- 有哪些可用工具
- 有哪些 MCP 服务

核心模块：
- CapabilityRegistry: 能力注册中心
- CapabilityInjector: 能力注入器（数据提供者）
- CapabilityEventBus: 事件总线
- TokenCalculator: Token 精确计算（可选，来自 TokenEconomics）

使用示例：
    from core.agents.capability import (
        global_capability_registry,
        global_capability_injector,
        global_capability_event_bus
    )
    
    # 注册技能
    global_capability_registry.register_skill(skill)
    
    # 注册工具
    global_capability_registry.register_tool(
        name="generate_api_test",
        description="生成 API 测试"
    )
    
    # 获取技能数据
    skills_data = global_capability_injector.get_skills_data()
    
    # 获取工具数据
    tools_data = global_capability_injector.get_tools_data()
    
    # 订阅事件
    from core.agents.capability.events import CapabilityEventType
    
    async def on_skill_registered(event):
        print(f"Skill registered: {event.capability_name}")
    
    global_capability_event_bus.subscribe(
        CapabilityEventType.SKILL_REGISTERED,
        on_skill_registered
    )
"""

from .base import (
    CapabilityType,
    SkillCapability,
    ToolCapability,
    MCPServerCapability,
    CapabilityManifest
)

from .events import (
    CapabilityEventType,
    CapabilityEvent,
    CapabilityEventBus,
    global_capability_event_bus
)

from .registry import (
    CapabilityRegistry,
    global_capability_registry
)

from .injector import (
    CapabilityInjector,
    global_capability_injector
)

from .cache import (
    CapabilityCache
)

from .mcp_client import (
    MCPClient
)

__all__ = [
    "CapabilityType",
    "SkillCapability",
    "ToolCapability",
    "MCPServerCapability",
    "CapabilityManifest",
    "CapabilityEventType",
    "CapabilityEvent",
    "CapabilityEventBus",
    "global_capability_event_bus",
    "CapabilityRegistry",
    "global_capability_registry",
    "CapabilityInjector",
    "global_capability_injector",
    "CapabilityCache",
    "MCPClient"
]