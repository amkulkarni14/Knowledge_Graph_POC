from typing import Annotated
from uuid import UUID
from fastapi import Depends, Request
from backend.app.repositories.sessions import Session


def get_session(session_id: UUID, request: Request) -> Session:
    return request.app.state.sessions.get(session_id)


CurrentSession = Annotated[Session, Depends(get_session)]
