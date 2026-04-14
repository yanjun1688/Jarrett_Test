"""
Skill-Tool Adapter - 技能与工具的双向适配器

此模块实现了Skill和Tool之间的双向转换：
1. Skill作为Tool（SkillAsToolAdapter）：将技能包装成工具
2. Tool作为Skill（ToolAsSkillAdapter）：将工具包装成技能

设计原则：
- 接口适配：转换参数和返回值格式
- 错误处理：包装异常和错误
- 性能考虑：最小化包装开销
- 类型安全：保持类型一致性
"""
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import logging
import asyncio
import time

from core.agents.skill_loader import Skill, SkillSpec
from core.tools.base_tool import BaseTool, ToolResult, ToolRegistry
from shared.constants import TestType, TimeConstants
from shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SkillAsToolAdapter(BaseTool):
    """
    Skill to Tool Adaptation
    将技能包装成工具，使其可以被其他组件调用
    """
    
    def __init__(self, skill: Skill, tool_name: Optional[str] = None):
        """
        初始化技能到工具的适配器
        
        Args:
            skill: 原始技能实例
            tool_name: 工具名称（可选，使用技能名称）
        """
        self.skill = skill
        actual_name = str(tool_name) if tool_name else f"skill_unknown_{id(skill)}"
        
        # 获取description和version，防止None错误
        spec = getattr(skill, 'spec', None) if hasattr(skill, 'spec') and skill.spec is not None else None
        if spec:
            spec_desc = getattr(spec, 'description', 'Unknown skill wrapper')
            spec_version = getattr(spec, 'version', '1.0.0') 
        else:
            spec_desc = 'Unknown skill wrapper'
            spec_version = '1.0.0'
            
        actual_desc = str(spec_desc) if spec_desc else "Unknown skill wrapper"
        actual_version = str(spec_version) if spec_version else "1.0.0"
        
        super().__init__(
            name=str(actual_name),
            description=str(actual_desc),
            version=str(actual_version)
        )
        
        # 缓存原始参数结构
        if spec:
            self._original_skill_parameters = getattr(spec, 'parameters', {})
        else:
            self._original_skill_parameters = {}
        
        logger.info(f"Created skill-as-tool adapter for skill: {getattr(skill, 'name', getattr(getattr(skill, 'spec', None), 'name', 'unnamed'))} -> {self.name}")
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute tool functionality - override abstract method
        
        Args:
            **kwargs: Tool execution parameters
            
        Returns:
            Tool execution result
        """
        start_time = time.perf_counter()
        
        try:
            # Execute the underlying skill
            # If the wrapped object has an execute method, call it, else simulate
            if hasattr(self.skill, 'execute'):
                skill_result = await self.skill.execute(kwargs)
                
                # Convert skill result to ToolResult
                success = skill_result.get("success", True)
                data = skill_result.get("data", {"result": skill_result if isinstance(skill_result, dict) else kwargs})
                error_msg = skill_result.get("error", None)
                
                execution_time = skill_result.get("execution_time", 
                    time.perf_counter() - start_time)
                
            else:
                # Fallback behavior
                success = True
                data = {"result": "skill executed", "parameters": kwargs}
                error_msg = None
                execution_time = 0.0
            
            result = ToolResult(
                success=success,
                data=data,
                error=error_msg,
                execution_time=execution_time,
                metadata={"adapter_type": "skill_as_tool", "original_skill": str(self.skill)}
            )
            
            return result
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            
            logger.error(f"Skill execution in adapter failed: {e}", exc_info=True)
            
            return ToolResult(
                success=False,
                data={},
                error=f"Skill execution failed: {str(e)}",
                execution_time=execution_time
            )


    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema
        
        Returns:
            Tool schema for validation
        """
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self._build_parameters_schema()
            }
        }

    def _build_parameters_schema(self) -> Dict[str, Any]:
        """
        构建参数schema用于描述工具
        
        Returns:
            参数schema字典
        """
        if self._original_skill_parameters:
            # 将技能参数转为工具schema格式
            result = {}
            for param_name, param_def in self._original_skill_parameters.items():
                type_mapping = {
                    "string": {"type": "string"},
                    "integer": {"type": "integer"},
                    "number": {"type": "number"},
                    "boolean": {"type": "boolean"},
                    "array": {"type": "array"},
                    "object": {"type": "object"}
                }
                
                # 基础类型转换
                param_type = param_def.get("type", "string")
                result[param_name] = type_mapping.get(param_type, {"type": "string"})
                
                # 添加其他约束
                if "description" in param_def:
                    result[param_name]["description"] = param_def["description"]
                if "default" in param_def:
                    result[param_name]["default"] = param_def["default"]
                if "enum" in param_def:
                    result[param_name]["enum"] = param_def["enum"]
                if "min" in param_def:
                    result[param_name]["minimum"] = param_def["min"]
                if "max" in param_def:
                    result[param_name]["maximum"] = param_def["max"]
                if "pattern" in param_def:
                    result[param_name]["pattern"] = param_def["pattern"]
            
            return {
                "properties": result,
                "required": self._get_required_parameters()
            }
        else:
            # 使用基本schema
            return {
                "properties": {},
                "required": []
            }

    def _get_required_parameters(self) -> List[str]:
        """
        获取必需参数列表
        
        Returns:
            必需参数名称列表
        """
        required = []
        if self._original_skill_parameters:
            for param_name, param_def in self._original_skill_parameters.items():
                if param_def.get("required", False):
                    required.append(param_name)
        return required


