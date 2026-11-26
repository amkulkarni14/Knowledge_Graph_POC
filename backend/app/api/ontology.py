from hashlib import sha256
from copy import copy
from fastapi import APIRouter, Query
from pydantic import ValidationError
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.ontology_compiler import s05_manual_ontology as manual
from kg_pipeline.ontology_compiler import s06_ai_suggestions as ai
from kg_pipeline.ontology_compiler import s07_review_approval as review
from kg_pipeline.ontology_compiler import s08_ontology_validation as validation
from kg_pipeline.ontology_compiler import s09_ontology_repository as versions
from backend.app.core.dependencies import CurrentSession
from backend.app.dto.models import (Result, Page, DraftRequest, OntologyRequest, ClassRequest,
    AttributesRequest, RenameRequest, RelationshipRequest, AIRequest, ReviewRequest,
    ApprovalRequest, ActorRequest, RejectRequest, Identifier, SaveDraftRequest)
from backend.app.exceptions.handlers import ApiError
from backend.app.services import ontology as service
from backend.app.repositories.library import save_working_draft
from backend.app.services.workflow import (execute, operation, require, storage, clear_from, require_enabled,
                                           same_ontology_model)
from backend.app.services.workflow_policy import VALIDATION_ONLY

router = APIRouter(prefix="/sessions/{session_id}/ontology", tags=["ontology"])


@router.post("/draft", response_model=Result[dict])
def draft(body: DraftRequest, session: CurrentSession):
    with operation(session):
        require(session, 3, 4)
        if body.mode == "schema":
            with storage(session):
                result = manual.draft_from_schema(session.ctx, body.ontology_id, body.namespace, body.name, body.author)
            onto, notes = result.ontology, result.notes
        else:
            onto, notes = manual.new_ontology(body.ontology_id, body.namespace, body.name, body.author), []
        service.update_editor(session, onto)
        return {"data": {"ontology": onto.model_dump(mode="json"), "notes": notes}}


@router.get("/draft", response_model=Result[Ontology])
def get_draft(session: CurrentSession):
    with operation(session):
        return {"data": service.editor(session)}


@router.put("/draft", response_model=Result[Ontology])
def replace_draft(body: OntologyRequest, session: CurrentSession):
    with operation(session):
        require(session, 3, 4)
        return {"data": service.update_editor(session, body.ontology)}


@router.post("/draft/revert", response_model=Result[Ontology])
def revert(session: CurrentSession):
    with operation(session):
        if session.saved_draft is None:
            raise ApiError(409, "no_saved_draft", "No stage 5 draft is available")
        return {"data": service.update_editor(session, session.saved_draft.model_copy(deep=True))}


@router.post("/draft/save", response_model=Result[Ontology])
def save(session: CurrentSession, body: SaveDraftRequest | None = None):
    with operation(session):
        onto = service.editor(session)
        if body is not None:
            onto = onto.model_copy(update={"name": body.name})
        saved_draft = session.saved_draft
        if (saved_draft is not None and session.ctx.is_done(5)
                and same_ontology_model(saved_draft, onto)):
            if onto.name != saved_draft.name:
                try:
                    save_working_draft(session.root, onto)
                except OSError:
                    raise ApiError(502, "dependency_failure", "Unable to save the ontology draft") from None
                session.ctx.manual_ontology = onto
                session.saved_draft = onto.model_copy(deep=True)
            session.editor = onto
            return {"data": onto}

        service.check_mappings(session, onto)
        def save(candidate):
            saved = manual.run(candidate, onto=onto)
            save_working_draft(session.root, saved)
            return saved

        saved = execute(session, 5, save)
        session.saved_draft = saved.model_copy(deep=True)
        session.editor = saved.model_copy(deep=True)
        return {"data": saved}


@router.post("/classes", response_model=Result[Ontology])
def add_class(body: ClassRequest, session: CurrentSession):
    with operation(session):
        onto = service.editor(session)
        definition = body.definition
        if not definition.mapping:
            raise ApiError(422, "mapping_required", "A source mapping is required")
        if onto.class_by_name(definition.name):
            raise ApiError(409, "duplicate_class", "Class already exists")
        result = onto.model_copy(deep=True)
        result.classes.append(definition)
        return {"data": service.update_editor(session, result)}


