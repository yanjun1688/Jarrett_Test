"""
Agent集成辅助模块
提供Agent辅助生成UI测试脚本的辅助方法

注意：test_agent_framework 已删除，本模块需要重构
"""
from typing import Dict, Any, List, Optional
import logging
from asgiref.sync import async_to_sync

from .services import UITestService

logger = logging.getLogger(__name__)


class AgentIntegrationService:
    """Agent集成服务 (暂时不可用)"""
    
    def __init__(self):
        self.ui_test_service = UITestService()
    
    async def generate_script_with_agent(
        self,
        description: str,
        project_id: int,
        url: Optional[str] = None,
        use_rag: bool = True,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        使用 TestPlanningAgent 生成UI测试脚本
        
        注意：test_agent_framework 已删除，服务暂时不可用
        """
        logger.warning("AgentIntegrationService.generate_script_with_agent called but test_agent_framework has been removed")
        return {
            'success': False,
            'error': 'Agent service temporarily unavailable',
            'reason': 'test_agent_framework has been removed, migration in progress'
        }
    
    generate_script_with_agent_sync = async_to_sync(generate_script_with_agent)
