"""
Save Test Case Tool
保存测试用例到数据库
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SaveTestCaseTool(BaseTool):
    """保存测试用例到数据库"""
    
    def __init__(self) -> None:
        super().__init__(
            name="save_test_case",
            description="将生成的测试用例保存到指定项目。\n\n参数：\n- content（必需）：测试用例内容（Markdown格式）\n- project_id（必需）：目标项目ID\n- source（可选）：来源标识，默认chatbot\n- prd_document_id（可选）：关联的PRD文档ID\n- conversation_id（可选）：生成会话ID\n\n返回：\n- saved_count: 保存数量\n- test_case_ids: 保存的用例ID列表",
            version="1.0.0"
        )
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "content": {
                "type": "string",
                "description": "测试用例内容（Markdown格式）"
            },
            "project_id": {
                "type": "integer",
                "description": "目标项目ID"
            },
            "source": {
                "type": "string",
                "enum": ["chatbot", "manual_upload", "manual_create"],
                "description": "来源标识",
                "default": "chatbot"
            },
            "prd_document_id": {
                "type": "string",
                "description": "关联的PRD文档ID（可选）"
            },
            "conversation_id": {
                "type": "string",
                "description": "生成会话ID（可选）"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["content", "project_id"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        保存测试用例
        
        Args:
            content: 测试用例内容
            project_id: 目标项目ID
            source: 来源标识
            prd_document_id: PRD文档ID
            conversation_id: 会话ID
            user_id: 用户ID
            
        Returns:
            保存结果
        """
        content = kwargs.get("content")
        project_id = kwargs.get("project_id")
        source = kwargs.get("source", "chatbot")
        prd_document_id = kwargs.get("prd_document_id")
        conversation_id = kwargs.get("conversation_id")
        user_id = kwargs.get("user_id")

        logger.info(f'[SaveTestCase] 参数: project_id={project_id}, source={source}, conversation_id={conversation_id}, user_id={user_id}, prd_document_id={prd_document_id}')

        if not content or not project_id:
            logger.warning(f'[SaveTestCase] 参数缺失: content={bool(content)}, project_id={bool(project_id)}')
            if content and not project_id:
                msg = "缺少目标项目ID。请先调用 query_projects 查询可用项目列表，让用户选择后再保存。"
            else:
                msg = "缺少必填参数: content 或 project_id"
            return ToolResult(
                success=False,
                data={},
                error=msg
            )
        
        try:
            test_cases = self._parse_test_cases(content)
            logger.info(f'[SaveTestCase] 解析出 {len(test_cases)} 条用例')
            created_ids: List[int] = []
            
            for i, case in enumerate(test_cases):
                logger.info(f'[SaveTestCase] 保存第 {i+1}/{len(test_cases)} 条: {case["title"][:50]}')
                tc = await self._create_test_case(
                    project_id=project_id,
                    title=case['title'],
                    steps=case['steps'],
                    expected_result=case.get('expected', ''),
                    precondition=case.get('precondition', ''),
                    source=source,
                    prd_document_id=prd_document_id,
                    conversation_id=conversation_id,
                    user_id=user_id
                )
                created_ids.append(tc.id)
                logger.info(f'[SaveTestCase] 第 {i+1} 条保存成功: test_case_id={tc.id}')
            
            logger.info(f'[SaveTestCase] 全部保存完成: 共 {len(created_ids)} 条, project_id={project_id}')
            return ToolResult(
                success=True,
                data={
                    "saved_count": len(created_ids),
                    "test_case_ids": [str(id) for id in created_ids],
                    "view_url": f"/test-cases?project={project_id}&source={source}",
                    "message": f"成功保存 {len(created_ids)} 条测试用例"
                },
                metadata={
                    "project_id": project_id,
                    "source": source
                }
            )
            
        except Exception as e:
            logger.error(f'[SaveTestCase] 保存失败: {e}', exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"保存测试用例失败: {str(e)}"
            )
    
    def _parse_test_cases(self, content: str) -> List[Dict[str, Any]]:
        """解析 Markdown 内容提取用例"""
        cases: List[Dict[str, Any]] = []
        
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
        
        for section in sections[1:]:
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            title = lines[0].strip()
            remaining_lines = '\n'.join(lines[1:]) if len(lines) > 1 else ''
            
            expected = ''
            precondition = ''
            steps = remaining_lines
            
            expected_match = re.search(r'(?:\[预期结果\]|预期结果[：:])\s*(.+)', remaining_lines)
            if expected_match:
                expected = expected_match.group(1).strip()
            
            precondition_match = re.search(r'(?:\[前置条件\]|前置条件[：:])\s*(.+)', remaining_lines)
            if precondition_match:
                precondition = precondition_match.group(1).strip()
            
            cases.append({
                "title": title,
                "steps": steps,
                "expected": expected,
                "precondition": precondition
            })
        
        if not cases:
            cases.append({
                "title": "Generated Test Case",
                "steps": content,
                "expected": "",
                "precondition": ""
            })
        
        return cases
    
    async def _create_test_case(
        self,
        project_id: int,
        title: str,
        steps: str,
        expected_result: str,
        precondition: str,
        source: str,
        prd_document_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Any:
        """创建功能测试用例（保存到 FeatureTestCase，与前端"功能测试用例"页面一致）"""
        from testmanager_app.serializers import FeatureTestCaseSerializer

        def _save() -> Any:
            data: Dict[str, Any] = {
                'title': title,
                'project': project_id,
                'pre_steps': precondition,
                'steps': steps,
                'expected_result': expected_result,
            }

            serializer = FeatureTestCaseSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            extra_kwargs: Dict[str, Any] = {}
            if user_id:
                extra_kwargs['created_by_id'] = user_id

            return serializer.save(**extra_kwargs)

        return await sync_to_async(_save)()
    
    async def _resolve_conversation_id(self, conversation_id: str) -> Optional[int]:
        """解析 conversation_id，返回主键"""
        from core.models.agents import AgentConversation
        
        try:
            conv_obj = await sync_to_async(AgentConversation.objects.filter(
                conversation_id=str(conversation_id)
            ).first)()
            if conv_obj:
                return conv_obj.pk
        except Exception as e:
            logger.warning(f"Failed to query conversation: {e}")
        
        try:
            return int(conversation_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid conversation_id: {conversation_id}")
            return None