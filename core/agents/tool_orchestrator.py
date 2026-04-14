"""
Tool Orchestrator - Manages tool execution

This module handles the orchestration of tool execution, including
tool registration, parameter validation, and result aggregation.
"""
from typing import Dict, Any, Optional, List
import logging
import asyncio

from core.tools.base_tool import BaseTool, ToolResult, ToolRegistry

logger = logging.getLogger(__name__)


class LazyLoadingRegistry:
    """
    懒加载的 ToolRegistry
    只在需要时才加载工具，避免初始化时的性能开销
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._loaded = False
        self.logger = logging.getLogger("tool.lazy_registry")
    
    def _ensure_loaded(self):
        """确保工具已加载（懒加载）"""
        if not self._loaded:
            self.logger.debug("Lazy loading tools...")
            # 这里可以添加核心工具的加载
            # 但目前保持空，按需添加工具
            self._loaded = True
    
    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        """注册工具"""
        # 如果提供了名称，则使用提供的名称，否则使用工具自身的名称
        if name:
            tool_name = name
        elif hasattr(tool, 'name') and getattr(tool, 'name', None):
            tool_name = getattr(tool, 'name')
        else:
            # 对于没有明确名称的对象，如mock，我们可以为其设置特定名称，或使用默认方式
            # 这里我们处理一种常见情况：将mock的name设置为通用名称
            tool_name = str(tool)
        
        # 使用工具的名称作为键注册
        self._tools[tool_name] = tool
        self.logger.info(f"Tool '{tool_name}' registered")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        self._ensure_loaded()
        return self._tools.get(name)
    
    def list(self) -> List[Dict[str, Any]]:
        """列出所有已注册工具"""
        self._ensure_loaded()
        return [
            {
                'name': name,
                'description': getattr(tool, 'description', 'No description'),
                'version': getattr(tool, 'version', '1.0.0'),
                'schema': tool.get_schema() if hasattr(tool, 'get_schema') else {}
            }
            for name, tool in self._tools.items()
        ]
    
    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具"""
        self._ensure_loaded()
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data={},
                error=f"Tool '{tool_name}' not found"
            )
        return await tool.execute_with_validation(**kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        self._ensure_loaded()
        return {
            'total_tools': len(self._tools),
            'loaded': self._loaded
        }


class ToolOrchestrator:
    """
    Orchestrates tool execution for the Chatbot agent
    
    This class:
    - Manages tool registration
    - Validates tool parameters
    - Executes tools concurrently or sequentially
    - Aggregates tool results
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize Tool Orchestrator
        优化：只注册必要的核心工具，避免自动扫描大量技能
        """
        if registry is None:
            # 使用懒加载Registry，避免初始化时进行扫描
            self.registry = LazyLoadingRegistry()  # 现在我们稍后创建这个类
        else:
            self.registry = registry
        self.logger = logging.getLogger(__name__)
    
    async def execute(
        self,
        tool_name: str,
        execution_logger=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool by name
        
        Args:
            tool_name: Name of the tool to execute
            execution_logger: Optional ChatBotExecutionLogger instance
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        self.logger.info(f"Executing tool: {tool_name}")
        
        # Pass execution_logger to tools if provided
        if execution_logger:
            kwargs['_execution_logger'] = execution_logger
        
        # Execute with validation
        result = await self.registry.execute(tool_name, **kwargs)
        
        # Convert to standard format
        return self._convert_to_standard_format(result)
    
    def _convert_to_standard_format(self, tool_result: ToolResult) -> Dict[str, Any]:
        """
        Convert ToolResult to standard format
        
        Args:
            tool_result: ToolResult instance
            
        Returns:
            Standard result dictionary
        """
        result_dict = tool_result.to_dict()
        
        return {
            "success": result_dict.get("success", False),
            "data": result_dict.get("data", {}),
            "error": result_dict.get("error"),
            "execution_time": result_dict.get("execution_time", 0.0),
            "metadata": result_dict.get("metadata", {})
        }
    
    async def execute_multiple(
        self,
        tools: List[Dict[str, Any]],
        execution_mode: str = "sequential"
    ) -> Dict[str, Any]:
        """
        Execute multiple tools
        
        Args:
            tools: List of tool execution specifications
            execution_mode: Execution mode ("sequential" or "concurrent")
            
        Returns:
            aggregated results
        """
        results = []
        
        if execution_mode == "concurrent":
            # Execute concurrently
            tasks = [
                self.execute(tool["name"], **tool.get("parameters", {}))
                for tool in tools
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute sequentially
            for tool in tools:
                try:
                    result = await self.execute(
                        tool["name"],
                        **tool.get("parameters", {})
                    )
                    results.append(result)
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": str(e)
                    })
        
        # Aggregate results
        return self._aggregate_results(results)
    
    def _aggregate_results(self, results: List[Any]) -> Dict[str, Any]:
        """
        Aggregate multiple tool results
        
        Args:
            results: List of tool results
            
        Returns:
            Aggregated result dictionary
        """
        successful = 0
        failed = 0
        total_time = 0.0
        
        output = {
            "results": [],
            "summary": {}
        }
        
        for result in results:
            if isinstance(result, Exception):
                output["results"].append({
                    "success": False,
                    "error": str(result)
                })
                failed += 1
            elif isinstance(result, dict):
                output["results"].append(result)
                
                if result.get("success"):
                    successful += 1
                else:
                    failed += 1
                
                total_time += result.get("execution_time", 0.0)
        
        output["summary"] = {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "total_execution_time": total_time
        }
        
        output["success"] = failed == 0
        
        return output
    
    def register_tool(self, tool: BaseTool, name: Optional[str] = None) -> bool:
        """
        Register a tool
         
        Args:
            tool: Tool instance to register
            name: Name to register the tool under (optional, uses tool's name if not provided)
             
        Returns:
            True if successful, False otherwise
        """
        try:
            self.registry.register(tool, name)
            self.logger.info(f"Tool registered: {name or getattr(tool, 'name', 'unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register tool: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            tool_name: Name of the tool to unregister
            
        Returns:
            True if successful, False otherwise
        """
        if tool_name in self.registry._tools:
            del self.registry._tools[tool_name]
            self.logger.info(f"Tool unregistered: {tool_name}")
            return True
        else:
            self.logger.warning(f"Tool not found for unregistration: {tool_name}")
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools
        
        Returns:
            List of tool information dictionaries
        """
        return self.registry.list()
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information dictionary or None
        """
        tool = self.registry.get(tool_name)
        if tool:
            return {
                "name": tool.name,
                "description": tool.description,
                "version": tool.version,
                "schema": tool.get_schema()
            }
        return None
    
    async def execute_with_schema_validation(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tool with schema validation
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            
        Returns:
            Tool execution result
        """
        # Get tool schema
        tool = self.registry.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        schema = tool.get_schema()
        
        # Extract parameters schema from OpenAI function format
        parameters_schema = schema.get('function', {}).get('parameters', schema)
        
        # Validate against schema using jsonschema
        validation_errors = self._validate_parameters(parameters, parameters_schema)
        
        if validation_errors:
            return {
                "success": False,
                "error": "Parameter validation failed",
                "validation_errors": validation_errors
            }
        
        # Execute with validated parameters
        return await self.execute(tool_name, **parameters)
    
    def _validate_parameters(
        self,
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[str]:
        """
        Validate parameters against schema using jsonschema
        
        Args:
            parameters: Parameters to validate
            schema: JSON schema (parameters schema from OpenAI function format)
            
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            import jsonschema
            jsonschema.validate(parameters, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Validation error: {e.message}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
        
        return errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics
        
        Returns:
            Statistics dictionary
        """
        return self.registry.get_statistics()
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Alias for execute() - Execute a tool by name
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        return await self.execute(tool_name, **kwargs)
    
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        Alias for get_available_tools() - Get list of available tools
        
        Returns:
            List of tool information dictionaries
        """
        return self.get_available_tools()


if __name__ == "__main__":
    # Simple test
    orchestrator = ToolOrchestrator()
    
    print("ToolOrchestrator created successfully")
    print(f"Available tools: {orchestrator.get_available_tools()}")
