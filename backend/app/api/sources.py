from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from kg_pipeline.config import settings
from kg_pipeline.preprocessing import s02_connect
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload, UploadLimits, ALLOWED_EXTENSIONS
from backend.app.core.dependencies import CurrentSession
from backend.app.dto.models import PostgresRequest, Result
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import execute, operation, require

router = APIRouter(prefix="/sessions/{session_id}/sources", tags=["sources"])


@router.post("/sample", response_model=Result[dict])
def sample(session: CurrentSession):
    with operation(session):
        return {"data": execute(session, 2, s02_connect.connect_sample)}


@router.post("/postgres", response_model=Result[dict])
def postgres(body: PostgresRequest, session: CurrentSession):
    with operation(session):
        args = body.model_dump(exclude={"password"})
        args["password"] = body.password.get_secret_value()
        return {"data": execute(session, 2, s02_connect.connect_postgres, **args)}


@router.post("/upload", response_model=Result[dict], openapi_extra={
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["files"], "properties": {"files": {
            "type": "array", "minItems": 1, "items": {"type": "string", "format": "binary"}}}}}}}})
async def upload(request: Request, session: CurrentSession):
    # Parse multipart only after the application middleware has bounded the body.
    # Unlike a bare UploadFile parameter, this also bounds parser file/field counts.
    require(session, 1)
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
                raise ApiError(422, "invalid_file_type", "Only CSV, TSV and text files are supported")
            data = await file.read(limits.max_bytes + 1)
            if len(data) > limits.max_bytes:
                raise ApiError(413, "file_too_large", "A file exceeds the configured upload limit")
            uploads.append(CsvUpload(name, data))
        with operation(session):
            return {"data": await run_in_threadpool(
                execute, session, 2, s02_connect.connect_csv, uploads=uploads, limits=limits)}


@router.get("", response_model=Result[dict])
def status(session: CurrentSession):
    with operation(session):
        return {"data": session.ctx.source_info}
