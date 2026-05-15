# JTest - AI驱动的智能测试管理平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Django-5.2.6-green.svg" alt="Django">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

JTest 是一个基于 Django + React 的智能化测试管理平台，深度融合 AI Agent 技术，支持 API 测试、UI 自动化测试、性能压测等功能。通过 Native Function Calling 架构和技能系统，让测试工作更高效、更智能。

## 核心功能

### API 测试管理
- **API 请求管理** - 创建、编辑、执行 RESTful API 请求
- **断言与验证** - 支持状态码、JSON Path、响应时间等多种断言
- **请求集合** - 批量执行多个 API 请求，支持并发和链式执行
- **变量传递** - 支持集合内变量提取和传递，实现接口依赖测试
- **YAML 导入导出** - 支持 Postman、Swagger 等格式的 YAML 导入导出

### UI 自动化测试
- **Playwright 录制** - 浏览器操作录制和回放
- **UI 测试脚本** - 管理和编辑 UI 测试脚本
- **执行引擎** - 基于 Playwright 的浏览器自动化执行
- **操作转换** - 录制操作转换为可执行测试脚本

### 性能测试（压测）
- **基础压测** - 简单的并发压力测试
- **高级压测** - 基于 Locust 的分布式压测，支持自定义压测脚本
- **实时监控** - WebSocket 实时推送压测进度和指标
- **压测报告** - 自动生成详细的性能测试报告

### AI 智能助手
- **ReAct 架构** - 多轮工具调用循环，LLM 自主决策工具选择和调用顺序
- **Native Function Calling** - 无需意图分类，LLM 直接决策调用工具或回复
- **多 LLM 支持** - 支持 OpenAI、Claude、DeepSeek、智谱 GLM、通义千问 Qwen（含 Anthropic 工具调用格式兼容）
- **测试生成** - AI 辅助生成 API/UI 测试用例和脚本
- **测试规划** - 智能测试计划生成和细化
- **智能对话** - 支持技能调用、测试执行、知识查询
- **对话记忆 RAG** - 消息写入时异步索引到 ChromaDB，用户提问时语义检索相关历史记忆注入 system prompt，突破 Token 经济学的冷区限制

### Token Economics（上下文管理）
- **Token 预算管理** - 监控和控制 Token 消耗
- **上下文缓存优化** - 智能缓存减少重复 Token 消耗
- **增量存储** - 增量更新上下文，避免重复传输
- **智能摘要** - 长对话自动摘要，保持上下文精简
- **三层压缩** - 热区（最近 10 条原始消息）→ 温区（中间 40 条 → 1 条结构化摘要）→ 冷区（最早 N 条 → 1 条短摘要）
- **对话记忆 RAG** - 异步索引消息到独立 ChromaDB collection，语义检索突破冷区限制

### 知识库管理（RAG）
- **文档上传** - 支持 PDF、Word、Markdown、TXT 格式
- **智能分块** - 按文档类型自动选择分块策略（PRD 按标题层级分割、API_DOC 按端点分割）
- **双路检索** - 向量检索（语义匹配）+ BM25 全文检索（关键词匹配）并行，RRF 融合
- **上下文注入** - 结构化 Prompt 组装（带编号、标题、类型），每次检索全量日志可追溯
- **知识库边界** - 仅存知识型文档（PRD、API 文档、最佳实践），业务数据不走 RAG
- **检索流程**：用户查询 → BM25 + Vector 双路 Top-50 → RRF 融合 → Top-10 → 上下文注入 → LLM

### 技能系统
- **技能市场** - 浏览和安装社区技能
- **MCP 工具集成** - 支持 Model Context Protocol 工具
- **内置技能** - 
  - 测试用例生成器（testcase-generator）
  - MCP 构建器（mcp-builder）
  - 技能创建器（skill-creator）
  - Agent 浏览器（agent-browser）
  - API 设计原则（api-design-principles）
- **自定义技能** - 开发并发布自己的测试技能

### 测试报告与统计
- **执行报告** - 详细的测试执行结果统计
- **可视化报表** - 图表展示测试趋势和分布
- **项目统计** - 项目级别的测试覆盖率、成功率统计
- **历史记录** - 完整的测试执行历史追踪

### 用户与权限
- **Token 认证** - 基于 Token 的 API 认证机制
- **角色权限** - 超级管理员和普通用户权限分离
- **用户管理** - 用户 CRUD 和权限分配

## 技术架构

