# API Tools / API 工具模块

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述

API 工具模块提供 HTTP 客户端功能，用于发起各种 HTTP 请求，支持：

- 多种 HTTP 方法（GET, POST, PUT, DELETE, PATCH 等）
- 自定义请求头和请求体
- 查询参数
- SSL 验证控制
- 重定向跟随
- 超时设置

## 文件结构

```
api/
├── __init__.py
└── http_client.py    # HTTP 客户端工具
```

## HTTPClientTool

### 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | `http_client` |
| 描述 | HTTP client for making API requests with support for various methods and authentication |
| 版本 | 1.0.0 |
| 默认超时 | 60 秒 |

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
        "description": "Request headers",
        "additionalProperties": {"type": "string"}
    },
    "body": {
        "type": ["object", "string", "null"],
        "description": "Request body (JSON, form data, etc.)"
    },
    "params": {
        "type": "object",
        "description": "Query parameters",
        "additionalProperties": {"type": "string"}
    },
    "timeout": {
        "type": "integer",
        "description": "Request timeout in seconds",
        "default": 30
    },
    "follow_redirects": {
        "type": "boolean",
        "description": "Whether to follow redirects",
        "default": True
    },
    "verify_ssl": {
        "type": "boolean",
        "description": "Whether to verify SSL certificates",
        "default": True
    }
}
```

### 必填参数

- `url` - API 端点 URL
- `method` - HTTP 方法

### 返回数据结构

```python
{
    'url': '请求的 URL',
    'method': 'HTTP 方法',
    'status_code': 200,
    'headers': {'Content-Type': 'application/json', ...},
    'body': {'key': 'value'},  # 自动解析 JSON
    'elapsed_time': 0.234,
    'request_info': {
        'headers': {...},
        'params': {...}
    }
}
```

## 使用示例

### 基本使用

```python
from core.tools.api.http_client import HTTPClientTool

client = HTTPClientTool()

# GET 请求
result = await client.execute(
    url="https://api.example.com/users",
    method="GET"
)

# POST 请求
result = await client.execute(
    url="https://api.example.com/users",
    method="POST",
    headers={"Authorization": "Bearer token"},
    body={"name": "John", "email": "john@example.com"}
)
```

### 便捷方法

```python
# GET 请求
result = await client.get("https://api.example.com/users")

# POST 请求
result = await client.post(
    "https://api.example.com/users",
    body={"name": "John"}
)

# PUT 请求
result = await client.put(
    "https://api.example.com/users/1",
    body={"name": "John Updated"}
)

# DELETE 请求
result = await client.delete("https://api.example.com/users/1")

# PATCH 请求
result = await client.patch(
    "https://api.example.com/users/1",
    body={"name": "John"}
)
```

### 带查询参数

```python
result = await client.execute(
    url="https://api.example.com/users",
    method="GET",
    params={"page": 1, "limit": 10}
)
```

### 自定义超时和 SSL

```python
result = await client.execute(
    url="https://api.example.com/users",
    method="GET",
    timeout=120,
    verify_ssl=False,
    follow_redirects=True
)
```

## 核心功能

### 请求准备

- 自动合并默认请求头
- JSON 请求体自动序列化
- 表单数据支持

### 响应解析

- JSON 响应自动解析
- 文本响应直接返回
- 二进制内容解码处理

### 错误处理

- 超时异常处理
- 请求错误处理
- 通用异常捕获

## 默认配置

```python
default_timeout = 60
default_headers = {
    'User-Agent': 'TestAutomation/1.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}
```

## 依赖

- `httpx` - 现代 HTTP 客户端库
- `shared.exceptions` - RequestError, ValidationError
- `shared.utils.validation` - URL 验证

---

<a name="english"></a>
## Overview

The API Tools module provides HTTP client functionality for making various HTTP requests with support for:

- Multiple HTTP methods (GET, POST, PUT, DELETE, PATCH, etc.)
- Custom headers and request body
- Query parameters
- SSL verification control
- Redirect following
- Timeout settings

## HTTPClientTool

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | API endpoint URL |
| method | string | Yes | HTTP method |
| headers | object | No | Request headers |
| body | object/string | No | Request body |
| params | object | No | Query parameters |
| timeout | integer | No | Timeout in seconds (default: 30) |
| follow_redirects | boolean | No | Follow redirects (default: true) |
| verify_ssl | boolean | No | Verify SSL (default: true) |

### Convenience Methods

- `get(url, **kwargs)` - GET request
- `post(url, body=None, **kwargs)` - POST request
- `put(url, body=None, **kwargs)` - PUT request
- `delete(url, **kwargs)` - DELETE request
- `patch(url, body=None, **kwargs)` - PATCH request

## Dependencies

- `httpx` - Modern HTTP client library
- `shared.exceptions` - RequestError, ValidationError
- `shared.utils.validation` - URL validation