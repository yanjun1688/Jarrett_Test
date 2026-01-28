"""
日志采集器 - 采集执行日志、截图和失败点
"""
import json
import logging
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

from asgiref.sync import sync_to_async
from django.utils import timezone

from ..models import UITestExecution

logger = logging.getLogger(__name__)


class LogCollector:
    """日志采集器"""

    def __init__(self, execution: UITestExecution, console_output: bool = True):
        self.execution = execution
        self.logs = []  # 存储结构化日志条目
        self.detailed_logs = []  # 存储详细日志文本（按行）
        self.screenshots = []
        self.failed_actions = []
        self.start_time = None
        self.console_output = console_output  # 是否输出到控制台
    
    def _format_timestamp(self, dt=None) -> str:
        """格式化时间戳为 [YYYY-MM-DD HH:MM:SS] 格式"""
        if dt is None:
            dt = timezone.now()
        return dt.strftime('[%Y-%m-%d %H:%M:%S]')
    
    def _add_log_line(self, message: str, timestamp=None):
        """添加一行日志"""
        ts = self._format_timestamp(timestamp)
        log_line = f"{ts} {message}"
        self.detailed_logs.append(log_line)

        # 实时输出到控制台（Django控制台）
        if self.console_output:
            # 使用 flush=True 确保实时输出
            print(f"[UITest] {log_line}", flush=True)
    
    async def log_execution_start(self, script, total_actions: int):
        """
        记录执行开始信息

        Args:
            script: UITestScript对象
            total_actions: 总actions数量
        """
        self.start_time = timezone.now()

        # 输出开始信息到控制台
        if self.console_output:
            print("\n" + "=" * 80, flush=True)
            print(f"[UITest] ======== 开始执行UI测试 ========", flush=True)
            print(f"[UITest] 执行记录ID: {self.execution.id}", flush=True)
            print(f"[UITest] 脚本名称: {script.name}", flush=True)
            print(f"[UITest] 脚本ID: {script.id}", flush=True)
            print(f"[UITest] 浏览器类型: {script.browser_type}", flush=True)
            print(f"[UITest] 无头模式: {'是' if script.headless else '否'}", flush=True)
            print(f"[UITest] 视口大小: {script.viewport_width}x{script.viewport_height}", flush=True)
            print(f"[UITest] 超时时间: {script.timeout}ms", flush=True)
            print(f"[UITest] 总Actions数: {total_actions}", flush=True)
            print("=" * 80 + "\n", flush=True)

        self._add_log_line("======== 开始执行UI测试 ========", self.start_time)
        self._add_log_line(f"执行记录ID: {self.execution.id}", self.start_time)
        self._add_log_line(f"脚本名称: {script.name}", self.start_time)
        self._add_log_line(f"脚本ID: {script.id}", self.start_time)
        self._add_log_line(f"浏览器类型: {script.browser_type}", self.start_time)
        self._add_log_line(f"无头模式: {'是' if script.headless else '否'}", self.start_time)
        self._add_log_line(f"视口大小: {script.viewport_width}x{script.viewport_height}", self.start_time)
        self._add_log_line(f"超时时间: {script.timeout}ms", self.start_time)
        self._add_log_line(f"总Actions数: {total_actions}", self.start_time)
        self._add_log_line("========================================", self.start_time)
    
    async def collect_action_result(self, action: Dict[str, Any],
                                   result: Dict[str, Any]):
        """
        采集单个action的执行结果

        Args:
            action: action定义
            result: action执行结果
        """
        action_id = action.get('id', 'unknown')
        action_order = action.get('order', 0)
        action_type = action.get('type', 'unknown')  # 修复：变量名应为 action_type
        description = action.get('description', '')
        selector = action.get('selector')
        params = action.get('params', {})
        
        timestamp = timezone.now()
        
        # 记录详细的action信息
        self._add_log_line(f">> Action {action_order}: {action_type} (ID: {action_id})", timestamp)
        
        if description:
            self._add_log_line(f"描述: {description}", timestamp)
        
        # 记录selector信息
        if selector:
            selector_type = selector.get('type', 'unknown')
            selector_value = selector.get('value', '')
            self._add_log_line(f"Selector: {selector_type}={selector_value}", timestamp)
        elif action_type not in ['navigate', 'wait', 'screenshot']:
            self._add_log_line("Selector: 无", timestamp)
        
        # 记录参数信息
        if params:
            try:
                params_json = json.dumps(params, ensure_ascii=False, indent=2)
                # 如果是多行JSON，需要每行前加时间戳
                if '\n' in params_json:
                    lines = params_json.split('\n')
                    self._add_log_line("参数:", timestamp)
                    for line in lines:
                        if line.strip():
                            self._add_log_line(f"  {line}", timestamp)
                else:
                    self._add_log_line(f"参数: {params_json}", timestamp)
            except Exception:
                self._add_log_line(f"参数: {str(params)}", timestamp)
        
        self._add_log_line("执行中...", timestamp)
        
        # 记录执行结果
        status = result.get('status', 'unknown')
        if status == 'passed':
            message = result.get('message', '')
            self._add_log_line(f"✅ 执行成功: {message}", timestamp)
            
            # 记录结果数据
            data = result.get('data', {})
            if data:
                try:
                    data_json = json.dumps(data, ensure_ascii=False, indent=2)
                    if '\n' in data_json:
                        lines = data_json.split('\n')
                        self._add_log_line("结果数据:", timestamp)
                        for line in lines:
                            if line.strip():
                                self._add_log_line(f"  {line}", timestamp)
                    else:
                        self._add_log_line(f"结果数据: {data_json}", timestamp)
                except Exception:
                    self._add_log_line(f"结果数据: {str(data)}", timestamp)
        elif status == 'skipped':
            message = result.get('message', '')
            self._add_log_line(f"⏭️ 跳过: {message}", timestamp)
        elif status == 'failed':
            error = result.get('error', '')
            message = result.get('message', '')
            self._add_log_line(f"❌ 执行失败: {error}", timestamp)
            if message:
                self._add_log_line(f"错误详情: {message}", timestamp)
        
        # 记录结构化日志（用于统计）
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'action_id': action_id,
            'order': action_order,
            'type': action_type,
            'status': status,
            'message': result.get('message', ''),
        }
        self.logs.append(log_entry)
        
        # 收集截图
        if result.get('status') == 'passed' and 'screenshot_path' in result.get('data', {}):
            screenshot_path = result['data']['screenshot_path']
            self.screenshots.append(screenshot_path)
            self._add_log_line(f"📸 截图已保存: {screenshot_path}", timestamp)
        elif result.get('status') == 'failed':
            # 失败时也截图（如果有）
            if 'screenshot_path' in result.get('data', {}):
                screenshot_path = result['data']['screenshot_path']
                self.screenshots.append(screenshot_path)
                self._add_log_line(f"📸 失败截图已保存: {screenshot_path}", timestamp)
        
        # 记录失败点
        if result.get('status') == 'failed':
            failed_info = {
                'action_id': action_id,
                'order': action_order,
                'type': action_type,
                'error': result.get('error'),
                'message': result.get('message'),
            }
            self.failed_actions.append(failed_info)
            
            # Removed verbose warning logging - failure is already recorded in execution log
    
    async def update_execution(self, all_results: List[Dict[str, Any]]):
        """
        更新执行记录

        Args:
            all_results: 所有action的执行结果列表
        """
        def _update():
            # 统计执行结果
            total_actions = len(all_results)
            passed_actions = len([r for r in all_results if r.get('status') == 'passed'])
            failed_actions = len([r for r in all_results if r.get('status') == 'failed'])

            # 确定最终状态
            if failed_actions > 0:
                self.execution.status = 'failed'
                # 找到第一个失败点
                first_failed = next(
                    (r for r in all_results if r.get('status') == 'failed'),
                    None
                )
                if first_failed:
                    self.execution.error_message = (
                        f"Action {first_failed.get('action_id')} 执行失败: "
                        f"{first_failed.get('error', first_failed.get('message', 'Unknown error'))}"
                    )
            elif passed_actions == 0:
                # 【修复】没有任何成功的action，标记为失败而不是passed
                self.execution.status = 'failed'
                self.execution.error_message = "所有操作都被跳过，脚本可能需要重新录制"
            else:
                self.execution.status = 'passed'
                self.execution.error_message = None

            # 更新完成时间
            completed_time = timezone.now()
            self.execution.completed_at = completed_time
            if self.execution.started_at:
                self.execution.duration = (
                    (completed_time - self.execution.started_at).total_seconds()
                )

            # 更新结果摘要
            self.execution.result_summary = {
                'total_actions': total_actions,
                'passed_actions': passed_actions,
                'failed_actions': failed_actions,
                'action_results': all_results,
            }

            # 更新截图列表
            self.execution.screenshots = self.screenshots

            # 生成详细的执行结束日志
            duration_seconds = self.execution.duration if self.execution.duration else 0
            status_text = '通过' if self.execution.status == 'passed' else '失败'

            # 输出结束信息到控制台
            if self.console_output:
                print("\n" + "=" * 80)
                print(f"[UITest] ======== 执行完成 ========")
                print(f"[UITest] 执行状态: {status_text}")
                print(f"[UITest] 总Actions: {total_actions}")
                print(f"[UITest] 通过: {passed_actions}")
                print(f"[UITest] 失败: {failed_actions}")
                print(f"[UITest] 执行耗时: {duration_seconds:.2f}秒")
                print(f"[UITest] 截图数量: {len(self.screenshots)}")
                print("=" * 80 + "\n")

            self._add_log_line("================================================", completed_time)
            self._add_log_line("======== 执行完成 ========", completed_time)
            self._add_log_line(f"执行状态: {status_text}", completed_time)
            self._add_log_line(f"总Actions: {total_actions}", completed_time)
            self._add_log_line(f"通过: {passed_actions}", completed_time)
            self._add_log_line(f"失败: {failed_actions}", completed_time)
            self._add_log_line(f"执行耗时: {duration_seconds:.2f}秒", completed_time)
            self._add_log_line(f"截图数量: {len(self.screenshots)}", completed_time)
            self._add_log_line("================================================", completed_time)

            # 更新执行日志（使用详细日志）
            log_text = '\n'.join(self.detailed_logs)
            self.execution.execution_log = log_text

            self.execution.save()

        await sync_to_async(_update, thread_sensitive=True)()