@router.put("/classes/{class_name}/attributes", response_model=Result[Ontology])
def attributes(class_name: str, body: AttributesRequest, session: CurrentSession):
    with operation(session):
        result = service.editor(session).model_copy(deep=True)
        target = result.class_by_name(class_name)
        if target is None:
            raise ApiError(404, "class_not_found", "Class does not exist")
        if len({a.name for a in body.attributes}) != len(body.attributes):
            raise ApiError(422, "duplicate_attribute", "Attribute names must be unique")
        target.attributes = body.attributes
        return {"data": service.update_editor(session, result)}


@router.patch("/classes/{class_name}", response_model=Result[Ontology])
def rename(class_name: str, body: RenameRequest, session: CurrentSession):
    with operation(session):
        onto = service.editor(session)
        if onto.class_by_name(class_name) is None:
            raise ApiError(404, "class_not_found", "Class does not exist")
        if onto.class_by_name(body.name):
            raise ApiError(409, "duplicate_class", "Class already exists")
        return {"data": service.update_editor(session, manual.rename_class(onto, class_name, body.name))}


@router.delete("/classes/{class_name}", response_model=Result[Ontology])
def remove_class(class_name: str, session: CurrentSession):
    with operation(session):
        onto = service.editor(session)
        if onto.class_by_name(class_name) is None:
            raise ApiError(404, "class_not_found", "Class does not exist")
        return {"data": service.update_editor(session, manual.remove_class(onto, class_name))}


@router.post("/relationships", response_model=Result[Ontology])
def add_relationship(body: RelationshipRequest, session: CurrentSession):
    with operation(session):
        onto = service.editor(session)
        if body.definition.key in {r.key for r in onto.relationships}:
            raise ApiError(409, "duplicate_relationship", "Relationship already exists")
        if body.definition.mapping is None:
            raise ApiError(422, "mapping_required", "A source mapping is required")
        result = onto.model_copy(deep=True)
        result.relationships.append(body.definition)
        return {"data": service.update_editor(session, result)}


@router.delete("/relationships", response_model=Result[Ontology])
def remove_relationship(session: CurrentSession, key: str = Query(min_length=1, max_length=200)):
    with operation(session):
        onto = service.editor(session)
        if key not in {r.key for r in onto.relationships}:
            raise ApiError(404, "relationship_not_found", "Relationship does not exist")
        return {"data": service.update_editor(session, manual.remove_relationship(onto, key))}


@router.post("/suggestions", response_model=Result[list[ai.ReviewItem]])
def suggestions(body: AIRequest, session: CurrentSession):
    with operation(session):
        require_enabled(session, 6)
        require(session, 5)
        if body.allowed_tables is not None and (not body.allowed_tables or
                set(body.allowed_tables) - set(session.ctx.catalog.tables)):
            raise ApiError(422, "invalid_allowlist", "Choose existing catalog tables")
        if not ai.settings.groq_available:
            raise ApiError(409, "provider_not_configured", "The AI provider is not configured")
        return {"data": execute(session, 6, ai.run, actor=body.actor, use_groq=True,
                               include_samples=body.include_samples,
                               allowed_tables=set(body.allowed_tables) if body.allowed_tables else None)}


@router.get("/suggestions", response_model=Result[dict])
def get_suggestions(session: CurrentSession):
    with operation(session):
        require(session, 6)
        return {"data": {"items": [i.model_dump(mode="json") for i in session.ctx.ai_items],
                         "metadata": session.ctx.ai_meta}}


@router.post("/suggestions/skip", response_model=Result[dict])
def skip(session: CurrentSession):
    with operation(session):
        execute(session, 6, ai.skip)
        return {"data": {"skipped": True}}


