# Generation Tools / 生成工具模块

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述
---暂未开发,预计遗弃。

生成工具模块提供从 API 规范自动生成测试用例的功能，支持：

- **OpenAPI/Swagger 规范解析** - 解析 API 规范文档
- **正向测试用例生成** - 生成正常场景测试用例
- **负向测试用例生成** - 生成异常场景测试用例
- **边界测试用例生成** - 生成边界值测试用例
- **测试数据自动生成** - 使用 Faker 生成测试数据

## 文件结构

```
generation/
├── __init__.py
└── test_case_generator.py    # 测试用例生成器
```

## TestCaseGeneratorTool

### 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | `test_case_generator` |
| 描述 | Generate test cases from API specifications (OpenAPI/Swagger) |
| 版本 | 1.0.0 |

### 参数定义

```python
{
    "api_spec": {
        "type": "object",
        "description": "API specification (OpenAPI/Swagger format)"
    },
    "base_url": {
        "type": "string",
        "description": "Base URL for API endpoints",
        "default": ""
    },
    "test_types": {
        "type": "array",
        "description": "Types of tests to generate",
        "items": {
            "type": "string",
            "enum": ["positive", "negative", "boundary", "security", "performance"]
        },
        "default": ["positive", "negative"]
    },
    "max_cases_per_endpoint": {
        "type": "integer",
        "description": "Maximum test cases per endpoint",
        "default": 5
    },
    "include_validation_rules": {
        "type": "boolean",
        "description": "Whether to include validation rules in test cases",
        "default": True
    }
}
```

### 必填参数

- `api_spec` - API 规范（OpenAPI/Swagger 格式的字典）

### 返回数据结构

```python
{
    'test_cases': [
        {
            'name': 'GET /api/users - Positive Test',
            'description': 'Positive test for GET /api/users',
            'endpoint': '/api/users',
            'method': 'GET',
            'url': 'https://api.example.com/api/users',
            'test_type': 'positive',
            'priority': 'high',
            'steps': [
                'Send GET request to https://api.example.com/api/users',
                'Verify response status code',
                'Verify response structure if applicable'
            ],
            'expected_result': 'Response status code should be 200',
            'request_data': {},
            'validation_rules': [
                {'type': 'status_code', 'expected': 200},
                {'type': 'response_time', 'value': 5.0}
            ],
            'expected_status': 200
        }
    ],
    'summary': {
        'total_cases': 10,
        'endpoints_covered': 3,
        'test_types': ['positive', 'negative']
    },
    'api_info': {
        'title': 'Sample API',
        'version': '1.0.0',
        'endpoint_count': 3
    }
}
```

## 使用示例

### 从 OpenAPI 规范生成测试用例

```python
from core.tools.generation.test_case_generator import TestCaseGeneratorTool
import json

generator = TestCaseGeneratorTool()

# 加载 OpenAPI 规范
with open('api_spec.json') as f:
    api_spec = json.load(f)

# 生成测试用例
result = await generator.execute(
    api_spec=api_spec,
    base_url="https://api.example.com",
    test_types=["positive", "negative", "boundary"],
    max_cases_per_endpoint=5,
    include_validation_rules=True
)

# 获取生成的测试用例
test_cases = result.data['test_cases']
for tc in test_cases:
    print(f"Test: {tc['name']}")
    print(f"  Type: {tc['test_type']}")
    print(f"  Endpoint: {tc['method']} {tc['endpoint']}")
```

### 只生成正向测试用例

```python
result = await generator.execute(
    api_spec=api_spec,
    base_url="https://api.example.com",
    test_types=["positive"]
)
```

### 限制每个端点的测试用例数量

```python
result = await generator.execute(
    api_spec=api_spec,
    max_cases_per_endpoint=3
)
```

## 测试类型说明

### 正向测试 (positive)

测试正常场景，使用有效数据验证 API 功能：

- 正确的请求参数
- 预期的状态码
- 有效的响应结构

### 负向测试 (negative)

测试异常场景，验证 API 错误处理：

| 场景 | 说明 |
|------|------|
| Missing Required Fields | 缺少必填字段 |
| Invalid Data Types | 无效的数据类型 |
| Out of Range Values | 超出范围的值 |
| Malformed Data | 格式错误的数据 |

### 边界测试 (boundary)

测试边界值，验证边界条件处理：

- 最小/最大值
- 字符串长度限制
- 数组大小限制

## 测试数据生成

使用 Faker 库根据 JSON Schema 自动生成测试数据：

### 支持的数据类型

| JSON Schema 类型 | 生成的数据 |
|-----------------|-----------|
| string | 随机字符串 |
| string (format: email) | 随机邮箱 |
| string (format: date-time) | ISO 日期时间 |
| string (enum) | 枚举值之一 |
| integer | 随机整数 |
| number | 随机浮点数 |
| boolean | 随机布尔值 |
| array | 随机数组 |
| object | 递归生成对象 |

### 示例：根据 Schema 生成数据

```python
# JSON Schema
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "age": {"type": "integer", "minimum": 0, "maximum": 120}
    }
}

# 自动生成的数据示例
{
    "name": "random_string",
    "email": "user@example.com",
    "age": 25
}
```

## 验证规则生成

根据 API 规范自动生成验证规则：

```python
validation_rules = [
    {'type': 'status_code', 'expected': 200},
    {'type': 'response_time', 'value': 5.0}
]
```

## 预期状态码

根据 HTTP 方法自动设置预期状态码：

| 方法 | 默认预期状态码 |
|------|--------------|
| GET | 200 |
| POST | 201 |
| PUT | 200 |
| DELETE | 204 |
| PATCH | 200 |
| HEAD | 200 |
| OPTIONS | 200 |

## 依赖

- `faker` - 测试数据生成库
- `shared.exceptions` - ValidationError

---

<a name="english"></a>
## Overview

The Generation Tools module provides automatic test case generation from API specifications with support for:

- **OpenAPI/Swagger Parsing** - Parse API specification documents
- **Positive Test Generation** - Generate happy path test cases
- **Negative Test Generation** - Generate error scenario test cases
- **Boundary Test Generation** - Generate boundary value test cases
- **Test Data Generation** - Auto-generate test data using Faker

## TestCaseGeneratorTool

Generates test cases from OpenAPI/Swagger specifications.

### Test Types

| Type | Description |
|------|-------------|
| positive | Happy path tests with valid data |
| negative | Error scenario tests |
| boundary | Boundary value tests |
| security | Security-related tests (planned) |
| performance | Performance tests (planned) |

### Negative Test Scenarios

- Missing Required Fields
- Invalid Data Types
- Out of Range Values
- Malformed Data

### Test Data Generation

Uses Faker library to auto-generate test data based on JSON Schema:

- string, integer, number, boolean
- Email, date-time formats
- Enum values
- Arrays and nested objects

### Expected Status Codes

Automatically sets expected status codes based on HTTP method:
- GET: 200, POST: 201, PUT: 200, DELETE: 204, PATCH: 200

## Dependencies

- `faker` - Test data generation library
- `shared.exceptions` - ValidationError