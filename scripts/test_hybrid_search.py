"""
Test hybrid search: Chunker + BM25 + Vector + RRF.
Tests the full pipeline with realistic knowledge content.
"""
from __future__ import annotations

import sys
import os
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

from core.agents.rag.chunker import Chunker
from core.agents.rag.bm25_index import BM25Index
from core.agents.rag.embedding_service import EmbeddingService
from core.agents.rag.vector_store import ChromaVectorStore
from core.agents.rag.knowledge_retriever import KnowledgeRetriever
from core.config import settings


TEST_PREFIX = 'test_hybrid_'


def clean():
    """Clean test data from both stores."""
    ChromaVectorStore().delete_by_prefix(TEST_PREFIX)
    BM25Index().delete_by_prefix(TEST_PREFIX)


def add_chunk(chunk_id: str, content: str, doc_type: str = 'prd', title: str = ''):
    """Add a chunk to both BM25 and ChromaDB."""
    embedder = EmbeddingService()
    vector_store = ChromaVectorStore()
    bm25 = BM25Index()

    # Vector
    embedding = embedder.embed_query(content)
    vector_store.add_documents(
        documents=[content],
        embeddings=[embedding],
        metadatas=[{
            'chroma_id_prefix': TEST_PREFIX,
            'doc_type': doc_type,
            'title': title,
        }],
        ids=[chunk_id],
    )

    # BM25
    bm25.add_document(
        chunk_id=chunk_id,
        content=content,
        doc_type=doc_type,
        title=title,
    )


def search(query: str, top_k: int = 5) -> list:
    """Hybrid search via retriever."""
    retriever = KnowledgeRetriever()
    return retriever.search(query, top_k=top_k)


def print_results(query: str, results: list):
    print(f'\nQuery: "{query}" → {len(results)} results')
    for i, r in enumerate(results):
        meta = r.get('metadata', {})
        rrf = r.get('rrf_score', 0)
        dist = r.get('distance', 0)
        content = (r.get('content') or '')[:80]
        print(f'  [{i+1}] rrf={rrf:.3f} dist={dist:.3f} {content}...')


# ═══════════════════════════════════════════════
#  Test data: realistic knowledge base content
# ═══════════════════════════════════════════════

