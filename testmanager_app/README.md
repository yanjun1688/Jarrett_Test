# TestManager App / 测试管理应用

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述

TestManager App 是 JTest 平台的核心 Django 应用，提供完整的测试管理功能：

- **项目管理** - 项目和模块的 CRUD 操作
- **测试用例管理** - 功能测试用例和测试执行记录
- **API 测试** - API 请求配置、断言、集合执行
- **测试报告** - 测试报告生成和统计
- **AI 对话** - 集成 LLM 的智能测试助手
- **技能系统** - 可扩展的技能工作流
- **实时通信** - SSE 推送和 Celery 异步任务

## 目录结构

```
testmanager_app/
├── __init__.py
├── apps.py                      # Django AppConfig
├── models.py                    # 数据模型定义
├── urls.py                      # URL 路由配置
├── admin.py                     # Django Admin 配置
├── permissions.py               # 权限控制
├── authentication.py            # 认证中间件
├── serializers.py               # DRF 序列化器
├── validators/                  # 验证器
├── utils/                       # 工具函数
│
├── views.py                     # 主视图入口
├── project_views.py             # 项目相关视图
├── testcase_views.py            # 测试用例视图
├── api_views.py                 # API 测试视图
├── report_views.py              # 报告视图
├── auth_views.py                # 认证视图
├── script_views.py              # 脚本视图
├── viewsets/                    # DRF ViewSets
│
├── agent_views.py               # Agent 集成视图
├── chatbot_views.py             # AI 对话视图
├── enhanced_chatbot_views.py    # 增强版对话视图
├── skill_api_views.py           # Skill API 视图
│
├── services/                    # 业务服务层
│   ├── __init__.py
│   ├── base_service.py          # 基础服务类
│   ├── execution_service.py     # 执行服务
│   ├── project_statistics.py    # 项目统计服务
│   ├── report_service.py        # 报告服务
│   ├── yaml_converter.py        # YAML 转换器
│   ├── yaml_parser.py           # YAML 解析器
│   └── yaml_validator.py        # YAML 验证器
│
├── sse/                         # Server-Sent Events
│   ├── __init__.py
│   ├── views.py                 # SSE 视图
│   └── channels.py              # 通道管理
│
├── tasks.py                     # Celery 异步任务
├── script_engine.py             # 脚本执行引擎
├── execution_strategies.py      # 执行策略
├── collection_execution_strategies.py  # 集合执行策略
├── agent_integration.py         # Agent 集成
├── shared_async_utils.py        # 异步工具函数
│
├── management/                  # Django 管理命令
├── migrations/                  # 数据库迁移
└── tests/                       # 测试用例
```

## 数据模型

### 核心模型

| 模型 | 说明 |
|------|------|
| `Project` | 项目 |
| `Module` | 模块 |
| `TestCase` | 测试用例 |
| `TestExecution` | 测试执行记录 |
| `TestReport` | 测试报告 |

### API 测试模型

| 模型 | 说明 |
|------|------|
| `ApiRequest` | API 请求配置 |
| `ApiAssertion` | API 断言配置 |
| `RequestCollection` | 请求集合 |
| `CollectionRequest` | 集合-请求关联 |
| `CollectionExecution` | 集合执行记录 |

### 脚本模型

| 模型 | 说明 |
|------|------|
| `TestScript` | 测试脚本 |
| `ScriptExecution` | 脚本执行记录 |

### 其他模型

| 模型 | 说明 |
|------|------|
| `FeatureTestCase` | 功能测试用例（MVP） |
| `AuthToken` | 认证 Token |

## API 端点

### REST API (ViewSet)

