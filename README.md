# JTest - AI 驱动的智能测试管理平台

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 项目简介

JTest 是一个基于 Django + React 的智能测试管理平台，深度融合 AI 能力，支持 API 测试、UI 自动化测试、测试用例管理等功能。通过 AI Agent 架构实现智能测试流程编排，让测试工作更高效、更智能。

## ✨ 核心特性

### 测试管理
- **API 测试** - 支持 RESTful API 的创建、执行和断言，支持请求集合批量执行
- **UI 自动化测试** - 基于 Playwright 的浏览器自动化录制和执行
- **测试用例管理** - 项目化管理测试用例和测试集合
- **测试报告** - 自动生成测试执行报告和统计分析

### AI 智能
- **智能对话** - 集成多 LLM 提供商的 AI 对话助手
- **测试生成** - AI 辅助生成 API/UI 测试用例
- **意图识别** - 基于集合论的智能意图分类系统
- **RAG 知识库** - 检索增强生成，提供测试最佳实践

### 技能系统
- **可扩展技能** - 支持从 skills.sh 安装和运行技能
- **自定义工作流** - 灵活的技能编排和执行

## 🏗️ 技术架构

### 后端技术栈
- Python 3.10+
- Django 5.x + Django REST Framework
- Celery（异步任务）
- Redis（缓存和消息队列）
- ChromaDB（向量数据库）
- Playwright（UI 自动化）

### 前端技术栈
- React 18
- Ant Design
- Axios

### AI/LLM 支持
- OpenAI GPT
- Anthropic Claude
- DeepSeek
- 智谱 GLM
- 通义千问 Qwen

## 📁 项目结构

```
JTest/
├── core/                          # 核心模块（v2.0 架构）
│   ├── agents/                    # AI Agent 系统
│   │   ├── generation/            # 测试生成 Agent
│   │   ├── intent/                # 意图识别 Agent
│   │   ├── llm/                   # LLM 服务层
│   │   ├── planning/              # 规划 Agent
│   │   ├── rag/                   # RAG 知识库 Agent
│   │   └── execution/             # 执行 Agent
│   ├── tools/                     # 测试工具库
│   │   ├── api/                   # API 测试工具
│   │   ├── chatbot/               # Chatbot 交互工具
│   │   ├── execution/             # 执行编排工具
│   │   ├── generation/            # 测试生成工具
│   │   └── validation/            # 响应验证工具
│   ├── services/                  # 核心服务层
│   └── config.py                  # 配置管理
│
├── api/                           # RESTful API（v1版本）
│   └── v1/
│       └── flows/                 # 流程相关 API
│
├── testmanager_app/               # 测试管理主应用
│   ├── models.py                  # 数据模型
│   ├── views.py                   # API 视图
│   ├── services/                  # 业务服务层
│   ├── sse/                       # Server-Sent Events
│   ├── tasks.py                   # Celery 异步任务
│   └── urls.py                    # URL 路由
│
├── test_ui_app/                   # UI 测试应用
│   ├── models.py                  # UI 测试数据模型
│   ├── recording/                 # 录制功能
│   └── execution/                 # 执行引擎
│
├── shared/                        # 共享基础设施
│   ├── exceptions.py              # 异常处理
│   ├── constants.py               # 常量定义
│   └── utils/                     # 工具函数
│
├── skills/                        # 已安装的技能
├── .agents/                       # Agent 技能配置
│
├── testmanager/                   # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
│
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── api/                   # API 调用封装
│   │   ├── components/            # React 组件
│   │   ├── features/              # 功能模块
│   │   └── utils/                 # 工具函数
│   └── public/
│
├── tests/                         # 测试用例
├── docs/                          # 文档
├── scripts/                       # 脚本工具
└── infrastructure/                # 基础设施配置
```

## 📚 详细文档

| 模块 | 说明 | 文档链接 |
|------|------|----------|
| Core Agents | AI Agent 系统 | [core/agents/README.md](core/agents/README.md) |
| Core Tools | 测试工具库 | [core/tools/README.md](core/tools/README.md) |
| TestManager App | 测试管理应用 | [testmanager_app/README.md](testmanager_app/README.md) |

