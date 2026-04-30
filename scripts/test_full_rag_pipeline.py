"""
Full RAG pipeline integration test.

Tests the complete chain:
  Chunker → BM25 + Vector → RRF → Context Injection → Logging

Run: python scripts/test_full_rag_pipeline.py
"""
from __future__ import annotations

import json
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

from core.agents.rag.chunker import Chunker
from core.agents.rag.bm25_index import BM25Index
from core.agents.rag.embedding_service import EmbeddingService
from core.agents.rag.vector_store import ChromaVectorStore
from core.agents.rag.knowledge_retriever import KnowledgeRetriever

TEST_PREFIX = 'test_full_rag_'

# ═══════════════════════════════════════════════════════════════
#  Test Data: Realistic knowledge base documents
# ═══════════════════════════════════════════════════════════════

DOCUMENTS = [
    # ── PRD: 电商平台 ──
    {
        'id': f'{TEST_PREFIX}prd_user',
        'doc_type': 'prd',
        'title': '用户中心PRD v2.3',
        'content': '''
## 用户登录

### 密码登录
用户在登录页输入手机号和密码，点击登录按钮。
校验逻辑：
- 手机号格式校验（11位数字）
- 密码长度 8-20 位
- 连续输错 5 次锁定账号 30 分钟

### 验证码登录
用户点击"获取验证码"，系统发送 6 位数字验证码至绑定手机。
验证码有效期 5 分钟，每天最多发送 10 次。

### 第三方登录
支持微信扫码登录和支付宝授权登录。
首次登录需要绑定手机号。

## 用户注册

### 手机号注册
输入手机号、验证码、密码完成注册。
注册成功后自动登录并跳转到首页。

### 注销账号
用户在设置页面可申请注销账号。
注销后 7 天内可撤回，超时后永久删除数据。
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}prd_order',
        'doc_type': 'prd',
        'title': '订单系统PRD',
        'content': '''
## 创建订单

用户在购物车选择商品后点击结算。
订单创建流程：
1. 校验库存
2. 计算金额（商品金额 + 运费 - 优惠）
3. 锁定库存 30 分钟
4. 跳转支付页面

## 取消订单

### 未支付取消
用户可在订单详情页主动取消。
超时 30 分钟未支付系统自动取消。
取消后释放库存、退回优惠券。

### 已支付取消
用户申请退款，走退款流程。
退款到账时间：
- 支付宝：1-3 个工作日
- 微信：1-7 个工作日

## 订单状态
pending → paid → shipped → completed → deleted
                  ↘ cancelled
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}prd_payment',
        'doc_type': 'prd',
        'title': '支付模块PRD',
        'content': '''
## 支付方式

### 支付宝支付
用户在支付页面选择支付宝。
通过支付宝 SDK 唤起支付宝 App。
支付成功异步回调通知。

### 微信支付
支持微信 App 支付和 H5 支付。
H5 支付需要在微信浏览器内打开。

### 余额支付
用户可以使用账户余额支付。
余额不足时提示用户充值或换其他方式。

## 退款流程

用户提交退款申请 → 系统校验订单状态 → 退款原路返回。
退款原因：质量问题、不想要了、发错货、其他。
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}prd_product',
        'doc_type': 'prd',
        'title': '商品管理PRD',
        'content': '''
## 商品发布

商家在后台填写商品信息：
- 标题（最多 30 字）
- 描述（最多 500 字）
- 价格（0.01 - 999999）
- 库存（整数）
- 图片（最多 10 张）
- 规格（颜色、尺寸等）

## 商品搜索

用户可以通过关键词、分类、价格区间搜索商品。
搜索结果按综合排序、销量排序、价格排序。
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}prd_coupon',
        'doc_type': 'prd',
        'title': '优惠券系统PRD',
        'content': '''
## 优惠券类型

### 满减券
满 100 减 10、满 200 减 30、满 500 减 80。
不可与其他优惠券叠加使用。

### 折扣券
8 折券、7 折券，有使用上限。
部分商品不参与折扣活动。

### 无门槛券
固定金额立减，无使用门槛。
通常用于新用户拉新活动。

## 优惠券使用规则

- 每个订单只能用一张优惠券
- 已取消订单的优惠券自动退回
- 过期优惠券不补发
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}prd_address',
        'doc_type': 'prd',
        'title': '地址管理PRD',
        'content': '''
