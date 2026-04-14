#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
from __future__ import annotations

import os
import sys
import asyncio
from typing import List

# Windows上设置事件循环策略以支持Playwright（必须在导入Django之前）
# Windows上使用默认的ProactorEventLoopPolicy
# Playwright需要Proactor才能创建子进程
# 不要设置SelectorEventLoopPolicy！


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testmanager.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
