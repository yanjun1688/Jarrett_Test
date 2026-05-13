"""
Query Test Scripts Tool
查询测试脚本（通过 UnifiedScript 统一查询所有类型）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.tools.base_tool import BaseTool, ToolResult


class QueryTestScriptsTool(BaseTool):
    """查询测试脚本列表（通过 UnifiedScript 统一查询所有类型）"""

    def __init__(self) -> None:
        super().__init__(
            name='query_test_scripts',
            description=(
                '查询测试脚本列表。根据脚本名称查找所有类型的测试脚本。\n\n'
                '注意：\n'
                '- 脚本名称必须精确匹配（不是模糊搜索）\n'
                '- 支持脚本类型：api、ui、pressure、advanced_pressure\n\n'
                '参数：\n'
                '- script_name：脚本名称，精确匹配\n'
                '- project_name（可选）：项目名称，精确匹配\n'
                '- test_type（可选）：脚本类型，默认查询所有\n\n'
                '返回：\n'
                '- 匹配的测试脚本列表（包含 unified_script_id、名称、类型、项目等）\n'
                '- 执行建议（包含 unified_script_id 用于执行）'
            ),
            version='3.0.0',
        )

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            'script_name': {
                'type': 'string',
                'description': '脚本名称（精确匹配，必填）',
            },
            'project_name': {
                'type': 'string',
                'description': '项目名称（精确匹配，可选）',
            },
            'test_type': {
                'type': 'string',
                'enum': ['api', 'ui', 'pressure', 'advanced_pressure', 'all'],
                'description': (
                    '脚本类型：api(API测试脚本)、ui(UI测试脚本)、'
                    'pressure(压测)、advanced_pressure(高级压测)、'
                    'all(查询所有类型，默认)'
                ),
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ['script_name']

    async def execute(self, **kwargs: Any) -> ToolResult:
        err = self.validate_required(kwargs, "script_name")
        if err:
            return err

        script_name = self.get_param(kwargs, "script_name")
        project_name = self.get_param(kwargs, "project_name")
        test_type = self.get_param(kwargs, "test_type", "all")

        self.logger.info(
            '[QueryTestScripts] script_name=%r, project_name=%r, test_type=%r',
            script_name, project_name, test_type,
        )

        def _query() -> List[Dict[str, Any]]:
            from core.models.unified import UnifiedScript

            filters: Dict[str, Any] = {'is_active': True, 'name': script_name}
            if project_name:
                filters['project__name'] = project_name
            if test_type != 'all':
                filters['script_type'] = test_type

            return list(
                UnifiedScript.objects.filter(**filters)
                .select_related('project', 'created_by', 'content_type')
            )

        scripts_raw = await self.run_query(_query, "查询测试脚本失败")

        if not scripts_raw:
            msg = f"未找到匹配的测试脚本: '{script_name}'"
            if project_name:
                msg += f" (项目: '{project_name}')"
            if test_type != 'all':
                msg += f" (类型: '{test_type}')"
            return ToolResult(success=True, data={'scripts': [], 'total': 0, 'message': msg})

        scripts = []
        for s in scripts_raw:
            scripts.append({
                'id': s.pk,
                'unified_script_id': s.pk,
                'name': s.name,
                'test_type': s.script_type,
                'script_type': s.script_type,
                'project_id': s.project_id,
                'project_name': s.project.name if s.project else None,
                'description': s.description,
                'created_by': s.created_by.username if s.created_by else None,
                'created_at': s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else None,
                'source_id': s.object_id,
                'source_type': s.content_type.model,
            })

        suggestion_parts = [
            f"{sc['script_type']}脚本 unified_script_id={sc['unified_script_id']}"
            f"('{sc['name']}'): execute_test(unified_script_id={sc['unified_script_id']})"
            for sc in scripts
        ]
        suggestion = f"找到 {len(scripts)} 个脚本:\n" + '\n'.join(suggestion_parts)

        return ToolResult(
            success=True,
            data={
                'scripts': scripts,
                'total': len(scripts),
                'message': f'找到 {len(scripts)} 个匹配的测试脚本',
                'suggestion': suggestion,
            },
        )
