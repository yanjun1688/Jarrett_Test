"""
Core Models Module

This module contains unified data models for the test automation framework.
It consolidates models from multiple apps into a single, coherent structure.
"""

from .project import Project, Module
from .test_management import TestExecution
from .knowledge import KnowledgeBase, KnowledgeDocument
from .agents import AgentConversation
from .chatbot_execution_log import ChatBotExecutionLog
from .unified import UnifiedScript, UnifiedExecution, ScriptType, UnifiedStatus

__all__ = [
    'Project',
    'Module',
    'TestExecution',
    'KnowledgeBase',
    'KnowledgeDocument',
    'AgentConversation',
    'ChatBotExecutionLog',
    'UnifiedScript',
    'UnifiedExecution',
    'ScriptType',
    'UnifiedStatus',
]