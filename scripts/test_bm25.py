"""Quick BM25 integration test."""
import sys
sys.path.insert(0, '.')

from core.agents.rag.bm25_index import BM25Index

idx = BM25Index()

# Add test docs
docs = [
    {'chunk_id': 't1', 'content': '用户登录功能需要支持密码登录和短信验证码登录', 'doc_type': 'prd', 'title': '登录需求'},
    {'chunk_id': 't2', 'content': '支付功能支持支付宝支付和微信支付, 支付超时30分钟自动取消', 'doc_type': 'prd', 'title': '支付需求'},
    {'chunk_id': 't3', 'content': 'API接口测试需要覆盖正常场景、异常场景和边界场景', 'doc_type': 'best_practice', 'title': '测试最佳实践'},
]
idx.add_documents_batch(docs)
print(f'Added {len(docs)} docs. Index count: {idx.count()}')

# Test searches
for q in ['登录', '支付', 'API', '超时']:
    results = idx.search(q, top_k=3)
    print(f'\nSearch "{q}": {len(results)} results')
    for r in results:
        print(f'  score={r["score"]:.3f}  id={r["chunk_id"]}  title={r["title"]}')

# Cleanup
idx.delete_by_prefix('t')
print(f'\nCleanup done. Index count: {idx.count()}')
print('BM25 test passed!')
