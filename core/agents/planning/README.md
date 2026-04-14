# Planning 模块 - 测试规划

## 概述

`planning` 模块提供统一的测试规划能力，支持多种测试类型（UI、API、集成测试）的流程生成。该模块将自然语言描述转换为可执行的测试流程（FlowIR）。

## 模块结构

```
planning/
└── test_planning_agent.py   # 测试规划 Agent
```

## TestPlanningAgent

统一的测试规划 Agent，负责：

- 解析自然语言测试需求
- 自动检测测试类型
- 生成 FlowIR 测试流程
- 集成 RAG 知识库增强规划

### 初始化

```python
from core.agents.planning import TestPlanningAgent

agent = TestPlanningAgent(
    llm_service=llm_service,
    rag_service=rag_service,
    knowledge_rag_agent=knowledge_agent
)
```

### 规划测试

```python
result = await agent.plan(
    description="测试用户登录功能，包括输入用户名密码、点击登录按钮、验证登录成功",
    test_type="ui",  # 可选: "ui", "api", "integration", "auto"
    additional_context={
        "url": "https://example.com/login",
        "element": "登录表单"
    },
    use_rag=True
)
```

## 测试类型

### UI 测试 (TestType.UI)

生成 UI 自动化测试流程：

```python
result = await agent.plan(
    description="测试购物车功能",
    test_type="ui"
)

# 生成的 FlowIR 包含:
# - ui_navigate: 导航节点
# - ui_click: 点击操作
# - ui_input: 输入操作
# - ui_assert: 断言验证
```

### API 测试 (TestType.API)

生成 API 测试流程：

```python
result = await agent.plan(
    description="测试用户注册接口",
    test_type="api",
    additional_context={
        "endpoint": "/api/users/register",
        "method": "POST"
    }
)

# 生成的 FlowIR 包含:
# - api_request: API 请求节点
# - api_validate: 响应验证节点
```

### 集成测试 (TestType.INTEGRATION)

生成集成测试流程：

```python
result = await agent.plan(
    description="测试订单完整流程",
    test_type="integration"
)

# 生成的 FlowIR 包含:
# - setup: 环境准备
# - execute: 执行步骤
# - cleanup: 环境清理
```

### 自动检测 (TestType.AUTO)

根据描述自动判断测试类型：

```python
result = await agent.plan(
    description="测试登录页面的按钮点击功能",  # 自动识别为 UI 测试
    test_type="auto"
)
```

## RAG 增强

### 使用知识库增强规划

```python
# 优先使用 KnowledgeRAGAgent 进行增强检索
result = await agent.plan(
    description="测试支付功能",
    test_type="api",
    use_rag=True
)

# 检索内容包括:
# - 相关文档
# - 最佳实践
# - 测试模式
# - 历史测试用例
```

### 检索流程

```
测试描述
    │
    ▼
┌─────────────────┐
│  KnowledgeRAG   │
│  Agent 检索      │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 文档    │ 最佳实践
    │ 测试模式 │ 历史用例
    └────┬────┘
         │
         ▼
┌─────────────────┐
│  构建 LLM 提示   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  生成 FlowIR    │
└─────────────────┘
```

## FlowIR 结构

生成的 FlowIR 包含：

```python
{
    "nodes": {
        "node_abc123": {
            "id": "node_abc123",
            "node_type": "ui_navigate",
            "parameters": {"url": "https://example.com"},
            "depends_on": [],
            "on_success": "node_def456",
            "metadata": {"name": "打开页面"}
        },
        "node_def456": {
            "id": "node_def456",
            "node_type": "ui_click",
            "parameters": {"selector": "button.submit"},
            "depends_on": ["node_abc123"],
            "on_success": "node_ghi789",
            "metadata": {"name": "点击提交"}
        }
    },
    "start_node": "node_abc123",
    "metadata": {
        "name": "测试流程",
        "test_type": "ui",
        "description": "...",
        "generated_by": "test_planning_agent"
    }
}
```

## 输出格式

```python
{
    "success": True,
    "flow_ir": {...},           # FlowIR 字典
    "validation": {             # 验证结果
        "valid": True,
        "errors": [],
        "warnings": []
    },
    "test_type": "ui",          # 实际测试类型
    "planning_stats": {         # 规划统计
        "total_plans": 10,
        "successful_plans": 9,
        "ui_plans": 5,
        "api_plans": 4
    },
    "agent_id": "agent_xxx"
}
```

## 高级功能

### 规划优化

```python
result = await agent.refine_plan(
    flow_ir=existing_flow_ir,
    feedback="增加异常处理步骤",
    additional_context={...}
)
```

### 获取统计信息

```python
stats = agent.get_planning_statistics()
# {
#     "total_plans": 100,
#     "successful_plans": 95,
#     "success_rate": 0.95,
#     "ui_plans": 50,
#     "api_plans": 30,
#     "integration_plans": 20
# }
```

### 获取能力描述

```python
capabilities = agent.get_capabilities()
# {
#     "planning_types": ["ui", "api", "integration", "auto"],
#     "supports_rag": True,
#     "supports_llm": True,
#     "max_nodes_per_flow": 50,
#     "available_node_types": [...]
# }
```

## 节点类型

| 类型 | 描述 | 参数示例 |
|------|------|----------|
| ui_navigate | 导航到页面 | `{"url": "..."}` |
| ui_click | 点击元素 | `{"selector": "..."}` |
| ui_input | 输入文本 | `{"selector": "...", "value": "..."}` |
| ui_assert | 断言验证 | `{"selector": "...", "expected_text": "..."}` |
| api_request | API 请求 | `{"method": "POST", "url": "..."}` |
| api_validate | 响应验证 | `{"status_code": 200, "schema": {...}}` |
| setup | 环境准备 | `{"environment": "test"}` |
| execute | 执行操作 | `{"steps": [...]}` |
| cleanup | 环境清理 | `{"remove_data": True}` |

## 配置

```python
DEFAULT_CONFIG = {
    "default_test_type": "auto",
    "use_rag": True,
    "validate_output": True,
    "timeout": 60,
    "max_retries": 3
}
```

## 错误处理

```python
from shared.exceptions import PlanningError, ValidationError

try:
    result = await agent.plan(description="...")
except ValidationError as e:
    # 输入验证失败
    print(f"验证错误: {e.details}")
except PlanningError as e:
    # 规划过程失败
    print(f"规划错误: {e}")
```

## 使用示例

### 完整流程

```python
async with TestPlanningAgent(
    llm_service=llm_service,
    knowledge_rag_agent=rag_agent
) as agent:
    # 规划测试
    result = await agent.plan(
        description="测试用户注册流程",
        test_type="ui"
    )
    
    if result["success"]:
        flow_ir = result["flow_ir"]
        # 执行 FlowIR
        # ...
```

### 与其他 Agent 协作

```python
# 1. 规划测试
planning_result = await planning_agent.plan(...)

# 2. 生成代码
generation_result = await generation_agent.generate_test_code(
    test_case=planning_result["flow_ir"],
    framework="pytest"
)

# 3. 执行测试
execution_result = await execution_agent.execute(
    flow_ir=planning_result["flow_ir"]
)
```