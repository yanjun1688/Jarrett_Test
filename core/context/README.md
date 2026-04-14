# Context - 会话上下文存储模块

基于 Markdown 文件的会话上下文存储系统，为 Agent 对话提供持久化上下文管理。

## 概述

本模块实现了**文件系统级别**的会话上下文存储，核心设计原则：

- **人类可读**: 使用 Markdown 格式，便于调试和审计
- **确定性路径**: `user_id + session_id` 映射到唯一文件路径
- **并发安全**: 线程锁 + 文件锁双重保护
- **无状态服务**: 存储层无业务逻辑，纯 I/O 操作

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    ConversationService                       │
│                    (业务逻辑层)                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   MarkdownContextStore                       │
│                    (存储抽象层)                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API                                                 │   │
│  │  • create_session()                                  │   │
│  │  • get_context()                                     │   │
│  │  • append_message()                                  │   │
│  │  • update_context_state()                            │   │
│  │  • delete_context_fields()                           │   │
│  │  • get_user_sessions()                               │   │
│  │  • delete_session()                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  并发控制                                             │   │
│  │  • _get_thread_lock() - 线程锁 (LRU 缓存)            │   │
│  │  • _file_lock() - 文件锁 (跨进程)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  序列化                                              │   │
│  │  • _render_markdown() - SessionContext → Markdown   │   │
│  │  • _parse_markdown() - Markdown → SessionContext    │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     文件系统                                 │
│                                                             │
│  context_data/                                              │
│  ├── user_1/                                                │
│  │   ├── session-uuid-1.md                                  │
│  │   ├── session-uuid-2.md                                  │
│  │   └── archive/                                           │
│  │       └── 2024-01/                                       │
│  │           └── session-uuid-old.md                        │
│  └── user_2/                                                │
│      └── session-uuid-3.md                                  │
└─────────────────────────────────────────────────────────────┘
```

## 文件格式

每个会话存储为一个 Markdown 文件，格式如下：

```markdown
---
session_id: 550e8400-e29b-41d4-a716-446655440000
user_id: 1
project_id: 42
created_at: 2024-01-15T10:30:00
updated_at: 2024-01-15T11:45:00
message_count: 3
title: "生成登录测试"
---

## Messages

<!-- msg:user:2024-01-15T10:30:00 -->
帮我生成一个登录测试用例
<!-- metadata:{"intent": "generate_test"} -->
<!-- endmsg -->

<!-- msg:assistant:2024-01-15T10:30:05 -->
好的，我来为您生成登录测试用例...
<!-- endmsg -->

<!-- msg:user:2024-01-15T11:45:00 -->
执行这个测试
<!-- endmsg -->

## Context State

```yaml
last_intent: "execute_test"
pending_tests: {"script_id": 123, "tests": [...]}
last_action_time: "2024-01-15T11:45:00"
```
```

### 格式设计考量

| 设计 | 原因 |
|------|------|
| **YAML Frontmatter** | 存储会话元数据，标准格式，易于解析 |
| **HTML 注释包裹消息** | 防止消息内容中的 `---` 破坏 frontmatter 结构 |
| **YAML 代码块存状态** | 人类可读，支持复杂数据结构 |

## 核心组件

### SessionContext

会话上下文数据结构：

```python
@dataclass
class SessionContext:
    session_id: str                           # 会话唯一标识
    user_id: str                              # 用户 ID
    project_id: Optional[str] = None          # 项目 ID
    title: str = ""                           # 会话标题
    messages: List[Dict[str, Any]]            # 消息历史
    context_state: Dict[str, Any]             # 业务上下文状态
    metadata: Dict[str, Any]                  # 元数据
    created_at: str                           # 创建时间
    updated_at: str                           # 更新时间
```

### MarkdownContextStore

存储操作类：

```python
from core.context import MarkdownContextStore
from pathlib import Path

# 初始化
store = MarkdownContextStore(root_dir=Path("./context_data"))

# 创建会话
store.create_session(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="1",
    project_id="42",
    title="测试会话"
)

# 追加消息
store.append_message(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="1",
    role="user",
    content="帮我生成测试用例",
    metadata={"intent": "generate"}
)

# 获取上下文
context = store.get_context(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="1"
)

# 更新上下文状态
store.update_context_state(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="1",
    updates={"last_intent": "generate_test", "script_name": "login_test.py"}
)

# 删除上下文字段
store.delete_context_fields(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="1",
    fields=["pending_tests", "last_action_time"]
)

# 获取用户会话列表
sessions = store.get_user_sessions(user_id="1", limit=10)

# 删除会话 (软删除 -> 归档)
store.delete_session(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="1",
    hard_delete=False  # True 则彻底删除
)
```

## 并发控制

### 双重锁机制

```
┌─────────────────────────────────────────────┐
│              请求写入                         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│          线程锁 (threading.Lock)             │
│     同一进程内的多线程同步                    │
│     LRU 缓存，最多 100 个锁                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│          文件锁 (fcntl / msvcrt)             │
│     跨进程同步                               │
│     Windows: msvcrt.locking                 │
│     Unix: fcntl.flock                       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│              文件 I/O                        │
└─────────────────────────────────────────────┘
```

### 锁缓存 LRU

```python
# 防止内存泄漏
MAX_LOCKS_CACHE = 100

def _get_thread_lock(self, filepath: Path) -> threading.Lock:
    with self._locks_mutex:
        if len(self._thread_locks) >= self.MAX_LOCKS_CACHE:
            # 移除最旧的锁
            oldest_key = next(iter(self._thread_locks))
            del self._thread_locks[oldest_key]
        # 创建新锁
        self._thread_locks[key] = threading.Lock()
