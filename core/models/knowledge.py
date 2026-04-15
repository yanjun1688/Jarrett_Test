"""
Knowledge Models

This module contains knowledge base and document models.
"""

from django.db import models
from django.contrib.auth.models import User

from .project import Project


class KnowledgeBase(models.Model):
    """Knowledge base metadata"""
    
    DOCUMENT_TYPES = [
        ('prd', 'PRD文档'),
        ('api_doc', '接口文档'),
        ('feature_test', '功能测试用例'),
        ('api_test', '接口测试用例'),
        ('ui_test', 'UI用例'),
    ]
    
    STATUS_CHOICES = [
        ('building', 'Building'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Knowledge Base Name')
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='knowledge_bases',
        verbose_name='Project'
    )
    description = models.TextField(blank=True, verbose_name='Description')
    embedding_model = models.CharField(
        max_length=255,
        default='sentence-transformers/all-MiniLM-L6-v2',
        verbose_name='Embedding Model'
    )
    chunk_size = models.IntegerField(default=1000, verbose_name='Chunk Size')
    chunk_overlap = models.IntegerField(default=200, verbose_name='Chunk Overlap')
    document_count = models.IntegerField(default=0, verbose_name='Document Count')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ready',
        verbose_name='Status'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='core_knowledge_bases',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Knowledge Base'
        verbose_name_plural = 'Knowledge Bases'
        ordering = ['-updated_at']
        db_table = 'core_knowledge_base'
    
    def __str__(self) -> str:
        return f"{self.name} ({self.project.name})"


class KnowledgeDocument(models.Model):
    """Knowledge document"""
    
    DOCUMENT_TYPES = KnowledgeBase.DOCUMENT_TYPES
    
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Knowledge Base'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES,
        verbose_name='Document Type'
    )
    file_path = models.CharField(max_length=500, blank=True, verbose_name='File Path')
    content = models.TextField(verbose_name='Content')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    embedding = models.JSONField(default=list, blank=True, verbose_name='Vector Embedding')
    chunk_index = models.IntegerField(default=0, verbose_name='Chunk Index')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='core_knowledge_documents',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    chroma_id_prefix = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='ChromaDB Document ID Prefix',
        help_text='Format: doc_{id}_, for batch deletion of all chunks'
    )
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('syncing', 'Syncing'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending',
        verbose_name='Sync Status'
    )
    sync_error = models.TextField(blank=True, verbose_name='Sync Error')
    synced_at = models.DateTimeField(null=True, blank=True, verbose_name='Synced At')
    
    class Meta:
        verbose_name = 'Knowledge Document'
        verbose_name_plural = 'Knowledge Documents'
        ordering = ['-created_at']
        db_table = 'core_knowledge_document'
        indexes = [
            models.Index(fields=['knowledge_base', 'document_type']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.document_type} - Chunk {self.chunk_index}"
    
    @property
    def chroma_id(self) -> str:
        """Generate complete ChromaDB ID"""
        return f"doc_{self.id}_chunk_{self.chunk_index}"