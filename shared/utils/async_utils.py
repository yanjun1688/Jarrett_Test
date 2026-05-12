"""
异步工具函数
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any, Dict, List, Optional, Union


async def async_run_command(
    command: Union[str, List[str]],
    timeout: float = 120.0,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False
) -> Dict[str, Any]:
    """
    异步执行命令（跨平台兼容）

    Uses asyncio.to_thread + subprocess.run to avoid event loop restrictions,
    suitable for Windows SelectorEventLoop environment.

    Args:
        command: command, can be string or list
        timeout: timeout in seconds, default 120
        cwd: working directory
        env: environment variables
        shell: whether to use shell
        capture_output: whether to capture output
        text: whether to return output as text
        check: whether to raise on non-zero return code

    Returns:
        dict with success, returncode, stdout, stderr, error keys
    """

    def _run_sync() -> Dict[str, Any]:
        run_env = env if env is not None else None

        if isinstance(command, list):
            cmd: Union[str, List[str]] = command
            use_shell = shell
        else:
            cmd = command
            use_shell = True

        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            encoding='utf-8' if text else None,
            errors='replace' if text else None,
            timeout=timeout,
            cwd=cwd,
            env=run_env,
            shell=use_shell,
            check=check
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout if result.stdout else "",
            "stderr": result.stderr if result.stderr else "",
            "error": result.stderr if result.returncode != 0 and result.stderr else None
        }

    try:
        return await asyncio.to_thread(_run_sync)
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "error": f"Command timed out ({timeout}s)"
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "error": f"Command not found: {e}"
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "returncode": e.returncode,
            "stdout": e.stdout if e.stdout else "",
            "stderr": e.stderr if e.stderr else "",
            "error": e.stderr if e.stderr else f"Command returned non-zero: {e.returncode}"
        }
