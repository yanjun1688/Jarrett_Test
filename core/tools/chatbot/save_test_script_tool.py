"""
Save Test Script Tool
保存测试脚本到数据库
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone

from core.tools.base_tool import BaseTool, ToolResult
from core.schemas.script_config import SCRIPT_CONFIG_SCHEMA_DESCRIPTION, validate_script_config

logger = logging.getLogger(__name__)


class SaveTestScriptTool(BaseTool):
    """保存测试脚本到数据库"""
    
    def __init__(self) -> None:
        super().__init__(
            name="save_test_script",
            description="将生成的API测试脚本保存到指定项目。code 必须为 JSON 格式的 API 测试配置，不能是 Python 代码。多个测试场景应合并为一个脚本（每个场景作为 steps 数组中的一个独立步骤），不要每个场景单独保存。\n\n参数：\n- code（必需）：测试脚本代码（JSON 格式，见 code 参数说明）\n- project_id（必需）：目标项目ID\n- name（可选）：脚本名称\n- source（可选）：来源标识，默认chatbot\n\n返回：\n- script_id: 保存的脚本ID\n- script_name: 脚本名称",
            version="1.0.0"
        )
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "code": {
                "type": "string",
                "description": f"API 测试配置（JSON 格式）。{SCRIPT_CONFIG_SCHEMA_DESCRIPTION}"
            },
            "project_id": {
                "type": "integer",
                "description": "目标项目ID"
            },
            "name": {
                "type": "string",
                "description": "脚本名称（可选）"
            },
            "source": {
                "type": "string",
                "enum": ["chatbot", "manual_upload", "manual_create"],
                "description": "来源标识",
                "default": "chatbot"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["code", "project_id"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        保存测试脚本
        
        Args:
            code: 测试脚本代码
            project_id: 目标项目ID
            name: 脚本名称
            source: 来源标识
            user_id: 用户ID
            
        Returns:
            保存结果
        """
        code = kwargs.get("code")
        project_id = kwargs.get("project_id")
        name = kwargs.get("name")
        source = kwargs.get("source", "chatbot")
        user_id = kwargs.get("user_id")

        logger.info(f'[SaveTestScript] 参数: project_id={project_id}, name={name!r}, source={source}, user_id={user_id}')

        if not code or not project_id:
            logger.warning(f'[SaveTestScript] 参数缺失: code={bool(code)}, project_id={bool(project_id)}')
            if code and not project_id:
                msg = "缺少目标项目ID。请先调用 query_projects 查询可用项目列表，让用户选择后再保存。"
            else:
                msg = "缺少必填参数: code 或 project_id"
            return ToolResult(
                success=False,
                data={},
                error=msg
            )

        is_valid, error_msg = validate_script_config(code)
        if not is_valid:
            logger.warning(f'[SaveTestScript] code 格式校验失败: {error_msg}')
            return ToolResult(
                success=False,
                data={},
                error=f"code 格式错误: {error_msg}。请参考参数说明中的格式要求重试。"
            )

        try:
            import json as json_lib
            formatted_code = json_lib.dumps(json_lib.loads(code), indent=2, ensure_ascii=False)
            script_name = name or f"Generated Script {timezone.now().strftime('%Y%m%d%H%M%S')}"
            logger.info(f'[SaveTestScript] code 校验通过，准备创建脚本: {script_name}')

            script = await sync_to_async(self._create_script)(
                name=script_name,
                code=formatted_code,
                project_id=project_id,
                source=source,
                user_id=user_id
            )

            logger.info(f'[SaveTestScript] 创建成功: script_id={script.id}, project_id={project_id}')
            return ToolResult(
                success=True,
                data={
                    "script_id": str(script.id),
                    "script_name": script_name,
                    "view_url": f"/test-scripts/{script.id}",
                    "message": f"成功保存脚本：{script_name}"
                },
                metadata={
                    "project_id": project_id,
                    "source": source,
                    "script_type": "api"
                }
            )

        except Exception as e:
            logger.error(f'[SaveTestScript] 创建失败: {e}', exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"保存测试脚本失败: {str(e)}"
            )
    
    def _create_script(
        self,
        name: str,
        code: str,
        project_id: int,
        source: str,
        user_id: Optional[int] = None
    ) -> Any:
        """创建测试脚本（和手动创建走同一 Serializer）"""
        from testmanager_app.serializers import TestScriptCreateSerializer

        data: Dict[str, Any] = {
            'name': name,
            'description': f"Generated from ChatBot at {timezone.now().isoformat()}",
            'script_type': 'api',
            'content': code,
            'project': project_id,
        }

        serializer = TestScriptCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        extra_kwargs: Dict[str, Any] = {
            'source': source,
            'is_active': True,
        }
        if user_id:
            extra_kwargs['created_by_id'] = user_id

        return serializer.save(**extra_kwargs)