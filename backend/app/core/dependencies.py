from dataclasses import dataclass
from typing import Annotated
from uuid import UUID
import jwt
from fastapi import Depends, Request
from backend.app.core.security import decode_access_token
from backend.app.exceptions.handlers import ApiError
from backend.app.repositories.sessions import Session


@dataclass(frozen=True)
class AuthUser:
    username: str
    token_id: str
    expires_at: float


def _unauthorized(message="Authentication required") -> ApiError:
    return ApiError(401, "unauthorized", message)


def get_current_user(request: Request) -> AuthUser:
    """Validate 'Authorization: Bearer <jwt>'. Any problem is a uniform 401."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()
    try:
        claims = decode_access_token(request.app.state.config, token.strip())
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Your session has expired. Sign in again.") from None
    except jwt.PyJWTError:
        raise _unauthorized("Invalid authentication token") from None
    if claims["jti"] in request.app.state.revoked_tokens:
        raise _unauthorized("Your session has ended. Sign in again.")
    return AuthUser(claims["sub"], claims["jti"], float(claims["exp"]))


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]


def get_session(session_id: UUID, request: Request, user: CurrentUser) -> Session:
    return request.app.state.sessions.get(session_id, user.username)


CurrentSession = Annotated[Session, Depends(get_session)]
