"""Run from the repository root: python -m uvicorn backend.app.main:app --workers 1."""
from contextlib import asynccontextmanager
import asyncio
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import ApiSettings
from backend.app.core.dependencies import get_current_user
from backend.app.core.middleware import BodyLimitMiddleware
from backend.app.core.security import RevokedTokens
from backend.app.exceptions.handlers import (
    ApiError, api_error_handler, validation_handler, http_handler, unexpected_handler)
from backend.app.repositories.sessions import SessionRepository
from backend.app.repositories.graph_versions import recover_interrupted
from backend.app.services.builds import BuildRunner
from backend.app.api import auth, sessions, sources, metadata, ontology, builds, graphs, graph_versions, insights, library


def create_app(config: ApiSettings | None = None):
    config = config or ApiSettings()

    @asynccontextmanager
    async def lifespan(app):
        async def reap():
            while True:
                await asyncio.to_thread(recover_interrupted)
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
                  description="Use one worker for active workflow sessions. Saved workspaces support explicit recovery. Sign in at /api/v1/login "
                              "and send 'Authorization: Bearer <token>'.")
    app.state.config = config
    app.state.revoked_tokens = RevokedTokens()
    app.state.sessions = SessionRepository(config)
    app.state.builds = BuildRunner(config.max_jobs)
    app.add_middleware(BodyLimitMiddleware, max_bytes=config.max_request_bytes)
    app.add_middleware(CORSMiddleware, allow_origins=list(config.cors_origins),
                       allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Content-Type", "Accept", "Authorization"])
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(HTTPException, http_handler)
    app.add_exception_handler(Exception, unexpected_handler)

    @app.get("/api/v1/health", tags=["health"])
    def health():
        return {"data": {"status": "ok", "session_storage": "process-local", "authentication": True}}

    # /login is the only public route besides /health; everything else requires a valid token.
    app.include_router(auth.router, prefix="/api/v1")
    for router in (sessions.router, sources.router, sources.manifest_router, metadata.router, ontology.router, builds.router,
                   graphs.router, graph_versions.router, insights.router, library.router):
        app.include_router(router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    return app


app = create_app()
