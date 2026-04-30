"""
Cleanup business data from knowledge base.

Deletes documents with removed doc_types from both MySQL and ChromaDB.
Removed types: feature_test, api_test, ui_test, page_structure
"""
from __future__ import annotations

import logging
import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

from core.models.knowledge import KnowledgeDocument
from core.agents.rag.knowledge_retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)

REMOVED_TYPES = ['feature_test', 'api_test', 'ui_test', 'page_structure']


def cleanup_chromadb(retriever: KnowledgeRetriever) -> int:
    """Delete business data from ChromaDB by chroma_id_prefix"""
    docs = KnowledgeDocument.objects.filter(document_type__in=REMOVED_TYPES)
    total_deleted = 0
    
    for doc in docs:
        if doc.chroma_id_prefix:
            try:
                count = retriever.delete_document_chunks(doc.chroma_id_prefix)
                total_deleted += count
                print(f"  ChromaDB: deleted {count} chunks for doc {doc.id} ({doc.document_type})")
            except Exception as e:
                print(f"  ChromaDB: failed to delete doc {doc.id}: {e}")
    
    return total_deleted


def cleanup_mysql() -> int:
    """Delete business data from MySQL"""
    docs = KnowledgeDocument.objects.filter(document_type__in=REMOVED_TYPES)
    count = docs.count()
    print(f"MySQL: found {count} KnowledgeDocument records to delete")
    
    for doc_type in REMOVED_TYPES:
        type_count = KnowledgeDocument.objects.filter(document_type=doc_type).count()
        print(f"  {doc_type}: {type_count} records")
    
    docs.delete()
    return count


def main() -> None:
    print("=" * 60)
    print("Knowledge Base Business Data Cleanup")
    print("=" * 60)
    print(f"\nRemoved doc_types: {REMOVED_TYPES}")
    
    # Count first
    for doc_type in REMOVED_TYPES:
        count = KnowledgeDocument.objects.filter(document_type=doc_type).count()
        print(f"  {doc_type}: {count} records in MySQL")
    
    total = KnowledgeDocument.objects.filter(document_type__in=REMOVED_TYPES).count()
    if total == 0:
        print("\nNo business data found. Nothing to clean.")
        return
    
    confirm = input(f"\nDelete {total} records from MySQL + ChromaDB? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return
    
    # Clean ChromaDB
    print("\n[Step 1/2] Cleaning ChromaDB...")
    retriever = KnowledgeRetriever()
    chroma_deleted = cleanup_chromadb(retriever)
    print(f"ChromaDB: deleted {chroma_deleted} chunks total")
    
    # Clean MySQL
    print("\n[Step 2/2] Cleaning MySQL...")
    mysql_deleted = cleanup_mysql()
    print(f"MySQL: deleted {mysql_deleted} KnowledgeDocument records")
    
    print(f"\nCleanup complete. Removed {total} documents from both stores.")


if __name__ == '__main__':
    main()
