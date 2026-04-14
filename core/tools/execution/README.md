# Execution Tools / 执行工具模块

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述

执行工具模块提供 API 测试编排功能，将 HTTP 客户端和响应验证工具组合使用，支持：

- **HTTP 请求执行** - 发送 HTTP 请求并获取响应
- **响应验证** - 根据验证规则检查响应
- **变量提取** - 从响应中提取变量用于后续测试
- **多端点测试** - 支持串行和并行测试执行

## 文件结构

```
execution/
├── __init__.py
└── api_test_orchestrator.py    # API 测试编排器
```

## APITestOrchestratorTool

### 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | `api_test_orchestrator` |
| 描述 | Orchestrates API testing by combining HTTP requests and validation |
| 版本 | 1.0.0 |
| 超时 | 120 秒 |

### 组合工具

该编排器内部组合了两个工具：

1. **HTTPClientTool** - 执行 HTTP 请求
2. **ResponseValidatorTool** - 验证响应

### 参数定义

```python
{
    "url": {
        "type": "string",
        "description": "API endpoint URL"
    },
    "method": {
        "type": "string",
        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        "description": "HTTP method",
        "default": "GET"
    },
    "headers": {
        "type": "object",
        "description": "Request headers"
    },
    "body": {
        "type": ["object", "string", "null"],
        "description": "Request body"
    },
    "params": {
        "type": "object",
        "description": "Query parameters"
    },
    "expected_status": {
        "type": "integer",
        "description": "Expected HTTP status code"
    },
    "validation_rules": {
        "type": "array",
        "description": "Validation rules"
    },
    "timeout": {
        "type": "integer",
        "description": "Request timeout in seconds",
        "default": 30
    },
    "follow_redirects": {
        "type": "boolean",
        "default": True
    },
    "verify_ssl": {
        "type": "boolean",
        "default": True
    },
    "extract_variables": {
        "type": "object",
        "description": "Variables to extract from response"
    },
    "strict_validation": {
        "type": "boolean",
        "description": "Fail on first validation error",
        "default": False
    }
}
```

### 必填参数

- `url` - API 端点 URL
- `method` - HTTP 方法

### 返回数据结构

```python
{
    'http_response': {
        'url': 'https://api.example.com/users',
        'method': 'GET',
        'status_code': 200,
        'headers': {...},
        'body': {...},
        'elapsed_time': 0.234
    },
    'validation_result': {
        'overall_passed': True,
        'passed_count': 2,
        'total_count': 2,
        'validation_results': [...]
    },
    'extracted_variables': {
        'user_id': 123,
        'token': 'abc123'
    },
    'test_passed': True,
    'metadata': {
        'url': '...',
        'method': 'GET',
        'response_time': 0.234,
        'status_code': 200
    }
}
```

## 使用示例

### 基本使用

```python
from core.tools.execution.api_test_orchestrator import APITestOrchestratorTool

orchestrator = APITestOrchestratorTool()

result = await orchestrator.execute(
    url="https://api.example.com/users",
    method="GET",
    expected_status=200
)
```

### 带验证规则的测试

```python
result = await orchestrator.execute(
    url="https://api.example.com/users",
    method="GET",
    validation_rules=[
        {"type": "status_code", "expected": 200},
        {"type": "response_time", "value": 2.0},
        {"type": "json_path", "path": "$.data", "operator": "exists"}
    ]
)
```

### 提取变量

```python
result = await orchestrator.execute(
    url="https://api.example.com/login",
    method="POST",
    body={"username": "admin", "password": "password"},
    extract_variables={
        "token": "$.access_token",
        "user_id": "$.user.id"
    }
)

# 后续测试可使用提取的变量
token = result.data['extracted_variables']['token']
```

### 简单测试

```python
result = await orchestrator.execute_simple_test(
    url="https://api.example.com/health",
    method="GET",
    expected_status=200,
    max_response_time=5.0
)
```

### 多端点测试

```python
endpoints = [
    {"url": "https://api.example.com/users", "method": "GET"},
    {"url": "https://api.example.com/products", "method": "GET"},
    {"url": "https://api.example.com/orders", "method": "GET"}
]

# 串行执行
results = await orchestrator.test_multiple_endpoints(
    endpoints=endpoints,
    parallel=False
)

# 并行执行（最大并发数 5）
results = await orchestrator.test_multiple_endpoints(
    endpoints=endpoints,
    parallel=True,
    max_concurrent=5
)
```

## 验证规则类型

| 类型 | 说明 | 必需参数 |
|------|------|----------|
| status_code | 验证状态码 | expected |
| response_time | 验证响应时间 | value (最大秒数) |
| json_schema | JSON Schema 验证 | value (schema) |
| json_path | JSON Path 验证 | path, expected, operator |
| regex | 正则表达式验证 | pattern |
| contains | 内容包含验证 | expected |
| header | 响应头验证 | value (header名), expected |
| content_type | Content-Type 验证 | expected |

## 比较操作符

| 操作符 | 说明 |
|--------|------|
| equals | 等于 |
| not_equals | 不等于 |
| contains | 包含 |
| not_contains | 不包含 |
| greater_than | 大于 |
| less_than | 小于 |
| matches | 正则匹配 |
| exists | 存在 |

## 变量提取

使用 JSON Path 从响应中提取变量：

```python
extract_variables = {
    "variable_name": "$.path.to.field"
}
```

**示例响应：**
```json
{
    "data": {
        "user": {
            "id": 123,
            "name": "John"
        }
    },
    "token": "abc123"
}
```

**提取配置：**
```python
extract_variables = {
    "user_id": "$.data.user.id",      # 提取: 123
    "token": "$.token"                 # 提取: "abc123"
}
```

## 依赖

- `httpx` - HTTP 客户端
- `jsonpath-ng` - JSON Path 解析
- `core.tools.api.http_client` - HTTP 客户端工具
- `core.tools.validation.response_validator` - 响应验证工具

---

<a name="english"></a>
## Overview

The Execution Tools module provides API test orchestration functionality, combining HTTP client and response validation tools with support for:

- **HTTP Request Execution** - Send HTTP requests and get responses
- **Response Validation** - Check responses against validation rules
- **Variable Extraction** - Extract variables from responses for subsequent tests
- **Multi-endpoint Testing** - Support for sequential and parallel test execution

## APITestOrchestratorTool

Combines HTTPClientTool and ResponseValidatorTool to provide complete API testing workflow.

### Key Features

- Execute HTTP requests with full parameter support
- Validate responses against multiple rule types
- Extract variables using JSON Path expressions
- Run tests on multiple endpoints (sequential or parallel)

### Validation Rule Types

- `status_code` - HTTP status code validation
- `response_time` - Response time validation
- `json_schema` - JSON Schema validation
- `json_path` - JSON Path expression validation
- `regex` - Regular expression validation
- `contains` - Content contains validation
- `header` - Response header validation
- `content_type` - Content-Type header validation

### Comparison Operators

- `equals`, `not_equals`, `contains`, `not_contains`
- `greater_than`, `less_than`
- `matches`, `exists`

## Dependencies

- `httpx` - HTTP client library
- `jsonpath-ng` - JSON Path parsing
- `core.tools.api.http_client` - HTTP client tool
- `core.tools.validation.response_validator` - Response validator tool