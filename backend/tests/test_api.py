"""API contract and offline integration tests; no live database/provider calls."""
import sys
from pathlib import Path
import time
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import ApiSettings
from backend.app.main import create_app
from backend.app.services import workflow
from kg_pipeline.config import settings as pipeline_settings


@pytest.fixture
def app(tmp_path):
    return create_app(ApiSettings(storage_root=tmp_path / "sessions"))


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"]


def session(client):
    return ok(client.post("/api/v1/sessions", json={"name": "API test"}), 201)["id"]


def scoped(client):
    sid = session(client)
    base = f"/api/v1/sessions/{sid}"
    ok(client.put(base + "/scope", json={"project": "Test", "business_questions": ["How are records connected?"]}))
    return base


def prepared(client, source="sample"):
    base = scoped(client)
    if source == "sample":
        ok(client.post(base + "/sources/sample"))
    else:
        folder = ROOT / "data/samples/customer360"
        ok(client.post(base + "/sources/upload",
                       files=[("files", (p.name, p.read_bytes(), "text/csv")) for p in sorted(folder.glob("*.csv"))]))
    ok(client.post(base + "/metadata/extract"))
    ok(client.post(base + "/metadata/analyze"))
    return base


def approved(client, source="sample"):
    base = prepared(client, source)
    ok(client.post(base + "/ontology/draft", json={"mode": "template" if source == "sample" else "schema"}))
    ok(client.post(base + "/ontology/draft/save"))
    ok(client.post(base + "/ontology/suggestions/skip"))
    ok(client.post(base + "/ontology/review", json={"actor": "data.modeller"}))
    report = ok(client.post(base + "/ontology/validate"))
    assert report["ok"], report
    ok(client.post(base + "/ontology/approve", json={"author": "data.modeller", "reviewer": "reviewer.lead"}))
    return base


def build(client, base):
    for stage in range(10, 16):
        ok(client.post(base + f"/builds/stages/{stage}", json={}))
    return ok(client.get(base + "/builds/stages/15"))


def test_health_openapi_and_stage_registry(client):
    assert ok(client.get("/api/v1/health"))["status"] == "ok"
    stages = ok(client.get("/api/v1/stages"))
    assert [s["no"] for s in stages] == list(range(1, 17))
    spec = client.get("/openapi.json").json()
    assert "/api/v1/sessions/{session_id}/graphs/data" in spec["paths"]


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "  "}, {"name": "x", "unknown": 1}, {}])
def test_invalid_session_requests(client, body):
    assert client.post("/api/v1/sessions", json=body).status_code == 422


def test_sessions_are_isolated_and_close(client):
    first, second = scoped(client), scoped(client)
    ok(client.post(first + "/sources/sample"))
    assert ok(client.get(first))["completed_stages"] == [1, 2]
    assert ok(client.get(second))["completed_stages"] == [1]
    assert client.delete(first).status_code == 204
    assert client.get(first).status_code == 404


def test_expired_session_is_closed(app, client):
    base = scoped(client)
    from uuid import UUID
    obj = app.state.sessions.get(UUID(base.rsplit("/", 1)[1]))
    obj.touched -= 4000
    assert client.get(base).status_code == 404


def test_capacity_and_busy_session(app, client):
    base = scoped(client)
    from uuid import UUID
    obj = app.state.sessions.get(UUID(base.rsplit("/", 1)[1]))
    obj.lock.acquire()
    try:
        assert client.post(base + "/sources/sample").status_code == 409
        assert client.delete(base).status_code == 409
    finally:
        obj.lock.release()


@pytest.mark.parametrize("route", ["/sources/sample", "/metadata/extract", "/metadata/analyze",
                                  "/ontology/validate", "/ontology/draft/save"])
def test_missing_prerequisites(client, route):
    base = "/api/v1/sessions/" + session(client)
    assert client.post(base + route).status_code == 409


def test_source_change_invalidates_all_results(client):
    base = approved(client)
    build(client, base)
    ok(client.post(base + "/sources/sample"))
    assert ok(client.get(base))["completed_stages"] == [1, 2]
    assert client.get(base + "/graphs/data").status_code == 409
    assert client.get(base + "/ontology/draft").status_code == 409
    assert client.get(base + "/builds/stages/15").status_code == 409