@router.post("/review/preview", response_model=Result[Ontology])
def preview(body: ReviewRequest, session: CurrentSession):
    with operation(session):
        require_enabled(session, 7)
        args = service.review_args(session, body)
        candidate = copy(session.ctx)
        candidate.completed = set(candidate.completed)
        candidate.events = list(candidate.events)
        return {"data": review.run(candidate, **args)}


@router.post("/review", response_model=Result[Ontology])
def apply_review(body: ReviewRequest, session: CurrentSession):
    with operation(session):
        require_enabled(session, 7)
        return {"data": execute(session, 7, review.run, **service.review_args(session, body))}


@router.post("/validate", response_model=Result[dict])
def validate(session: CurrentSession):
    with operation(session):
        def validate_saved_draft(candidate):
            draft = candidate.manual_ontology
            if draft is None:
                raise ApiError(409, "no_saved_draft", "Save your draft before validation")
            report = validation.run(candidate, draft=draft)
            if report.ok:
                candidate.validated_ontology = draft.model_copy(deep=True)
                digest = sha256(draft.model_dump_json().encode("utf-8")).hexdigest()
                candidate.ontology_validation_digest = digest
                candidate.log(8, f"Validated build input: {draft.ontology_id} (sha256:{digest})")
            return report

        policy = session.workflow_policy
        report = execute(session, 8, validate_saved_draft if policy == VALIDATION_ONLY else validation.run)
        return {"data": {**report.model_dump(mode="json"), "ok": report.ok, "summary": report.summary()}}


@router.get("/validation", response_model=Result[dict])
def validation_result(session: CurrentSession):
    with operation(session):
        report = session.ctx.ontology_report
        if report is None:
            raise ApiError(409, "no_validation", "Validate the ontology first")
        return {"data": {**report.model_dump(mode="json"), "ok": report.ok, "summary": report.summary()}}


@router.post("/approve", response_model=Result[Ontology])
def approve(body: ApprovalRequest, session: CurrentSession):
    with operation(session):
        require_enabled(session, 9)
        require(session, 8)
        onto = session.ctx.hybrid_draft
        if onto.created_by.strip().casefold() != body.author.casefold():
            raise ApiError(422, "author_mismatch", "Author must match the reviewed draft")
        return {"data": execute(session, 9, versions.run, author=body.author,
                               reviewer=body.reviewer, repo=service.repository(session))}


@router.get("/versions", response_model=Result[list[dict]])
def list_versions(session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        return {"data": service.repository(session).version_rows(ontology_id)}


def existing_version(session, ontology_id, version):
    repo = service.repository(session)
    if version not in repo.versions(ontology_id):
        raise ApiError(404, "version_not_found", "Ontology version does not exist")
    return repo, repo.get(ontology_id, version)


@router.get("/versions/{version}", response_model=Result[Ontology])
def get_version(version: int, session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        return {"data": existing_version(session, ontology_id, version)[1]}


@router.post("/versions/{version}/rollback", response_model=Result[Ontology])
def rollback(version: int, body: ActorRequest, session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        require_enabled(session, 9)
        require(session, 3, 4)
        repo, old = existing_version(session, ontology_id, version)
        service.check_mappings(session, old)
        draft = repo.rollback(ontology_id, version, body.actor)
        service.update_editor(session, draft)
        return {"data": draft}


@router.post("/use-approved", response_model=Result[Ontology])
def use_approved(session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        require_enabled(session, 9)
        require(session, 3)
        repo = service.repository(session)
        onto = repo.get_approved(ontology_id)
        if onto is None:
            raise ApiError(404, "version_not_found", "No approved ontology is available")
        report = validation.validate_ontology(onto, session.ctx.catalog)
        if not report.ok:
            raise ApiError(422, "incompatible_ontology", "Approved version does not match the source catalog")
        clear_from(session.ctx, 9)
        return {"data": versions.use_existing(session.ctx, ontology_id, repo)}


@router.get("/audit", response_model=Result[Page[dict]])
def audit(session: CurrentSession, ontology_id: Identifier,
          offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    with operation(session):
        rows = list(reversed(service.repository(session).history(ontology_id)))
        return {"data": {"items": rows[offset:offset + limit], "total": len(rows), "offset": offset, "limit": limit}}
