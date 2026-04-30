"""
Locust 高级压测引擎 — 子进程隔离模式

关键设计:
  ⚠ Windows 上 gevent 与 asyncio 不兼容，线程隔离也无效。
     解决方案：Locust 运行在独立子进程中 (python -m locust --headless --print-stats)，
     引擎通过读取 stdout 获取实时统计，通过 asyncio 事件循环推送到 WebSocket。
     执行完毕后解析 CSV 汇总并写入 DB。

架构:
  Daphne 进程 (asyncio)              Locust 子进程 (gevent)
  ┌──────────────────────┐          ┌───────────────────────────┐
  │ execute_existing()   │          │ python -m locust          │
  │   ├ subprocess.Popen │──stdout─→│   --headless              │
  │   ├ read stdout (async)        │   --print-stats           │
  │   ├ parse + WS push  │          │   --csv stats             │
  │   ├ wait proc exit   │          │   (gevent 自由运行)       │
  │   ├ parse CSV final  │          └───────────────────────────┘
  │   ├ WS stats_summary │
  │   └ DB update        │
  └──────────────────────┘
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# 解析 Locust stdout 输出用的正则
_LOCUST_HEADER_RE = re.compile(r'^\s*(?:Type|Name|\#|----)')
_LOCUST_STAT_LINE_RE = re.compile(r'^\s*\S+\s+\S+\s+')
_LOCUST_AGGREGATED_RE = re.compile(r'Aggregated')
_LOCUST_TABLE_END_RE = re.compile(r'^\s*$|Response time percentiles|^$')


@dataclass
class LocustRealtimeStats:
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


class LocustEngine:
    """
    Locust 高级压测引擎 — 子进程隔离模式

    Locust 通过 subprocess 在独立进程中运行，gevent 自由初始化。
    主进程通过 stdout 获得实时统计，完结后解析 CSV 获取最终数据。
    """

    def __init__(
        self,
        config: Any,
        websocket: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.websocket = websocket
        self._execution: Optional[Any] = None
        self._process: Optional[subprocess.Popen] = None
        self._locustfile: Optional[str] = None
        self._csv_dir: Optional[str] = None
        self._peak_users: int = 0
        self._current_stats: Dict[str, Any] = {}
        self._stdout_lines: List[str] = []
        self._stop_flag = False

        logger.info(
            f'[LocustEngine] Initialized - config_id={config.id}, '
            f'users={config.user_count}, spawn_rate={config.spawn_rate}, '
            f'duration={config.duration_seconds}s'
        )

    async def execute_existing(self, execution: Any) -> Any:
        self._execution = execution
        try:
            logger.info('[LocustEngine] update status to running')
            await self._update_execution_status(execution, 'running')

            logger.info('[LocustEngine] send started message')
            await self._send_started_message()

            logger.info('[LocustEngine] generate locustfile')
            await sync_to_async(self._generate_locustfile)()

            logger.info('[LocustEngine] start subprocess')
            await self._start_subprocess()

            logger.info('[LocustEngine] read stdout loop (real-time stats)')
            await self._read_stdout_loop()

            logger.info('[LocustEngine] wait process exit')
            await self._wait_process()

            logger.info('[LocustEngine] parse CSV final stats')
            final_stats = self._collect_final_stats()

            logger.info('[LocustEngine] push stats_summary via WS')
            await self._send_stats_summary(final_stats)

            logger.info('[LocustEngine] update DB execution record')
            await self._update_execution_complete(execution, final_stats, 'completed')

            logger.info(
                f'[LocustEngine] done - '
                f'total={final_stats.get("total_requests", 0)}, '
                f'success={final_stats.get("success_count", 0)}'
            )

            logger.info('[LocustEngine] send complete message via WS')
            await self._send_complete_message(execution, final_stats)

        except asyncio.CancelledError:
            self._stop_flag = True
            self._kill_process()
            final_stats = self._current_stats
            await self._update_execution_complete(execution, final_stats, 'stopped')
            raise

        except Exception as e:
            logger.error(f'[LocustEngine] Execution failed: {e}', exc_info=True)
            self._stop_flag = True
            self._kill_process()
            final_stats = self._current_stats
            await self._update_execution_complete(execution, final_stats, 'failed', error=str(e))
            raise

        finally:
            self._cleanup()

        return execution

    async def stop(self) -> None:
        logger.info('[LocustEngine] Stop requested')
        self._stop_flag = True
        self._kill_process()

    # ── locustfile 生成 ─────────────────────────────────────────────────

    def _generate_locustfile(self) -> None:
        steps = (self.config.scenario or {}).get('steps', [])
        think_time = (self.config.scenario or {}).get('think_time', {'min': 1, 'max': 3})

        # ── 预加载 ApiRequest 数据（主进程有 Django，子进程没有） ──
        api_data: Dict[str, Dict[str, Any]] = {}
        api_ids = [s['api_request_id'] for s in steps if s.get('api_request_id')]
        if api_ids:
            from testmanager_app.models import ApiRequest
            for req in ApiRequest.objects.filter(id__in=api_ids):
                api_data[str(req.id)] = {
                    'url': req.url,
                    'method': req.method,
                    'body': req.body or '',
                    'headers': req.headers or '{}',
                }

        lines: List[str] = []
        lines.append('"""Auto-generated locustfile for pressure test."""')
        lines.append('from __future__ import annotations')
        lines.append('import json, re')
        lines.append('from typing import Any, Dict, Optional')
        lines.append('from locust import HttpUser, task, between')
        lines.append('')

        # ── 内联 TransactionContext（子进程无法 import Django 模块） ──
        lines.append('class TransactionContext:')
        lines.append('    def __init__(self):')
        lines.append('        self.variables: Dict[str, Any] = {}')
        lines.append('    def set(self, name, value):')
        lines.append('        self.variables[name] = value')
        lines.append('    def get(self, name, default=None):')
        lines.append('        return self.variables.get(name, default)')
        lines.append('')

        # ── 内联 extract_value ──
        lines.append('def extract_value(response, extractor):')
        lines.append('    ext_type = extractor.get("type", "")')
        lines.append('    expression = extractor.get("expression", "")')
        lines.append('    if ext_type == "json_path":')
        lines.append('        try:')
        lines.append('            from jsonpath_ng import parse as jsonpath_parse')
        lines.append('            jd = response.json()')
        lines.append('            je = jsonpath_parse(expression)')
        lines.append('            m = [match.value for match in je.find(jd)]')
        lines.append('            return m[0] if m else None')
        lines.append('        except Exception:')
        lines.append('            return None')
        lines.append('    if ext_type == "regex":')
        lines.append('        m = re.search(expression, response.text)')
        lines.append('        if m:')
        lines.append('            return m.group(1) if m.lastindex else m.group(0)')
        lines.append('        return None')
        lines.append('    if ext_type == "header":')
        lines.append('        return response.headers.get(expression)')
        lines.append('    if ext_type == "status_code":')
        lines.append('        return response.status_code')
        lines.append('    return None')
        lines.append('')

        # ── 预加载的 API 数据 ──
        lines.append(f'API_DATA = {json.dumps(api_data)}')
        lines.append('')

        # ── User class ──
        lines.append('class AdvancedTestUser(HttpUser):')
        lines.append(f'    wait_time = between({think_time.get("min", 1)}, {think_time.get("max", 3)})')
        lines.append('')
        lines.append('    def on_start(self):')
        lines.append('        print("[Locust-User] on_start: spawned")')
        lines.append('        self.tx_context = TransactionContext()')

        lines.append('')

        for idx, step in enumerate(steps):
            name = step.get('name', f'step_{idx}')
            weight = step.get('weight', 1)
            extractors = step.get('extractors', [])

            if step.get('api_request_id'):
                api_id = step['api_request_id']
                lines.append(f'    @task({weight})')
                lines.append(f'    def task_{idx}(self):')
                lines.append(f'        """{name}"""')
                lines.append(f'        print(\"[Locust-User] task_{idx} ({name}) called, weight={weight}, api_id={api_id}\")')
                lines.append(f'        _info = API_DATA.get("{api_id}")')
                lines.append('        if not _info:')
                lines.append(f'            print(\"[Locust-User] task_{idx}: API_DATA key={api_id} NOT FOUND, skipping\")')
                lines.append('            return')
                lines.append('        try:')
                lines.append('            _headers = {}')
                lines.append("            try: _headers = json.loads(_info.get('headers', '{}'))")
                lines.append('            except Exception: pass')
                lines.append(f'            _resp = self.client.request(_info["method"], _info["url"], data=_info.get("body",""), headers=_headers, name="{name}")')
                for ext in extractors:
                    lines.append(f'            _val = extract_value(_resp, {json.dumps(ext)})')
                    if ext.get('name'):
                        lines.append(f'            if _val is not None:')
                        lines.append(f'                self.tx_context.set("{ext["name"]}", _val)')
                lines.append('        except Exception:')
                lines.append('            pass')
            else:
                url = step.get('url', '/')
                method = step.get('method', 'GET')
                lines.append(f'    @task({weight})')
                lines.append(f'    def task_{idx}(self):')
                lines.append(f'        """{name}"""')
                lines.append(f'        print("[Locust-User] task_{idx} ({name}) called, direct mode")')
                lines.append(f'        _resp = self.client.request("{method}", "{url}", name="{name}")')
                for ext in extractors:
                    lines.append(f'        _val = extract_value(_resp, {json.dumps(ext)})')
                    if ext.get('name'):
                        lines.append(f'        if _val is not None:')
                        lines.append(f'            self.tx_context.set("{ext["name"]}", _val)')
            lines.append('')

        code = '\n'.join(lines)

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8',
        ) as f:
            f.write(code)
            self._locustfile = f.name

    # ── 子进程启动 ──────────────────────────────────────────────────────

    async def _start_subprocess(self) -> None:
        import time
        self._csv_dir = tempfile.mkdtemp(prefix='locust_')
        csv_prefix = os.path.join(self._csv_dir, 'stats')

        cmd = [
            sys.executable, '-m', 'locust',
            '--locustfile', self._locustfile,
            '--host', self.config.host,
            '--users', str(self.config.user_count),
            '--spawn-rate', str(self.config.spawn_rate),
            '--run-time', f'{self.config.duration_seconds}s',
            '--headless',
            '--print-stats',
            '--csv', csv_prefix,
        ]

        logger.info(f'[LocustEngine] Starting: {" ".join(cmd)}')

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )
        logger.info(f'[LocustEngine] Subprocess PID={self._process.pid}')

    # ── stdout 实时读取 ──────────────────────────────────────────────────

    async def _read_stdout_loop(self) -> None:
        if not self._process or not self._process.stdout:
            return

        loop = asyncio.get_event_loop()
        last_push = 0.0

        while not self._stop_flag:
            line = await loop.run_in_executor(None, self._process.stdout.readline)
            if not line:
                break

            line_stripped = line.strip()

            # Collect all stdout for final log
            self._stdout_lines.append(line_stripped)

            # Parse locust table output for real-time stats
            stats = self._parse_locust_line(line_stripped)
            if stats:
                self._current_stats = stats
                self._peak_users = max(self._peak_users, self.config.user_count)

                now = asyncio.get_event_loop().time()
                if now - last_push >= 2.0 and self.websocket:
                    last_push = now
                    ws_stats = LocustRealtimeStats(
                        current_users=self.config.user_count,
                        total_requests=stats.get('total_requests', 0),
                        success_count=stats.get('success_count', 0),
                        failed_count=stats.get('failed_count', 0),
                        rps=stats.get('throughput', 0),
                        fail_ratio=stats.get('error_rate', 0),
                        avg_response_time=stats.get('avg_response_time', 0),
                        min_response_time=stats.get('min_response_time', 0),
                        max_response_time=stats.get('max_response_time', 0),
                        peak_users=self._peak_users,
                    )
                    try:
                        await self.websocket.send_stats(ws_stats)
                    except Exception as e:
                        logger.warning(f'[LocustEngine] WS stats push error: {e}')

            # Log relevant lines
            if line_stripped:
                logger.info(f'[Locust stdout] {line_stripped[:200]}')

    def _parse_locust_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a Locust stdout stat line like:
        Aggregated    150    0(0.00%) | 45  30  80  42 | 1.50  0.00
        """
        if not _LOCUST_AGGREGATED_RE.search(line):
            return None
        if 'Response time' in line:
            return None
        if 'GET' in line or 'POST' in line or 'PUT' in line:
            return None

        try:
            parts = line.split('|')
            if len(parts) < 3:
                return None

            # Left: Aggregated  <requests>  <failures>(<fail_rate>)
            left = parts[0].strip().split()
            if len(left) < 3 or left[0] != 'Aggregated':
                return None

            total_requests = int(left[1])
            fails_str = left[2]
            if '(' in fails_str:
                failed_count = int(fails_str.split('(')[0])
            else:
                failed_count = int(fails_str)

            success_count = total_requests - failed_count

            # Middle: <avg> <min> <max> <median>
            middle = parts[1].strip().split()
            avg_rt = float(middle[0]) if len(middle) > 0 else 0.0
            min_rt = float(middle[1]) if len(middle) > 1 else 0.0
            max_rt = float(middle[2]) if len(middle) > 2 else 0.0

            # Right: <rps> <failures/s>
            right = parts[2].strip().split()
            rps = float(right[0]) if len(right) > 0 else 0.0

            error_rate = round(failed_count / total_requests * 100, 2) if total_requests > 0 else 0.0

            return {
                'total_requests': total_requests,
                'success_count': success_count,
                'failed_count': failed_count,
                'error_rate': error_rate,
                'avg_response_time': avg_rt,
                'min_response_time': min_rt,
                'max_response_time': max_rt,
                'throughput': rps,
            }
        except (ValueError, IndexError):
            return None

    async def _wait_process(self) -> None:
        if not self._process:
            return
        loop = asyncio.get_event_loop()

        while self._process.poll() is None and not self._stop_flag:
            await asyncio.sleep(0.5)

        if self._process.poll() is None:
            self._kill_process()

    # ── 结果汇总 ─────────────────────────────────────────────────────────

    def _collect_final_stats(self) -> Dict[str, Any]:
        """Parse Locust CSV summary file for final stats."""
        import csv

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
            'peak_users': self.config.user_count,
            'duration_seconds': float(self.config.duration_seconds),
        }

        if not self._csv_dir:
            return stats

        csv_file = os.path.join(self._csv_dir, 'stats_stats.csv')
        if not os.path.exists(csv_file):
            logger.warning(f'[LocustEngine] CSV not found: {csv_file}')
            return stats

        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Name', '')
                    if name != 'Aggregated':
                        continue

                    stats['total_requests'] = int(float(row.get('Request Count', 0) or 0))
                    stats['failed_count'] = int(float(row.get('Failure Count', 0) or 0))
                    stats['success_count'] = stats['total_requests'] - stats['failed_count']

                    if stats['total_requests'] > 0:
                        stats['error_rate'] = round(
                            (stats['failed_count'] / stats['total_requests']) * 100, 2,
                        )

                    for key, col in [
                        ('avg_response_time', 'Average Response Time'),
                        ('min_response_time', 'Min Response Time'),
                        ('max_response_time', 'Max Response Time'),
                    ]:
                        try:
                            stats[key] = float(row.get(col, '0') or '0')
                        except ValueError:
                            pass

                    try:
                        stats['throughput'] = float(row.get('Requests/s', '0') or '0')
                    except ValueError:
                        pass

                    for key, col in [
                        ('p50_response_time', '50%'),
                        ('p90_response_time', '90%'),
                        ('p95_response_time', '95%'),
                        ('p99_response_time', '99%'),
                    ]:
                        try:
                            stats[key] = float(row.get(col, '0') or '0')
                        except ValueError:
                            pass

            logger.info(f'[LocustEngine] CSV stats: total={stats["total_requests"]}, '
                        f'avg={stats["avg_response_time"]}ms, rps={stats["throughput"]}')
        except Exception as e:
            logger.warning(f'[LocustEngine] CSV parse error: {e}')

        return stats

    # ── WebSocket 推送 ──────────────────────────────────────────────────

    async def _send_started_message(self) -> None:
        if not self.websocket:
            return
        try:
            await self.websocket.send(json.dumps({
                'type': 'started',
                'execution_id': self._execution.id if self._execution else None,
                'message': 'Pressure test started',
                'config': {
                    'name': self.config.name,
                    'user_count': self.config.user_count,
                    'spawn_rate': self.config.spawn_rate,
                    'duration_seconds': self.config.duration_seconds,
                    'use_distributed': self.config.use_distributed,
                    'worker_count': 1,
                    'web_ui_url': None,  # subprocess mode, no web UI
                },
            }))
        except Exception as e:
            logger.warning(f'[LocustEngine] Send started error: {e}')

    async def _send_stats_summary(self, stats: Dict[str, Any]) -> None:
        if not self.websocket:
            return
        try:
            await self.websocket.send_stats_summary(stats)
        except Exception as e:
            logger.warning(f'[LocustEngine] Send summary error: {e}')

    async def _send_complete_message(
        self, execution: Any, stats: Dict[str, Any],
    ) -> None:
        if not self.websocket:
            return
        try:
            await self.websocket.send(json.dumps({
                'type': 'complete',
                'execution_id': execution.id,
                'message': 'Advanced pressure test completed',
                'summary': {
                    'status': execution.status,
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
                },
            }))
        except Exception as e:
            logger.warning(f'[LocustEngine] Send complete error: {e}')

    # ── 进程管理 ─────────────────────────────────────────────────────────

    def _kill_process(self) -> None:
        if not self._process:
            return
        if self._process.poll() is None:
            try:
                if sys.platform == 'win32':
                    self._process.terminate()
                else:
                    self._process.send_signal(signal.SIGTERM)
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

    def _cleanup(self) -> None:
        self._kill_process()
        if self._locustfile and os.path.exists(self._locustfile):
            try:
                os.unlink(self._locustfile)
            except Exception:
                pass
        if self._csv_dir and os.path.exists(self._csv_dir):
            try:
                import shutil
                shutil.rmtree(self._csv_dir)
            except Exception:
                pass
        self._locustfile = None
        self._csv_dir = None
        self._process = None

    # ── 数据库操作 ─────────────────────────────────────────────────────

    @sync_to_async
    def _update_execution_status(self, execution: Any, status: str) -> None:
        from django.utils import timezone
        execution.status = status
        if status == 'running':
            execution.started_at = timezone.now()
        execution.save(update_fields=['status', 'started_at'])

    @sync_to_async
    def _update_execution_complete(
        self, execution: Any, stats: Dict[str, Any], status: str, error: str = '',
    ) -> None:
        from django.utils import timezone
        execution.status = status
        execution.finished_at = timezone.now()
        if execution.started_at:
            execution.duration_seconds = (
                execution.finished_at - execution.started_at
            ).total_seconds()
        execution.total_requests = stats.get('total_requests', 0)
        execution.success_count = stats.get('success_count', 0)
        execution.failed_count = stats.get('failed_count', 0)
        execution.error_rate = stats.get('error_rate', 0)
        execution.min_response_time = stats.get('min_response_time')
        execution.max_response_time = stats.get('max_response_time')
        execution.avg_response_time = stats.get('avg_response_time')
        execution.p50_response_time = stats.get('p50_response_time')
        execution.p90_response_time = stats.get('p90_response_time')
        execution.p95_response_time = stats.get('p95_response_time')
        execution.p99_response_time = stats.get('p99_response_time')
        execution.throughput = stats.get('throughput', 0)
        execution.peak_users = stats.get('peak_users', 0)
        execution.worker_count = 1
        if error:
            execution.error_log = error
        sep = '=' * 60
        log_lines: List[str] = [
            sep,
            '  高级压测执行报告',
            sep,
            f'',
            f'--- 基本信息 ---',
            f'配置: {self.config.name} (ID={self.config.id})',
            f'目标: {self.config.host}',
            f'参数: {self.config.user_count} 并发用户, {self.config.spawn_rate}/s 启动率, {self.config.duration_seconds}s 持续时间',
            f'开始时间: {execution.started_at}',
            f'结束时间: {execution.finished_at}',
            f'耗时: {execution.duration_seconds:.1f}s',
            f'状态: {status}',
            f'进程PID: {self._process.pid if self._process else "N/A"}',
            f'',
            f'--- 统计摘要 ---',
            f'总请求: {stats.get("total_requests", 0)}',
            f'成功: {stats.get("success_count", 0)}, 失败: {stats.get("failed_count", 0)}',
            f'错误率: {stats.get("error_rate", 0):.2f}%',
            f'平均响应: {stats.get("avg_response_time", 0):.1f}ms',
            f'最小/最大: {stats.get("min_response_time", 0):.1f} / {stats.get("max_response_time", 0):.1f}ms',
            f'P50: {stats.get("p50_response_time", 0):.1f}ms  P90: {stats.get("p90_response_time", 0):.1f}ms',
            f'P95: {stats.get("p95_response_time", 0):.1f}ms  P99: {stats.get("p99_response_time", 0):.1f}ms',
            f'吞吐量: {stats.get("throughput", 0):.2f} RPS',
            f'',
            f'--- Locust 完整输出 ---',
        ]
        log_lines.extend(self._stdout_lines)
        log_lines.append('')
        log_lines.append(sep)
        if error:
            log_lines.insert(-2, f'')
            log_lines.insert(-2, f'--- 错误日志 ---')
            log_lines.insert(-2, error)
        execution.logs = '\n'.join(log_lines)
        execution.save()
