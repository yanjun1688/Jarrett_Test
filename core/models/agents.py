"""
Agent Models

This module contains agent conversation models.
"""

from django.db import models
from django.contrib.auth.models import User

from .project import Project


class AgentConversation(models.Model):
    """Agent conversation history"""

    AGENT_TYPES = [
        ('test_generation', 'Test Generation Agent'),
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
        verbose_name='Intent Type'
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
