"""
InkLoop Agent Session & Conversation Persistence.
Durable store saving conversation history, user messages, tool calls, and run traces
surviving process restarts and client refreshes.
"""
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.config import PROJECT_ROOT
from app.agent.schemas import AgentSession, AgentMessage

class SessionStore:
    _instance: Optional["SessionStore"] = None
    _lock = threading.RLock()

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or (PROJECT_ROOT / "runs" / "agent_sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, AgentSession] = {}
        self._file_signatures: Dict[str, tuple[int, int]] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "SessionStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def create_session(self, project_id: str, title: str = "New Session", session_id: Optional[str] = None) -> AgentSession:
        with self._lock:
            sid = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{project_id}"
            now = datetime.now(timezone.utc).isoformat()
            session = AgentSession(
                session_id=sid,
                project_id=project_id,
                title=title,
                created_at=now,
                updated_at=now,
            )
            self._save(session)
            return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        with self._lock:
            file_path = self.sessions_dir / f"{session_id}.json"
            if file_path.exists():
                try:
                    stat = file_path.stat()
                    signature = (stat.st_mtime_ns, stat.st_size)
                    cached = self._cache.get(session_id)
                    if cached is not None and self._file_signatures.get(session_id) == signature:
                        return cached
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    session = AgentSession.model_validate(data)
                    self._cache[session_id] = session
                    self._file_signatures[session_id] = signature
                    return session
                except Exception:
                    return None
            self._cache.pop(session_id, None)
            self._file_signatures.pop(session_id, None)
            return None

    def list_sessions(self, project_id: Optional[str] = None) -> List[AgentSession]:
        with self._lock:
            sessions = []
            present_ids = set()
            for file_path in self.sessions_dir.glob("*.json"):
                try:
                    session_id = file_path.stem
                    present_ids.add(session_id)
                    stat = file_path.stat()
                    signature = (stat.st_mtime_ns, stat.st_size)
                    sess = self._cache.get(session_id)
                    if sess is None or self._file_signatures.get(session_id) != signature:
                        data = json.loads(file_path.read_text(encoding="utf-8"))
                        sess = AgentSession.model_validate(data)
                        self._cache[session_id] = sess
                        self._file_signatures[session_id] = signature
                    if project_id is None or sess.project_id == project_id:
                        sessions.append(sess)
                except Exception:
                    continue
            for session_id in set(self._cache) - present_ids:
                self._cache.pop(session_id, None)
                self._file_signatures.pop(session_id, None)
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            return sessions

    def append_message(self, session_id: str, message: AgentMessage) -> AgentSession:
        with self._lock:
            session = self.get_session(session_id)
            if not session:
                session = self.create_session(project_id="default_project", session_id=session_id)
            session.messages.append(message)
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._save(session)
            return session

    def save_session(self, session: AgentSession) -> AgentSession:
        """Persist an in-flight workflow checkpoint without appending a chat turn."""
        with self._lock:
            current = self.get_session(session.session_id)
            if current and current.project_id != session.project_id:
                raise PermissionError("Agent session belongs to a different project.")
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._save(session)
            return session

    def remove_last_turn(self, session_id: str, project_id: str) -> tuple[AgentSession, List[AgentMessage]]:
        """Remove the newest user prompt and every response message after it."""
        with self._lock:
            session = self.get_session(session_id)
            if not session:
                raise KeyError("Agent session was not found.")
            if session.project_id != project_id:
                raise PermissionError("Agent session belongs to a different project.")
            user_index = next(
                (index for index in range(len(session.messages) - 1, -1, -1) if session.messages[index].role == "user"),
                None,
            )
            if user_index is None:
                raise ValueError("This chat has no prompt to delete or retry.")
            removed = session.messages[user_index:]
            del session.messages[user_index:]
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._save(session)
            return session, removed

    def restore_turn(self, session_id: str, project_id: str, keep_message_count: int, messages: List[AgentMessage]) -> AgentSession:
        """Restore a removed turn after a retry failed before it could be recorded."""
        with self._lock:
            session = self.get_session(session_id)
            if not session or session.project_id != project_id:
                raise KeyError("Agent session was not found in the requested project.")
            if keep_message_count > len(session.messages):
                raise ValueError("Session changed while retry was being prepared; removed turn was not restored automatically.")
            del session.messages[keep_message_count:]
            session.messages.extend(messages)
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._save(session)
            return session

    def _save(self, session: AgentSession) -> None:
        self._cache[session.session_id] = session
        file_path = self.sessions_dir / f"{session.session_id}.json"
        file_path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        stat = file_path.stat()
        self._file_signatures[session.session_id] = (stat.st_mtime_ns, stat.st_size)
