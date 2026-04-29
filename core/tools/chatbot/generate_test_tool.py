"""
Generate Test Tool
根据PRD文档或API定义生成测试用例
直接调用 LLM，不再走 TestGenerationService
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult
from core.agents.llm import create_llm_service

logger = logging.getLogger(__name__)


class GenerateTestTool(BaseTool):
    """根据PRD文档或API定义生成测试用例"""

    def __init__(self, llm_service: Optional[Any] = None) -> None:
        super().__init__(
            name="generate_test",
            description="根据PRD文档或API定义生成测试用例，返回预览供用户确认。\n\n参数：\n- document_id（必需）：知识库文档ID\n- document_type（可选）：文档类型（prd/api），默认prd\n\n返回：\n- preview: 测试用例预览（前500字符）\n- full_content: 完整内容\n- 确认保存提示",
            version="2.0.0"
        )
        self._llm_service = llm_service

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "document_id": {
                "type": "string",
                "description": "PRD文档ID或知识库文档ID"
            },
            "document_type": {
                "type": "string",
                "enum": ["prd", "api"],
                "description": "文档类型：prd 或 api",
                "default": "prd"
            }
        }

    def _get_required_parameters(self) -> List[str]:
        return ["document_id"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        生成测试用例，直接调用 LLM

        Args:
            document_id: 文档ID
            document_type: 文档类型（prd/api）

        Returns:
            测试用例预览
        """
        document_id = kwargs.get("document_id")
        document_type = kwargs.get("document_type", "prd")

        if not document_id:
            return ToolResult(
                success=False,
                data={
                    "options": [
                        {"id": "upload_prd", "label": "上传PRD文档", "description": "先上传PRD文档到知识库"},
                        {"id": "describe_test", "label": "直接描述需求", "description": "直接描述测试需求生成用例"},
                    ],
                    "message": "请先选择PRD文档或描述您的测试需求："
                },
                error="Missing required parameter: document_id"
            )

        try:
            # 获取文档内容
            doc = await self._get_document(document_id)

            if not doc:
                return ToolResult(
                    success=False,
                    data={
                        "options": [
                            {"id": "upload_prd", "label": "上传PRD文档", "description": "文档不存在，请先上传"},
                            {"id": "query_prd", "label": "查询知识库", "description": "查询知识库中的PRD文档"},
                        ],
                        "message": f"文档 {document_id} 不存在，请先上传PRD文档或重新选择："
                    },
                    error=f"文档 {document_id} 不存在"
                )

            # 初始化 LLM 服务
            if not self._llm_service:
                self._llm_service = create_llm_service(provider='zhipu')

            # 获取文档内容
            content = doc.content if hasattr(doc, 'content') and doc.content else doc.file_path if hasattr(doc, 'file_path') else None
            if hasattr(doc, 'file_path') and doc.file_path:
                # 从文件读取内容
                try:
                    import aiofiles
                    async with aiofiles.open(doc.file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                except Exception as e:
                    logger.warning(f"Failed to read document file: {e}")
                    content = None

            if not content:
                return ToolResult(
                    success=False,
                    data={},
                    error="无法读取文档内容"
                )

            # 根据文档类型选择 prompt
            if document_type == "prd":
                prompt = self._build_prd_prompt(content)
                system_message = "你是专业的软件测试工程师，擅长分析PRD文档并生成全面的测试用例。"
            else:
                prompt = self._build_api_prompt(content)
                system_message = "你是专业的API测试工程师，擅长根据API定义生成测试用例。"

            # 调用 LLM 生成
            response = await self._llm_service.generate(
                prompt=prompt,
                system_message=system_message,
                temperature=0.3,
                max_tokens=4000
            )

            # 生成结果
            quality_score = self._calculate_quality_score(response, document_type)
            preview = response[:500] + "..." if len(response) > 500 else response

            return ToolResult(
                success=True,
                data={
                    "preview": preview,
                    "full_content": response,
                    "document_id": document_id,
                    "document_type": document_type,
                    "quality_score": quality_score,
                    "message": "已生成测试用例，请确认是否保存："
                },
                metadata={
                    "document_type": document_type,
                    "content_length": len(response),
                    "quality_score": quality_score
                }
            )

        except Exception as e:
            logger.error(f"Generate test failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"测试用例生成失败: {str(e)}"
            )

    def _build_prd_prompt(self, prd_content: str) -> str:
        """构建PRD分析prompt"""
        return f"""请根据以下产品需求文档(PRD)内容进行分析并生成测试用例。

## PRD内容

{prd_content}

## 请按以下格式输出分析结果

### 1. 需求概述
简要总结PRD中的主要功能点和测试范围。

### 2. 测试策略
说明测试的整体策略和方法。

### 3. 测试用例

#### 功能测试
| 用例编号 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|---------|---------|---------|---------|---------|--------|
| TC-001 | ... | ... | ... | ... | High/Medium/Low |

#### 边界值测试
| 用例编号 | 测试点 | 边界值 | 预期结果 | 优先级 |
|---------|-------|-------|---------|--------|
| BV-001 | ... | ... | ... | ... |

#### 异常场景测试
| 用例编号 | 异常场景 | 测试步骤 | 预期结果 |
|---------|---------|---------|---------|
| EX-001 | ... | ... | ... |

### 4. 测试数据建议
列出需要的测试数据。

### 5. 风险评估
列出潜在的风险和注意事项。

请使用Markdown格式输出，确保格式清晰、易于阅读。

请自我检查：
- 是否覆盖了所有主要功能点？
- 是否包含边界值和异常场景？
- 测试步骤是否清晰可执行？
- 预期结果是否明确？"""

    def _build_api_prompt(self, api_content: str) -> str:
        """构建API分析prompt"""
        return f"""请根据以下API定义生成测试用例。

## API定义

{api_content}

## 请生成以下测试用例

### 1. 正常场景测试
- 标准请求测试
- 必填字段验证
- 可选字段验证

### 2. 异常场景测试
- 参数缺失测试
- 参数类型错误测试
- 参数值范围测试
- 鉴权失败测试
- 资源不存在测试

### 3. 边界值测试
- 最大/最小值测试
- 空值/Null测试
- 特殊字符测试
- 超长字符串测试

### 4. 性能测试建议
- 并发测试场景
- 大数据量测试

请使用Markdown表格格式输出，包含：
| 用例编号 | 用例描述 | 请求方法 | 请求路径 | 请求参数 | 预期状态码 | 预期响应 |

请自我检查：
- 是否覆盖了所有接口路径？
- 是否包含HTTP方法的组合？
- 是否考虑了安全和鉴权？
- 边界场景是否完整？"""

    async def _get_document(self, document_id: str) -> Optional[Any]:
        """获取文档"""
        try:
            doc_id_int = int(document_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid document_id format: {document_id}")
            return None

        try:
            from core.models.knowledge import KnowledgeDocument
            return await sync_to_async(KnowledgeDocument.objects.get)(id=doc_id_int)
        except KnowledgeDocument.DoesNotExist:
            logger.warning(f"Document not found: {doc_id_int}")
            return None

    def _calculate_quality_score(self, content: str, document_type: str) -> int:
        """计算生成内容的质量评分"""
        score = 0

        if len(content) >= 200:
            score += 20

        if '## ' in content or 'TC-' in content or '| 用例编号' in content:
            score += 30

        if '步骤' in content or 'step' in content.lower():
            score += 20

        if '预期' in content or 'expected' in content.lower():
            score += 20

        if '边界' in content or 'boundary' in content.lower() or '异常' in content:
            score += 10

        return min(score, 100)
