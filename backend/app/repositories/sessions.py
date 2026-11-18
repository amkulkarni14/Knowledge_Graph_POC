"""Bounded, expiring, process-local workflow sessions."""
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, RLock
from time import monotonic
from uuid import UUID, uuid4
from typing import Any
from kg_pipeline.core.context import PipelineContext
from backend.app.core.config import ApiSettings
from backend.app.exceptions.handlers import ApiError


@dataclass
class Session:
    id: UUID
    name: str
    root: Path
    ctx: PipelineContext = field(default_factory=PipelineContext)
    editor: Any = None
    saved_draft: Any = None
    touched: float = field(default_factory=monotonic)
    lock: Any = field(default_factory=Lock)
    status_lock: Any = field(default_factory=RLock)
    completed: list[int] = field(default_factory=list)
    source_version: int = 0
    job: dict | None = None
    closed: bool = False

    def sync(self):
        with self.status_lock:
            self.completed = sorted(self.ctx.completed)
            self.source_version = self.ctx.source_version

    def view(self, ttl):
        with self.status_lock:
            return {"id": self.id, "name": self.name, "completed_stages": list(self.completed),
                    "source_version": self.source_version, "job": dict(self.job) if self.job else None,
                    "expires_in_seconds": max(0, int(ttl - (monotonic() - self.touched)))}

    def close(self):
        self.closed = True
        if self.ctx.source is not None:
            try:
                self.ctx.source.close()
            except Exception:
                pass


class SessionRepository:
    def __init__(self, settings: ApiSettings):
        self.settings = settings
        self._sessions: dict[UUID, Session] = {}
        self._lock = RLock()

    def cleanup(self):
        with self._lock:
            for sid, session in list(self._sessions.items()):
                if monotonic() - session.touched > self.settings.session_ttl_seconds:
                    if session.lock.acquire(blocking=False):
                        try:
                            session.close()
                            del self._sessions[sid]
                        finally:
                            session.lock.release()

    def create(self, name: str):
        with self._lock:
            self.cleanup()
            if len(self._sessions) >= self.settings.max_sessions:
                raise ApiError(503, "session_capacity", "Session capacity reached")
            sid = uuid4()
            session = Session(sid, name, self.settings.storage_root / str(sid))
            self._sessions[sid] = session
            return session

    def get(self, sid: UUID):
        with self._lock:
            self.cleanup()
            session = self._sessions.get(sid)
            if session is None or session.closed:
                raise ApiError(404, "session_not_found", "Session does not exist or has expired")
            session.touched = monotonic()
            return session

    def delete(self, sid: UUID):
        with self._lock:
            session = self.get(sid)
            if not session.lock.acquire(blocking=False):
                raise ApiError(409, "session_busy", "Wait for the current operation")
            try:
                session.close()
                del self._sessions[sid]
            finally:
                session.lock.release()

    def close(self):
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()
