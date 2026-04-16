"""
压测执行引擎
支持三种压测模式：瞬时并发、持续并发、分批并发
"""

import asyncio
import time
import math
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from asgiref.sync import sync_to_async
import httpx

logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    """单次请求结果"""
    index: int
    status_code: Optional[int]
    response_time_ms: float
    success: bool
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RealtimeStats:
    """实时统计数据"""
    completed: int = 0
    total: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    rps: float = 0.0
    current_concurrent: int = 0
    peak_concurrent: int = 0  # 峰值并发数


class MetricsCollector:
    """指标收集器（简化锁策略）"""
    
    def __init__(self):
        self.results: List[RequestResult] = []
        self.start_time: Optional[datetime] = None
        self.peak_concurrent = 0
    
    def start(self):
        """开始收集"""
        self.start_time = datetime.now()
    
    async def add_result(self, result: RequestResult) -> None:
        """添加单次结果（asyncio 单线程，append 是原子操作，无需锁）"""
        self.results.append(result)
    
    async def update_peak_concurrent(self, current: int) -> None:
        """更新峰值并发数（asyncio 单线程，整数操作是原子，无需锁）"""
        if current > self.peak_concurrent:
            self.peak_concurrent = current
    
    def get_realtime_stats(self, total: int, current_concurrent: int = 0) -> RealtimeStats:
        """获取实时统计（读取时复制数据，避免不一致）"""
        if not self.results or not self.start_time:
            return RealtimeStats(total=total, current_concurrent=current_concurrent, peak_concurrent=self.peak_concurrent)
        
        results_snapshot = self.results.copy()
        completed = len(results_snapshot)
        success_count = sum(1 for r in results_snapshot if r.success)
        response_times = [r.response_time_ms for r in results_snapshot]
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return RealtimeStats(
            completed=completed,
            total=total,
            success_rate=round(success_count / completed * 100, 2) if completed > 0 else 0,
            avg_response_time=round(sum(response_times) / len(response_times), 2) if response_times else 0,
            rps=round(completed / elapsed, 2) if elapsed > 0 else 0,
            current_concurrent=current_concurrent,
            peak_concurrent=self.peak_concurrent
        )
    
    def calculate_final_stats(self) -> Dict[str, Any]:
        """计算最终统计"""
        if not self.results:
            return {}
        
        response_times = [r.response_time_ms for r in self.results]
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        
        def percentile(p: float) -> float:
            """计算百分位数"""
            if n == 0:
                return 0
            k = (n - 1) * p / 100
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_times[int(k)]
            return sorted_times[f] * (c - k) + sorted_times[c] * (k - f)
        
        success_count = sum(1 for r in self.results if r.success)
        
        elapsed = 0.0
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'total_requests': n,
            'success_count': success_count,
            'failed_count': n - success_count,
            'error_rate': round((n - success_count) / n * 100, 2) if n > 0 else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'avg_response_time': round(sum(response_times) / n, 2) if n > 0 else 0,
            'p50_response_time': round(percentile(50), 2),
            'p90_response_time': round(percentile(90), 2),
            'p95_response_time': round(percentile(95), 2),
            'p99_response_time': round(percentile(99), 2),
            'throughput': round(n / elapsed, 2) if elapsed > 0 else 0,
        }