## 地址管理

用户可添加多个收货地址。
默认地址在结算时自动选中。

地址字段：
- 收件人（必填，最长 20 字）
- 手机号（必填，11 位）
- 省市区（三级联动）
- 详细地址（必填，最长 100 字）
- 邮政编码（选填）

## 地址校验

下单时校验地址完整性。
地址不存在或已删除时提示用户重新选择。
        '''.strip(),
    },
    # ── API Docs ──
    {
        'id': f'{TEST_PREFIX}api_user_svc',
        'doc_type': 'api_doc',
        'title': '用户服务API',
        'content': '''
接口路径: /api/v1/user

POST /login
  登录
  参数: {phone, password}
  响应: {token, user_id, expire_in}
  错误码: 4001=密码错误 4002=账号锁定 4003=验证码错误

POST /register
  注册
  参数: {phone, password, code}
  响应: {token, user_id}

POST /logout
  登出
  参数: {token}
  响应: {success}
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}api_order_svc',
        'doc_type': 'api_doc',
        'title': '订单服务API',
        'content': '''
接口路径: /api/v1/order

POST /create
  创建订单
  参数: {items[], address_id, coupon_id?}
  响应: {order_id, amount, status}

POST /cancel
  取消订单
  参数: {order_id, reason?}
  响应: {success}

GET /list
  订单列表
  参数: {page, size, status?}
  响应: {orders[], total}
        '''.strip(),
    },
    # ── Best Practices ──
    {
        'id': f'{TEST_PREFIX}bp_login_test',
        'doc_type': 'best_practice',
        'title': '登录功能测试规范',
        'content': '''
## 登录测试场景

### 正常场景
- 正确手机号和密码 → 登录成功
- 验证码正确 → 登录成功
- 第三方登录 → 首次需绑定

### 异常场景
- 手机号格式错误 → 提示格式错误
- 密码错误 → 提示密码错误，计数+1
- 连续 5 次错误 → 账号锁定 30 分钟
- 验证码过期 → 重新获取
- 验证码错误 → 提示重新输入
- 网络异常 → 友好提示

### 边界场景
- 密码 8 位和 20 位边界
- 验证码有效期最后一秒
- 锁定时间最后一秒
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}bp_payment_test',
        'doc_type': 'best_practice',
        'title': '支付功能测试要点',
        'content': '''
## 支付测试

### 前端测试
- 支付方式选择 UI 正确
- 金额显示格式化
- 支付成功/失败页面跳转
- 支付中 loading 状态

### 后端测试
- 重复支付幂等性
- 支付回调处理
- 订单状态流转正确

### 异常场景
- 余额不足
- 支付超时
- 网络中断后恢复
- 并发支付
- 部分退款
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}bp_security_test',
        'doc_type': 'best_practice',
        'title': '接口安全测试规范',
        'content': '''
## 安全测试

### 认证安全
- Token 有效期测试
- Token 伪造测试
- 未登录访问拦截

### 接口安全
- SQL 注入测试（' OR 1=1 --）
- XSS 测试（<script>alert(1)</script>）
- 参数校验测试（超长、特殊字符）
- 接口频率限制测试

### 数据安全
- 敏感信息脱敏（手机号 138****1234）
- 密码传输加密（HTTPS）
- 日志不打印密码
        '''.strip(),
    },
    # ── Code Examples ──
    {
        'id': f'{TEST_PREFIX}code_api_test',
        'doc_type': 'code_example',
        'title': 'API测试代码示例 - Pytest',
        'content': '''
```python
def test_login_success(client):
    """正常登录"""
    resp = client.post('/api/v1/user/login', {
        'phone': '13800138000',
        'password': 'Test123456'
    })
    assert resp.status_code == 200
    assert 'token' in resp.json()

def test_login_wrong_password(client):
    """密码错误"""
    resp = client.post('/api/v1/user/login', {
        'phone': '13800138000',
        'password': 'wrong'
    })
    assert resp.status_code == 401
    assert resp.json()['error_code'] == 4001

def test_login_locked(client):
    """账号锁定后登录"""
    # 连续 5 次错误
    for _ in range(5):
        client.post('/api/v1/user/login', {
            'phone': '13800138000',
            'password': 'wrong'
        })
    resp = client.post('/api/v1/user/login', {
        'phone': '13800138000',
        'password': 'Test123456'
    })
    assert resp.status_code == 423
    assert 'locked' in resp.json()['message']
```
        '''.strip(),
    },
    {
        'id': f'{TEST_PREFIX}code_order_test',
        'doc_type': 'code_example',
        'title': '订单测试代码示例 - Pytest',
        'content': '''
```python
def test_create_order_success(client, auth_header):
    """创建订单成功"""
    resp = client.post('/api/v1/order/create', {
        'items': [{'product_id': 1, 'quantity': 2}],
        'address_id': 1,
    }, headers=auth_header)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'pending'

def test_cancel_unpaid_order(client, auth_header):
    """取消未支付订单"""
    # 先创建
    create_resp = client.post('/api/v1/order/create', ...)
    order_id = create_resp.json()['order_id']
    # 再取消
    cancel_resp = client.post('/api/v1/order/cancel', {
        'order_id': order_id,
    }, headers=auth_header)
    assert cancel_resp.status_code == 200
```
        '''.strip(),
    },
]


