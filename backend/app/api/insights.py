from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.core.dependencies import CurrentSession
from backend.app.dto.insights import InsightsFilters, InsightsResponse
from backend.app.dto.models import Result
from backend.app.services.insights import dashboard
from backend.app.services.workflow import operation

router = APIRouter(prefix="/sessions/{session_id}", tags=["business insights"])


@router.get("/insights", response_model=Result[InsightsResponse])
def insights(session: CurrentSession, filters: Annotated[InsightsFilters, Query()]):
    with operation(session):
        ctx = session.ctx
        key = (id(ctx), ctx.source_version, id(ctx.catalog), id(ctx.graph), id(ctx.dq_report),
               len(ctx.events), filters.model_dump_json(exclude={"refresh"}))
        entry = session.insights_cache
        if not filters.refresh and entry and entry[0] == key and monotonic() < entry[1]:
            return {"data": entry[2]}
        result = dashboard(session, filters)
        session.insights_cache = (key, monotonic() + 60, result)
        return {"data": result}
