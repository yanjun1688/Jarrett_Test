"""
WebSocket Handler - WebSocket通信处理器

处理WebSocket连接、消息收发和会话管理
"""
import json
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable, List
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
import logging

logger = logging.getLogger(__name__)


@dataclass
class WebSocketSession:
    """WebSocket会话"""
    session_id: str
    websocket: Any
    connected_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketHandler:
    """
    WebSocket处理器
    
    管理WebSocket连接、消息路由和广播
    """
    
    def __init__(self):
        """初始化WebSocket处理器"""
        self._sessions: Dict[str, WebSocketSession] = {}
        self._session_by_ws: Dict[Any, str] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_id, ...]
        self._lock = Lock()
        self._message_handlers: Dict[str, Callable] = {}
        
    async def handle_connect(self, websocket, user_id: Optional[str] = None) -> str:
        """
        处理新的WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID（用于按用户广播）
            
        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())
        
        with self._lock:
            session = WebSocketSession(
                session_id=session_id,
                websocket=websocket
            )
            if user_id:
                session.metadata["user_id"] = user_id
            self._sessions[session_id] = session
            self._session_by_ws[websocket] = session_id
            if user_id:
                self._user_sessions.setdefault(user_id, []).append(session_id)
        
        logger.info(f"WebSocket connected: {session_id}")
        
        # 发送欢迎消息
        await self.send_message(websocket, {
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to Chatbot Service"
        })
        
        return session_id
    
    async def handle_disconnect(self, websocket) -> None:
        """
        处理WebSocket断开
        
        Args:
            websocket: WebSocket连接对象
        """
        session_id = None
        
        with self._lock:
            session_id = self._session_by_ws.pop(websocket, None)
            if session_id and session_id in self._sessions:
                session = self._sessions.pop(session_id)
                user_id = session.metadata.get("user_id")
                if user_id and user_id in self._user_sessions:
                    try:
                        self._user_sessions[user_id].remove(session_id)
                        if not self._user_sessions[user_id]:
                            del self._user_sessions[user_id]
                    except ValueError:
                        pass
        
        if session_id:
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def handle_message(self, websocket, message: str) -> None:
        """
        处理接收到的消息
        
        Args:
            websocket: WebSocket连接对象
            message: 消息内容（JSON字符串）
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type", "message")
            
            # 获取会话ID
            with self._lock:
                session_id = self._session_by_ws.get(websocket)

            # 根据消息类型处理
            if msg_type == "ping":
                await self.send_message(websocket, {"type": "pong"})
            elif msg_type == "message":
                with self._lock:
                    session = self._sessions.get(session_id) if session_id else None
                    if session:
                        session.metadata["last_message"] = datetime.now()
            else:
                # 自定义处理器
                handler = self._message_handlers.get(msg_type)
                if handler:
                    await handler(websocket, data)
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message: {message[:100]}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def send_message(self, websocket, data: Dict[str, Any]) -> None:
        """
        发送消息到WebSocket
        
        Args:
            websocket: WebSocket连接对象
            data: 要发送的数据
        """
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast_to_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        向指定会话发送消息
        
        Args:
            session_id: 会话ID
            data: 要发送的数据
            
        Returns:
            是否发送成功
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            ws = session.websocket

        try:
            await ws.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            return False
    
    async def broadcast_to_all(self, data: Dict[str, Any]) -> int:
        """
        向所有会话广播消息
        
        Args:
            data: 要发送的数据
            
        Returns:
            成功发送的数量
        """
        success_count = 0
        
        with self._lock:
            sessions = list(self._sessions.values())
        
        for session in sessions:
            try:
                await session.websocket.send_json(data)
                success_count += 1
            except Exception as e:
                logger.error(f"Broadcast to {session.session_id} failed: {e}")
        
        return success_count

    async def broadcast_to_user(self, user_id: str, data: Dict[str, Any]) -> int:
        """
        向指定用户的所有会话广播消息
        
        Args:
            user_id: 用户ID
            data: 要发送的数据
            
        Returns:
            成功发送的数量
        """
        success_count = 0

        with self._lock:
            session_ids = list(self._user_sessions.get(user_id, []))
            sessions = [self._sessions[sid] for sid in session_ids if sid in self._sessions]

        for session in sessions:
            try:
                await session.websocket.send_json(data)
                success_count += 1
            except Exception as e:
                logger.error(f"Broadcast to user {user_id} session {session.session_id} failed: {e}")

        return success_count
    
    def get_session_count(self) -> int:
        """获取连接数量"""
        with self._lock:
            return len(self._sessions)
    
    def get_session_id(self, websocket) -> Optional[str]:
        """获取WebSocket对应的会话ID"""
        with self._lock:
            return self._session_by_ws.get(websocket)
    
    def register_handler(self, msg_type: str, handler: Callable[[Any, Dict], Awaitable[None]]) -> None:
        """
        注册消息处理器
        
        Args:
            msg_type: 消息类型
            handler: 处理函数
        """
        self._message_handlers[msg_type] = handler
    
    async def close_session(self, session_id: str) -> bool:
        """
        关闭会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功关闭
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            ws = session.websocket
            user_id = session.metadata.get("user_id")

        try:
            await ws.close()
        except Exception:
            pass
        finally:
            with self._lock:
                self._session_by_ws.pop(ws, None)
                self._sessions.pop(session_id, None)
                if user_id and user_id in self._user_sessions:
                    try:
                        self._user_sessions[user_id].remove(session_id)
                        if not self._user_sessions[user_id]:
                            del self._user_sessions[user_id]
                    except ValueError:
                        pass
            
        return True


# 全局WebSocket处理器
_global_handler: Optional[WebSocketHandler] = None
_global_handler_lock = Lock()


def get_websocket_handler() -> WebSocketHandler:
    """获取全局WebSocket处理器"""
    global _global_handler
    if _global_handler is not None:
        return _global_handler
    with _global_handler_lock:
        if _global_handler is not None:
            return _global_handler
        _global_handler = WebSocketHandler()
    return _global_handler


def reset_websocket_handler() -> None:
    """重置全局WebSocket处理器（用于测试）"""
    global _global_handler
    with _global_handler_lock:
        _global_handler = None