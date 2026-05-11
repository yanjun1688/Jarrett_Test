"""
Install Skill Tool
同步安装 skill，直接返回安装结果，避免 Celery 异步的"已提交但不知结果"问题
"""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.tools.base_tool import BaseTool, ToolResult

import logging

logger = logging.getLogger(__name__)

# ANSI 转义码正则
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


class InstallSkillTool(BaseTool):
    """从 GitHub 或 skills.sh 下载并安装 skill（同步）"""

    def __init__(self):
        super().__init__(
            name="install_skill",
            description="Install a skill from GitHub or skills.sh. Call when user asks to install/download a skill.",
            version="2.0.0",
            timeout=300,
        )

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "skill_id": {
                "type": "string",
                "description": "Skill ID，格式如：owner/repo 或完整 GitHub URL",
            },
            "skill_name": {
                "type": "string",
                "description": "安装后的名称（可选，默认从 skill_id 提取）",
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ["skill_id"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        raw_input: str = kwargs["skill_id"].strip()
        skill_name: Optional[str] = kwargs.get("skill_name")

        logger.info(f"[InstallSkill] 开始安装: skill_id={raw_input}, skill_name={skill_name}")

        if not raw_input:
            return ToolResult(success=False, data={}, error="缺少参数: skill_id")

        # 从各种 URL 格式中提取 owner/repo
        skill_id = self._extract_skill_id(raw_input)
        if not skill_id:
            return ToolResult(success=False, data={}, error=f"无法从输入中识别 skill 仓库: {raw_input}")

        # 安全校验
        if not re.match(r'^[a-zA-Z0-9@/._-]+$', skill_id):
            return ToolResult(success=False, data={}, error=f"skill_id 包含非法字符: {skill_id}")

        final_name = skill_name or skill_id.rstrip("/").split("/")[-1]

        # 查找 npx
        from shared.utils.command_utils import get_npx_command
        npx_cmd = get_npx_command()
        if not npx_cmd:
            return ToolResult(
                success=False, data={},
                error="npx 未找到，请确保 Node.js 已安装",
            )

        # project_root 使用 Django settings，不硬编码
        from django.conf import settings
        project_root: Path = settings.BASE_DIR
        cmd = [npx_cmd, "skills", "add", skill_id, "--agent", "openclaw", "-y"]
        if skill_name:
            cmd.extend(["--skill", skill_name])

        logger.info(f"[InstallSkill] 执行: {' '.join(cmd)}")

        # 在子线程中同步执行（跨平台兼容，Windows 上 asyncio 子进程不可用）
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    cwd=str(project_root),
                    timeout=self.timeout,
                ),
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[InstallSkill] 超时 ({self.timeout}s): {skill_id}")
            return ToolResult(success=False, data={}, error=f"安装超时（{self.timeout}秒），请重试")
        except FileNotFoundError:
            return ToolResult(success=False, data={}, error=f"命令不存在: {cmd[0]}")
        except Exception as e:
            logger.error(f"[InstallSkill] 执行异常: {e}", exc_info=True)
            return ToolResult(success=False, data={}, error=f"安装失败: {e}")

        stdout = _ANSI_RE.sub("", result.stdout.decode("utf-8", errors="replace"))
        stderr = _ANSI_RE.sub("", result.stderr.decode("utf-8", errors="replace"))

        if result.returncode != 0:
            error_msg = stderr or stdout or "未知错误"
            logger.error(f"[InstallSkill] 失败: {error_msg[:500]}")
            return ToolResult(success=False, data={}, error=f"安装失败: {error_msg[:500]}")

        logger.info(f"[InstallSkill] 安装成功: {skill_id}")

        # 刷新 skill 全局缓存（类级，影响所有 SkillLoader 实例）
        from core.agents.skill_loader import SkillLoader
        SkillLoader.invalidate_cache()
        logger.info("[InstallSkill] skill 缓存已刷新")

        return ToolResult(
            success=True,
            data={
                "skill_id": skill_id,
                "skill_name": final_name,
                "message": f"Skill '{final_name}' 安装成功！",
            },
        )

    @staticmethod
    def _extract_skill_id(raw: str) -> Optional[str]:
        """从 URL 或 ID 中提取 owner/repo 格式"""
        cleaned = raw.strip()
        if not cleaned:
            return None

        # 已经是 owner/repo 格式（允许多级路径）
        if re.match(r'^[a-zA-Z0-9@._-]+(/[a-zA-Z0-9@._-]+)+$', cleaned):
            return cleaned

        # GitHub URL: https://github.com/owner/repo 或 https://github.com/owner/repo.git
        m = re.search(r'github\.com[/:]([a-zA-Z0-9@._-]+/[a-zA-Z0-9@._-]+?)(?:\.git)?\s*$', cleaned)
        if m:
            return m.group(1)

        # skills.sh URL
        m = re.search(r'skills\.sh/([a-zA-Z0-9@/._-]+)', cleaned)
        if m:
            return m.group(1).rstrip("/")

        return None