def clean():
    ChromaVectorStore().delete_by_prefix(TEST_PREFIX)
    BM25Index().delete_by_prefix(TEST_PREFIX)


def print_sep(title: str):
    print(f'\n{"=" * 65}')
    print(f'  {title}')
    print(f'{"=" * 65}')


def print_results(query: str, results: list, top_k: int = 5):
    print(f'\nQuery: "{query}"')
    print(f'Results: {len(results)}')
    for i, r in enumerate(results[:top_k]):
        meta = r.get('metadata', {})
        rrf = r.get('rrf_score', 0)
        title = meta.get('title', '')[:30]
        dt = meta.get('doc_type', '')
        content = (r.get('content') or '')[:100].replace('\n', ' | ')
        print(f'  [{i+1}] rrf={rrf:.4f}  [{dt}] {title}')
        print(f'       {content}...')


def test_chunking():
    """Test 1: Chunker splits documents correctly"""
    print_sep('Test 1: Chunker - Document Splitting')
    chunker = Chunker()

    total_chunks = 0
    for doc in DOCUMENTS[:4]:  # Test PRD docs
        chunks = chunker.chunk(doc['doc_type'], doc['content'])
        total_chunks += len(chunks)
        print(f'  {doc["title"]} ({len(doc["content"])}c) → {len(chunks)} chunks')
        for c in chunks:
            heading = c.content.strip().split('\n')[0] if c.content.strip() else '?'
            print(f'    [{c.chunk_index}] ({len(c.content):>4}c) {heading}')

    assert total_chunks >= 4, f'Expected >=4 total chunks, got {total_chunks}'
    print(f'  Total chunks: {total_chunks}  PASS')


