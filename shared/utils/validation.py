"""
验证工具函数
"""

from __future__ import annotations

import re
import json
from typing import Dict, Any, List, Optional, Union, Callable

import jsonschema
from ..exceptions import ValidationError




def validate_json_schema(data: Union[Dict[str, Any], List[Any]], schema: Dict[str, Any]) -> List[str]:
    """验证JSON数据是否符合schema
    
    Args:
        data: 要验证的数据
        schema: JSON Schema
        
    Returns:
        错误消息列表，空列表表示验证通过
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
        return []
    except jsonschema.ValidationError as e:
        return [str(e)]
    except jsonschema.SchemaError as e:
        return [f"Schema错误: {str(e)}"]


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """验证必需字段是否存在
    
    Args:
        data: 数据字典
        required_fields: 必需字段列表
        
    Returns:
        缺失字段列表，空列表表示所有字段都存在
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    return missing_fields


def validate_url(url: str) -> bool:
    """验证URL格式"""
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return bool(re.match(pattern, url))


def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None) -> bool:
    """验证整数"""
    try:
        int_value = int(value)
        if min_value is not None and int_value < min_value:
            return False
        if max_value is not None and int_value > max_value:
            return False
        return True
    except (ValueError, TypeError):
        return False


def validate_float(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> bool:
    """验证浮点数"""
    try:
        float_value = float(value)
        if min_value is not None and float_value < min_value:
            return False
        if max_value is not None and float_value > max_value:
            return False
        return True
    except (ValueError, TypeError):
        return False


def validate_string(value: Any, min_length: Optional[int] = None, max_length: Optional[int] = None) -> bool:
    """验证字符串"""
    if not isinstance(value, str):
        return False
    
    length = len(value)
    if min_length is not None and length < min_length:
        return False
    if max_length is not None and length > max_length:
        return False
    return True


def validate_enum(value: Any, allowed_values: List[Any]) -> bool:
    """验证枚举值"""
    return value in allowed_values


def validate_datetime_format(datetime_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> bool:
    """验证日期时间格式"""
    try:
        from datetime import datetime
        datetime.strptime(datetime_str, format)
        return True
    except ValueError:
        return False


def validate_and_raise(data: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> None:
    """验证数据并根据规则抛出异常
    
    Args:
        data: 要验证的数据
        rules: 验证规则字典
            {
                "field_name": {
                    "required": bool,
                    "type": str,  # "string", "integer", "float", "boolean", "array", "object"
                    "min": int/float,
                    "max": int/float,
                    "min_length": int,
                    "max_length": int,
                    "pattern": str,  # 正则表达式
                    "enum": list,  # 允许的值列表
                    "schema": dict,  # JSON Schema
                    "custom": callable  # 自定义验证函数
                }
            }
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    errors = []
    
    for field, rule in rules.items():
        value = data.get(field)
        
        # 检查必需字段
        if rule.get("required", False) and (value is None or (isinstance(value, str) and not value.strip())):
            errors.append(f"字段 '{field}' 是必需的")
            continue
        
        # 如果字段不是必需的且值为None，跳过其他验证
        if value is None:
            continue
        
        # 类型验证
        expected_type = rule.get("type")
        if expected_type:
            type_valid = False
            if expected_type == "string":
                type_valid = isinstance(value, str)
            elif expected_type == "integer":
                type_valid = isinstance(value, int) and not isinstance(value, bool)
            elif expected_type == "float":
                type_valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif expected_type == "boolean":
                type_valid = isinstance(value, bool)
            elif expected_type == "array":
                type_valid = isinstance(value, list)
            elif expected_type == "object":
                type_valid = isinstance(value, dict)
            
            if not type_valid:
                errors.append(f"字段 '{field}' 必须是 {expected_type} 类型")
                continue
        
        # 数值范围验证
        if isinstance(value, (int, float)):
            min_val = rule.get("min")
            max_val = rule.get("max")
            if min_val is not None and value < min_val:
                errors.append(f"字段 '{field}' 不能小于 {min_val}")
            if max_val is not None and value > max_val:
                errors.append(f"字段 '{field}' 不能大于 {max_val}")
        
        # 字符串长度验证
        if isinstance(value, str):
            min_len = rule.get("min_length")
            max_len = rule.get("max_length")
            if min_len is not None and len(value) < min_len:
                errors.append(f"字段 '{field}' 长度不能小于 {min_len}")
            if max_len is not None and len(value) > max_len:
                errors.append(f"字段 '{field}' 长度不能大于 {max_len}")
            
            # 正则表达式验证
            pattern = rule.get("pattern")
            if pattern and not re.match(pattern, value):
                errors.append(f"字段 '{field}' 格式无效")
        
        # 枚举值验证
        enum_values = rule.get("enum")
        if enum_values and value not in enum_values:
            errors.append(f"字段 '{field}' 必须是以下值之一: {', '.join(map(str, enum_values))}")
        
        # JSON Schema验证
        schema = rule.get("schema")
        if schema and isinstance(value, (dict, list)):
            schema_errors = validate_json_schema(value, schema)
            errors.extend([f"字段 '{field}': {err}" for err in schema_errors])
        
        # 自定义验证函数
        custom_validator = rule.get("custom")
        if custom_validator:
            try:
                if not custom_validator(value):
                    errors.append(f"字段 '{field}' 自定义验证失败")
            except Exception as e:
                errors.append(f"字段 '{field}' 自定义验证错误: {str(e)}")
    
    if errors:
        raise ValidationError("验证失败", details={"errors": errors})


def validate_flow_ir(flow_ir_data: Dict[str, Any]) -> None:
    """验证FlowIR数据结构
    
    Args:
        flow_ir_data: FlowIR数据字典
        
    Raises:
        ValidationError: 如果FlowIR无效
    """
    if not isinstance(flow_ir_data, dict):
        raise ValidationError("FlowIR必须是字典类型")
    
    # 检查必需字段
    required_fields = ['nodes', 'edges', 'metadata']
    missing_fields = validate_required_fields(flow_ir_data, required_fields)
    if missing_fields:
        raise ValidationError(f"FlowIR缺少必需字段: {', '.join(missing_fields)}")
    
    # 验证nodes
    nodes = flow_ir_data.get('nodes', {})
    if not isinstance(nodes, dict):
        raise ValidationError("nodes必须是字典类型")
    
    for node_id, node_data in nodes.items():
        if not isinstance(node_data, dict):
            raise ValidationError(f"节点 {node_id} 必须是字典类型")
        
        # 检查节点必需字段
        node_required = ['type', 'config']
        node_missing = validate_required_fields(node_data, node_required)
        if node_missing:
            raise ValidationError(f"节点 {node_id} 缺少字段: {', '.join(node_missing)}")
    
    # 验证edges
    edges = flow_ir_data.get('edges', [])
    if not isinstance(edges, list):
        raise ValidationError("edges必须是列表类型")
    
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValidationError("边必须是字典类型")
        
        edge_required = ['source', 'target']
        edge_missing = validate_required_fields(edge, edge_required)
        if edge_missing:
            raise ValidationError(f"边缺少字段: {', '.join(edge_missing)}")
    
    # 验证metadata
    metadata = flow_ir_data.get('metadata', {})
    if not isinstance(metadata, dict):
        raise ValidationError("metadata必须是字典类型")


def validate_page_structure(elements: List[Dict[str, Any]]) -> None:
    """验证页面结构元素
    
    Args:
        elements: 页面元素列表
        
    Raises:
        ValidationError: 如果页面结构无效
    """
    if not isinstance(elements, list):
        raise ValidationError("elements必须是列表类型")
    
    if not elements:
        raise ValidationError("页面元素不能为空")
    
    for i, element in enumerate(elements):
        if not isinstance(element, dict):
            raise ValidationError(f"元素 {i} 必须是字典类型")
        
        # 检查必需字段
        required_fields = ['type', 'tag']
        missing_fields = validate_required_fields(element, required_fields)
        if missing_fields:
            raise ValidationError(f"元素 {i} 缺少字段: {', '.join(missing_fields)}")
        
        # 验证类型
        element_type = element.get('type')
        if element_type not in ['input', 'button', 'link', 'select', 'checkbox', 'radio', 'text', 'image', 'container', 'unknown']:
            raise ValidationError(f"元素 {i} 类型无效: {element_type}")
        
        # 验证attributes（如果存在）
        attributes = element.get('attributes')
        if attributes is not None and not isinstance(attributes, dict):
            raise ValidationError(f"元素 {i} 的attributes必须是字典类型")
        
        # 验证selector_hints（如果存在）
        selector_hints = element.get('selector_hints')
        if selector_hints is not None:
            if not isinstance(selector_hints, list):
                raise ValidationError(f"元素 {i} 的selector_hints必须是列表类型")
            for hint in selector_hints:
                if not isinstance(hint, str):
                    raise ValidationError(f"元素 {i} 的selector_hints必须包含字符串")