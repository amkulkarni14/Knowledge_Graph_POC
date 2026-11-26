"""Versioned, explicitly projected workspace checkpoints in the existing library."""
import hashlib
import json
import re
from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from backend.app.exceptions.handlers import ApiError
from backend.app.repositories.library import catalog
from backend.app.services.workflow_policy import stage_enabled
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.s01_scope import ScopeSheet
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.ontology_compiler.s08_ontology_validation import ValidationReport

VERSION = 1
ACTIVE_JOBS = {"queued", "running", "cancelling", "publishing"}
MODELS = {
    "scope": ScopeSheet, "catalog": SchemaCatalog,
    "manual_ontology": Ontology, "validated_ontology": Ontology,
    "hybrid_draft": Ontology, "approved_ontology": Ontology,
    "ontology_report": ValidationReport,
}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,62}")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS workspace_recovery (
        workspace_id TEXT PRIMARY KEY, version INTEGER NOT NULL, payload TEXT NOT NULL,
        fingerprint TEXT NOT NULL, updated_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
    )""")


def records(root, owner, workspace_id=None):
    with catalog(root) as db:
        _schema(db)
        query = """SELECT w.id,w.name,r.version,r.payload,r.fingerprint,r.updated_at
                   FROM workspace w LEFT JOIN workspace_recovery r ON w.id=r.workspace_id
                   WHERE w.owner=? AND coalesce(r.archived,0)=0"""
        args = (owner,)
        if workspace_id is not None:
            query += " AND w.id=?"
            args += (str(workspace_id),)
        return db.execute(query + " ORDER BY r.updated_at DESC,w.name,w.id", args).fetchall()


def archive(root, session):
    with catalog(root) as db:
        _schema(db)
        db.execute("""INSERT INTO workspace_recovery VALUES (?,?,?,?,?,1)
                      ON CONFLICT(workspace_id) DO UPDATE SET archived=1""",
                   (str(session.id), VERSION, "{}", digest({}), utc_now()))


def delete_workspace(root, workspace_id, owner):
    """Retire the catalog entry and checkpoint together, retaining local artifacts."""
    with catalog(root) as db:
        _schema(db)
        result = db.execute("DELETE FROM workspace WHERE id=? AND owner=?", (str(workspace_id), owner))
        if result.rowcount != 1:
            raise ApiError(404, "session_not_found", "Workspace does not exist or is unavailable")
        db.execute("DELETE FROM workspace_recovery WHERE workspace_id=?", (str(workspace_id),))


def snapshot_reference(manifest):
    if (isinstance(manifest, dict) and manifest.get("storage") != "neo4j"
            and manifest.get("ontology_id") and manifest.get("build_id")):
        return {key: manifest[key] for key in ("ontology_id", "build_id")}
    return None


def checkpoint(session):
    if session.owner is None:
        return
    ctx = session.ctx
    source = ctx.source_info
    source_hint = {key: source[key] for key in ("mode", "assets") if key in source}
    if source_hint:
        source_hint["credential_reference"] = None  # No credential vault is configured.
    evidence = set(ctx.completed)
    if ctx.source is None and session.reconnect_required:
        evidence.update(session.historical_stages)
    values = jsonable_encoder({field: getattr(ctx, field) for field in MODELS})
    payload = {
        "policy": session.workflow_policy, "completed": sorted(evidence),
        "source_version": ctx.source_version, "source": source_hint,
        "domain_id": session.domain_id, "models": values,
        "saved_draft": jsonable_encoder(session.pending_draft or session.saved_draft),
        "table_analysis": ctx.table_analysis, "validation_digest": ctx.ontology_validation_digest,
        "build_plan": ctx.build_plan, "build_request": session.build_request,
        "snapshot": snapshot_reference(ctx.snapshot) or session.recovered_snapshot,
        "published_build": session.published_build,
        "graph_report": ctx.graph_report or session.saved_graph_report,
        "job": session.job, "events": ctx.events[-200:], "summary": session.summary,
    }
    payload = jsonable_encoder(payload)
    # Bind the completion ledger to the captured inputs as well as the whole record.
    payload["input_fingerprint"] = digest({key: payload[key] for key in (
        "policy", "source", "source_version", "domain_id", "models", "build_request")})
    fingerprint = digest(payload)
    if fingerprint == session.checkpoint_fingerprint:
        return
    updated = utc_now()
    with catalog(session.root.parent) as db:
        _schema(db)
        db.execute("""INSERT INTO workspace_recovery VALUES (?,?,?,?,?,0)
                      ON CONFLICT(workspace_id) DO UPDATE SET version=excluded.version,
                      payload=excluded.payload,fingerprint=excluded.fingerprint,updated_at=excluded.updated_at
                      WHERE workspace_recovery.archived=0""",
                   (str(session.id), VERSION, json.dumps(payload), fingerprint, updated))
    session.checkpoint_fingerprint = fingerprint
    session.updated_at = updated


def decode(row):
    _, _, version, text, fingerprint, _ = row
    if version is None:
        return {}, "legacy"
    try:
        payload = json.loads(text)
        if version == VERSION and isinstance(payload, dict) and digest(payload) == fingerprint:
            return payload, "saved"
    except (TypeError, ValueError):
        pass
    return {}, "checkpoint_invalid"


def _legacy_draft(session):
    folder = session.root / "working_drafts"
    if folder.resolve().parent != session.root.resolve():
        return None
    files = list(folder.glob("*.json"))
    if len(files) == 1 and files[0].resolve().parent == folder.resolve():
        try:
            return Ontology.model_validate_json(files[0].read_text(encoding="utf-8"))
        except (ValueError, OSError):
            session.recovery_issues.append("A saved ontology draft could not be read.")
    return None


def _snapshot(session, reference):
    from backend.app.services import graphs
    if reference is None:
        folder = session.root / "graphs"
        if not folder.is_dir() or folder.resolve().parent != session.root.resolve():
            return None
        for path in sorted(folder.iterdir()):
            if not IDENTIFIER.fullmatch(path.name):
                continue
            try:
                pointer = graphs.checked_path(session, path.name, artifact=None) / "CURRENT"
                if pointer.is_file() and pointer.resolve().parent == path.resolve():
                    reference = {"ontology_id": path.name, "build_id": pointer.read_text(encoding="utf-8").strip()}
                    break
            except (OSError, ApiError):
                continue
    if not reference:
        return None
    try:
        ontology, build = reference["ontology_id"], reference["build_id"]
        if not graphs.verify_snapshot(session, ontology, build)["validation"]["ok"]:
            raise ValueError
        return reference
    except (KeyError, TypeError, ValueError, ApiError):
        session.recovery_issues.append("A saved snapshot is missing or failed integrity checks.")
        return None


def restore(session, row):
    payload, state = decode(row)
    session.updated_at = row[-1]
    if state == "checkpoint_invalid":
        session.recovery_issues.append("The workspace checkpoint is damaged or unsupported.")
    if state == "legacy":
        session.recovery_issues.append("This workspace predates checkpoints. Saved artifacts can still be opened.")
    ctx = session.ctx
    session.domain_id = payload.get("domain_id")
    session.build_request = payload.get("build_request")
    session.published_build = payload.get("published_build")
    session.recovered_snapshot = _snapshot(session, payload.get("snapshot"))
    session.saved_graph_report = payload.get("graph_report") if session.recovered_snapshot else None
    job = payload.get("job")
    if job and job["status"] in ACTIVE_JOBS:
        job = {**job, "status": "interrupted", "finished_at": utc_now(),
               "error": {"code": "workspace_restarted", "message": "The job was interrupted. Review the saved state before retrying."}}
        if job.get("steps"):
            from backend.app.services.builds import mark_step
            for step in job["steps"]:
                if step["status"] == "running":
                    mark_step(job, step["stage"], "interrupted")
                elif step["status"] == "pending":
                    mark_step(job, step["stage"], "skipped")
    session.job = job
    ctx.events = payload.get("events", [])
    ctx.source_version = payload.get("source_version", 0)
    ctx.source_info = payload.get("source", {})
    session.reconnect_required = bool(ctx.source_info)
    historical = {stage for stage in payload.get("completed", []) if stage_enabled(session.workflow_policy, stage)}
    session.historical_stages = sorted(historical)
    if historical.intersection(range(11, 16)) and not session.recovered_snapshot:
        session.recovery_issues.append("Staged rows and unsaved graphs must be rebuilt.")
    values = payload.get("models", {})
    for field, model in MODELS.items():
        try:
            if values.get(field) is not None:
                setattr(ctx, field, model.model_validate(values[field]))
        except ValidationError:
            session.recovery_issues.append(f"Saved {field.replace('_', ' ')} could not be restored.")
    try:
        session.saved_draft = Ontology.model_validate(payload["saved_draft"]) if payload.get("saved_draft") else None
    except ValidationError:
        session.recovery_issues.append("A saved ontology draft could not be read.")
    if state == "legacy":
        session.saved_draft = _legacy_draft(session)
    session.pending_draft = session.saved_draft
    session.editor = session.saved_draft
    if 1 in historical and ctx.scope is not None:
        ctx.completed.add(1)
    if 3 in historical and ctx.catalog is not None and 1 in ctx.completed:
        ctx.completed.add(3)
    if 4 in historical and 3 in ctx.completed:
        ctx.table_analysis = payload.get("table_analysis", [])
        ctx.completed.add(4)
    if 5 in historical and 4 in ctx.completed and ctx.manual_ontology and ctx.manual_ontology == session.saved_draft:
        ctx.completed.add(5)
    if payload.get("policy") != session.workflow_policy or 5 not in ctx.completed:
        if 5 in ctx.completed and payload.get("policy") != session.workflow_policy:
            session.recovery_issues.append("Workflow policy changed. Validate the ontology again.")
        ctx.approved_ontology = ctx.hybrid_draft = ctx.validated_ontology = ctx.ontology_report = None
        return
    from backend.app.services.workflow import same_ontology_model
    from backend.app.services.workflow_policy import VALIDATION_ONLY
    if session.workflow_policy == VALIDATION_ONLY:
        validation_digest = payload.get("validation_digest")
        if (8 in historical and ctx.ontology_report and ctx.ontology_report.ok and ctx.validated_ontology
                and same_ontology_model(ctx.validated_ontology, ctx.manual_ontology)
                and hashlib.sha256(ctx.validated_ontology.model_dump_json().encode()).hexdigest() == validation_digest):
            ctx.ontology_validation_digest = validation_digest
            ctx.completed.add(8)
    else:
        # A restart never infers approval from a version file or a completed stage number.
        ctx.approved_ontology = ctx.hybrid_draft = ctx.ontology_report = None
        session.recovery_issues.append("Review and approval must be confirmed again under the governed policy.")
    if 8 not in ctx.completed:
        ctx.validated_ontology = None
    if 8 in ctx.completed and 10 in historical and payload.get("build_plan") is not None:
        ctx.build_plan = payload["build_plan"]
        ctx.completed.add(10)
