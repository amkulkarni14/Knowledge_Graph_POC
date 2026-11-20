from fastapi import APIRouter, Request, Response, Query
from kg_pipeline.core.context import STAGES
from kg_pipeline.core.s01_scope import run as scope_run
from backend.app.core.dependencies import CurrentSession, CurrentUser
from backend.app.dto.models import Result, SessionCreate, SessionView, ScopeRequest, Page, StageAdvice, StageAdviceRequest
from backend.app.services.workflow import execute, operation

from backend.app.exceptions.handlers import ApiError
from backend.app.services import stage_advice

router = APIRouter(tags=["sessions"])


@router.get("/stages", response_model=Result[list[dict]])
def stages():
    return {"data": STAGES}


@router.post("/sessions", status_code=201, response_model=Result[SessionView])
def create(body: SessionCreate, request: Request, user: CurrentUser):
    session = request.app.state.sessions.create(body.name, owner=user.username)
    return {"data": session.view(request.app.state.config.session_ttl_seconds)}


@router.get("/sessions", response_model=Result[list[SessionView]])
def list_sessions(request: Request, user: CurrentUser):
    return {"data": request.app.state.sessions.list_owned(user.username)}


@router.get("/sessions/{session_id}", response_model=Result[SessionView])
def read(session: CurrentSession, request: Request):
    return {"data": session.view(request.app.state.config.session_ttl_seconds)}


@router.delete("/sessions/{session_id}", status_code=204)
def close(session: CurrentSession, request: Request):
    request.app.state.sessions.delete(session.id)
    return Response(status_code=204)


@router.put("/sessions/{session_id}/scope", response_model=Result[dict])
def scope(body: ScopeRequest, session: CurrentSession):
    with operation(session):
        return {"data": execute(session, 1, scope_run, scope=body.domain()).model_dump(mode="json")}


@router.get("/sessions/{session_id}/scope", response_model=Result[dict | None])
def get_scope(session: CurrentSession):
    with operation(session):
        return {"data": session.ctx.scope.model_dump(mode="json") if session.ctx.scope else None}


@router.get("/sessions/{session_id}/events", response_model=Result[Page[dict]])
def events(session: CurrentSession, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    # A snapshot of append-only events is safe to poll while a job is running.
    items = list(session.ctx.events)
    return {"data": {"items": items[offset:offset + limit], "total": len(items), "offset": offset, "limit": limit}}


@router.post("/sessions/{session_id}/stage-advice/{stage}", response_model=Result[StageAdvice])
def advice(stage: int, body: StageAdviceRequest, session: CurrentSession):
    if stage not in stage_advice.GUIDES:
        raise ApiError(404, "stage_not_found", "Choose a workflow stage or graph exploration view")
    with operation(session):
        facts = stage_advice.context_for(session, stage)
    return {"data": stage_advice.advise(stage, facts, body.question)}
