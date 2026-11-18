"""Public errors never include database/provider exceptions or submitted secrets."""
from dataclasses import dataclass, field
from typing import Any
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


@dataclass
class ApiError(Exception):
    status: int
    code: str
    message: str
    details: list[dict[str, Any]] = field(default_factory=list)


def response(status, code, message, details=None):
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "details": details or []}})


async def api_error_handler(request: Request, exc: ApiError):
    return response(exc.status, exc.code, exc.message, exc.details)


async def validation_handler(request: Request, exc: RequestValidationError):
    # Pydantic's input/ctx/msg may contain submitted passwords or arbitrary payloads.
    details = [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
    return response(422, "validation_error", "Request validation failed", details)


async def http_handler(request: Request, exc: HTTPException):
    return response(exc.status_code, "http_error", "Request could not be completed")


async def unexpected_handler(request: Request, exc: Exception):
    return response(500, "internal_error", "The operation could not be completed")
