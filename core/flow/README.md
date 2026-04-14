# Flow Engine - 测试流程编排引擎

基于中间表示 (IR) 架构的测试流程编排引擎，支持 Agent 生成的测试流程的解析、验证和执行。

## 概述

Flow Engine 是一个**编译时与运行时分离**的流程引擎，核心设计思想：

- **FlowIR**: 流程的中间表示，描述节点结构和控制流
- **ExecutionEngine**: 执行引擎，编排节点执行顺序和状态管理
- **NodeFactory**: IR 到运行时的转换层
- **TestNodeRegistry**: 节点类型注册中心

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent 生成的测试流程                           │
│                      (JSON / YAML 格式)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FlowIR 层                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FlowIR                                                   │   │
│  │  ├── nodes: Dict[str, FlowNodeIR]                        │   │
│  │  ├── start_node: str                                      │   │
│  │  └── metadata: Dict                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FlowNodeIR                                               │   │
│  │  ├── id: str                    # 节点唯一标识            │   │
│  │  ├── node_type: str             # 节点类型                │   │
│  │  ├── parameters: Dict           # 节点参数                │   │
│  │  ├── depends_on: List[str]      # 数据依赖                │   │
│  │  ├── on_success: str | None     # 成功跳转                │   │
│  │  ├── on_failure: str | None     # 失败跳转                │   │
│  │  └── condition: str | None      # 执行条件                │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      转换层 (NodeFactory)                        │
│                                                                 │
│   FlowNodeIR ──────► BaseTestNode 实例                          │
│   (编译时表示)         (运行时执行器)                             │
│                                                                 │
│   职责:                                                         │
│   • 从 Registry 获取节点执行器类                                  │
│   • 验证节点参数                                                  │
│   • 创建节点实例                                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    执行层 (ExecutionEngine)                      │
│                                                                 │
│   执行流程:                                                      │
│   1. 验证流程 (循环依赖、孤立节点)                                 │
│   2. 从 start_node 开始执行                                      │
│   3. 根据节点结果决定跳转:                                        │
│      • SUCCESS → on_success                                     │
│      • FAILED  → on_failure                                     │
│      • None    → 结束                                           │
│   4. 收集执行指标                                                │
│   5. 触发事件回调                                                │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. FlowIR (`flow_ir.py`)

流程中间表示，Agent 操作的核心数据结构。

```python
from core.flow import FlowIR, FlowNodeIR

# 创建节点
node1 = FlowNodeIR(
    id="login",
    node_type="ui_action",
    parameters={"action": "click", "selector": "#login-btn"},
    on_success="verify_dashboard"
)

node2 = FlowNodeIR(
    id="verify_dashboard",
    node_type="assertion",
    parameters={"expected": "Dashboard"},
    depends_on=["login"]
)

# 组装流程
flow = FlowIR(
    nodes={"login": node1, "verify_dashboard": node2},
    start_node="login",
    metadata={"name": "Login Test", "test_type": "ui"}
)

# 验证
result = flow.validate()
# {"errors": [], "warnings": []}
```

### 2. ExecutionEngine (`execution_engine.py`)

执行引擎，编排节点执行。

```python
from core.flow import ExecutionEngine, global_node_registry

engine = ExecutionEngine(registry=global_node_registry)

# 设置事件回调
engine.on_node_start = lambda e: print(f"开始: {e['node_id']}")
engine.on_node_complete = lambda e: print(f"完成: {e['node_id']}")

# 执行流程
result = await engine.run(flow, context={"env": "staging"})
```

### 3. NodeFactory (`node_factory.py`)

IR 到运行时的转换工厂。

```python
from core.flow import NodeFactory, global_node_registry

factory = NodeFactory(registry=global_node_registry)

# 创建单个节点
node_instance = factory.create_node(ir_node)

# 批量创建
instances = factory.create_nodes_batch(flow.nodes)

# 验证节点类型
validation = factory.validate_node("ui_action", {"action": "click"})
```

### 4. TestNodeRegistry (`test_node_registry.py`)

节点类型注册中心。

```python
from core.flow import TestNodeRegistry, NodeSpec, ParameterSpec

registry = TestNodeRegistry()

# 定义节点规格
spec = NodeSpec(
    node_type="ui_action",
    name="UI Action",
    description="执行 UI 操作",
    category="ui",
    inputs=[
        ParameterSpec(name="action", type="string", required=True),
        ParameterSpec(name="selector", type="string", required=True),
        ParameterSpec(name="value", type="string", required=False)
    ]
)

# 注册节点
registry.register(spec, UIActionNode)

# 查询节点
node_class = registry.get_node_class("ui_action")
node_spec = registry.get_node_spec("ui_action")
```

## 控制流

### 顺序执行

```
[A] ──on_success──► [B] ──on_success──► [C] ──None──► 结束
```

### 条件分支

```
                    ┌──on_success──► [成功处理]
[A] ──执行结果──►
                    └──on_failure──► [失败处理]
```

### 依赖等待

```python
# 节点 C 等待 A 和 B 都完成
node_c = FlowNodeIR(
    id="c",
    node_type="merge",
    depends_on=["a", "b"]  # 必须等待 a, b 完成
)
```

### 条件执行

```python
# 仅当 ${skip_login} 为 false 时执行
node = FlowNodeIR(
    id="login",
    node_type="ui_action",
    condition="${skip_login}",  # 条件变量
    parameters={"action": "login"}
)
```

## 验证机制

FlowIR 提供多层验证：

```python
result = flow.validate(strict=True)
# {
#     "errors": [...],    # 必须修复的问题
#     "warnings": [...]   # 可选修复的问题
# }
```