### Agent 子模块文档

| 子模块 | 说明 | 文档链接 |
|--------|------|----------|
| Generation | 测试生成 Agent | [core/agents/generation/README.md](core/agents/generation/README.md) |
| Intent | 意图识别 Agent | [core/agents/intent/README.md](core/agents/intent/README.md) |
| LLM | LLM 服务层 | [core/agents/llm/README.md](core/agents/llm/README.md) |
| Planning | 规划 Agent | [core/agents/planning/README.md](core/agents/planning/README.md) |
| RAG | RAG 知识库 Agent | [core/agents/rag/README.md](core/agents/rag/README.md) |
| Execution | 执行 Agent | [core/agents/execution/README.md](core/agents/execution/README.md) |

### Tools 子模块文档

| 子模块 | 说明 | 文档链接 |
|--------|------|----------|
| API | HTTP 客户端工具 | [core/tools/api/README.md](core/tools/api/README.md) |
| Chatbot | Chatbot 交互工具 | [core/tools/chatbot/README.md](core/tools/chatbot/README.md) |
| Execution | 执行编排工具 | [core/tools/execution/README.md](core/tools/execution/README.md) |
| Generation | 测试生成工具 | [core/tools/generation/README.md](core/tools/generation/README.md) |
| Validation | 响应验证工具 | [core/tools/validation/README.md](core/tools/validation/README.md) |

## 🚀 快速开始

### 环境准备

1. **克隆项目**
```bash
git clone https://github.com/yanjun1688/Jarrett_Test.git
cd JTest
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库、Redis、LLM API Key 等
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
```

7. **安装前端依赖**
```bash
cd frontend
npm install
```

### 启动服务

**启动后端服务：**

```bash
# 启动 Django 开发服务器 (默认端口 8000)
python manage.py runserver

# 或启动 Daphne (生产环境，支持 WebSocket)
daphne -b 0.0.0.0 -p 8000 testmanager.asgi:application
```

**启动 Celery Worker（异步任务处理）：**

```bash
# Windows
celery -A testmanager worker -l info -P solo

# Linux/Mac
celery -A testmanager worker -l info
```

**启动前端开发服务器：**

```bash
cd frontend
npm start
```

**完整启动流程：**

```bash
# 启动 Django 后端 (默认端口 8000)
python manage.py runserver

# 启动 Celery Worker (异步任务处理)
celery -A testmanager worker -l info -P solo

# 启动前端开发服务器 (默认端口 3000)
cd frontend && npm start
```

### 访问地址

- 前端界面: http://localhost:3000
- 后端 API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/

## 🔌 API 端点

### REST API

| 端点 | 说明 |
|------|------|
| `/api/projects/` | 项目管理 |
| `/api/modules/` | 模块管理 |
| `/api/testcases/` | 测试用例管理 |
| `/api/executions/` | 执行记录管理 |
| `/api/api-requests/` | API 请求管理 |
| `/api/request-collections/` | 请求集合管理 |
| `/api/reports/` | 测试报告 |

### AI 对话 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chatbot/chat/` | POST | AI 对话 |
| `/api/chatbot/conversations/` | GET | 会话列表 |
| `/api/chatbot/models/` | GET | 可用模型列表 |

### Skill API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills/remote-search/` | GET | 远程搜索 Skill |
| `/api/skills/install/` | POST | 安装 Skill |
| `/api/skills/execute/` | POST | 执行 Skill |

### SSE 实时推送

| 端点 | 说明 |
|------|------|
| `/api/sse/chatbot/` | ChatBot 进度推送 |
| `/api/sse/test-execution/<id>/` | 测试执行进度 |
| `/api/sse/task/<id>/` | 任务进度 |

## 🤖 AI Agent 系统

### 架构设计

JTest v2.0 采用模块化的 AI Agent 架构：

```
用户输入 → 意图识别 → 规划 Agent → 执行 Agent → 结果生成
                ↓
           RAG 知识库
                ↓
            LLM 服务
```

