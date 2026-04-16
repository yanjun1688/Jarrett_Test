"""
高级压测WebSocket Consumer
基于Locust的实时通信
"""

import json
import logging
from typing import Any, Dict, Optional

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class AdvancedPressureTestConsumer(AsyncWebsocketConsumer):
    """高级压测WebSocket Consumer"""
    
    async def connect(self):
        """WebSocket连接"""
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f"advanced_pressure_test_{self.execution_id}"
        
        # 获取token进行认证
        query_string = self.scope['query_string'].decode()
        token = None
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]
        
        # 认证检查
        self.authenticated = await self._authenticate_token(token)
        
        if not self.authenticated:
            logger.warning(f"[AdvancedPressureWS] Connection rejected - invalid token for execution {self.execution_id}")
            await self.close(code=4001)
            return
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"[AdvancedPressureWS] Connected - execution_id={self.execution_id}")
        
        # 发送连接成功消息
        await self.send(json.dumps({
            'type': 'connected',
            'message': 'WebSocket连接成功',
            'execution_id': self.execution_id
        }))
    
    async def disconnect(self, close_code):
        """断开连接"""
        # 离开房间组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # 停止引擎（如果运行中）
        if hasattr(self, 'engine') and self.engine:
            try:
                await self.engine.stop()
            except Exception as e:
                logger.error(f"[AdvancedPressureWS] Error stopping engine: {e}")
        
        logger.info(f"[AdvancedPressureWS] Disconnected - execution_id={self.execution_id}, code={close_code}")
    
    async def receive(self, text_data):
        """接收消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'start':
                await self.handle_start()
            elif message_type == 'stop':
                await self.handle_stop()
            else:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"[AdvancedPressureWS] Receive error: {e}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Error: {str(e)}'
            }))
    
    async def handle_start(self):
        """开始压测"""
        from testmanager_app.models import AdvancedPressureTestConfig, AdvancedPressureTestExecution
        from testmanager_app.services.execution_engine.locust_engine import LocustEngine
        
        try:
            logger.info(f"[AdvancedPressureWS] Start requested - execution_id={self.execution_id}")
            
            # 获取执行记录
            execution = await database_sync_to_async(
                lambda: AdvancedPressureTestExecution.objects.select_related('config').get(id=self.execution_id)
            )()
            
            config = execution.config
            
            logger.info(f"[AdvancedPressureWS] Got config - id={config.id}, name={config.name}, "
                        f"distributed={config.use_distributed}, workers={config.worker_count}")
            
            if execution.status not in ['pending', 'running']:
                logger.warning(f"[AdvancedPressureWS] Start rejected - execution already {execution.status}")
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Execution already completed with status: {execution.status}'
                }))
                return
            
            # 创建引擎
            logger.info(f"[AdvancedPressureWS] Creating Locust engine...")
            self.engine = LocustEngine(config, websocket=self)
            logger.info(f"[AdvancedPressureWS] Engine created")
            
            # 发送开始消息
            await self.send(json.dumps({
                'type': 'started',
                'execution_id': self.execution_id,
                'message': 'Advanced pressure test started',
                'config': {
                    'name': config.name,
                    'user_count': config.user_count,
                    'spawn_rate': config.spawn_rate,
                    'duration_seconds': config.duration_seconds,
                    'use_distributed': config.use_distributed,
                    'worker_count': config.worker_count if config.use_distributed else 1,
                    'web_ui_url': f"http://localhost:{config.web_ui_port}" if config.enable_web_ui else None
                }
            }))
            
            logger.info(f"[AdvancedPressureWS] Started message sent, beginning execution...")
            
            # 执行压测
            execution = await self.engine.execute_existing(execution)
            logger.info(f"[AdvancedPressureWS] Execution completed - status={execution.status}, "
                        f"total={execution.total_requests}, success={execution.success_count}")
            
            # 发送完成消息（包含完整统计）
            await self.send(json.dumps({
                'type': 'complete',
                'execution_id': execution.id,
                'message': 'Advanced pressure test completed',
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
                    'peak_users': execution.peak_users,
                    'duration_seconds': execution.duration_seconds,
                    'requests_per_endpoint': getattr(self.engine, '_parsed_stats', {}).get('requests_per_endpoint', {})
                }
            }))
            logger.info(f"[AdvancedPressureWS] Complete message sent")
        
        except Exception as e:
            logger.error(f"[AdvancedPressureWS] Execution error: {e}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Execution failed: {str(e)}'
            }))
    
    async def handle_stop(self):
        """停止压测"""
        if hasattr(self, 'engine') and self.engine:
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
    
    async def stop_test(self, event):
        """处理来自channel layer的停止消息"""
        logger.info(f"[AdvancedPressureWS] Stop signal received from channel layer")
        if hasattr(self, 'engine') and self.engine:
            await self.engine.stop()
    
    async def send_result(self, result):
        """推送单次请求结果"""
        try:
            await self.send(json.dumps({
                'type': 'result',
                'name': result.name,
                'request_type': result.request_type,
                'response_time': result.response_time_ms,
                'response_length': result.response_length,
                'success': result.success,
                'error_message': result.error_message,
                'timestamp': result.timestamp.isoformat()
            }))
        except Exception as e:
            logger.error(f"[AdvancedPressureWS] Send result error: {e}")
    
    async def send_stats(self, stats):
        """推送实时统计"""
        try:
            await self.send(json.dumps({
                'type': 'stats',
                'current_users': stats.current_users,
                'total_requests': stats.total_requests,
                'success_count': stats.success_count,
                'failed_count': stats.failed_count,
                'rps': stats.rps,
                'fail_ratio': stats.fail_ratio,
                'avg_response_time': stats.avg_response_time,
                'min_response_time': stats.min_response_time,
                'max_response_time': stats.max_response_time,
                'peak_users': stats.peak_users
            }))
        except Exception as e:
            logger.error(f"[AdvancedPressureWS] Send stats error: {e}")
    
    async def send_worker_status(self, workers):
        """推送Worker状态"""
        try:
            await self.send(json.dumps({
                'type': 'worker_status',
                'workers': workers
            }))
        except Exception as e:
            logger.error(f"[AdvancedPressureWS] Send worker status error: {e}")
    
    async def send_stats_summary(self, stats: Dict[str, Any]) -> None:
        """推送统计汇总（CSV方案）"""
        try:
            await self.send(json.dumps({
                'type': 'stats_summary',
                'total_requests': stats.get('total_requests', 0),
                'success_count': stats.get('success_count', 0),
                'failed_count': stats.get('failed_count', 0),
                'error_rate': stats.get('error_rate', 0.0),
                'avg_response_time': stats.get('avg_response_time', 0.0),
                'min_response_time': stats.get('min_response_time', 0.0),
                'max_response_time': stats.get('max_response_time', 0.0),
                'p50_response_time': stats.get('p50_response_time', 0.0),
                'p90_response_time': stats.get('p90_response_time', 0.0),
                'p95_response_time': stats.get('p95_response_time', 0.0),
                'p99_response_time': stats.get('p99_response_time', 0.0),
                'throughput': stats.get('throughput', 0.0),
                'peak_users': stats.get('peak_users', 0),
                'duration_seconds': stats.get('duration_seconds', 0),
                'requests_per_endpoint': stats.get('requests_per_endpoint', {})
            }))
            logger.info(f"[AdvancedPressureWS] Stats summary sent: {stats.get('total_requests', 0)} requests")
        except Exception as e:
            logger.error(f"[AdvancedPressureWS] Send stats summary error: {e}")
    
    @database_sync_to_async
    def _authenticate_token(self, token: Optional[str]) -> bool:
        """认证token"""
        if not token:
            return False
        
        try:
            from rest_framework.authtoken.models import Token
            Token.objects.get(key=token)
            return True
        except Token.DoesNotExist:
            return False