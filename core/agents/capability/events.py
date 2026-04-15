from __future__ import annotations

import asyncio
import logging

from typing import Callable, Dict, List, Any, Awaitable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CapabilityEventType(Enum):
    SKILL_REGISTERED = "skill_registered"
    SKILL_UNREGISTERED = "skill_unregistered"
    TOOL_REGISTERED = "tool_registered"
    TOOL_UNREGISTERED = "tool_unregistered"
    MCP_SERVER_CONNECTED = "mcp_server_connected"
    MCP_SERVER_DISCONNECTED = "mcp_server_disconnected"
    CAPABILITIES_CLEARED = "capabilities_cleared"


@dataclass
class CapabilityEvent:
    event_type: CapabilityEventType
    capability_name: str
    capability_data: Any = None
    timestamp: Optional[str] = None
    
    def __post_init__(self) -> None:
        if self.timestamp is None:
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()


EventCallback = Callable[[CapabilityEvent], Awaitable[None]]


class CapabilityEventBus:
    """
    能力事件总线（异步版本）
    
    实现观察者模式，处理能力变化事件
    支持同步和异步回调，适配异步上下文
    """
    
    def __init__(self) -> None:
        self._subscribers: Dict[CapabilityEventType, List[EventCallback]] = {}
    
    def subscribe(
        self, 
        event_type: CapabilityEventType, 
        callback: EventCallback
    ) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.value}")
    
    def unsubscribe(
        self, 
        event_type: CapabilityEventType, 
        callback: EventCallback
    ) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
    
    async def publish(self, event: CapabilityEvent) -> None:
        logger.info(f"Publishing event: {event.event_type.value} - {event.capability_name}")
        
        if event.event_type not in self._subscribers:
            return
        
        for callback in self._subscribers[event.event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    def publish_sync(self, event: CapabilityEvent) -> None:
        logger.info(f"Publishing sync event: {event.event_type.value} - {event.capability_name}")
        
        if event.event_type not in self._subscribers:
            return
        
        for callback in self._subscribers[event.event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")


global_capability_event_bus: CapabilityEventBus = CapabilityEventBus()