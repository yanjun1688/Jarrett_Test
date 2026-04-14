from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional

class TestCase(BaseModel):
    """测试用例模型"""
    id: Optional[str] = None
    title: str
    description: str
    preconditions: Optional[str] = None
    steps: List[str]
    expected_result: str
    priority: str  # High, Medium, Low
    type: str  # Functional, Non-functional, etc.
    category: Optional[str] = None  # UI, API, Integration, etc.

class TestSuite(BaseModel):
    """测试套件模型"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    test_cases: List[TestCase]

class ProcessedPRDChunk(BaseModel):
    """处理后的PRD块模型"""
    chunk_id: str
    content: str
    test_suites: List[TestSuite]
