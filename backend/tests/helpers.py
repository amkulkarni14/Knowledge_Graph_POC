"""Shared test helpers for authenticated API tests."""
import bcrypt
from backend.app.core.config import ApiSettings

SECRET = "test-secret-key-test-secret-key-0123456789"
PASSWORD_HASH = bcrypt.hashpw(b"admin", bcrypt.gensalt(4)).decode()  # low cost keeps tests fast


def make_settings(**overrides) -> ApiSettings:
    values = dict(jwt_secret_key=SECRET, auth_username="admin", auth_password_hash=PASSWORD_HASH)
    values.update(overrides)
    return ApiSettings(**values)


def login_headers(client) -> dict:
    token = client.post("/api/v1/login", json={"username": "admin", "password": "admin"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
