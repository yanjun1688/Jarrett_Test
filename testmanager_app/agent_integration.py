"""
Agent集成辅助模块 - 提供Agent辅助生成API测试用例的方法

注意：本模块已从 test_agent_framework 迁移到 core 模块
"""
import json
from typing import Dict, Any, List, Optional
import logging
from asgiref.sync import async_to_sync

from core.models import TestCase, Module

logger = logging.getLogger(__name__)


class APIAgentIntegrationService:
    """API测试Agent集成服务 (使用 TestPlanningAgent)"""
    
    async def generate_test_case_with_agent(
        self,
        api_definition: str,
        project_id: int,
        module_id: Optional[int] = None,
        use_rag: bool = True,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        使用 TestPlanningAgent 生成API测试用例
        
        注意：test_agent_framework 已删除，需要从 core 模块重新实现
        """
        logger.warning("Agent integration service temporarily unavailable - test_agent_framework removed")
        return {
            "success": False,
            "message": "Agent service temporarily unavailable",
            "reason": "test_agent_framework has been removed, migration in progress",
            "test_case": None,
            "flow_ir": None
        }

    generate_test_case_with_agent_sync = async_to_sync(generate_test_case_with_agent)
