"""Bounded active sessions with explicit owner-scoped recovery."""
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
from backend.app.repositories import workspace_recovery as recovery
from backend.app.services.workflow_policy import GOVERNED


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
    workflow_policy: str = GOVERNED
    source_candidate: Any = None
    insights_cache: tuple | None = None
    updated_at: str | None = None
    checkpoint_fingerprint: str | None = None
    domain_id: str | None = None
    reconnect_required: bool = False
    historical_stages: list[int] = field(default_factory=list)
    recovery_issues: list[str] = field(default_factory=list)
    recovered_snapshot: dict | None = None
    published_build: dict | None = None
    saved_graph_report: dict | None = None
    pending_draft: Any = None
    build_request: dict | None = None

    def sync(self):
        with self.status_lock:
            self.completed = sorted(self.ctx.completed)
            self.source_version = self.ctx.source_version
            ctx = self.ctx
            ontology = ctx.build_ontology or ctx.hybrid_draft or self.editor
            draft = ctx.manual_ontology
            self.summary = {
                "source_type": ctx.source_info.get("mode"),
                "source_name": ctx.source_info.get("name"),
                "source_files": len(ctx.source_info.get("files", [])),
                "tables": len(ctx.catalog.tables) if ctx.catalog is not None else None,
                "table_types": dict(Counter(row["type"] for row in ctx.table_analysis)),
                "nodes": ctx.graph.number_of_nodes() if ctx.graph is not None else None,
                "edges": ctx.graph.number_of_edges() if ctx.graph is not None else None,
                "ontology": {
                    "id": ontology.ontology_id,
                    "name": draft.name if draft and draft.ontology_id == ontology.ontology_id else ontology.name,
                    "version": ontology.version,
                    "status": "validated" if ontology is ctx.validated_ontology else ontology.status.value,
                    "classes": len(ontology.classes),
                    "relationships": len(ontology.relationships),
                } if ontology is not None else None,
            }

    def view(self, ttl):
        with self.status_lock:
            return {"id": self.id, "name": self.name, "completed_stages": list(self.completed),
                    "source_version": self.source_version, "summary": self.summary, "job": dict(self.job) if self.job else None,
                    "expires_in_seconds": max(0, int(ttl - (monotonic() - self.touched))),
                    "updated_at": self.updated_at, "domain_id": self.domain_id,
                    "reconnect_required": self.reconnect_required,
                    "historical_stages": self.historical_stages, "recovery_issues": self.recovery_issues,
                    "snapshot": recovery.snapshot_reference(self.ctx.snapshot) or self.recovered_snapshot,
                    "published_build": self.published_build,
                    "build_configuration": self.build_request,
                    "active": True}

    def checkpoint(self):
        with self.status_lock:
            if not self.closed:
                recovery.checkpoint(self)

    def close(self):
        self.closed = True
        for source in (self.source_candidate, self.ctx.source):
            if source is not None:
                try:
                    source.close()
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
            session = Session(sid, name, self.settings.storage_root / str(sid), owner=owner,
                              workflow_policy=self.settings.workflow_policy)
            if owner is not None:
                register_workspace(self.settings.storage_root, sid, owner, name)
                session.checkpoint()
            self._sessions[sid] = session
            return session

    def durable_owned(self, owner):
        with self._lock:
            self.cleanup()
            results = []
            for row in recovery.records(self.settings.storage_root, owner):
                sid, name, _, _, _, updated = row
                active = self._sessions.get(UUID(sid))
                if active:
                    results.append(active.view(self.settings.session_ttl_seconds))
                    continue
                payload, state = recovery.decode(row)
                results.append({
                    "id": sid, "name": name, "updated_at": updated, "active": False,
                    "completed_stages": [], "historical_stages": payload.get("completed", []),
                    "summary": payload.get("summary", {}), "source_version": payload.get("source_version", 0),
                    "reconnect_required": bool(payload.get("source")), "expires_in_seconds": 0,
                    "job": payload.get("job"), "recovery_issues": [] if state == "saved" else [state],
                })
            return results

    def reopen(self, sid: UUID, owner: str):
        with self._lock:
            self.cleanup()
            active = self._sessions.get(sid)
            if active:
                return self.get(sid, owner)
            rows = recovery.records(self.settings.storage_root, owner, sid)
            if not rows:
                raise ApiError(404, "session_not_found", "Workspace does not exist or is unavailable")
            if len(self._sessions) >= self.settings.max_sessions:
                raise ApiError(503, "session_capacity", "Session capacity reached")
            session = Session(sid, rows[0][1], self.settings.storage_root / str(sid), owner=owner,
                              workflow_policy=self.settings.workflow_policy)
            if session.root.resolve().parent != self.settings.storage_root.resolve():
                raise ApiError(409, "workspace_path_invalid", "Workspace files could not be opened safely")
            recovery.restore(session, rows[0])
            session.sync()
            if session.job and session.job["status"] == "interrupted":
                session.checkpoint()
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

    def delete_workspace(self, sid: UUID, owner: str):
        with self._lock:
            session = self._sessions.get(sid)
            if session is None:
                recovery.delete_workspace(self.settings.storage_root, sid, owner)
                return
            if session.owner != owner:
                raise ApiError(404, "session_not_found", "Workspace does not exist or is unavailable")
            if not session.lock.acquire(blocking=False):
                raise ApiError(409, "session_busy", "Wait for the current workspace operation")
            try:
                if session.job and session.job.get("status") in recovery.ACTIVE_JOBS:
                    raise ApiError(409, "session_busy", "Wait for the active build or publication to finish")
                recovery.delete_workspace(self.settings.storage_root, sid, owner)
                session.close()
                del self._sessions[sid]
            finally:
                session.lock.release()

    def delete(self, sid: UUID):
        with self._lock:
            session = self.get(sid)
            if not session.lock.acquire(blocking=False):
                raise ApiError(409, "session_busy", "Wait for the current operation")
            try:
                if session.owner is not None:
                    recovery.archive(self.settings.storage_root, session)
                session.close()
                del self._sessions[sid]
            finally:
                session.lock.release()

    def close(self):
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()