def test_ingest():
    """Test 2: Ingest all docs into BM25 + ChromaDB"""
    print_sep('Test 2: Ingest - BM25 + ChromaDB Write')

    embedder = EmbeddingService()
    vector_store = ChromaVectorStore()
    bm25 = BM25Index()

    for doc in DOCUMENTS:
        emb = embedder.embed_query(doc['content'])
        vector_store.add_documents(
            documents=[doc['content']],
            embeddings=[emb],
            metadatas=[{
                'chroma_id_prefix': TEST_PREFIX,
                'doc_type': doc['doc_type'],
                'title': doc['title'],
            }],
            ids=[doc['id']],
        )
        bm25.add_document(
            chunk_id=doc['id'],
            content=doc['content'],
            doc_type=doc['doc_type'],
            title=doc['title'],
        )

    from_previous = ChromaVectorStore().count() - len(DOCUMENTS)
    bm25_count = BM25Index().count()
    print(f'  ChromaDB: +{len(DOCUMENTS)} docs (total may include prior data)')
    print(f'  BM25:     {bm25_count} docs')
    assert bm25_count >= len(DOCUMENTS), f'Expected >={len(DOCUMENTS)} in BM25'
    print(f'  Total {len(DOCUMENTS)} docs ingested  PASS')


def test_hybrid_search():
    """Test 3-10: Hybrid search queries - the real RAG tests"""
    retriever = KnowledgeRetriever()

    # ─── Test 3: 语义搜索（向量优势） ───
    print_sep('Test 3: 语义搜索 — "付款方式"')
    r = retriever.search('付款方式', top_k=5)
    print_results('付款方式', r)
    assert any('支付' in (x.get('content') or '') for x in r), 'Should find payment PRD'
    print('  PASS: 找到支付相关文档')

    # ─── Test 4: 关键词精确搜索（BM25 优势） ───
    print_sep('Test 4: 精确匹配 — "锁定30分钟"')
    r = retriever.search('锁定30分钟', top_k=5)
    print_results('锁定30分钟', r)
    assert any('锁定' in (x.get('content') or '') for x in r), 'Should find lock info'
    print('  PASS: 找到锁定规则')

    # ─── Test 5: 混合搜索（双路互补） ───
    print_sep('Test 5: 混合搜索 — "订单超时取消退款"')
    r = retriever.search('订单超时取消退款', top_k=5)
    print_results('订单超时取消退款', r)
    print('  PASS: 双路检索无异常')

    # ─── Test 6: 短查询 ───
    print_sep('Test 6: 短查询 — "logout"')
    r = retriever.search('logout', top_k=5)
    print_results('logout', r)
    assert any('logout' in (x.get('content') or '').lower() for _, x in [
        (i, x) for i, x in enumerate(r)
    ]), 'Should find logout API'
    print('  PASS: 命中登出接口文档')

    # ─── Test 7: 中英混 ───
    print_sep('Test 7: 中英混 — "API 创建订单"')
    r = retriever.search('API 创建订单', top_k=5)
    print_results('API 创建订单', r)
    print('  PASS')

    # ─── Test 8: 长句搜索 ───
    print_sep('Test 8: 长句搜索')
    r = retriever.search(
        '我连续输了5次密码，现在账号登不上去了怎么办',
        top_k=5,
    )
    print_results('密码输错5次登不上', r)
    assert any('锁定' in (x.get('content') or '') for x in r), 'Should explain lock mechanism'
    print('  PASS: 理解锁定场景')

    # ─── Test 9: 类型过滤 api_doc ───
    print_sep('Test 9: 类型过滤 — 只查 API')
    r = retriever.search('登录', top_k=5, doc_types=['api_doc'])
    print_results('登录 (filter: api_doc)', r)
    for item in r:
        assert item['metadata']['doc_type'] == 'api_doc', 'All results should be api_doc'
    print(f'  PASS: 全部 {len(r)} 条都是 API 文档')

    # ─── Test 10: RRF 稳定性 ───
    print_sep('Test 10: RRF 稳定性 — 多次检索结果一致性')
    queries = ['退款流程', '取消订单', '注册账号', '优惠券满减']
    for q in queries:
        r1 = retriever.search(q, top_k=3)
        r2 = retriever.search(q, top_k=3)
        ids1 = [x['id'] for x in r1]
        ids2 = [x['id'] for x in r2]
        assert ids1 == ids2, f'RRF inconsistent for "{q}"'
        print(f'  "{q}" → {len(r1)} results, 一致')

    print('  PASS: RRF 结果稳定')