### 后端
- **Python 3.11+** - 主要开发语言
- **Django 5.2.6** - Web 框架
- **Django REST Framework** - RESTful API
- **Django Channels** - WebSocket 支持
- **Celery** - 异步任务处理
- **Redis** - 缓存和消息队列
- **ChromaDB** - 向量数据库（语义检索）
- **Whoosh + jieba** - BM25 全文检索引擎（关键词检索）
- **Playwright** - UI 自动化测试
- **Locust** - 性能测试框架

### 前端
- **React 18** - UI 框架
- **Ant Design** - 组件库
- **Axios** - HTTP 客户端
- **Recharts** - 数据可视化

### AI/LLM
- OpenAI GPT
- Anthropic Claude
- DeepSeek
- 智谱 GLM
- 通义千问 Qwen

## 项目结构

```
JTest/
├── core/                          # 核心 AI Agent 系统
│   ├── agents/                    # Agent 实现
│   │   ├── generation/           # 测试生成 Agent
│   │   ├── chatbot_agent.py      # Chatbot Agent (ReAct 架构)
│   │   ├── react_engine.py       # ReAct 循环引擎（多轮工具调用）
│   │   ├── rag/                  # RAG 知识库 Agent + 对话记忆 RAG
│   │   │   ├── knowledge_retriever.py   # 知识库双路检索（BM25 + Vector）
│   │   │   ├── conversation_memory.py   # 对话记忆检索与索引（ARCH-02）
│   │   │   └── vector_store.py          # ChromaDB 向量存储（多 collection 支持）
│   │   └── llm/                  # LLM 服务层（Anthropic/OpenAI 等格式兼容）
│   ├── context/                   # 上下文管理
│   │   ├── markdown_store.py     # Markdown 文件存储
│   │   └── token_economics/      # Token Economics 系统（三层压缩）
│   ├── task_events.py            # Celery 任务事件发布（WebSocket 通知）
│   └── tools/                     # 测试工具库
│       ├── api/                   # HTTP 客户端
│       ├── chatbot/              # Chatbot 工具
│       ├── execution/            # 执行编排
│       ├── generation/           # 测试生成
│       └── validation/           # 响应验证
│
├── api/v1/                        # RESTful API v1
│   ├── execution/                # 执行相关 API
│   ├── knowledge/                # 知识库 API
│
├── testmanager_app/              # API 测试管理应用
│   ├── models.py                 # 数据模型
│   ├── controllers/              # API 控制器
│   ├── services/                 # 业务服务
│   │   ├── execution_engine/     # 执行引擎
│   │   ├── yaml_converter.py     # YAML 转换
│   │   └── report_service.py     # 报告服务
│   └── chatbots/                 # AI 对话
│
├── test_ui_app/                  # UI 测试应用
│   ├── recording/                # 录制功能
│   ├── execution/                # 执行引擎
│   ├── consumers.py              # WebSocket 消费者
│   └── advanced_pressure_consumers.py  # 压测消费者
│
├── test_ai_agent/                # AI Agent 应用
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── features/            # 功能模块
│   │   ├── components/          # 组件
│   │   └── api/                 # API 封装
│   └── package.json
│
├── skills/                       # 技能系统
├── shared/                       # 共享工具
└── testmanager/                  # Django 配置
```

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 16+
- MySQL 8.0+ 或 PostgreSQL
- Redis 6.0+

### 安装

1. **克隆项目**
```bash
git clone https://github.com/yanjun1688/JTest.git
cd JTest
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库、Redis、LLM API Key
```

3. **安装后端依赖**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **安装 Playwright 浏览器**
```bash
python -m playwright install chromium
```

5. **数据库迁移**
```bash
python manage.py migrate
```

6. **创建管理员账户**
```bash
python manage.py createsuperuser
# 输入用户名、邮箱、密码
```

7. **安装前端依赖**
```bash
cd frontend
npm install
```

## 启动服务

**启动 Django 后端**
```bash
# 开发环境
python manage.py runserver

# 或启动 Daphne（支持 WebSocket）
daphne -b 0.0.0.0 -p 8000 testmanager.asgi:application
```

**启动 Celery Worker**
```bash
# Windows
celery -A testmanager worker -l info -P solo

# Linux/Mac
celery -A testmanager worker -l info
```

**启动前端**
```bash
cd frontend
npm start
```

**访问地址**
- 前端界面: http://localhost:3000
- 后端 API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/

## 用户管理

### 系统权限说明

| 角色 | 权限 |
|------|------|
| **超级管理员** | 创建/删除用户、管理所有资源、系统配置 |
| **普通用户** | 创建/管理自己的测试项目、执行测试、查看报告 |

### 创建用户

