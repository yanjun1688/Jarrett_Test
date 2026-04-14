"""
字符串工具
提供跨模块使用的字符串处理功能
"""

from __future__ import annotations

import re
import hashlib
import json
from typing import Any, Dict, List, Union


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断字符串
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        str: 截断后的字符串
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_json_parse(json_str: str, default: Any = None) -> Any:
    """
    安全解析JSON字符串
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        Any: 解析结果或默认值
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_stringify(data: Any, default: str = "") -> str:
    """
    安全序列化为JSON字符串
    
    Args:
        data: 要序列化的数据
        default: 序列化失败时的默认值
        
    Returns:
        str: JSON字符串或默认值
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


def generate_hash(text: str, algorithm: str = "md5") -> str:
    """
    生成字符串哈希
    
    Args:
        text: 原始文本
        algorithm: 哈希算法（md5, sha1, sha256）
        
    Returns:
        str: 哈希值
    """
    hash_func = getattr(hashlib, algorithm, hashlib.md5)
    return hash_func(text.encode()).hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    # 移除非法字符
    sanitized = re.sub(r'[<>:"/\|?*]', '_', filename)
    # 移除连续的下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    # 移除首尾空格和下划线
    sanitized = sanitized.strip(' _')
    
    return sanitized if sanitized else "unnamed_file"


def extract_emails(text: str) -> List[str]:
    """
    从文本中提取邮箱地址
    
    Args:
        text: 原始文本
        
    Returns:
        list: 邮箱地址列表
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)


def extract_urls(text: str) -> List[str]:
    """
    从文本中提取URL
    
    Args:
        text: 原始文本
        
    Returns:
        list: URL列表
    """
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.findall(url_pattern, text)


def camel_to_snake(camel_str: str) -> str:
    """
    驼峰命名转蛇形命名
    
    Args:
        camel_str: 驼峰命名字符串
        
    Returns:
        str: 蛇形命名字符串
    """
    # 插入下划线并在大写字母前添加下划线
    snake_str = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str)
    # 转换为小写
    return snake_str.lower()


def snake_to_camel(snake_str: str) -> str:
    """
    蛇形命名转驼峰命名
    
    Args:
        snake_str: 蛇形命名字符串
        
    Returns:
        str: 驼峰命名字符串
    """
    components = snake_str.split('_')
    # 将每个部分的首字母大写（除了第一个部分）
    return components[0] + ''.join(x.title() for x in components[1:])