```

## API 参考

### create_session

创建新会话。

```python
def create_session(
    self,
    session_id: str,
    user_id: str,
    project_id: Optional[str] = None,
    title: Optional[str] = None
) -> bool
```

### get_context

获取会话上下文。

```python
def get_context(
    self,
    session_id: str,
    user_id: str
) -> Optional[Dict[str, Any]]
```

### append_message

追加消息到会话。

```python
def append_message(
    self,
    session_id: str,
    user_id: str,
    role: str,           # "user" | "assistant" | "system"
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool
```

### update_context_state

更新上下文状态。值 `None` 表示删除字段。

```python
def update_context_state(
    self,
    session_id: str,
    user_id: str,
    updates: Dict[str, Any]  # 值为 None 删除字段
) -> bool
```

### delete_context_fields

删除指定上下文字段。

```python
def delete_context_fields(
    self,
    session_id: str,
    user_id: str,
    fields: List[str]
) -> bool
```

### get_user_sessions

获取用户所有会话。

```python
def get_user_sessions(
    self,
    user_id: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]
```

### delete_session

删除会话。

```python
def delete_session(
    self,
    session_id: str,
    user_id: str,
    hard_delete: bool = False  # False 软删除到归档
) -> bool
```

## 与 ConversationService 集成

`ConversationService` 是业务层，`MarkdownContextStore` 是存储层：

```python
# ConversationService 内部使用 MarkdownContextStore

class ConversationService:
    @staticmethod
    def create_conversation(user: User, project_id: int = None):
        conversation_id = str(uuid.uuid4())
        
        # 创建 MySQL 记录 (索引)
        conversation = AgentConversation.objects.create(
            conversation_id=conversation_id,
            user=user,
            migrated_to_markdown=True
        )
        
        # 创建 Markdown 文件 (内容)
        md_store = get_markdown_store()
        md_store.create_session(
            session_id=conversation_id,
            user_id=str(user.id),
            project_id=str(project_id)
        )
        
        return conversation
```

## 设计决策

### 为什么选择 Markdown 而非数据库？

| 方面 | Markdown | 数据库 |
|------|----------|--------|
| **可读性** | 人类可直接查看 | 需要工具 |
| **调试** | 直接打开文件 | 需要 SQL |
| **备份** | 文件复制 | 导出/导入 |
| **版本控制** | Git 友好 | 不友好 |
| **扩展性** | 无 Schema 限制 | 需要 Migration |
| **查询性能** | 较慢 | 快 |
| **复杂查询** | 不支持 | 支持 |

**结论**: 对于会话消息存储，可读性和调试便利性更重要。

### 为什么需要 MySQL + Markdown 双存储？

```
MySQL (索引层):
├── 用户权限验证
├── 会话列表快速查询
├── 外键关联 (project, user)
└── 元数据快照

Markdown (内容层):
├── 消息历史 (可能很长)
├── 业务上下文状态
└── 无 Schema 限制的扩展数据
```

## 文件结构

```
core/context/
├── __init__.py           # 模块导出
├── markdown_store.py     # 核心存储实现
└── README.md             # 本文档

context_data/             # 数据目录 (默认)
├── user_1/
│   ├── session-uuid.md
│   └── archive/
│       └── 2024-01/
│           └── deleted-session.md
└── user_2/
    └── session-uuid.md
```

## 错误处理

所有方法在失败时返回 `False` 或 `None`，并记录日志：

```python
# 创建失败
success = store.create_session(...)
if not success:
    # 检查日志获取错误详情

# 会话不存在
context = store.get_context(...)
if context is None:
    # 会话不存在或解析失败
```

## 后续优化方向

### 1. 消息压缩

对于长对话，可压缩旧消息：

```python
def compress_old_messages(self, session_id: str, keep_last: int = 10):
    """压缩旧消息为摘要"""
    context = self.get_context(session_id)
    if len(context["messages"]) > keep_last:
        # 使用 LLM 生成摘要
        summary = summarize(context["messages"][:-keep_last])
        # 存储摘要，删除原消息
        ...
```

### 2. 增量写入

当前每次追加消息都需要重写整个文件，可优化为增量追加：

```python
def append_message_incremental(self, ...):
    """增量追加，避免重写整个文件"""
    with open(filepath, 'a') as f:
        f.write(f"<!-- msg:{role}:{timestamp} -->\n")
        f.write(f"{content}\n")
        f.write("<!-- endmsg -->\n")
```

### 3. 异步 I/O

支持异步文件操作：

```python
async def append_message_async(self, ...):
    """异步追加消息"""
    import aiofiles
    async with aiofiles.open(filepath, 'r') as f:
        ...
```

### 4. 加密存储

敏感数据加密：

```python
class EncryptedMarkdownStore(MarkdownContextStore):
    def _render_markdown(self, context: SessionContext) -> str:
        content = super()._render_markdown(context)
        return encrypt(content)
    
    def _parse_markdown(self, content: str) -> SessionContext:
        return super()._parse_markdown(decrypt(content))
```

### 5. 多后端支持

抽象存储接口，支持多种后端：

```python
class ContextStore(ABC):
    @abstractmethod
    def create_session(self, session_id: str, user_id: str) -> bool: ...
    
    @abstractmethod
    def get_context(self, session_id: str, user_id: str) -> Optional[Dict]: ...

class MarkdownContextStore(ContextStore): ...
class RedisContextStore(ContextStore): ...
class S3ContextStore(ContextStore): ...
```

## 参考

- [上下文存储设计文档](../../docs/context_markdown_storage_design_v2.md)
- [ConversationService 源码](../services/conversation_service.py)