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

_rate_limit_store = defaultdict(list)


class ChatBotConsumer(AsyncWebsocketConsumer):
    """
    ChatBot WebSocket Consumer
    支持实时流式传输意图分类、知识检索、工具执行进度
    """
    
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
        
        llm_service = get_llm_service('qwen')
        
        chatbot_agent = ChatbotAgent(
            llm_service=llm_service
        )
        await chatbot_agent.initialize()
        
        input_data = {
            "message": message,
            "user_id": user_id,
            "context": {}
        }
        
        try:
            result = await chatbot_agent.execute(input_data)
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


class PressureTestConsumer(AsyncWebsocketConsumer):
    """
    压测 WebSocket Consumer
    实时推送压测进度和性能指标
    """
    
    async def connect(self):
        self.execution_id = self.scope.get("url_route", {}).get("kwargs", {}).get("execution_id")
        self.authenticated = False
        self.user = None
        self.engine = None
        
        logger.info(f"[PressureTestWS] Connect attempt - execution_id={self.execution_id}")
        
        from testmanager_app.models import PressureTestExecution
        
        @sync_to_async
        def get_execution():
            try:
                return PressureTestExecution.objects.get(pk=self.execution_id)
            except PressureTestExecution.DoesNotExist:
                return None
        
        execution = await get_execution()
        
        if execution is None:
            logger.warning(f"[PressureTestWS] Reject connection - execution_id={self.execution_id} not found")
            await self.close()
            return
        
        logger.info(f"[PressureTestWS] Found execution - id={execution.id}, status={execution.status}, "
                    f"config_id={execution.config_id}")
        
        await self.accept()
        logger.info(f"[PressureTestWS] Connected - execution_id={self.execution_id}, channel={self.channel_name}")
    
    async def disconnect(self, close_code):
        """断开连接时停止压测"""
        logger.info(f"[PressureTestWS] Disconnecting - execution_id={self.execution_id}, close_code={close_code}")
        if self.engine:
            try:
                await self.engine.stop()
                logger.info(f"[PressureTestWS] Engine stopped - execution_id={self.execution_id}")
            except Exception as e:
                logger.error(f"[PressureTestWS] Error stopping engine: {e}")
        
        logger.info(f"[PressureTestWS] Disconnected - execution_id={self.execution_id}")
    
    async def receive(self, text_data):
        """处理客户端消息"""
        logger.debug(f"[PressureTestWS] Received message - execution_id={self.execution_id}, "
                     f"length={len(text_data)}, authenticated={self.authenticated}")
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            logger.info(f"[PressureTestWS] Message type: {msg_type} - execution_id={self.execution_id}")
            
            if msg_type == 'auth':
                await self.handle_auth(data)
            elif msg_type == 'start':
                await self.handle_start(data)
            elif msg_type == 'stop':
                await self.handle_stop()
            else:
                logger.warning(f"[PressureTestWS] Unknown message type: {msg_type}")
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}'
                }))
        except json.JSONDecodeError as e:
            logger.error(f"[PressureTestWS] JSON decode error: {e}")
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"[PressureTestWS] Error: {e}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def handle_auth(self, data):
        """处理认证"""
        logger.info(f"[PressureTestWS] Auth request - execution_id={self.execution_id}")
        from test_ui_app.middleware import TokenAuthMiddleware
        
        token = data.get('token')
        if not token:
            logger.warning(f"[PressureTestWS] Auth failed - no token provided")
            await self.send(json.dumps({
                'type': 'auth_error',
                'message': 'Token required'
            }))
            return
        
        try:
            middleware = TokenAuthMiddleware(lambda x: x)
            user = await middleware.get_user_from_token(token)
        except Exception as e:
            logger.error(f"[PressureTestWS] Auth error: {e}")
            user = None
        
        if user is not None and getattr(user, 'id', None):
            self.authenticated = True
            self.user = user
            logger.info(f"[PressureTestWS] Auth success - user_id={user.id}, username={getattr(user, 'username', 'N/A')}")
            await self.send(json.dumps({
                'type': 'auth_success',
                'message': 'Authenticated successfully'
            }))
        else:
            logger.warning(f"[PressureTestWS] Auth failed - invalid token")
            await self.send(json.dumps({
                'type': 'auth_error',
                'message': 'Invalid token'
            }))
    
    async def handle_start(self, data):
        """开始压测"""
        logger.info(f"[PressureTestWS] Start request - execution_id={self.execution_id}, authenticated={self.authenticated}")
        if not self.authenticated:
            logger.warning(f"[PressureTestWS] Start rejected - not authenticated")
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Authentication required'
            }))
            return
        
        if not self.execution_id:
            logger.warning(f"[PressureTestWS] Start rejected - no execution_id")
            await self.send(json.dumps({
                'type': 'error',
                'message': 'execution_id not found in URL'
            }))
            return
        
        try:
            logger.info(f"[PressureTestWS] Fetching execution and config - execution_id={self.execution_id}")
            from testmanager_app.models import PressureTestExecution, PressureTestConfig
            
            @sync_to_async
            def get_execution_and_config():
                execution = PressureTestExecution.objects.select_related('config', 'config__api_request').get(pk=self.execution_id)
                return execution, execution.config
            
            execution, config = await get_execution_and_config()
            logger.info(f"[PressureTestWS] Got execution - status={execution.status}")
            logger.info(f"[PressureTestWS] Got config - id={config.id}, name={config.name}, "
                        f"mode={config.pressure_mode}, api_request_id={config.api_request_id}")
            logger.info(f"[PressureTestWS] API request - url={config.api_request.url}, method={config.api_request.method}")
            
            if execution.status not in ['pending', 'running']:
                logger.warning(f"[PressureTestWS] Start rejected - execution already {execution.status}")
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Execution already completed with status: {execution.status}'
                }))
                return
            
            logger.info(f"[PressureTestWS] Creating engine...")
            from testmanager_app.services.execution_engine.pressure_test_engine import PressureTestEngine
            self.engine = PressureTestEngine(config, websocket=self)
            logger.info(f"[PressureTestWS] Engine created - mode={config.pressure_mode}")
            
            await self.send(json.dumps({
                'type': 'started',
                'execution_id': self.execution_id,
                'message': 'Pressure test started',
                'config': {
                    'name': config.name,
                    'mode': config.pressure_mode,
                    'request_count': config.request_count if config.pressure_mode == 'instant' else None,
                    'rate_per_second': config.rate_per_second if config.pressure_mode == 'sustained' else None,
                    'duration_seconds': config.duration_seconds if config.pressure_mode == 'sustained' else None,
                }
            }))
            logger.info(f"[PressureTestWS] Started message sent, beginning execution...")
            
            execution = await self.engine.execute_existing(execution)
            logger.info(f"[PressureTestWS] Execution completed - status={execution.status}, "
                        f"total={execution.total_requests}, success={execution.success_count}")
            
            await self.send(json.dumps({
                'type': 'complete',
                'execution_id': execution.id,
                'message': 'Pressure test completed',
                'summary': {
                    'status': execution.status,
                    'total_requests': execution.total_requests,
                    'success_count': execution.success_count,
                    'failed_count': execution.failed_count,
                    'error_rate': execution.error_rate,
                    'avg_response_time': execution.avg_response_time,
                    'min_response_time': execution.min_response_time,
                    'max_response_time': execution.max_response_time,
                    'p50_response_time': execution.p50_response_time,
                    'p90_response_time': execution.p90_response_time,
                    'p95_response_time': execution.p95_response_time,
                    'p99_response_time': execution.p99_response_time,
                    'throughput': execution.throughput,
                    'peak_concurrent': execution.peak_concurrent,
                    'duration_seconds': execution.duration_seconds
                }
            }))
            logger.info(f"[PressureTestWS] Complete message sent")
            
        except Exception as e:
            logger.error(f"[PressureTestWS] Execution error: {e}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Execution failed: {str(e)}'
            }))
    
    async def handle_stop(self):
        """停止压测"""
        if self.engine:
            await self.engine.stop()
            await self.send(json.dumps({
                'type': 'stopped',
                'message': 'Pressure test stopped by user'
            }))
        else:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'No running pressure test'
            }))
    
    async def send_result(self, result):
        """推送单次请求结果"""
        try:
            await self.send(json.dumps({
                'type': 'result',
                'index': result.index,
                'status_code': result.status_code,
                'response_time': result.response_time_ms,
                'success': result.success,
                'timestamp': result.timestamp.isoformat()
            }))
        except Exception as e:
            logger.error(f"[PressureTestWS] Send result error: {e}")
    
    async def send_stats(self, stats):
        """推送实时统计"""
        try:
            await self.send(json.dumps({
                'type': 'stats',
                'completed': stats.completed,
                'total': stats.total,
                'success_rate': stats.success_rate,
                'avg_response_time': stats.avg_response_time,
                'rps': stats.rps
            }))
        except Exception as e:
            logger.error(f"[PressureTestWS] Send stats error: {e}")
