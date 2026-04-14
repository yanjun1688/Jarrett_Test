"""
Conversation Service - 会话管理服务（支持 Markdown 存储）

管理会话的创建、查询、更新、删除，以及消息历史和业务上下文
支持双存储：MySQL（旧数据）+ Markdown 文件（新数据）
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from core.models.agents import AgentConversation
from core.context.markdown_store import MarkdownContextStore

logger = logging.getLogger(__name__)


MAX_CONVERSATIONS_PER_USER = 30
PENDING_TESTS_EXPIRE_HOURS = 1
TITLE_MAX_LENGTH = 30

_md_store: Optional[MarkdownContextStore] = None


def get_markdown_store() -> MarkdownContextStore:
    """获取 Markdown 存储单例"""
    global _md_store
    if _md_store is None:
        root_dir = getattr(settings, 'CONTEXT_ROOT_DIR', Path(settings.BASE_DIR / "context_data"))
        _md_store = MarkdownContextStore(root_dir)
    return _md_store


@dataclass
class Message:
    """消息数据类"""
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )


class ConversationService:
    """
    会话管理服务
    
    支持双存储：MySQL（索引）+ Markdown 文件（消息存储）
    - MySQL: 存储会话索引、权限、元数据快照
    - Markdown: 存储消息历史、上下文状态
    """
    
    @staticmethod
    def create_conversation(
        user: User,
        project_id: Optional[int] = None,
        agent_type: str = "test_generation"
    ) -> Tuple[Optional[AgentConversation], Optional[str]]:
        """
        创建新会话
        
        Args:
            user: 用户对象
            project_id: 项目ID（可选）
            agent_type: Agent类型，默认 test_generation
            
        Returns:
            (会话对象, 错误信息) - 成功时错误信息为 None
        """
        current_count = AgentConversation.objects.filter(user=user).count()
        
        if current_count >= MAX_CONVERSATIONS_PER_USER:
            return None, f"会话数量已达上限（{MAX_CONVERSATIONS_PER_USER}个），请删除部分会话后重试"
        
        conversation_id = str(uuid.uuid4())
        
        md_store = get_markdown_store()
        md_created = md_store.create_session(
            session_id=conversation_id,
            user_id=str(user.id),  # type: ignore
            project_id=str(project_id) if project_id else None
        )
        
        if not md_created:
            return None, "创建会话存储失败"
        
        try:
            conversation = AgentConversation.objects.create(
                conversation_id=conversation_id,
                user=user,
                project_id=project_id,
                agent_type=agent_type,
                messages=[],
                metadata={},
                migrated_to_markdown=True
            )
        except Exception as e:
            md_store.delete_session(conversation_id, str(user.id), hard_delete=True)  # type: ignore
            logger.error(f"Failed to create MySQL conversation record: {e}")
            return None, "创建会话失败"
        
        logger.info(f"Created conversation: {conversation_id} for user {user.id}")  # type: ignore
        return conversation, None
    
    @staticmethod
    def get_conversation(conversation_id: str, user: User) -> Optional[AgentConversation]:
        """
        获取会话
        
        Args:
            conversation_id: 会话ID
            user: 用户对象（用于权限验证）
            
        Returns:
            会话对象，不存在或无权限返回 None
        """
        try:
            return AgentConversation.objects.get(
                conversation_id=conversation_id,
                user=user
            )
        except AgentConversation.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_conversations(user: User) -> List[AgentConversation]:
        """
        获取用户所有会话列表
        
        Args:
            user: 用户对象
            
        Returns:
            会话列表，按更新时间倒序
        """
        return list(AgentConversation.objects.filter(user=user).order_by("-updated_at"))
    
    @staticmethod
    def delete_conversation(conversation_id: str, user: User) -> Tuple[bool, Optional[str]]:
        """
        删除会话
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            
        Returns:
            (是否成功, 错误信息)
        """
        conversation = ConversationService.get_conversation(conversation_id, user)
        if not conversation:
            return False, "会话不存在或无权限删除"
        
        migrated_to_markdown = conversation.migrated_to_markdown
        
        try:
            conversation.delete()
        except Exception as e:
            logger.error(f"Failed to delete MySQL conversation: {e}")
            return False, "删除会话失败"
        
        if migrated_to_markdown:
            md_store = get_markdown_store()
            md_deleted = md_store.delete_session(conversation_id, str(user.id), hard_delete=True)  # type: ignore
            if not md_deleted:
                logger.warning(f"MySQL deleted but Markdown cleanup failed for: {conversation_id}")
        
        logger.info(f"Deleted conversation: {conversation_id}")
        return True, None
    
    @staticmethod
    def add_message(
        conversation_id: str,
        user: User,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        添加消息到会话
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 消息元数据（可选）
            
        Returns:
            (是否成功, 错误信息)
        """
        conversation = ConversationService.get_conversation(conversation_id, user)
        if not conversation:
            return False, "会话不存在"
        
        if conversation.migrated_to_markdown:
            md_store = get_markdown_store()
            success = md_store.append_message(
                session_id=conversation_id,
                user_id=str(user.id),  # type: ignore
                role=role,
                content=content,
                metadata=metadata
            )
            
            if success and not conversation.title and role == "user":
                conversation.title = content[:TITLE_MAX_LENGTH]
                conversation.save(update_fields=["title", "updated_at"])
            elif success:
                conversation.save(update_fields=["updated_at"])
            
            return success, None if success else "写入失败"
        else:
            message = Message(
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            messages = conversation.messages or []
            messages.append(message.to_dict())
            conversation.messages = messages
            
            if not conversation.title and role == "user":
                conversation.title = content[:TITLE_MAX_LENGTH]
            
            conversation.save(update_fields=["messages", "title", "updated_at"])
            
            return True, None
    
    @staticmethod
    def get_messages(conversation_id: str, user: User) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        获取会话消息历史
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            
        Returns:
            (消息列表, 错误信息)
        """
        conversation = ConversationService.get_conversation(conversation_id, user)
        if not conversation:
            return [], "会话不存在"
        
        if conversation.migrated_to_markdown:
            md_store = get_markdown_store()
            context = md_store.get_context(conversation_id, str(user.id))  # type: ignore
            if context:
                return context.get("messages", []), None
            return [], "读取消息失败"
        
        return conversation.messages or [], None
    
    @staticmethod
    def get_messages_for_llm(conversation_id: str, user: User) -> List[Dict[str, str]]:
        """
        获取用于 LLM 的消息历史（简化格式）
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            
        Returns:
            消息列表 [{"role": "user", "content": "..."}, ...]
        """
        messages, _ = ConversationService.get_messages(conversation_id, user)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
            if msg.get("role") in ["user", "assistant"]
        ]
    
    @staticmethod
    def update_metadata(
        conversation_id: str,
        user: User,
        metadata: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        更新会话元数据（业务上下文）
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            metadata: 要更新的元数据
            
        Returns:
            (是否成功, 错误信息)
        """
        conversation = ConversationService.get_conversation(conversation_id, user)
        if not conversation:
            return False, "会话不存在"
        
        if conversation.migrated_to_markdown:
            md_store = get_markdown_store()
            success = md_store.update_context_state(
                session_id=conversation_id,
                user_id=str(user.id),  # type: ignore
                updates=metadata
            )
            if success:
                conversation.save(update_fields=["updated_at"])
            return success, None if success else "更新失败"
        
        current_metadata = conversation.metadata or {}
        current_metadata.update(metadata)
        conversation.metadata = current_metadata
        conversation.save(update_fields=["metadata", "updated_at"])
        
        return True, None
    
    @staticmethod
    def get_metadata(conversation_id: str, user: User) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        获取会话元数据
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            
        Returns:
            (元数据, 错误信息)
        """
        conversation = ConversationService.get_conversation(conversation_id, user)
        if not conversation:
            return {}, "会话不存在"
        
        if conversation.migrated_to_markdown:
            md_store = get_markdown_store()
            context = md_store.get_context(conversation_id, str(user.id))  # type: ignore
            if context:
                return context.get("context_state", {}), None
            return {}, "读取元数据失败"
        
        return conversation.metadata or {}, None
    
    @staticmethod
    def get_pending_tests(conversation_id: str, user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        获取待执行的测试数据（带过期检查）
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            
        Returns:
            (测试数据, 错误信息) - 如果过期返回 (None, "测试数据已过期...")
        """
        metadata, _ = ConversationService.get_metadata(conversation_id, user)
        
        pending_tests = metadata.get("pending_tests")
        last_action_time = metadata.get("last_action_time")
        
        if not pending_tests:
            return None, None
        
        if last_action_time:
            try:
                action_time = datetime.fromisoformat(last_action_time)
                expire_time = action_time + timedelta(hours=PENDING_TESTS_EXPIRE_HOURS)
                
                if datetime.now() > expire_time:
                    ConversationService.clear_pending_tests(conversation_id, user)
                    return None, f"测试数据已过期（超过{PENDING_TESTS_EXPIRE_HOURS}小时），请重新生成"
            except (ValueError, TypeError):
                pass
        
        return pending_tests, None
    
    @staticmethod
    def set_pending_tests(
        conversation_id: str,
        user: User,
        tests: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        设置待执行的测试数据
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            tests: 测试数据
            
        Returns:
            (是否成功, 错误信息)
        """
        return ConversationService.update_metadata(conversation_id, user, {
            "pending_tests": tests,
            "last_action_time": datetime.now().isoformat()
        })
    
    @staticmethod
    def clear_pending_tests(conversation_id: str, user: User) -> Tuple[bool, Optional[str]]:
        """
        清空待执行的测试数据
        
        Args:
            conversation_id: 会话ID
            user: 用户对象
            
        Returns:
            (是否成功, 错误信息)
        """
        conversation = ConversationService.get_conversation(conversation_id, user)
        if not conversation:
            return False, "会话不存在"
        
        if conversation.migrated_to_markdown:
            md_store = get_markdown_store()
            return md_store.delete_context_fields(
                session_id=conversation_id,
                user_id=str(user.id),  # type: ignore
                fields=["pending_tests", "last_action_time"]
            ), None
        
        metadata = conversation.metadata or {}
        if "pending_tests" in metadata:
            del metadata["pending_tests"]
        if "last_action_time" in metadata:
            del metadata["last_action_time"]
        conversation.metadata = metadata
        conversation.save(update_fields=["metadata", "updated_at"])
        
        return True, None
    
    @staticmethod
    def get_or_create_conversation(
        user: User,
        conversation_id: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> Tuple[Optional[AgentConversation], Optional[str], bool]:
        """
        获取或创建会话
        
        Args:
            user: 用户对象
            conversation_id: 会话ID（可选，不提供则创建新会话）
            project_id: 项目ID（可选）
            
        Returns:
            (会话对象, 错误信息, 是否新建)
        """
        if conversation_id:
            conversation = ConversationService.get_conversation(conversation_id, user)
            if conversation:
                return conversation, None, False
            return None, "会话不存在", False
        
        conversation, error = ConversationService.create_conversation(user, project_id)
        if conversation:
            return conversation, None, True
        return None, error, False
    
    @staticmethod
    def get_conversation_count(user: User) -> int:
        """
        获取用户会话数量
        
        Args:
            user: 用户对象
            
        Returns:
            会话数量
        """
        return AgentConversation.objects.filter(user=user).count()