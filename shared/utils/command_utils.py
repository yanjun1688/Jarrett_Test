"""
命令行工具检测工具
提供跨平台的命令行工具检测功能
"""

from __future__ import annotations

import shutil
import platform
from typing import Optional


def get_npx_command() -> Optional[str]:
    """
    获取npx命令路径，支持Windows和Linux
    
    在Windows上，npx实际上是npx.cmd
    在Linux/Mac上，直接使用npx
    
    Returns:
        npx命令的完整路径，如果找不到则返回None
    """
    if platform.system() == 'Windows':
        npx_cmd = shutil.which('npx.cmd') or shutil.which('npx')
    else:
        npx_cmd = shutil.which('npx')
    
    return npx_cmd


def check_command_available(command: str) -> bool:
    """
    检查命令是否可用
    
    Args:
        command: 命令名称
        
    Returns:
        命令是否可用
    """
    return shutil.which(command) is not None