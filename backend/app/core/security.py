"""Password hashing and JWT helpers. Stateless apart from the logout deny-list."""
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4
import hmac
import bcrypt
import jwt

# bcrypt only reads the first 72 bytes; newer releases raise instead of truncating.
_MAX_PASSWORD_BYTES = 72
# Verified against when the username is unknown so response time does not reveal it.
_DUMMY_HASH = bcrypt.hashpw(b"unused", bcrypt.gensalt(12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if not password_hash or len(raw) > _MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:  # malformed hash in configuration
        return False


def authenticate(settings, username: str, password: str) -> str | None:
    """Authenticate the configured bootstrap account or an active metadata user."""
    from backend.app.repositories.graph_versions import user_password_hash

    known = hmac.compare_digest(username.encode("utf-8"), settings.auth_username.encode("utf-8"))
    password_hash = settings.auth_password_hash if known else user_password_hash(username)
    ok = verify_password(password, password_hash or _DUMMY_HASH)
    return username if password_hash and ok else None


def create_access_token(settings, username: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": username, "iat": now, "jti": uuid4().hex,
              "exp": now + timedelta(minutes=settings.access_token_expire_minutes)}
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(settings, token: str) -> dict:
    """Raises jwt.PyJWTError for any invalid, tampered or expired token."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm],
                      options={"require": ["exp", "sub", "jti"]})


class RevokedTokens:
    """Process-local deny-list for logout, consistent with the single-worker session store."""

    def __init__(self):
        self._items: dict[str, float] = {}
        self._lock = Lock()

    def revoke(self, jti: str, expires_at: float) -> None:
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v > now}
            self._items[jti] = expires_at

    def __contains__(self, jti: str) -> bool:
        with self._lock:
            return jti in self._items
