"""
压力测试 WebSocket Consumers

压力测试（基础 + Locust 高级）的 WebSocket 实时通信，
与 REST API 同属 testmanager_app 层。

迁移自 test_ui_app/consumers.py 和 test_ui_app/advanced_pressure_consumers.py
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


# =========================================================================
# 基础压测 Consumer
# =========================================================================


class PressureTestConsumer(AsyncWebsocketConsumer):
    """基础压测 WebSocket Consumer"""

    async def connect(self) -> None:
        self.execution_id = self.scope.get('url_route', {}).get('kwargs', {}).get('execution_id')
        self.authenticated = False
        self.user: Any = None
        self.engine: Any = None

        logger.info(f'[PressureTestWS] Connect attempt - execution_id={self.execution_id}')

        from testmanager_app.models import PressureTestExecution

        @sync_to_async
        def get_execution() -> Any:
            try:
                return PressureTestExecution.objects.get(pk=self.execution_id)
            except PressureTestExecution.DoesNotExist:
                return None

        execution = await get_execution()

        if execution is None:
            logger.warning(f'[PressureTestWS] Reject connection - execution_id={self.execution_id} not found')
            await self.close()
            return

        await self.accept()
        logger.info(f'[PressureTestWS] Connected - execution_id={self.execution_id}, channel={self.channel_name}')

    async def disconnect(self, close_code: int) -> None:
        logger.info(f'[PressureTestWS] Disconnecting - execution_id={self.execution_id}, close_code={close_code}')
        if self.engine:
            try:
                await self.engine.stop()
            except Exception as e:
                logger.error(f'[PressureTestWS] Error stopping engine: {e}')

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'auth':
                await self.handle_auth(data)
            elif msg_type == 'start':
                await self.handle_start(data)
            elif msg_type == 'stop':
                await self.handle_stop()
            else:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}',
                }))
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))
        except Exception as e:
            logger.error(f'[PressureTestWS] Error: {e}', exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e),
            }))

    async def handle_auth(self, data: Dict[str, Any]) -> None:
        from test_ui_app.middleware import TokenAuthMiddleware

        token = data.get('token')
        if not token:
            await self.send(json.dumps({
                'type': 'auth_error',
                'message': 'Token required',
            }))
            return

        try:
            middleware = TokenAuthMiddleware(lambda x: x)
            user = await middleware.get_user_from_token(token)
        except Exception as e:
            logger.error(f'[PressureTestWS] Auth error: {e}')
            user = None

        if user is not None and getattr(user, 'id', None):
            self.authenticated = True
            self.user = user
            await self.send(json.dumps({
                'type': 'auth_success',
                'message': 'Authenticated successfully',
            }))
        else:
            await self.send(json.dumps({
                'type': 'auth_error',
                'message': 'Invalid token',
            }))

    async def handle_start(self, data: Dict[str, Any]) -> None:
        if not self.authenticated:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Authentication required',
            }))
            return

        if not self.execution_id:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'execution_id not found in URL',
            }))
            return

        try:
            from testmanager_app.models import PressureTestExecution, PressureTestConfig

            @sync_to_async
            def get_execution_and_config() -> tuple:
                execution = PressureTestExecution.objects.select_related(
                    'config', 'config__api_request',
                ).get(pk=self.execution_id)
                return execution, execution.config

            execution, config = await get_execution_and_config()

            if execution.status not in ['pending', 'running']:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Execution already completed with status: {execution.status}',
                }))
                return

            from testmanager_app.services.execution_engine.pressure_test_engine import (
                PressureTestEngine,
            )
            self.engine = PressureTestEngine(config, websocket=self)

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
                },
            }))

            execution = await self.engine.execute_existing(execution)

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
                    'duration_seconds': execution.duration_seconds,
                },
            }))

        except Exception as e:
            logger.error(f'[PressureTestWS] Execution error: {e}', exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Execution failed: {str(e)}',
            }))

    async def handle_stop(self) -> None:
        if self.engine:
            await self.engine.stop()
            await self.send(json.dumps({
                'type': 'stopped',
                'message': 'Pressure test stopped by user',
            }))
        else:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'No running pressure test',
            }))

    async def send_result(self, result: Any) -> None:
        try:
            await self.send(json.dumps({
                'type': 'result',
                'index': result.index,
                'status_code': result.status_code,
                'response_time': result.response_time_ms,
                'success': result.success,
                'timestamp': result.timestamp.isoformat(),
            }))
        except Exception as e:
            logger.error(f'[PressureTestWS] Send result error: {e}')

    async def send_stats(self, stats: Any) -> None:
        try:
            await self.send(json.dumps({
                'type': 'stats',
                'completed': stats.completed,
                'total': stats.total,
                'success_rate': stats.success_rate,
                'avg_response_time': stats.avg_response_time,
                'rps': stats.rps,
            }))
        except Exception as e:
            logger.error(f'[PressureTestWS] Send stats error: {e}')


# =========================================================================
# 高级压测 Consumer
# =========================================================================


class AdvancedPressureTestConsumer(AsyncWebsocketConsumer):
    """高级压测（Locust）WebSocket Consumer"""

    async def connect(self) -> None:
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'advanced_pressure_test_{self.execution_id}'

        logger.info(f'[AdvancedPressureWS] === Step 2/3 === WS connect - execution_id={self.execution_id}')

        query_string = self.scope['query_string'].decode()
        token: Optional[str] = None
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]

        token_preview = f'"{token[:20]}..."' if token else 'None'
        logger.info(f'[AdvancedPressureWS]     token received: {token_preview} (len={len(token) if token else 0})')
        self.authenticated = await self._authenticate_token(token)

        if not self.authenticated:
            logger.warning(f'[AdvancedPressureWS]     token rejected, closing')
            await self.close(code=4001)
            return

        logger.info(f'[AdvancedPressureWS]     token validated, joining group')

        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name,
        )

        await self.accept()
        logger.info(f'[AdvancedPressureWS] === Step 2/3 done === Connected, waiting for {{type: "start"}} message')

        await self.send(json.dumps({
            'type': 'connected',
            'message': 'WebSocket连接成功',
            'execution_id': self.execution_id,
        }))

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name,
        )

        if hasattr(self, 'engine') and self.engine:
            try:
                await self.engine.stop()
            except Exception as e:
                logger.error(f'[AdvancedPressureWS] Error stopping engine: {e}')

        logger.info(f'[AdvancedPressureWS] Disconnected - execution_id={self.execution_id}, code={close_code}')

    async def receive(self, text_data: str) -> None:
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
                    'message': f'Unknown message type: {message_type}',
                }))

        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))
        except Exception as e:
            logger.error(f'[AdvancedPressureWS] Receive error: {e}', exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Error: {str(e)}',
            }))

    async def handle_start(self) -> None:
        from testmanager_app.models import AdvancedPressureTestConfig, AdvancedPressureTestExecution
        from testmanager_app.services.execution_engine.locust_engine import LocustEngine

        try:
            logger.info(f'[AdvancedPressureWS] === Step 3/3 === WS {{type: "start"}} received - execution_id={self.execution_id}')

            execution = await database_sync_to_async(
                lambda: AdvancedPressureTestExecution.objects.select_related('config').get(
                    id=self.execution_id,
                ),
            )()

            config = execution.config
            logger.info(f'[AdvancedPressureWS]     execution status={execution.status}, config_id={config.id}, name={config.name}')

            if execution.status not in ['pending', 'running']:
                logger.warning(f'[AdvancedPressureWS]     rejected - status={execution.status}')
                await self.send(json.dumps({
                    'type': 'error',
                    'message': f'Execution already completed with status: {execution.status}',
                }))
                return

            logger.info('[AdvancedPressureWS]     creating LocustEngine, starting in background')
            self.engine = LocustEngine(config, websocket=self)

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
                },
            }))

            # Background: 引擎自行管理生命周期，通过 WS push stats/complete
            asyncio.ensure_future(self.engine.execute_existing(execution))

        except Exception as e:
            logger.error(f'[AdvancedPressureWS] Execution error: {e}', exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Execution failed: {str(e)}',
            }))

    async def handle_stop(self) -> None:
        if hasattr(self, 'engine') and self.engine:
            await self.engine.stop()
            await self.send(json.dumps({
                'type': 'stopped',
                'message': 'Pressure test stopped by user',
            }))
        else:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'No running pressure test',
            }))

    async def stop_test(self, event: Dict[str, Any]) -> None:
        logger.info('[AdvancedPressureWS] Stop signal received from channel layer')
        if hasattr(self, 'engine') and self.engine:
            await self.engine.stop()

    async def send_result(self, result: Any) -> None:
        try:
            await self.send(json.dumps({
                'type': 'result',
                'name': result.name,
                'request_type': result.request_type,
                'response_time': result.response_time_ms,
                'response_length': result.response_length,
                'success': result.success,
                'error_message': result.error_message,
                'timestamp': result.timestamp.isoformat(),
            }))
        except Exception as e:
            logger.error(f'[AdvancedPressureWS] Send result error: {e}')

    async def send_stats(self, stats: Any) -> None:
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
                'peak_users': stats.peak_users,
            }))
        except Exception as e:
            logger.error(f'[AdvancedPressureWS] Send stats error: {e}')

    async def send_worker_status(self, workers: Any) -> None:
        try:
            await self.send(json.dumps({
                'type': 'worker_status',
                'workers': workers,
            }))
        except Exception as e:
            logger.error(f'[AdvancedPressureWS] Send worker status error: {e}')

    async def send_stats_summary(self, stats: Dict[str, Any]) -> None:
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
                'requests_per_endpoint': stats.get('requests_per_endpoint', {}),
            }))
        except Exception as e:
            logger.error(f'[AdvancedPressureWS] Send stats summary error: {e}')

    @database_sync_to_async
    def _authenticate_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        try:
            from testmanager_app.models import AuthToken
            AuthToken.objects.get(key=token, is_active=True)
            return True
        except AuthToken.DoesNotExist:
            return False