class ToolAsSkillAdapter:
    """
    Tool to Skill Adaptation
    将工具包装成技能，使其可以被按技能方式调用
    """
    
    def __init__(self, spec: SkillSpec, tool: BaseTool):
        """
        初始化工具到技能的适配器
        
        Args:
            spec: 工具包装后的技能规范
            tool: 原始工具实例
        """
        self.spec = spec
        self.tool = tool
        self.name = spec.name
        self.version = self.spec.version
        self.execution_count = 0
        self.error_count = 0
        
        logger.info(f"Created tool-as-skill adapter for tool: {tool.name} -> skill {spec.name}")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute as a skill, call underlying tool
        
        Args:
            parameters: Skill execution parameters (converted to tool kwargs)
            
        Returns:
            Skill-format response
        """
        start_time = time.perf_counter()
        self.execution_count += 1
        
        try:
            logger.debug(f"Executing tool {self.tool.name} as skill {self.spec.name}")
            
            # Execute the underlying tool
            tool_result: ToolResult = await self.tool.execute(**parameters)
            
            # Convert ToolResult to skill response format
            execution_time = time.perf_counter() - start_time
            
            response = {
                "success": tool_result.success,
                "data": tool_result.data,
                "error": tool_result.error,
                "execution_time": max(tool_result.execution_time, execution_time),
                "execution_metadata": {
                    "adapter_type": "tool_as_skill",
                    "original_tool": self.tool.name,
                    "skill_name": self.spec.name
                }
            }
            
            # Add execution stats to metadata
            if not response.get("execution_metadata"):
                response["execution_metadata"] = {}
            response["execution_metadata"]["execution_count"] = self.execution_count
            
            logger.debug(f"Tool {self.tool.name} as skill result: success={response['success']}")
            
            return response
            
        except Exception as e:
            self.error_count += 1
            execution_time = time.perf_counter() - start_time
            
            logger.error(f"Tool execution as skill failed: {e}", exc_info=True)
            
            return {
                "success": False,
                "data": {},
                "error": f"Tool execution failed: {str(e)}",
                "execution_time": execution_time,
                "execution_metadata": {
                    "adapter_type": "tool_as_skill",
                    "original_tool": self.tool.name,
                    "skill_name": self.spec.name,
                    "error_type": type(e).__name__
                }
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取适配技能的执行统计"""
        return {
            "name": self.name,
            "version": self.version,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_rate": (self.execution_count - self.error_count) / self.execution_count if self.execution_count > 0 else 0.0,
            "adapter_type": "tool_as_skill",
            "wrapped_component": {
                "type": "tool",
                "name": self.tool.name
            }
        }
    
    def get_spec(self) -> SkillSpec:
        """获取技能规格"""
        return self.spec


