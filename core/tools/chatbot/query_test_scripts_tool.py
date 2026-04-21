"""
Query Test Scripts Tool
查询测试脚本（通过 UnifiedScript 统一查询所有类型）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


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
        """
        查询测试脚本

        Args:
            script_name: 脚本名称（精确匹配，必填）
            project_name: 项目名称（精确匹配，可选）
            test_type: 脚本类型 'api'/'ui'/'pressure'/'advanced_pressure'/'all'，默认 'all'

        Returns:
            测试脚本列表
        """
        script_name: Optional[str] = kwargs.get('script_name')
        project_name: Optional[str] = kwargs.get('project_name')
        test_type: str = kwargs.get('test_type', 'all')

        if not script_name:
            return ToolResult(
                success=False,
                data={},
                error='缺少必填参数: script_name',
            )

        logger.info(
            '[QueryTestScripts] 开始查询: script_name=%r, '
            'project_name=%r, test_type=%r',
            script_name, project_name, test_type,
        )

        try:
            @sync_to_async
            def query_scripts() -> List[Dict[str, Any]]:
                from core.models.unified import UnifiedScript

                filters: Dict[str, Any] = {
                    'is_active': True,
                    'name': script_name,
                }
                if project_name:
                    filters['project__name'] = project_name
                if test_type != 'all':
                    filters['script_type'] = test_type

                logger.info(
                    '[QueryTestScripts] 查询 UnifiedScript, 条件: %s',
                    filters,
                )

                scripts = (
                    UnifiedScript.objects
                    .filter(**filters)
                    .select_related('project', 'created_by', 'content_type')
                )

                results: List[Dict[str, Any]] = []
                for s in scripts:
                    logger.info(
                        '[QueryTestScripts] 找到脚本: id=%s, name=%r, '
                        'script_type=%r',
                        s.pk, s.name, s.script_type,
                    )
                    results.append({
                        'id': s.pk,
                        'unified_script_id': s.pk,
                        'name': s.name,
                        'test_type': s.script_type,
                        'script_type': s.script_type,
                        'project_id': s.project_id,
                        'project_name': (
                            s.project.name if s.project else None
                        ),
                        'description': s.description,
                        'created_by': (
                            s.created_by.username
                            if s.created_by else None
                        ),
                        'created_at': (
                            s.created_at.strftime('%Y-%m-%d %H:%M:%S')
                            if s.created_at else None
                        ),
                        'source_id': s.object_id,
                        'source_type': s.content_type.model,
                    })

                logger.info(
                    '[QueryTestScripts] 总计找到 %d 个脚本',
                    len(results),
                )
                return results

            scripts = await query_scripts()

            if not scripts:
                message = f"未找到匹配的测试脚本: '{script_name}'"
                if project_name:
                    message += f" (项目: '{project_name}')"
                if test_type != 'all':
                    message += f" (类型: '{test_type}')"

                logger.warning('[QueryTestScripts] %s', message)

                return ToolResult(
                    success=True,
                    data={
                        'success': True,
                        'scripts': [],
                        'total': 0,
                        'message': message,
                    },
                    metadata={
                        'script_name': script_name,
                        'project_name': project_name,
                        'test_type': test_type,
                        'total_found': 0,
                    },
                )

            logger.info(
                '[QueryTestScripts] 查询成功: 返回 %d 个脚本',
                len(scripts),
            )
            for i, script in enumerate(scripts):
                logger.info(
                    '[QueryTestScripts] 脚本 %d: unified_script_id=%s, '
                    'script_type=%s, name=%r',
                    i + 1,
                    script['unified_script_id'],
                    script['script_type'],
                    script['name'],
                )

            # 构建 suggestion
            suggestion_parts: List[str] = []
            for script in scripts:
                suggestion_parts.append(
                    f"{script['script_type']}脚本 "
                    f"unified_script_id={script['unified_script_id']}"
                    f"('{script['name']}'): "
                    f"execute_test("
                    f"unified_script_id={script['unified_script_id']})"
                )

            suggestion = (
                f"找到 {len(scripts)} 个脚本:\n"
                + '\n'.join(suggestion_parts)
                + '\n\n请确认要执行哪个脚本，'
                + '然后说"执行这个脚本"或'
                + '"执行 unified_script_id=X 的脚本"'
            )

            return ToolResult(
                success=True,
                data={
                    'success': True,
                    'scripts': scripts,
                    'total': len(scripts),
                    'message': f'找到 {len(scripts)} 个匹配的测试脚本',
                    'suggestion': suggestion,
                },
                metadata={
                    'script_name': script_name,
                    'project_name': project_name,
                    'test_type': test_type,
                    'total_found': len(scripts),
                },
            )

        except Exception as e:
            logger.error(
                '[QueryTestScripts] 查询失败: %s', str(e), exc_info=True,
            )
            return ToolResult(
                success=False,
                data={},
                error=f'查询测试脚本失败: {str(e)}',
            )
