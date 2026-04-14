# RAG 模块 - 知识检索

## 概述

`rag` 模块提供检索增强生成（RAG）能力，用于知识库的存储、检索和管理。结合向量数据库和 Embedding 模型实现语义搜索。

## 模块结构

```
rag/
├── __init__.py                # 模块入口
├── knowledge_rag_agent.py     # 知识检索 Agent
├── rag_retriever_service.py   # RAG 检索器服务抽象
├── knowledge_retriever.py     # 知识检索核心组件
├── embedding_service.py       # Embedding 服务
└── vector_store.py            # ChromaDB 向量存储
```

## 核心组件

### KnowledgeRAGAgent

知识检索 Agent，提供高级检索接口：

```python
from core.agents.rag import KnowledgeRAGAgent

agent = KnowledgeRAGAgent(
    llm_service=llm_service,
    rag_retriever=retriever
)

# 查询知识库
result = await agent.query(
    query="如何编写好的单元测试？",
    top_k=5,
    use_llm=True  # 使用 LLM 生成答案
)
```

### KnowledgeRetriever

核心检索组件，结合 Embedding 和向量存储：

```python
from core.agents.rag import KnowledgeRetriever

retriever = KnowledgeRetriever()

# 添加文档
retriever.add_document(
    content="测试驱动开发是一种开发方法...",
    metadata={"type": "article", "project_id": 1},
    doc_id="doc_001"
)

# 批量添加
retriever.add_documents_batch(
    contents=[...],
    metadatas=[...],
    doc_ids=[...]
)

# 搜索
results = retriever.search(
    query="TDD 最佳实践",
    top_k=5,
    doc_types=["article"],
    project_id=1,
    boost_project=True  # 优先返回项目内文档
)
```

### EmbeddingService

文本 Embedding 服务，单例模式：

```python
from core.agents.rag import EmbeddingService

embedding_service = EmbeddingService()

# 生成单个 Embedding
embedding = embedding_service.embed_query("测试文本")

# 批量生成
embeddings = embedding_service.embed_texts(["文本1", "文本2"])

# 获取维度
dim = embedding_service.dimension  # 如 384, 768 等
```

### ChromaVectorStore

ChromaDB 向量存储封装：

```python
from core.agents.rag import ChromaVectorStore

store = ChromaVectorStore()

# 添加文档
store.add_documents(
    documents=["文档内容1", "文档内容2"],
    embeddings=[[0.1, ...], [0.2, ...]],
    metadatas=[{"type": "article"}, {"type": "code"}],
    ids=["id1", "id2"]
)

# 查询
results = store.query(
    query_embedding=[0.1, 0.2, ...],
    n_results=5,
    where={"type": "article"}  # 元数据过滤
)

# 删除
store.delete(ids=["id1"])
store.delete_by_prefix("doc_123_")  # 批量删除

# 统计
count = store.count()
```

## RAGRetriever 抽象

便于依赖注入的抽象接口：

```python
from core.agents.rag import RAGRetriever, DjangoORMRAGRetriever

# 抽象基类
class CustomRetriever(RAGRetriever):
    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        # 自定义实现
        pass

# Django ORM 实现
retriever = DjangoORMRAGRetriever(
    project_id=1,
    knowledge_base_id=1
)

# Mock 实现（测试用）
from core.agents.rag.rag_retriever_service import MockRAGRetriever
mock_retriever = MockRAGRetriever(mock_results=[...])
```

## 使用场景

### 通用查询

```python
result = await agent.query(
    query="什么是测试金字塔？",
    top_k=5,
    use_llm=True
)

# 返回:
# {
#     "success": True,
#     "answer": "测试金字塔是...",
#     "documents": [...],
#     "metadata": {"retrieved_count": 5}
# }
```

### 按类型查询

```python
# 查询最佳实践
result = await agent.get_best_practices(
    topic="API testing",
    top_k=5
)

# 查询测试模式
result = await agent.get_test_patterns(
    scenario="用户认证",
    top_k=5
)

# 查询代码示例
result = await agent.get_code_examples(
    description="pytest fixture",
    language="python",
    top_k=3
)
```

### 历史测试用例检索

```python
# API 测试用例
result = await agent.get_api_test_cases(
    endpoint="/api/users",
    method="POST",
    top_k=5
)

# UI 测试用例
result = await agent.get_ui_test_cases(
    page_url="https://example.com/login",
    page_element="登录按钮",
    top_k=5
)
```

### UI 元素管理

```python
# 存储页面元素
result = await agent.store_ui_elements(
    page_url="https://example.com/login",
    elements=[
        {"id": "username", "selector": "#username", "tag": "input"},
        {"id": "password", "selector": "#password", "tag": "input"},
        {"id": "submit", "selector": "button[type=submit]", "tag": "button"}
    ],
    metadata={"page_title": "登录页面"}
)

# 查询页面元素
result = await agent.query_ui_elements(
    page_url="https://example.com/login",
    element_type="button",
    top_k=10
)
```

## 配置

### Django Settings

```python
# settings.py
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMADB_PATH = "data/chromadb"
CHROMADB_COLLECTION_NAME = "kb_knowledge"
```

### 环境变量

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMADB_PATH=./data/chromadb
```

## 数据模型

### 文档结构

```python
{
    "id": "doc_abc123",
    "content": "文档内容...",
    "metadata": {
        "doc_type": "article",      # 文档类型
        "project_id": 1,            # 项目 ID
        "file_path": "/path/to/file",
        "created_at": "2024-01-01",
        "source": "upload",
        # ... 其他元数据
    }
}
```

### 检索结果

```python
{
    "id": "doc_abc123",
    "content": "匹配的文档内容...",
    "metadata": {...},
    "distance": 0.15,           # 向量距离（越小越相似）
    "combined_score": 0.85      # 综合分数（越高越相关）
}
```

## 检索模式

### 全局搜索

```python
results = retriever.search(
    query="测试最佳实践",
    top_k=10
)
```

### 类型过滤

```python
results = retriever.search(
    query="API 测试",
    top_k=5,
    doc_types=["article", "code"]
)
```

### 项目优先

```python
results = retriever.search(
    query="登录测试",
    top_k=5,
    project_id=1,
    boost_project=True  # 项目内结果排在前面
)
```

## 线程安全

### EmbeddingService

使用 `threading.Lock` 保证单例初始化的线程安全：

```python
class EmbeddingService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
```

### ChromaVectorStore

使用 `threading.local()` 隔离线程：

```python
class ChromaVectorStore:
    _local = threading.local()
    
    @classmethod
    def get_client(cls):
        if not hasattr(cls._local, 'client'):
            cls._local.client = chromadb.PersistentClient(...)
        return cls._local.client
```

## 最佳实践

1. **批量操作**: 使用 `add_documents_batch` 提高效率
2. **元数据设计**: 合理设计元数据便于过滤
3. **项目隔离**: 使用 `project_id` 实现多租户
4. **缓存策略**: 对频繁查询实现缓存

## 错误处理

```python
try:
    result = await agent.query(query="...")
except Exception as e:
    logger.error(f"检索失败: {e}")
    return {
        "success": False,
        "answer": "",
        "documents": [],
        "error": str(e)
    }
```

## 测试

```python
# 使用 Mock RAG Retriever
from core.agents.rag.rag_retriever_service import MockRAGRetriever

mock_retriever = MockRAGRetriever(
    mock_results=[
        {"document": "测试内容", "metadata": {"type": "article"}}
    ]
)

agent = KnowledgeRAGAgent(rag_retriever=mock_retriever)
```