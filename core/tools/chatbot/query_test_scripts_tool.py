"""
Query Test Scripts Tool
查询测试脚本（API测试脚本和UI测试脚本）
"""
from typing import Dict, Any, List, Optional
import logging

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class QueryTestScriptsTool(BaseTool):
    """查询测试脚本列表（支持API和UI两种类型）"""
    
    def __init__(self) -> None:
        super().__init__(
            name="query_test_scripts",
            description="查询测试脚本列表。根据脚本名称查找 API 测试脚本或 UI 测试脚本。\n\n"
                       "注意：\n"
                       "- 脚本名称必须精确匹配（不是模糊搜索）\n"
                       "- 支持两种脚本类型：api（API测试脚本）和 ui（UI测试脚本）\n\n"
                       "参数：\n"
                       "- script_name：脚本名称，精确匹配\n"
                       "- project_name（可选）：项目名称，精确匹配\n"
                       "- test_type（可选）：脚本类型，'api' 或 'ui'，默认查询所有\n\n"
                       "返回：\n"
                       "- 匹配的测试脚本列表（包含 ID、名称、类型、项目等）\n"
                       "- 脚本类型标识 test_type: api/ui\n"
                       "- 执行建议（包含正确的执行参数）",
            version="2.0.0"
        )
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "script_name": {
                "type": "string",
                "description": "脚本名称（精确匹配，必填）"
            },
            "project_name": {
                "type": "string",
                "description": "项目名称（精确匹配，可选）"
            },
            "test_type": {
                "type": "string",
                "enum": ["api", "ui", "all"],
                "description": "脚本类型：api(API测试脚本)、ui(UI测试脚本)、all(查询所有类型，默认)"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["script_name"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        查询测试脚本
        
        Args:
            script_name: 脚本名称（精确匹配，必填）
            project_name: 项目名称（精确匹配，可选）
            test_type: 脚本类型 'api'/'ui'/'all'，默认 'all'
            
        Returns:
            测试脚本列表
        """
        script_name = kwargs.get("script_name")
        project_name = kwargs.get("project_name")
        test_type = kwargs.get("test_type", "all")
        
        if not script_name:
            return ToolResult(
                success=False,
                data={},
                error="缺少必填参数: script_name"
            )
        
        logger.info(f"[QueryTestScripts] 开始查询: script_name='{script_name}', project_name='{project_name}', test_type='{test_type}'")
        
        try:
            @sync_to_async
            def query_scripts() -> List[Dict[str, Any]]:
                from testmanager_app.models import TestScript
                from test_ui_app.models import UITestScript
                from core.models import Project
                
                project_id: Optional[int] = None
                if project_name:
                    try:
                        project = Project.objects.get(name=project_name)
                        project_id = project.id
                        logger.info(f"[QueryTestScripts] 找到项目: id={project_id}, name='{project.name}'")
                    except Project.DoesNotExist:
                        logger.warning(f"[QueryTestScripts] 项目不存在: '{project_name}'")
                        return []
                
                results: List[Dict[str, Any]] = []
                
                # 查询 API 测试脚本（TestScript）
                if test_type in ["api", "all"]:
                    api_filters: Dict[str, Any] = {'is_active': True, 'name': script_name}
                    if project_id:
                        api_filters['project'] = project_id
                    
                    logger.info(f"[QueryTestScripts] 查询 API 脚本, 条件: {api_filters}")
                    api_scripts = TestScript.objects.filter(**api_filters).select_related('project', 'created_by')
                    
                    for api_script in api_scripts:
                        logger.info(f"[QueryTestScripts] 找到 API 脚本: id={api_script.id}, name='{api_script.name}', type='{api_script.script_type}'")
                        results.append({
                            'id': api_script.id,
                            'name': api_script.name,
                            'test_type': 'api',
                            'script_type': api_script.script_type,
                            'project_id': api_script.project.id if api_script.project else None,
                            'project_name': api_script.project.name if api_script.project else None,
                            'description': api_script.description,
                            'created_by': api_script.created_by.username if api_script.created_by else None,
                            'created_at': api_script.created_at.strftime('%Y-%m-%d %H:%M:%S') if api_script.created_at else None,
                        })
                
                # 查询 UI 测试脚本（UITestScript）
                if test_type in ["ui", "all"]:
                    ui_filters: Dict[str, Any] = {'is_active': True, 'name': script_name}
                    if project_id:
                        ui_filters['project'] = project_id
                    
                    logger.info(f"[QueryTestScripts] 查询 UI 脚本, 条件: {ui_filters}")
                    ui_scripts = UITestScript.objects.filter(**ui_filters).select_related('project', 'created_by')
                    
                    for ui_script in ui_scripts:
                        logger.info(f"[QueryTestScripts] 找到 UI 脚本: id={ui_script.id}, name='{ui_script.name}', browser='{ui_script.browser_type}'")
                        results.append({
                            'id': ui_script.id,
                            'name': ui_script.name,
                            'test_type': 'ui',
                            'script_type': 'playwright',
                            'browser_type': ui_script.browser_type,
                            'project_id': ui_script.project.id if ui_script.project else None,
                            'project_name': ui_script.project.name if ui_script.project else None,
                            'description': ui_script.description,
                            'created_by': ui_script.created_by.username if ui_script.created_by else None,
                            'created_at': ui_script.created_at.strftime('%Y-%m-%d %H:%M:%S') if ui_script.created_at else None,
                        })
                
                logger.info(f"[QueryTestScripts] 总计找到 {len(results)} 个脚本")
                return results
            
            scripts = await query_scripts()
            
            if not scripts:
                message = f"未找到匹配的测试脚本: '{script_name}'"
                if project_name:
                    message += f" (项目: '{project_name}')"
                if test_type != "all":
                    message += f" (类型: '{test_type}')"
                
                logger.warning(f"[QueryTestScripts] {message}")
                
                return ToolResult(
                    success=True,
                    data={
                        "success": True,
                        "scripts": [],
                        "total": 0,
                        "message": message
                    },
                    metadata={
                        "script_name": script_name,
                        "project_name": project_name,
                        "test_type": test_type,
                        "total_found": 0
                    }
                )
            
            logger.info(f"[QueryTestScripts] 查询成功: 返回 {len(scripts)} 个脚本")
            for i, script in enumerate(scripts):
                logger.info(f"[QueryTestScripts] 脚本 {i+1}: id={script['id']}, test_type={script['test_type']}, name='{script['name']}'")
            
            # 构建 suggestion
            suggestion_parts = []
            for script in scripts:
                if script['test_type'] == 'api':
                    suggestion_parts.append(f"API脚本 ID={script['id']}('{script['name']}'): execute_test(test_script_id={script['id']})")
                else:
                    suggestion_parts.append(f"UI脚本 ID={script['id']}('{script['name']}'): execute_test(test_id={script['id']})")
            
            suggestion = f"找到 {len(scripts)} 个脚本:\n" + "\n".join(suggestion_parts)
            suggestion += f"\n\n请确认要执行哪个脚本，然后说\"执行这个脚本\"或\"执行 ID=X 的脚本\""
            
            return ToolResult(
                success=True,
                data={
                    "success": True,
                    "scripts": scripts,
                    "total": len(scripts),
                    "message": f"找到 {len(scripts)} 个匹配的测试脚本",
                    "suggestion": suggestion
                },
                metadata={
                    "script_name": script_name,
                    "project_name": project_name,
                    "test_type": test_type,
                    "total_found": len(scripts)
                }
            )
            
        except Exception as e:
            logger.error(f"[QueryTestScripts] 查询失败: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"查询测试脚本失败: {str(e)}"
            )