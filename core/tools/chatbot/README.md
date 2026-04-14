# Chatbot Tools / 聊天机器人工具模块

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述

聊天机器人工具模块提供与聊天机器人交互的工具集，支持：

- **API 测试生成** - 根据用户描述生成 API 测试用例
- **UI 测试生成** - 根据用户描述生成 UI 自动化测试脚本
- **测试执行** - 执行已生成或已保存的测试用例
- **知识库查询** - 查询测试最佳实践和示例代码
- **Skill 管理** - 安装和运行 Skill

## 文件结构

```
chatbot/
├── __init__.py
├── generate_api_test_tool.py      # API 测试生成工具
├── generate_ui_test_tool.py       # UI 测试生成工具
├── execute_test_tool.py           # 测试执行工具
├── execute_pending_tests_tool.py  # 待执行测试工具
├── query_knowledge_tool.py        # 知识库查询工具
├── install_skill_tool.py          # Skill 安装工具
└── run_skill_tool.py              # Skill 运行工具
```

## 工具列表

### 1. GenerateAPITestTool - API 测试生成工具

| 属性 | 值 |
|------|-----|
| 名称 | `generate_api_test` |
| 描述 | 生成 API/接口测试脚本。当用户需要测试 REST API、HTTP 接口时调用。 |
| 版本 | 1.0.0 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| endpoint | string | 是 | API 端点路径，如 /api/login |
| method | string | 是 | HTTP 方法 (GET, POST, PUT, DELETE, PATCH) |
| description | string | 否 | 测试场景描述 |

#### 返回数据

```python
{
    "test_cases": [
        {
            "name": "测试用例名称",
            "description": "测试用例描述",
            "endpoint": "/api/users",
            "method": "GET",
            "headers": {"Content-Type": "application/json"},
            "body": {},
            "expected_status": 200,
            "test_type": "positive",
            "validation_rules": [{"type": "status_code", "expected": 200}]
        }
    ],
    "summary": {
        "total_cases": 3,
        "positive_cases": 1,
        "negative_cases": 1,
        "boundary_cases": 1
    },
    "user_options": {
        "can_save": True,
        "can_execute": True,
        "save_options": [...],
        "execute_options": [...]
    }
}
```

---

### 2. GenerateUITestTool - UI 测试生成工具

| 属性 | 值 |
|------|-----|
| 名称 | `generate_ui_test` |
| 描述 | 生成 UI/Web 自动化测试脚本。当用户需要测试网页功能、表单、按钮点击等UI交互时调用。 |
| 版本 | 1.0.0 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| url | string | 否 | 要测试的网页 URL |
| description | string | 是 | 测试场景描述，如'测试登录功能' |
| actions | array | 否 | 要执行的操作列表 |

#### 返回数据

```python
{
    "script": {
        "language": "python",
        "framework": "playwright",
        "code": "from playwright.sync_api import ...",
        "actions": [
            {"type": "navigate", "selector": None, "value": "https://..."},
            {"type": "fill", "selector": "#username", "value": "admin"},
            {"type": "click", "selector": "#login-btn", "value": None}
        ]
    },
    "user_options": {...}
}
```

---

### 3. ExecuteTestTool - 测试执行工具

| 属性 | 值 |
|------|-----|
| 名称 | `execute_test` |
| 描述 | 执行已有的测试用例。当用户要求运行、执行测试时调用。 |
| 版本 | 1.1.0 |
| 超时 | 120 秒 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| test_id | integer | 否 | 测试用例ID（UI测试脚本ID） |
| test_type | string | 否 | 测试类型（api/ui） |
| test_data | object | 否 | 测试数据 |
| base_url | string | 否 | API 基础 URL |
| script_name | string | 否 | 测试脚本名称 |

#### 支持的执行方式

1. **通过 ID 执行** - `test_id` 参数
2. **通过脚本名称执行** - `script_name` 参数（支持 .py 和 .robot）
3. **通过测试数据执行** - `test_type` + `test_data` 参数

---

### 4. ExecutePendingTestsTool - 待执行测试工具

| 属性 | 值 |
|------|-----|
| 名称 | `execute_pending_tests` |
| 描述 | 执行会话上下文中已生成的测试用例。当用户在生成测试后说'执行'、'运行'时调用。 |
| 版本 | 1.0.0 |
| 超时 | 120 秒 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| pending_tests | object | 是 | 会话上下文中的待执行测试数据 |

#### 待执行测试数据结构

```python
{
    "api": {
        "test_cases": [...],
        "base_url": "https://api.example.com"
    },
    "ui": {
        "script": {...}
    }
}
```

---

### 5. QueryKnowledgeTool - 知识库查询工具

| 属性 | 值 |
|------|-----|
| 名称 | `query_knowledge` |
| 描述 | 查询知识库获取测试最佳实践、示例代码、文档等。当用户询问'如何'、'最佳实践'、'示例'等问题时调用。 |
| 版本 | 1.0.0 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| query | string | 是 | 搜索查询内容 |
| topic | string | 否 | 查询主题类型 |

#### 主题类型

- `best_practice` - 最佳实践
- `code_example` - 代码示例
- `test_pattern` - 测试模式
- `general` - 通用查询（默认）

---

### 6. InstallSkillTool - Skill 安装工具

| 属性 | 值 |
|------|-----|
| 名称 | `install_skill` |
| 描述 | 从 skills.sh 下载并安装一个 skill。当用户要求下载、安装 skill 时调用。 |
| 版本 | 2.0.0 |
| 超时 | 10 秒 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| skill_id | string | 是 | Skill ID，格式如：chyax98/twu/testcase-generator 或完整 URL |
| skill_name | string | 否 | 安装后的名称（默认从 skill_id 提取） |

#### 特点

- 使用 Celery 异步安装
- 避免 HTTP 超时
- 返回任务 ID 用于追踪

---

### 7. RunSkillTool - Skill 运行工具

| 属性 | 值 |
|------|-----|
| 名称 | `run_skill` |
| 描述 | 执行已安装的 skill。当用户要求使用某个 skill 完成任务时调用。 |
| 版本 | 1.0.0 |
| 超时 | 120 秒 |

#### 参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| skill_name | string | 是 | 已安装的 skill 名称 |
| user_input | string | 是 | 用户的任务需求 |

#### 执行模式

Skill 支持两种执行模式，由 SKILL.md 中的 frontmatter `mode` 字段决定：

1. **generate 模式（默认）** - LLM 直接生成内容
2. **execute 模式** - LLM 解析意图，执行命令，返回结果

#### 模式配置示例

```yaml
---
mode: execute
---
```

---

<a name="english"></a>
## Overview

The Chatbot Tools module provides tools for chatbot interactions including:

- **API Test Generation** - Generate API test cases from user descriptions
- **UI Test Generation** - Generate UI automation scripts from user descriptions
- **Test Execution** - Execute generated or saved test cases
- **Knowledge Query** - Query testing best practices and code examples
- **Skill Management** - Install and run Skills

## Tools Summary

| Tool Name | Description |
|-----------|-------------|
| generate_api_test | Generate API test scripts from descriptions |
| generate_ui_test | Generate UI/Web automation scripts (Playwright) |
| execute_test | Execute existing test cases by ID or script name |
| execute_pending_tests | Execute pending tests from session context |
| query_knowledge | Query knowledge base for best practices |
| install_skill | Install skills from skills.sh (async via Celery) |
| run_skill | Execute installed skills |

## Execution Modes for RunSkillTool

1. **generate mode (default)** - LLM directly generates content
2. **execute mode** - LLM parses intent, executes commands, returns results