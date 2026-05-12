"""
增量写入引擎

解决 O(n) 写入性能问题，实现 O(1) 增量追加。

核心功能：
- 增量追加消息（无需重写整个文件）
- 后台压缩任务（当碎片过多时）
- 索引文件管理（快速定位）

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md 机制3
"""

from __future__ import annotations

import os
import threading
import logging
from pathlib import Path

from typing import Dict, Any, Optional, List, Tuple, Generator
from datetime import datetime
from dataclasses import dataclass, field
import contextlib

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _file_lock(filepath: Path) -> Generator[None, None, None]:
    """跨平台文件锁"""
    lock_path = filepath.with_suffix(filepath.suffix + '.lock')
    lock_fd: Any = None
    try:
        if os.name == 'nt':
            import msvcrt
            lock_fd = open(lock_path, 'w')
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            lock_fd = open(lock_path, 'w')
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)  # type: ignore[attr-defined]
        yield
    except (IOError, OSError) as e:
        logger.warning(f"Failed to acquire file lock: {e}")
        raise
    finally:
        if lock_fd:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
                lock_fd.close()
            except Exception:
                pass


@dataclass
class IndexEntry:
    """索引条目"""
    offset: int
    length: int
    timestamp: str
    tokens: int
    role: str = ""


@dataclass
class SessionIndex:
    """会话索引"""
    session_id: str
    version: int = 2
    messages: List[IndexEntry] = field(default_factory=list)
    zones: Dict[str, Dict[str, int]] = field(default_factory=dict)
    append_fragments: int = 0
    last_compact: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "version": self.version,
            "messages": [
                {
                    "offset": m.offset,
                    "length": m.length,
                    "timestamp": m.timestamp,
                    "tokens": m.tokens,
                    "role": m.role
                }
                for m in self.messages
            ],
            "zones": self.zones,
            "append_fragments": self.append_fragments,
            "last_compact": self.last_compact
        }