DOCS = [
    # ── PRD: 登录模块 ──
    {
        'id': f'{TEST_PREFIX}prd_login',
        'content': '''
## 用户登录功能

### 手机号密码登录
用户通过输入已注册的手机号和密码进行登录。
密码需要满足复杂度要求：8-20位，包含大小写字母和数字。
连续输错密码5次后，账号将被锁定30分钟。

### 短信验证码登录
用户可以选择短信验证码登录方式。
验证码有效期为5分钟，每天最多发送10次。
支持国内所有运营商手机号。

### 第三方登录
支持微信扫码登录和支付宝授权登录。
首次第三方登录需要绑定已有手机号。
''',
        'doc_type': 'prd',
        'title': '用户登录模块PRD',
    },
    # ── PRD: 支付模块 ──
    {
        'id': f'{TEST_PREFIX}prd_payment',
        'content': '''
## 支付功能需求

### 支付方式
支持支付宝支付、微信支付和银联支付三种方式。
用户可以在账户设置中调整支付方式的默认排序。

### 支付流程
用户在订单确认页选择支付方式后点击「去支付」。
调用第三方支付SDK唤起支付页面。
支付成功后跳转到订单详情页。

### 超时处理
支付超时时间为30分钟。
超时后订单自动取消，库存释放。
已用的优惠券和积分退回用户账户。
''',
        'doc_type': 'prd',
        'title': '支付模块PRD',
    },
    # ── Best Practice: 测试规范 ──
    {
        'id': f'{TEST_PREFIX}bp_api_test',
        'content': '''
## API接口测试规范

### 覆盖场景
每个API接口需要覆盖以下三类场景：
1. 正常场景：正确的参数输入，验证返回200和正确响应体
2. 异常场景：缺失参数、错误格式、无效token，验证返回4xx
3. 边界场景：参数最大值、最小值、空值、特殊字符

### 断言要求
- 状态码断言必须精确匹配
- 响应体字段类型必须校验
- 数组类型需要验证length
- 嵌套对象需要递归校验

### 用例命名
格式: [模块]_[接口名]_[场景]
示例: 登录_密码登录_密码错误
''',
        'doc_type': 'best_practice',
        'title': 'API测试规范',
    },
    # ── Best Practice: 压测规范 ──
    {
        'id': f'{TEST_PREFIX}bp_perf',
        'content': '''
## 性能测试规范

### 压力测试场景
1. 基准测试：单用户稳定运行，确认功能正常
2. 负载测试：逐步增加并发到目标值，观察性能拐点
3. 压力测试：超过目标负载30%，验证系统不会崩溃
4. 稳定性测试：80%负载持续运行24小时，观察有无内存泄漏

### 指标要求
- 接口响应时间 P95 < 500ms
- 接口响应时间 P99 < 1000ms
- 错误率 < 0.1%
- CPU使用率 < 70%
- 内存占用 < 80%

### 报告模板
测试报告需要包含：测试环境、场景描述、并发数、TPS、
响应时间分布、错误率、资源使用率、结论与建议。
''',
        'doc_type': 'best_practice',
        'title': '性能测试规范',
    },
    # ── Best Practice: 安全测试 ──
    {
        'id': f'{TEST_PREFIX}bp_security',
        'content': '''
## 安全测试规范

### 认证安全
- 密码传输必须使用HTTPS加密
- JWT Token必须设置过期时间，不超过24小时
- 刷新Token机制，access_token过期后自动续期
- 登录失败次数限制，防止暴力破解

### 接口安全
- 敏感接口需要添加签名校验
- 防重放攻击，请求中添加nonce和timestamp
- SQL注入防护，所有参数必须参数化查询
- XSS防护，输出内容需要转义

### 数据安全
- 用户密码必须使用bcrypt加密存储
- 手机号、身份证等敏感信息需要脱敏展示
- 日志中不能打印密码和Token
''',
        'doc_type': 'best_practice',
        'title': '安全测试规范',
    },
    # ── API_DOC: 用户接口文档 ──
    {
        'id': f'{TEST_PREFIX}api_user',
        'content': """# 用户服务API

## POST /api/v1/user/login
登录接口
- Content-Type: application/json
- Body: {phone, password}
- Response: {token, user_info}
- 错误码: 4001=密码错误, 4002=账号锁定, 4003=验证码错误

## POST /api/v1/user/register
注册接口
- Body: {phone, password, code}
- Response: {user_id, token}

## GET /api/v1/user/info
获取用户信息
- Header: Authorization: Bearer {token}
- Response: {nickname, avatar, phone_mask}""",
        'doc_type': 'api_doc',
        'title': '用户服务API文档',
    },
    # ── API_DOC: 订单接口文档 ──
    {
        'id': f'{TEST_PREFIX}api_order',
        'content': """# 订单服务API

## POST /api/v1/order/create
创建订单
- Body: {items, address_id, coupon_id}
- Response: {order_id, total_amount, status}

## GET /api/v1/order/list
订单列表
- Params: {page, size, status}
- Response: {orders[], total, page}

## POST /api/v1/order/cancel
取消订单
- Body: {order_id, reason}
- Note: 已支付的订单取消后触发退款流程""",
        'doc_type': 'api_doc',
        'title': '订单服务API文档',
    },
]


