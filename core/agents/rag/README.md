# RAG 模块 - 知识检索

## 概述

RAG 检索系统采用 **双路混合检索 + RRF 融合** 架构：
- **向量检索**（ChromaDB + MiniLM）：找"意思接近的"——语义匹配
- **BM25 全文检索**（Whoosh + jieba）：找"字面匹配的"——关键词匹配
- **RRF 融合**：不依赖分数归一化，根据排名合并两路结果

```
                    ┌──→ ChromaDB 向量检索 ──→ 按语义排序
                    │       (384维 embedding)
用户查询 ──→ 分词 ──┤                              ├── RRF 融合 ──→ Top-K
                    │       (Whoosh + jieba)
                    └──→ BM25 全文检索 ──→ 按词频排序
```

## 模块结构

```
rag/
├── __init__.py                # 模块入口
├── knowledge_rag_agent.py     # 知识检索 Agent
├── rag_retriever_service.py   # RAG 检索器服务抽象
├── knowledge_retriever.py     # 核心检索（双路 + RRF + 监控打点）
├── embedding_service.py       # Embedding 服务（MiniLM，384维）
├── vector_store.py            # ChromaDB 向量存储
├── bm25_index.py              # BM25 索引（Whoosh + jieba分词）
├── chunker.py                 # 文档分块策略
└── rag_metrics.py             # 检索质量监控（RAGMetrics + Timer + 阈值）
```

## 核心组件

### Chunker

按文档类型自动选择分块策略：

| 策略 | 文档类型 | 说明 |
|------|---------|------|
| RecursiveStrategy | PRD | 按 `##` → `###` → 段落递归分割，chunk_size=512 |
| EndpointStrategy | API_DOC | 按每个 path+method 分割 |
| NoSplitStrategy | BEST_PRACTICE / TEST_PATTERN | 短文本整篇保留 |

数据模型约定：
```
KnowledgeDocument (MySQL)
├── chunk_index = -1     # 根文档（全文存 MySQL，不参与检索）
└── chroma_id_prefix     # "source_{pk}_"，关联 ChromaDB + BM25

ChromaDB + BM25
└── chunk_id = "source_{pk}_chunk_{index}"   # 对齐的 chunk ID
```

### KnowledgeRetriever

核心检索组件，实现双路 + RRF：

```python
from core.agents.rag import KnowledgeRetriever

retriever = KnowledgeRetriever()

results = retriever.search(
    query="支付超时取消订单",
    top_k=5,
    doc_types=["prd"],        # 按文档类型过滤
    project_id=1,             # 按项目过滤
    hybrid_search=True,       # 启用 BM25 + Vector 双路
)
```

### EmbeddingService

文本 Embedding 服务（进程级单例）：

```python
from core.agents.rag import EmbeddingService

embedding_service = EmbeddingService()
embedding = embedding_service.embed_query("测试文本")
embeddings = embedding_service.embed_texts(["文本1", "文本2"])
dim = embedding_service.dimension  # 384
```

### ChromaVectorStore

ChromaDB 向量存储封装（单集合 `kb_knowledge`）：

```python
from core.agents.rag import ChromaVectorStore

store = ChromaVectorStore()
store.add_documents(documents=[...], embeddings=[...], metadatas=[...], ids=[...])
results = store.query(query_embedding=[...], n_results=50, where={...})
store.delete_by_prefix("source_123_")
count = store.count()
```

### BM25Index

Whoosh BM25 全文索引（jieba 中文分词）：

```python
from core.agents.rag.bm25_index import BM25Index

idx = BM25Index()
idx.add_document(chunk_id="source_1_chunk_0", content="...", doc_type="prd")
results = idx.search("登录", top_k=50)
idx.delete_by_prefix("source_1_")
```

## 检索流程

### 写入

```
上传文档
  → MySQL: 存根文档（chunk_index=-1）
  → Chunker: 分块
  → 每个 chunk embedding → ChromaDB
  → 每个 chunk 分词 → Whoosh BM25
  → 更新 sync_status = 'synced'
```

### 查询

```
用户输入
  → embed_query → ChromaDB 搜 Top-50
  → 同时 jieba 分词 → BM25 搜 Top-50
  → RRF 融合：score = 1/(60 + rank_v) + 1/(60 + rank_b)
  → 返回 Top-K
```

### 删除

```
删除根文档
  → ChromaDB.delete_by_prefix("source_{pk}_")
  → BM25Index.delete_by_prefix("source_{pk}_")
  → MySQL 删根文档
```

## 配置

```python
# core/config.py
rag_enabled: bool = True
embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
chunk_size: int = 512
chunk_overlap: int = 50
top_k: int = 5

chromadb_path: str = "./data/chromadb"
chromadb_collection_name: str = "kb_knowledge"

bm25_index_path: str = "./data/bm25_index"
bm25_enabled: bool = True
bm25_top_k: int = 50
rrf_k: int = 60
```

## 检索模式

### 全局搜索

```python
results = retriever.search(query="登录功能", top_k=10)
```

### 类型过滤

```python
results = retriever.search(query="API测试", top_k=5, doc_types=["api_doc"])
```

### 知识库过滤

```python
results = retriever.search(query="测试规范", top_k=5, knowledge_base_id=1)
```

### 项目优先

```python
results = retriever.search(query="支付测试", top_k=5, project_id=1, boost_project=True)
```

## 知识库边界

知识库**仅存储知识型文档**，业务数据不应经过 RAG：

| 存入知识库 | 不存知识库 |
|-----------|-----------|
| PRD / 需求文档 | 功能测试用例（ORM 查询） |
| API 文档（OpenAPI） | API 测试用例（ORM 查询） |
| 最佳实践/规范 | UI 测试脚本（ORM 查询） |
| 测试模式/策略 | 执行记录/报告（ORM 查询） |
| 代码示例 | 项目/用户/配置（ORM 查询） |

## 实测效果

```
查询 "密码错误"           → BM25 关键词匹配 → 找到 API 测试规范
查询 "付款"               → 向量语义匹配    → 找到支付 PRD
查询 "银联"               → BM25 稀有词匹配 → 找到支付 PRD
查询 "压力测试并发指标"    → 双路都能命中     → RRF 融合排序
查询 "密码输错5次会锁定"   → 向量语义匹配    → 找到登录 PRD
查询 "支付超时取消订单"    → 双路互补        → RRF 融合排序
```

## 代码参考

- 分块器: `core/agents/rag/chunker.py`
- BM25 索引: `core/agents/rag/bm25_index.py`
- 核心检索: `core/agents/rag/knowledge_retriever.py`
- 同步任务: `core/tasks.py`
- 设计文档: `docs/rag-rebuild/`