class PressureTestEngine:
    """压测执行引擎"""
    
    def __init__(self, config, websocket=None):
        """
        初始化压测引擎
        
        Args:
            config: PressureTestConfig 实例
            websocket: WebSocket consumer 实例（可选）
        """
        from testmanager_app.models import PressureTestConfig
        self.config: PressureTestConfig = config
        self.api_request = config.api_request
        self.websocket = websocket
        self.metrics = MetricsCollector()
        self.stop_event = asyncio.Event()
        self._active_count = 0
        self._execution = None
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"[PressureEngine] Initialized - config_id={config.id}, mode={config.pressure_mode}")
        logger.info(f"[PressureEngine] Config details: request_count={config.request_count}, "
                    f"rate={config.rate_per_second}, duration={config.duration_seconds}s, "
                    f"batch_size={config.batch_size}, batch_interval={config.batch_interval}s, "
                    f"max_concurrent={config.max_concurrent}")
        logger.info(f"[PressureEngine] Target API: {config.api_request.method} {config.api_request.url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建共享的 AsyncClient（连接池复用）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(
                    max_connections=self.config.max_concurrent,
                    max_keepalive_connections=self.config.max_concurrent,
                    keepalive_expiry=30.0
                )
            )
            logger.info(f"[PressureEngine] Created shared AsyncClient with "
                        f"max_connections={self.config.max_concurrent}")
        return self._client
    
    async def _close_client(self) -> None:
        """关闭共享的 AsyncClient"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info(f"[PressureEngine] Closed AsyncClient")
    
    async def create_execution_only(self) -> Any:
        """
        仅创建执行记录，不执行
        
        Returns:
            PressureTestExecution 实例
        """
        self._execution = await self._create_execution()
        return self._execution
    
    async def execute_existing(self, execution: Any) -> Any:
        """
        执行已存在的 execution 记录
        
        Args:
            execution: PressureTestExecution 实例
            
        Returns:
            PressureTestExecution 实例
        """
        self._execution = execution
        logger.info(f"[PressureEngine] execute_existing called - execution_id={execution.id}")
        
        strategy_map = {
            'instant': self._execute_instant,
            'sustained': self._execute_sustained,
            'batch': self._execute_batch,
        }
        
        strategy = strategy_map.get(self.config.pressure_mode)
        if not strategy:
            logger.error(f"[PressureEngine] Unknown mode: {self.config.pressure_mode}")
            raise ValueError(f"未知的压测模式: {self.config.pressure_mode}")
        
        logger.info(f"[PressureEngine] Using strategy: {self.config.pressure_mode}")
        
        try:
            await self._update_execution_status(execution, 'running')
            logger.info(f"[PressureEngine] Status updated to 'running'")
            self.metrics.start()
            logger.info(f"[PressureEngine] Metrics collector started")
            
            logger.info(f"[PressureEngine] Beginning execution...")
            await strategy()
            logger.info(f"[PressureEngine] Strategy completed")
            
            final_stats = self.metrics.calculate_final_stats()
            logger.info(f"[PressureEngine] Final stats calculated: total={final_stats.get('total_requests')}, "
                        f"success={final_stats.get('success_count')}, failed={final_stats.get('failed_count')}, "
                        f"avg_time={final_stats.get('avg_response_time')}ms")
            await self._update_execution_complete(execution, final_stats, 'completed')
            logger.info(f"[PressureEngine] Execution marked as 'completed'")
            
        except asyncio.CancelledError:
            logger.warning(f"[PressureEngine] Execution cancelled")
            final_stats = self.metrics.calculate_final_stats()
            await self._update_execution_complete(execution, final_stats, 'stopped')
            raise
        except Exception as e:
            logger.error(f"[PressureEngine] Execution failed: {e}", exc_info=True)
            final_stats = self.metrics.calculate_final_stats()
            await self._update_execution_complete(execution, final_stats, 'failed')
            raise
        finally:
            await self._close_client()
        
        return execution
    
    async def stop(self):
        """停止压测"""
        self.stop_event.set()
        await self._close_client()
    
    async def _create_execution(self):
        """创建执行记录"""
        from testmanager_app.models import PressureTestExecution
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create():
            return PressureTestExecution.objects.create(
                config=self.config,
                status='pending'
            )
        
        return await create()
    
    async def _update_execution_status(self, execution: Any, status: str) -> None:
        """更新执行状态"""
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        
        @sync_to_async
        def update():
            execution.status = status
            if status == 'running':
                execution.started_at = timezone.now()
            execution.save()
        
        await update()
    
    async def _update_execution_complete(self, execution: Any, stats: Dict[str, Any], status: str) -> None:
        """更新执行完成状态"""
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        
        @sync_to_async
        def update():
            execution.status = status
            execution.finished_at = timezone.now()
            if execution.started_at:
                execution.duration_seconds = (execution.finished_at - execution.started_at).total_seconds()
            
            # 基础统计
            execution.total_requests = stats.get('total_requests', 0)
            execution.success_count = stats.get('success_count', 0)
            execution.failed_count = stats.get('failed_count', 0)
            execution.error_rate = stats.get('error_rate', 0)
            
            # 响应时间统计
            execution.min_response_time = stats.get('min_response_time')
            execution.max_response_time = stats.get('max_response_time')
            execution.avg_response_time = stats.get('avg_response_time')
            execution.p50_response_time = stats.get('p50_response_time')
            execution.p90_response_time = stats.get('p90_response_time')
            execution.p95_response_time = stats.get('p95_response_time')
            execution.p99_response_time = stats.get('p99_response_time')
            
            # 吞吐量
            execution.throughput = stats.get('throughput', 0)
            
            # 峰值并发数
            execution.peak_concurrent = self.metrics.peak_concurrent
            
            # 保存原始结果
            execution.raw_results = [
                {
                    'index': r.index,
                    'status_code': r.status_code,
                    'response_time_ms': r.response_time_ms,
                    'success': r.success,
                    'error_message': r.error_message,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in self.metrics.results
            ]
            
            execution.save()
        
        await update()
    
    async def _execute_single(self, index: int) -> RequestResult:
        """执行单个请求（使用共享 AsyncClient）"""
        import time
        
        start_time = time.time()
        logger.debug(f"[PressureEngine] Request {index}: Starting")
        
        try:
            method = self.api_request.method
            url = self.api_request.url
            headers = self._parse_headers(self.api_request.headers)
            body = self.api_request.body
            
            logger.debug(f"[PressureEngine] Request {index}: {method} {url}")
            
            client = await self._get_client()
            
            if body and method in ['POST', 'PUT', 'PATCH']:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body.encode('utf-8') if isinstance(body, str) else body
                )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers
                )
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"[PressureEngine] Request {index}: Completed in {elapsed_ms:.2f}ms, "
                        f"status={response.status_code}")
            
            return RequestResult(
                index=index,
                status_code=response.status_code,
                response_time_ms=round(elapsed_ms, 2),
                success=200 <= response.status_code < 400
            )
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(f"[PressureEngine] Request {index}: Failed after {elapsed_ms:.2f}ms - {e}")
            return RequestResult(
                index=index,
                status_code=None,
                response_time_ms=round(elapsed_ms, 2),
                success=False,
                error_message=str(e)
            )
    
    def _parse_headers(self, headers: Any) -> Dict[str, str]:
        """解析请求头"""
        import json
        if isinstance(headers, dict):
            return headers
        if isinstance(headers, str):
            try:
                parsed = json.loads(headers)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return {}
            except:
                return {}
        return {}
    
    async def _on_request_complete(self, result: RequestResult, total: int, current_concurrent: int = 0) -> None:
        """请求完成回调"""
        await self.metrics.add_result(result)
        
        # 更新峰值并发数
        await self.metrics.update_peak_concurrent(current_concurrent)
        
        # 推送 WebSocket 消息
        if self.websocket:
            try:
                await self.websocket.send_result(result)
                
                # 每秒推送一次统计
                stats = self.metrics.get_realtime_stats(total, current_concurrent)
                await self.websocket.send_stats(stats)
            except Exception:
                pass  # WebSocket 推送失败不影响执行
    
    async def _execute_instant(self):
        """瞬时并发：同时发起N个请求"""
        total = self.config.request_count
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        logger.info(f"[PressureEngine] _execute_instant: total={total}, max_concurrent={self.config.max_concurrent}")
        
        async def bounded_request(index: int) -> None:
            async with semaphore:
                if self.stop_event.is_set():
                    return
                
                self._active_count += 1
                current = self._active_count
                
                try:
                    result = await self._execute_single(index)
                    await self._on_request_complete(result, total, current)
                finally:
                    self._active_count -= 1
        
        tasks = [bounded_request(i) for i in range(total)]
        logger.info(f"[PressureEngine] Created {len(tasks)} tasks")
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"[PressureEngine] All tasks completed")
    
    async def _execute_sustained(self):
        """持续并发：每秒X个，持续Y秒（方案二改进版：等待发送时间 + semaphore）"""
        total = self.config.rate_per_second * self.config.duration_seconds
        MAX_TOTAL_REQUESTS = 5000  # 保守方案：单机压测安全上限
        if total > MAX_TOTAL_REQUESTS:
            logger.error(f"[PressureEngine] Total requests exceeds limit: {total} > {MAX_TOTAL_REQUESTS}")
            raise ValueError(f"持续并发模式总请求数超过上限 ({total} > {MAX_TOTAL_REQUESTS})，请降低 rate_per_second 或 duration_seconds")
        
        interval = 1.0 / self.config.rate_per_second
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        start_time = time.time()
        
        logger.info(f"[PressureEngine] _execute_sustained: total={total}, rate={self.config.rate_per_second}/s, "
                    f"duration={self.config.duration_seconds}s, interval={interval}s, max_concurrent={self.config.max_concurrent}")
        
        async def bounded_request(index: int) -> None:
            # 1. 先等待到发送时间（独立于 semaphore）
            send_time = start_time + index * interval
            wait_time = send_time - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # 2. 获取 semaphore 后实际发送
            async with semaphore:
                if self.stop_event.is_set():
                    return
                
                self._active_count += 1
                current = self._active_count
                
                try:
                    result = await self._execute_single(index)
                    await self._on_request_complete(result, total, current)
                finally:
                    self._active_count -= 1
        
        # 同时创建所有任务，每个任务内部控制发送时间
        tasks = [asyncio.create_task(bounded_request(i)) for i in range(total)]
        logger.info(f"[PressureEngine] Created {len(tasks)} tasks with rate control")
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"[PressureEngine] All sustained tasks completed")
    
    async def _execute_batch(self):
        """分批并发：每批N个，间隔T秒"""
        total = self.config.request_count
        batch_size = self.config.batch_size
        batch_interval = self.config.batch_interval
        
        total_batches = math.ceil(total / batch_size)
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        logger.info(f"[PressureEngine] _execute_batch: total={total}, batch_size={batch_size}, "
                    f"batch_interval={batch_interval}s, total_batches={total_batches}, max_concurrent={self.config.max_concurrent}")
        
        async def bounded_request(index: int) -> None:
            async with semaphore:
                if self.stop_event.is_set():
                    return
                
                self._active_count += 1
                current = self._active_count
                
                try:
                    result = await self._execute_single(index)
                    await self._on_request_complete(result, total, current)
                finally:
                    self._active_count -= 1
        
        for batch_idx in range(total_batches):
            if self.stop_event.is_set():
                logger.warning(f"[PressureEngine] Stopped at batch {batch_idx}/{total_batches}")
                break
            
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total)
            logger.info(f"[PressureEngine] Starting batch {batch_idx + 1}/{total_batches}: "
                        f"requests {start_idx}-{end_idx - 1}")
            
            tasks = [bounded_request(i) for i in range(start_idx, end_idx)]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"[PressureEngine] Batch {batch_idx + 1} completed")
            
            if batch_idx < total_batches - 1 and not self.stop_event.is_set():
                logger.debug(f"[PressureEngine] Waiting {batch_interval}s before next batch")
                await asyncio.sleep(batch_interval)
        
        logger.info(f"[PressureEngine] All batches completed")
