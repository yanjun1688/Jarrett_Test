# Execution 模块 - 测试执行

## 概述

`execution` 模块负责测试用例的执行管理。目前该模块为预留扩展目录，测试执行功能由其他模块协作完成。

## 当前状态

该目录当前为空目录，测试执行功能通过以下方式实现：

1. **Tool 系统**: `core/tools/` 模块提供测试执行工具
2. **Flow 执行**: `core/flow/` 模块提供 FlowIR 执行引擎
3. **Agent 协作**: `ChatbotAgent` 和 `ToolOrchestrator` 协调执行

## 规划中的功能

未来版本计划在此模块实现：

- `test_execution_agent.py` - 测试执行 Agent
- `execution_engine.py` - 执行引擎
- `result_collector.py` - 结果收集器
- `parallel_executor.py` - 并行执行器

## 相关模块

### Tool 系统

测试执行工具位于 `core/tools/`：

- `execute_test.py` - 测试执行工具
- `execute_pending_tests.py` - 待执行测试工具
- `api_test_orchestrator.py` - API 测试编排

### Flow 执行

`core/flow/` 模块提供：

- `flow_executor.py` - FlowIR 执行器
- `node_executor.py` - 节点执行器

## 执行流程

当前测试执行流程：

```
用户请求
    │
    ▼
┌─────────────────┐
│  ChatbotAgent   │
│  意图分类       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ToolOrchestrator│
│ 工具路由        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ExecuteTest    │
│  执行工具       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FlowExecutor   │
│  流程执行       │
└────────┬────────┘
         │
         ▼
    执行结果
```

## 使用现有功能

### 通过 ChatbotAgent 执行

```python
result = await chatbot_agent.run({
    "message": "执行测试用例 123",
    "project_id": 1
})
```

### 通过 Tool 直接执行

```python
from core.tools.chatbot import ExecuteTestTool

tool = ExecuteTestTool()
result = await tool.execute(test_id=123)
```

### 通过 FlowIR 执行

```python
from core.flow import FlowExecutor

executor = FlowExecutor()
result = await executor.execute(flow_ir)
```

## 扩展指南

如需在此模块添加功能，建议遵循以下结构：

```
execution/
├── __init__.py
├── test_execution_agent.py   # 执行 Agent
├── execution_engine.py       # 执行引擎核心
├── result_collector.py       # 结果收集
├── parallel_executor.py      # 并行执行
├── retry_handler.py          # 重试处理
└── report_generator.py       # 报告生成
```

### TestExecutionAgent 设计

```python
class TestExecutionAgent(BaseAgent):
    """测试执行 Agent"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 解析执行请求
        # 2. 准备执行环境
        # 3. 执行测试
        # 4. 收集结果
        # 5. 生成报告
        pass
```

## 配置

执行相关配置在 `shared/constants.py`：

```python
class TimeConstants:
    DEFAULT_EXECUTION_TIMEOUT = 300  # 默认超时（秒）
    MAX_RETRY_COUNT = 3              # 最大重试次数
```

## 注意事项

1. 此目录为预留扩展目录
2. 添加新文件时需更新 `__init__.py`
3. 保持与其他模块的一致性
4. 添加适当的单元测试