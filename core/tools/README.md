# Core Tools / 核心工具模块

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 概述

核心工具模块提供了一套完整的测试自动化工具框架，包括：

- **基础工具抽象** - 定义工具的标准接口和行为
- **API 测试工具** - HTTP 客户端和 API 测试编排
- **Chatbot 工具** - 与聊天机器人交互的工具集
- **测试生成工具** - 从 API 规范自动生成测试用例
- **验证工具** - API 响应验证和断言

## 目录结构

```
core/tools/
├── __init__.py              # 模块导出
├── base_tool.py             # 基础工具类和注册表
├── api/                     # API 相关工具
│   ├── __init__.py
│   └── http_client.py       # HTTP 客户端工具
├── chatbot/                 # 聊天机器人工具
│   ├── __init__.py
│   ├── generate_api_test_tool.py      # API 测试生成工具
│   ├── generate_ui_test_tool.py       # UI 测试生成工具
│   ├── execute_test_tool.py           # 测试执行工具
│   ├── execute_pending_tests_tool.py  # 待执行测试工具
│   ├── query_knowledge_tool.py        # 知识库查询工具
│   ├── install_skill_tool.py          # Skill 安装工具
│   └── run_skill_tool.py              # Skill 运行工具
├── execution/               # 执行相关工具
│   ├── __init__.py
│   └── api_test_orchestrator.py       # API 测试编排器
├── generation/              # 生成相关工具
│   ├── __init__.py
│   └── test_case_generator.py         # 测试用例生成器
├── validation/              # 验证相关工具
│   ├── __init__.py
│   └── response_validator.py          # 响应验证器
├── data/                    # 数据相关工具（预留）
└── ui/                      # UI 相关工具（预留）
```

## 核心组件

### BaseTool - 基础工具类

所有工具的抽象基类，提供：

- 统一的工具接口定义
- 参数验证机制
- 执行统计追踪
- 错误处理

```python
from core.tools.base_tool import BaseTool, ToolResult

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="工具描述",
            version="1.0.0",
            timeout=30
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        # 实现工具逻辑
        return ToolResult(success=True, data={})
```

### ToolResult - 工具执行结果

标准化的执行结果数据结构：

```python
@dataclass
class ToolResult:
    success: bool                    # 是否成功
    data: Dict[str, Any]            # 返回数据
    error: Optional[str] = None     # 错误信息
    execution_time: float = 0.0     # 执行时间
    metadata: Optional[Dict] = None # 元数据
```

### ToolRegistry - 工具注册表

管理工具的注册、查找和执行：

```python
from core.tools.base_tool import ToolRegistry

registry = ToolRegistry()
registry.register(my_tool)
tool = registry.get("my_tool")
result = await registry.execute("my_tool", param="value")
```

### LazyLoadingRegistry - 懒加载注册表

延迟加载工具，避免初始化时加载过多技能：

```python
from core.tools.base_tool import LazyLoadingRegistry

registry = LazyLoadingRegistry(max_tools=10)
registry.register(my_tool)
```

## 子模块说明

| 模块 | 说明 | 文档 |
|------|------|------|
| `api/` | HTTP 客户端工具 | [README](api/README.md) |
| `chatbot/` | 聊天机器人交互工具 | [README](chatbot/README.md) |
| `execution/` | 测试执行编排工具 | [README](execution/README.md) |
| `generation/` | 测试用例生成工具 | [README](generation/README.md) |
| `validation/` | 响应验证工具 | [README](validation/README.md) |

## 使用示例

### 创建自定义工具

```python
from core.tools.base_tool import BaseTool, ToolResult

class CustomValidator(BaseTool):
    def __init__(self):
        super().__init__(
            name="custom_validator",
            description="自定义验证器"
        )
    
    def _build_parameters_schema(self):
        return {
            "input": {"type": "string", "description": "输入数据"}
        }
    
    def _get_required_parameters(self):
        return ["input"]
    
    async def execute(self, **kwargs) -> ToolResult:
        input_data = kwargs.get("input")
        # 执行验证逻辑
        return ToolResult(success=True, data={"result": "valid"})
```

### 注册和使用工具

```python
from core.tools.base_tool import global_tool_registry

# 注册工具
global_tool_registry.register(CustomValidator())

# 执行工具
result = await global_tool_registry.execute(
    "custom_validator",
    input="test_data"
)
print(result.to_dict())
```

### 获取工具统计信息

```python
stats = tool.get_statistics()
# {
#     'name': 'my_tool',
#     'version': '1.0.0',
#     'execution_count': 10,
#     'error_count': 1,
#     'total_execution_time': 5.23,
#     'average_execution_time': 0.523,
#     'success_rate': 0.9
# }
```

## 工具状态枚举

```python
class ToolStatus(Enum):
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 执行中
    SUCCESS = "success"     # 执行成功
    FAILED = "failed"       # 执行失败
    TIMEOUT = "timeout"     # 执行超时
```

## 设计原则

1. **统一接口** - 所有工具继承自 BaseTool，保证接口一致性
2. **参数验证** - 使用 JSON Schema 进行参数验证
3. **异步执行** - 所有工具支持异步调用
4. **统计追踪** - 自动记录执行次数、时间和错误
5. **错误处理** - 统一的错误处理和返回格式

---

<a name="english"></a>
## Overview

The Core Tools module provides a comprehensive testing automation framework including:

- **Base Tool Abstraction** - Standard interface and behavior for all tools
- **API Testing Tools** - HTTP client and API test orchestration
- **Chatbot Tools** - Toolset for chatbot interactions
- **Test Generation Tools** - Auto-generate test cases from API specs
- **Validation Tools** - API response validation and assertions

## Key Components

### BaseTool

Abstract base class providing:
- Unified tool interface
- Parameter validation
- Execution statistics
- Error handling

### ToolResult

Standardized execution result with success status, data, error info, and execution time.

### ToolRegistry

Manages tool registration, lookup, and execution.

### LazyLoadingRegistry

Lazy-loading registry to avoid loading too many skills at initialization.

## Design Principles

1. **Unified Interface** - All tools inherit from BaseTool
2. **Parameter Validation** - JSON Schema based validation
3. **Async Execution** - All tools support async calls
4. **Statistics Tracking** - Automatic execution tracking
5. **Error Handling** - Unified error handling format