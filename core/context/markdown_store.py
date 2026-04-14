"""
Markdown 上下文存储（简化版）

职责：会话上下文的文件存储
特点：
1. 路径确定：user_id + session_id -> 文件路径
2. Markdown 格式：YAML frontmatter + HTML 注释包裹消息
3. 单文件锁：防止并发写入冲突（支持多进程）
4. 无消息数量限制：一个会话一个文件

Reference: docs/context_markdown_storage_design_v2.md
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import re
import threading
import contextlib

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _file_lock(filepath: Path):
    """
    跨平台文件锁（支持多进程）
    
    使用系统级文件锁，确保多进程环境下的并发安全
    """
    lock_path = filepath.with_suffix(filepath.suffix + '.lock')
    lock_fd = None
    try:
        if os.name == 'nt':
            import msvcrt
            lock_fd = open(lock_path, 'w')
            # 使用阻塞锁（LK_LOCK）而非非阻塞锁（LK_NBLCK），
            # 确保并发时排队等待而非直接失败
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            lock_fd = open(lock_path, 'w')
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        yield
    except (IOError, OSError) as e:
        logger.warning(f"Failed to acquire file lock for {filepath}: {e}")
        raise
    finally:
        if lock_fd:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
            except Exception:
                pass


@dataclass
class SessionContext:
    """会话上下文数据结构"""
    session_id: str
    user_id: str
    project_id: Optional[str] = None
    title: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class MarkdownContextStore:
    """
    Markdown 上下文存储
    
    存储格式：
    ---
    session_id: xxx
    user_id: xxx
    ...
    ---
    
    ## Messages
    
    <!-- msg:user:2024-01-15T10:30:00 -->
    用户消息内容
    <!-- endmsg -->
    
    ## Context State
    
    ```yaml
    last_intent: xxx
    ```
    """
    
    MAX_LOCKS_CACHE = 100
    
    def __init__(self, root_dir: Path):
        """
        初始化存储
        
        Args:
            root_dir: 上下文根目录
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        self._thread_locks: Dict[str, threading.Lock] = {}
        self._locks_mutex = threading.Lock()
    
    def _get_thread_lock(self, filepath: Path) -> threading.Lock:
        """
        获取线程锁（同一进程内的线程同步）
        
        使用 LRU 策略限制锁数量，防止内存泄漏
        """
        key = str(filepath)
        with self._locks_mutex:
            if key not in self._thread_locks:
                if len(self._thread_locks) >= self.MAX_LOCKS_CACHE:
                    oldest_key = next(iter(self._thread_locks))
                    del self._thread_locks[oldest_key]
                self._thread_locks[key] = threading.Lock()
            return self._thread_locks[key]
    
    def _get_path(self, user_id: str, session_id: str) -> Path:
        """
        获取确定性路径
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            
        Returns:
            文件路径
            
        Raises:
            ValueError: 路径遍历攻击检测
        """
        filepath = self.root_dir / f"user_{user_id}" / f"{session_id}.md"
        # 路径遍历防护
        resolved = filepath.resolve()
        if not resolved.is_relative_to(self.root_dir.resolve()):
            raise ValueError(f"Path traversal detected: user_id={user_id}, session_id={session_id}")
        return filepath
    
    def create_session(
        self,
        session_id: str,
        user_id: str,
        project_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> bool:
        """
        创建新会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            project_id: 项目 ID (可选)
            title: 会话标题 (可选)
            
        Returns:
            是否创建成功
        """
        try:
            filepath = self._get_path(user_id, session_id)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            now = datetime.now().isoformat()
            
            context = SessionContext(
                session_id=session_id,
                user_id=user_id,
                project_id=project_id,
                title=title or "",
                messages=[],
                context_state={},
                metadata={
                    "project_id": project_id,
                    "title": title or "",
                    "message_count": 0,
                    "created_at": now,
                    "updated_at": now
                },
                created_at=now,
                updated_at=now
            )
            
            content = self._render_markdown(context)
            
            lock = self._get_thread_lock(filepath)
            with lock:
                with _file_lock(filepath):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
            
            logger.debug(f"[MarkdownStore] Created session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to create session: {e}")
            return False
    
    def get_context(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取会话上下文
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            
        Returns:
            上下文字典，不存在返回 None
        """
        try:
            filepath = self._get_path(user_id, session_id)
            
            if not filepath.exists():
                return None
            
            lock = self._get_thread_lock(filepath)
            with lock:
                with _file_lock(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
            
            context = self._parse_markdown(content)
            
            if context.session_id != session_id:
                logger.warning(f"[MarkdownStore] Session ID mismatch")
                return None
            
            return {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "messages": context.messages,
                "context_state": context.context_state,
                "metadata": context.metadata,
                "created_at": context.created_at,
                "updated_at": context.updated_at
            }
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to get context: {e}")
            return None
    
    def append_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        追加消息到会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 消息元数据 (可选)
            
        Returns:
            是否写入成功
        """
        # 空内容检查
        if not content or not content.strip():
            return False
        
        try:
            filepath = self._get_path(user_id, session_id)
            
            if not filepath.exists():
                logger.warning(f"[MarkdownStore] Session not found: {session_id}")
                return False
            
            lock = self._get_thread_lock(filepath)
            with lock:
                with _file_lock(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    context = self._parse_markdown(file_content)
                
                    # 添加消息
                    now = datetime.now().isoformat()
                    message = {
                        "role": role,
                        "content": content,
                        "timestamp": now,
                        "metadata": metadata or {}
                    }
                    context.messages.append(message)
                    
                    # 更新元数据
                    context.metadata["message_count"] = len(context.messages)
                    context.metadata["updated_at"] = now
                    context.updated_at = now
                    
                    # 重新写入（在文件锁内）
                    new_content = self._render_markdown(context)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            
            logger.debug(f"[MarkdownStore] Appended message to session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to append message: {e}")
            return False
    
    def update_context_state(
        self,
        session_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新上下文状态
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            updates: 状态更新字典，值为 None 表示删除该字段
            
        Returns:
            是否更新成功
        """
        try:
            filepath = self._get_path(user_id, session_id)
            
            if not filepath.exists():
                return False
            
            lock = self._get_thread_lock(filepath)
            with lock:
                with _file_lock(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    context = self._parse_markdown(file_content)
                    
                    for key, value in updates.items():
                        if value is None:
                            context.context_state.pop(key, None)
                        else:
                            context.context_state[key] = value
                    context.metadata["updated_at"] = datetime.now().isoformat()
                    
                    new_content = self._render_markdown(context)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            
            logger.debug(f"[MarkdownStore] Updated context state: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to update context state: {e}")
            return False
    
    def delete_context_fields(
        self,
        session_id: str,
        user_id: str,
        fields: List[str]
    ) -> bool:
        """
        删除上下文状态中的指定字段
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            fields: 要删除的字段名列表
            
        Returns:
            是否删除成功
        """
        try:
            filepath = self._get_path(user_id, session_id)
            
            if not filepath.exists():
                return False
            
            lock = self._get_thread_lock(filepath)
            with lock:
                with _file_lock(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    context = self._parse_markdown(file_content)
                    
                    for field in fields:
                        context.context_state.pop(field, None)
                    context.metadata["updated_at"] = datetime.now().isoformat()
                    
                    new_content = self._render_markdown(context)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            
            logger.debug(f"[MarkdownStore] Deleted context fields: {fields} from {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to delete context fields: {e}")
            return False
    
    def get_user_sessions(
        self,
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有会话列表
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制 (可选)
            
        Returns:
            会话列表，按更新时间倒序
        """
        sessions = []
        
        try:
            user_dir = self.root_dir / f"user_{user_id}"
            
            if not user_dir.exists():
                return []
            
            # glob 所有 .md 文件
            for filepath in user_dir.glob("*.md"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    context = self._parse_markdown(content)
                    
                    sessions.append({
                        "session_id": context.session_id,
                        "title": context.metadata.get("title", ""),
                        "created_at": context.created_at,
                        "updated_at": context.updated_at,
                        "message_count": context.metadata.get("message_count", 0)
                    })
                except Exception:
                    continue
            
            # 按更新时间倒序
            sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            if limit:
                sessions = sessions[:limit]
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to get user sessions: {e}")
        
        return sessions
    
    def delete_session(
        self,
        session_id: str,
        user_id: str,
        hard_delete: bool = False
    ) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            hard_delete: 是否彻底删除 (False 则移入归档)
            
        Returns:
            是否删除成功
        """
        try:
            filepath = self._get_path(user_id, session_id)
            
            if not filepath.exists():
                return False
            
            if hard_delete:
                filepath.unlink()
            else:
                # 软删除：移入归档目录
                archive_dir = filepath.parent / "archive"
                archive_dir.mkdir(exist_ok=True)
                
                # 按日期分子目录
                date_dir = archive_dir / datetime.now().strftime("%Y-%m")
                date_dir.mkdir(exist_ok=True)
                
                archive_path = date_dir / filepath.name
                filepath.rename(archive_path)
            
            logger.debug(f"[MarkdownStore] Deleted session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[MarkdownStore] Failed to delete session: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════
    # 内部方法：Markdown 渲染和解析
    # ═══════════════════════════════════════════════════════════════
    
    def _render_markdown(self, context: SessionContext) -> str:
        """
        渲染 Markdown 内容
        
        使用 HTML 注释包裹消息，防止 frontmatter 注入
        """
        lines = []
        
        # Frontmatter
        lines.append("---")
        lines.append(f"session_id: {context.session_id}")
        lines.append(f"user_id: {context.user_id}")
        if context.project_id:
            lines.append(f"project_id: {context.project_id}")
        lines.append(f"created_at: {context.created_at}")
        lines.append(f"updated_at: {context.updated_at}")
        lines.append(f"message_count: {len(context.messages)}")
        if context.title:
            lines.append(f"title: \"{context.title}\"")
        lines.append("---")
        lines.append("")
        
        # Messages
        lines.append("## Messages")
        lines.append("")
        
        for msg in context.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            msg_metadata = msg.get("metadata", {})
            
            # 使用 HTML 注释包裹，防止 --- 破坏结构
            lines.append(f"<!-- msg:{role}:{timestamp} -->")
            lines.append(content)
            # 在 endmsg 前添加 metadata（如果有）
            if msg_metadata:
                import json
                lines.append(f"<!-- metadata:{json.dumps(msg_metadata, ensure_ascii=False)} -->")
            lines.append("<!-- endmsg -->")
            lines.append("")
        
        # Context State
        lines.append("## Context State")
        lines.append("")
        lines.append("```yaml")
        for key, value in context.context_state.items():
            lines.append(f"{key}: {self._render_yaml_value(value)}")
        lines.append("```")
        lines.append("")
        
        return "\n".join(lines)
    
    def _render_yaml_value(self, value: Any) -> str:
        """渲染 YAML 值"""
        if isinstance(value, str):
            return f"\"{value}\""
        elif isinstance(value, (list, dict)):
            import json
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)
    
    def _parse_markdown(self, content: str) -> SessionContext:
        """
        解析 Markdown 内容
        
        Returns:
            SessionContext 对象
        """
        lines = content.split("\n")
        
        # 解析 frontmatter
        metadata = {}
        in_frontmatter = False
        frontmatter_end = 0
        
        for i, line in enumerate(lines):
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    frontmatter_end = i
                    break
            
            if in_frontmatter:
                if ":" in line:
                    key, value = line.split(":", 1)
                    value = value.strip().strip('"')
                    # 尝试解析为数字
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                    metadata[key.strip()] = value
        
        # 解析消息
        messages = []
        current_msg = None
        current_content = []
        
        for i, line in enumerate(lines[frontmatter_end + 1:], start=frontmatter_end + 1):
            # 消息开始标记
            msg_match = re.match(r"<!-- msg:(\w+):([^ ]+) -->", line)
            if msg_match:
                if current_msg:
                    current_msg["content"] = "\n".join(current_content).strip()
                    messages.append(current_msg)
                
                current_msg = {
                    "role": msg_match.group(1),
                    "timestamp": msg_match.group(2),
                    "content": "",
                    "metadata": {}
                }
                current_content = []
                continue
            
            # metadata 标记
            metadata_match = re.match(r"<!-- metadata:(.+) -->", line)
            if metadata_match and current_msg:
                import json
                try:
                    current_msg["metadata"] = json.loads(metadata_match.group(1))
                except json.JSONDecodeError:
                    pass
                continue
            
            # 消息结束标记
            if line.strip() == "<!-- endmsg -->":
                if current_msg:
                    current_msg["content"] = "\n".join(current_content).strip()
                    messages.append(current_msg)
                    current_msg = None
                    current_content = []
                continue
            
            # 消息内容
            if current_msg:
                current_content.append(line)
        
        # 解析 context_state（从 YAML 代码块）
        context_state = {}
        in_state_block = False
        state_lines = []
        
        for line in lines[frontmatter_end + 1:]:
            if line.strip() == "```yaml":
                in_state_block = True
                continue
            if line.strip() == "```" and in_state_block:
                break
            if in_state_block:
                state_lines.append(line)
        
        for line in state_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                context_state[key.strip()] = self._parse_yaml_value(value.strip())
        
        return SessionContext(
            session_id=metadata.get("session_id", ""),
            user_id=metadata.get("user_id", ""),
            project_id=metadata.get("project_id"),
            title=metadata.get("title", ""),
            messages=messages,
            context_state=context_state,
            metadata=metadata,
            created_at=metadata.get("created_at", ""),
            updated_at=metadata.get("updated_at", "")
        )
    
    def _parse_yaml_value(self, value: str) -> Any:
        """解析 YAML 值"""
        # 字符串
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        
        # 数字
        try:
            return int(value)
        except ValueError:
            pass
        
        try:
            return float(value)
        except ValueError:
            pass
        
        # 布尔
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        
        # JSON 数组/对象
        if value.startswith("[") or value.startswith("{"):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        return value