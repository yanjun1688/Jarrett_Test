# JTest - AI驱动的智能测试管理平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Django-5.2.6-green.svg" alt="Django">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

JTest 是一个基于 Django + React 的智能化测试管理平台，深度融合 AI Agent 技术，支持 API 测试、UI 自动化测试、性能测试等功能。通过模块化 Agent 架构和技能系统，让测试工作更高效、更智能。

## 核心功能

### 测试管理
- **API 测试** - RESTful API 的创建、执行、断言和报告
- **UI 自动化测试** - 基于 Playwright 的浏览器录制和执行
- **性能测试** - 压力测试和并发性能评估
- **测试集合** - 批量执行、链式执行和变量传递

### AI 智能
- **智能对话** - 多 LLM 提供商（OpenAI/Claude/DeepSeek/GLM/Qwen）
- **测试生成** - AI 辅助生成 API/UI 测试用例和脚本
- **意图识别** - 基于集合论的智能意图分类系统
- **RAG 知识库** - 检索增强生成，提供测试最佳实践

### 技能系统
- **可扩展技能** - 支持动态安装和执行测试技能
- **自定义工作流** - 灵活的技能编排和执行
- **Agent 编排** - 多 Agent 协同完成复杂测试任务

## 技术架构

### 后端
- **Python 3.11+** - 主要开发语言
- **Django 5.2.6** - Web 框架
- **Django REST Framework** - RESTful API
- **Celery** - 异步任务处理
- **Redis** - 缓存和消息队列
- **ChromaDB** - 向量数据库（RAG）
- **Playwright** - UI 自动化测试

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
│   │   ├── planning/             # 测试规划 Agent
│   │   ├── execution/            # 执行 Agent
│   │   ├── rag/                  # RAG 知识库 Agent
│   │   └── llm/                  # LLM 服务层
│   └── tools/                     # 测试工具库
│       ├── api/                   # HTTP 客户端
│       ├── chatbot/              # Chatbot 工具
│       ├── execution/            # 执行编排
│       ├── generation/           # 测试生成
│       ├── ui/                   # UI 测试工具
│       └── validation/           # 响应验证
│
├── api/v1/                        # RESTful API
├── testmanager_app/              # API 测试管理应用
│   ├── models.py                 # 数据模型
│   ├── viewsets/                 # API 视图集
│   ├── services/                 # 业务服务
│   └── chatbots/                 # AI 对话
│
├── test_ui_app/                  # UI 测试应用
│   ├── recording/                # 录制功能
│   ├── execution/                # 执行引擎
│   └── playwright_engine.py      # Playwright 引擎
│
├── test_ai_agent/                # AI Agent 应用
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── features/            # 功能模块
│   │   ├── components/          # 组件
│   │   ├── api/                 # API 封装
│   │   └── hooks/               # React Hooks
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
python manage.py createsuperuser
```

6. **安装前端依赖**
```bash
cd frontend
npm install
```

### 启动服务

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

## 使用示例

### API 测试

1. 创建项目 → 添加 API 请求
2. 配置请求参数（URL、方法、Headers、Body）
3. 添加断言规则（状态码、JSON Path 等）
4. 执行测试并查看报告

### UI 自动化测试

1. 录制浏览器操作
2. 编辑生成的测试脚本
3. 配置执行环境
4. 运行测试并查看结果

### AI 对话

```
用户: 帮我生成 /api/login 接口的测试用例

AI: 好的，我来为您生成 /api/login 接口的测试用例：

1. POST /api/login - 正向测试（有效凭据）
2. POST /api/login - 边界测试（空用户名）
3. POST /api/login - 异常测试（错误密码）
...

是否立即执行这些测试用例？
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
```

## API 文档

主要 API 端点：

| 端点 | 说明 |
|------|------|
| `/api/projects/` | 项目管理 |
| `/api/modules/` | 模块管理 |
| `/api/testcases/` | 测试用例 |
| `/api/api-requests/` | API 请求 |
| `/api/request-collections/` | 请求集合 |
| `/api/executions/` | 执行记录 |
| `/api/chatbot/chat/` | AI 对话 |
| `/api/skills/` | 技能管理 |

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
