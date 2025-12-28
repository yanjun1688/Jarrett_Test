import pandas as pd
from typing import List
from test_ai_agent.models import TestCase, TestSuite, ProcessedPRDChunk
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理器，用于处理测试用例并导出为Excel"""
    
    @staticmethod
    def test_cases_to_dataframe(test_cases: List[TestCase]) -> pd.DataFrame:
        """将测试用例列表转换为DataFrame"""
        data = []
        for case in test_cases:
            data.append({
                'ID': case.id or '',
                'Title': case.title,
                'Description': case.description,
                'Preconditions': case.preconditions or '',
                'Steps': '\n'.join(case.steps),
                'Expected Result': case.expected_result,
                'Priority': case.priority,
                'Type': case.type,
                'Category': case.category or ''
            })
        return pd.DataFrame(data)
    