**验证项**:
- 节点 ID 有效性
- 起始节点存在性
- 依赖引用完整性
- 跳转目标存在性
- 循环依赖检测
- 孤立节点警告

## 执行指标

```python
from core.flow import FlowExecutionMetrics, NodeExecutionResult

# 执行结果包含完整指标
result = await engine.run(flow)

# 节点级指标
for node_id, node_result in result["node_results"].items():
    print(f"{node_id}: {node_result['status']} ({node_result['duration']:.2f}s)")

# 流程级指标
metrics = result["metrics"]
print(f"总节点: {metrics['total_nodes']}")
print(f"成功: {metrics['successful_nodes']}")
print(f"失败: {metrics['failed_nodes']}")
print(f"跳过: {metrics['skipped_nodes']}")
```

## 节点开发规范

节点执行器需实现以下接口：

```python
class BaseTestNode:
    # 类属性
    NODE_TYPE: str = "custom_node"
    NODE_NAME: str = "Custom Node"
    NODE_DESCRIPTION: str = "Description"
    NODE_CATEGORY: str = "custom"
    DEFAULT_TIMEOUT: int = 30
    SUPPORTS_RETRY: bool = True
    PARAMETERS_SCHEMA: Dict = {}
    
    def __init__(self, node_id: str, parameters: Dict[str, Any]):
        self.node_id = node_id
        self.parameters = parameters
    
    async def execute(
        self, 
        parameters: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行节点
        
        Returns:
            {
                "output": Any,           # 输出数据
                "metadata": Dict,        # 执行元数据
                "context_updates": Dict  # 上下文更新
            }
        """
        return {"output": None, "metadata": {}, "context_updates": {}}
```

## 文件结构

```
core/flow/
├── __init__.py              # 模块导出
├── flow_ir.py               # 流程中间表示
├── node_spec.py             # 节点规格定义
├── node_factory.py          # 节点工厂
├── test_node_registry.py    # 节点注册表
├── execution_engine.py      # 执行引擎
├── execution_metrics.py     # 执行指标
└── nodes/                   # 内置节点 (待实现)
    ├── __init__.py
    ├── ui_action.py
    ├── api_request.py
    ├── assertion.py
    └── ...
```

## 与 Agent 集成

Agent 生成的测试用例可转换为 FlowIR：

```python
# Agent 生成的测试步骤
agent_output = {
    "steps": [
        {"action": "click", "selector": "#login", "name": "点击登录"},
        {"action": "input", "selector": "#username", "value": "admin"},
        {"action": "assert", "expected": "Dashboard"}
    ]
}

# 转换为 FlowIR
def agent_output_to_flow(steps: List[Dict]) -> FlowIR:
    nodes = {}
    prev_id = None
    
    for i, step in enumerate(steps):
        node_id = f"step_{i}"
        node = FlowNodeIR(
            id=node_id,
            node_type=f"ui_{step['action']}",
            parameters=step,
            on_success=f"step_{i+1}" if i < len(steps) - 1 else None
        )
        nodes[node_id] = node
        prev_id = node_id
    
    return FlowIR(
        nodes=nodes,
        start_node="step_0",
        metadata={"source": "agent"}
    )
```

## 后续兼容功能

### 1. 可视化流程编辑器

- 拖拽式节点编排
- 实时预览执行路径
- 流程模板库

### 2. 并行执行

```python
# 当前: 顺序执行
# 未来: 支持并行分支

flow = FlowIR(
    nodes={
        "parallel_start": FlowNodeIR(
            id="parallel_start",
            node_type="parallel",
            branches=["branch_a", "branch_b"]  # 并行分支
        ),
        "branch_a": FlowNodeIR(...),
        "branch_b": FlowNodeIR(...),
        "parallel_end": FlowNodeIR(
            id="parallel_end",
            node_type="join",
            depends_on=["branch_a", "branch_b"]
        )
    }
)
```

### 3. 子流程调用

```python
# 支持流程嵌套
node = FlowNodeIR(
    id="subflow_call",
    node_type="call_subflow",
    parameters={
        "flow_id": "login_flow",
        "inputs": {"username": "${user}"}
    }
)
```

### 4. 循环结构

```python
# 支持循环迭代
node = FlowNodeIR(
    id="iterate_items",
    node_type="foreach",
    parameters={
        "iterator": "${items}",
        "body_node": "process_item"
    }
)
```

### 5. 断点与调试

- 节点断点暂停
- 单步执行
- 变量实时查看
- 执行回放

### 6. 流程版本管理

- 流程快照
- 变更历史
- 回滚机制
- A/B 测试

### 7. 分布式执行

- 节点分片到多个 Worker
- 跨服务节点调用
- 执行状态同步

## 展望

### 短期目标

1. **完善内置节点库**: 实现 UI 操作、API 请求、断言等常用节点
2. **Agent 集成**: 与 Chatbot Agent 深度集成，支持自然语言生成测试流程
3. **测试覆盖率**: 补充单元测试和集成测试

### 中期目标

1. **可视化编辑器**: 提供图形化流程设计界面
2. **并行执行引擎**: 支持并行分支，提升执行效率
3. **流程市场**: 共享和复用测试流程模板

### 长期愿景

1. **智能优化**: 基于执行历史自动优化流程
2. **自愈能力**: 失败节点自动重试或降级
3. **跨平台执行**: 支持云端、本地、混合执行环境

## 参考

- [流程设计文档](../../docs/flow_design.md)
- [节点开发指南](../../docs/node_development.md)
- [API 参考](../../docs/flow_api.md)