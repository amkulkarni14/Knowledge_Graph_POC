"""Login, current-user and logout. Only /login is public."""
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from backend.app.core.dependencies import CurrentUser
from backend.app.core.security import authenticate, create_access_token
from backend.app.dto.models import Result
from backend.app.exceptions.handlers import ApiError

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    # Not StrictModel: passwords must not be whitespace-stripped.
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256, repr=False)


class AuthUserView(BaseModel):
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserView


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    config = request.app.state.config
    username = authenticate(config, body.username.strip(), body.password)
    if username is None:
        raise ApiError(401, "invalid_credentials", "Invalid username or password")
    return TokenResponse(access_token=create_access_token(config, username), user=AuthUserView(username=username))


@router.get("/me", response_model=Result[AuthUserView])
def me(user: CurrentUser):
    return {"data": {"username": user.username}}


@router.post("/logout", status_code=204)
def logout(user: CurrentUser, request: Request):
    request.app.state.revoked_tokens.revoke(user.token_id, user.expires_at)
    return Response(status_code=204)
