"""
录制会话管理器
"""
from __future__ import annotations
import uuid
import logging
from typing import Any
from datetime import datetime
from django.core.cache import cache

logger = logging.getLogger(__name__)


class RecordingSessionManager:
    """录制会话管理器"""
    
    SESSION_PREFIX = 'recording_session:'
    SESSION_TIMEOUT = 3600  # 1小时超时
    
    @classmethod
    def create_session(
        cls,
        user_id: int | None = None,
        start_url: str = 'about:blank',
        browser_type: str = 'chromium',
    ) -> str:
        """
        创建新的录制会话
        
        Args:
            user_id: 用户ID
            start_url: 起始URL
            browser_type: 浏览器类型
            
        Returns:
            str: 会话ID
        """
        session_id = str(uuid.uuid4())
        session_data: dict[str, Any] = {
            'session_id': session_id,
            'user_id': user_id,
            'start_url': start_url,
            'browser_type': browser_type,
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'steps': [],
            'screenshot_task_running': False,
        }
        
        cache_key = cls.SESSION_PREFIX + session_id
        
        try:
            # django-redis会自动管理连接，使用cache API即可
            cache.set(cache_key, session_data, timeout=cls.SESSION_TIMEOUT)
            
        except Exception as e:
            error_msg = str(e)
            
            # 提供更友好的错误信息
            if 'Connection refused' in error_msg or 'ConnectionError' in error_msg:
                raise Exception("无法连接到Redis服务器，请确保Redis服务正在运行")
            elif 'timeout' in error_msg.lower():
                raise Exception("Redis响应超时，请检查Redis服务状态")
            else:
                raise Exception(f"创建录制会话失败：{error_msg}")
        
        return session_id
    
    @classmethod
    def get_session(cls, session_id: str) -> dict[str, Any] | None:
        """获取会话数据"""
        cache_key = cls.SESSION_PREFIX + session_id
        try:
            result: dict[str, Any] | None = cache.get(cache_key)
            return result
        except Exception as e:
            logger.error(f"获取会话失败: {session_id}, 错误: {str(e)}")
            return None
    
    @classmethod
    def update_session(cls, session_id: str, **kwargs: Any) -> bool:
        """更新会话数据"""
        session = cls.get_session(session_id)
        if not session:
            return False
        
        try:
            session.update(kwargs)
            cache_key = cls.SESSION_PREFIX + session_id
            cache.set(cache_key, session, timeout=cls.SESSION_TIMEOUT)
            return True
        except Exception as e:
            logger.error(f"更新会话失败: {session_id}, 错误: {str(e)}")
            return False
    
    @classmethod
    def add_step(cls, session_id: str, step: dict[str, Any]) -> bool:
        """添加步骤到会话"""
        session = cls.get_session(session_id)
        if not session:
            return False
        
        try:
            steps = session.get('steps', [])
            steps.append(step)
            session['steps'] = steps
            
            cache_key = cls.SESSION_PREFIX + session_id
            cache.set(cache_key, session, timeout=cls.SESSION_TIMEOUT)
            return True
        except Exception as e:
            logger.error(f"添加步骤失败: {session_id}, 错误: {str(e)}")
            return False
    
    @classmethod
    def get_steps(cls, session_id: str) -> list[dict[str, Any]]:
        """获取会话的所有步骤"""
        session = cls.get_session(session_id)
        if not session:
            return []
        result: list[dict[str, Any]] = session.get('steps', [])
        return result
    
    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """删除会话"""
        cache_key = cls.SESSION_PREFIX + session_id
        try:
            cache.delete(cache_key)
            # Removed verbose logging
            return True
        except Exception as e:
            logger.error(f"删除会话失败: {session_id}, 错误: {str(e)}")
            return False
    
    @classmethod
    def set_screenshot_task_status(cls, session_id: str, running: bool) -> bool:
        """设置截图任务状态"""
        return cls.update_session(session_id, screenshot_task_running=running)

