# Shared - 共享基础模块

跨模块共享的基础设施，包括常量定义、异常处理和工具函数。

## 概述

本模块提供项目级别的基础设施，遵循以下设计原则：

- **零依赖业务逻辑**: 纯工具性质，不包含业务代码
- **类型安全**: 所有函数都有类型注解
- **统一错误处理**: 标准化异常层次结构
- **可复用性**: 跨应用、跨模块共享

## 目录结构

```
shared/
├── __init__.py
├── constants.py        # 常量定义
├── exceptions.py       # 异常定义
└── utils/              # 工具函数
    ├── __init__.py
    ├── async_utils.py  # 异步工具
    ├── http_utils.py   # HTTP 请求工具
    ├── logging_utils.py # 日志工具
    ├── validation.py   # 验证工具
    └── command_utils.py # 命令行工具
```

## 模块详解

### 1. constants.py - 常量定义

集中管理项目所有常量，避免魔法字符串和数字。

```python
from shared.constants import TestType, NodeType, ExecutionStatus, DocType

# 测试类型
TestType.UI       # "ui"
TestType.API      # "api"
TestType.AUTO     # "auto"
TestType.is_valid("ui")  # True

# 节点类型
NodeType.UI_CLICK      # "ui_click"
NodeType.API_REQUEST   # "api_request"
NodeType.get_category("ui_click")  # "ui"

# 执行状态
ExecutionStatus.SUCCESS   # "success"
ExecutionStatus.FAILED    # "failed"
ExecutionStatus.is_completed("success")  # True

# 文档类型
DocType.KNOWLEDGE         # "knowledge"
DocType.is_valid("knowledge")  # True
```

#### 常量类列表

| 类名 | 用途 |
|------|------|
| `TestType` | 测试类型 (UI, API, Integration) |
| `NodeType` | 流程节点类型 |
| `ExecutionStatus` | 执行状态 |
| `DocType` | 文档类型 |

---

### 2. exceptions.py - 异常定义

统一的异常层次结构，所有异常继承自 `JTestError`。

```python
from shared.exceptions import (
    JTestError,
    ValidationError,
)

# 基础异常
raise JTestError("发生错误", code="INTERNAL_ERROR", details={"key": "value"})

# 验证错误
raise ValidationError("用户名不能为空", field="username")
```

#### 异常层次

```
JTestError (基类)
├── ValidationError         # 验证错误
├── ExternalServiceError    # 外部服务错误
│   └── RequestError        # HTTP 请求错误
└── IsolationViolation      # RAG 检索隔离违规
```

---

### 3. utils/async_utils.py - 异步工具

异步编程辅助函数。

```python
from shared.utils import run_async, batch_process, with_timeout, retry_async

# 在异步上下文中运行同步函数
result = await run_async(sync_function, arg1, arg2)

# 批量处理（支持并发控制）
results = await batch_process(
    items=[1, 2, 3, 4, 5],
    process_func=async_processor,
    batch_size=10,
    max_concurrent=5
)

# 超时控制
@with_timeout(5.0)
async def slow_operation():
    await asyncio.sleep(10)  # 会超时

# 重试机制
result = await retry_async(
    func=unstable_async_call,
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)

# 并行执行
results = await parallel_execute(
    task1(),
    task2(),
    task3(),
    max_concurrent=2
)

# 执行时间测量
result, duration = await measure_execution_time(some_coroutine())

# 异步队列
queue = AsyncQueue(maxsize=100)
await queue.put(item)
item = await queue.get()
await queue.process(process_func, num_workers=3)
```

---

### 4. utils/logging_utils.py - 日志工具

结构化日志和装饰器。

```python
from shared.utils import setup_logging, get_logger, log_execution_time

# 初始化日志
setup_logging(level="DEBUG", filename="app.log")

# 获取 logger
logger = get_logger(__name__)
logger.info("操作完成")

# 执行时间装饰器
@log_execution_time()
def slow_function():
    time.sleep(1)

# API 调用日志
@log_api_call
def api_view(request):
    return Response(data)

# 外部服务调用日志
@log_external_service_call("OpenAI")
def call_openai():
    ...
```

---

### 5. utils/http_utils.py - HTTP 工具

HTTP 请求相关函数。

