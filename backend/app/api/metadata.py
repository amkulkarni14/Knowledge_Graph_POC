from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.metadata_extractor import s03_schema_extraction as extract, s04_schema_analysis as analysis
from backend.app.core.dependencies import CurrentSession
from backend.app.dto.models import Result, Page, Table
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import execute, operation, require, storage

router = APIRouter(prefix="/sessions/{session_id}/metadata", tags=["metadata"])


@router.post("/extract", response_model=Result[SchemaCatalog])
def run_extract(session: CurrentSession):
    with operation(session):
        return {"data": execute(session, 3, extract.run)}


@router.get("", response_model=Result[SchemaCatalog])
def catalog(session: CurrentSession):
    with operation(session):
        require(session, 3)
        return {"data": session.ctx.catalog}


@router.get("/tables", response_model=Result[Page[dict]])
def tables(session: CurrentSession, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    with operation(session):
        require(session, 3)
        rows = extract.catalog_rows(session.ctx.catalog)
        return {"data": {"items": rows[offset:offset + limit], "total": len(rows), "offset": offset, "limit": limit}}


@router.get("/columns", response_model=Result[list[dict]])
def columns(session: CurrentSession, table: Table):
    with operation(session):
        require(session, 3)
        if table not in session.ctx.catalog.tables:
            raise ApiError(404, "table_not_found", "Table is outside this catalog")
        return {"data": extract.column_rows(session.ctx.catalog, table)}


@router.get("/preview", response_model=Result[list[dict]])
def preview(session: CurrentSession, table: Table, limit: int = Query(20, ge=1, le=100)):
    with operation(session):
        require(session, 3)
        if table not in session.ctx.catalog.tables:
            raise ApiError(404, "table_not_found", "Table is outside this catalog")
        sensitive = set(session.ctx.scope.sensitive_columns)
        try:
            with storage(session):
                rows = session.ctx.source.sample_rows(table, limit)
        except Exception:
            raise ApiError(502, "source_failure", "Source preview failed") from None
        return {"data": jsonable_encoder([{k: v for k, v in row.items() if f"{table}.{k}" not in sensitive}
                                          for row in rows])}


@router.post("/analyze", response_model=Result[dict])
def analyze(session: CurrentSession):
    with operation(session):
        rows = execute(session, 4, analysis.run)
        return {"data": {"tables": rows, "relationships": analysis.relationship_candidates(session.ctx.catalog, rows)}}


@router.get("/analysis", response_model=Result[list[dict]])
def get_analysis(session: CurrentSession):
    with operation(session):
        require(session, 4)
        return {"data": session.ctx.table_analysis}