### 意图识别

基于集合论和谓词逻辑的意图分类系统（V-O-M 模型）：

| 意图类型 | 说明 | 示例 |
|---------|------|------|
| GENERATE_API_TEST | 生成 API 测试 | "帮我生成登录接口的测试用例" |
| GENERATE_UI_TEST | 生成 UI 测试 | "生成登录页面的 UI 测试" |
| EXECUTE_TEST | 执行测试 | "运行这个测试用例" |
| QUERY_KNOWLEDGE | 查询知识 | "如何设计 API 测试用例" |
| INSTALL_SKILL | 安装技能 | "安装 testcase-generator 技能" |

### LLM 服务

支持多提供商的统一 LLM 接口：

```python
from core.agents.llm.base_llm import create_llm_service

# 创建 LLM 服务
llm = create_llm_service(provider="qwen")

# 生成文本
response = await llm.generate(
    prompt="帮我生成测试用例",
    temperature=0.7
)
```

### RAG 知识库

基于 ChromaDB 的检索增强生成：

```python
from core.agents.rag.rag_agent import RAGAgent

# 查询知识库
rag = RAGAgent()
result = await rag.query(
    query="API 测试最佳实践",
    top_k=5
)
```

## 🛠️ 测试工具库

### 工具类型

| 工具 | 名称 | 说明 |
|------|------|------|
| HTTPClientTool | http_client | HTTP 请求客户端 |
| GenerateAPITestTool | generate_api_test | 生成 API 测试用例 |
| GenerateUITestTool | generate_ui_test | 生成 UI 测试脚本 |
| ExecuteTestTool | execute_test | 执行测试用例 |
| QueryKnowledgeTool | query_knowledge | 查询知识库 |
| InstallSkillTool | install_skill | 安装技能 |
| RunSkillTool | run_skill | 运行技能 |

### 使用示例

```python
from core.tools.base_tool import global_tool_registry

# 执行工具
result = await global_tool_registry.execute(
    "generate_api_test",
    endpoint="/api/login",
    method="POST",
    description="测试登录功能"
)
```

## 📋 使用示例

### API 测试操作流程

1. **创建项目**: 进入"项目管理"，点击"新建项目"
2. **创建 API 请求**: 添加 API 请求，配置 URL、方法、请求头、请求体
3. **添加断言**: 配置断言规则（状态码、响应体字段等）
4. **执行测试**: 点击"执行"运行测试
5. **查看报告**: 在"测试报告"中查看执行结果

### 请求集合执行

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 并发执行 | 所有请求同时发起 | 压力测试、独立请求验证 |
| 链式执行 | 顺序执行 + 变量传递 | 完整业务流程测试 |

**变量传递示例：**
```json
// 第一个请求：登录接口，提取 token
// 配置变量提取: $.data.token → token

// 第二个请求：使用 token
{
  "url": "https://api.example.com/users",
  "headers": {
    "Authorization": "Bearer {{token}}"
  }
}
```

### AI 对话使用

```
用户: 帮我生成 /api/users 接口的测试用例

AI: 好的，我来为您生成 /api/users 接口的测试用例。

已生成以下测试用例：
1. GET /api/users - 正向测试（获取用户列表）
2. POST /api/users - 正向测试（创建用户）
3. GET /api/users/{id} - 正向测试（获取单个用户）
...

是否立即执行这些测试用例？
```

## ⚙️ 配置说明

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥 | `your-secret-key` |
| `DATABASE_URL` | 数据库连接 | `sqlite:///db.sqlite3` |
| `REDIS_HOST` | Redis 主机 | `localhost` |
| `CELERY_BROKER_URL` | Celery Broker | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | LLM 提供商 | `qwen` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-...` |

### LLM 提供商配置

```env
# 选择默认 LLM 提供商
LLM_PROVIDER=qwen

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4

# DeepSeek
DEEPSEEK_API_KEY=sk-xxx

# 智谱
ZHIPU_API_KEY=xxx

