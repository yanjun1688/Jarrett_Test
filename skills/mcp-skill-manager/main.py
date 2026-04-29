"""MCP Skill Manager Server

Provides skill search, install, and list management MCP Server
Replaces direct npx CLI calls with unified handling for ANSI/formatting/errors
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

mcp = FastMCP("skill-manager")

# Project root (for locating skills directory)
PROJECT_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
AGENT_SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"


def strip_ansi(text: str) -> str:
    """Clean ANSI escape codes"""
    if not text:
        return text
    # eslint-disable-next-line no-control-regex
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def get_npx_command() -> str:
    """Get npx command"""
    import shutil
    npx_cmd = shutil.which('npx')
    return npx_cmd or 'npx'


@mcp.tool()
async def search_skills(keyword: str) -> dict[str, Any]:
    """
    搜索远程 skills，返回原始终端输出（带 ANSI 颜色码）

    Args:
        keyword: 搜索关键词，如 "webapp", "test", "api"

    Returns:
        {"success": bool, "output": str, "error": str|None}
        output 包含原始 ANSI 转义码，前端可用终端组件渲染
    """
    logger.info(f"[MCP Skill Manager] Searching skills: keyword={keyword}")

    try:
        # 输入校验
        if not keyword or not keyword.strip():
            return {
                "success": False,
                "error": "搜索关键词不能为空",
                "output": ""
            }

        keyword = keyword.strip()
        if not re.match(r'^[a-zA-Z0-9@/._\- ]+$', keyword):
            return {
                "success": False,
                "error": "搜索关键词包含非法字符",
                "output": ""
            }

        npx_cmd = get_npx_command()

        # Execute npx skills find async
        proc = await asyncio.create_subprocess_exec(
            npx_cmd, 'skills', 'find', keyword,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT)
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=60
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("[MCP Skill Manager] Search timeout")
            return {
                "success": False,
                "error": "搜索超时（超过60秒）",
                "output": ""
            }

        if proc.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "搜索失败"
            logger.error(f"[MCP Skill Manager] Search failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "output": ""
            }

        # Return raw output (with ANSI color codes)
        output = stdout.decode('utf-8', errors='replace')
        logger.info(f"[MCP Skill Manager] Search success, output length: {len(output)}")

        return {
            "success": True,
            "output": output,
            "error": None
        }

    except Exception as e:
        logger.exception("[MCP Skill Manager] Search exception")
        return {
            "success": False,
            "error": str(e),
            "output": ""
        }


@mcp.tool()
async def install_skill(skill_id: str, skill_name: str | None = None) -> dict[str, Any]:
    """
    安装 skill 到本地

    Args:
        skill_id: Skill ID，如 "@opencode-ai/skills/webapp-testing@latest"
        skill_name: 可选，安装后的名称

    Returns:
        {"success": bool, "message": str, "error": str|None, ...}
    """
    logger.info(f"[MCP Skill Manager] Installing skill: skill_id={skill_id}, skill_name={skill_name}")

    try:
        # 输入校验
        if not skill_id or not skill_id.strip():
            return {
                "success": False,
                "error": "skill_id 不能为空"
            }

        skill_id = skill_id.strip()

        # Strip ANSI (if input contains colored text)
        skill_id = strip_ansi(skill_id)

        if not re.match(r'^[a-zA-Z0-9@/._\-]+$', skill_id):
            return {
                "success": False,
                "error": f"skill_id 包含非法字符: {skill_id}"
            }

        if skill_name and not re.match(r'^[a-zA-Z0-9@/._\-]+$', skill_name):
            return {
                "success": False,
                "error": "skill_name 包含非法字符"
            }

        npx_cmd = get_npx_command()

        # 构建命令
        cmd = [npx_cmd, 'skills', 'add', skill_id, '--agent', 'openclaw', '-y']
        if skill_name:
            cmd.extend(['--skill', skill_name])

        logger.info(f"[MCP Skill Manager] Executing command: {' '.join(cmd)}")

        # Execute install asynchronously (wrap sync process to avoid blocking)
        # Install is blocking, wrapped as async to avoid blocking MCP Server
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT)
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=300  # 5分钟超时
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("[MCP Skill Manager] Install timeout")
            return {
                "success": False,
                "error": "安装超时（超过300秒）"
            }

        if proc.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "安装失败"
            stdout_msg = stdout.decode('utf-8', errors='replace')[:500] if stdout else None
            logger.error(f"[MCP Skill Manager] Install failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "stdout": stdout_msg
            }

        # Extract basename
        basename = skill_id.split('@')[0].split('/')[-1]
        installed_name = skill_name or basename
        installed_path = AGENT_SKILLS_DIR / installed_name

        logger.info(f"[MCP Skill Manager] Install success: {installed_name}")

        return {
            "success": True,
            "skill_id": skill_id,
            "skill_name": installed_name,
            "basename": basename,
            "installed_path": str(installed_path),
            "message": f"Skill '{installed_name}' 安装成功",
            "stdout": stdout.decode('utf-8', errors='replace')[:500] if stdout else None
        }

    except Exception as e:
        logger.exception("[MCP Skill Manager] Install exception")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def list_local_skills() -> dict[str, Any]:
    """
    获取本地已安装的 skills 列表

    Returns:
        {"success": bool, "skills": [...], "error": str|None}
    """
    logger.info("[MCP Skill Manager] Getting local skills list")

    try:
        skills = []

        # Scan builtin skills
        if SKILLS_DIR.exists():
            for skill_dir in SKILLS_DIR.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skill_name = skill_dir.name
                    skills.append({
                        "name": skill_name,
                        "path": str(skill_dir),
                        "source": "builtin",
                        "installed_at": None
                    })

        # Scan user installed skills
        if AGENT_SKILLS_DIR.exists():
            for skill_dir in AGENT_SKILLS_DIR.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skill_name = skill_dir.name
                    stat = skill_dir.stat()
                    skills.append({
                        "name": skill_name,
                        "path": str(skill_dir),
                        "source": "user_installed",
                        "installed_at": str(int(stat.st_mtime))
                    })

        logger.info(f"[MCP Skill Manager] Found {len(skills)} local skills")
        return {
            "success": True,
            "skills": skills,
            "error": None
        }

    except Exception as e:
        logger.exception("[MCP Skill Manager] Get local list exception")
        return {
            "success": False,
            "error": str(e),
            "skills": []
        }


@mcp.tool()
async def get_skill_info(skill_name: str) -> dict[str, Any]:
    """
    获取指定 skill 的详细信息

    Args:
        skill_name: Skill 名称

    Returns:
        {"success": bool, "info": {...}|None, "error": str|None}
    """
    logger.info(f"[MCP Skill Manager] Getting skill info: {skill_name}")

    try:
        if not skill_name:
            return {
                "success": False,
                "error": "skill_name 不能为空",
                "info": None
            }

        # Search in builtin and user directories
        for base_dir in [SKILLS_DIR, AGENT_SKILLS_DIR]:
            skill_path = base_dir / skill_name
            if skill_path.exists() and (skill_path / "SKILL.md").exists():
                skill_file = skill_path / "SKILL.md"
                content = skill_file.read_text(encoding='utf-8', errors='replace')

                # Parse frontmatter (simple implementation)
                info = {
                    "name": skill_name,
                    "path": str(skill_path),
                    "source": "builtin" if base_dir == SKILLS_DIR else "user_installed",
                    "description": "",
                    "content": content[:2000]  # 限制长度
                }

                # Try to extract description
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('---'):
                        info["description"] = line[:200]
                        break

                return {
                    "success": True,
                    "info": info,
                    "error": None
                }

        return {
            "success": False,
            "error": f"Skill '{skill_name}' 未找到",
            "info": None
        }

    except Exception as e:
        logger.exception("[MCP Skill Manager] Get info exception")
        return {
            "success": False,
            "error": str(e),
            "info": None
        }


async def main() -> None:
    """MCP Server entry point"""
    logger.info("[MCP Skill Manager] Server started")
    logger.info(f"[MCP Skill Manager] Project root: {PROJECT_ROOT}")
    logger.info(f"[MCP Skill Manager] Skills dir: {SKILLS_DIR}")
    logger.info(f"[MCP Skill Manager] Agent skills dir: {AGENT_SKILLS_DIR}")

    # Use FastMCP standard async run
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
