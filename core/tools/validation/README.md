# Validation Tools / 验证工具模块

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述

验证工具模块提供 API 响应验证功能，支持：

- **状态码验证** - 验证 HTTP 状态码
- **响应时间验证** - 验证响应时间限制
- **JSON Schema 验证** - 验证响应结构
- **JSON Path 验证** - 验证特定字段值
- **正则表达式验证** - 模式匹配验证
- **内容包含验证** - 验证响应内容
- **响应头验证** - 验证 HTTP 响应头

## 文件结构

```
validation/
├── __init__.py
└── response_validator.py    # 响应验证器
```

## ResponseValidatorTool

### 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | `response_validator` |
| 描述 | Validate API responses against various rules and schemas |
| 版本 | 1.0.0 |

### 参数定义

```python
{
    "response_data": {
        "type": "object",
        "description": "Response data to validate",
        "properties": {
            "status_code": {"type": "integer"},
            "body": {"type": ["object", "string", "array", "null"]},
            "headers": {"type": "object"}
        },
        "required": ["status_code", "body"]
    },
    "validation_rules": {
        "type": "array",
        "description": "Validation rules to apply",
        "items": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["status_code", "response_time", "json_schema", 
                            "json_path", "regex", "contains", "header", "content_type"]
                },
                "value": {"type": ["string", "integer", "object", "array"]},
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "expected": {"type": ["string", "integer", "boolean", "object", "array"]},
                "operator": {
                    "type": "string",
                    "enum": ["equals", "not_equals", "contains", "not_contains", 
                            "greater_than", "less_than", "matches", "exists"],
                    "default": "equals"
                }
            },
            "required": ["type"]
        }
    },
    "strict_mode": {
        "type": "boolean",
        "description": "Whether to fail on first validation error",
        "default": False
    }
}
```

### 必填参数

- `response_data` - 要验证的响应数据
- `validation_rules` - 验证规则列表

### 返回数据结构

```python
{
    'overall_passed': True,
    'passed_count': 3,
    'total_count': 3,
    'validation_results': [
        {
            'rule': {'type': 'status_code', 'expected': 200},
            'passed': True,
            'message': 'Status code 200 equals expected 200',
            'actual': 200,
            'expected': 200
        }
    ],
    'response_summary': {
        'status_code': 200,
        'has_body': True
    }
}
```

## 使用示例

### 基本使用

```python
from core.tools.validation.response_validator import ResponseValidatorTool

validator = ResponseValidatorTool()

result = await validator.execute(
    response_data={
        'status_code': 200,
        'body': {'data': {'id': 1, 'name': 'Test'}},
        'headers': {'Content-Type': 'application/json'},
        'elapsed_time': 0.234
    },
    validation_rules=[
        {'type': 'status_code', 'expected': 200},
        {'type': 'response_time', 'value': 1.0}
    ]
)
```

### 严格模式

```python
# 遇到第一个失败就停止验证
result = await validator.execute(
    response_data=response_data,
    validation_rules=validation_rules,
    strict_mode=True
)
```

## 验证类型详解

### 1. 状态码验证 (status_code)

验证 HTTP 状态码：

```python
# 等于
{'type': 'status_code', 'expected': 200, 'operator': 'equals'}

# 不等于
{'type': 'status_code', 'expected': 500, 'operator': 'not_equals'}

# 大于
{'type': 'status_code', 'expected': 199, 'operator': 'greater_than'}

# 小于
{'type': 'status_code', 'expected': 400, 'operator': 'less_than'}
```

### 2. 响应时间验证 (response_time)

验证响应时间是否在限制内：

```python
{'type': 'response_time', 'value': 5.0}  # 最大 5 秒
```

### 3. JSON Schema 验证 (json_schema)

验证响应体是否符合 JSON Schema：

```python
{
    'type': 'json_schema',
    'value': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'}
        },
        'required': ['id', 'name']
    }
}
```

### 4. JSON Path 验证 (json_path)

验证响应体中特定字段的值：

```python
# 检查字段是否存在
{'type': 'json_path', 'path': '$.data.id', 'operator': 'exists'}

# 检查字段值相等
{'type': 'json_path', 'path': '$.data.name', 'expected': 'Test', 'operator': 'equals'}

# 检查字段值包含
{'type': 'json_path', 'path': '$.data.name', 'expected': 'es', 'operator': 'contains'}
```

