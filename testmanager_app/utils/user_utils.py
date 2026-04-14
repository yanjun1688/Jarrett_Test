"""
用户相关工具函数
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User

logger = logging.getLogger(__name__)