from fastapi import APIRouter, Request, Query
from itertools import islice
from fastapi.encoders import jsonable_encoder
from backend.app.core.dependencies import CurrentSession
from backend.app.dto.models import BuildRequest, Result, Page, Table
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import operation, require
from backend.app.services.builds import run_stage, stage_result

router = APIRouter(prefix="/sessions/{session_id}/builds", tags=["builds"])


@router.post("", status_code=202, response_model=Result[dict])
def start(body: BuildRequest, session: CurrentSession, request: Request):
    return {"data": request.app.state.builds.start(session, body)}


@router.get("/status", response_model=Result[dict | None])
def status(session: CurrentSession):
    with session.status_lock:
        return {"data": dict(session.job) if session.job else None}


@router.post("/stages/{stage}", response_model=Result[dict])
def stage(stage: int, body: BuildRequest, session: CurrentSession):
    with operation(session):
        return {"data": run_stage(session, stage, body)}


@router.get("/stages/{stage}", response_model=Result[dict])
def result(stage: int, session: CurrentSession):
    with operation(session):
        if stage not in range(10, 16):
            raise ApiError(404, "stage_not_found", "Choose a build stage from 10 through 15")
        # Reports for blocked validation stages remain available.
        if not session.ctx.is_done(stage) and not (
                stage == 12 and session.ctx.dq_report is not None or stage == 15 and session.ctx.graph_report is not None):
            raise ApiError(409, "no_result", "Run this stage first")
        return {"data": jsonable_encoder(stage_result(session, stage))}


@router.get("/extracted-rows", response_model=Result[Page[dict]])
def extracted(session: CurrentSession, table: Table,
              offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    with operation(session):
        require(session, 11)
        rows = session.ctx.extraction.staged.rows.get(table)
        if rows is None:
            raise ApiError(404, "table_not_found", "Table was not extracted")
        sensitive = set(session.ctx.scope.sensitive_columns)
        items = [{k: v for k, v in row.items() if f"{table}.{k}" not in sensitive}
                 for row in rows[offset:offset + limit]]
        return {"data": jsonable_encoder({"items": items, "total": len(rows), "offset": offset, "limit": limit})}


@router.get("/cleaning/{kind}", response_model=Result[Page[dict]])
def cleaning(kind: str, session: CurrentSession,
             offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    with operation(session):
        require(session, 13)
        if kind not in ("merges", "changes", "quarantine", "records"):
            raise ApiError(404, "result_not_found", "Unknown cleaning result")
        value = getattr(session.ctx.clean, kind)
        items = ([{"node_id": key, **props} for key, props in islice(value.items(), offset, offset + limit)]
                 if isinstance(value, dict) else value[offset:offset + limit])
        return {"data": jsonable_encoder({"items": items, "total": len(value), "offset": offset, "limit": limit})}
