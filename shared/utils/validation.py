"""
验证工具函数
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Union

import jsonschema


def validate_json_schema(data: Union[Dict[str, Any], List[Any]], schema: Dict[str, Any]) -> List[str]:
    """验证JSON数据是否符合schema"""
    try:
        jsonschema.validate(instance=data, schema=schema)
        return []
    except jsonschema.ValidationError as e:
        return [str(e)]
    except jsonschema.SchemaError as e:
        return [f"Schema错误: {str(e)}"]


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """验证必需字段是否存在"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    return missing_fields


def validate_url(url: str) -> bool:
    """验证URL格式"""
    import re
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return bool(re.match(pattern, url))
