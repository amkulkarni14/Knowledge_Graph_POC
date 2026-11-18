"""Run from the repository root: python -m uvicorn backend.app.main:app --workers 1."""
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import ApiSettings
from backend.app.core.middleware import BodyLimitMiddleware
from backend.app.exceptions.handlers import (
    ApiError, api_error_handler, validation_handler, http_handler, unexpected_handler)
from backend.app.repositories.sessions import SessionRepository
from backend.app.services.builds import BuildRunner
from backend.app.api import sessions, sources, metadata, ontology, builds, graphs


def create_app(config: ApiSettings | None = None):
    config = config or ApiSettings()

    @asynccontextmanager
    async def lifespan(app):
        async def reap():
            while True:
                await asyncio.sleep(min(60, config.session_ttl_seconds))
                await asyncio.to_thread(app.state.sessions.cleanup)
        task = asyncio.create_task(reap())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await asyncio.to_thread(app.state.builds.close)
            await asyncio.to_thread(app.state.sessions.close)

    app = FastAPI(title="Knowledge Graph Platform API", version="1.0.0", lifespan=lifespan,
                  description="Process-local workflow sessions; use one worker. No authentication is implemented.")
    app.state.config = config
    app.state.sessions = SessionRepository(config)
    app.state.builds = BuildRunner(config.max_jobs)
    app.add_middleware(BodyLimitMiddleware, max_bytes=config.max_request_bytes)
    app.add_middleware(CORSMiddleware, allow_origins=list(config.cors_origins),
                       allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Content-Type", "Accept"])
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(HTTPException, http_handler)
    app.add_exception_handler(Exception, unexpected_handler)

    @app.get("/api/v1/health", tags=["health"])
    def health():
        return {"data": {"status": "ok", "session_storage": "process-local", "authentication": False}}

    for router in (sessions.router, sources.router, metadata.router, ontology.router, builds.router, graphs.router):
        app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