```python
from shared.utils import make_http_request, validate_url, parse_headers, build_query_string

# 发送请求
response = make_http_request(
    method="POST",
    url="https://api.example.com/data",
    headers={"Content-Type": "application/json"},
    body={"key": "value"},
    timeout=30.0
)
# {
#     'status_code': 200,
#     'headers': {...},
#     'body': {...},
#     'content_type': 'json',
#     'elapsed': 0.123,
#     'success': True
# }

# URL 验证
validate_url("https://example.com")  # True

# 解析 headers 字符串
parse_headers("Content-Type: application/json\nAuthorization: Bearer token")
# {"Content-Type": "application/json", "Authorization": "Bearer token"}

# 构建查询字符串
build_query_string({"page": 1, "size": 10})  # "page=1&size=10"
```

---

### 6. utils/validation.py - 验证工具

数据验证函数。

```python
from shared.utils import validate_json_schema, validate_required_fields, validate_and_raise

# JSON Schema 验证
errors = validate_json_schema(data, schema)

# 必需字段检查
missing = validate_required_fields(data, ["name", "email"])

# 综合验证
validate_and_raise(data, {
    "name": {"required": True, "type": "string", "min_length": 1, "max_length": 100},
    "age": {"type": "integer", "min": 0, "max": 150},
    "email": {"required": True, "pattern": r'^[\w.-]+@[\w.-]+\.\w+$'},
    "status": {"enum": ["active", "inactive"]},
    "metadata": {"type": "object"},
    "tags": {"type": "array"}
})```

---

### 7. utils/command_utils.py - 命令行工具

跨平台命令检测。

```python
from shared.utils import get_npx_command, check_command_available

# 获取 npx 命令（跨平台）
npx_path = get_npx_command()  # Windows: npx.cmd, Linux: npx

# 检查命令是否可用
if check_command_available("python"):
    print("Python 已安装")
```

## 使用示例

### 完整工作流

```python
from shared.utils import get_logger, with_timeout, retry_async
from shared.exceptions import ValidationError
from shared.constants import ExecutionStatus

logger = get_logger(__name__)

@with_timeout(30.0)
async def process_test_case(case_id: str) -> dict:
    """处理测试用例"""
    logger.info(f"开始处理: {case_id}")
    
    try:
        # 验证
        if not case_id:
            raise ValidationError("case_id 不能为空")
        
        # 执行（带重试）
        result = await retry_async(
            lambda: execute_test(case_id),
            max_attempts=3,
            exceptions=(ConnectionError,)
        )
        
        logger.info(f"处理完成: {case_id}")
        return {"status": ExecutionStatus.SUCCESS, "result": result}
        
    except Exception as e:
        logger.error(f"处理失败: {case_id}", exc_info=True)
        raise
```

## 设计原则

### 1. 单一职责

每个模块只负责一类功能：

- `constants.py`: 只有常量定义
- `exceptions.py`: 只有异常类
- `utils/`: 每个工具文件只负责一类功能

### 2. 无业务依赖

共享模块不依赖任何业务模块，可独立使用：

```
shared/ ←── core/
          ←── testmanager_app/
          ←── test_ui_app/
```

### 3. 统一接口风格

- 所有函数都有类型注解
- 异常类继承统一基类
- 返回值格式一致

## 扩展指南

### 添加新常量

```python
# constants.py

class NewCategory:
    """新常量类别"""
    VALUE_A = "value_a"
    VALUE_B = "value_b"
    
    ALL = [VALUE_A, VALUE_B]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.ALL
```

### 添加新异常

```python
# exceptions.py

class NewFeatureError(JTestError):
    """新功能错误"""
    
    def __init__(self, message: str, feature: str, details: Optional[Dict] = None):
        details = details or {}
        details["feature"] = feature
        super().__init__(message, "NEW_FEATURE_ERROR", details)
```

### 添加新工具函数

```python
# utils/new_utils.py

def new_utility_function(param: str) -> str:
    """新工具函数"""
    ...

# utils/__init__.py
from .new_utils import new_utility_function

__all__ = [
    # ...existing exports...
    'new_utility_function'
]
```

## 参考

- [Python 类型注解](https://docs.python.org/3/library/typing.html)
- [JSON Schema](https://json-schema.org/)
- [Python Logging](https://docs.python.org/3/library/logging.html)