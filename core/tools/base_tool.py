"""
Base tool class for all tools
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import time
from enum import Enum


class ToolStatus(Enum):
    """Tool execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'success': self.success,
            'data': self.data,
            'execution_time': self.execution_time
        }
        
        if self.error:
            result['error'] = self.error
        
        if self.metadata:
            result['metadata'] = self.metadata
        
        return result


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        timeout: int = 30
    ):
        """
        Initialize base tool
        
        Args:
            name: Tool name
            description: Tool description
            version: Tool version
            timeout: Execution timeout in seconds
        """
        self.name = name
        self.description = description
        self.version = version
        self.timeout = timeout
        self.logger = logging.getLogger(f"tool.{name}")
        
        # Execution tracking
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.error_count = 0
        
        self.logger.info(f"Tool '{name}' v{version} initialized")
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema for parameter validation in OpenAI function calling format
        
        Returns:
            OpenAI function calling schema
        """
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': self._build_parameters_schema(),
                    'required': self._get_required_parameters()
                }
            }
        }
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        """
        Build parameters schema
        
        Returns:
            Parameters schema dictionary
        """
        return {}
    
    def _get_required_parameters(self) -> List[str]:
        """
        Get required parameters
        
        Returns:
            List of required parameter names
        """
        return []
    
    async def execute_with_validation(
        self,
        **kwargs
    ) -> ToolResult:
        """
        Execute tool with parameter validation
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        start_time = time.time()
        
        try:
            # Validate parameters
            validation_result = self._validate_parameters(kwargs)
            if not validation_result['valid']:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Parameter validation failed: {validation_result['errors']}",
                    execution_time=time.time() - start_time
                )
            
            # Execute tool
            self.execution_count += 1
            result = await self.execute(**kwargs)
            result.execution_time = time.time() - start_time
            
            # Update statistics
            self.total_execution_time += result.execution_time
            
            if not result.success:
                self.error_count += 1
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.error_count += 1
            self.logger.error(f"Tool execution failed: {str(e)}")
            
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_parameters(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate tool parameters
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Validation result
        """
        # Basic validation - check required parameters
        required_params = self._get_required_parameters()
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params:
            return {
                'valid': False,
                'errors': f"Missing required parameters: {', '.join(missing_params)}"
            }
        
        # Type validation would go here (using JSON schema)
        # For now, just return success
        return {
            'valid': True,
            'errors': None
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get tool execution statistics
        
        Returns:
            Statistics dictionary
        """
        avg_time = 0.0
        if self.execution_count > 0:
            avg_time = self.total_execution_time / self.execution_count
        
        success_rate = 0.0
        if self.execution_count > 0:
            success_rate = (self.execution_count - self.error_count) / self.execution_count
        
        return {
            'name': self.name,
            'version': self.version,
            'execution_count': self.execution_count,
            'error_count': self.error_count,
            'total_execution_time': self.total_execution_time,
            'average_execution_time': avg_time,
            'success_rate': success_rate
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"Tool(name='{self.name}', description='{self.description}')"


class ToolRegistry:
    """Registry for managing tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger("tool.registry")
    
    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        """
        Register a tool
        
        Args:
            tool: Tool to register
            name: Optional name to register under (uses tool.name if not provided)
        """
        register_name = name or tool.name
        if register_name in self._tools:
            self.logger.warning(f"Tool '{register_name}' already registered, overwriting")
        
        self._tools[register_name] = tool
        self.logger.info(f"Tool '{register_name}' registered")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list(self) -> List[Dict[str, Any]]:
        """
        List all registered tools
        
        Returns:
            List of tool information dictionaries
        """
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'version': tool.version,
                'schema': tool.get_schema()
            }
            for tool in self._tools.values()
        ]
    
    async def execute(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool by name
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data={},
                error=f"Tool '{tool_name}' not found"
            )
        
        return await tool.execute_with_validation(**kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics
        
        Returns:
            Statistics dictionary
        """
        tools_stats = {}
        total_executions = 0
        total_errors = 0
        
        for name, tool in self._tools.items():
            stats = tool.get_statistics()
            tools_stats[name] = stats
            total_executions += stats['execution_count']
            total_errors += stats['error_count']
        
        return {
            'total_tools': len(self._tools),
            'total_executions': total_executions,
            'total_errors': total_errors,
            'tools': tools_stats
        }


# Global tool registry instance
global_tool_registry = ToolRegistry()


class LazyLoadingRegistry:
    """
    懒加载注册表 - 避免自动扫描技能目录
    这个设计只在需要的时候才加载特定工具
    """
    
    def __init__(self, max_tools: int = 10):  # 限制最大工具数量来避免加载过多技能
        self._tools: Dict[str, BaseTool] = {}
        self._loaded = False
        self._initial_tools = []  # 存储初始时加载的必需工具
        self.logger = logging.getLogger("lazy_tool.registry")
        
    def register(self, tool: BaseTool) -> None:
        """
        注册一个工具
        
        Args:
            tool: 要注册的工具
        """
        if tool.name not in self._tools:
            self._tools[tool.name] = tool
        else:
            self.logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self.logger.info(f"Tool '{tool.name}' registered")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        根据名称获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例或None
        """
        # 不进行自动加载，只返回已经注册的工具
        return self._tools.get(name)
    
    def list(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的工具
        
        Returns:
            工具信息字典列表
        """
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'version': tool.version,
                'schema': tool.get_schema()
            }
            for tool in self._tools.values()
        ]
    
    async def execute(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """
        执行名为的工具
        
        Args:
            tool_name: 要执行的工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        tool = self.get(tool_name)
        if not tool:
            self.logger.error(f"Tool '{tool_name}' not found in registry")
            return ToolResult(
                success=False,
                data={},
                error=f"Tool '{tool_name}' not found"
            )
        
        return await tool.execute_with_validation(**kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            统计信息字典
        """
        tools_stats = {}
        total_executions = 0
        total_errors = 0
        
        for name, tool in self._tools.items():
            stats = tool.get_statistics()
            tools_stats[name] = stats
            total_executions += stats['execution_count']
            total_errors += stats['error_count']
        
        return {
            'total_tools': len(self._tools),
            'total_executions': total_executions,
            'total_errors': total_errors,
            'tools': tools_stats
        }