def run_tests():
    print('=' * 65)
    print('  Hybrid Search Test Suite: BM25 + Vector + RRF')
    print('=' * 65)

    # Setup: clean and add docs
    clean()
    print(f'\nAdding {len(DOCS)} documents...')
    for doc in DOCS:
        add_chunk(doc['id'], doc['content'], doc['doc_type'], doc['title'])
    print(f'BM25 index count: {BM25Index().count()}')
    print(f'ChromaDB collection count: {ChromaVectorStore().count()}')

    # ══════════════════════════════════════
    # Test 1: Exact keyword match (BM25 strength)
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 1: Exact keyword match')
    print('  Query: "密码错误"')
    print('-' * 65)
    r = search('密码错误', top_k=3)
    print_results('密码错误', r)
    # Should find: api_user (error_code 4001), login PRD, security BP
    assert any('4001' in (x.get('content') or '') for x in r), 'Should match password error'

    # ══════════════════════════════════════
    # Test 2: Short query (BM25 strong)
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 2: Short query - "登录"')
    print('-' * 65)
    r = search('登录', top_k=3)
    print_results('登录', r)
    assert any('登录' in (x.get('content') or '') for x in r), 'Login should match'

    # ══════════════════════════════════════
    # Test 3: Semantic match (Vector strength)
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 3: Semantic match')
    print('  Query: "付款" (should find payment PRD)')
    print('-' * 65)
    r = search('付款', top_k=3)
    print_results('付款', r)
    assert any('支付' in (x.get('content') or '') for x in r), 'Should match payment content'

    # ══════════════════════════════════════
    # Test 4: Complex multi-word query
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 4: Complex multi-word query')
    print('  Query: "压力测试并发指标响应时间")')
    print('-' * 65)
    r = search('压力测试并发指标响应时间', top_k=3)
    print_results('压力测试并发指标响应时间', r)
    assert any('压力' in (x.get('content') or '') for x in r), 'Should match perf test'

    # ══════════════════════════════════════
    # Test 5: Mixed Chinese + English
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 5: Mixed Chinese + English')
    print('  Query: "API登录接口文档"')
    print('-' * 65)
    r = search('API登录接口文档', top_k=3)
    print_results('API登录接口文档', r)
    # Should find user API doc or login PRD
    assert len(r) > 0, 'Should find something'

    # ══════════════════════════════════════
    # Test 6: Long query (full sentence)
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 6: Long query (full sentence)')
    print('  Query: "用户密码连续输错5次后账号会被锁定吗"')
    print('-' * 65)
    r = search('用户密码连续输错5次后账号会被锁定吗', top_k=3)
    print_results('用户密码连续输错5次后账号会被锁定吗', r)
    assert any('锁定' in (x.get('content') or '') for x in r), 'Should find account lock info'

    # ══════════════════════════════════════
    # Test 7: RRF fusion test - query that BM25 and Vector rank differently
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 7: RRF fusion effect')
    print('  Query: "支付超时取消订单"')
    print('-' * 65)
    r = search('支付超时取消订单', top_k=3)
    print_results('支付超时取消订单', r)
    # Both payment PRD and order API are relevant
    assert len(r) >= 2, 'RRF should merge both BM25 and vector results'

    # ══════════════════════════════════════
    # Test 8: Empty / irrelevant query
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 8: Irrelevant query')
    print('  Query: "今天天气怎么样"')
    print('-' * 65)
    r = search('今天天气怎么样', top_k=3)
    print_results('今天天气怎么样', r)
    # Should return some results anyway (low scores), not crash
    print('  (no crash → pass)')

    # ══════════════════════════════════════
    # Test 9: Filter by doc_type
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 9: Filter by doc_type (api_doc only)')
    print('  Query: "创建订单"')
    print('-' * 65)
    retriever = KnowledgeRetriever()
    r = retriever.search('创建订单', top_k=5, doc_types=['api_doc'])
    print_results('创建订单 (filtered: api_doc)', r)
    for item in r:
        dt = item.get('metadata', {}).get('doc_type', '')
        assert dt == 'api_doc', f'Expected api_doc, got {dt}'
    print('  All results are api_doc → pass')

    # ══════════════════════════════════════
    # Test 10: BM25-only results (doc exists in BM25 but not covered by vector)
    # ══════════════════════════════════════
    print('\n' + '-' * 65)
    print('  Test 10: BM25 catches keyword match')
    print('  Query: "银联" (specific payment term)')
    print('-' * 65)
    r = search('银联', top_k=3)
    print_results('银联', r)
    assert any('银联' in (x.get('content') or '') for x in r), 'Should find union pay mention'

    print('\n' + '=' * 65)
    print('  All tests passed!')
    print('=' * 65)

    # Cleanup
    clean()
    print('Test data cleaned up.')


if __name__ == '__main__':
    run_tests()
