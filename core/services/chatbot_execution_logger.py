"""
ChatBot Execution Logger Service

Provides unified logging for ChatBot-triggered operations.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Optional, Any, Dict, List, Generator
from dataclasses import dataclass, field

from core.models import ChatBotExecutionLog
from core.models import TestExecution

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """单个日志条目"""
    id: Optional[int] = None
    log_type: str = ''
    title: str = ''
    message: str = ''
    details: Dict[str, Any] = field(default_factory=dict)
    execution_id: Optional[int] = None
    created_at: Optional[str] = None


class ChatBotExecutionLogger:
    """
    ChatBot执行日志收集器
    
    用法:
        logger = ChatBotExecutionLogger(conversation_id)
        logger.start('skill', '执行Skill', '正在执行 xxx')
        logger.log('步骤1完成')
        logger.set_detail('skill_name', 'my_skill')
        logger.finish({'status': 'success'})
        
        # 或者使用上下文管理器
        with ChatBotExecutionLogger(conversation_id) as log:
            log.start('api_test', '执行API测试', '测试用户登录')
            # ... 执行操作
            log.finish({'passed': True})
    """

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self._current_log: Optional[ChatBotExecutionLog] = None
        self._log_ids: List[int] = []
        self._details: Dict[str, Any] = {}

    def start(
        self,
        log_type: str,
        title: str,
        message: str = '',
        details: Optional[Dict[str, Any]] = None
    ) -> ChatBotExecutionLog:
        """开始一个新的日志记录"""
        self._details = details or {}
        self._current_log = ChatBotExecutionLog.objects.create(
            conversation_id=self.conversation_id,
            log_type=log_type,
            title=title,
            message=message,
            details=self._details
        )
        self._log_ids.append(self._current_log.id)  # pyright: ignore
        logger.info(f"[ChatBotLogger] Started: [{log_type}] {title}")
        return self._current_log

    def log(self, message: str) -> None:
        """添加日志消息"""
        if self._current_log:
            current_message = self._current_log.message
            self._current_log.message = f"{current_message}\n{message}" if current_message else message
            self._current_log.save(update_fields=['message'])

    def set_detail(self, key: str, value: Any) -> None:
        """设置详情字段"""
        if self._current_log:
            self._details[key] = value
            self._current_log.details = self._details
            self._current_log.save(update_fields=['details'])

    def set_execution(self, execution_id: int) -> None:
        """关联TestExecution记录"""
        if self._current_log:
            try:
                execution = TestExecution.objects.get(id=execution_id)
                self._current_log.execution = execution
                self._current_log.save(update_fields=['execution'])
            except TestExecution.DoesNotExist:
                logger.warning(f"[ChatBotLogger] Execution {execution_id} not found")

    def finish(self, result: Optional[Dict[str, Any]] = None) -> None:
        """完成日志记录"""
        if self._current_log:
            if result:
                self._current_log.details = {**self._current_log.details, **result}
                self._current_log.save(update_fields=['details'])
            logger.info(f"[ChatBotLogger] Finished: {self._current_log.id}")  # pyright: ignore

    def get_log_ids(self) -> List[int]:
        """获取所有日志ID"""
        return self._log_ids.copy()

    def get_logs(self) -> List[LogEntry]:
        """获取所有日志条目的字典列表"""
        logs = []
        for log_id in self._log_ids:
            try:
                log = ChatBotExecutionLog.objects.get(id=log_id)
                logs.append(LogEntry(
                    id=log.id,  # pyright: ignore
                    log_type=log.log_type,
                    title=log.title,
                    message=log.message,
                    details=log.details,
                    execution_id=log.execution_id,  # pyright: ignore
                    created_at=log.created_at.isoformat() if log.created_at else None
                ))
            except ChatBotExecutionLog.DoesNotExist:
                pass
        return logs

    @contextmanager
    def log_operation(self, log_type: str, title: str, message: str = '') -> Generator[ChatBotExecutionLogger, None, None]:
        """上下文管理器方式记录操作"""
        self.start(log_type, title, message)
        try:
            yield self
            self.finish({'status': 'success'})
        except Exception as e:
            self.finish({'status': 'error', 'error': str(e)})
            raise


def get_chatbot_logger(conversation_id: str) -> ChatBotExecutionLogger:
    """工厂函数：创建Logger实例"""
    return ChatBotExecutionLogger(conversation_id)