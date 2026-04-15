"""
Agent Models

This module contains agent conversation and execution models.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .project import Project


class AgentConversation(models.Model):
    """Agent conversation history"""
    
    AGENT_TYPES = [
        ('ui_test', 'UI Test Agent'),
        ('api_test', 'API Test Agent'),
        ('test_generation', 'Test Generation Agent'),
        ('code_generation', 'Code Generation Agent'),
        ('error_analysis', 'Error Analysis Agent'),
        ('test_planning', 'Test Planning Agent'),
        ('knowledge_retrieval', 'Knowledge Retrieval Agent'),
    ]
    
    agent_type = models.CharField(
        max_length=50,
        choices=AGENT_TYPES,
        verbose_name='Agent Type'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='agent_conversations',
        null=True,
        blank=True,
        verbose_name='Project'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agent_conversations',
        null=True,
        verbose_name='User'
    )
    conversation_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Conversation ID'
    )
    title = models.CharField(max_length=255, blank=True, verbose_name='Title')
    intent_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Intent Type'  # 新增：意图类型
    )
    messages = models.JSONField(default=list, verbose_name='Messages')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    migrated_to_markdown = models.BooleanField(
        default=False,
        verbose_name='Migrated to Markdown'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Agent Conversation'
        verbose_name_plural = 'Agent Conversations'
        ordering = ['-updated_at']
        db_table = 'core_agent_conversation'
        indexes = [
            models.Index(fields=['agent_type', 'project']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_agent_type_display()} - {self.conversation_id}"
    
    @property
    def message_count(self) -> int:
        """Number of messages in conversation"""
        return len(self.messages) if self.messages else 0
    
    @property
    def duration(self) -> float:
        """Conversation duration"""
        if self.updated_at and self.created_at:
            return (self.updated_at - self.created_at).total_seconds()
        return 0


class AgentExecution(models.Model):
    """Agent execution record"""
    
    TASK_TYPES = [
        ('test_planning', 'Test Planning'),
        ('code_generation', 'Code Generation'),
        ('test_execution', 'Test Execution'),
        ('knowledge_retrieval', 'Knowledge Retrieval'),
        ('error_analysis', 'Error Analysis'),
        ('flow_generation', 'Flow Generation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    agent_type = models.CharField(
        max_length=50,
        choices=AgentConversation.AGENT_TYPES,
        verbose_name='Agent Type'
    )
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPES,
        verbose_name='Task Type'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='agent_executions',
        null=True,
        blank=True,
        verbose_name='Project'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agent_executions',
        null=True,
        verbose_name='User'
    )
    execution_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Execution ID'
    )
    input_data = models.JSONField(default=dict, verbose_name='Input Data')
    output_data = models.JSONField(default=dict, blank=True, verbose_name='Output Data')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    error_message = models.TextField(blank=True, verbose_name='Error Message')
    metrics = models.JSONField(default=dict, blank=True, verbose_name='Metrics')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started At')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed At')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Agent Execution'
        verbose_name_plural = 'Agent Executions'
        ordering = ['-created_at']
        db_table = 'core_agent_execution'
        indexes = [
            models.Index(fields=['agent_type', 'task_type']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_agent_type_display()} - {self.get_task_type_display()}"
    
    @property
    def duration(self) -> float:
        """Execution duration in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0