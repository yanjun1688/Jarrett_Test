"""
Locust高级压测引擎
支持分布式、事务编排、实时统计推送
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


@dataclass
class LocustRequestResult:
    """Locust单次请求结果"""
    name: str = ""
    request_type: str = ""
    response_time_ms: float = 0.0
    response_length: int = 0
    success: bool = True
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocustRealtimeStats:
    """Locust实时统计"""
    current_users: int = 0
    total_requests: int = 0
    success_count: int = 0
    failed_count: int = 0
    rps: float = 0.0
    fail_ratio: float = 0.0
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    peak_users: int = 0
    # 修复 - 添加缺失的属性
    success_rate: float = 0.0
    response_time_avg: float = 0.0
    current_rps: float = 0.0


class TransactionContext:
    """事务上下文，用于步骤间数据传递"""
    
    def __init__(self):
        self.variables: Dict[str, Any] = {}
    
    def set(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def render(self, template: str) -> str:
        """渲染模板，替换 ${variable} 格式的变量"""
        if not template:
            return template
        
        result = template
        for name, value in self.variables.items():
            placeholder = f'${{{name}}}'
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
    
    def render_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """渲染字典中的所有字符串值"""
        if not data:
            return data
        
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.render(value)
            elif isinstance(value, dict):
                result[key] = self.render_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.render(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class LocustMetricsCollector:
    """Locust指标收集器"""
    
    def __init__(self):
        self.results: List[LocustRequestResult] = []
        self.start_time: Optional[datetime] = None
        self.peak_users = 0
        self._lock = asyncio.Lock()
    
    def start(self) -> None:
        """开始收集"""
        self.start_time = datetime.now()
    
    async def add_result(self, result: LocustRequestResult) -> None:
        """添加结果"""
        async with self._lock:
            self.results.append(result)
    
    async def update_peak_users(self, current: int) -> None:
        """更新峰值用户数"""
        async with self._lock:
            self.peak_users = max(self.peak_users, current)
    
    def get_realtime_stats(self, current_users: int = 0) -> LocustRealtimeStats:
        """获取实时统计"""
        if not self.results or not self.start_time:
            return LocustRealtimeStats(current_users=current_users)
        
        total = len(self.results)
        success_count = sum(1 for r in self.results if r.success)
        failed_count = total - success_count
        
        response_times = [r.response_time_ms for r in self.results if r.success]
        avg_response_time = round(sum(response_times) / len(response_times), 2) if response_times else 0.0
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rps = round(total / elapsed, 2) if elapsed > 0 else 0.0
        fail_ratio = round(failed_count / total * 100, 2) if total > 0 else 0.0
        success_rate = round(success_count / total * 100, 2) if total > 0 else 0.0
        
        return LocustRealtimeStats(
            current_users=current_users,
            total_requests=total,
            success_count=success_count,
            failed_count=failed_count,
            rps=rps,
            fail_ratio=fail_ratio,
            avg_response_time=avg_response_time,
            min_response_time=min(response_times) if response_times else 0.0,
            max_response_time=max(response_times) if response_times else 0.0,
            peak_users=self.peak_users,
            success_rate=success_rate,
            response_time_avg=avg_response_time,
            current_rps=rps
        )
    
    def calculate_final_stats(self) -> Dict[str, Any]:
        """计算最终统计"""
        if not self.results:
            return {}
        
        total = len(self.results)
        success_count = sum(1 for r in self.results if r.success)
        failed_count = total - success_count
        
        response_times = [r.response_time_ms for r in self.results if r.success]
        
        if not response_times:
            response_times = [0]
        
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        
        def percentile(p: float) -> float:
            """计算百分位数"""
            if n == 0:
                return 0
            k = (n - 1) * p / 100
            f = int(k)
            c = f + 1 if f < n - 1 else f
            if f == c:
                return sorted_times[f]
            return sorted_times[f] * (c - k) + sorted_times[c] * (k - f)
        
        elapsed = 0
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'total_requests': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'error_rate': round(failed_count / total * 100, 2) if total > 0 else 0,
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'avg_response_time': round(sum(response_times) / n, 2) if n > 0 else 0,
            'p50_response_time': round(percentile(50), 2),
            'p90_response_time': round(percentile(90), 2),
            'p95_response_time': round(percentile(95), 2),
            'p99_response_time': round(percentile(99), 2),
            'throughput': round(total / elapsed, 2) if elapsed > 0 else 0,
            'peak_users': self.peak_users
        }


class LocustEngine:
    """Locust高级压测引擎"""
    
    def __init__(self, config: Any, websocket: Optional[Any] = None):
        """
        初始化Locust引擎
        
        Args:
            config: AdvancedPressureTestConfig 实例
            websocket: WebSocket consumer 实例（可选）
        """
        from testmanager_app.models import AdvancedPressureTestConfig
        
        self.config: AdvancedPressureTestConfig = config
        self.websocket = websocket
        self.metrics = LocustMetricsCollector()
        self.stop_event = asyncio.Event()
        self._execution = None
        self._worker_processes: List[subprocess.Popen] = []
        self._locustfile_path: Optional[str] = None
        self._parsed_stats: Optional[Dict[str, Any]] = None
        
        logger.info(f"[LocustEngine] Initialized - config_id={config.id}, name={config.name}")
        logger.info(f"[LocustEngine] Users={config.user_count}, spawn_rate={config.spawn_rate}, "
                    f"duration={config.duration_seconds}s")
        logger.info(f"[LocustEngine] Distributed={config.use_distributed}, workers={config.worker_count}")
    
    async def create_execution_only(self) -> Any:
        """仅创建执行记录"""
        self._execution = await self._create_execution()
        return self._execution
    
    async def execute_existing(self, execution: Any) -> Any:
        """执行已存在的execution记录"""
        self._execution = execution
        logger.info(f"[LocustEngine] execute_existing called - execution_id={execution.id}")
        
        try:
            logger.info("[LocustEngine] Step 1: Updating execution status to 'running'")
            await self._update_execution_status(execution, 'running')
            logger.info("[LocustEngine] Step 1 completed")
            
            logger.info("[LocustEngine] Step 2: Starting metrics collector")
            self.metrics.start()
            logger.info("[LocustEngine] Step 2 completed")
            
            logger.info("[LocustEngine] Step 3: Generating locustfile")
            self._locustfile_path = await self._generate_locustfile()
            logger.info(f"[LocustEngine] Step 3 completed - locustfile: {self._locustfile_path}")
            
            logger.info("[LocustEngine] Step 4: Starting pressure test")
            # 启动压测
            if self.config.use_distributed:
                logger.info("[LocustEngine] Using distributed mode")
                await self._run_distributed_mode()
            else:
                logger.info("[LocustEngine] Using standalone mode")
                await self._run_standalone_mode()
            logger.info("[LocustEngine] Step 4 completed - pressure test finished")
            
            logger.info("[LocustEngine] Step 5: Calculating final stats")
            # 计算最终统计 - 优先使用解析的统计数据（subprocess模式）
            if hasattr(self, '_parsed_stats') and self._parsed_stats:
                final_stats = self._parsed_stats
                logger.info(f"[LocustEngine] Step 5 completed - using parsed stats from subprocess: {final_stats}")
            else:
                final_stats = self.metrics.calculate_final_stats()
                logger.info(f"[LocustEngine] Step 5 completed - using metrics collector stats: {final_stats}")
            
            logger.info("[LocustEngine] Step 6: Updating execution complete status")
            await self._update_execution_complete(execution, final_stats, 'completed')
            logger.info("[LocustEngine] Step 6 completed")
            
            logger.info("[LocustEngine] Step 7: Generating report")
            await self._generate_report()
            logger.info("[LocustEngine] Step 7 completed")
            
        except asyncio.CancelledError:
            logger.warning(f"[LocustEngine] Execution cancelled")
            final_stats = self.metrics.calculate_final_stats()
            await self._update_execution_complete(execution, final_stats, 'stopped')
            raise
        except Exception as e:
            logger.error(f"[LocustEngine] Execution failed: {e}", exc_info=True)
            final_stats = self.metrics.calculate_final_stats()
            await self._update_execution_complete(execution, final_stats, 'failed', error=str(e))
            raise
        finally:
            logger.info("[LocustEngine] Step 8: Cleanup")
            self._cleanup()
            logger.info("[LocustEngine] Step 8 completed")
        
        logger.info(f"[LocustEngine] execute_existing completed - returning execution")
        return execution
    
    async def execute(self) -> Any:
        """执行压测（向后兼容）"""
        execution = await self.create_execution_only()
        return await self.execute_existing(execution)
    
    async def stop(self) -> None:
        """停止压测"""
        logger.info(f"[LocustEngine] Stopping execution...")
        self.stop_event.set()
        
        # 终止所有Worker进程
        for proc in self._worker_processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    
    async def _generate_locustfile(self, callback_port: int = 18090) -> str:
        """生成Locust测试文件"""
        from .locust_user_generator import LocustUserGenerator
        
        generator = LocustUserGenerator(self.config, callback_port=callback_port)
        locust_code = generator.generate()
        
        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(locust_code)
            logger.info(f"[LocustEngine._generate_locustfile] Generated locustfile with callback_port={callback_port}")
            return f.name
    
    async def _run_standalone_mode(self) -> None:
        """单机模式运行 - 使用HTTP服务接收Locust真实请求结果"""
        import subprocess
        import sys
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        
        # 回调端口
        callback_port = 18090
        
        logger.info(f"[LocustEngine._run_standalone_mode] Starting HTTP callback server on port {callback_port}")
        
        # 存储请求结果
        request_results: List[LocustRequestResult] = []
        test_stopped = False
        server_running = True
        
        # 创建简单的 HTTP 处理器
        class ResultHandler(BaseHTTPRequestHandler):
            def do_POST(handler):
                content_length = int(handler.headers.get('Content-Length', 0))
                body = handler.rfile.read(content_length)
                
                try:
                    data = json.loads(body.decode('utf-8'))
                    result = LocustRequestResult(
                        name=data.get('name', ''),
                        request_type=data.get('request_type', ''),
                        response_time_ms=float(data.get('response_time_ms', 0)),
                        response_length=int(data.get('response_length', 0)),
                        success=data.get('success', True),
                        error_message=data.get('error_message', ''),
                    )
                    
                    request_results.append(result)
                    
                    # 同步推送 WebSocket（在 asyncio 外部）
                    if self.websocket:
                        try:
                            # 使用 asyncio.run_coroutine_threadsafe
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    self.websocket.send_result(result),
                                    loop
                                )
                        except Exception as e:
                            logger.warning(f"[LocustEngine] WebSocket push error: {e}")
                    
                    handler.send_response(200)
                    handler.send_header('Content-Type', 'text/plain')
                    handler.end_headers()
                    handler.wfile.write(b'OK')
                    
                except Exception as e:
                    logger.warning(f"[LocustEngine] Handle result error: {e}")
                    handler.send_response(500)
                    handler.end_headers()
            
            def log_message(handler, format, *args):
                pass  # 禁用默认日志
        
        # 启动 HTTP 服务（在独立线程中）
        server = HTTPServer(('localhost', callback_port), ResultHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        logger.info(f"[LocustEngine._run_standalone_mode] HTTP callback server started")
        
        try:
            # 生成 locustfile（传入回调端口）
            self._locustfile_path = await self._generate_locustfile(callback_port)
            logger.info(f"[LocustEngine._run_standalone_mode] Locustfile: {self._locustfile_path}")
            
            # 启动 Locust
            cmd = [
                sys.executable, '-m', 'locust',
                '--locustfile', self._locustfile_path,
                '--host', self.config.host,
                '--users', str(self.config.user_count),
                '--spawn-rate', str(self.config.spawn_rate),
                '--run-time', f'{self.config.duration_seconds}s',
                '--headless',
                '--only-summary',
            ]
            
            logger.info(f"[LocustEngine._run_standalone_mode] Command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            logger.info(f"[LocustEngine._run_standalone_mode] Locust process started, PID={process.pid}")
            
            # 等待 Locust 结束或收到 stop 通知，同时实时打印输出
            start_time = asyncio.get_event_loop().time()
            max_wait = self.config.duration_seconds + 30
            
            while process.poll() is None and not test_stopped:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait:
                    logger.warning(f"[LocustEngine._run_standalone_mode] Timeout, terminating process")
                    process.terminate()
                    break
                
                # 实时读取 Locust 输出（包含回调错误）
                if process.stdout:
                    try:
                        line = process.stdout.readline()
                        if line:
                            line = line.strip()
                            if 'Callback Error' in line or 'Error' in line:
                                logger.warning(f"[Locust Output] {line}")
                            elif 'Starting' in line or 'spawned' in line or 'Shutting' in line:
                                logger.info(f"[Locust Output] {line}")
                    except Exception:
                        pass
                
                await asyncio.sleep(0.1)
            
            # 等待进程完全结束
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            
            logger.info(f"[LocustEngine._run_standalone_mode] Locust process ended with code={process.returncode}")
            
            # 读取剩余输出
            remaining_output = process.stdout.read() if process.stdout else ''
            if remaining_output:
                logger.info(f"[LocustEngine._run_standalone_mode] Remaining output: {remaining_output[:500]}")
            
            # 解析最终统计（从合并的输出中）
            all_output = remaining_output
            if all_output:
                stats_parsed = self._parse_locust_stats(all_output)
                self._parsed_stats = stats_parsed
                logger.info(f"[LocustEngine._run_standalone_mode] Parsed final stats: {stats_parsed}")
            
            # 等待最后的回调请求到达
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"[LocustEngine._run_standalone_mode] Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            # 关闭 HTTP 服务
            server.shutdown()
            server.server_close()
            logger.info(f"[LocustEngine._run_standalone_mode] HTTP callback server stopped")
        
        # 存储结果并添加到 metrics
        for result in request_results:
            await self.metrics.add_result(result)
        
        self._websocket_results = request_results
        logger.info(f"[LocustEngine._run_standalone_mode] Collected {len(request_results)} real request results")
        
        await self._generate_report()
    
    async def _read_csv_and_push_websocket(self, csv_dir: str) -> None:
        """读取Locust CSV文件并推送每个请求结果到WebSocket"""
        import os
        import csv
        
        if not self.websocket:
            logger.info("[LocustEngine._read_csv_and_push_websocket] No websocket, skipping")
            return
        
        # Locust生成的CSV文件名
        stats_csv = os.path.join(csv_dir, 'stats.csv')
        stats_history_csv = os.path.join(csv_dir, 'stats_history.csv')
        
        # 尝试读取stats_history.csv（包含每个请求的记录）
        if os.path.exists(stats_history_csv):
            logger.info(f"[LocustEngine._read_csv_and_push_websocket] Reading {stats_history_csv}")
            try:
                with open(stats_history_csv, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        try:
                            # 构造请求结果
                            result = LocustRequestResult(
                                name=row.get('Name', ''),
                                request_type=row.get('Type', ''),
                                response_time_ms=float(row.get('Average Response Time', 0) or 0),
                                response_length=int(row.get('Response Length', 0) or 0),
                                success=row.get('Success Rate', '100') == '100',
                                error_message=row.get('Error', ''),
                                context={},
                            )
                            
                            # 推送到WebSocket
                            await self.websocket.send_result(result)
                            await self.metrics.add_result(result)
                            count += 1
                            
                        except (ValueError, KeyError) as e:
                            logger.warning(f"[LocustEngine._read_csv_and_push_websocket] Failed to parse row: {e}")
                    
                    logger.info(f"[LocustEngine._read_csv_and_push_websocket] Pushed {count} results to WebSocket")
                    
            except Exception as e:
                logger.error(f"[LocustEngine._read_csv_and_push_websocket] Error reading CSV: {e}")
        else:
            logger.warning(f"[LocustEngine._read_csv_and_push_websocket] CSV file not found: {stats_history_csv}")
            
            # 尝试读取stats.csv作为备选
            if os.path.exists(stats_csv):
                logger.info(f"[LocustEngine._read_csv_and_push_websocket] Reading {stats_csv} as fallback")
                try:
                    with open(stats_csv, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('Name') != 'Aggregated':
                                result = LocustRequestResult(
                                    name=row.get('Name', ''),
                                    request_type=row.get('Type', ''),
                                    response_time_ms=float(row.get('Average Response Time', 0) or 0),
                                    response_length=0,
                                    success=row.get('Failures', '0') == '0',
                                    error_message='',
                                    context={},
                                )
                                await self.websocket.send_result(result)
                except Exception as e:
                    logger.error(f"[LocustEngine._read_csv_and_push_websocket] Error reading stats.csv: {e}")
    
    async def _run_distributed_mode(self) -> None:
        """分布式模式运行"""
        import locust
        from locust.env import Environment
        from locust.runners import MasterRunner
        from locust.web import WebUI
        from locust.log import setup_logging
        
        setup_logging("INFO")
        
        # 动态加载User类
        import importlib.util
        spec = importlib.util.spec_from_file_location("locustfile", self._locustfile_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Failed to load locustfile: {self._locustfile_path}")
        locustfile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(locustfile)
        
        user_classes = []
        for attr_name in dir(locustfile):
            attr = getattr(locustfile, attr_name)
            if isinstance(attr, type) and hasattr(attr, 'tasks') and attr_name != 'HttpUser':
                user_classes.append(attr)
        
        if not user_classes:
            raise ValueError("No User class found in locustfile")
        
        # 创建Environment
        self.env = Environment(user_classes=user_classes)
        self.env.host = self.config.host
        
        # 注册事件监听
        self._register_event_handlers()
        
        # 创建Master Runner
        self.runner = MasterRunner(self.env, master_bind_host="*")
        
        # 启动Web UI
        if self.config.enable_web_ui:
            self.web_ui = WebUI(
                self.env, 
                self.runner,
                port=self.config.web_ui_port
            )
            logger.info(f"[LocustEngine] Web UI started on port {self.config.web_ui_port}")
        
        # 启动Worker进程
        await self._spawn_workers()
        
        # 等待Worker连接
        await self._wait_for_workers()
        
        # 启动压测
        self.runner.start(
            user_count=self.config.user_count,
            spawn_rate=self.config.spawn_rate
        )
        
        logger.info(f"[LocustEngine] Distributed mode started - users={self.config.user_count}, "
                    f"workers={self.config.worker_count}")
        
        # 等待完成
        try:
            await asyncio.wait_for(
                self._wait_for_completion(),
                timeout=self.config.duration_seconds
            )
        except asyncio.TimeoutError:
            logger.info(f"[LocustEngine] Duration limit reached")
        
        # 停止
        self.runner.stop()
        
        # 生成报告
        await self._generate_report()
    
    async def _spawn_workers(self) -> None:
        """启动Worker进程"""
        if not self._locustfile_path:
            raise ValueError("Locustfile path is not set")
        
        for i in range(self.config.worker_count):
            proc = subprocess.Popen(
                [
                    'python', '-m', 'locust',
                    '--worker',
                    '--master-host', 'localhost',
                    '--locustfile', str(self._locustfile_path)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self._worker_processes.append(proc)
            logger.info(f"[LocustEngine] Worker {i+1}/{self.config.worker_count} started (PID: {proc.pid})")
        
        # 更新执行记录中的Worker信息
        await self._update_worker_status()
    
    async def _wait_for_workers(self) -> None:
        """等待Worker连接"""
        import time
        max_wait = 30  # 最多等待30秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.runner and self.runner.ready:
                logger.info(f"[LocustEngine] All workers connected")
                return
            await asyncio.sleep(0.5)
        
        logger.warning(f"[LocustEngine] Timeout waiting for workers")
    
    async def _wait_for_completion(self) -> None:
        """等待压测完成"""
        while not self.stop_event.is_set():
            # 更新实时统计
            if hasattr(self, 'runner') and self.runner:
                current_users = self.runner.user_count
                await self.metrics.update_peak_users(current_users)
                
                stats = self.metrics.get_realtime_stats(current_users)
                
                # 推送WebSocket
                if self.websocket:
                    try:
                        await self.websocket.send_stats(stats)
                    except Exception:
                        pass
            
            await asyncio.sleep(1)
    
    def _register_event_handlers(self) -> None:
        """注册Locust事件处理器"""
        from locust import events
        
        @events.request.add_listener
        def on_request(request_type, name, response_time, response_length,
                       exception, context, **kwargs):
            """请求事件监听"""
            result = LocustRequestResult(
                name=name,
                request_type=request_type,
                response_time_ms=response_time,
                response_length=response_length or 0,
                success=exception is None,
                error_message=str(exception) if exception else "",
                context=context or {}
            )
            
            # 使用asyncio.create_task异步添加结果
            asyncio.create_task(self._on_request_complete(result))
        
        @events.user_error.add_listener
        def on_user_error(user_instance, exception, tb, **kwargs):
            """用户错误事件监听"""
            logger.error(f"[LocustEngine] User error: {exception}")
    
    async def _on_request_complete(self, result: LocustRequestResult) -> None:
        """请求完成回调"""
        await self.metrics.add_result(result)
        
        # 推送WebSocket
        if self.websocket:
            try:
                await self.websocket.send_result(result)
            except Exception:
                pass
    
    async def _generate_report(self) -> None:
        """生成HTML报告"""
        logger.info("[LocustEngine._generate_report] Starting")
        
        # subprocess 模式下 self.env 为 None，跳过报告生成
        if not hasattr(self, 'env') or not self.env:
            logger.info("[LocustEngine._generate_report] subprocess mode - no env, skipping report generation")
            return
        
        try:
            logger.info("[LocustEngine._generate_report] in-process mode, importing locust.stats")
            from locust.stats import get_percentile_stats
            logger.info("[LocustEngine._generate_report] Imported locust.stats")
            
            logger.info("[LocustEngine._generate_report] self.env exists, getting stats")
            stats = self.env.runner.stats
            
            # 生成HTML报告内容
            html_content = self._build_html_report(stats)
            logger.info(f"[LocustEngine._generate_report] HTML content length: {len(html_content)}")
            
            # 保存到执行记录
            await self._save_report(html_content)
            logger.info("[LocustEngine._generate_report] Report saved")
                
        except Exception as e:
            logger.error(f"[LocustEngine._generate_report] Failed to generate report: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _parse_locust_stats(self, stderr_output: str) -> Dict[str, Any]:
        """解析 Locust 输出的统计数据"""
        import re
        
        stats: Dict[str, Any] = {
            'total_requests': 0,
            'success_count': 0,
            'failed_count': 0,
            'error_rate': 0.0,
            'avg_response_time': 0.0,
            'min_response_time': 0.0,
            'max_response_time': 0.0,
            'p50_response_time': 0.0,
            'p90_response_time': 0.0,
            'p95_response_time': 0.0,
            'p99_response_time': 0.0,
            'throughput': 0.0,
            'requests_per_endpoint': {},
            'peak_users': self.config.user_count,
        }
        
        lines = stderr_output.split('\n')
        
        # 解析主统计表（Aggregated 行）
        # 格式: Aggregated    18    0(0.00%) | 567  302  1234  370 | 1.98  0.00
        for line in lines:
            if 'Aggregated' in line and '|' in line and 'GET' not in line and 'POST' not in line and 'Response' not in line:
                logger.info(f"[LocustEngine._parse_locust_stats] Found Aggregated stats line: {line}")
                try:
                    # 分割: 左边是请求统计，右边是响应时间和rps
                    parts = line.split('|')
                    if len(parts) >= 3:
                        # Part 1: Aggregated    18    0(0.00%)
                        req_part = parts[0].strip()
                        req_tokens = req_part.split()
                        for i, t in enumerate(req_tokens):
                            if t == 'Aggregated':
                                if i + 1 < len(req_tokens):
                                    stats['total_requests'] = int(req_tokens[i + 1])
                                if i + 2 < len(req_tokens):
                                    fails_str = req_tokens[i + 2]
                                    if '(' in fails_str:
                                        fails_num = fails_str.split('(')[0]
                                        stats['failed_count'] = int(fails_num)
                                        stats['success_count'] = stats['total_requests'] - stats['failed_count']
                                        if stats['total_requests'] > 0:
                                            stats['error_rate'] = round((stats['failed_count'] / stats['total_requests']) * 100, 2)
                        
                        # Part 2: 567  302  1234  370 (Avg, Min, Max, Med)
                        resp_part = parts[1].strip()
                        resp_tokens = resp_part.split()
                        if len(resp_tokens) >= 4:
                            stats['avg_response_time'] = float(resp_tokens[0])
                            stats['min_response_time'] = float(resp_tokens[1])
                            stats['max_response_time'] = float(resp_tokens[2])
                        
                        # Part 3: 1.98  0.00 (req/s, failures/s)
                        rps_part = parts[2].strip()
                        rps_tokens = rps_part.split()
                        if len(rps_tokens) >= 1:
                            stats['throughput'] = float(rps_tokens[0])
                        
                        logger.info(f"[LocustEngine._parse_locust_stats] Parsed main stats: total={stats['total_requests']}, avg={stats['avg_response_time']}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"[LocustEngine._parse_locust_stats] Failed to parse Aggregated stats: {e}")
        
        # 解析百分位数表（Response time percentiles）
        # 格式: Aggregated    490  520  650  880  1200  1200  1200  1200  1200  1200  1200    18
        percentile_section_started = False
        for line in lines:
            if 'Response time percentiles' in line:
                percentile_section_started = True
                continue
            if percentile_section_started and 'Aggregated' in line and 'GET' not in line and 'POST' not in line:
                logger.info(f"[LocustEngine._parse_locust_stats] Found percentile line: {line}")
                try:
                    parts = line.strip().split()
                    # 找到 Aggregated 后面的百分位数值
                    for i, p in enumerate(parts):
                        if p == 'Aggregated':
                            # 紧接着是百分位数值: P50, P66, P75, P80, P90, P95, P98, P99, P99.9, P99.99, P100, #reqs
                            percentile_indices = {
                                'p50': i + 1,
                                'p90': i + 5,
                                'p95': i + 6,
                                'p99': i + 8,
                            }
                            for key, idx in percentile_indices.items():
                                if idx < len(parts):
                                    try:
                                        stats[f'{key}_response_time'] = float(parts[idx])
                                    except ValueError:
                                        pass
                            break
                except (ValueError, IndexError) as e:
                    logger.warning(f"[LocustEngine._parse_locust_stats] Failed to parse percentile: {e}")
        
        # 解析各端点统计
        for line in lines:
            if ('GET' in line or 'POST' in line or 'PUT' in line or 'DELETE' in line) and '---' not in line and '|' in line:
                try:
                    # 格式: GET  get_homepage  3  0(0.00%) | 671  488  879  650 | 0.33  0.00
                    parts = line.split('|')
                    if len(parts) >= 1:
                        left_part = parts[0].strip()
                        tokens = left_part.split()
                        if len(tokens) >= 3:
                            method = tokens[0]
                            name = tokens[1]
                            reqs = int(tokens[2])
                            if reqs > 0:
                                stats['requests_per_endpoint'][name] = {
                                    'method': method,
                                    'requests': reqs,
                                }
                except (ValueError, IndexError):
                    pass
        
        logger.info(f"[LocustEngine._parse_locust_stats] Final parsed stats: {stats}")
        return stats
    
    def _build_html_report(self, stats) -> str:
        """构建HTML报告"""
        # 简化的HTML报告模板
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Locust Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #4CAF50; color: white; }
                tr:nth-child(even) { background-color: #f2f2f2; }
                .stats { background: #f9f9f9; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Locust Test Report</h1>
            <div class="stats">
                <h2>Statistics</h2>
                <p>Generated at: {timestamp}</p>
                {stats_table}
            </div>
        </body>
        </html>
        """
        
        # 构建统计表格
        stats_table = "<table><tr><th>Method</th><th>Name</th><th>Requests</th>"
        stats_table += "<th>Failures</th><th>Median</th><th>Average</th>"
        stats_table += "<th>Min</th><th>Max</th><th>Content Size</th><th>Req/s</th></tr>"
        
        for key in sorted(stats.entries.keys()):
            entry = stats.entries[key]
            stats_table += f"<tr><td>{entry.method}</td><td>{entry.name}</td>"
            stats_table += f"<td>{entry.num_requests}</td>"
            stats_table += f"<td>{entry.num_failures}</td>"
            stats_table += f"<td>{entry.median_response_time:.0f}</td>"
            stats_table += f"<td>{entry.avg_response_time:.0f}</td>"
            stats_table += f"<td>{entry.min_response_time:.0f}</td>"
            stats_table += f"<td>{entry.max_response_time:.0f}</td>"
            stats_table += f"<td>{entry.avg_content_length:.0f}</td>"
            stats_table += f"<td>{entry.total_rps:.2f}</td></tr>"
        
        stats_table += "</table>"
        
        return html_template.format(
            timestamp=datetime.now().isoformat(),
            stats_table=stats_table
        )
    
    async def _save_report(self, html_content: str) -> None:
        """保存报告到执行记录"""
        logger.info("[LocustEngine._save_report] Starting")
        if self._execution is None:
            logger.info("[LocustEngine._save_report] self._execution is None, skipping")
            return
        
        execution = self._execution  # type: ignore
        
        @sync_to_async
        def update():
            logger.info("[LocustEngine._save_report] Inside sync_to_async update()")
            execution.report_html = html_content
            execution.save(update_fields=['report_html'])
            logger.info("[LocustEngine._save_report] execution.save() completed")
        
        await update()
        logger.info("[LocustEngine._save_report] completed")
    
    def _cleanup(self) -> None:
        """清理资源"""
        logger.info("[LocustEngine._cleanup] Starting cleanup")
        # 删除临时文件
        if self._locustfile_path and os.path.exists(self._locustfile_path):
            logger.info(f"[LocustEngine._cleanup] Deleting locustfile: {self._locustfile_path}")
            try:
                os.unlink(self._locustfile_path)
                logger.info("[LocustEngine._cleanup] Locustfile deleted")
            except Exception as e:
                logger.warning(f"[LocustEngine._cleanup] Failed to cleanup locustfile: {e}")
        else:
            logger.info(f"[LocustEngine._cleanup] No locustfile to delete (path={self._locustfile_path})")
        
        # 终止Worker进程
        logger.info(f"[LocustEngine._cleanup] Worker processes count: {len(self._worker_processes)}")
        for i, proc in enumerate(self._worker_processes):
            logger.info(f"[LocustEngine._cleanup] Checking worker {i}, poll={proc.poll()}")
            if proc.poll() is None:
                logger.info(f"[LocustEngine._cleanup] Terminating worker {i}")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                    logger.info(f"[LocustEngine._cleanup] Worker {i} terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"[LocustEngine._cleanup] Worker {i} didn't terminate, killing")
                    proc.kill()
        logger.info("[LocustEngine._cleanup] Cleanup completed")
    
    # Database operations
    async def _create_execution(self) -> Any:
        """创建执行记录"""
        from testmanager_app.models import AdvancedPressureTestExecution
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create():
            return AdvancedPressureTestExecution.objects.create(
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
    
    async def _update_execution_complete(self, execution: Any, stats: Dict, 
                                         status: str, error: str = "") -> None:
        """更新执行完成状态"""
        logger.info(f"[LocustEngine._update_execution_complete] Starting - status={status}, stats={stats}")
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        
        @sync_to_async
        def update():
            logger.info("[LocustEngine._update_execution_complete] Inside sync_to_async update()")
            execution.status = status
            execution.finished_at = timezone.now()
            
            if execution.started_at:
                execution.duration_seconds = (
                    execution.finished_at - execution.started_at
                ).total_seconds()
            
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
            
            # 并发统计
            execution.peak_users = stats.get('peak_users', 0)
            
            # Worker信息
            execution.worker_count = self.config.worker_count if self.config.use_distributed else 1
            
            # 错误日志
            if error:
                execution.error_log = error
            
            # 原始结果
            execution.raw_results = [
                {
                    'name': r.name,
                    'request_type': r.request_type,
                    'response_time_ms': r.response_time_ms,
                    'success': r.success,
                    'error_message': r.error_message,
                    'timestamp': r.timestamp.isoformat(),
                    'context': r.context
                }
                for r in self.metrics.results
            ]
            
            logger.info("[LocustEngine._update_execution_complete] Calling execution.save()")
            execution.save()
            logger.info("[LocustEngine._update_execution_complete] execution.save() completed")
        
        logger.info("[LocustEngine._update_execution_complete] Calling update()")
        await update()
        logger.info("[LocustEngine._update_execution_complete] update() completed")
    
    async def _update_worker_status(self) -> None:
        """更新Worker状态"""
        if self._execution is None:
            return
        
        execution = self._execution
        config = self.config
        processes = self._worker_processes
        
        @sync_to_async
        def update():
            worker_status = {
                'total': config.worker_count,
                'connected': 0,
                'workers': []
            }
            
            for i, proc in enumerate(processes):
                worker_status['workers'].append({
                    'id': f'worker-{i+1}',
                    'pid': proc.pid,
                    'status': 'starting'
                })
            
            execution.worker_status = worker_status
            execution.save(update_fields=['worker_status'])
        
        await update()