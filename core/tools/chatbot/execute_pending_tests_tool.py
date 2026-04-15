"""
Execute Pending Tests Tool
执行会话上下文中的待执行测试
"""
from typing import Dict, Any, List, Optional
import logging
import time

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ExecutePendingTestsTool(BaseTool):
    """执行会话上下文中的待执行测试"""
    
    def __init__(self) -> None:
        super().__init__(
            name="execute_pending_tests",
            description="执行会话上下文中已生成的测试用例。当用户在生成测试后说'执行'、'运行'时调用。",
            version="1.0.0",
            timeout=120
        )
        self._api_orchestrator = None
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "pending_tests": {
                "type": "object",
                "description": "会话上下文中的待执行测试数据",
                "properties": {
                    "api": {
                        "type": "object",
                        "description": "API测试数据"
                    },
                    "ui": {
                        "type": "object",
                        "description": "UI测试数据"
                    }
                }
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["pending_tests"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        执行待执行的测试
        
        Args:
            pending_tests: 待执行的测试数据
            
        Returns:
            执行结果
        """
        pending_tests = kwargs.get("pending_tests", {})
        
        if not pending_tests:
            return ToolResult(
                success=False,
                data={},
                error="没有待执行的测试数据"
            )
        
        results = {}
        
        api_tests = pending_tests.get("api", {})
        if api_tests:
            api_result = await self._execute_api_tests(api_tests)
            results["api"] = api_result
        
        ui_tests = pending_tests.get("ui", {})
        if ui_tests:
            ui_result = await self._execute_ui_tests(ui_tests)
            results["ui"] = ui_result
        
        if not results:
            return ToolResult(
                success=False,
                data={},
                error="待执行的测试数据格式不正确"
            )
        
        overall_success = all(
            r.get("success", False) for r in results.values()
        )
        
        return ToolResult(
            success=overall_success,
            data=results,
            metadata={
                "test_types": list(results.keys()),
                "total_tests": sum(
                    r.get("execution_result", {}).get("total_tests", 0) 
                    for r in results.values() 
                    if isinstance(r, dict)
                )
            }
        )
    
    async def _execute_api_tests(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 API 测试"""
        if self._api_orchestrator is None:
            from core.tools.execution.api_test_orchestrator import APITestOrchestratorTool
            self._api_orchestrator = APITestOrchestratorTool()
        
        test_cases = test_data.get("test_cases", [])
        base_url = test_data.get("base_url", "")
        results = []
        start_time = time.time()
        
        for test_case in test_cases:
            endpoint = test_case.get("endpoint", "")
            method = test_case.get("method", "GET")
            headers = test_case.get("headers", {})
            body = test_case.get("body")
            expected_status = test_case.get("expected_status", 200)
            
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}" if base_url else endpoint
            
            try:
                result = await self._api_orchestrator.execute(
                    url=url,
                    method=method,
                    headers=headers,
                    body=body,
                    expected_status=expected_status
                )
                
                test_result = {
                    "test_name": test_case.get("name", "Unknown"),
                    "status": "passed" if result.success else "failed",
                    "response_time": result.execution_time,
                    "status_code": result.data.get("http_response", {}).get("status_code") if result.data else None,
                    "error": result.error if not result.success else None
                }
                
            except Exception as e:
                test_result = {
                    "test_name": test_case.get("name", "Unknown"),
                    "status": "failed",
                    "error": str(e)
                }
            
            results.append(test_result)
        
        execution_result = self._build_execution_report(results)
        execution_result["duration"] = time.time() - start_time
        
        return {
            "success": execution_result["status"] == "passed",
            "execution_result": execution_result,
            "details": results
        }
    
    async def _execute_ui_tests(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 UI 测试"""
        return {
            "success": False,
            "error": "UI测试执行暂不支持，请使用 execute_test 工具执行已保存的UI测试脚本"
        }
    
    def _build_execution_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建执行报告"""
        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = total - passed
        
        status = "passed" if failed == 0 else "failed"
        
        return {
            "status": status,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "duration": sum(r.get("response_time", 0) for r in results)
        }