| 端点 | 说明 |
|------|------|
| `/api/projects/` | 项目管理 |
| `/api/modules/` | 模块管理 |
| `/api/testcases/` | 测试用例管理 |
| `/api/executions/` | 执行记录管理 |
| `/api/reports/` | 测试报告管理 |
| `/api/test-scripts/` | 测试脚本管理 |
| `/api/api-requests/` | API 请求管理 |
| `/api/api-assertions/` | API 断言管理 |
| `/api/request-collections/` | 请求集合管理 |
| `/api/collection-executions/` | 集合执行管理 |
| `/api/users/` | 用户管理 |
| `/api/feature-tests/` | 功能测试用例管理 |

### 认证 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login/` | POST | 用户登录 |
| `/api/auth/me/` | GET | 获取当前用户信息 |
| `/api/auth/logout/` | POST | 用户登出 |

### AI 对话 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chatbot/chat/` | POST | AI 对话 |
| `/api/chatbot/models/` | GET | 获取模型列表 |
| `/api/chatbot/clear/` | POST | 清空会话 |
| `/api/chatbot/tools/` | GET | 获取可用工具 |
| `/api/chatbot/test-tool/` | POST | 测试工具执行 |
| `/api/chatbot/conversations/` | GET | 会话列表 |
| `/api/chatbot/conversations/<id>/` | GET/DELETE | 会话详情/删除 |

### Agent API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/api-test/agent/generate/` | POST | Agent 生成测试用例 |
| `/api/agent/knowledge/query/` | POST | 查询知识库 |
| `/api/agent/knowledge/build/` | POST | 构建知识库 |
| `/api/agent/knowledge/list/` | GET | 知识库列表 |
| `/api/agent/best-practices/` | GET | 获取最佳实践 |

### Skill API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills/remote-search/` | GET | 远程搜索 Skill |
| `/api/skills/install/` | POST | 安装 Skill |
| `/api/skills/local/` | GET | 本地 Skill 列表 |
| `/api/skills/execute/` | POST | 执行 Skill |

### SSE 实时推送

| 端点 | 说明 |
|------|------|
| `/api/sse/chatbot/` | ChatBot 进度推送 |
| `/api/sse/test-execution/<id>/` | 测试执行进度 |
| `/api/sse/task/<id>/` | 任务进度 |
| `/api/sse/recording/<id>/` | 录制事件 |

### YAML 配置 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/projects/<id>/yaml-to-collection/` | POST | YAML 转集合 |
| `/api/projects/<id>/yaml/validate/` | POST | YAML 验证 |

## Celery 异步任务

### 任务列表

| 任务名称 | 说明 |
|---------|------|
| `testmanager_app.execute_collection` | 执行请求集合 |
| `testmanager_app.execute_api_request` | 执行单个 API 请求 |
| `testmanager_app.install_skill` | 安装 Skill |

### 任务状态查询

```python
from testmanager_app.tasks import get_task_status

status = get_task_status(task_id)
# {
#     'task_id': 'xxx',
#     'status': 'SUCCESS',
#     'ready': True,
#     'successful': True,
#     'result': {...}
# }
```

## SSE 通道管理

### 通道类型

| 类型 | 通道名称 | 说明 |
|------|---------|------|
| chatbot | chatbot-progress | AI 对话进度 |
| test-execution | test-execution-progress | 测试执行进度 |
| task | task-progress | 任务进度 |
| recording | recording-events | 录制事件 |

### 使用示例

```python
from testmanager_app.sse.channels import SSEChannel

# 创建 ChatBot 进度回调
callback = SSEChannel.create_chatbot_callback(user_id)
callback['send_progress']('intent_classification', '正在分析意图...', 25)
callback['send_complete']({'result': '...'})

# 创建测试执行回调
callback = SSEChannel.create_test_execution_callback(user_id, execution_id)
callback['send_info']('开始执行...')
callback['send_progress']('running', '执行中...', 50, {'total': 10})
```

## 服务层

### TestExecutionService

测试执行核心服务：

```python
from testmanager_app.services.execution_service import TestExecutionService

# 执行 API 测试
result = TestExecutionService.execute_api_test(execution, user)
```

### YamlToCollectionConverter

YAML 配置转换器：

