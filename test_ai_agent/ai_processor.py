"""
AI处理器 - 处理PRD并生成测试用例
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
import os
from typing import Any
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from core.agents.llm import create_llm_service
import logging

logger = logging.getLogger(__name__)


class AIProcessor:
    """AI处理器，用于生成测试用例"""

    def __init__(self, api_key=None, model_name=None, temperature=None):
        # 延迟加载环境变量（仅在初始化时执行，不在模块级别）
        load_dotenv()

        # 初始化语言模型，使用 Zhipu (GLM) 模型
        if not api_key:
            api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            logger.warning("ZHIPU_API_KEY not found in environment variables or parameters")
            raise ValueError("API Key is required. Please provide ZHIPU_API_KEY in environment or pass it as parameter.")

        # 模型名称配置，支持从环境变量读取
        if not model_name:
            model_name = os.getenv("ZHIPU_MODEL_NAME", "glm-4.7-flash")

        # Temperature 配置，支持从环境变量读取
        if temperature is None:
            temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))

        # 使用 Zhipu LLM 服务
        self.llm_service = create_llm_service(
            provider="zhipu",
            model_name=model_name,
            api_key=api_key,
            temperature=temperature
        )

        # 定义Prompt模板 - 要求返回Markdown格式
        self.prompt_template = PromptTemplate(
            input_variables=["prd_content"],
            template="""
你是一个专业的软件测试工程师，请根据以下产品需求文档(PRD)内容进行分析并生成测试用例。

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
""")

    async def analyze_prd(self, prd_content: str) -> str:
        """分析PRD文档并返回Markdown格式的测试用例分析"""
        logger.info("Analyzing PRD content")

        response = await self.llm_service.generate(
            prompt=self.prompt_template.format(prd_content=prd_content),
            system_message="你是一个专业的软件测试工程师，擅长分析PRD文档。请使用Markdown格式输出详细的测试用例分析。"
        )

        logger.info("PRD analysis completed")
        return response

    async def process_document(self, file_path: str) -> dict[str, Any]:
        """处理文档并返回分析结果"""
        from .document_loader import DocumentLoader

        # 加载文档
        document_loader = DocumentLoader()
        content = document_loader.load_document(file_path)

        # 分析文档
        analysis = await self.analyze_prd(content)

        return {
            'content': content,
            'analysis': analysis
        }