class BidirectionalAdapterManager:
    """双向适配管理器 - 管理技能工具相互转换"""
    
    def __init__(self):
        self._skill_to_tool_adapters = {}
        self._tool_to_skill_adapters = {}
        
        logger.info("Bidirectional adapter manager initialized")
    
    def adapt_skill_to_tool(self, skill: Skill, tool_name: Optional[str] = None) -> BaseTool:
        """
        将技能适配为工具
        
        Args:
            skill: 原始技能
            tool_name: 可选工具名称
            
        Returns:
            适配后的工具实例
        """
        if not tool_name:
            tool_name = f"skill_{skill.spec.name if hasattr(skill, 'spec') else 'unknown'}_tool"
        
        adapter = SkillAsToolAdapter(skill, tool_name)
        
        # 缓存适配器
        self._skill_to_tool_adapters[tool_name] = adapter
        
        logger.info(f"Skill '{skill.name if hasattr(skill, 'name') else 'unnamed'}' adapted as tool '{tool_name}'")
        
        return adapter
    
    def adapt_tool_to_skill(self, spec: SkillSpec, tool: BaseTool) -> Skill:
        """
        将工具适配为技能
        
        Args:
            spec: 技能规格
            tool: 原始工具
            
        Returns:
            适配后的技能实例（包装在Adapter中）
        """
        adapter = ToolAsSkillAdapter(spec, tool)
        
        # 为了与Skill类型兼容，创建一个wrapper实例
        return adapter  # type: ignore[return-value]
    
    def register_adapted_tool(self, tool: BaseTool, registry: Optional[ToolRegistry] = None) -> bool:
        """
        注册适配后的工具到注册表
        
        Args:
            tool: 适配后的工具
            registry: 工具注册表（可选，使用全局注册表）
            
        Returns:
            是否成功注册
        """
        actual_registry = registry or ToolRegistry()
        
        try:
            actual_registry.register(tool)
            logger.info(f"Adapted tool registered: {tool.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register adapted tool: {e}")
            return False
    
    def get_adapter_statistics(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        return {
            "skill_to_tool_count": len(self._skill_to_tool_adapters),
            "tool_to_skill_count": len(self._tool_to_skill_adapters),
            "registered_adapters": {
                "skill_to_tool": list(self._skill_to_tool_adapters.keys()),
                "tool_to_skill": list(self._tool_to_skill_adapters.keys())
            }
        }


# 便捷工厂函数
def create_skill_as_tool_adapter(skill: Skill, custom_name: Optional[str] = None) -> SkillAsToolAdapter:
    """快捷创建技能到工具的适配器"""
    return SkillAsToolAdapter(skill, custom_name)


def create_tool_as_skill_adapter(spec: SkillSpec, tool: BaseTool) -> ToolAsSkillAdapter:
    """快捷创建工具到技能的适配器"""
    return ToolAsSkillAdapter(spec, tool)


def setup_bidirectional_adapter(skill: Skill, tool: BaseTool) -> tuple:
    """
    设置双向适配（技能<->工具）
    
    Args:
        skill: 原始技能
        tool: 原始工具
        
    Returns:
        (skill_as_tool, tool_as_skill) 
    """
    manager = BidirectionalAdapterManager()
    
    # 从技能创建工具
    skill_based_tool = manager.adapt_skill_to_tool(skill)
    
    # 为工具创建技能规格
    tool_spec = SkillSpec(
        name=f"tool_{tool.name}_skill",
        description=f"Converted from tool: {tool.description}",
        version=tool.version if hasattr(tool, 'version') else "1.0.0",
        execution_config={"type": "tool_wrapper"}
    )
    
    # 从工具创建技能
    tool_based_skill = manager.adapt_tool_to_skill(tool_spec, tool)
    
    return skill_based_tool, tool_based_skill, manager


if __name__ == "__main__":
    print("Skill-Tool Adapter ready")