```python
from testmanager_app.services.yaml_converter import YamlToCollectionConverter

converter = YamlToCollectionConverter(project_id=1, created_by_id=1)
success, result = converter.convert(yaml_content, name, description, execution_mode)
```

### YamlValidator

YAML 配置验证器：

```python
from testmanager_app.services.yaml_validator import YamlValidator

validator = YamlValidator()
is_valid, result = validator.validate(yaml_content)
```

## 执行策略

### 请求集合执行模式

| 模式 | 说明 |
|------|------|
| `concurrent` | 并发执行 |
| `chain` | 链式执行（支持变量传递） |

### CollectionExecutionStrategyFactory

```python
from testmanager_app.collection_execution_strategies import CollectionExecutionStrategyFactory

strategy = CollectionExecutionStrategyFactory.get_strategy('chain')
executions = strategy.execute_in_worker(collection_requests, user, collection_exec, context)
```

## 认证机制

### AuthToken

自定义 Token 模型，支持：

- 过期时间设置
- 多端点登录
- Token 刷新

```python
from testmanager_app.models import AuthToken

# 创建 Token
token = AuthToken.create_token(user, expires_in_days=7)

# 检查过期
if token.is_expired():
    token.refresh()
```

## 断言类型

### ApiAssertion 断言类型

| 类型 | 说明 |
|------|------|
| `status_code` | HTTP 状态码 |
| `response_time` | 响应时间 |
| `response_body_field` | 响应体字段 |
| `response_header_field` | 响应头字段 |

### 比较操作符

| 操作符 | 说明 |
|--------|------|
| `equals` | 等于 |
| `contains` | 包含 |
| `not_contains` | 不包含 |
| `greater_than` | 大于 |
| `less_than` | 小于 |

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_HOST` | 172.17.61.120 | Redis 主机 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `CHANNELS_REDIS_DB` | 3 | SSE Channel Redis DB |

---

<a name="english"></a>
## Overview

TestManager App is the core Django application of JTest platform, providing complete test management functionality:

- **Project Management** - CRUD operations for projects and modules
- **Test Case Management** - Functional test cases and execution records
- **API Testing** - API request configuration, assertions, collection execution
- **Test Reports** - Report generation and statistics
- **AI Chat** - LLM-intelligent test assistant
- **Skill System** - Extensible skill workflows
- **Real-time Communication** - SSE push and Celery async tasks

## Key Models

### Core Models
- `Project` - Project
- `Module` - Module
- `TestCase` - Test case
- `TestExecution` - Test execution record
- `TestReport` - Test report

### API Testing Models
- `ApiRequest` - API request configuration
- `ApiAssertion` - API assertion configuration
- `RequestCollection` - Request collection
- `CollectionExecution` - Collection execution record

## API Endpoints Summary

| Category | Endpoints |
|----------|-----------|
| REST API | `/api/projects/`, `/api/testcases/`, `/api/executions/`, etc. |
| Auth | `/api/auth/login/`, `/api/auth/me/`, `/api/auth/logout/` |
| ChatBot | `/api/chatbot/chat/`, `/api/chatbot/conversations/` |
| Agent | `/api/api-test/agent/generate/`, `/api/agent/knowledge/` |
| Skills | `/api/skills/install/`, `/api/skills/execute/` |
| SSE | `/api/sse/chatbot/`, `/api/sse/task/<id>/` |

## Celery Tasks

- `execute_collection_task` - Execute request collection
- `execute_api_request_task` - Execute single API request
- `install_skill_task` - Install skill

## SSE Channels

| Channel Type | Purpose |
|--------------|---------|
| chatbot | AI chat progress |
| test-execution | Test execution progress |
| task | Task progress |
| recording | Recording events |

## Assertion Types

- `status_code` - HTTP status code
- `response_time` - Response time
- `response_body_field` - Response body field
- `response_header_field` - Response header field

## Comparison Operators

- `equals`, `contains`, `not_contains`
- `greater_than`, `less_than`