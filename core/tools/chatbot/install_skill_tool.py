"""
Install Skill Tool
使用 Celery 异步安装 skill，避免 HTTP 超时
"""
from typing import Dict, Any, List
import logging

from core.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class InstallSkillTool(BaseTool):
    """从 skills.sh 下载并安装 skill（异步）"""
    
    def __init__(self):
        super().__init__(
            name="install_skill",
            description="从 skills.sh 下载并安装一个 skill。当用户要求下载、安装 skill 时调用。",
            version="2.0.0",
            timeout=10
        )
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "skill_id": {
                "type": "string",
                "description": "Skill ID，格式如：chyax98/twu/testcase-generator 或完整URL https://skills.sh/xxx"
            },
            "skill_name": {
                "type": "string",
                "description": "安装后的名称（可选，默认从skill_id提取）"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["skill_id"]
    
    async def execute(self, **kwargs) -> ToolResult:
        skill_id = kwargs.get("skill_id")
        skill_name = kwargs.get("skill_name")
        
        logger.info(f"[InstallSkill] 开始异步安装 skill: skill_id={skill_id}, skill_name={skill_name}")
        
        if not skill_id:
            return ToolResult(
                success=False,
                data={},
                error="缺少参数: skill_id"
            )
        
        if skill_id.startswith("http"):
            if "skills.sh" in skill_id:
                skill_id = skill_id.replace("https://skills.sh/", "").replace("http://skills.sh/", "").rstrip("/")
                logger.info(f"[InstallSkill] 从 skills.sh URL 提取 skill_id: {skill_id}")
            else:
                logger.info(f"[InstallSkill] 保留完整 URL 作为 skill_id: {skill_id}")
        
        try:
            from testmanager_app.tasks import install_skill_task
            
            task = install_skill_task.delay(skill_id, skill_name)  # type: ignore[union-attr]
            
            logger.info(f"[InstallSkill] Celery 任务已创建: task_id={task.id}")  # type: ignore[attr-defined]
            
            return ToolResult(
                success=True,
                data={
                    "task_id": task.id,
                    "skill_id": skill_id,
                    "skill_name": skill_name or skill_id.split('/')[-1],
                    "status": "installing",
                    "message": f"Skill '{skill_id}' 正在后台安装中，请稍后使用"
                },
                metadata={
                    "task_id": task.id,
                    "skill_id": skill_id
                }
            )
            
        except Exception as e:
            logger.error(f"[InstallSkill] 创建 Celery 任务失败: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                error=f"创建安装任务失败: {str(e)}"
            )