# 通义千问
QWEN_API_KEY=xxx
```

## 🔧 开发指南

### 代码规范

- **Python**: 遵循 PEP 8，使用 Black 格式化
- **JavaScript/React**: 遵循 ESLint 规则
- **提交信息**: 使用语义化提交 (feat/fix/docs/refactor)

### 添加新的 Agent

```python
# core/agents/my_agent/my_agent.py
from core.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, user_input: str, context: dict) -> dict:
        # 实现处理逻辑
        return {"result": "..."}
```

### 添加新的 Tool

```python
# core/tools/my_tool.py
from core.tools.base_tool import BaseTool, ToolResult

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="工具描述"
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        # 实现工具逻辑
        return ToolResult(success=True, data={})
```

## 📖 常见问题

### Q: Playwright 浏览器安装失败？
```bash
python -m playwright install chromium
```

### Q: Celery Worker 无法启动？
确保 Redis 服务已启动，检查 `.env` 中的 Redis 配置。

### Q: 前端无法连接后端 API？
检查 `frontend/.env` 中的 API 地址配置。

### Q: LLM 调用失败？
检查 `.env` 中对应 LLM 提供商的 API Key 是否正确配置。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📬 联系方式

- GitHub Issues: [提交问题](https://github.com/yanjun1688/Jarrett_Test/issues)
- 项目主页: [Jarrett_Test](https://github.com/yanjun1688/Jarrett_Test)
- 邮箱：hyanjun546@gmail.com

---

<a name="english"></a>
## Project Overview

JTest is an AI-powered intelligent test management platform built with Django + React, supporting API testing, UI automation testing, and test case management with deep AI integration.

## ✨ Key Features

### Test Management
- **API Testing** - RESTful API creation, execution, and assertions
- **UI Automation** - Playwright-based browser automation
- **Test Case Management** - Project-based test organization
- **Test Reports** - Automatic report generation

### AI Intelligence
- **Smart Chat** - Multi-LLM provider AI assistant
- **Test Generation** - AI-assisted test case generation
- **Intent Recognition** - Set theory-based intent classification
- **RAG Knowledge Base** - Retrieval-Augmented Generation

### Skill System
- **Extensible Skills** - Install and run skills from skills.sh
- **Custom Workflows** - Flexible skill orchestration

## 🏗️ Architecture

### Backend Stack
- Python 3.10+, Django 5.x, DRF
- Celery, Redis, ChromaDB
- Playwright

### Frontend Stack
- React 18, Ant Design

### AI/LLM Support
- OpenAI GPT, Anthropic Claude, DeepSeek, Zhipu GLM, Qwen

## 📁 Project Structure

```
JTest/
├── core/                    # Core modules (v2.0)
│   ├── agents/              # AI Agent system
│   └── tools/               # Testing tools
├── api/                     # RESTful API (v1)
├── testmanager_app/         # Main test management app
├── test_ui_app/             # UI testing app
├── shared/                  # Shared infrastructure
├── frontend/                # React frontend
└── testmanager/             # Django project config
```

## 📚 Documentation

| Module | Description | Link |
|--------|-------------|------|
| Core Agents | AI Agent System | [core/agents/README.md](core/agents/README.md) |
| Core Tools | Testing Tools | [core/tools/README.md](core/tools/README.md) |
| TestManager App | Test Management | [testmanager_app/README.md](testmanager_app/README.md) |

## 🚀 Quick Start

```bash
# Clone project
git clone https://github.com/yanjun1688/Jarrett_Test.git
cd JTest

# Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Setup database
python manage.py migrate
python manage.py createsuperuser

# Start services
python manage.py runserver &          # Backend
celery -A testmanager worker -l info & # Worker
cd frontend && npm start               # Frontend
```

## 🔌 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/projects/` | Project management |
| `/api/chatbot/chat/` | AI chat |
| `/api/skills/execute/` | Skill execution |
| `/api/sse/chatbot/` | SSE real-time push |

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 📬 Contact

- GitHub: [Jarrett_Test](https://github.com/yanjun1688/Jarrett_Test)
- Email: hyanjun546@gmail.com