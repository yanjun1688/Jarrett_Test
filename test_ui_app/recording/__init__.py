"""
录制模块

推荐使用 SyncBrowserRecorder（同步模式 + 线程隔离）进行浏览器录制。
"""
from .sync_recorder import SyncBrowserRecorder
from .session_manager import RecordingSessionManager

__all__ = [
    'SyncBrowserRecorder',
    'RecordingSessionManager',
]
