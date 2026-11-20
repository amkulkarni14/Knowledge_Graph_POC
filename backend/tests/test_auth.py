"""JWT login flow and route protection; offline."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import jwt
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.tests.helpers import SECRET, make_settings, login_headers


@pytest.fixture
def anon(tmp_path):
    with TestClient(create_app(make_settings(storage_root=tmp_path)), raise_server_exceptions=False) as client:
        yield client


def login(client, username="admin", password="admin"):
    return client.post("/api/v1/login", json={"username": username, "password": password})


def test_login_returns_signed_jwt(anon):
    response = login(anon)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer" and body["user"] == {"username": "admin"}
    claims = jwt.decode(body["access_token"], SECRET, algorithms=["HS256"])
    assert claims["sub"] == "admin"
    assert 59 * 60 <= claims["exp"] - claims["iat"] <= 61 * 60


@pytest.mark.parametrize("username,password", [
    ("admin", "wrong"), ("other", "admin"), ("ADMIN", "admin"), ("admin", "x" * 200)])
def test_bad_credentials_are_401_and_uniform(anon, username, password):
    response = login(anon, username, password)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert password not in response.text


def test_missing_hash_disables_login(tmp_path):
    app = create_app(make_settings(storage_root=tmp_path, auth_password_hash=""))
    with TestClient(app) as client:
        assert login(client).status_code == 401


def test_protected_routes_require_token(anon):
    assert anon.get("/api/v1/health").status_code == 200
    for method, path in (("get", "/api/v1/stages"), ("post", "/api/v1/sessions"), ("get", "/api/v1/sessions"),
                         ("get", "/api/v1/me"), ("post", "/api/v1/logout")):
        response = getattr(anon, method)(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


def test_me_and_protected_access_with_token(anon):
    headers = login_headers(anon)
    assert anon.get("/api/v1/me", headers=headers).json() == {"data": {"username": "admin"}}
    assert anon.get("/api/v1/stages", headers=headers).status_code == 200


@pytest.mark.parametrize("header", ["Bearer", "Bearer not.a.jwt", "Basic abc", "token"])
def test_malformed_headers_rejected(anon, header):
    assert anon.get("/api/v1/me", headers={"Authorization": header}).status_code == 401


def forge(**kw):
    now = datetime.now(timezone.utc)
    claims = {"sub": "admin", "jti": "x", "iat": now, "exp": now + timedelta(minutes=5)}
    key = kw.pop("key", SECRET)
    algorithm = kw.pop("algorithm", "HS256")
    claims.update(kw)
    return jwt.encode(claims, key, algorithm=algorithm)


def test_expired_wrong_key_and_missing_claims_rejected(anon):
    expired = forge(exp=datetime.now(timezone.utc) - timedelta(seconds=5))
    response = anon.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401 and "expired" in response.json()["error"]["message"]
    for token in (forge(key="another-secret-another-secret-0123456789"),
                  forge(algorithm="HS512"),
                  jwt.encode({"sub": "admin"}, SECRET, algorithm="HS256")):
        assert anon.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_unsigned_token_rejected(anon):
    token = jwt.encode({"sub": "admin", "jti": "x",
                        "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, key=None, algorithm="none")
    assert anon.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_revokes_token(anon):
    headers = login_headers(anon)
    assert anon.post("/api/v1/logout", headers=headers).status_code == 204
    assert anon.get("/api/v1/me", headers=headers).status_code == 401
    assert anon.get("/api/v1/me", headers=login_headers(anon)).status_code == 200


def test_cors_allows_authorization_header(anon):
    response = anon.options("/api/v1/me", headers={
        "Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization"})
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
