"""
模板渲染引擎工具类
支持变量替换、嵌套路径、默认值
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """统一的模板渲染引擎"""

    # 匹配 {{variable}} 或 {{nested.variable}} 或 {{var|default:"value"}} 或 {{}}
    # 改进的正则表达式，支持空变量名，更好地处理引号和嵌套情况
    VARIABLE_PATTERN = re.compile(r'\{\{\s*([^|}]*?)(?:\s*\|\s*default:\s*"((?:[^"\\]|\\.)*)")?\s*\}\}')

    @classmethod
    def render(cls, template: Any, context: Dict[str, Any], default_value: str = "") -> Any:
        """
        渲染模板，替换变量为实际值

        Args:
            template: 模板对象（可以是 str/dict/list）
            context: 变量上下文字典
            default_value: 全局默认值（当变量不存在且未指定默认值时使用）

        Returns:
            渲染后的对象
        """
        if isinstance(template, dict):
            return {k: cls.render(v, context, default_value) for k, v in template.items()}
        elif isinstance(template, list):
            return [cls.render(item, context, default_value) for item in template]
        elif isinstance(template, str):
            return cls._render_string(template, context, default_value)
        else:
            return template

    @classmethod
    def _render_string(cls, template_str: str, context: Dict[str, Any], default_value: str) -> str:
        """
        渲染字符串模板

        支持的格式：
        - {{var}}: 简单变量
        - {{obj.prop}}: 嵌套变量（支持多层）
        - {{var|default:"abc"}}: 带默认值
        """
        result = template_str

        # 查找所有变量匹配
        for match in cls.VARIABLE_PATTERN.finditer(template_str):
            full_match = match.group(0)  # 完整匹配如 {{user.name|default:"guest"}}
            var_path = match.group(1)  # 变量路径如 user.name（保留原始空格）
            var_default = match.group(2)  # 默认值（如果指定）

            # 处理转义的引号
            if var_default:
                var_default = var_default.replace('\\"', '"').replace("\\'", "'")

            # 获取变量值（查找时去除空格，但保留原始路径用于错误日志）
            value = cls._get_nested_value(context, var_path.strip())

            # 检查变量是否真的存在（而不是存在但为None）
            var_exists = cls._variable_exists(context, var_path.strip())

            # 处理变量值逻辑
            if not var_exists:
                # 变量不存在
                if var_default is not None:
                    # 有指定的默认值，使用它
                    value = var_default
                elif default_value:
                    # 没有指定默认值，使用全局默认值
                    value = default_value
                else:
                    # 没有任何默认值，保留原始模板不变
                    continue
            elif value == "" and var_default is not None:
                # 变量存在但为空字符串，且有默认值，使用默认值
                value = var_default
            elif value == "" and default_value:
                # 变量存在但为空字符串，且有全局默认值，使用全局默认值
                value = default_value
            elif not var_exists and var_default is None and not default_value:
                # 变量不存在且没有默认值，保留模板不变
                continue

            # 替换模板中的变量
            result = result.replace(full_match, str(value))

        return result

    @classmethod
    def _get_nested_value(cls, context: Dict[str, Any], path: str) -> Any:
        """
        从上下文中获取嵌套变量的值

        Args:
            context: 上下文字典
            path: 变量路径（如 "user.name" 或 "data.0.id"）

        Returns:
            变量值，不存在返回 None
        """
        # 处理空路径特殊情况
        if path == "":
            # 空路径直接返回空字符串对应的值
            return context.get("", None)

        if not context:
            return None

        parts = path.split('.')
        current = context

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                return None

        return current

    @classmethod
    def _variable_exists(cls, context: Dict[str, Any], path: str) -> bool:
        """
        检查变量是否存在于上下文中（而不是None）

        Args:
            context: 上下文字典
            path: 变量路径

        Returns:
            变量是否存在（True=存在，False=不存在）
        """
        if not path or not context:
            return False

        # 处理空路径特殊情况
        if path == "":
            return "" in context

        parts = path.split('.')
        current = context

        try:
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                    current = current[int(part)]
                else:
                    return False
        except (KeyError, IndexError, ValueError):
            return False

        return True
