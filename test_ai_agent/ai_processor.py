import os
import json
from typing import List
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from dotenv import load_dotenv
from .models import TestCase, TestSuite, ProcessedPRDChunk
import logging

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class AIProcessor:
    """AI处理器，用于生成测试用例"""
    
    def __init__(self, api_key=None, model_name=None, temperature=None):
        # 初始化语言模型，支持动态传入api_key
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables or parameters")
            raise ValueError("API Key is required. Please provide OPENAI_API_KEY in environment or pass it as parameter.")
        
        # 模型名称配置，支持从环境变量读取
        if not model_name:
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        
        # Temperature 配置，支持从环境变量读取
        if temperature is None:
            temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            temperature=temperature
        )
        
        # 定义输出解析器
        self.parser = JsonOutputParser()
        
        # 定义Prompt模板
        self.prompt_template = PromptTemplate(
            input_variables=["prd_content"],
            template="""
            你是一个专业的软件测试工程师，请根据以下产品需求文档内容生成详细的测试用例。
            
            要求：
            1. 分析需求中的功能点和边界条件
            2. 为每个功能点生成多个测试用例，包括正常情况、异常情况和边界值测试
            3. 测试用例应包括标题、描述、前置条件、步骤、预期结果等字段
            4. 指定测试用例的优先级（High/Medium/Low）和类型（Functional/Non-functional）
            5. 包含具体的边界值示例
            6. 考虑异常场景和错误处理
            
            产品需求文档内容：
            {prd_content}
            
            请严格按照以下JSON格式输出结果：
            {{
                "test_suites": [
                    {{
                        "name": "测试套件名称",
                        "description": "测试套件描述",
                        "test_cases": [
                            {{
                                "title": "测试用例标题",
                                "description": "测试用例详细描述",
                                "preconditions": "前置条件（可选）",
                                "steps": ["步骤1", "步骤2", ...],
                                "expected_result": "预期结果",
                                "priority": "High",
                                "type": "Functional",
                                "category": "UI"
                            }}
                        ]
                    }}
                ]
            }}
            
            注意事项：
            1. 必须返回有效的JSON格式
            2. 不要包含任何额外的文本或解释
            3. 确保所有字段都符合要求的格式
            4. 至少生成3个测试用例
            5. 包含边界值测试用例
            """
        )
        
        # 创建处理链
        self.chain = self.prompt_template | self.llm | self.parser
    
    def generate_test_cases(self, prd_content: str) -> dict:
        """根据PRD内容生成测试用例"""
        try:
            logger.info("Generating test cases from PRD content")
            response = self.chain.invoke({"prd_content": prd_content})
            return response
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}")
            raise
    
    def process_prd_chunk(self, chunk_id: str, content: str, api_key: str = None) -> ProcessedPRDChunk:
        """处理PRD块并生成测试用例"""
        try:
            raw_output = self.generate_test_cases(content)
            
            # 解析生成的测试套件
            test_suites = []
            if 'test_suites' in raw_output:
                for suite_data in raw_output['test_suites']:
                    test_cases = []
                    for case_data in suite_data.get('test_cases', []):
                        test_case = TestCase(
                            title=case_data.get('title', ''),
                            description=case_data.get('description', ''),
                            preconditions=case_data.get('preconditions'),
                            steps=case_data.get('steps', []),
                            expected_result=case_data.get('expected_result', ''),
                            priority=case_data.get('priority', 'Medium'),
                            type=case_data.get('type', 'Functional'),
                            category=case_data.get('category')
                        )
                        test_cases.append(test_case)
                    
                    test_suite = TestSuite(
                        name=suite_data.get('name', ''),
                        description=suite_data.get('description'),
                        test_cases=test_cases
                    )
                    test_suites.append(test_suite)
            
            return ProcessedPRDChunk(
                chunk_id=chunk_id,
                content=content,
                test_suites=test_suites
            )
        except Exception as e:
            logger.error(f"Error processing PRD chunk {chunk_id}: {str(e)}")
            raise