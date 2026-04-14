"""
ChatBot Execution Log Models

Stores execution logs for ChatBot-triggered operations (skill execution, API tests, UI tests).
"""

from django.db import models
from django.contrib.auth.models import User


class ChatBotExecutionLog(models.Model):
    """ChatBot执行日志模型"""

    LOG_TYPE_CHOICES = [
        ('skill', 'Skill执行'),
        ('api_test', '接口测试'),
        ('ui_test', 'UI测试'),
    ]

    conversation_id = models.CharField(max_length=64, db_index=True)
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    execution = models.ForeignKey(
        'core.TestExecution',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='chatbot_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ChatBot执行日志'
        verbose_name_plural = 'ChatBot执行日志'
        indexes = [
            models.Index(fields=['conversation_id', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.log_type}] {self.title} - {self.created_at}"

    def to_dict(self):
        return {
            'id': self.id,  # type: ignore[attr-defined]
            'conversation_id': self.conversation_id,
            'log_type': self.log_type,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'execution_id': self.execution_id,  # type: ignore[attr-defined]
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }