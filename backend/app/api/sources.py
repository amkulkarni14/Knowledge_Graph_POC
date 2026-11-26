from uuid import UUID
from fastapi import APIRouter, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool
from kg_pipeline.preprocessing import s02_connect
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload, UploadLimits, ALLOWED_EXTENSIONS
from backend.app.core.dependencies import CurrentSession
from backend.app.dto.models import Page, PostgresRequest, Result
from backend.app.dto.sources import AssetView, ConnectionRequest, ConnectionView, Connector, ConnectorSpec, PreviewRequest, PreviewView, SelectionRequest
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import execute, operation
from backend.app.services import provider_sources, source_connections as connectors

manifest_router = APIRouter(tags=["sources"])
router = APIRouter(prefix="/sessions/{session_id}/sources", tags=["sources"])


@router.post("/postgres", response_model=Result[dict])
def postgres(body: PostgresRequest, session: CurrentSession):
    with operation(session):
        info = execute(session, 2, s02_connect.connect_postgres, **connectors.postgres_options(body))
        discard_candidate(session)
        return {"data": info}


UPLOAD_BODY = {
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["files"], "properties": {"files": {
            "type": "array", "minItems": 1, "items": {"type": "string", "format": "binary"}}}}}}}}
async def read_upload(request):
    # Parse multipart only after the application middleware has bounded the body.
    # Unlike a bare UploadFile parameter, this also bounds parser file/field counts.
    limits = UploadLimits.from_settings()
    async with request.form(max_files=limits.max_files, max_fields=0,
                            max_part_size=limits.max_bytes) as form:
        entries = list(form.multi_items())
        if not entries or any(k != "files" or not hasattr(v, "read") for k, v in entries):
            raise ApiError(422, "invalid_upload", "Send one or more files in the 'files' multipart field")
        uploads = []
        for _, file in entries:
            name = file.filename or ""
            if not name or len(name) > 255 or "/" in name or "\\" in name:
                raise ApiError(422, "invalid_filename", "Upload filenames must be plain basenames")
            if not name.lower().endswith(ALLOWED_EXTENSIONS):
                raise ApiError(422, "invalid_file_type", "Only CSV files are supported")
            data = await file.read(limits.max_bytes + 1)
            if len(data) > limits.max_bytes:
                raise ApiError(413, "file_too_large", "A file exceeds the configured upload limit")
            uploads.append(CsvUpload(name, data))
        return uploads, limits


@router.post("/upload", response_model=Result[dict], openapi_extra=UPLOAD_BODY)
async def upload(request: Request, session: CurrentSession):
    uploads, limits = await read_upload(request)
    with operation(session):
        info = await run_in_threadpool(execute, session, 2, s02_connect.connect_csv, uploads=uploads, limits=limits)
        discard_candidate(session)
        return {"data": info}


@router.post("/connections/upload", response_model=Result[ConnectionView], openapi_extra=UPLOAD_BODY)
async def upload_candidate(request: Request, session: CurrentSession):
    uploads, limits = await read_upload(request)
    with operation(session):
        candidate = await run_in_threadpool(connectors.prepare_upload, uploads, limits)
        return {"data": remember(session, candidate)}


@router.get("", response_model=Result[dict])
def status(session: CurrentSession):
    with operation(session):
        return {"data": session.ctx.source_info}


@router.get("/schema", response_model=Result[dict[str, list[str]]])
def confirmed_schema(session: CurrentSession):
    with operation(session):
        source = session.ctx.source
        if source is None or not session.ctx.is_done(2):
            raise ApiError(409, "source_not_confirmed", "Confirm or reconnect a data source first")
        try:
            catalog = source.introspect_schema()
        except Exception:
            raise ApiError(502, "source_schema_failed", "Could not read the confirmed source schema") from None
        return {"data": {name: sorted(table.columns) for name, table in sorted(catalog.tables.items())}}


@router.get("/health", response_model=Result[dict])
def health(session: CurrentSession):
    source = session.ctx.source
    if source is None:
        return {"data": {"status": "unconfigured"}}
    try:
        source.ping()
        status = "available"
    except Exception:
        status = "unavailable"
    return {"data": {"status": status, "mode": session.ctx.source_info.get("mode")}}



def discard_candidate(session):
    connectors.close(session.source_candidate)
    session.source_candidate = None


def remember(session, candidate):
    discard_candidate(session)
    session.source_candidate = candidate
    return candidate.info


def candidate_for(session, connection_id):
    candidate = session.source_candidate
    if candidate is None or candidate.info.id != connection_id:
        raise ApiError(404, "source_connection_not_found", "This connection is unavailable in the workspace")
    return candidate


@manifest_router.get("/source-types", response_model=Result[dict[Connector, ConnectorSpec]])
def types():
    return {"data": {
        "sample": {"required": [], "authentication": {}},
        "csv": {"required": [], "authentication": {}, "formats": ALLOWED_EXTENSIONS},
        "postgres": {"required": ["host", "port", "dbname", "user"], "optional": ["sslmode", "schemas"],
                     "authentication": {"password": ["password"]}},
        **{kind: {"required": keys, "optional": provider_sources.OPTIONAL.get(kind, ()),
                  "authentication": provider_sources.AUTH[kind], "location": provider_sources.LOCATIONS.get(kind)}
           for kind, keys in provider_sources.FIELDS.items()},
    }}


@router.post("/test", response_model=Result[ConnectionView])
def test_connection(body: ConnectionRequest, session: CurrentSession):
    with operation(session):
        candidate = connectors.prepare(body, discover=False)
        try:
            return {"data": candidate.info}
        finally:
            candidate.close()


@router.post("/locations", response_model=Result[list[str]])
def locations(body: ConnectionRequest, session: CurrentSession):
    with operation(session):
        config = {key: value.get_secret_value() for key, value in body.configuration.items()}
        if any(len(value) > 4096 for value in config.values()):
            raise ApiError(422, "invalid_source_config", "A connection field exceeds its supported length")
        return {"data": provider_sources.locations(body.source, config)}


@router.post("/connections", response_model=Result[ConnectionView])
def connect(body: ConnectionRequest, session: CurrentSession):
    with operation(session):
        return {"data": remember(session, connectors.prepare(body))}


@router.get("/connections/candidate", response_model=Result[ConnectionView | None])
def pending_connection(session: CurrentSession):
    with operation(session):
        return {"data": session.source_candidate.info if session.source_candidate else None}


@router.get("/connections/{connection_id}/assets", response_model=Result[Page[AssetView]])
def assets(connection_id: UUID, session: CurrentSession, offset: int = Query(0, ge=0),
           limit: int = Query(25, ge=1, le=100), search: str = Query("", max_length=200)):
    with operation(session):
        candidate = candidate_for(session, connection_id)
        entries = [asset for asset in candidate.catalog.tables.values()
                   if search.casefold() in (asset.source_path or asset.name).casefold()]
        return {"data": {"items": [{"id": asset.name, "name": asset.source_path or asset.name,
                                    "kind": asset.asset_kind, "columns": len(asset.columns),
                                    "size_bytes": asset.size_bytes, "relationship_origin": asset.relationship_origin}
                                   for asset in entries[offset:offset + limit]],
                         "total": len(entries), "offset": offset, "limit": limit}}


@router.post("/connections/{connection_id}/preview", response_model=Result[PreviewView])
def preview(connection_id: UUID, body: PreviewRequest, session: CurrentSession):
    with operation(session):
        candidate = candidate_for(session, connection_id)
        table = candidate.catalog.table(body.asset)
        if table is None:
            raise ApiError(404, "source_asset_not_found", "This asset is unavailable in the connection")
        try:
            if not table.columns and hasattr(candidate.source, "describe"):
                table = candidate.source.describe(body.asset)
            columns = body.columns if body.columns is not None else list(table.columns)
            if not set(columns) <= table.columns.keys():
                raise ApiError(422, "invalid_columns", "Select columns from this asset")
            sensitive = {item.casefold() for item in session.ctx.scope.sensitive_columns} if session.ctx.scope else set()
            columns = [name for name in columns if f"{body.asset}.{name}".casefold() not in sensitive]
            rows = candidate.source.sample_rows(body.asset, body.limit) if columns else []
            safe = [{name: row.get(name) for name in columns} for row in rows[:body.limit]]
            if sum(len(repr(row).encode("utf-8")) for row in safe) > 1024 * 1024:
                raise ApiError(413, "source_preview_limit", "Reduce the preview row count or selected columns")
            return {"data": {"columns": [table.columns[name] for name in columns], "rows": jsonable_encoder(safe)}}
        except ApiError:
            raise
        except Exception:
            raise ApiError(502, "source_preview_failed", "Could not preview this asset") from None


@router.post("/connections/{connection_id}/select", response_model=Result[ConnectionView])
def select(connection_id: UUID, body: SelectionRequest, session: CurrentSession):
    with operation(session):
        candidate = candidate_for(session, connection_id)
        try:
            selected = connectors.SelectedSource(candidate, body.assets)
        except ApiError:
            raise
        except Exception:
            raise ApiError(422, "source_selection_failed", "Could not validate the selected assets") from None
        info = candidate.info.model_copy(update={"asset_count": len(body.assets)})
        status = {"mode": info.source, **info.model_dump(mode="json"), "assets": body.assets}
        if info.source == "csv":
            reports = [report for report in candidate.source.reports if report.table in body.assets]
            status["files"] = [report.as_row() for report in reports]
            status["links"] = [{"from": report.table, **link} for report in reports for link in report.link_specs
                               if link["to_table"] in body.assets]
            status["warnings"] = candidate.source.warnings
        execute(session, 2, s02_connect.activate_source, source=selected, info=status)
        session.source_candidate = None
        with session.status_lock:
            session.job = None
        return {"data": info}


@router.delete("/connections/{connection_id}", status_code=204)
def cancel_candidate(connection_id: UUID, session: CurrentSession):
    with operation(session):
        candidate_for(session, connection_id)
        discard_candidate(session)
        return Response(status_code=204)


@router.delete("", status_code=204)
def disconnect(session: CurrentSession):
    with operation(session):
        execute(session, 2, s02_connect.activate_source, source=None, info={})
        discard_candidate(session)
        with session.status_lock:
            session.job = None
        return Response(status_code=204)
