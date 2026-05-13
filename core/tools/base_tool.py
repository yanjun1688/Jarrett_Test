"""
Base tool class for all tools
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import time
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
    async def execute(self, **kwargs: Any) -> ToolResult:
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

    def get_param(self, kwargs: Dict[str, Any], name: str, default: Any = None) -> Any:
        """从 kwargs 提取参数，带默认值"""
        return kwargs.get(name, default)

    def validate_required(self, kwargs: Dict[str, Any], *names: str) -> Optional[ToolResult]:
        """校验必填参数。返回 None 表示通过，返回 ToolResult 表示失败（直接 return）"""
        missing = [n for n in names if not kwargs.get(n)]
        if missing:
            return ToolResult(
                success=False,
                data={},
                error=f"缺少必填参数: {', '.join(missing)}",
            )
        return None

    async def run_query(self, query_fn: Any, error_msg: str) -> Any:
        """包装同步 DB 查询为异步，统一错误处理和日志"""
        from asgiref.sync import sync_to_async
        try:
            result = await sync_to_async(query_fn)()
            return result
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            raise

    async def execute_with_validation(
        self,
        **kwargs: Any
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
    """唯一工具注册表"""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger("tool.registry")

    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        register_name = name or tool.name
        if register_name in self._tools:
            self.logger.warning(f"Tool '{register_name}' already registered, overwriting")
        self._tools[register_name] = tool
        self.logger.info(f"Tool '{register_name}' registered")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_definitions(self) -> List[Dict[str, Any]]:
        """返回 OpenAI function calling 格式的工具定义（不含过滤）"""
        return [t.get_schema() for t in self._tools.values()]

    def count(self) -> int:
        return len(self._tools)

    def get_statistics(self) -> Dict[str, Any]:
        tools_stats: Dict[str, Any] = {}
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
            'tools': tools_stats,
        }