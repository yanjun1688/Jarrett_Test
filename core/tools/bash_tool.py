"""
Bash Tool — 执行 Shell 命令

提供给 LLM 的通用命令执行能力，用于运行测试、Git 操作、构建命令等。

平台适配：
- Windows: 使用 PowerShell (UTF-8 原生支持)
- Linux: 使用 sh -c

安全限制：
- 禁止删除文件（rm/del/Remove-Item 等）
- 修改文件需用户确认（confirmed=true 参数）
- 禁止使用 agent-browser CLI（应走 MCP Playwright）
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional

from core.tools.base_tool import BaseTool, ToolResult
from shared.utils.async_utils import async_run_command

import logging

logger = logging.getLogger(__name__)

# 禁止的命令前缀（匹配命令开头）
_FORBIDDEN_PREFIXES = ("agent-browser",)

# 文件删除禁止模式
_DELETION_PATTERN = re.compile(
    r'(?:^|\s|&&|\|\||;)(?:'
    r'del\b|erase\b|rd\b|rmdir\b'
    r'|rm\b(?!\s*-{1,2}version)'
    r'|Remove-Item\b|ri\b'
    r')',
    re.IGNORECASE,
)

# 文件修改需确认模式（排除 stderr 重定向到 null 设备的写法）
_MODIFICATION_PATTERN = re.compile(
    r'(?:'
    r'>>|>(?!\s*(?:&|/dev/null|NUL\b))'  # 排除 2>&1, 2>/dev/null, 2>NUL
    r'|\becho\b.*?>'
    r'|\b(?:Set-Content|Out-File|Add-Content)\b'
    r')',
    re.IGNORECASE,
)


class BashTool(BaseTool):
    name = "bash"
    description = "Execute shell commands. Use for test runs, git ops, build commands."

    def __init__(self, timeout: int = 120):
        super().__init__(name=self.name, description=self.description, timeout=timeout)

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "command": {"type": "string", "description": "Shell command to execute"},
            "cwd": {"type": "string", "description": "Working directory (optional)"},
            "confirmed": {
                "type": "boolean",
                "description": "用户已确认执行该操作（修改文件时需要设为 true）",
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ["command"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        command: str = kwargs["command"].strip()
        cwd: Optional[str] = kwargs.get("cwd")
        confirmed: bool = kwargs.get("confirmed", False)

        # 1. 禁止前缀检查
        for prefix in _FORBIDDEN_PREFIXES:
            if command.startswith(prefix):
                return ToolResult(
                    success=False,
                    data={},
                    error=f"禁止使用 bash + {prefix}，请使用对应的 mcp__playwright__* 工具",
                )

        # 2. 文件删除禁止
        if _DELETION_PATTERN.search(command):
            return ToolResult(
                success=False,
                data={},
                error="禁止删除文件。如需删除文件请告知用户，由用户确认后通过其他方式处理。",
            )

        # 3. 文件修改需确认
        if _MODIFICATION_PATTERN.search(command) and not confirmed:
            return ToolResult(
                success=False,
                data={},
                error="修改文件需要用户确认。请先询问用户是否允许，获得确认后请设置 confirmed=true 重新执行。",
            )

        # 4. 执行 — Windows 用 PowerShell (UTF-8), Linux 用 sh
        if sys.platform == 'win32':
            cmd_args = ['powershell', '-NoProfile', '-Command', command]
        else:
            cmd_args = ['sh', '-c', command]

        # 注入 Python 编码环境变量，确保 Python 子进程输出 UTF-8
        encoding_env = os.environ.copy()
        encoding_env.setdefault('PYTHONIOENCODING', 'utf-8')
        encoding_env.setdefault('PYTHONUTF8', '1')

        result = await async_run_command(cmd_args, timeout=self.timeout, cwd=cwd, env=encoding_env)
        return ToolResult(
            success=result["success"],
            data={
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "returncode": result.get("returncode"),
            },
            error=result.get("error"),
        )