**方式1：通过 Django Admin（推荐）**
```bash
# 1. 启动后端
python manage.py runserver

# 2. 访问 http://localhost:8000/admin/
# 3. 用超级管理员登录
# 4. 进入 "Users" → "Add user"
# 5. 填写用户名、密码，勾选 "Staff status" 可设为管理员
```

**方式2：通过 API（需管理员权限）**
```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your-admin-token" \
  -d '{
    "username": "newuser",
    "password": "userpassword",
    "email": "user@example.com"
  }'
```

### 用户登录

**获取 Token**
```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'

# 响应示例：
{
  "token": "abc123xyz...",
  "user": {
    "user_id": 1,
    "username": "your-username",
    "token_expires_at": "2026-04-24T12:00:00"
  }
}
```

**使用 Token 访问 API**
```bash
# 在所有请求头中添加：
Authorization: Token your-token-here

curl http://localhost:8000/api/projects/ \
  -H "Authorization: Token abc123xyz..."
```

**前端登录**
- 访问 http://localhost:3000
- 输入用户名密码
- 系统自动保存 Token 到 localStorage

### 用户登出

```bash
curl -X POST http://localhost:8000/api/logout/ \
  -H "Authorization: Token your-token-here"
```

## 使用示例

### API 测试流程

1. **创建项目** → 在项目管理页面新建项目
2. **添加 API 请求** → 配置 URL、方法、Headers、Body
3. **配置断言** → 添加状态码、JSON Path 等断言规则
4. **创建请求集合** → 将多个请求组织成集合
5. **执行测试** → 支持单个执行、批量并发、链式执行
6. **查看报告** → 查看执行结果和详细报告

**YAML 导入示例：**
```yaml
name: 用户管理接口测试
description: 登录获取 token，然后用 token 获取用户信息
variables:
  base_url: https://api.example.com
steps:
  - name: 登录接口
    request:
      method: POST
      url: "{{base_url}}/api/auth/login"
      headers:
        Content-Type: application/json
      json:
        username: admin
        password: "123456"
    extract:
      - name: auth_token
        jsonpath: "$.token"
    assertions:
      - type: status_code
        expected: 200
        comparison: equals
      - type: jsonpath
        expression: "$.token"
        expected: "some-token-value"
        comparison: not_equals

  - name: 获取用户信息
    request:
      method: GET
      url: "{{base_url}}/api/users/me"
      headers:
        Authorization: "Bearer {{auth_token}}"
    assertions:
      - type: status_code
        expected: 200
        comparison: equals
      - type: jsonpath
        expression: "$.username"
        expected: admin
        comparison: equals
```

**YAML 字段说明：**

| 字段 | 说明 | 必填 |
|------|------|------|
| `name` | 脚本名称 | ✅ |
| `description` | 脚本描述 | ❌ |
| `variables` | 初始变量（字典格式，支持 `{{var}}` 模板） | ❌ |
| `steps` | 测试步骤列表 | ✅ |
| `setup` | 前置步骤（失败则中止） | ❌ |
| `teardown` | 后置步骤（无论成功失败都执行） | ❌ |
| `stop_on_failure` | 步骤失败时是否中止（默认 true） | ❌ |

**步骤字段：**

| 字段 | 说明 | 必填 |
|------|------|------|
| `name` | 步骤名称 | ✅ |
| `request.method` | HTTP 方法 | ✅ |
| `request.url` | 请求 URL（支持 `{{var}}` 模板） | ✅ |
| `request.headers` | 请求头（支持模板） | ❌ |
| `request.json` | JSON 请求体 | ❌ |
| `request.data` | 表单数据 | ❌ |
| `extract` | 变量提取规则 `[{name, jsonpath}]` | ❌ |
| `assertions` | 断言列表 | ❌ |

**断言字段：**

| 字段 | 说明 | 必填 |
|------|------|------|
| `type` | 断言类型：`status_code` 或 `jsonpath` | ✅ |
| `expected` | 期望值 | ✅ |
| `comparison` | 比较方式：`equals`、`not_equals`、`contains`、`gt`、`gte`、`lt`、`lte` | ✅ |
| `expression` | JSONPath 表达式（type=jsonpath 时必填） | 条件必填 |

### UI 自动化测试流程

1. **启动录制** → 点击录制按钮开始录制浏览器操作
2. **执行操作** → 在浏览器中执行登录、点击、填写表单等操作
3. **停止录制** → 系统自动生成测试脚本
4. **编辑脚本** → 可编辑生成的脚本，添加断言
5. **执行测试** → 选择浏览器环境执行测试
6. **查看结果** → 查看执行截图和日志

### 性能压测流程

