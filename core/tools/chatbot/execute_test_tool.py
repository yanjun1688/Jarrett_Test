"""
Execute Test Tool
执行生成的测试用例或测试脚本
"""
from typing import Dict, Any, List, Optional
import logging
import time
import asyncio
import tempfile
import os

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult
from shared.utils.async_utils import async_run_command

logger = logging.getLogger(__name__)


class ExecuteTestTool(BaseTool):
    """执行生成的测试用例或测试脚本"""
    
    def __init__(self):
        super().__init__(
            name="execute_test",
            description="执行已有的测试用例或测试脚本。\n\n"
                       "**执行方式：**\n\n"
                       "1. **单步执行（推荐）**：用户说\"执行 XXX 脚本\"时，直接调用此工具\n"
                       "   - 参数：script_name（脚本名称）、project_name（可选，项目名称）\n"
                       "   - 系统会自动查找并执行匹配的脚本\n\n"
                       "2. **两步执行**：先调用 query_test_scripts 查询，确认后再执行\n"
                       "   - 步骤1：query_test_scripts 返回脚本列表和 ID\n"
                       "   - 步骤2：用户确认后，调用 execute_test(test_script_id=ID)\n\n"
                       "3. **执行 UI 测试脚本**：使用 test_id 参数\n\n"
                       "**注意：** 当用户说\"执行这个脚本\"时，检查上下文中是否有脚本ID，如果有则直接用 test_script_id 执行。",
            version="1.3.0",
            timeout=120
        )
        self._api_orchestrator = None
        self._ui_executor = None
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "test_script_id": {
                "type": "integer",
                "description": "TestScript ID（从 query_test_scripts 返回结果获取，或从上下文中的脚本ID）"
            },
            "script_name": {
                "type": "string",
                "description": "脚本名称（精确匹配，用于单步执行，系统会自动查找并执行）"
            },
            "project_name": {
                "type": "string",
                "description": "项目名称（精确匹配，配合 script_name 使用，缩小搜索范围）"
            },
            "test_id": {
                "type": "integer",
                "description": "UITestScript ID（UI测试脚本ID）"
            },
            "test_type": {
                "type": "string",
                "enum": ["api", "ui"],
                "description": "测试类型（可选，如果不提供任何ID或名称则需要）"
            },
            "test_data": {
                "type": "object",
                "description": "测试数据（可选，用于执行生成的测试）"
            },
            "base_url": {
                "type": "string",
                "description": "API 基础 URL（可选）"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行测试
        
        Args:
            test_script_id: TestScript ID（从 query_test_scripts 获取）
            script_name: 脚本名称（单步执行，自动查找）
            project_name: 项目名称（配合 script_name 使用）
            test_id: UITestScript ID（UI测试脚本ID）
            test_type: 测试类型 (api/ui)
            test_data: 测试数据
            base_url: API 基础 URL
            
        Returns:
            执行结果
        """
        test_script_id = kwargs.get("test_script_id")
        script_name = kwargs.get("script_name")
        project_name = kwargs.get("project_name")
        test_id = kwargs.get("test_id")
        test_type = kwargs.get("test_type")
        test_data = kwargs.get("test_data")
        base_url = kwargs.get("base_url", "")
        execution_logger = kwargs.get("_execution_logger")
        
        logger.info(f"[ExecuteTest] 收到执行请求: test_script_id={test_script_id}, script_name='{script_name}', project_name='{project_name}', test_id={test_id}")
        
        if execution_logger:
            log_type = 'api_test' if (test_script_id or script_name or test_type == "api") else 'ui_test'
            await sync_to_async(execution_logger.start)(log_type, '执行测试', f'正在执行{"API" if test_script_id or script_name or test_type == "api" else "UI"}测试')
        
        # 优先级1: 直接使用 test_script_id 执行
        if test_script_id:
            logger.info(f"[ExecuteTest] 使用 test_script_id={test_script_id} 直接执行")
            result = await self._execute_test_script(test_script_id)
            if execution_logger:
                await sync_to_async(execution_logger.finish)({
                    'status': 'success' if result.success else 'error',
                    'test_script_id': test_script_id
                })
            return result
        
        # 优先级2: 使用 script_name 单步执行（自动查找）
        if script_name:
            logger.info(f"[ExecuteTest] 使用 script_name='{script_name}' 单步查找执行")
            result = await self._execute_by_script_name_direct(script_name, project_name)
            if execution_logger:
                await sync_to_async(execution_logger.finish)({
                    'status': 'success' if result.success else 'error',
                    'script_name': script_name
                })
            return result
        
        # 优先级3: 使用 test_id 执行 UI 测试
        if test_id:
            logger.info(f"[ExecuteTest] 使用 test_id={test_id} 执行 UI 测试")
            result = await self._execute_by_id(test_id)
            if execution_logger:
                await sync_to_async(execution_logger.finish)({
                    'status': 'success' if result.success else 'error',
                    'test_id': test_id
                })
            return result
        
        if not test_type:
            if execution_logger:
                await sync_to_async(execution_logger.finish)({'status': 'error', 'error': 'Missing parameter'})
            return ToolResult(
                success=False,
                data={},
                error="Missing parameter: 请提供 test_script_id、script_name 或 test_id"
            )
        
        if not test_data:
            if execution_logger:
                await sync_to_async(execution_logger.finish)({'status': 'error', 'error': 'Missing parameter: test_data'})
            return ToolResult(
                success=False,
                data={},
                error="Missing parameter: test_data"
            )
        
        if test_type not in ["api", "ui"]:
            if execution_logger:
                await sync_to_async(execution_logger.finish)({'status': 'error', 'error': f'Invalid test_type: {test_type}'})
            return ToolResult(
                success=False,
                data={},
                error=f"Invalid test_type: {test_type}. Must be 'api' or 'ui'"
            )
        
        if not self._validate_test_data(test_type, test_data):
            if execution_logger:
                await sync_to_async(execution_logger.finish)({'status': 'error', 'error': f'Invalid test_data for {test_type}'})
            return ToolResult(
                success=False,
                data={},
                error=f"Invalid test_data for {test_type} test"
            )
        
        try:
            if test_type == "api":
                result = await self._execute_api_tests(test_data, base_url)
            else:
                result = await self._execute_ui_tests(test_data)
            
            if execution_logger:
                await sync_to_async(execution_logger.finish)({
                    'status': 'success',
                    'test_type': test_type
                })
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "test_type": test_type,
                    "total_tests": result.get("execution_result", {}).get("total_tests", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            if execution_logger:
                await sync_to_async(execution_logger.finish)({'status': 'error', 'error': str(e)})
            return ToolResult(
                success=False,
                data={},
                error=f"Execution error: {str(e)}"
            )
    
    async def _execute_by_script_name_direct(self, script_name: str, project_name: Optional[str] = None) -> ToolResult:
        """通过脚本名称单步查找并执行（用户说\"执行XXX脚本\"时的自动处理）"""
        logger.info(f"[ExecuteDirect] 开始单步执行: script_name='{script_name}', project_name='{project_name}'")
        
        try:
            @sync_to_async
            def find_and_execute():
                from testmanager_app.models import TestScript
                from core.models import Project
                from testmanager_app.services.execution_engine.script_engine import TestChainExecutor
                
                filters = {'is_active': True, 'name': script_name}
                
                if project_name:
                    try:
                        project = Project.objects.get(name=project_name)
                        filters['project'] = project.id  # type: ignore[attr-defined]
                        logger.info(f"[ExecuteDirect] 限定项目: id={project.id}, name='{project.name}'")  # type: ignore[attr-defined]
                    except Project.DoesNotExist:
                        logger.warning(f"[ExecuteDirect] 项目不存在: '{project_name}'")
                        return None, {"error": f"项目不存在: '{project_name}'"}
                
                logger.info(f"[ExecuteDirect] 查询条件: {filters}")
                scripts = TestScript.objects.filter(**filters).select_related('project')
                
                if not scripts.exists():
                    logger.warning(f"[ExecuteDirect] 未找到脚本: name='{script_name}'")
                    return None, {"error": f"未找到测试脚本: '{script_name}'"}
                
                if scripts.count() > 1:
                    logger.warning(f"[ExecuteDirect] 找到多个同名脚本: count={scripts.count()}")
                    script_list = [{"id": s.id, "project": s.project.name if s.project else None} for s in scripts]  # type: ignore[attr-defined,union-attr]
                    return None, {"error": f"找到多个同名脚本，请指定项目或使用 query_test_scripts 查询", "scripts": script_list}
                
                script = scripts.first()
                if script is None:
                    logger.warning(f"[ExecuteDirect] 脚本查询结果为空")
                    return None, {"error": "脚本查询结果为空"}
                
                logger.info(f"[ExecuteDirect] 找到脚本: id={script.id}, name='{script.name}', type='{script.script_type}'")  # type: ignore[attr-defined]
                
                engine = TestChainExecutor()
                logger.info(f"[ExecuteDirect] 开始执行脚本...")
                
                if script.script_type == 'yaml':  # type: ignore[union-attr]
                    result = engine.execute_yaml_script(script.content)  # type: ignore[union-attr]
                elif script.script_type == 'api':  # type: ignore[union-attr]
                    result = engine.execute_api_script(script.content)  # type: ignore[union-attr]
                else:
                    result = engine.execute_json_script(script.content)  # type: ignore[union-attr]
                
                logger.info(f"[ExecuteDirect] 执行完成: success={result.get('success', False)}")
                return script, result
            
            script, result = await find_and_execute()
            
            if script is None:
                return ToolResult(
                    success=False,
                    data={},
                    error=result.get("error", "执行失败")
                )
            
            logs = result.get('logs', [])
            if isinstance(logs, list):
                logs_str = '\n'.join(logs)
            else:
                logs_str = logs
            
            logger.info(f"[ExecuteDirect] 返回结果: script_name='{script.name}', success={result.get('success')}, logs_length={len(logs_str)}")  # type: ignore[attr-defined]
            
            return ToolResult(
                success=bool(result.get('success', False)),
                data={
                    "script_id": script.id,  # type: ignore[attr-defined]
                    "script_name": script.name,  # type: ignore[attr-defined]
                    "script_type": script.script_type,  # type: ignore[attr-defined]
                    "success": result.get('success', False),
                    "logs": logs_str,
                    "context": result.get('context', {}),
                    "results": result.get('results', []),
                    "error": result.get('error', '')
                },
                metadata={
                    "script_name": script_name,
                    "project_name": project_name,
                    "found_script_id": script.id  # type: ignore[attr-defined]
                }
            )
            
        except Exception as e:
            logger.error(f"[ExecuteDirect] 执行失败: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"执行失败: {str(e)}"
            )
    
    async def _execute_test_script(self, test_script_id: int) -> ToolResult:
        """通过ID执行TestScript（API测试脚本）"""
        logger.info(f"[ExecuteTestScript] 开始执行测试脚本: test_script_id={test_script_id}")
        
        try:
            @sync_to_async
            def _execute_sync():
                from testmanager_app.models import TestScript
                from testmanager_app.services.execution_engine.script_engine import TestChainExecutor
                
                logger.info(f"[ExecuteTestScript] 正在查询脚本: id={test_script_id}")
                script = TestScript.objects.get(id=test_script_id, is_active=True)
                logger.info(f"[ExecuteTestScript] 找到脚本: id={script.id}, name='{script.name}', type='{script.script_type}', project_id={script.project.id if script.project else None}")  # type: ignore[attr-defined]
                
                engine = TestChainExecutor()
                logger.info(f"[ExecuteTestScript] 创建执行引擎，开始执行...")
                
                if script.script_type == 'yaml':
                    logger.info(f"[ExecuteTestScript] 执行 YAML 类型脚本")
                    result = engine.execute_yaml_script(script.content)
                elif script.script_type == 'api':
                    logger.info(f"[ExecuteTestScript] 执行 API 类型脚本")
                    result = engine.execute_api_script(script.content)
                else:
                    logger.info(f"[ExecuteTestScript] 执行 JSON 类型脚本")
                    result = engine.execute_json_script(script.content)
                
                success = result.get('success', False)
                logger.info(f"[ExecuteTestScript] 执行完成: success={success}, logs_count={len(result.get('logs', []))}")
                
                return script, result
            
            script, result = await _execute_sync()
            
            logs = result.get('logs', [])
            if isinstance(logs, list):
                logs_str = '\n'.join(logs)
            else:
                logs_str = logs
            
            logger.info(f"[ExecuteTestScript] 返回结果: script_name='{script.name}', success={result.get('success', False)}, logs_length={len(logs_str)}")
            
            if result.get('success', False):
                logger.info(f"[ExecuteTestScript] ✅ 执行成功! 脚本 '{script.name}' 所有断言通过")
            else:
                logger.warning(f"[ExecuteTestScript] ❌ 执行失败! 脚本 '{script.name}' 有断言未通过或执行出错")
                if result.get('error'):
                    logger.warning(f"[ExecuteTestScript] 错误信息: {result.get('error')}")
            
            if logs_str:
                logger.info(f"[ExecuteTestScript] 执行日志(前500字符):\n{logs_str[:500]}")
            
            results_summary = result.get('results', [])
            if results_summary:
                passed_count = sum(1 for r in results_summary if r.get('success'))
                failed_count = len(results_summary) - passed_count
                logger.info(f"[ExecuteTestScript] 步骤统计: 总计={len(results_summary)}, 通过={passed_count}, 失败={failed_count}")
                for i, step_result in enumerate(results_summary):
                    status = '✅ 通过' if step_result.get('success') else '❌ 失败'
                    logger.info(f"[ExecuteTestScript] 步骤 {i+1}: {status}, status_code={step_result.get('status_code')}")
            
            return ToolResult(
                success=result.get('success', False),
                data={
                    "script_id": test_script_id,
                    "script_name": script.name,
                    "script_type": script.script_type,
                    "success": result.get('success', False),
                    "logs": logs_str,
                    "context": result.get('context', {}),
                    "results": result.get('results', []),
                    "error": result.get('error', '')
                },
                metadata={
                    "test_script_id": test_script_id,
                    "script_name": script.name,
                    "script_type": script.script_type
                }
            )
            
        except Exception as e:
            error_msg = str(e)
            if "DoesNotExist" in error_msg:
                logger.error(f"[ExecuteTestScript] 脚本不存在: test_script_id={test_script_id}")
                return ToolResult(
                    success=False,
                    data={},
                    error=f"测试脚本不存在: ID={test_script_id}"
                )
            logger.error(f"[ExecuteTestScript] 执行失败: {error_msg}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"执行失败: {error_msg}"
            )
    
    async def _execute_by_id(self, test_id: int, script_name: Optional[str] = None) -> ToolResult:
        """通过ID执行UI测试脚本"""
        try:
            @sync_to_async
            def _execute_sync():
                from test_ui_app.models import UITestScript
                from test_ui_app.services import UITestService
                
                script = UITestScript.objects.get(id=test_id)
                service = UITestService()
                return script, service.execute_script_sync(script_id=script.id)  # type: ignore[attr-defined]
            
            script, result = await _execute_sync()
            
            if result.get("success"):
                return ToolResult(
                    success=True,
                    data={
                        "script_name": script_name or script.name,
                        "task_id": result.get("task_id"),
                        "message": "测试任务已提交执行"
                    },
                    metadata={
                        "test_id": test_id,
                        "script_name": script_name or script.name
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    data={},
                    error=result.get("error", "执行失败")
                )
                
        except Exception as e:
            error_msg = str(e)
            if "DoesNotExist" in error_msg:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"测试脚本不存在: ID={test_id}"
                )
            logger.error(f"Execute by ID failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"执行失败: {error_msg}"
            )
    
    async def _execute_by_script_name(self, script_name: str) -> ToolResult:
        """通过脚本名称执行测试"""
        import os
        
        try:
            script_basename = os.path.basename(script_name)
            script_name_lower = script_basename.lower()
            
            if script_name_lower.endswith('.robot'):
                return await self._execute_robot_script(script_name)
            elif script_name_lower.endswith('.py'):
                return await self._execute_python_script(script_name)
            else:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"不支持的脚本类型: {script_name}。支持的类型: .py, .robot"
                )
                
        except Exception as e:
            logger.error(f"Execute by script name failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"执行失败: {str(e)}"
            )
    
    async def _execute_python_script(self, script_name: str) -> ToolResult:
        """执行 Python 测试脚本"""
        import os
        
        script_basename = os.path.basename(script_name)
        
        try:
            @sync_to_async
            def find_and_execute():
                from test_ui_app.models import UITestScript
                from test_ui_app.services import UITestService
                
                try:
                    script = UITestScript.objects.get(name=script_basename)
                    service = UITestService()
                    return script, service.execute_script_sync(script_id=script.id)  # type: ignore[attr-defined]
                except UITestScript.DoesNotExist:
                    script = UITestScript.objects.get(name=script_name)
                    service = UITestService()
                    return script, service.execute_script_sync(script_id=script.id)  # type: ignore[attr-defined]
            
            script, result = await find_and_execute()
            
            if result.get("success"):
                return ToolResult(
                    success=True,
                    data={
                        "script_name": script.name,
                        "task_id": result.get("task_id"),
                        "message": f"测试脚本 {script_name} 已提交执行"
                    },
                    metadata={
                        "script_name": script.name
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    data={},
                    error=result.get("error", "执行失败")
                )
                
        except Exception as e:
            error_msg = str(e)
            if "DoesNotExist" in error_msg:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"测试脚本不存在: {script_name}"
                )
            logger.error(f"Execute Python script failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"执行失败: {error_msg}"
            )
    
    async def _execute_robot_script(self, script_name: str) -> ToolResult:
        """执行 Robot Framework 测试脚本"""
        import os
        import tempfile
        
        script_basename = os.path.basename(script_name)
        
        try:
            @sync_to_async
            def find_robot_script():
                from django.conf import settings
                import glob
                
                search_patterns = [
                    os.path.join(settings.BASE_DIR, "**", script_name),
                    os.path.join(settings.BASE_DIR, "**", script_basename),
                ]
                
                for pattern in search_patterns:
                    matches = glob.glob(pattern, recursive=True)
                    if matches:
                        return matches[0]
                return None
            
            script_path = await find_robot_script()
            
            if not script_path:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"找不到 Robot 脚本: {script_name}"
                )
            
            result = await async_run_command(
                ['robot', '--outputdir', tempfile.gettempdir(), script_path],
                timeout=self.timeout
            )
            
            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "script_name": script_name,
                        "output": result["stdout"],
                        "message": f"Robot 测试 {script_name} 执行成功"
                    },
                    metadata={
                        "script_name": script_name,
                        "script_path": script_path
                    }
                )
            else:
                error_msg = result.get("error") or result.get("stderr") or f"Robot 测试执行失败，返回码: {result['returncode']}"
                return ToolResult(
                    success=False,
                    data={},
                    error=error_msg
                )
                
        except Exception as e:
            if "超时" in str(e) or "timeout" in str(e).lower():
                return ToolResult(
                    success=False,
                    data={},
                    error="Robot 测试执行超时"
                )
            elif "未找到" in str(e) or "not found" in str(e).lower():
                return ToolResult(
                    success=False,
                    data={},
                    error="找不到 robot 命令，请确保 Robot Framework 已安装"
                )
            logger.error(f"Execute Robot script failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"执行失败: {str(e)}"
            )
    
    def _validate_test_data(self, test_type: str, test_data: Dict[str, Any]) -> bool:
        """验证测试数据"""
        if test_type == "api":
            test_cases = test_data.get("test_cases", [])
            if not test_cases:
                return False
            return True
        elif test_type == "ui":
            script = test_data.get("script", {})
            if not script.get("code"):
                return False
            return True
        return False
    
    async def _execute_api_tests(
        self,
        test_data: Dict[str, Any],
        base_url: str
    ) -> Dict[str, Any]:
        """执行 API 测试"""
        if self._api_orchestrator is None:
            from core.tools.execution.api_test_orchestrator import APITestOrchestratorTool
            self._api_orchestrator = APITestOrchestratorTool()
        
        test_cases = test_data.get("test_cases", [])
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
            "execution_result": execution_result,
            "details": results
        }
    
    async def _execute_ui_tests(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 UI 测试"""
        script = test_data.get("script", {})
        code = script.get("code", "")
        
        results = []
        start_time = time.time()
        
        try:
            result = await self._run_playwright_script(code)
            
            test_result = {
                "test_name": "UI Test",
                "status": "passed" if result.get("success") else "failed",
                "error": result.get("error") if not result.get("success") else None
            }
            
        except Exception as e:
            test_result = {
                "test_name": "UI Test",
                "status": "failed",
                "error": str(e)
            }
        
        results.append(test_result)
        
        execution_result = self._build_execution_report(results)
        execution_result["duration"] = time.time() - start_time
        
        return {
            "execution_result": execution_result,
            "details": results
        }
    
    async def _run_playwright_script(self, code: str) -> Dict[str, Any]:
        """运行 Playwright 脚本"""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                result = await async_run_command(
                    ['python', temp_file],
                    timeout=self.timeout
                )
                
                if result["success"]:
                    return {"success": True, "output": result["stdout"]}
                else:
                    return {
                        "success": False,
                        "error": result.get("error") or result.get("stderr") or "Test execution failed"
                    }
                    
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "超时" in str(e):
                return {"success": False, "error": "Test execution timed out"}
            elif "not found" in error_str or "未找到" in str(e):
                return {"success": False, "error": "Python interpreter not found"}
            return {"success": False, "error": str(e)}
    
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