### 5. 正则表达式验证 (regex)

使用正则表达式验证响应内容：

```python
{'type': 'regex', 'pattern': r'"id":\s*\d+'}
```

### 6. 内容包含验证 (contains)

验证响应内容是否包含特定文本：

```python
{'type': 'contains', 'expected': 'success'}
```

### 7. 响应头验证 (header)

验证响应头：

```python
# 检查头是否存在
{'type': 'header', 'value': 'X-Custom-Header', 'operator': 'exists'}

# 检查头值相等
{'type': 'header', 'value': 'Content-Type', 'expected': 'application/json', 'operator': 'equals'}

# 检查头值包含
{'type': 'header', 'value': 'Content-Type', 'expected': 'json', 'operator': 'contains'}
```

### 8. Content-Type 验证 (content_type)

验证 Content-Type 响应头：

```python
{'type': 'content_type', 'expected': 'application/json'}
```

## 比较操作符

| 操作符 | 适用类型 | 说明 |
|--------|----------|------|
| equals | 通用 | 等于 |
| not_equals | 通用 | 不等于 |
| contains | string, array | 包含 |
| not_contains | string, array | 不包含 |
| greater_than | number | 大于 |
| less_than | number | 小于 |
| matches | string | 正则匹配 |
| exists | 通用 | 存在 |

## 响应数据格式

验证器期望的响应数据格式：

```python
response_data = {
    'status_code': 200,           # 必填：HTTP 状态码
    'body': {...},                # 必填：响应体
    'headers': {...},             # 可选：响应头
    'elapsed_time': 0.234         # 可选：响应时间（秒）
}
```

## 验证结果示例

```python
{
    'overall_passed': True,
    'passed_count': 3,
    'total_count': 3,
    'validation_results': [
        {
            'rule': {'type': 'status_code', 'expected': 200},
            'passed': True,
            'message': 'Status code 200 equals expected 200',
            'actual': 200,
            'expected': 200
        },
        {
            'rule': {'type': 'response_time', 'value': 1.0},
            'passed': True,
            'message': 'Response time 0.234s is within limit of 1.0s',
            'actual': 0.234,
            'expected': 1.0
        },
        {
            'rule': {'type': 'json_path', 'path': '$.data.id', 'operator': 'exists'},
            'passed': True,
            'message': "JSON path '$.data.id' exists in response",
            'path': '$.data.id',
            'matches': [1]
        }
    ],
    'response_summary': {
        'status_code': 200,
        'has_body': True
    }
}
```

## 依赖

- `jsonschema` - JSON Schema 验证库
- `jsonpath-ng` - JSON Path 解析库
- `shared.exceptions` - ValidationError

---

<a name="english"></a>
## Overview

The Validation Tools module provides API response validation with support for:

- **Status Code Validation** - Validate HTTP status codes
- **Response Time Validation** - Validate response time limits
- **JSON Schema Validation** - Validate response structure
- **JSON Path Validation** - Validate specific field values
- **Regex Validation** - Pattern matching validation
- **Content Contains Validation** - Validate response content
- **Header Validation** - Validate HTTP response headers

## ResponseValidatorTool

Validates API responses against various rules and schemas.

### Validation Types

| Type | Description | Required Parameters |
|------|-------------|---------------------|
| status_code | HTTP status code validation | expected |
| response_time | Response time validation | value (max seconds) |
| json_schema | JSON Schema validation | value (schema) |
| json_path | JSON Path validation | path, expected, operator |
| regex | Regular expression validation | pattern |
| contains | Content contains validation | expected |
| header | Response header validation | value (header name), expected |
| content_type | Content-Type validation | expected |

### Comparison Operators

| Operator | Description |
|----------|-------------|
| equals | Equal to |
| not_equals | Not equal to |
| contains | Contains |
| not_contains | Does not contain |
| greater_than | Greater than |
| less_than | Less than |
| matches | Regex matches |
| exists | Exists |

### Strict Mode

When `strict_mode=True`, validation stops on first failure.

## Dependencies

- `jsonschema` - JSON Schema validation library
- `jsonpath-ng` - JSON Path parsing library
- `shared.exceptions` - ValidationError