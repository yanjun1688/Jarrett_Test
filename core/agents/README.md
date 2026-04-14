# Core Agents 模块

## 概述

`core/agents` 是 JTest 平台的核心 Agent 模块，提供测试规划、执行和知识检索的 Agent 抽象。该模块采用分层架构，包含基础 Agent 类、多个专业化 Agent 实现以及支持模块。

## 模块结构

```
core/agents/
├── __init__.py              # 模块入口，导出主要 Agent 类
├── base_agent.py            # Agent 基类，提供统一接口和生命周期管理
├── chatbot_agent.py         # 聊天机器人 Agent，处理自然语言对话
├── response_generator.py    # 响应生成器，生成 Agent 回复
├── skill_loader.py          # 技能加载器，管理技能系统
├── skill_registry.py        # 技能注册表，全局技能管理
├── skill_tool_adapter.py    # 技能-工具双向适配器
├── tool_orchestrator.py     # 工具编排器，管理工具执行
├── ui_test_agent.py         # UI 测试 Agent，生成 UI 测试脚本
├── ui_test.py               # UI 测试完整工作流
├── websocket_handler.py     # WebSocket 通信处理器
├── generation/              # 代码生成子模块
├── intent/                  # 意图分类子模块
├── llm/                     # LLM 服务子模块
├── planning/                # 测试规划子模块
├── rag/                     # 知识检索子模块
└── execution/               # 测试执行子模块
```

## 核心 Agent

### BaseAgent（基类）

所有 Agent 的抽象基类，提供：

- **生命周期管理**: `initialize()`, `execute()`, `cleanup()`
- **状态管理**: 状态追踪、历史记录、统计信息
- **异步上下文管理**: 支持 `async with` 语法
- **输入输出验证**: 可扩展的验证机制
- **工厂模式**: `AgentFactory` 支持动态注册和创建

```python
from core.agents import BaseAgent

class MyAgent(BaseAgent):
    async def initialize(self) -> None:
        # 初始化资源
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # 执行主要功能
        pass
    
    async def cleanup(self) -> None:
        # 清理资源
        pass
```

### ChatbotAgent

主要的聊天机器人 Agent，采用 ReAct 模式：

- **意图分类**: 使用规则 + LLM 双重分类
- **知识检索**: 集成 RAG 知识库
- **工具执行**: 支持多工具并发/顺序执行
- **技能系统**: 支持动态安装和运行技能

```python
from core.agents import ChatbotAgent

agent = ChatbotAgent(
    llm_service=llm_service,
    knowledge_rag_agent=rag_agent,
    tool_orchestrator=orchestrator
)

result = await agent.run({
    "message": "生成登录功能的测试用例",
    "project_id": 1
})
```

### TestPlanningAgent

统一的测试规划 Agent：

- **多类型支持**: UI、API、集成测试
- **自动检测**: 根据描述自动判断测试类型
- **RAG 增强**: 使用知识库增强规划质量
- **FlowIR 生成**: 生成可执行的测试流程

```python
from core.agents import TestPlanningAgent

agent = TestPlanningAgent(
    llm_service=llm_service,
    knowledge_rag_agent=rag_agent
)

result = await agent.plan(
    description="测试用户登录功能",
    test_type="ui"
)
```

### UITestAgent

UI 测试专用 Agent：

- **元素提取**: 使用 Playwright 提取页面元素
- **知识检索**: 检索历史测试案例
- **脚本生成**: 支持 pytest/playwright 格式

## 技能系统

### SkillLoader

技能加载器，负责：

- 扫描和加载技能目录
- 解析 YAML 配置文件
- 验证技能参数
- 执行技能并管理超时

```python
from core.agents.skill_loader import SkillLoader

loader = SkillLoader(skill_dir="skills")
await loader.load_skill("testcase-generator")
result = await loader.execute_skill("testcase-generator", **params)
```

### SkillRegistry

全局技能注册表，线程安全的技能管理：

```python
from core.agents.skill_registry import global_skill_registry

# 注册技能
global_skill_registry.register_skill(skill)

# 获取技能
skill = global_skill_registry.get_skill("skill_name")
```

### SkillAsToolAdapter / ToolAsSkillAdapter

双向适配器，实现技能与工具的互转：

```python
from core.agents.skill_tool_adapter import SkillAsToolAdapter

# 将技能包装为工具
tool = SkillAsToolAdapter(skill, "my_tool")
result = await tool.execute(**kwargs)
```

## 工具编排

### ToolOrchestrator

管理工具的注册和执行：

- **懒加载**: 按需加载工具
- **并发执行**: 支持多工具并发
- **参数验证**: Schema 验证
- **结果聚合**: 统一结果格式

```python
from core.agents.tool_orchestrator import ToolOrchestrator

orchestrator = ToolOrchestrator()
orchestrator.register_tool(tool)
result = await orchestrator.execute("tool_name", **params)
```

## WebSocket 支持

### WebSocketHandler

管理 WebSocket 连接和消息：

- 会话管理
- 消息路由
- 广播功能
- 自定义消息处理器

```python
from core.agents.websocket_handler import WebSocketHandler

handler = WebSocketHandler()
session_id = await handler.handle_connect(websocket)
await handler.broadcast_to_all({"type": "notification"})
```

## 设计原则

1. **单一职责**: 每个 Agent 专注于特定功能
2. **可组合性**: Agent 可组合使用
3. **可测试性**: 完整的依赖注入和 Mock 支持
4. **异步优先**: 所有 I/O 操作均为异步

## 子模块

- [generation/](./generation/README.md) - 测试代码生成
- [intent/](./intent/README.md) - 意图分类系统
- [llm/](./llm/README.md) - LLM 服务层
- [planning/](./planning/README.md) - 测试规划
- [rag/](./rag/README.md) - 知识检索
- [execution/](./execution/README.md) - 测试执行

## 使用示例

### 创建自定义 Agent

```python
from core.agents import BaseAgent

class CustomAgent(BaseAgent):
    async def initialize(self) -> None:
        self.update_state("ready")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._process(input_data)
        return {"success": True, "data": result}
    
    async def cleanup(self) -> None:
        pass

# 使用
async with CustomAgent() as agent:
    result = await agent.run({"input": "data"})
```

### 注册到工厂

```python
from core.agents.base_agent import AgentFactory

AgentFactory.register("custom", CustomAgent)
agent = AgentFactory.create("custom", config={...})
```

## 配置

Agent 配置通过 `core.config.settings` 管理，主要配置项：

- `LLM_TEMPERATURE`: LLM 温度参数
- `LLM_MAX_TOKENS`: 最大 Token 数
- `DEFAULT_TIMEOUT`: 默认超时时间