1. **创建压测配置** → 配置并发用户数、压测时长、请求频率
2. **编写压测脚本**（高级模式）→ 使用 Locust 编写自定义压测脚本
3. **启动压测** → WebSocket 实时推送压测进度
4. **监控指标** → 实时查看 QPS、响应时间、错误率
5. **生成报告** → 自动生成详细的压测报告

### AI 对话使用

```
用户: 帮我生成 /api/login 接口的测试用例

AI: 好的，我来为您生成 /api/login 接口的测试用例：

1. POST /api/login - 正向测试（有效凭据）
   - 预期：返回 200，包含 token
   
2. POST /api/login - 边界测试（空用户名）
   - 预期：返回 400，提示用户名不能为空
   
3. POST /api/login - 异常测试（错误密码）
   - 预期：返回 401，提示认证失败

是否立即执行这些测试用例？
```

### 技能使用示例

```bash
# 安装技能
curl -X POST http://localhost:8000/api/skills/install/ \
  -H "Authorization: Token your-token" \
  -d '{"skill_name": "testcase-generator"}'

# 执行技能
curl -X POST http://localhost:8000/api/skills/execute/ \
  -H "Authorization: Token your-token" \
  -d '{
    "skill_name": "testcase-generator",
    "input": {"endpoint": "/api/users", "method": "GET"}
  }'
```

## 配置说明

### 环境变量 (.env)

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=jtest
DB_USER=root
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=3306

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# LLM 配置（选填一个或多个）
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
ZHIPU_API_KEY=xxx
QWEN_API_KEY=sk-xxx

# Token Economics（可选）
TOKEN_BUDGET_DAILY=100000
CONTEXT_CACHE_ENABLED=true
```

## API 文档

### 主要 API 端点

| 端点 | 说明 |
|------|------|
| `/api/projects/` | 项目管理 |
| `/api/modules/` | 模块管理 |
| `/api/api-requests/` | API 请求管理 |
| `/api/request-collections/` | 请求集合管理 |
| `/api/collection-executions/` | 集合执行记录 |
| `/api/test-scripts/` | 测试脚本管理 |
| `/api/script-executions/` | 脚本执行记录 |
| `/api/pressure-test-configs/` | 压测配置管理 |
| `/api/pressure-test-executions/` | 压测执行记录 |
| `/api/advanced-pressure-test-configs/` | 高级压测配置 |
| `/api/advanced-pressure-test-executions/` | 高级压测执行 |
| `/api/test-reports/` | 测试报告 |
| `/api/skills/` | 技能管理 |
| `/api/login/` | 用户登录 |
| `/api/logout/` | 用户登出 |
| `/api/me/` | 当前用户信息 |

### 任务实时通知
- **Celery Task Awareness** - 任务完成/失败时通过 Channel Layer 广播 WebSocket 通知
- **按用户隔离** - 每个用户只收到自己的任务事件（`celery_tasks_{user_id}` 群组）
- **覆盖任务** - 文档同步、ChromaDB 操作、UI 测试执行、对话记忆索引等
- **前端 Hook** - `useTaskWebSocket` React Hook，按 `task_name` 注册回调

### WebSocket 端点

| 端点 | 说明 |
|------|------|
| `/ws/chatbot/` | Chatbot 实时对话 |
| `/ws/celery/tasks/` | Celery 任务状态实时通知 |
| `/ws/pressure-test/<id>/` | 压测实时进度 |
| `/ws/advanced-pressure-test/<id>/` | 高级压测实时进度 |

## 开发指南

### 代码规范
- Python: PEP 8, Black 格式化
- JavaScript: ESLint 规则
- Git 提交: 语义化提交 (feat/fix/docs/refactor)

### 添加 Agent

```python
# core/agents/my_agent.py
from core.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, user_input: str, context: dict) -> dict:
        # 实现处理逻辑
        return {"result": "..."}
```

### 添加 Tool

```python
# core/tools/my_tool.py
from core.tools.base_tool import BaseTool, ToolResult

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="...")
    
    async def execute(self, **kwargs) -> ToolResult:
        # 实现工具逻辑
        return ToolResult(success=True, data={})
```

### 添加 Skill

```python
# skills/my-skill/skill.yaml
name: my-skill
description: "My custom skill"
version: "1.0.0"
entry_point: main.py

# skills/my-skill/main.py
async def execute(input_data: dict) -> dict:
    # 实现技能逻辑
    return {"result": "..."}
```

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'feat: add feature'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- **GitHub**: [yanjun1688/JTest](https://github.com/yanjun1688/JTest)
- **Issues**: [提交问题](https://github.com/yanjun1688/JTest/issues)
- **邮箱**: hyanjun546@gmail.com

---

<p align="center">Made with ❤️ by JTest Team</p>
