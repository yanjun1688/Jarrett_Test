"""
Test chunker end-to-end: upload → chunk → ChromaDB → query.
Run: python scripts/test_chunker.py
"""
from __future__ import annotations

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

from core.agents.rag.chunker import Chunker
from core.agents.rag.vector_store import ChromaVectorStore
from core.agents.rag.embedding_service import EmbeddingService


def print_sep(title: str) -> None:
    print()
    print('=' * 60)
    print(f'  {title}')
    print('=' * 60)


def test_prd_chunking():
    """Test: Chunker splits PRD into heading-based chunks"""
    print_sep('Test 1: PRD Chunking (logic only)')

    content = """
## User Module
### Register
User can register with phone number and verification code.
Password must contain uppercase, lowercase and numbers.
### Login
Support password login and SMS verification code login.
5 failed attempts trigger captcha.

## Product Module
### Product List
Paginated query, 20 items per page by default.
Support sorting by category, price, sales volume.
### Product Detail
Display main image, title, price, stock.
Support multi-spec selection (color, size).

## Order Module
### Create Order
Create order from shopping cart.
Support coupons and points.
Redirect to payment after creation.
### Order List
Filter by status: pending payment, pending shipment, completed.
Support cancel order and refund request.
"""

    chunker = Chunker()
    chunks = chunker.chunk('prd', content)
    print(f'Input: {len(content)} chars')
    print(f'Chunks: {len(chunks)}')
    for c in chunks:
        lines = c.content.strip().split('\n')
        heading = lines[0] if lines else '?'
        print(f'  [{c.chunk_index}] {len(c.content):>4}c  {heading}')
    assert len(chunks) >= 3, f'Expected >=3 chunks, got {len(chunks)}'
    print('  PASS')


def test_api_chunking():
    """Test: EndpointStrategy splits OpenAPI by path+method"""
    print_sep('Test 2: API_DOC Chunking (logic only)')

    content = '{"openapi":"3.0.0","info":{"title":"Order API"},"paths":{"/orders":{"get":{"summary":"List orders","parameters":[{"name":"page","in":"query"}]},"post":{"summary":"Create order","requestBody":{"content":{"application/json":{"schema":{"type":"object"}}}},"responses":{"201":{"description":"Created"}}}},"/orders/{id}":{"get":{"summary":"Get order","parameters":[{"name":"id","in":"path","required":true}]}},"/orders/{id}/cancel":{"post":{"summary":"Cancel order","responses":{"200":{"description":"Cancelled"}}}}}}'

    chunker = Chunker()
    chunks = chunker.chunk('api_doc', content)
    print(f'Chunks: {len(chunks)} (expect 4 endpoints)')
    for c in chunks:
        lines = c.content.split('\n')
        endpoint = lines[2] if len(lines) > 2 else '?'
        print(f'  [{c.chunk_index}] {len(c.content):>4}c  {endpoint}')
    assert len(chunks) == 4, f'Expected 4 chunks, got {len(chunks)}'
    print('  PASS')


def test_vector_integration():
    """Test: Embedding + ChromaDB write + query (real vector storage)"""
    print_sep('Test 3: Vector Integration (ChromaDB + Embedding)')

    content = 'The user login functionality should support password login and SMS verification code login.'
    chunker = Chunker()
    chunks = chunker.chunk('prd', content)

    embedder = EmbeddingService()
    vector_store = ChromaVectorStore()
    test_prefix = 'test_chunker_'

    # Clean previous test data
    vector_store.delete_by_prefix(test_prefix)

    # Embed and write
    texts = [c.content for c in chunks]
    embeddings = embedder.embed_texts(texts)
    ids = [f'{test_prefix}chunk_{c.chunk_index}' for c in chunks]
    metadatas = [{'chroma_id_prefix': test_prefix, 'chunk_index': c.chunk_index, 'doc_type': 'prd'} for c in chunks]

    vector_store.add_documents(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    print(f'Written {len(chunks)} chunks to ChromaDB')

    # Verify count
    count = vector_store.count()
    print(f'Collection count: {count} (should exist)')
    assert count > 0
    print('  ChromaDB write: PASS')

    # Query similar
    query = 'SMS verification code login'
    query_embedding = embedder.embed_query(query)
    results = vector_store.query(query_embedding=query_embedding, n_results=3)

    result_count = len(results.get('ids', [[]])[0])
    print(f'Query "{query}" → {result_count} results')

    if result_count > 0:
        doc = results['documents'][0][0]
        dist = results['distances'][0][0]
        print(f'  Top result (distance={dist:.4f}): "{doc[:80]}..."')

    assert result_count > 0, 'Expected at least 1 result from vector store'
    print('  ChromaDB query: PASS')

    # Cleanup
    vector_store.delete_by_prefix(test_prefix)
    print('  Cleanup: PASS')


def test_short_doc():
    """Test: Short BEST_PRACTICE stays as single chunk"""
    print_sep('Test 4: NoSplitStrategy (short doc)')

    content = 'Always verify edge cases and error handling in API tests.'
    chunker = Chunker()
    chunks = chunker.chunk('best_practice', content)
    assert len(chunks) == 1, f'Expected 1 chunk, got {len(chunks)}'
    print(f'Content: {len(content)} chars → 1 chunk (kept intact)')
    print('  PASS')


if __name__ == '__main__':
    test_prd_chunking()
    test_api_chunking()
    test_short_doc()
    test_vector_integration()
    print()
    print('All tests passed!')
