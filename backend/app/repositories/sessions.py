"""Bounded, expiring, process-local workflow sessions."""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, RLock
from time import monotonic
from uuid import UUID, uuid4
from typing import Any
from kg_pipeline.core.context import PipelineContext
from backend.app.core.config import ApiSettings
from backend.app.exceptions.handlers import ApiError
from backend.app.repositories.library import register_workspace


@dataclass
class Session:
    id: UUID
    name: str
    root: Path
    owner: str | None = None
    ctx: PipelineContext = field(default_factory=PipelineContext)
    editor: Any = None
    saved_draft: Any = None
    touched: float = field(default_factory=monotonic)
    lock: Any = field(default_factory=Lock)
    status_lock: Any = field(default_factory=RLock)
    completed: list[int] = field(default_factory=list)
    source_version: int = 0
    summary: dict = field(default_factory=dict)
    job: dict | None = None
    closed: bool = False

    def sync(self):
        with self.status_lock:
            self.completed = sorted(self.ctx.completed)
            self.source_version = self.ctx.source_version
            ctx = self.ctx
            ontology = ctx.approved_ontology or ctx.hybrid_draft or self.editor
            self.summary = {
                "source_type": ctx.source_info.get("mode"),
                "source_name": ctx.source_info.get("name"),
                "source_files": len(ctx.source_info.get("files", [])),
                "tables": len(ctx.catalog.tables) if ctx.catalog is not None else None,
                "table_types": dict(Counter(row["type"] for row in ctx.table_analysis)),
                "nodes": ctx.graph.number_of_nodes() if ctx.graph is not None else None,
                "edges": ctx.graph.number_of_edges() if ctx.graph is not None else None,
                "ontology": {
                    "id": ontology.ontology_id, "name": ontology.name, "version": ontology.version,
                    "status": ontology.status.value, "classes": len(ontology.classes),
                    "relationships": len(ontology.relationships),
                } if ontology is not None else None,
            }

    def view(self, ttl):
        with self.status_lock:
            return {"id": self.id, "name": self.name, "completed_stages": list(self.completed),
                    "source_version": self.source_version, "summary": self.summary, "job": dict(self.job) if self.job else None,
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

    def list_owned(self, owner: str):
        with self._lock:
            self.cleanup()
            sessions = (session for session in self._sessions.values()
                        if session.owner == owner and not session.closed)
            return [session.view(self.settings.session_ttl_seconds)
                    for session in sorted(sessions, key=lambda item: item.touched, reverse=True)]

    def create(self, name: str, owner: str | None = None):
        with self._lock:
            self.cleanup()
            if len(self._sessions) >= self.settings.max_sessions:
                raise ApiError(503, "session_capacity", "Session capacity reached")
            sid = uuid4()
            session = Session(sid, name, self.settings.storage_root / str(sid), owner=owner)
            if owner is not None:
                register_workspace(self.settings.storage_root, sid, owner, name)
            self._sessions[sid] = session
            return session

    def get(self, sid: UUID, owner: str | None = None):
        with self._lock:
            self.cleanup()
            session = self._sessions.get(sid)
            if session is None or session.closed or (owner is not None and session.owner != owner):
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