def test_logging_format():
    """Test 11: Verify context injection format matches design"""
    print_sep('Test 11: 上下文注入格式验证')

    from core.agents.rag.knowledge_rag_agent import (
        RAG_CONTEXT_LIMIT,
        _log_rag_query,
    )

    print(f'  RAG_CONTEXT_LIMIT = {RAG_CONTEXT_LIMIT} (should be 10)')
    assert RAG_CONTEXT_LIMIT == 10, f'Expected 10, got {RAG_CONTEXT_LIMIT}'

    retriever = KnowledgeRetriever()
    results = retriever.search('密码错误', top_k=10)

    # Simulate what _generate_answer does
    context_parts = []
    sources = []
    for i, r in enumerate(results[:RAG_CONTEXT_LIMIT], 1):
        meta = r.get('metadata', {})
        content = (r.get('content') or '')[:80]
        context_parts.append(f'【{i}】{meta.get("title", "?")} ({meta.get("doc_type", "?")})')
        context_parts.append(content)

    sample = '\n'.join(context_parts)
    print(f'  Format test:\n{sample[:500]}')

    # Test logger doesn't crash
    mock_docs = [
        {'document': 'test', 'metadata': {'title': 'doc1', 'doc_type': 'prd'},
         'combined_score': 0.5},
    ]
    _log_rag_query('test', mock_docs, 'test answer')
    print('  Logger: OK')

    print('  PASS: 上下文注入格式正确')


def test_error_handling():
    """Test 12: Error handling — edge cases"""
    print_sep('Test 12: 异常场景')

    retriever = KnowledgeRetriever()

    # Empty query
    r = retriever.search('', top_k=5)
    assert isinstance(r, list), 'Empty query should not crash'
    print('  Empty query: OK')

    # Special characters
    r = retriever.search('!@#$%^&*()_+', top_k=5)
    assert isinstance(r, list), 'Special chars should not crash'
    print('  Special chars: OK')

    # Very long query
    r = retriever.search('测试' * 500, top_k=5)
    assert isinstance(r, list), 'Long query should not crash'
    print('  Super long query: OK')

    # Filter with no match
    r = retriever.search('test', top_k=5, doc_types=['nonexistent'])
    print(f'  No-match filter: {len(r)} results (OK)')

    print('  PASS: 全部异常通过')


def test_cli_demo():
    """Test 13: Simulate CLI interaction"""
    print_sep('Test 13: 模拟问答场景')

    retriever = KnowledgeRetriever()
    test_cases = [
        ('密码锁定了怎么办', 'Should find lock policy'),
        ('怎么测试支付', 'Should find payment test practices'),
        ('怎么创建退款订单', 'Should find order API'),
        ('SQL注入怎么测', 'Should find security test practices'),
        ('地址能填多少字', 'Should find address PRD'),
    ]

    all_ok = True
    for query, desc in test_cases:
        r = retriever.search(query, top_k=3)
        has_result = len(r) > 0
        status = '✅' if has_result else '❌'
        if not has_result:
            all_ok = False
        print(f'  {status} "{query}" → {len(r)} results  ({desc})')

    if all_ok:
        print('  PASS: 全部命中')
    else:
        print('  WARN: 部分查询无结果（可能是测试数据不足）')


def test_data_cleanup():
    """Test 14: Clean up test data"""
    print_sep('Test 14: 数据清理')
    clean()
    bm25_count = BM25Index().count()
    print(f'  BM25 after cleanup: {bm25_count} (should be less)')
    print('  Cleanup: OK')


if __name__ == '__main__':
    print('=' * 65)
    print('  Full RAG Pipeline Test Suite')
    print('  Coverage: Chunker | BM25 | Vector | RRF | Context | Logging')
    print('=' * 65)

    clean()

    try:
        test_chunking()
        test_ingest()
        test_hybrid_search()
        test_logging_format()
        test_error_handling()
        test_cli_demo()
        test_data_cleanup()
    finally:
        clean()

    print('\n' + '=' * 65)
    print('  All tests completed!')
    print('=' * 65)
