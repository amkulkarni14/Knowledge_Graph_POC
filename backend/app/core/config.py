"""Backend settings and access to the existing pipeline package."""
from dataclasses import dataclass, field
from pathlib import Path
import logging
import os
import secrets
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
PIPELINE_SRC = ROOT / "data_pipeline" / "src"
if str(PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINE_SRC))
load_dotenv(ROOT / ".env")

log = logging.getLogger("kg.auth")
JWT_ALGORITHMS = ("HS256", "HS384", "HS512")


def _jwt_secret() -> str:
    value = os.environ.get("JWT_SECRET_KEY", "").strip()
    if value:
        return value
    log.warning("JWT_SECRET_KEY is not set; using a random per-process key. "
                "Tokens become invalid on restart. Set it in .env.")
    return secrets.token_urlsafe(48)


def _token_minutes() -> int:
    try:
        return int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except ValueError:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from None


@dataclass(frozen=True)
class ApiSettings:
    storage_root: Path = field(default_factory=lambda: Path(
        os.environ.get("KG_API_STORAGE_DIR", str(ROOT / "storage" / "api_sessions"))).resolve())
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        value.strip() for value in os.environ.get(
            "KG_API_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if value.strip()))
    session_ttl_seconds: int = 3600
    max_sessions: int = 100
    max_request_bytes: int = 64 * 1024 * 1024
    max_jobs: int = 2
    workflow_policy: str = field(default_factory=lambda: os.getenv("KG_WORKFLOW_POLICY", "governed").strip())
    deployment_environment: str = field(default_factory=lambda: os.getenv("KG_DEPLOYMENT_ENV", "").strip().lower())
    # Authentication. The default account comes from the environment so it can later
    # be replaced by a users table without touching the login endpoint's contract.
    jwt_secret_key: str = field(default_factory=_jwt_secret, repr=False)
    jwt_algorithm: str = field(default_factory=lambda: os.environ.get("JWT_ALGORITHM", "HS256").strip())
    access_token_expire_minutes: int = field(default_factory=_token_minutes)
    auth_username: str = field(default_factory=lambda: os.environ.get("AUTH_DEFAULT_USERNAME", "admin").strip())
    auth_password_hash: str = field(
        default_factory=lambda: os.environ.get("AUTH_DEFAULT_PASSWORD_HASH", "").strip(), repr=False)

    def __post_init__(self):
        from backend.app.services.workflow_policy import GOVERNED, VALIDATION_ONLY

        if self.workflow_policy not in {GOVERNED, VALIDATION_ONLY}:
            raise ValueError("KG_WORKFLOW_POLICY must be governed or poc_validation_only")
        if self.workflow_policy == VALIDATION_ONLY and self.deployment_environment in {"production", "prod"}:
            raise ValueError("Validation-only workflow policy cannot be used in production")
        if min(self.session_ttl_seconds, self.max_sessions, self.max_request_bytes, self.max_jobs,
               self.access_token_expire_minutes) < 1:
            raise ValueError("API resource limits must be positive")
        if self.jwt_algorithm not in JWT_ALGORITHMS:
            raise ValueError(f"JWT_ALGORITHM must be one of {', '.join(JWT_ALGORITHMS)}")
        if not self.jwt_secret_key:
            raise ValueError("JWT secret key must not be empty")
        if "*" in self.cors_origins:
            raise ValueError("Configure explicit CORS origins")
