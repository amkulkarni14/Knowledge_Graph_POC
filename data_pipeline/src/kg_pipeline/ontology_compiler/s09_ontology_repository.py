"""Stage 9 - Save and version the ontology.

Rules enforced:
  * every save creates a NEW version number; approved versions are immutable;
  * only one APPROVED version per ontology; the previous one becomes SUPERSEDED;
  * approval needs a passing validation report AND a reviewer different from the author;
  * rollback copies an old version into a new draft (history is never rewritten);
  * every action is appended to an audit log.

This file-based repository mirrors kg_meta.ontology_version / kg_meta.ontology_audit
(database/postgres/init/02_kg_meta_schema.sql); swap the storage calls to move it into PostgreSQL.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.ontology_models import OntologyStatus
from kg_pipeline.ontology_compiler.s08_ontology_validation import ValidationReport
from kg_pipeline.ontology_compiler.s08_ontology_validation import validate_ontology


class OntologyRepository:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or settings.ontology_repo_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, ontology_id: str) -> Path:
        d = self.root / ontology_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _file(self, ontology_id: str, version: int) -> Path:
        return self._dir(ontology_id) / f"v{version:04d}.json"

    def _audit(self, ontology_id: str, action: str, version: int, actor: str, detail: dict | None = None):
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "action": action,
                 "version": version, "actor": actor, "detail": detail or {}}
        with open(self._dir(ontology_id) / "audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _write(self, onto: Ontology) -> None:
        self._file(onto.ontology_id, onto.version).write_text(onto.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def definition_hash(onto: Ontology) -> str:
        body = onto.model_dump(mode="json", exclude={"version", "parent_version", "status", "created_at",
                                                     "created_by", "approved_by", "change_note"})
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]

    # ------------------------------------------------------------ queries
    def ontology_ids(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())

    def versions(self, ontology_id: str) -> list[int]:
        return sorted(int(p.stem[1:]) for p in self._dir(ontology_id).glob("v*.json"))

    def get(self, ontology_id: str, version: int) -> Ontology:
        return Ontology.model_validate_json(self._file(ontology_id, version).read_text(encoding="utf-8"))

    def get_approved(self, ontology_id: str) -> Optional[Ontology]:
        for v in reversed(self.versions(ontology_id)):
            o = self.get(ontology_id, v)
            if o.status == OntologyStatus.APPROVED:
                return o
        return None

    def history(self, ontology_id: str) -> list[dict]:
        p = self._dir(ontology_id) / "audit.jsonl"
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def version_rows(self, ontology_id: str) -> list[dict]:
        rows = []
        for v in self.versions(ontology_id):
            o = self.get(ontology_id, v)
            rows.append({"version": v, "status": o.status.value, "parent": o.parent_version,
                         "author": o.created_by, "approver": o.approved_by or "", "classes": len(o.classes),
                         "relationships": len(o.relationships), "hash": self.definition_hash(o),
                         "note": o.change_note, "created_at": o.created_at[:19]})
        return rows

    # ------------------------------------------------------------ commands
    def save_draft(self, onto: Ontology, actor: str) -> Ontology:
        existing = self.versions(onto.ontology_id)
        draft = onto.model_copy(deep=True)
        draft.parent_version = existing[-1] if existing else None
        draft.version = (existing[-1] + 1) if existing else 1
        draft.status = OntologyStatus.DRAFT
        draft.created_by = actor
        draft.approved_by = None
        draft.created_at = datetime.now(timezone.utc).isoformat()
        self._write(draft)
        self._audit(draft.ontology_id, "save_draft", draft.version, actor, {"note": draft.change_note})
        return draft

    def submit(self, ontology_id: str, version: int, actor: str) -> Ontology:
        onto = self.get(ontology_id, version)
        if onto.status != OntologyStatus.DRAFT:
            raise ValueError(f"v{version} is {onto.status.value}; only drafts can be submitted")
        onto.status = OntologyStatus.PENDING_REVIEW
        self._write(onto)
        self._audit(ontology_id, "submit", version, actor)
        return onto

    def approve(self, ontology_id: str, version: int, reviewer: str, report: ValidationReport) -> Ontology:
        if not report.ok:
            raise ValueError(f"cannot approve v{version}: {report.summary()}")
        onto = self.get(ontology_id, version)
        if onto.status not in (OntologyStatus.DRAFT, OntologyStatus.PENDING_REVIEW):
            raise ValueError(f"v{version} is {onto.status.value}; only drafts can be approved")
        if reviewer.strip().lower() == onto.created_by.strip().lower():
            raise ValueError("four-eyes rule: the reviewer must be a different person from the author")
        current = self.get_approved(ontology_id)
        if current is not None:
            current.status = OntologyStatus.SUPERSEDED
            self._write(current)
            self._audit(ontology_id, "supersede", current.version, reviewer)
        onto.status = OntologyStatus.APPROVED
        onto.approved_by = reviewer
        self._write(onto)
        self._audit(ontology_id, "approve", version, reviewer, {"validation": report.summary()})
        return onto

    def reject(self, ontology_id: str, version: int, reviewer: str, reason: str) -> None:
        onto = self.get(ontology_id, version)
        onto.status = OntologyStatus.REJECTED
        self._write(onto)
        self._audit(ontology_id, "reject", version, reviewer, {"reason": reason})

    def rollback(self, ontology_id: str, to_version: int, actor: str) -> Ontology:
        old = self.get(ontology_id, to_version)
        old.change_note = f"Rollback to v{to_version}"
        draft = self.save_draft(old, actor)
        self._audit(ontology_id, "rollback", draft.version, actor, {"from_version": to_version})
        return draft


def run(ctx: PipelineContext, author: str, reviewer: str, repo: OntologyRepository | None = None) -> Ontology:
    """Save the validated draft as a new version and approve it (four-eyes)."""
    draft = ctx.hybrid_draft or ctx.manual_ontology
    if draft is None:
        raise RuntimeError("Stage 5/7 must run first")
    repo = repo or OntologyRepository()
    previous = repo.get_approved(draft.ontology_id)
    # re-validate against the CURRENT approved version (conflict / breaking-change checks)
    report = validate_ontology(draft, ctx.catalog, previous)
    ctx.ontology_report = report
    if not report.ok:
        ctx.log(9, f"Approval blocked: {report.summary()}", "error")
        raise ValueError(f"validation failed: {report.summary()}")
    saved = repo.save_draft(draft, actor=author)
    repo.submit(saved.ontology_id, saved.version, actor=author)
    approved = repo.approve(saved.ontology_id, saved.version, reviewer=reviewer, report=report)
    ctx.invalidate_from(9)
    ctx.approved_ontology = approved
    ctx.log(9, f"Ontology '{approved.ontology_id}' v{approved.version} saved by {author} and approved by {reviewer}"
               + (f" (v{previous.version} superseded)" if previous else ""))
    ctx.mark_done(9)
    return approved


def use_existing(ctx: PipelineContext, ontology_id: str, repo: OntologyRepository | None = None) -> Ontology:
    """Skip editing and build from the already-approved version in the repository."""
    repo = repo or OntologyRepository()
    approved = repo.get_approved(ontology_id)
    if approved is None:
        raise ValueError(f"no approved version for {ontology_id}")
    ctx.invalidate_from(9)
    ctx.approved_ontology = approved
    ctx.log(9, f"Using approved ontology '{ontology_id}' v{approved.version} from the repository")
    ctx.mark_done(9)
    return approved
