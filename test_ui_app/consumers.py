"""
ChatBot WebSocket Consumer
处理聊天机器人的实时流式消息
"""
# pyright: reportAttributeAccessIssue=false
import json
import logging
import time
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from test_ui_app.middleware import TokenAuthMiddleware
from testmanager_app.chatbots.chatbot_views import get_llm_service
from core.agents.chatbot_agent import ChatbotAgent

logger = logging.getLogger(__name__)

MAX_MESSAGE_SIZE = 1024 * 100  # 100KB
RATE_LIMIT_WINDOW = 60  # 60 seconds
RATE_LIMIT_MAX_MESSAGES = 30  # max messages per window

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


class ChatBotConsumer(AsyncWebsocketConsumer):
    """
    ChatBot WebSocket Consumer
    支持实时流式传输意图分类、知识检索、工具执行进度
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chatbot_agent: ChatbotAgent | None = None

    async def connect(self):
        self.authenticated = False
        self.user = None
        self._message_count = 0
        self._window_start = time.time()
        
        await self.accept()
        logger.info(f"[ChatBotWS] WebSocket connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        logger.info(f"[ChatBotWS] WebSocket disconnected: {close_code}")
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        now = time.time()
        key = f"ws_{user_id}"
        
        messages = _rate_limit_store[key]
        messages = [t for t in messages if now - t < RATE_LIMIT_WINDOW]
        _rate_limit_store[key] = messages
        
        if len(messages) >= RATE_LIMIT_MAX_MESSAGES:
            return False
        
        _rate_limit_store[key].append(now)
        return True
    
    async def receive(self, text_data):
        """处理接收到的消息"""
        if len(text_data) > MAX_MESSAGE_SIZE:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Message too large'
            }))
            return
        
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            
            if msg_type == 'auth':
                await self.handle_auth(data)
            elif msg_type == 'chat':
                await self.handle_chat(data)
            else:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}'
                }))
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"[ChatBotWS] Error processing message: {e}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def handle_auth(self, data):
        """处理认证消息"""
        token = data.get('token')
        
        if not token:
            await self.send(json.dumps({
                'type': 'auth_error',
                'message': 'Token required'
            }))
            return
        
        def get_user_sync(token_key):
            middleware = TokenAuthMiddleware(lambda x: x)
            return middleware.get_user_from_token(token_key)
        
        try:
            user = await sync_to_async(get_user_sync)(token)
        except Exception as e:
            logger.error(f"[ChatBotWS] Token auth error: {e}")
            user = None
        
        if user is not None and getattr(user, 'id', None):
            self.authenticated = True
            self.user = user
            await self.send(json.dumps({
                'type': 'auth_success',
                'message': 'Authenticated successfully'
            }))
        else:
            await self.send(json.dumps({
                'type': 'auth_error',
                'message': 'Invalid token'
            }))
    
    async def handle_chat(self, data):
        """处理聊天消息"""
        if not self.authenticated:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Authentication required'
            }))
            return
        
        user_id = getattr(self.user, 'id', None)
        if user_id and not self._check_rate_limit(user_id):
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Rate limit exceeded. Please wait before sending more messages.'
            }))
            return
        
        message = data.get('message', '').strip()
        if not message:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Message cannot be empty'
            }))
            return
        
        await self.send(json.dumps({
            'type': 'processing',
            'message': 'Starting chat processing...'
        }))
        
        async def send_progress(msg):
            await self.send(json.dumps(msg))
        
        # Cache agent instance and conversation_id across messages within same WebSocket session
        if self._chatbot_agent is None:
            llm_service = get_llm_service('qwen')
            self._chatbot_agent = ChatbotAgent(llm_service=llm_service)
            await self._chatbot_agent.initialize()

        conversation_id = data.get('conversation_id') or getattr(self, '_conversation_id', None)
        if not conversation_id:
            from core.services.conversation_service import ConversationService
            from django.contrib.auth.models import User
            current_user = self.user
            if not isinstance(current_user, User):
                await self.send(json.dumps({
                    'type': 'error',
                    'message': '未认证用户'
                }))
                return
            conversation, error = await sync_to_async(ConversationService.create_conversation)(
                user=current_user
            )
            if error or conversation is None:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': error or '创建会话失败'
                }))
                return
            self._conversation_id = str(conversation.conversation_id)
            conversation_id = self._conversation_id
        elif not getattr(self, '_conversation_id', None):
            self._conversation_id = conversation_id

        input_data = {
            "message": message,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "context": {}
        }
        
        try:
            result = await self._chatbot_agent.execute(input_data)
            await self.send(json.dumps({
                'type': 'complete',
                'result': result
            }))
        except Exception as e:
            logger.error(f"[ChatBotWS] Chat execution error: {e}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def chat_message(self, event):
        """处理来自channel layer的群组消息"""
        message = event['message']
        await self.send(text_data=json.dumps(message))