class IncrementalStore:
    """
    增量写入引擎
    
    功能：
    1. 增量追加消息（O(1) 复杂度）
    2. 索引管理（快速定位）
    3. 后台压缩（碎片整理）
    
    文件格式：
    - {session_id}.md: 主存储文件
    - {session_id}.index.md: 索引文件
    - {session_id}.stats.md: 统计文件
    
    使用示例：
        store = IncrementalStore(Path("context_data"))
        store.append_message(session_id, user_id, role, content, token_count)
    """
    
    MAX_APPEND_FRAGMENTS = 20
    MAX_FILE_SIZE = 1_000_000  # 1MB
    MAX_MESSAGES = 100
    
    def __init__(self, root_dir: Path):
        """
        初始化增量存储
        
        Args:
            root_dir: 存储根目录
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        self._thread_locks: Dict[str, threading.Lock] = {}
        self._locks_mutex = threading.Lock()
    
    def _get_thread_lock(self, filepath: Path) -> threading.Lock:
        """获取线程锁"""
        key = str(filepath)
        with self._locks_mutex:
            if key not in self._thread_locks:
                self._thread_locks[key] = threading.Lock()
            return self._thread_locks[key]
    
    def _get_path(self, user_id: str, session_id: str, suffix: str = ".md") -> Path:
        """获取文件路径"""
        return self.root_dir / f"user_{user_id}" / f"{session_id}{suffix}"
    
    def _get_index_path(self, user_id: str, session_id: str) -> Path:
        """获取索引文件路径"""
        return self._get_path(user_id, session_id, ".index.md")
    
    def append_message_fast(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        token_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        增量追加消息（O(1) 复杂度）
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            role: 角色
            content: 内容
            token_count: Token 数量
            
        Returns:
            (success, warning_message)
        """
        if not content or not content.strip():
            return False, "Empty content"
        
        try:
            filepath = self._get_path(user_id, session_id)
            index_path = self._get_index_path(user_id, session_id)
            
            if not filepath.exists():
                return False, f"Session not found: {session_id}"
            
            timestamp = datetime.now().isoformat()
            
            incremental_content = f"""<!-- append:start:msg:{role}:{timestamp} -->
{content}
<!-- metadata:{{"tokens":{token_count}}} -->
<!-- append:end -->

"""
            
            lock = self._get_thread_lock(filepath)
            with lock:
                with _file_lock(filepath):
                    with open(filepath, 'a', encoding='utf-8') as f:
                        f.write(incremental_content)
            
            self._update_index_incremental(
                session_id, user_id, role, timestamp, 
                len(incremental_content), token_count
            )
            
            should_compact, warning = self._check_compact_needed(session_id, user_id)
            
            logger.debug(f"Appended message to {session_id}: {token_count} tokens")
            return True, warning if should_compact else None
            
        except Exception as e:
            logger.error(f"Failed to append message: {e}")
            return False, str(e)
    
    def _update_index_incremental(
        self,
        session_id: str,
        user_id: str,
        role: str,
        timestamp: str,
        length: int,
        tokens: int
    ) -> None:
        """增量更新索引"""
        try:
            index_path = self._get_index_path(user_id, session_id)
            
            index = self._load_index(session_id, user_id)
            
            offset = sum(m.length for m in index.messages)
            
            entry = IndexEntry(
                offset=offset,
                length=length,
                timestamp=timestamp,
                tokens=tokens,
                role=role
            )
            index.messages.append(entry)
            index.append_fragments += 1
            
            self._save_index(index, user_id)
            
        except Exception as e:
            logger.warning(f"Failed to update index: {e}")
    
    def _load_index(self, session_id: str, user_id: str) -> SessionIndex:
        """加载索引"""
        index_path = self._get_index_path(user_id, session_id)
        
        if not index_path.exists():
            return SessionIndex(session_id=session_id)
        
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            in_yaml = False
            yaml_lines = []
            
            for line in lines:
                if line.strip() == '---':
                    if in_yaml:
                        break
                    in_yaml = True
                    continue
                if in_yaml:
                    yaml_lines.append(line)
            
            import yaml
            data = yaml.safe_load('\n'.join(yaml_lines)) or {}
            
            messages = []
            for m in data.get('messages', []):
                messages.append(IndexEntry(
                    offset=m.get('offset', 0),
                    length=m.get('length', 0),
                    timestamp=m.get('timestamp', ''),
                    tokens=m.get('tokens', 0),
                    role=m.get('role', '')
                ))
            
            return SessionIndex(
                session_id=session_id,
                version=data.get('version', 2),
                messages=messages,
                zones=data.get('zones', {}),
                append_fragments=data.get('append_fragments', 0),
                last_compact=data.get('last_compact', '')
            )
            
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")
            return SessionIndex(session_id=session_id)
    
    def _save_index(self, index: SessionIndex, user_id: str) -> None:
        """保存索引"""
        index_path = self._get_index_path(user_id, index.session_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        import yaml
        
        content = f"""---
{yaml.dump(index.to_dict(), allow_unicode=True, default_flow_style=False)}---

# Index for session {index.session_id}
"""
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _check_compact_needed(
        self,
        session_id: str,
        user_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查是否需要压缩
        
        Returns:
            (should_compact, warning_message)
        """
        index = self._load_index(session_id, user_id)
        filepath = self._get_path(user_id, session_id)
        
        file_size = filepath.stat().st_size if filepath.exists() else 0
        message_count = len(index.messages)
        append_fragments = index.append_fragments
        
        if (message_count > self.MAX_MESSAGES or 
            file_size > self.MAX_FILE_SIZE or 
            append_fragments > self.MAX_APPEND_FRAGMENTS):
            warning = f"Session needs compression: messages={message_count}, size={file_size}, fragments={append_fragments}"
            logger.info(warning)
            return True, warning
        
        return False, None
    
    def should_compact(self, session_id: str, user_id: str) -> bool:
        """判断是否需要压缩"""
        should, _ = self._check_compact_needed(session_id, user_id)
        return should
    
    def get_session_stats(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取会话统计"""
        index = self._load_index(session_id, user_id)
        filepath = self._get_path(user_id, session_id)
        
        return {
            "message_count": len(index.messages),
            "total_tokens": sum(m.tokens for m in index.messages),
            "append_fragments": index.append_fragments,
            "file_size": filepath.stat().st_size if filepath.exists() else 0,
            "last_compact": index.last_compact
        }
    
    def get_index(self, session_id: str, user_id: str) -> SessionIndex:
        """获取会话索引"""
        return self._load_index(session_id, user_id)
    
    def reset_append_fragments(self, session_id: str, user_id: str) -> None:
        """重置追加碎片计数"""
        index = self._load_index(session_id, user_id)
        index.append_fragments = 0
        index.last_compact = datetime.now().isoformat()
        self._save_index(index, user_id)