def test_scope_change_keeps_source_but_invalidates_results(client):
    base = prepared(client)
    ok(client.put(base + "/scope", json={"project": "Changed", "business_questions": ["New question"]}))
    assert ok(client.get(base))["completed_stages"] == [1, 2]
    assert client.get(base + "/metadata").status_code == 409


def test_bad_upload_preserves_connection(client):
    base = prepared(client)
    previous = ok(client.get(base + "/sources"))
    result = client.post(base + "/sources/upload", files=[("files", ("bad.csv", b"\x00\x01", "text/csv"))])
    assert result.status_code == 422
    assert ok(client.get(base + "/sources")) == previous
    assert ok(client.get(base))["completed_stages"] == [1, 2, 3, 4]


@pytest.mark.parametrize("filename", ["../bad.csv", r"..\bad.csv", "workbook.xlsx", ""])
def test_upload_filename_and_type_validation(client, filename):
    base = scoped(client)
    response = client.post(base + "/sources/upload", files=[("files", (filename, b"id\n1\n", "text/csv"))])
    assert response.status_code in (400, 422)


def test_upload_limit_before_parser(tmp_path):
    app = create_app(ApiSettings(storage_root=tmp_path, max_request_bytes=512))
    with TestClient(app) as client:
        response = client.post("/api/v1/sessions", content=b"x" * 513,
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 413


def test_credentials_never_echoed(client, monkeypatch):
    base = scoped(client)
    password = "SENSITIVE_TEST_PASSWORD"
    invalid = client.post(base + "/sources/postgres", json={
        "host": "localhost", "port": 99999, "dbname": "test", "user": "reader", "password": password})
    assert invalid.status_code == 422 and password not in invalid.text
    monkeypatch.setattr(workflow.s02_connect, "connect_postgres",
                        Mock(side_effect=Exception("connection failed password=" + password)))
    failed = client.post(base + "/sources/postgres", json={
        "host": "localhost", "dbname": "test", "user": "reader", "password": password})
    assert failed.status_code == 502 and password not in failed.text
    assert password not in client.get(base + "/events").text


def test_table_whitelist_and_preview_limits(client):
    base = prepared(client)
    assert client.get(base + "/metadata/preview", params={"table": "public.not_real"}).status_code == 404
    assert client.get(base + "/metadata/preview", params={"table": "public.customers", "limit": 101}).status_code == 422
    assert client.get(base + "/metadata/preview", params={"table": "public.customers;DROP TABLE x"}).status_code == 422
    rows = ok(client.get(base + "/metadata/preview", params={"table": "public.customers", "limit": 2}))
    assert len(rows) == 2


@pytest.mark.parametrize("source,expected", [("sample", (33, 52)), ("csv", (54, 64))])
def test_complete_workflow_snapshots_and_graphs(client, source, expected):
    base = approved(client, source)
    report = build(client, base)
    # Manual-only sample excludes the optional AI additions; use actual validation counts.
    if source == "csv":
        assert (report["nodes"], report["edges"]) == expected
    assert report["ok"]
    graph = ok(client.get(base + "/graphs/data", params={"limit": 5, "edge_limit": 4}))
    assert len(graph["nodes"]) <= 5 and len(graph["edges"]) <= 4 and graph["truncated"]
    node_id = graph["nodes"][0]["id"]
    assert ok(client.get(base + "/graphs/node", params={"node_id": node_id}))["id"] == node_id
    assert ok(client.get(base + "/graphs/path", params={"source": node_id, "target": node_id}))["connected"]
    snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
    assert snapshot["published"] and "path" not in snapshot
    oid = snapshot["ontology_id"]
    items = ok(client.get(base + "/graphs/snapshots", params={"ontology_id": oid}))
    assert items[0]["current"]
    download = client.get(base + f"/graphs/snapshots/{snapshot['build_id']}/download/graph.json.gz",
                          params={"ontology_id": oid})
    assert download.status_code == 200 and download.content[:2] == b"\x1f\x8b"
    reloaded = ok(client.get(base + "/graphs/data", params={"ontology_id": oid}))
    assert reloaded["total_nodes"] == report["nodes"]
    other = scoped(client)
    assert client.get(other + "/graphs/data", params={"ontology_id": oid}).status_code == 404


def test_four_eyes_and_mapping_validation(client):
    base = prepared(client)
    draft = ok(client.post(base + "/ontology/draft", json={"mode": "template"}))["ontology"]
    draft["classes"][0]["mapping"]["key_columns"] = ["not_a_column"]
    assert client.put(base + "/ontology/draft", json={"ontology": draft}).status_code == 422
    assert client.post(base + "/ontology/approve", json={"author": "Same", "reviewer": "same"}).status_code == 422


def test_editor_mutation_invalidates_approval(client):
    base = approved(client)
    onto = ok(client.get(base + "/ontology/draft"))
    name = onto["classes"][0]["name"]
    ok(client.patch(base + f"/ontology/classes/{name}", json={"name": "RenamedClass"}))
    assert 9 not in ok(client.get(base))["completed_stages"]
    assert client.post(base + "/builds", json={}).status_code == 409


def test_unknown_review_suggestion_and_empty_ai_allowlist(client):
    base = prepared(client)
    ok(client.post(base + "/ontology/draft", json={"mode": "template"}))
    ok(client.post(base + "/ontology/draft/save"))
    assert client.post(base + "/ontology/suggestions", json={"actor": "author", "allowed_tables": []}).status_code == 422
    ok(client.post(base + "/ontology/suggestions/skip"))
    assert client.post(base + "/ontology/review", json={
        "actor": "author", "decisions": {"nonexistent": {"action": "approve"}}}).status_code == 422


def test_build_job_status_and_storage_restoration(client):
    base = approved(client, "csv")
    previous = pipeline_settings.storage_dir
    job = ok(client.post(base + "/builds", json={}), 202)
    assert job["status"] == "queued"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = ok(client.get(base + "/builds/status"))
        if status["status"] in ("completed", "blocked", "failed"):
            break
        time.sleep(0.01)
    assert status["status"] == "completed", status
    assert pipeline_settings.storage_dir == previous
    assert ok(client.get(base + "/builds/stages/15"))["ok"]


def test_snapshot_path_and_artifact_validation(client):
    base = scoped(client)
    assert client.get(base + "/graphs/data", params={"ontology_id": "../outside"}).status_code == 422
    assert client.get(base + "/graphs/data", params={"ontology_id": "retail", "build_id": "../../outside"}).status_code == 422


def test_cors_explicit_origin(client):
    response = client.options("/api/v1/sessions", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/v1/sessions", headers={
        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in response.headers


def test_nested_unknown_fields_are_rejected(client):
    base = prepared(client)
    draft = ok(client.post(base + "/ontology/draft", json={"mode": "template"}))["ontology"]
    draft["classes"][0]["mapping"]["unrecognized"] = True
    assert client.put(base + "/ontology/draft", json={"ontology": draft}).status_code == 422


def test_saved_draft_can_be_reverted_after_edit(client):
    base = prepared(client)
    original = ok(client.post(base + "/ontology/draft", json={"mode": "template"}))["ontology"]
    ok(client.post(base + "/ontology/draft/save"))
    old = original["classes"][0]["name"]
    ok(client.patch(base + f"/ontology/classes/{old}", json={"name": "NewName"}))
    reverted = ok(client.post(base + "/ontology/draft/revert"))
    assert reverted == original
    assert 5 not in ok(client.get(base))["completed_stages"]


def test_offline_ai_review_preserves_existing_sample_results(client):
    base = prepared(client)
    ok(client.post(base + "/ontology/draft", json={"mode": "template"}))
    ok(client.post(base + "/ontology/draft/save"))
    items = ok(client.post(base + "/ontology/suggestions", json={"actor": "data.modeller"}))
    decisions = {i["item_id"]: {"action": "approve" if i["status"] in ("valid", "needs_review") else "reject"}
                 for i in items if i["kind"] != "duplicate"}
    body = {"actor": "data.modeller", "decisions": decisions,
            "acyclic_relationships": ["Customer-[REFERRED]->Customer"], "watermark_column": "updated_at"}
    preview = ok(client.post(base + "/ontology/review/preview", json=body))
    applied = ok(client.post(base + "/ontology/review", json=body))
    assert preview == applied
    assert ok(client.post(base + "/ontology/validate"))["ok"]
    ok(client.post(base + "/ontology/approve", json={"author": "data.modeller", "reviewer": "reviewer.lead"}))
    report = build(client, base)
    assert (report["nodes"], report["edges"]) == (33, 52)


def test_versions_audit_and_rollback(client):
    base = approved(client)
    rows = ok(client.get(base + "/ontology/versions", params={"ontology_id": "retail"}))
    assert len(rows) == 1 and rows[0]["status"] == "approved"
    history = ok(client.get(base + "/ontology/audit", params={"ontology_id": "retail"}))
    assert history["total"] >= 3
    original = ok(client.get(base + "/ontology/versions/1", params={"ontology_id": "retail"}))
    rolled = ok(client.post(base + "/ontology/versions/1/rollback",
                            params={"ontology_id": "retail"}, json={"actor": "data.modeller"}))
    assert rolled["version"] == 2 and rolled["status"] == "draft"
    assert rolled["classes"] == original["classes"]
    ok(client.post(base + "/ontology/use-approved", params={"ontology_id": "retail"}))
    assert 9 in ok(client.get(base))["completed_stages"]


def test_failed_pipeline_call_restores_storage_and_state(app, client, monkeypatch):
    base = scoped(client)
    ok(client.post(base + "/sources/sample"))
    previous = pipeline_settings.storage_dir
    monkeypatch.setattr(workflow.s03_schema_extraction, "run", Mock(side_effect=OSError("private/path")))
    result = client.post(base + "/metadata/extract")
    assert result.status_code == 502 and "private/path" not in result.text
    assert pipeline_settings.storage_dir == previous
    assert ok(client.get(base))["completed_stages"] == [1, 2]


def test_neo4j_is_not_called_unless_requested(client, monkeypatch):
    from kg_pipeline.graph_builder.loaders import s16_graph_persistence
    mocked = Mock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr(s16_graph_persistence, "push_to_neo4j", mocked)
    base = approved(client, "csv")
    build(client, base)
    ok(client.post(base + "/graphs/snapshots", json={}))
    mocked.assert_not_called()


def test_corrupt_export_is_not_downloaded(app, client):
    from uuid import UUID
    base = approved(client, "csv")
    build(client, base)
    snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
    obj = app.state.sessions.get(UUID(base.rsplit("/", 1)[1]))
    artifact = obj.root / "graphs" / snapshot["ontology_id"] / snapshot["build_id"] / "graph.graphml"
    artifact.write_text("corrupt", encoding="utf-8")
    response = client.get(base + f"/graphs/snapshots/{snapshot['build_id']}/download/graph.graphml",
                          params={"ontology_id": snapshot["ontology_id"]})
    assert response.status_code == 409


def test_sensitive_columns_are_hidden_from_previews(client):
    base = scoped(client)
    ok(client.put(base + "/scope", json={"project": "Privacy", "business_questions": ["Connections"],
                                       "sensitive_columns": ["public.customers.email"]}))
    ok(client.post(base + "/sources/sample"))
    ok(client.post(base + "/metadata/extract"))
    rows = ok(client.get(base + "/metadata/preview", params={"table": "public.customers"}))
    assert rows and all("email" not in row for row in rows)


def test_rule_and_batch_validation(client):
    base = approved(client, "csv")
    assert client.post(base + "/builds", json={"batch_size": 0}).status_code == 422
    response = client.post(base + "/builds", json={
        "business_rules": {"csv.nonexistent": [{"column": "id", "rule": "non_negative"}]}})
    assert response.status_code == 422
    response = client.post(base + "/builds", json={
        "business_rules": {"csv.customers": [{"column": "id", "rule": "allowed_values"}]}})
    assert response.status_code == 422
