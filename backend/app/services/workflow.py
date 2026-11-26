"""State transitions around the existing pipeline; no processing algorithms are replaced."""
from contextlib import contextmanager
from copy import copy
from threading import RLock
from time import monotonic
from typing import Callable
from pydantic import ValidationError
from kg_pipeline.config import settings as pipeline_settings
from kg_pipeline.core import s01_scope
from kg_pipeline.metadata_extractor import s03_schema_extraction, s04_schema_analysis
from kg_pipeline.preprocessing import s02_connect, s11_extraction, s12_data_quality, s13_cleaning_er
from kg_pipeline.graph_builder import s10_build_plan, s14_graph_builder, s15_graph_validation
from backend.app.exceptions.handlers import ApiError
from backend.app.repositories.workspace_recovery import snapshot_reference
from backend.app.services.workflow_policy import VALIDATION_ONLY, prerequisites, stage_enabled

# Existing pipeline modules use a shared Settings instance. Serialize calls while
# temporarily selecting session storage, restoring it even when a call fails.
PIPELINE_LOCK = RLock()
RESULTS = {3: {"catalog": None}, 4: {"table_analysis": []}, 5: {"manual_ontology": None},
           6: {"ai_items": [], "ai_meta": {}}, 7: {"hybrid_draft": None},
           8: {"ontology_report": None, "validated_ontology": None, "ontology_validation_digest": None}, 9: {"approved_ontology": None},
           10: {"build_plan": None}, 11: {"extraction": None}, 12: {"dq_report": None},
           13: {"clean": None}, 14: {"graph": None, "build_stats": None},
           15: {"graph_report": None}, 16: {"snapshot": None}}


def require(session, *stages):
    missing = session.ctx.require(*stages)
    if missing is not None:
        prerequisite = {1: "Goal & Scope", 2: "Data Sources"}.get(missing, f"stage {missing}")
        raise ApiError(409, "stage_prerequisite", f"Complete {prerequisite} first",
                       [{"missing_stage": missing}])


def require_enabled(session, stage):
    if not stage_enabled(session.workflow_policy, stage):
        raise ApiError(409, "stage_disabled", "This stage is disabled by the workflow policy")


def same_ontology_model(left, right):
    return left.model_copy(update={"name": right.name}) == right


def current_build_ontology(session):
    ctx = session.ctx
    if session.workflow_policy != VALIDATION_ONLY:
        return ctx.approved_ontology if ctx.is_done(9) else None
    # Keep the original validated snapshot and digest for lineage. The display name
    # can change without changing any of the validated model or mapping inputs.
    if (ctx.is_done(8) and ctx.ontology_report is not None and ctx.ontology_report.ok
            and ctx.validated_ontology is not None and ctx.manual_ontology is not None
            and same_ontology_model(ctx.validated_ontology, ctx.manual_ontology)):
        return ctx.validated_ontology
    return None


def require_build_ontology(session):
    require(session, 8 if session.workflow_policy == VALIDATION_ONLY else 9)
    ontology = current_build_ontology(session)
    if ontology is None:
        raise ApiError(409, "ontology_required", "Validate the current ontology before building"
                       if session.workflow_policy == VALIDATION_ONLY else "Approve an ontology before building")
    return ontology


def clear_from(ctx, stage):
    ctx.invalidate_from(stage)
    for number, fields in RESULTS.items():
        if number >= stage:
            for field, value in fields.items():
                setattr(ctx, field, copy(value))


@contextmanager
def storage(session):
    with PIPELINE_LOCK:
        previous = pipeline_settings.storage_dir
        pipeline_settings.storage_dir = session.root
        try:
            yield
        finally:
            pipeline_settings.storage_dir = previous


@contextmanager
def operation(session):
    if not session.lock.acquire(blocking=False):
        raise ApiError(409, "session_busy", "Wait for the current operation")
    try:
        if session.closed:
            raise ApiError(404, "session_not_found", "Session has expired")
        yield
    finally:
        try:
            session.touched = monotonic()
            session.sync()
            session.checkpoint()
        finally:
            session.lock.release()


def execute(session, stage: int, fn: Callable, **kwargs):
    """Publish new stage state only after success; retain previous state on errors."""
    require_enabled(session, stage)
    require(session, *prerequisites(session.workflow_policy, stage))
    if stage == 11:
        require(session, 2)
    if stage >= 10 and session.workflow_policy == VALIDATION_ONLY:
        require_build_ontology(session)
    candidate = copy(session.ctx)
    candidate.completed = set(session.ctx.completed)
    candidate.events = list(session.ctx.events)
    # Source replacement checks input first in s02_connect. Scope changes retain
    # an established connection while discarding all derived results.
    if stage == 1:
        clear_from(candidate, 3)
        candidate.completed = {n for n in candidate.completed if n <= 2}
    elif stage != 2:
        clear_from(candidate, stage)
    try:
        with storage(session):
            result = fn(candidate, **kwargs)
    except ApiError:
        raise
    except s11_extraction.ExtractionLimitError as exc:
        raise ApiError(413, "source_extraction_limit", str(exc)) from None
    except ValidationError:
        raise ApiError(422, "domain_validation", "Domain validation failed") from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ApiError(422, "invalid_operation", "Input cannot be applied to this workflow") from None
    except RuntimeError:
        raise ApiError(409, "workflow_conflict", "Workflow prerequisites are not satisfied") from None
    except Exception:
        raise ApiError(502, "dependency_failure", "A source, provider or storage operation failed") from None
    snapshot = snapshot_reference(session.ctx.snapshot)
    if snapshot is not None:
        session.recovered_snapshot = snapshot
        session.saved_graph_report = session.ctx.graph_report
    session.ctx = candidate
    if stage == 2:
        session.reconnect_required = False
        session.historical_stages = []
    if stage <= 4:
        session.editor = None
        session.saved_draft = None
    if stage == 4 and session.pending_draft is not None:
        session.editor = session.pending_draft
    if stage == 5:
        session.pending_draft = None
    if stage == 1 and candidate.source is not None:
        candidate.completed.add(2)
    session.sync()
    return result


STAGE_FUNCTIONS = {3: s03_schema_extraction.run, 4: s04_schema_analysis.run,
                   10: s10_build_plan.run, 11: s11_extraction.run,
                   12: s12_data_quality.run, 13: s13_cleaning_er.run,
                   14: s14_graph_builder.run, 15: s15_graph_validation.run}


def rules_for(session, request):
    if request.business_rules is None:
        return None
    catalog = session.ctx.catalog
    output = {}
    for table, rules in request.business_rules.items():
        if table not in catalog.tables:
            raise ApiError(422, "invalid_table", "Rule table is outside the catalog")
        output[table] = []
        for rule in rules:
            if not catalog.has_column(table, rule.column):
                raise ApiError(422, "invalid_column", "Rule column is outside the catalog")
            item = (rule.column, rule.rule)
            if rule.values is not None:
                item += (set(v.upper() for v in rule.values),)
            output[table].append(item)
    return output
